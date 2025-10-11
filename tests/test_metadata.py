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

from __future__ import annotations

import json
import re
from string import ascii_lowercase, digits
from typing import Any

import pytest
from extra_platforms import ALL_IDS, is_windows

from gha_utils.metadata import NUITKA_BUILD_TARGETS, Dialects, Metadata


@pytest.mark.parametrize("target_id, target_data", NUITKA_BUILD_TARGETS.items())
def test_nuitka_targets(target_id: str, target_data: dict[str, str]) -> None:
    assert isinstance(target_id, str)
    assert isinstance(target_data, dict)

    assert set(target_data) == {
        "os",
        "platform_id",
        "arch",
        "extension",
    }, f"Unexpected keys in target data for {target_id}"

    assert isinstance(target_data["os"], str)
    assert isinstance(target_data["platform_id"], str)
    assert isinstance(target_data["arch"], str)
    assert isinstance(target_data["extension"], str)

    assert set(target_data["os"]).issubset(ascii_lowercase + digits + "-.")
    assert target_data["platform_id"] in ALL_IDS
    assert target_data["arch"] in {"arm64", "x64"}
    assert set(target_data["extension"]).issubset(ascii_lowercase)

    assert target_id == target_data["platform_id"] + "-" + target_data["arch"]
    assert set(target_id).issubset(ascii_lowercase + digits + "-")


def regex(pattern: str) -> re.Pattern:
    """Compile a regex pattern with DOTALL flag."""
    return re.compile(pattern, re.DOTALL)


def iter_checks(metadata: Any, expected: Any, context: Any) -> None:
    """Recursively iterate over expected content and check it matches in metadata."""

    if isinstance(expected, re.Pattern):
        assert isinstance(metadata, str)
        assert re.fullmatch(expected, metadata) is not None, (
            f"{metadata!r} does not match {expected.pattern!r} in {context!r}"
        )

    elif isinstance(expected, dict):
        assert isinstance(metadata, dict)
        assert set(metadata) == set(expected)
        for key, value in expected.items():
            # By convention, keys ending with "_files" are path strings so they need to
            # be adjusted for Windows.
            if key.endswith("_files") and is_windows():
                # Path are stored as a list in JSON format.
                if isinstance(value, list):
                    value = [v.replace("/", "\\") for v in value]
                # Path are space-separated and serialized as a string in GitHub format.
                else:
                    value = value.replace("/", "\\")

            iter_checks(metadata[key], value, metadata)

    elif isinstance(expected, list):
        assert isinstance(metadata, list)
        assert len(metadata) == len(expected)
        for item in expected:
            iter_checks(metadata[expected.index(item)], item, metadata)

    else:
        assert metadata == expected, (
            f"{metadata!r} does not match {expected!r} in {context!r}"
        )
        assert type(metadata) is type(expected)


