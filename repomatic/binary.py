# Copyright Kevin Deldycke <kevin@deldycke.com> and contributors.
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

"""Binary build targets and verification utilities.

Defines the Nuitka compilation targets for all supported platforms and
provides binary architecture verification using exiftool.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

from extra_platforms import is_windows

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Final


NUITKA_BUILD_TARGETS = {
    "linux-arm64": {
        "os": "ubuntu-24.04-arm",
        "platform_id": "linux",
        "arch": "arm64",
        "extension": "bin",
    },
    "linux-x64": {
        "os": "ubuntu-24.04",
        "platform_id": "linux",
        "arch": "x64",
        "extension": "bin",
    },
    "macos-arm64": {
        "os": "macos-26",
        "platform_id": "macos",
        "arch": "arm64",
        "extension": "bin",
    },
    "macos-x64": {
        "os": "macos-26-intel",
        "platform_id": "macos",
        "arch": "x64",
        "extension": "bin",
    },
    "windows-arm64": {
        "os": "windows-11-arm",
        "platform_id": "windows",
        "arch": "arm64",
        "extension": "exe",
    },
    "windows-x64": {
        "os": "windows-2025",
        "platform_id": "windows",
        "arch": "x64",
        "extension": "exe",
    },
}
"""List of GitHub-hosted runners used for Nuitka builds.

The key of the dictionary is the target name, which is used as a short name for
user-friendlyness. As such, it is used to name the compiled binary.

Values are dictionaries with the following keys:

