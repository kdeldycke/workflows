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
from packaging.version import Version

from gha_utils.metadata import (
    NUITKA_BUILD_TARGETS,
    NULL_SHA,
    SKIP_BINARY_BUILD_BRANCHES,
    Dialect,
    Metadata,
    get_latest_tag_version,
    get_release_version_from_commits,
    is_version_bump_allowed,
)


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


class OptionalList:
    """Matcher for values that can be None or a list matching a pattern.

    Used for fields like ``new_commits`` that are ``None`` outside GitHub Actions
    but contain commit SHAs when running in CI with event data.
    """

    def __init__(self, item_pattern: re.Pattern) -> None:
        self.item_pattern = item_pattern


class OptionalString:
    """Matcher for GitHub format values that can be empty or space-separated items.

    GitHub Actions format converts None to empty string and lists to space-separated
    quoted strings. This class matches either case.
    """

    def __init__(self, item_pattern: re.Pattern) -> None:
        self.item_pattern = item_pattern


class AnyBool:
    """Matcher that accepts either True or False.

    Used for fields that depend on repository state and can vary between test runs.
    """


class AnyBoolString:
    """Matcher that accepts either 'true' or 'false' string.

    Used for GitHub format booleans that depend on repository state.
    """


class AnyLengthList:
    """Matcher for lists where each item matches a pattern, regardless of length.

    Used for matrix fields like ``commit`` where the number of commits can vary
    depending on how many are pushed together.
    """

    def __init__(self, item_pattern: re.Pattern) -> None:
        self.item_pattern = item_pattern


class PartialIncludeList:
    """Matcher for include lists where required items must be present.

    The nuitka_matrix ``include`` list contains per-commit entries that multiply
    when multiple commits are pushed together. This matcher validates that all
    required items (build targets, entry point info, state) are present, while
    allowing additional commit-specific items.
    """

    def __init__(self, required_items: list[dict]) -> None:
        self.required_items = required_items


class OptionalMatrix:
    """Matcher for values that can be None or a matrix dict with commit data.

    Used for fields like ``new_commits_matrix`` that are ``None`` outside GitHub Actions
    but contain a matrix dict when running in CI with event data.
    """


class OptionalMatrixOrEmptyString:
    """Matcher for GitHub format values that can be empty string or a matrix dict.

    GitHub Actions format converts None to empty string. In CI, the value is a dict.
    """


class OptionalVersionString:
    """Matcher for values that can be None or a version string.

    Used for ``released_version`` which is ``None`` during development but contains
    a version string like ``"5.5.0"`` on release branches.
    """

    def __init__(self, version_pattern: re.Pattern) -> None:
        self.version_pattern = version_pattern


class OptionalVersionOrEmptyString:
    """Matcher for GitHub format values that can be empty string or a version string.

    GitHub Actions format converts None to empty string. On release branches,
    the value is a version string.
    """

    def __init__(self, version_pattern: re.Pattern) -> None:
        self.version_pattern = version_pattern


class AnyReleaseNotes:
    """Matcher for release notes that vary based on development vs release state.

    During development, release notes contain a warning that the version is not
    released yet. On release branches, the notes contain actual release content.
    """

    def __init__(self, dev_pattern: re.Pattern, release_pattern: re.Pattern) -> None:
        self.dev_pattern = dev_pattern
        self.release_pattern = release_pattern


class AnyReleaseNotesOrEmptyString:
    """Matcher for GitHub format release notes.

    Can be empty string (when no version), or match either development or release
    notes patterns.
    """

    def __init__(self, dev_pattern: re.Pattern, release_pattern: re.Pattern) -> None:
        self.dev_pattern = dev_pattern
        self.release_pattern = release_pattern


def _matches_pattern(item: Any, pattern: dict) -> bool:
    """Check if an item matches a pattern dict.

    Returns True if item is a dict with all keys from pattern, and each value
    matches (either exact match or regex match for Pattern objects).
    """
    if not isinstance(item, dict):
        return False
    if not set(pattern.keys()).issubset(set(item.keys())):
        return False
    for key, expected_value in pattern.items():
        actual_value = item[key]
        if isinstance(expected_value, re.Pattern):
            if not isinstance(actual_value, str):
                return False
            if re.fullmatch(expected_value, actual_value) is None:
                return False
        elif actual_value != expected_value:
            return False
    return True