expected = {
    "is_bot": False,
    "new_commits": None,
    "release_commits": None,
    "mailmap_exists": True,
    "gitignore_exists": True,
    "python_files": [
        "gha_utils/__init__.py",
        "gha_utils/__main__.py",
        "gha_utils/changelog.py",
        "gha_utils/cli.py",
        "gha_utils/mailmap.py",
        "gha_utils/matrix.py",
        "gha_utils/metadata.py",
        "gha_utils/test_plan.py",
        "tests/__init__.py",
        "tests/test_changelog.py",
        "tests/test_mailmap.py",
        "tests/test_matrix.py",
        "tests/test_metadata.py",
    ],
    "json_files": [],
    "yaml_files": [
        ".github/dependabot.yaml",
        ".github/funding.yml",
        ".github/labeller-content-based.yaml",
        ".github/labeller-file-based.yaml",
        ".github/labels-awesome.yaml",
        ".github/labels.yaml",
        ".github/workflows/autofix.yaml",
        ".github/workflows/autolock.yaml",
        ".github/workflows/changelog.yaml",
        ".github/workflows/debug.yaml",
        ".github/workflows/docs.yaml",
        ".github/workflows/label-sponsors.yaml",
        ".github/workflows/labeller-content-based.yaml",
        ".github/workflows/labeller-file-based.yaml",
        ".github/workflows/labels.yaml",
        ".github/workflows/lint.yaml",
        ".github/workflows/release.yaml",
        ".github/workflows/tests.yaml",
        "tests/cli-test-plan.yaml",
    ],
    "workflow_files": [
        ".github/workflows/autofix.yaml",
        ".github/workflows/autolock.yaml",
        ".github/workflows/changelog.yaml",
        ".github/workflows/debug.yaml",
        ".github/workflows/docs.yaml",
        ".github/workflows/label-sponsors.yaml",
        ".github/workflows/labeller-content-based.yaml",
        ".github/workflows/labeller-file-based.yaml",
        ".github/workflows/labels.yaml",
        ".github/workflows/lint.yaml",
        ".github/workflows/release.yaml",
        ".github/workflows/tests.yaml",
    ],
    "doc_files": [
        ".github/code-of-conduct.md",
        "changelog.md",
        "readme.md",
    ],
    "markdown_files": [
        ".github/code-of-conduct.md",
        "changelog.md",
        "readme.md",
    ],
    "image_files": [
        "docs/assets/repo-workflow-permissions.png",
    ],
    "zsh_files": [],
    "is_python_project": True,
    "package_name": "gha-utils",
    "blacken_docs_params": (
        "--target-version py311 "
        "--target-version py312 "
        "--target-version py313 "
        "--target-version py314"
    ),
    "mypy_params": "--python-version 3.11",
    "current_version": regex(r"[0-9\.]+"),
    "released_version": None,
    "is_sphinx": False,
    "active_autodoc": False,
    "release_notes": regex(
        r"### Changes\n\n"
        r"> \[\!IMPORTANT\]\n"
        r"> This version is not released yet and is under active development\.\n\n"
        r".+"
    ),
    "new_commits_matrix": None,
    "release_commits_matrix": None,
    "build_targets": [
        {
            "target": "linux-arm64",
            "os": "ubuntu-24.04-arm",
            "platform_id": "linux",
            "arch": "arm64",
            "extension": "bin",
        },
        {
            "target": "linux-x64",
            "os": "ubuntu-24.04",
            "platform_id": "linux",
            "arch": "x64",
            "extension": "bin",
        },
        {
            "target": "macos-arm64",
            "os": "macos-26",
            "platform_id": "macos",
            "arch": "arm64",
            "extension": "bin",
        },
        {
            "target": "macos-x64",
            "os": "macos-15-intel",
            "platform_id": "macos",
            "arch": "x64",
            "extension": "bin",
        },
        {
            "target": "windows-arm64",
            "os": "windows-11-arm",
            "platform_id": "windows",
            "arch": "arm64",
            "extension": "exe",
        },
        {
            "target": "windows-x64",
            "os": "windows-2025",
            "platform_id": "windows",
            "arch": "x64",
            "extension": "exe",
        },
    ],
    "nuitka_matrix": {
        "os": [
            "ubuntu-24.04-arm",
            "ubuntu-24.04",
            "macos-26",
            "macos-15-intel",
            "windows-11-arm",
            "windows-2025",
        ],
        "entry_point": ["gha-utils"],
        "commit": [regex(r"[a-z0-9]+")],
        "include": [
            {
                "target": "linux-arm64",
                "os": "ubuntu-24.04-arm",
                "platform_id": "linux",
                "arch": "arm64",
                "extension": "bin",
            },
            {
                "target": "linux-x64",
                "os": "ubuntu-24.04",
                "platform_id": "linux",
                "arch": "x64",
                "extension": "bin",
            },
            {
                "target": "macos-arm64",
                "os": "macos-26",
                "platform_id": "macos",
                "arch": "arm64",
                "extension": "bin",
            },
            {
                "target": "macos-x64",
                "os": "macos-15-intel",
                "platform_id": "macos",
                "arch": "x64",
                "extension": "bin",
            },
            {
                "target": "windows-arm64",
                "os": "windows-11-arm",
                "platform_id": "windows",
                "arch": "arm64",
                "extension": "exe",
            },
            {
                "target": "windows-x64",
                "os": "windows-2025",
                "platform_id": "windows",
                "arch": "x64",
                "extension": "exe",
            },
            {
                "entry_point": "gha-utils",
                "cli_id": "gha-utils",
                "module_id": "gha_utils.__main__",
                "callable_id": "main",
                "module_path": regex(r"gha_utils(/|\\)__main__\.py"),
            },
            {
                "commit": regex(r"[a-z0-9]+"),
                "short_sha": regex(r"[a-z0-9]+"),
                "current_version": regex(r"[0-9\.]+"),
            },
            {
                "os": "ubuntu-24.04-arm",
                "entry_point": "gha-utils",
                "commit": regex(r"[a-z0-9]+"),
                "bin_name": regex(r"gha-utils-linux-arm64-[a-z0-9]+\.bin"),
            },
            {
                "os": "ubuntu-24.04",
                "entry_point": "gha-utils",
                "commit": regex(r"[a-z0-9]+"),
                "bin_name": regex(r"gha-utils-linux-x64-[a-z0-9]+\.bin"),
            },
            {
                "os": "macos-26",
                "entry_point": "gha-utils",
                "commit": regex(r"[a-z0-9]+"),
                "bin_name": regex(r"gha-utils-macos-arm64-[a-z0-9]+\.bin"),
            },
            {
                "os": "macos-15-intel",
                "entry_point": "gha-utils",
                "commit": regex(r"[a-z0-9]+"),
                "bin_name": regex(r"gha-utils-macos-x64-[a-z0-9]+\.bin"),
            },
            {
                "os": "windows-11-arm",
                "entry_point": "gha-utils",
                "commit": regex(r"[a-z0-9]+"),
                "bin_name": regex(r"gha-utils-windows-arm64-[a-z0-9]+\.exe"),
            },
            {
                "os": "windows-2025",
                "entry_point": "gha-utils",
                "commit": regex(r"[a-z0-9]+"),
                "bin_name": regex(r"gha-utils-windows-x64-[a-z0-9]+\.exe"),
            },
            {"state": "stable"},
        ],
    },
}


