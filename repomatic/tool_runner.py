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

"""Unified tool runner with managed config resolution.

Provides ``repomatic run <tool>`` — a single entry point that installs an
external tool at a pinned version, resolves its configuration through a strict
4-level precedence chain, translates ``[tool.X]`` sections from
``pyproject.toml`` into the tool's native format, and invokes the tool with
the resolved config.

.. important::
    Config resolution precedence (first match wins, no merging):

    1. **Native config file** — tool's own config file in the repo.
    2. **``[tool.X]`` in ``pyproject.toml``** — translated to native format.
    3. **Bundled default** — from ``repomatic/data/``.
    4. **Bare invocation** — no config at all.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
import sys
import tarfile
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from importlib.resources import as_file, files
from pathlib import Path, PurePosixPath
from urllib.request import Request, urlopen

import tomlkit
import yaml
from extra_platforms import (
    is_aarch64,
    is_github_ci,
    is_linux,  # Stubs added in extra_platforms 11.0.3.
    is_macos,
    is_windows,
    is_x86_64,
)

from .uv import uv_cmd, uvx_cmd

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence
    from typing import Any

    from .metadata import Metadata


class ArchiveFormat(Enum):
    """Archive format for binary tool downloads."""

    RAW = "raw"
    TAR_GZ = "tar.gz"
    TAR_XZ = "tar.xz"


class NativeFormat(Enum):
    """Target format for ``[tool.X]`` translation."""

    YAML = "yaml"
    TOML = "toml"
    JSON = "json"


@dataclass(frozen=True)
class BinarySpec:
    """Platform-specific binary download specification.

    Platform keys: ``linux-x64``, ``linux-arm64``, ``macos-x64``,
    ``macos-arm64``, ``windows-x64``, ``windows-arm64``.

    .. hint::
        Structural integrity checks (valid platform keys, checksum format,
        URL placeholders, strip_components consistency) are enforced in
        ``test_tool_spec_integrity``. If the registry becomes user-configurable
        in the future, move these checks to ``__post_init__``.
    """

    urls: dict[str, str]
    """Platform key to URL template mapping. URLs use ``{version}`` placeholders."""

    checksums: dict[str, str]
    """Platform key to SHA-256 hex digest mapping."""

    archive_format: ArchiveFormat
    """Archive format of the downloaded file."""

    archive_executable: str | None = None
    """Path of the executable inside the archive. ``None`` defaults to the
    tool name. For ``RAW`` format, used as the final filename.
    """

    strip_components: int = 0
    """Number of leading path components to strip when extracting."""


VALID_PLATFORM_KEYS = frozenset({
    "linux-arm64",
    "linux-x64",
    "macos-arm64",
    "macos-x64",
    "windows-arm64",
    "windows-x64",
})
"""Recognized platform keys for ``BinarySpec.urls`` and ``BinarySpec.checksums``."""


@dataclass(frozen=True)
class ToolSpec:
    """Specification for an external tool managed by repomatic.

    .. hint::
        Structural integrity checks (name format, version format, flag
        conventions, field consistency) are enforced in
        ``test_tool_spec_integrity``. If the registry becomes user-configurable
        in the future, move these checks to ``__post_init__``.
    """

    name: str
    """Tool identity: CLI name for ``repomatic run <name>``, default PyPI
    package name, and default executable name.
    """

    version: str
    """Pinned version (e.g., ``'1.38.0'``)."""

    package: str | None = None
    """PyPI package name. ``None`` defaults to ``name``. Only set when the
    package name differs from the tool name.
    """

    executable: str | None = None
    """Executable name if different from the tool name. ``None`` defaults to
    the registry key.
    """

    native_config_files: tuple[str, ...] = ()
    """Config filenames the tool auto-discovers, checked in order.

    Paths relative to repo root (e.g., ``'zizmor.yaml'``,
    ``'.github/actionlint.yaml'``). Empty for tools with no config file.
    """

    config_flag: str | None = None
    """CLI flag to pass a config file path (e.g., ``'--config'``,
    ``'--config-file'``). ``None`` if the tool only reads from fixed paths.
    """

    native_format: NativeFormat = NativeFormat.YAML
    """Target format for ``[tool.X]`` translation."""

    default_config: str | None = None
    """Filename in ``repomatic/data/`` for bundled defaults, stored in
    ``native_format``. ``None`` if no bundled default exists.
    """

    reads_pyproject: bool = False
    """Whether the tool natively reads ``[tool.X]`` from ``pyproject.toml``.

    When ``True`` and ``[tool.X]`` exists in ``pyproject.toml``, repomatic
    skips Level 2 translation (the tool reads it directly). Resolution still
    falls through to Level 3 (bundled default) and Level 4 (bare) when no
    config is found.
    """

    default_flags: tuple[str, ...] = ()
    """Flags always passed to the tool (e.g., ``('--strict',)``)."""

    ci_flags: tuple[str, ...] = ()
    """Flags added only when ``$GITHUB_ACTIONS`` is set (e.g., output format)."""

    with_packages: tuple[str, ...] = ()
    """Extra packages installed alongside the tool (e.g., mdformat plugins).

    Passed as ``--with <pkg>`` to uvx.
    """

    needs_venv: bool = False
    """If ``True``, use ``uv run`` (project venv) instead of ``uvx`` (isolated).

    Required when the tool imports project code (mypy, pytest).
    """

    computed_params: Callable[[Metadata], list[str]] | None = None
    """Callable that receives a ``Metadata`` instance and returns extra CLI args
    derived from project metadata (e.g., mypy's ``--python-version`` from
    ``requires-python``). ``None`` if no computed params.
    """

    post_process: Callable[[Sequence[str]], None] | None = None
    """Callback invoked on ``extra_args`` after the tool exits successfully.

    Intended for temporary workarounds that fix known upstream formatting bugs
    in-place. Remove the callback once upstream ships the fix.
    """

    binary: BinarySpec | None = None
    """Platform-specific binary download spec. When set, the tool is downloaded
    as a binary instead of installed via ``uvx`` or ``uv run``.
    """


# ---------------------------------------------------------------------------
# Post-process callbacks
# ---------------------------------------------------------------------------

_DIRECTIVE_YAML_OPTIONS_RE = re.compile(
    r"^((?:`{3,}|:{3,})\{[^}]+\}[^\n]*\n)"
    r"---\n"
    r"((?:[^\n]+\n)+?)"
    r"---\n",
    re.MULTILINE,
)
"""Match YAML-block directive options immediately after a MyST fence opening.