def iter_checks(metadata: Any, expected: Any, context: Any) -> None:
    """Recursively iterate over expected content and check it matches in metadata."""

    if isinstance(expected, re.Pattern):
        assert isinstance(metadata, str)
        assert re.fullmatch(expected, metadata) is not None, (
            f"{metadata!r} does not match {expected.pattern!r} in {context!r}"
        )

    elif isinstance(expected, OptionalList):
        # Allow None or a list of items matching the pattern.
        if metadata is None:
            return
        assert isinstance(metadata, list), (
            f"{metadata!r} should be None or a list in {context!r}"
        )
        for item in metadata:
            assert isinstance(item, str), f"{item!r} should be a string in {context!r}"
            assert re.fullmatch(expected.item_pattern, item) is not None, (
                f"{item!r} does not match {expected.item_pattern.pattern!r} in {context!r}"
            )

    elif isinstance(expected, OptionalString):
        # Allow empty string or space-separated quoted items matching the pattern.
        assert isinstance(metadata, str), (
            f"{metadata!r} should be a string in {context!r}"
        )
        if metadata == "":
            return
        # Parse space-separated items: "sha1" "sha2" -> ["sha1", "sha2"].
        for item in metadata.split():
            assert re.fullmatch(expected.item_pattern, item) is not None, (
                f"{item!r} does not match {expected.item_pattern.pattern!r} in {context!r}"
            )

    elif isinstance(expected, AnyBool):
        # Accept either True or False.
        assert isinstance(metadata, bool), (
            f"{metadata!r} should be a boolean in {context!r}"
        )

    elif isinstance(expected, AnyBoolString):
        # Accept either 'true' or 'false' string.
        assert metadata in ("true", "false"), (
            f"{metadata!r} should be 'true' or 'false' in {context!r}"
        )

    elif isinstance(expected, AnyLengthList):
        # Accept a list of any length where each item matches the pattern.
        assert isinstance(metadata, list), (
            f"{metadata!r} should be a list in {context!r}"
        )
        assert len(metadata) >= 1, f"list should have at least one item in {context!r}"
        for item in metadata:
            assert isinstance(item, str), f"{item!r} should be a string in {context!r}"
            assert re.fullmatch(expected.item_pattern, item) is not None, (
                f"{item!r} does not match {expected.item_pattern.pattern!r} in {context!r}"
            )

    elif isinstance(expected, PartialIncludeList):
        # Accept a list where all required items are present, allowing extras.
        assert isinstance(metadata, list), (
            f"{metadata!r} should be a list in {context!r}"
        )
        assert len(metadata) >= len(expected.required_items), (
            f"list should have at least {len(expected.required_items)} items in "
            f"{context!r}"
        )
        # Check each required item has at least one match in metadata.
        for required in expected.required_items:
            found = False
            for item in metadata:
                if _matches_pattern(item, required):
                    found = True
                    break
            assert found, (
                f"required item {required!r} not found in metadata list in {context!r}"
            )

    elif isinstance(expected, OptionalMatrix):
        # Allow None or a matrix dict with commit data.
        if metadata is None:
            return
        assert isinstance(metadata, dict), (
            f"{metadata!r} should be None or a dict in {context!r}"
        )
        # Validate basic matrix structure if present.
        if "commit" in metadata:
            assert isinstance(metadata["commit"], list)

    elif isinstance(expected, OptionalMatrixOrEmptyString):
        # Allow empty string or a matrix dict.
        if metadata == "":
            return
        assert isinstance(metadata, dict), (
            f"{metadata!r} should be '' or a dict in {context!r}"
        )
        # Validate basic matrix structure if present.
        if "commit" in metadata:
            assert isinstance(metadata["commit"], list)

    elif isinstance(expected, OptionalVersionString):
        # Allow None or a version string matching the pattern.
        if metadata is None:
            return
        assert isinstance(metadata, str), (
            f"{metadata!r} should be None or a string in {context!r}"
        )
        assert re.fullmatch(expected.version_pattern, metadata) is not None, (
            f"{metadata!r} does not match {expected.version_pattern.pattern!r} in {context!r}"
        )

    elif isinstance(expected, OptionalVersionOrEmptyString):
        # Allow empty string or a version string matching the pattern.
        if metadata == "":
            return
        assert isinstance(metadata, str), (
            f"{metadata!r} should be '' or a string in {context!r}"
        )
        assert re.fullmatch(expected.version_pattern, metadata) is not None, (
            f"{metadata!r} does not match {expected.version_pattern.pattern!r} in {context!r}"
        )

    elif isinstance(expected, AnyReleaseNotes):
        # Allow release notes matching either development or release pattern.
        assert isinstance(metadata, str), (
            f"{metadata!r} should be a string in {context!r}"
        )
        dev_match = re.fullmatch(expected.dev_pattern, metadata) is not None
        release_match = re.fullmatch(expected.release_pattern, metadata) is not None
        assert dev_match or release_match, (
            f"{metadata!r} does not match dev pattern {expected.dev_pattern.pattern!r} "
            f"or release pattern {expected.release_pattern.pattern!r} in {context!r}"
        )

    elif isinstance(expected, AnyReleaseNotesOrEmptyString):
        # Allow empty string or release notes matching either pattern.
        if metadata == "":
            return
        assert isinstance(metadata, str), (
            f"{metadata!r} should be '' or a string in {context!r}"
        )
        dev_match = re.fullmatch(expected.dev_pattern, metadata) is not None
        release_match = re.fullmatch(expected.release_pattern, metadata) is not None
        assert dev_match or release_match, (
            f"{metadata!r} does not match dev pattern {expected.dev_pattern.pattern!r} "
            f"or release pattern {expected.release_pattern.pattern!r} in {context!r}"
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
    "skip_binary_build": False,
    # new_commits is None when running outside GitHub Actions (no event data).
    # In CI, it contains commit SHAs extracted from the push event payload.
    "new_commits": OptionalList(regex(r"[a-f0-9]{40}")),
    # release_commits is None when there are no release commits in the event.
    # It contains SHAs only when a "[changelog] Release vX.Y.Z" commit is present.
    "release_commits": OptionalList(regex(r"[a-f0-9]{40}")),
    "mailmap_exists": True,
    "gitignore_exists": True,
    "python_files": [
        "gha_utils/__init__.py",
        "gha_utils/__main__.py",
        "gha_utils/binary.py",
        "gha_utils/broken_links.py",
        "gha_utils/bundled_config.py",
        "gha_utils/changelog.py",
        "gha_utils/cli.py",
        "gha_utils/data/__init__.py",
        "gha_utils/deps_graph.py",
        "gha_utils/git_ops.py",
        "gha_utils/github.py",
        "gha_utils/lint_repo.py",
        "gha_utils/mailmap.py",
        "gha_utils/matrix.py",
        "gha_utils/metadata.py",
        "gha_utils/release_prep.py",
        "gha_utils/renovate.py",
        "gha_utils/sphinx_linkcheck.py",
        "gha_utils/sponsor.py",
        "gha_utils/test_plan.py",
        "tests/__init__.py",
        "tests/test_binary.py",
        "tests/test_broken_links.py",
        "tests/test_bundled_config.py",
        "tests/test_changelog.py",
        "tests/test_deps_graph.py",
        "tests/test_git_ops.py",
        "tests/test_lint_repo.py",
        "tests/test_mailmap.py",
        "tests/test_matrix.py",
        "tests/test_metadata.py",
        "tests/test_release_prep.py",
        "tests/test_renovate.py",
        "tests/test_sphinx_linkcheck.py",
        "tests/test_workflows.py",
    ],
    "json_files": [],
    "yaml_files": [
        ".github/actions/pr-metadata/action.yml",
        ".github/funding.yml",
        ".github/workflows/autofix.yaml",
        ".github/workflows/autolock.yaml",
        ".github/workflows/changelog.yaml",
        ".github/workflows/debug.yaml",
        ".github/workflows/docs.yaml",
        ".github/workflows/labels.yaml",
        ".github/workflows/lint.yaml",
        ".github/workflows/release.yaml",
        ".github/workflows/renovate.yaml",
        ".github/workflows/tests.yaml",
        "gha_utils/data/labeller-content-based.yaml",
        "gha_utils/data/labeller-file-based.yaml",
        "tests/cli-test-plan.yaml",
    ],
    "toml_files": [
        "gha_utils/data/bumpversion.toml",
        "gha_utils/data/labels.toml",
        "gha_utils/data/mypy.toml",
        "gha_utils/data/pytest.toml",
        "gha_utils/data/ruff.toml",
        "lychee.toml",
        "pyproject.toml",
    ],
    "workflow_files": [
        ".github/workflows/autofix.yaml",
        ".github/workflows/autolock.yaml",
        ".github/workflows/changelog.yaml",
        ".github/workflows/debug.yaml",
        ".github/workflows/docs.yaml",
        ".github/workflows/labels.yaml",
        ".github/workflows/lint.yaml",
        ".github/workflows/release.yaml",
        ".github/workflows/renovate.yaml",
        ".github/workflows/tests.yaml",
    ],
    "doc_files": [
        ".github/code-of-conduct.md",
        "changelog.md",
        "claude.md",
        "readme.md",
    ],
    "markdown_files": [
        ".github/code-of-conduct.md",
        "changelog.md",
        "claude.md",
        "readme.md",
    ],
    "image_files": [
        "docs/assets/repo-workflow-permissions.png",
    ],
    "zsh_files": [],
    "is_python_project": True,
    "package_name": "gha-utils",
    "project_description": "🧩 CLI for GitHub Actions + reusable workflows",
    "mypy_params": "--python-version 3.10",
    "current_version": regex(r"[0-9\.]+"),
    # released_version is None during development, but contains a version string
    # on release branches (e.g., "5.5.0" when a "[changelog] Release v5.5.0"
    # commit exists).
    "released_version": OptionalVersionString(regex(r"[0-9]+\.[0-9]+\.[0-9]+")),
    "is_sphinx": False,
    "active_autodoc": False,
    # Release notes vary based on development vs release state.
    # Development: contains "not released yet" warning.
    # Release: contains actual changelog content and PyPI link.
    "release_notes": AnyReleaseNotes(
        dev_pattern=regex(
            r"### Changes\n\n"
            r"> \[\!IMPORTANT\]\n"
            r"> This version is not released yet and is under active development\.\n\n"
            r".+"
        ),
        release_pattern=regex(
            r"### Changes\n\n"
            r"(?!> \[\!IMPORTANT\])"  # Not starting with the warning.
            r".+"
        ),
    ),
    # new_commits_matrix is None when running outside GitHub Actions.
    # In CI, it contains a matrix dict with commit data.
    "new_commits_matrix": OptionalMatrix(),
    # release_commits_matrix is None when there are no release commits.
    # It contains a matrix dict only when a "[changelog] Release vX.Y.Z"
    # commit is present.
    "release_commits_matrix": OptionalMatrix(),
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
        "commit": AnyLengthList(regex(r"[a-z0-9]+")),
        # The include list contains per-commit entries that multiply with more commits.
        # We validate that required fixed items are present (build targets, entry point,
        # state) plus at least one commit info and one bin_name entry.
        "include": PartialIncludeList([
            # Build targets (fixed, one per platform).
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
            # Entry point info (fixed, one per entry point).
            {
                "entry_point": "gha-utils",
                "cli_id": "gha-utils",
                "module_id": "gha_utils.__main__",
                "callable_id": "main",
                "module_path": regex(r"gha_utils(/|\\)__main__\.py"),
            },
            # State (fixed).
            {"state": "stable"},
            # At least one commit info entry (varies by commit count).
            {
                "commit": regex(r"[a-z0-9]+"),
                "short_sha": regex(r"[a-z0-9]+"),
                "current_version": regex(r"[0-9\.]+"),
            },
            # At least one bin_name entry per OS (varies by commit count).
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
        ]),
    },
    # Bump allowed values depend on comparing current version vs latest git tag.
    # These can be True or False depending on the current development cycle state.
    "minor_bump_allowed": AnyBool(),
    "major_bump_allowed": AnyBool(),
}