def test_metadata_json_format():
    metadata = Metadata().dump(Dialects.json)
    assert isinstance(metadata, str)

    iter_checks(json.loads(metadata), expected, metadata)


def test_metadata_github_format():
    raw_metadata = Metadata().dump()
    assert isinstance(raw_metadata, str)

    # Prepare metadata for checks
    metadata = {}
    # Accumulation states.
    acc_key = None
    acc_delimiter = None
    acc_lines = []
    for line in raw_metadata.splitlines():
        # We are at the end of the accumulation for a key.
        if line == acc_delimiter:
            assert acc_delimiter
            assert acc_key
            assert acc_lines
            metadata[acc_key] = "\n".join(acc_lines)
            # Reset accumulation states.
            acc_key = None
            acc_delimiter = None
            acc_lines = []
            continue

        # We are accumulating lines for a key.
        if acc_key:
            acc_lines.append(line)
            continue

        # We should not have any accumulation state at this point.
        assert acc_key is None
        assert acc_delimiter is None
        assert acc_lines == []

        # We are starting a new accumulation for a key.
        if "<<" in line:
            # Check the delimiter syntax.
            assert line.count("<<") == 1
            acc_key, acc_delimiter = line.split("<<", 1)
            assert re.fullmatch(r"GHA_DELIMITER_[0-9]+", acc_delimiter)
            continue

        # We are at a simple key-value pair.
        if "=" in line:
            key, value = line.split("=", 1)
            # Convert list-like and dict-like JSON string into Python objects.
            if value.startswith(("[", "{")):
                value = json.loads(value)
            metadata[key] = value
            continue

        raise ValueError(
            f"Unexpected line format in metadata: {line!r}. "
            "Expecting a key-value pair or a delimited block."
        )

    # Adapt expected values to match GitHub Actions format.
    github_format_expected = {}
    for key, value in expected.items():
        new_value = value
        if value is None:
            new_value = ""
        elif isinstance(value, bool):
            new_value = str(value).lower()
        elif isinstance(value, list) and all(isinstance(i, str) for i in value):
            new_value = " ".join(f'"{i}"' for i in value)
        github_format_expected[key] = new_value

    iter_checks(metadata, github_format_expected, raw_metadata)