- `os`: Operating system name, as used in [GitHub-hosted runners](https://docs.github.com/en/actions/writing-workflows/choosing-where-your-workflow-runs/choosing-the-runner-for-a-job#standard-github-hosted-runners-for-public-repositories).

    :::{hint}
    We choose to run the compilation only on the latest supported version of each
    OS, for each architecture. Note that macOS and Windows do not have the latest
    version available for each architecture.
    :::

- `platform_id`: Platform identifier, as defined by [Extra Platform](https://github.com/kdeldycke/extra-platforms).

- `arch`: Architecture identifier.

    :::{note}
    Architecture IDs are [inspired from those specified for self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/supported-architectures-and-operating-systems-for-self-hosted-runners#supported-processor-architectures)
    :::

    :::{note}
    Maybe we should just adopt [target triple](https://mcyoung.xyz/2025/04/14/target-triples/).
    :::

- `extension`: File extension of the compiled binary.
"""


FLAT_BUILD_TARGETS = [
    {"target": target_id} | target_data
    for target_id, target_data in NUITKA_BUILD_TARGETS.items()
]
"""List of build targets in a flat format, suitable for matrix inclusion."""


BINARY_AFFECTING_PATHS: Final[tuple[str, ...]] = (
    ".github/workflows/release.yaml",
    "pyproject.toml",
    "tests/",
    "uv.lock",
)
"""Path prefixes that always affect compiled binaries, regardless of the project.

Project-specific source directories (derived from `[project.scripts]` in
`pyproject.toml`) are added dynamically by
{attr}`~repomatic.metadata.Metadata.binary_affecting_paths`.
"""

SKIP_BINARY_BUILD_BRANCHES: Final[frozenset[str]] = frozenset((
    # Autofix branches that don't affect compiled binaries.
    "format-json",
    "format-markdown",
    "format-images",
    "format-shell",
    "sync-gitignore",
    "sync-mailmap",
    "update-deps-graph",
))
"""Branch names for which binary builds should be skipped.

These branches contain changes that do not affect compiled binaries:

- `.mailmap` updates only affect contributor attribution
- Documentation and image changes don't affect code
- `.gitignore` and JSON config changes don't affect binaries

This allows workflows to skip expensive Nuitka compilation jobs for PRs that cannot
possibly change the binary output.
"""

# Map each target to their exiftool architecture strings.
# Ubuntu:
#   CPU Type      : Arm 64-bits (Armv8/AArch64)
#   CPU Type      : AMD x86-64
# macOS:
#   CPU Type      : ARM 64-bit
#   CPU Type      : x86 64-bit
# Windows
#   Machine Type  : ARM64 little endian
#   Machine Type  : AMD AMD64
BINARY_ARCH_MAPPINGS: Final[dict[str, tuple[str, str]]] = {
    "linux-arm64": ("CPUType", "Arm 64-bits"),
    "linux-x64": ("CPUType", "AMD x86-64"),
    "macos-arm64": ("CPUType", "ARM 64-bit"),
    "macos-x64": ("CPUType", "x86 64-bit"),
    "windows-arm64": ("MachineType", "ARM64"),
    "windows-x64": ("MachineType", "AMD64"),
}
"""Mapping of build targets to (exiftool_field, expected_substring) tuples.

ABI signatures reported by `file(1)` for each compiled binary:

- `linux-arm64`: ELF 64-bit LSB pie executable, ARM aarch64, version 1 (SYSV),
  dynamically linked, interpreter /lib/ld-linux-aarch64.so.1, for GNU/Linux 3.7.0,
  stripped
- `linux-x64`: ELF 64-bit LSB pie executable, x86-64, version 1 (SYSV),
  dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, for GNU/Linux 3.2.0,
  stripped
- `macos-arm64`: Mach-O 64-bit executable arm64
- `macos-x64`: Mach-O 64-bit executable x86_64
- `windows-arm64`: PE32+ executable (console) Aarch64, for MS Windows
- `windows-x64`: PE32+ executable (console) x86-64, for MS Windows
"""


def get_exiftool_command() -> str:
    """Return the platform-appropriate exiftool command.

    On Windows, exiftool is installed as `exiftool.exe`.
    """
    return "exiftool.exe" if is_windows() else "exiftool"


def run_exiftool(binary_path: Path) -> dict[str, str]:
    """Run exiftool on a binary and return parsed JSON output.

    :param binary_path: Path to the binary file.
    :return: Dictionary of exiftool metadata.
    :raises subprocess.CalledProcessError: If exiftool fails.
    :raises json.JSONDecodeError: If output is not valid JSON.
    """
    cmd = get_exiftool_command()
    if not shutil.which(cmd):
        msg = f"{cmd} not found on PATH. Install exiftool before verifying binaries."
        raise FileNotFoundError(msg)
    result = subprocess.run(
        [cmd, "-json", "-CPUType", "-MachineType", str(binary_path.resolve())],
        capture_output=True,
        text=True,
        check=True,
    )
    logging.debug(f"ExifTool output:\n{result.stdout}")
    output: list[dict[str, str]] = json.loads(result.stdout)
    return output[0]


def verify_binary_arch(target: str, binary_path: Path) -> None:
    """Verify that a binary matches the expected architecture for a target.

    :param target: Build target (e.g., 'linux-arm64', 'macos-x64').
    :param binary_path: Path to the binary file.
    :raises ValueError: If target is unknown.
    :raises AssertionError: If binary architecture does not match expected.
    """
    if target not in BINARY_ARCH_MAPPINGS:
        msg = (
            f"Unknown target: {target!r}. "
            f"Valid targets: {', '.join(sorted(BINARY_ARCH_MAPPINGS))}."
        )
        raise ValueError(msg)

    field, expected_substring = BINARY_ARCH_MAPPINGS[target]
    metadata = run_exiftool(binary_path)
    reported_arch = metadata.get(field, "")

    if expected_substring not in reported_arch:
        raise AssertionError(
            f"Binary architecture mismatch!\n"
            f"Expected: {expected_substring!r} in field {field!r}\n"
            f"Got: {reported_arch!r}"
        )

    logging.info(
        f"Binary architecture matches: {expected_substring!r} found in {field!r} "
        f"for {target} target."
    )