def test_metadata_json_format():
    metadata = Metadata().dump(Dialect.json)
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
        elif isinstance(value, OptionalList):
            # Convert OptionalList to OptionalString for GitHub format.
            new_value = OptionalString(value.item_pattern)
        elif isinstance(value, AnyBool):
            # Convert AnyBool to AnyBoolString for GitHub format.
            new_value = AnyBoolString()
        elif isinstance(value, OptionalMatrix):
            # Convert OptionalMatrix to OptionalMatrixOrEmptyString for GitHub format.
            new_value = OptionalMatrixOrEmptyString()
        elif isinstance(value, OptionalVersionString):
            # Convert OptionalVersionString to OptionalVersionOrEmptyString for GitHub
            # format.
            new_value = OptionalVersionOrEmptyString(value.version_pattern)
        elif isinstance(value, AnyReleaseNotes):
            # Convert AnyReleaseNotes to AnyReleaseNotesOrEmptyString for GitHub format.
            new_value = AnyReleaseNotesOrEmptyString(
                value.dev_pattern, value.release_pattern
            )
        elif isinstance(value, list) and all(isinstance(i, str) for i in value):
            new_value = " ".join(f'"{i}"' for i in value)
        github_format_expected[key] = new_value

    iter_checks(metadata, github_format_expected, raw_metadata)