.. note::
    Workaround for `executablebooks/mdformat-myst#21
    <https://github.com/executablebooks/mdformat-myst/issues/21>`_ where
    ``mdformat-myst`` unconditionally converts ``:key: value`` directive
    options to YAML blocks (``---`` / ``key: value`` / ``---``). Remove when
    upstream merges `executablebooks/mdformat-myst#49
    <https://github.com/executablebooks/mdformat-myst/pull/49>`_.
"""


def _yaml_block_to_field_list(match: re.Match[str]) -> str:
    """Convert a single YAML-block directive option to field-list syntax."""
    directive_line = match.group(1)
    yaml_lines = match.group(2)
    # Prepend ":" to each non-empty line: ``key: value`` → ``:key: value``.
    field_lines = re.sub(r"^(?=\S)", ":", yaml_lines, flags=re.MULTILINE)
    return directive_line + field_lines


def _fix_myst_directive_options(extra_args: Sequence[str]) -> None:
    """Rewrite YAML-block directive options back to field-list syntax.

    Operates in-place on every file in *extra_args* that exists on disk.
    Files without matching patterns are left untouched.
    """
    for arg in extra_args:
        path = Path(arg)
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        fixed = _DIRECTIVE_YAML_OPTIONS_RE.sub(_yaml_block_to_field_list, content)
        if fixed != content:
            path.write_text(fixed, encoding="utf-8")
            logging.debug("Fixed MyST directive options in %s", path)


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, ToolSpec] = {
    # actionlint configuration reference:
    # - Config discovery: https://github.com/rhysd/actionlint/blob/main/docs/config.md
    #   Searches .github/actionlint.yaml, .github/actionlint.yml.
    # - CLI flags: https://github.com/rhysd/actionlint/blob/main/docs/usage.md
    #   -color for colored output; -ignore for suppressing specific errors.
    # - Source: https://github.com/rhysd/actionlint
    "actionlint": ToolSpec(
        name="actionlint",
        version="1.7.11",
        default_flags=("-color",),
        binary=BinarySpec(
            urls={
                "linux-x64": "https://github.com/rhysd/actionlint/releases/download/v{version}/actionlint_{version}_linux_amd64.tar.gz",
            },
            checksums={
                "linux-x64": "900919a84f2229bac68ca9cd4103ea297abc35e9689ebb842c6e34a3d1b01b0a",
            },
            archive_format=ArchiveFormat.TAR_GZ,
        ),
    ),
    # autopep8 configuration reference:
    # - CLI flags: https://pypi.org/project/autopep8/
    #   No config file support; all options via CLI flags.
    # - Source: https://github.com/hhatto/autopep8
    "autopep8": ToolSpec(
        name="autopep8",
        version="2.3.2",
        default_flags=(
            "--recursive",
            "--in-place",
            "--max-line-length",
            "88",
            "--select",
            "E501",
        ),
    ),
    # biome configuration reference:
    # - Config discovery: https://biomejs.dev/reference/configuration/
    #   Searches biome.json, biome.jsonc in CWD and parents.
    # - CLI flags: https://biomejs.dev/reference/cli/
    #   format --write for formatting; --no-errors-on-unmatched to skip unknown files.
    # - Source: https://github.com/biomejs/biome
    "biome": ToolSpec(
        name="biome",
        version="2.4.5",
        native_config_files=("biome.json", "biome.jsonc"),
        config_flag="--config-path",
        native_format=NativeFormat.JSON,
        binary=BinarySpec(
            urls={
                "linux-x64": "https://github.com/biomejs/biome/releases/download/%40biomejs%2Fbiome%40{version}/biome-linux-x64",
            },
            checksums={
                "linux-x64": "a31815f19b0b90fa043eb23fbf769ed931fbcde6d98bb89894ea8be1387d8394",
            },
            archive_format=ArchiveFormat.RAW,
        ),
    ),
    # bump-my-version configuration reference:
    # - Config discovery: https://callowayproject.github.io/bump-my-version/reference/configuration/
    #   Reads [tool.bumpversion] from pyproject.toml, .bumpversion.toml.
    # - CLI flags: https://callowayproject.github.io/bump-my-version/reference/cli/
    #   bump and show are subcommands; --verbose for detailed output.
    # - Source: https://github.com/callowayproject/bump-my-version
    "bump-my-version": ToolSpec(
        name="bump-my-version",
        version="1.2.7",
        reads_pyproject=True,
    ),
    # gitleaks configuration reference:
    # - Config discovery: https://github.com/gitleaks/gitleaks#configuration
    #   Searches .gitleaks.toml in CWD.
    # - CLI flags: https://github.com/gitleaks/gitleaks#usage
    #   detect subcommand; -c / --config for explicit config; --report-format
    #   for output format (json, csv, junit, sarif).
    # - Source: https://github.com/gitleaks/gitleaks
    "gitleaks": ToolSpec(
        name="gitleaks",
        version="8.30.1",
        native_config_files=(".gitleaks.toml", ".github/gitleaks.toml"),
        config_flag="--config",
        native_format=NativeFormat.TOML,
        binary=BinarySpec(
            urls={
                "linux-x64": "https://github.com/gitleaks/gitleaks/releases/download/v{version}/gitleaks_{version}_linux_x64.tar.gz",
            },
            checksums={
                "linux-x64": "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb",
            },
            archive_format=ArchiveFormat.TAR_GZ,
        ),
    ),
    # labelmaker configuration reference:
    # - CLI flags: https://github.com/jwodder/labelmaker
    #   apply subcommand with label file and repository arguments.
    # - Source: https://github.com/jwodder/labelmaker
    "labelmaker": ToolSpec(
        name="labelmaker",
        version="0.6.4",
        binary=BinarySpec(
            urls={
                "linux-x64": "https://github.com/jwodder/labelmaker/releases/download/v{version}/labelmaker-x86_64-unknown-linux-gnu.tar.xz",
            },
            checksums={
                "linux-x64": "d76f8e64f9671884dac1758fe54a28a6680c5d9bf0ffd593a2c68ba558cc49a2",
            },
            archive_format=ArchiveFormat.TAR_XZ,
            strip_components=1,
        ),
    ),
    # lychee configuration reference:
    # - Config discovery: https://lychee.cli.rs/configuration/
    #   Searches lychee.toml, .lycheerc in CWD.
    # - CLI flags: https://lychee.cli.rs/usage/cli/
    #   --format for output format; --hidden to check hidden files.
    # - Source: https://github.com/lycheeverse/lychee
    "lychee": ToolSpec(
        name="lychee",
        version="0.23.0",
        native_config_files=("lychee.toml",),
        config_flag="--config",
        native_format=NativeFormat.TOML,
        binary=BinarySpec(
            urls={
                "linux-x64": "https://github.com/lycheeverse/lychee/releases/download/lychee-v{version}/lychee-x86_64-unknown-linux-gnu.tar.gz",
            },
            checksums={
                "linux-x64": "1fcb6ccf10d04c22b8c5873c5b9cb7be32ee7423e12169d6f1a79a6f1962ef81",
            },
            archive_format=ArchiveFormat.TAR_GZ,
        ),
    ),
    # mdformat configuration reference:
    # - Config discovery: https://mdformat.readthedocs.io/en/stable/users/configuration_file.html
    #   Searches .mdformat.toml in CWD and parents.
    # - CLI flags: https://mdformat.readthedocs.io/en/stable/users/cli.html
    #   --strict-front-matter for YAML front matter validation (plugin flag).
    # - Source: https://github.com/hukkin/mdformat
    "mdformat": ToolSpec(
        name="mdformat",
        version="1.0.0",
        native_config_files=(".mdformat.toml",),
        native_format=NativeFormat.TOML,
        default_config="mdformat.toml",
        reads_pyproject=True,
        default_flags=("--strict-front-matter",),
        with_packages=(
            "mdformat_admon==2.1.1",
            "mdformat-config==0.2.1",
            "mdformat_deflist==0.1.4",
            "mdformat_footnote==0.1.3",
            "mdformat-front-matters==2.0.0",
            "mdformat-gfm==1.0.0",
            "mdformat_gfm_alerts==2.0.0",
            "mdformat_myst==0.3.0",
            "mdformat-pelican @ git+https://github.com/kdeldycke/mdformat-pelican@fix-mdformat-1.0.0",
            "mdformat_pyproject==0.1.1",
            "mdformat-recover-urls==0.0.2",
            "mdformat-ruff==0.1.3",
            "mdformat-shfmt==0.2.0",
            "mdformat_simple_breaks==0.1.0",
            "mdformat-toc==0.5.0",
            "mdformat-web==0.2.0",
            "ruff==0.15.5",
        ),
        post_process=_fix_myst_directive_options,
    ),
    # mypy configuration reference:
    # - Config discovery: https://mypy.readthedocs.io/en/stable/config_file.html
    #   Reads [tool.mypy] from pyproject.toml natively.
    # - CLI flags: https://mypy.readthedocs.io/en/stable/command_line.html
    #   --python-version for target version; --color-output for colored output.
    # - Source: https://github.com/python/mypy
    "mypy": ToolSpec(
        name="mypy",
        version="1.19.1",
        reads_pyproject=True,
        needs_venv=True,
        default_flags=("--color-output",),
        computed_params=lambda m: m.mypy_params or [],
    ),
    # pyproject-fmt configuration reference:
    # - Config discovery: https://pyproject-fmt.readthedocs.io/en/latest/
    #   Reads [tool.pyproject-fmt] from pyproject.toml natively.
    # - CLI flags: https://pyproject-fmt.readthedocs.io/en/latest/
    #   --expand-tables for table expansion. Returns exit code 1 when file is
    #   reformatted.
    # - Source: https://github.com/tox-dev/pyproject-fmt
    "pyproject-fmt": ToolSpec(
        name="pyproject-fmt",
        version="2.16.2",
        reads_pyproject=True,
        default_flags=(
            "--expand-tables",
            "project.entry-points,project.optional-dependencies,project.urls,project.scripts",
        ),
    ),
    # ruff configuration reference:
    # - Config discovery: https://docs.astral.sh/ruff/configuration/
    #   Reads [tool.ruff] from pyproject.toml, ruff.toml, .ruff.toml.
    # - CLI flags: https://docs.astral.sh/ruff/configuration/#command-line-interface
    #   check and format are subcommands; --output-format for CI annotations.
    # - Source: https://github.com/astral-sh/ruff
    "ruff": ToolSpec(
        name="ruff",
        version="0.15.5",
        native_config_files=("ruff.toml", ".ruff.toml"),
        config_flag="--config",
        native_format=NativeFormat.TOML,
        default_config="ruff.toml",
        reads_pyproject=True,
    ),
    # typos configuration reference:
    # - Config discovery: https://github.com/crate-ci/typos/blob/master/docs/reference.md
    #   Reads [tool.typos] from pyproject.toml, typos.toml, .typos.toml, _typos.toml.
    # - CLI flags: https://github.com/crate-ci/typos/blob/master/docs/reference.md
    #   --write-changes for in-place fixes.
    # - Source: https://github.com/crate-ci/typos
    "typos": ToolSpec(
        name="typos",
        version="1.44.0",
        reads_pyproject=True,
        default_flags=("--write-changes",),
        binary=BinarySpec(
            urls={
                "linux-x64": "https://github.com/crate-ci/typos/releases/download/v{version}/typos-v{version}-x86_64-unknown-linux-musl.tar.gz",
            },
            checksums={
                "linux-x64": "1b788b7d764e2f20fe089487428a3944ed218d1fb6fcd8eac4230b5893a38779",
            },
            archive_format=ArchiveFormat.TAR_GZ,
        ),
    ),
    # yamllint configuration reference:
    # - Config discovery: https://yamllint.readthedocs.io/en/stable/configuration.html
    #   Searches .yamllint, .yamllint.yaml, .yamllint.yml in CWD and parents.
    # - CLI flags: https://yamllint.readthedocs.io/en/stable/quickstart.html
    #   -c / --config-file for explicit config; -f / --format for output format.
    # - Source: https://github.com/adrienverge/yamllint
    "yamllint": ToolSpec(
        name="yamllint",
        version="1.38.0",
        native_config_files=(
            ".yamllint.yaml",
            ".yamllint.yml",
            ".yamllint",
        ),
        config_flag="--config-file",
        default_config="yamllint.yaml",
        default_flags=("--strict",),
        ci_flags=("--format", "github"),
    ),
    # zizmor configuration reference:
    # - Config discovery: https://docs.zizmor.sh/configuration/
    #   Searches zizmor.yml / zizmor.yaml in input dir, .github/, then parents
    #   up to first .git directory.
    # - CLI flags: https://docs.zizmor.sh/usage/
    #   --config for explicit config; --format for output format; --offline to
    #   disable network requests.
    # - Source: https://github.com/zizmorcore/zizmor
    "zizmor": ToolSpec(
        name="zizmor",
        version="1.23.0",
        native_config_files=("zizmor.yaml",),
        config_flag="--config",
        default_config="zizmor.yaml",
        default_flags=("--offline",),
        ci_flags=("--format", "github"),
    ),
}


# ---------------------------------------------------------------------------
# Bundled data file access
# ---------------------------------------------------------------------------


@contextmanager
def get_data_file_path(filename: str) -> Iterator[Path]:
    """Yield the filesystem path of a bundled data file.

    Unlike ``init_project.get_data_content()`` which returns string content,
    this yields a ``Path`` suitable for passing to external tools via
    ``--config <path>``. The path is valid only within the context manager.
    """
    data_files = files("repomatic.data")
    with as_file(data_files.joinpath(filename)) as path:
        if not path.exists():
            msg = f"Bundled data file not found: {filename}"
            raise FileNotFoundError(msg)
        yield path


# ---------------------------------------------------------------------------
# Config resolution
# ---------------------------------------------------------------------------


def load_pyproject_tool_section(tool_name: str) -> dict[str, Any]:
    """Load ``[tool.<tool_name>]`` from ``pyproject.toml`` in the current directory.

    :return: The tool's config dict, or empty dict if not found.
    """
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        return {}
    pyproject_data = tomllib.loads(pyproject_path.read_text(encoding="UTF-8"))
    tool_section: dict[str, Any] = pyproject_data.get("tool", {}).get(tool_name, {})
    return tool_section


def resolve_config(
    spec: ToolSpec,
    tool_config: dict[str, Any] | None = None,
) -> tuple[list[str], Path | None]:
    """Resolve config for a tool using the 4-level precedence chain.

    :param spec: Tool specification.
    :param tool_config: Pre-loaded ``[tool.X]`` config dict. If ``None``,
        reads from ``pyproject.toml`` in the current directory.
    :return: Tuple of (extra CLI args for config, temp file path to clean up).
        The temp file path is ``None`` when no temp file was created.
    """
    # Level 1: Native config file exists in the repo.
    for config_file in spec.native_config_files:
        if Path(config_file).exists():
            logging.debug("Using native config: %s", config_file)
            return [], None

    # Level 2: [tool.X] in pyproject.toml.
    if tool_config is None:
        tool_config = load_pyproject_tool_section(spec.name)

    if tool_config:
        # Tool reads pyproject.toml natively — no translation needed.
        if spec.reads_pyproject:
            logging.debug(
                "[tool.%s] in pyproject.toml; tool reads it natively.", spec.name
            )
            return [], None

        if not spec.config_flag:
            msg = (
                f"{spec.name} has [tool.{spec.name}] config but no config_flag "
                f"to pass a translated config file. Configure the tool via its "
                f"native config file ({', '.join(spec.native_config_files)}) instead."
            )
            raise NotImplementedError(msg)

        if spec.native_format == NativeFormat.YAML:
            content = yaml.safe_dump(
                tool_config, default_flow_style=False, sort_keys=False
            )
        elif spec.native_format == NativeFormat.TOML:
            content = tomlkit.dumps(tool_config)
        elif spec.native_format == NativeFormat.JSON:
            content = json.dumps(tool_config, indent=2) + "\n"

        logging.debug(
            "Translated [tool.%s] to %s:\n%s",
            spec.name,
            spec.native_format,
            content,
        )

        # Write to temp file. Caller is responsible for cleanup via the
        # returned path.
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=f".{spec.native_format.value}",
            prefix=f"repomatic-{spec.name}-",
            delete=False,
        ) as tmp:
            tmp.write(content)
        tmp_path = Path(tmp.name)
        logging.debug("Wrote temp config: %s", tmp_path)

        if spec.config_flag:
            return [spec.config_flag, str(tmp_path)], tmp_path
        return [], tmp_path

    # Level 3: Bundled default from repomatic/data/.
    if spec.default_config:
        if spec.config_flag:
            logging.debug("Using bundled default: %s", spec.default_config)
            # Return a sentinel; the actual path is resolved at invocation time
            # inside the get_data_file_path() context manager.
            return ["__bundled__"], None

        if spec.native_config_files:
            # Tool discovers config by searching CWD (no --config flag).
            # Write the bundled default to the first native config path so the
            # tool picks it up, then clean it up after invocation.
            target = Path(spec.native_config_files[0])
            with get_data_file_path(spec.default_config) as bundled_path:
                content = bundled_path.read_text(encoding="UTF-8")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="UTF-8")
            logging.debug(
                "Wrote bundled default to CWD: %s",
                target,
            )
            return [], target

    # Level 4: Bare invocation.
    logging.debug("No config found for %s, bare invocation.", spec.name)
    return [], None


# ---------------------------------------------------------------------------
# Binary download infrastructure
# ---------------------------------------------------------------------------


def _get_platform_key() -> str:
    """Return platform key for the current OS and architecture.

    :return: One of ``linux-x64``, ``linux-arm64``, ``macos-x64``,
        ``macos-arm64``, ``windows-x64``, ``windows-arm64``.
    :raises RuntimeError: If the current platform is not supported.
    """
    if is_linux():
        os_part = "linux"
    elif is_macos():
        os_part = "macos"
    elif is_windows():
        os_part = "windows"
    else:
        msg = f"Unsupported OS for binary downloads: {sys.platform}"
        raise RuntimeError(msg)

    if is_x86_64():
        arch_part = "x64"
    elif is_aarch64():
        arch_part = "arm64"
    else:
        msg = "Binary downloads are only supported on x64 and arm64 architectures."
        raise RuntimeError(msg)

    return f"{os_part}-{arch_part}"


def _download_and_verify(url: str, expected_sha256: str, dest_path: Path) -> None:
    """Download a file and verify its SHA-256 checksum.

    Uses streaming download with chunked hash computation to handle large
    binaries without loading the entire file into memory.

    :param url: URL to download.
    :param expected_sha256: Expected lowercase hex SHA-256 digest.
    :param dest_path: Where to write the downloaded file.
    :raises ValueError: If the checksum does not match.
    """
    request = Request(url)
    sha256 = hashlib.sha256()
    with urlopen(request) as response, dest_path.open("wb") as f:
        while chunk := response.read(65536):
            f.write(chunk)
            sha256.update(chunk)
    actual = sha256.hexdigest()
    if actual != expected_sha256:
        dest_path.unlink(missing_ok=True)
        msg = f"SHA-256 mismatch for {url}: expected {expected_sha256}, got {actual}"
        raise ValueError(msg)
    logging.debug("SHA-256 verified for %s: %s", url, actual)


def _extract_binary(
    archive_path: Path,
    spec: BinarySpec,
    dest_dir: Path,
    tool_name: str,
) -> Path:
    """Extract the tool executable from a downloaded archive.

    :param archive_path: Path to the downloaded archive file.
    :param spec: Binary specification with format and executable info.
    :param dest_dir: Directory to extract into.
    :param tool_name: Tool name, used as default for ``archive_executable``.
    :return: Path to the extracted executable.
    :raises FileNotFoundError: If the executable is not found in the archive.
    """
    executable = spec.archive_executable or tool_name

    if spec.archive_format == ArchiveFormat.RAW:
        dest = dest_dir / executable
        archive_path.rename(dest)
        dest.chmod(0o755)
        return dest

    # TAR_GZ or TAR_XZ.
    target = executable

    with tarfile.open(
        str(archive_path),
        "r:gz" if spec.archive_format == ArchiveFormat.TAR_GZ else "r:xz",
    ) as tar:
        for member in tar.getmembers():
            # Tar member names always use forward slashes. Use PurePosixPath
            # to avoid backslash issues on Windows.
            parts = PurePosixPath(member.name).parts
            if len(parts) <= spec.strip_components:
                continue
            stripped = str(PurePosixPath(*parts[spec.strip_components :]))
            if stripped == target:
                # Security: validate member path before extraction.
                if ".." in parts or member.name.startswith("/"):
                    msg = f"Unsafe archive member path: {member.name}"
                    raise ValueError(msg)
                if sys.version_info >= (3, 12):
                    tar.extract(member, dest_dir, filter="data")
                else:
                    tar.extract(member, dest_dir)
                extracted = dest_dir / member.name
                final = dest_dir / PurePosixPath(target).name
                if extracted != final:
                    extracted.rename(final)
                final.chmod(0o755)
                return final

    msg = f"Executable {target!r} not found in archive"
    raise FileNotFoundError(msg)


def _install_binary(spec: ToolSpec, tmp_dir: Path) -> Path:
    """Download, verify, and extract a binary tool.

    :param spec: Tool specification with ``binary`` set.
    :param tmp_dir: Temporary directory for download and extraction.
    :return: Path to the ready-to-run executable.
    :raises RuntimeError: If no binary is available for the current platform.
    """
    binary = spec.binary
    assert binary is not None

    platform_key = _get_platform_key()
    if platform_key not in binary.urls:
        msg = (
            f"No binary available for platform {platform_key!r}. "
            f"Available: {', '.join(sorted(binary.urls))}"
        )
        raise RuntimeError(msg)

    url = binary.urls[platform_key].format(version=spec.version)
    checksum = binary.checksums[platform_key]

    # Derive archive filename from URL.
    archive_name = url.rsplit("/", 1)[-1]
    archive_path = tmp_dir / archive_name

    logging.info("Downloading %s %s for %s...", spec.name, spec.version, platform_key)
    _download_and_verify(url, checksum, archive_path)

    return _extract_binary(archive_path, binary, tmp_dir, spec.name)


@contextmanager
def binary_tool_context(name: str) -> Iterator[Path]:
    """Download a binary tool and yield its executable path.

    For tools invoked indirectly by repomatic commands (e.g., labelmaker
    called by ``sync-labels``) rather than via ``run_tool()``. Downloads
    once; the binary stays valid for the context's duration.

    :param name: Tool name (must be in ``TOOL_REGISTRY`` with ``binary`` set).
    :yields: Path to the ready-to-run executable.
    """
    spec = TOOL_REGISTRY[name]
    assert spec.binary is not None, f"{name} has no binary spec"
    with tempfile.TemporaryDirectory(prefix=f"repomatic-{name}-bin-") as bin_dir:
        yield _install_binary(spec, Path(bin_dir))


# ---------------------------------------------------------------------------
# Tool invocation
# ---------------------------------------------------------------------------


def _build_install_args(spec: ToolSpec) -> list[str]:
    """Build the command prefix for installing and running a tool."""
    package_pin = f"{spec.package or spec.name}=={spec.version}"
    executable = spec.executable or spec.name

    if spec.needs_venv:
        cmd = uv_cmd("run", frozen=True)
        cmd.extend(["--with", package_pin, "--", executable])
    else:
        cmd = uvx_cmd()
        for pkg in spec.with_packages:
            cmd.extend(["--with", pkg])
        cmd.extend(["--from", package_pin, executable])

    return cmd


def run_tool(
    name: str,
    extra_args: Sequence[str] = (),
) -> int:
    """Run an external tool with managed config resolution.

    :param name: Tool name (must be in ``TOOL_REGISTRY``).
    :param extra_args: Extra arguments passed through to the tool.
    :return: The tool's exit code.
    """
    if name not in TOOL_REGISTRY:
        msg = (
            f"Unknown tool: {name!r}. "
            f"Available tools: {', '.join(sorted(TOOL_REGISTRY))}"
        )
        raise ValueError(msg)

    spec = TOOL_REGISTRY[name]
    config_args, tmp_path = resolve_config(spec)

    bin_dir = None
    try:
        # Build command prefix: binary download or uvx/uv-run.
        if spec.binary is not None:
            bin_dir = tempfile.TemporaryDirectory(
                prefix=f"repomatic-{name}-bin-",
            )
            bin_path = _install_binary(spec, Path(bin_dir.name))
            cmd = [str(bin_path)]
        else:
            cmd = _build_install_args(spec)

        # Default flags (always applied).
        if spec.default_flags:
            cmd.extend(spec.default_flags)

        # CI output format flags.
        if spec.ci_flags and is_github_ci():
            cmd.extend(spec.ci_flags)

        # Computed parameters derived from project metadata.
        if spec.computed_params:
            from .metadata import Metadata

            cmd.extend(spec.computed_params(Metadata()))

        # Config args from resolution.
        if config_args == ["__bundled__"]:
            # Level 3: use bundled default via context manager.
            # Both are guaranteed non-None when __bundled__ is returned.
            assert spec.default_config is not None
            assert spec.config_flag is not None
            with get_data_file_path(spec.default_config) as bundled_path:
                cmd.extend([spec.config_flag, str(bundled_path)])
                cmd.extend(extra_args)
                logging.debug("Running: %s", " ".join(cmd))
                result = subprocess.run(cmd, check=False)
        else:
            cmd.extend(config_args)
            cmd.extend(extra_args)
            logging.debug("Running: %s", " ".join(cmd))
            result = subprocess.run(cmd, check=False)

        if result.returncode == 0 and spec.post_process:
            spec.post_process(extra_args)

        return result.returncode

    finally:
        if bin_dir is not None:
            bin_dir.cleanup()
        if tmp_path is not None:
            logging.debug("Cleaning up temp config: %s", tmp_path)
            tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


def resolve_config_source(spec: ToolSpec) -> str:
    """Return a human-readable description of the active config source.

    Used by ``repomatic run --list`` to show which precedence level is active
    for each tool in the current repo.

    :param name: Tool name (registry key).
    :param spec: Tool specification.
    """
    # Level 1: Native config file.
    for config_file in spec.native_config_files:
        if Path(config_file).exists():
            return config_file

    # Level 2: [tool.X] in pyproject.toml.
    tool_config = load_pyproject_tool_section(spec.name)
    if tool_config:
        return f"[tool.{spec.name}] in pyproject.toml"

    # Level 3: Bundled default.
    if spec.default_config:
        return "bundled default"

    # Level 4: Bare invocation.
    return "(bare)"


def find_unmodified_configs() -> list[tuple[str, str]]:
    """Find native config files identical to their bundled defaults.

    Iterates over every tool in :data:`TOOL_REGISTRY` that has a
    ``default_config``.  For each, checks whether any of its
    ``native_config_files`` exists on disk and is content-identical
    to the bundled default after trailing-whitespace normalization.

    The normalization (``rstrip() + "\\n"``) matches the convention
    used by ``_init_config_files`` when writing files during ``init``.

    :return: List of ``(tool_name, relative_path)`` tuples for each
        unmodified file found.
    """
    unmodified: list[tuple[str, str]] = []

    for name, spec in sorted(TOOL_REGISTRY.items()):
        if not spec.default_config:
            continue

        with get_data_file_path(spec.default_config) as bundled_path:
            bundled = bundled_path.read_text(encoding="UTF-8").rstrip() + "\n"

        for config_file in spec.native_config_files:
            path = Path(config_file)
            if not path.exists():
                continue
            native = path.read_text(encoding="UTF-8").rstrip() + "\n"
            if native == bundled:
                unmodified.append((name, config_file))

    return unmodified