def test_get_latest_tag_version():
    """Test that we can retrieve the latest Git tag version."""
    latest = get_latest_tag_version()
    # In CI environments with shallow clones, tags may not be available.
    if latest is None:
        pytest.skip("No release tags available (shallow clone in CI).")
    assert isinstance(latest, Version)
    # Sanity check: version should be a reasonable semver.
    assert latest.major >= 0
    assert latest.minor >= 0
    assert latest.micro >= 0


def test_is_version_bump_allowed_returns_bool():
    """Test that is_version_bump_allowed returns a boolean."""
    # Test minor check.
    result = is_version_bump_allowed("minor")
    assert isinstance(result, bool)

    # Test major check.
    result = is_version_bump_allowed("major")
    assert isinstance(result, bool)


def test_is_version_bump_allowed_invalid_part():
    """Test that is_version_bump_allowed raises for invalid parts."""
    with pytest.raises(ValueError, match="Invalid version part"):
        is_version_bump_allowed("patch")


def test_is_version_bump_allowed_current_repo():
    """Test the version bump check logic against the current repository state.

    This test verifies the correct behavior based on comparing current version
    in pyproject.toml against the latest Git tag.
    """
    current_version_str = Metadata.get_current_version()
    assert current_version_str is not None
    current = Version(current_version_str)

    latest_tag = get_latest_tag_version()
    # In CI environments with shallow clones, tags may not be available.
    if latest_tag is None:
        pytest.skip("No release tags available (shallow clone in CI).")

    # Verify the logic matches what the function should return.
    minor_allowed = is_version_bump_allowed("minor")
    major_allowed = is_version_bump_allowed("major")

    # Expected: minor bump blocked if minor already ahead (within same major).
    expected_minor_blocked = current.major > latest_tag.major or (
        current.major == latest_tag.major and current.minor > latest_tag.minor
    )
    assert minor_allowed == (not expected_minor_blocked)

    # Expected: major bump blocked if major already ahead.
    expected_major_blocked = current.major > latest_tag.major
    assert major_allowed == (not expected_major_blocked)


def test_minor_bump_allowed_property() -> None:
    """Test that minor_bump_allowed property returns a boolean."""
    metadata = Metadata()
    assert isinstance(metadata.minor_bump_allowed, bool)


def test_major_bump_allowed_property() -> None:
    """Test that major_bump_allowed property returns a boolean."""
    metadata = Metadata()
    assert isinstance(metadata.major_bump_allowed, bool)


def test_null_sha_constant():
    """Test that NULL_SHA is a valid 40-character string of zeros.

    This constant is used to detect when GitHub sends a null SHA as the "before"
    commit when a tag is created (since there is no previous commit).
    """
    assert isinstance(NULL_SHA, str)
    assert len(NULL_SHA) == 40
    assert NULL_SHA == "0" * 40
    # Verify it's truthy (important for the fix: we can't just check `if not sha`).
    assert bool(NULL_SHA) is True


def test_skip_binary_build_branches_constant():
    """Test that SKIP_BINARY_BUILD_BRANCHES contains expected branch names."""
    assert isinstance(SKIP_BINARY_BUILD_BRANCHES, frozenset)
    # Verify the list contains expected branches for non-code changes.
    assert "update-mailmap" in SKIP_BINARY_BUILD_BRANCHES
    assert "format-markdown" in SKIP_BINARY_BUILD_BRANCHES
    assert "optimize-images" in SKIP_BINARY_BUILD_BRANCHES
    assert "update-gitignore" in SKIP_BINARY_BUILD_BRANCHES
    # Verify branches that affect code are NOT in the list.
    assert "format-python" not in SKIP_BINARY_BUILD_BRANCHES
    assert "prepare-release" not in SKIP_BINARY_BUILD_BRANCHES
    assert "main" not in SKIP_BINARY_BUILD_BRANCHES


def test_skip_binary_build_property_false_by_default():
    """Test that skip_binary_build is False when not in a PR context."""
    metadata = Metadata()
    # Outside of PR context (GITHUB_HEAD_REF not set), skip_binary_build is False.
    assert isinstance(metadata.skip_binary_build, bool)
    assert metadata.skip_binary_build is False


def test_is_bot_false_by_default():
    """Test that is_bot is False when not in a bot context."""
    metadata = Metadata()
    # Outside of bot context (no bot actor or renovate branch), is_bot is False.
    assert isinstance(metadata.is_bot, bool)
    assert metadata.is_bot is False


def test_is_bot_detects_renovate_branch(monkeypatch):
    """Test that is_bot returns True for Renovate branch patterns."""
    monkeypatch.setenv("GITHUB_HEAD_REF", "renovate/taiki-e-install-action-2.x")
    metadata = Metadata()
    assert metadata.is_bot is True


def test_is_bot_ignores_non_renovate_branch(monkeypatch):
    """Test that is_bot returns False for non-Renovate branches."""
    monkeypatch.setenv("GITHUB_HEAD_REF", "feature/add-new-feature")
    metadata = Metadata()
    assert metadata.is_bot is False


def test_get_release_version_from_commits():
    """Test that get_release_version_from_commits returns expected type.

    This function searches recent commits for release messages matching
    ``[changelog] Release vX.Y.Z`` pattern and extracts the version.
    """
    result = get_release_version_from_commits()
    # Result can be None (no release commits) or a Version object.
    assert result is None or isinstance(result, Version)
    if result is not None:
        # Sanity check: version should be a reasonable semver.
        assert result.major >= 0
        assert result.minor >= 0
        assert result.micro >= 0


def test_get_release_version_from_commits_max_count():
    """Test that max_count parameter limits commit search."""
    # With max_count=1, we only check the HEAD commit.
    result = get_release_version_from_commits(max_count=1)
    assert result is None or isinstance(result, Version)

    # With max_count=0, no commits should be checked.
    result = get_release_version_from_commits(max_count=0)
    assert result is None


def test_is_version_bump_allowed_uses_commit_fallback():
    """Test that is_version_bump_allowed still works when tags might not be available.

    This test verifies the function returns a boolean regardless of whether
    tags are found, as it now has a fallback to parse commit messages.
    """
    # The function should always return a boolean, even if tags aren't available.
    result = is_version_bump_allowed("minor")
    assert isinstance(result, bool)

    result = is_version_bump_allowed("major")
    assert isinstance(result, bool)
