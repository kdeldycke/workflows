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

from repomatic.github.actions import NULL_SHA
from repomatic.metadata import (
    Dialect,
    NUITKA_BUILD_TARGETS,
    SKIP_BINARY_BUILD_BRANCHES,
    Config,
    Metadata,
    get_latest_tag_version,
    get_project_name,
    get_release_version_from_commits,
    is_version_bump_allowed,
    load_repomatic_config,
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
    "is_bot": AnyBool(),
    "skip_binary_build": False,
    # new_commits is None when running outside GitHub Actions (no event data).
    # In CI, it contains commit SHAs extracted from the push event payload.
    "new_commits": OptionalList(regex(r"[a-f0-9]{40}")),
    # release_commits is None when there are no release commits in the event.
    # It contains SHAs only when a "[changelog] Release vX.Y.Z" commit is present.
    "release_commits": OptionalList(regex(r"[a-f0-9]{40}")),
    "mailmap_exists": True,
    "gitignore_exists": True,
    "renovate_config_exists": True,
    "python_files": [
        "repomatic/__init__.py",
        "repomatic/__main__.py",
        "repomatic/binary.py",
        "repomatic/broken_links.py",
        "repomatic/changelog.py",
        "repomatic/checksums.py",
        "repomatic/cli.py",
        "repomatic/data/__init__.py",
        "repomatic/deps_graph.py",
        "repomatic/git_ops.py",
        "repomatic/github/__init__.py",
        "repomatic/github/actions.py",
        "repomatic/github/gh.py",
        "repomatic/github/issue.py",
        "repomatic/github/matrix.py",
        "repomatic/github/pr_body.py",
        "repomatic/github/token.py",
        "repomatic/github/unsubscribe.py",
        "repomatic/github/workflow_sync.py",
        "repomatic/init_project.py",
        "repomatic/lint_repo.py",
        "repomatic/mailmap.py",
        "repomatic/metadata.py",
        "repomatic/release_prep.py",
        "repomatic/renovate.py",
        "repomatic/sponsor.py",
        "repomatic/templates/__init__.py",
        "repomatic/test_plan.py",
        "tests/__init__.py",
        "tests/test_binary.py",
        "tests/test_broken_links.py",
        "tests/test_changelog.py",
        "tests/test_deps_graph.py",
        "tests/test_git_ops.py",
        "tests/test_init_project.py",
        "tests/test_lint_repo.py",
        "tests/test_mailmap.py",
        "tests/test_matrix.py",
        "tests/test_metadata.py",
        "tests/test_pr_body.py",
        "tests/test_release_prep.py",
        "tests/test_renovate.py",
        "tests/test_sync_renovate.py",
        "tests/test_workflow_sync.py",
        "tests/test_workflows.py",
    ],
    "json_files": [],
    "yaml_files": [
        ".github/funding.yml",
        ".github/workflows/autofix.yaml",
        ".github/workflows/autolock.yaml",
        ".github/workflows/cancel-runs.yaml",
        ".github/workflows/changelog.yaml",
        ".github/workflows/debug.yaml",
        ".github/workflows/docs.yaml",
        ".github/workflows/labels.yaml",
        ".github/workflows/lint.yaml",
        ".github/workflows/release.yaml",
        ".github/workflows/renovate.yaml",
        ".github/workflows/tests.yaml",
        "repomatic/data/labeller-content-based.yaml",
        "repomatic/data/labeller-file-based.yaml",
        "repomatic/data/zizmor.yaml",
        "tests/cli-test-plan.yaml",
        "zizmor.yaml",
    ],
    "toml_files": [
        "lychee.toml",
        "pyproject.toml",
        "repomatic/data/bumpversion.toml",
        "repomatic/data/labels.toml",
        "repomatic/data/mypy.toml",
        "repomatic/data/pytest.toml",
        "repomatic/data/ruff.toml",
    ],
    "workflow_files": [
        ".github/workflows/autofix.yaml",
        ".github/workflows/autolock.yaml",
        ".github/workflows/cancel-runs.yaml",
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
        ".claude/agents/grunt-qa.md",
        ".claude/agents/qa-engineer.md",
        ".claude/skills/repomatic-changelog/SKILL.md",
        ".claude/skills/repomatic-deps/SKILL.md",
        ".claude/skills/repomatic-init/SKILL.md",
        ".claude/skills/repomatic-lint/SKILL.md",
        ".claude/skills/repomatic-metadata/SKILL.md",
        ".claude/skills/repomatic-release/SKILL.md",
        ".claude/skills/repomatic-sync/SKILL.md",
        ".claude/skills/repomatic-test/SKILL.md",
        ".github/code-of-conduct.md",
        "changelog.md",
        "claude.md",
        "readme.md",
        "repomatic/templates/bump-version.md",
        "repomatic/templates/detect-squash-merge.md",
        "repomatic/templates/fix-typos.md",
        "repomatic/templates/format-json.md",
        "repomatic/templates/format-markdown.md",
        "repomatic/templates/format-pyproject.md",
        "repomatic/templates/format-python.md",
        "repomatic/templates/lint-changelog.md",
        "repomatic/templates/pr-metadata.md",
        "repomatic/templates/prepare-release.md",
        "repomatic/templates/refresh-tip.md",
        "repomatic/templates/release-notes.md",
        "repomatic/templates/setup-guide.md",
        "repomatic/templates/sync-bumpversion.md",
        "repomatic/templates/sync-gitignore.md",
        "repomatic/templates/sync-linter-configs.md",
        "repomatic/templates/sync-mailmap.md",
        "repomatic/templates/sync-renovate.md",
        "repomatic/templates/sync-uv-lock.md",
        "repomatic/templates/sync-workflows.md",
        "repomatic/templates/update-deps-graph.md",
        "repomatic/templates/update-docs.md",
    ],
    "markdown_files": [
        ".claude/agents/grunt-qa.md",
        ".claude/agents/qa-engineer.md",
        ".claude/skills/repomatic-changelog/SKILL.md",
        ".claude/skills/repomatic-deps/SKILL.md",
        ".claude/skills/repomatic-init/SKILL.md",
        ".claude/skills/repomatic-lint/SKILL.md",
        ".claude/skills/repomatic-metadata/SKILL.md",
        ".claude/skills/repomatic-release/SKILL.md",
        ".claude/skills/repomatic-sync/SKILL.md",
        ".claude/skills/repomatic-test/SKILL.md",
        ".github/code-of-conduct.md",
        "changelog.md",
        "claude.md",
        "readme.md",
        "repomatic/templates/bump-version.md",
        "repomatic/templates/detect-squash-merge.md",
        "repomatic/templates/fix-typos.md",
        "repomatic/templates/format-json.md",
        "repomatic/templates/format-markdown.md",
        "repomatic/templates/format-pyproject.md",
        "repomatic/templates/format-python.md",
        "repomatic/templates/lint-changelog.md",
        "repomatic/templates/pr-metadata.md",
        "repomatic/templates/prepare-release.md",
        "repomatic/templates/refresh-tip.md",
        "repomatic/templates/release-notes.md",
        "repomatic/templates/setup-guide.md",
        "repomatic/templates/sync-bumpversion.md",
        "repomatic/templates/sync-gitignore.md",
        "repomatic/templates/sync-linter-configs.md",
        "repomatic/templates/sync-mailmap.md",
        "repomatic/templates/sync-renovate.md",
        "repomatic/templates/sync-uv-lock.md",
        "repomatic/templates/sync-workflows.md",
        "repomatic/templates/update-deps-graph.md",
        "repomatic/templates/update-docs.md",
    ],
    "image_files": [
        "docs/assets/repo-workflow-permissions.png",
    ],
    "zsh_files": [],
    "is_python_project": True,
    "nuitka": True,
    "package_name": "repomatic",
    "project_description": "🧩 CLI for GitHub Actions + reusable workflows",
    "mypy_params": "--python-version 3.10",
    "current_version": regex(r"[0-9\.]+(\.dev[0-9]+)?"),
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
            r"> \[\!WARNING\]\n"
            r"> This version is \*\*not released yet\*\* and is under active development\.\n\n"
            r".+"
        ),
        release_pattern=regex(
            r"(?:### Changes\n\n(?!> \[\!WARNING\]).+|"  # With changelog entries.
            # Without.
            r"> \[\!NOTE\]\n> `.+` is available on \[🐍 PyPI\].+ and \[🐙 GitHub\].+)"
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
        "entry_point": ["repomatic"],
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
                "entry_point": "repomatic",
                "cli_id": "repomatic",
                "module_id": "repomatic.__main__",
                "callable_id": "main",
                "module_path": regex(r"repomatic(/|\\)__main__\.py"),
            },
            # Nuitka extra args from [tool.repomatic] config (fixed).
            {
                "nuitka_extra_args": (
                    "--include-package-data=extra_platforms"
                    " --include-data-files=repomatic/templates/*.md=repomatic/templates/"
                ),
            },
            # State (fixed).
            {"state": "stable"},
            # At least one commit info entry (varies by commit count).
            {
                "commit": regex(r"[a-z0-9]+"),
                "short_sha": regex(r"[a-z0-9]+"),
                "current_version": regex(r"[0-9\.]+(\.dev[0-9]+)?"),
            },
            # At least one bin_name entry per OS (varies by commit count).
            {
                "os": "ubuntu-24.04-arm",
                "entry_point": "repomatic",
                "commit": regex(r"[a-z0-9]+"),
                "bin_name": "repomatic-linux-arm64.bin",
            },
            {
                "os": "ubuntu-24.04",
                "entry_point": "repomatic",
                "commit": regex(r"[a-z0-9]+"),
                "bin_name": "repomatic-linux-x64.bin",
            },
            {
                "os": "macos-26",
                "entry_point": "repomatic",
                "commit": regex(r"[a-z0-9]+"),
                "bin_name": "repomatic-macos-arm64.bin",
            },
            {
                "os": "macos-15-intel",
                "entry_point": "repomatic",
                "commit": regex(r"[a-z0-9]+"),
                "bin_name": "repomatic-macos-x64.bin",
            },
            {
                "os": "windows-11-arm",
                "entry_point": "repomatic",
                "commit": regex(r"[a-z0-9]+"),
                "bin_name": "repomatic-windows-arm64.exe",
            },
            {
                "os": "windows-2025",
                "entry_point": "repomatic",
                "commit": regex(r"[a-z0-9]+"),
                "bin_name": "repomatic-windows-x64.exe",
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
    assert "sync-mailmap" in SKIP_BINARY_BUILD_BRANCHES
    assert "format-markdown" in SKIP_BINARY_BUILD_BRANCHES
    assert "optimize-images" in SKIP_BINARY_BUILD_BRANCHES
    assert "sync-gitignore" in SKIP_BINARY_BUILD_BRANCHES
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


def test_nuitka_enabled_default():
    """Test that nuitka config defaults to True."""
    metadata = Metadata()
    assert metadata.config["nuitka"] is True


def test_nuitka_disabled_skips_matrix(tmp_path, monkeypatch):
    """Test that nuitka_matrix returns None when nuitka is disabled in pyproject.toml."""
    pyproject_content = """\
[project]
name = "test-project"
version = "1.0.0"

[project.scripts]
my-cli = "my_package.__main__:main"

[tool.repomatic]
nuitka = false
"""
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text(pyproject_content)

    # Override the pyproject path to point to our temporary file.
    monkeypatch.setattr(Metadata, "pyproject_path", pyproject_file)

    metadata = Metadata()
    assert metadata.config["nuitka"] is False
    assert metadata.nuitka_matrix is None


def test_is_bot_false_by_default(monkeypatch):
    """Test that is_bot is False when not in a bot context."""
    # Clear CI env vars that could make is_bot return True (e.g., when tests run
    # on a commit pushed by Renovate, GITHUB_ACTOR is "renovate-bot").
    monkeypatch.delenv("GITHUB_ACTOR", raising=False)
    monkeypatch.delenv("GITHUB_EVENT_PATH", raising=False)
    monkeypatch.delenv("GITHUB_HEAD_REF", raising=False)
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


def test_repomatic_config_defaults():
    """Test that [tool.repomatic] config properties return sensible defaults."""
    metadata = Metadata()
    assert metadata.config["test-plan-file"] == "./tests/cli-test-plan.yaml"
    assert metadata.config["timeout"] is None
    assert metadata.config["test-plan"] is None
    assert metadata.config["gitignore-location"] == "./.gitignore"
    assert metadata.config["gitignore-extra-categories"] == []
    assert metadata.config["gitignore-extra-content"] == (
        "junit.xml\n\n# Claude Code local settings.\n.claude/settings.local.json"
    )
    assert (
        metadata.config["dependency-graph-output"] == "./docs/assets/dependencies.mmd"
    )
    assert metadata.config["dependency-graph-all-groups"] is True
    assert metadata.config["dependency-graph-all-extras"] is True
    assert metadata.config["dependency-graph-no-groups"] == []
    assert metadata.config["dependency-graph-no-extras"] == []
    assert metadata.config["dependency-graph-level"] is None
    assert metadata.config["extra-label-files"] == []
    assert metadata.config["extra-file-rules"] == ""
    assert metadata.config["extra-content-rules"] == ""
    assert metadata.config["renovate-sync"] is True
    assert metadata.config["workflow-sync"] is True
    assert metadata.config["workflow-sync-exclude"] == []


def test_repomatic_config_custom_values(tmp_path, monkeypatch):
    """Test that [tool.repomatic] config properties read from pyproject.toml."""
    pyproject_content = """\
[project]
name = "test-project"
version = "1.0.0"

[tool.repomatic]
test-plan-file = "./custom/test-plan.yaml"
timeout = 120
test-plan = "- args: --version"
gitignore-location = "./custom/.gitignore"
gitignore-extra-categories = ["terraform", "go"]
gitignore-extra-content = '''
junit.xml

# Claude Code
.claude/
'''
dependency-graph-output = "./custom/deps.mmd"
dependency-graph-all-groups = false
dependency-graph-all-extras = true
dependency-graph-no-groups = ["typing"]
dependency-graph-no-extras = ["xml"]
dependency-graph-level = 2
unstable-targets = ["linux-arm64", "windows-x64"]
extra-label-files = ["https://example.com/labels.toml"]
extra-file-rules = "docs:\\n  - docs/**"
extra-content-rules = "security:\\n  - '(CVE|vulnerability)'"
renovate-sync = false
workflow-sync = false
workflow-sync-exclude = ["debug.yaml", "autolock.yaml"]
"""
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text(pyproject_content)
    monkeypatch.setattr(Metadata, "pyproject_path", pyproject_file)

    metadata = Metadata()
    assert metadata.config["test-plan-file"] == "./custom/test-plan.yaml"
    assert metadata.config["timeout"] == 120
    assert metadata.config["test-plan"] == "- args: --version"
    assert metadata.config["gitignore-location"] == "./custom/.gitignore"
    assert metadata.config["gitignore-extra-categories"] == [
        "terraform",
        "go",
    ]
    assert (
        metadata.config["gitignore-extra-content"]
        == "junit.xml\n\n# Claude Code\n.claude/\n"
    )
    assert metadata.config["dependency-graph-output"] == "./custom/deps.mmd"
    assert metadata.config["dependency-graph-all-groups"] is False
    assert metadata.config["dependency-graph-all-extras"] is True
    assert metadata.config["dependency-graph-no-groups"] == ["typing"]
    assert metadata.config["dependency-graph-no-extras"] == ["xml"]
    assert metadata.config["dependency-graph-level"] == 2
    assert metadata.unstable_targets == {"linux-arm64", "windows-x64"}
    assert metadata.config["extra-label-files"] == [
        "https://example.com/labels.toml",
    ]
    assert metadata.config["extra-file-rules"] == "docs:\n  - docs/**"
    assert (
        metadata.config["extra-content-rules"] == "security:\n  - '(CVE|vulnerability)'"
    )
    assert metadata.config["renovate-sync"] is False
    assert metadata.config["workflow-sync"] is False
    assert metadata.config["workflow-sync-exclude"] == [
        "debug.yaml",
        "autolock.yaml",
    ]


def test_unstable_targets_default():
    """Test that unstable_targets defaults to an empty set."""
    metadata = Metadata()
    assert metadata.unstable_targets == set()


def test_unstable_targets_ignores_unknown(tmp_path, monkeypatch):
    """Test that unrecognized unstable targets are discarded with a warning."""
    pyproject_content = """\
[project]
name = "test-project"
version = "1.0.0"

[tool.repomatic]
unstable-targets = ["linux-arm64", "unknown-target"]
"""
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text(pyproject_content)
    monkeypatch.setattr(Metadata, "pyproject_path", pyproject_file)

    metadata = Metadata()
    # Only known targets are kept.
    assert metadata.unstable_targets == {"linux-arm64"}


def test_nuitka_extra_args_default(tmp_path, monkeypatch):
    """Test that nuitka-extra-args defaults to an empty list."""
    monkeypatch.chdir(tmp_path)
    config = load_repomatic_config()
    assert config["nuitka-extra-args"] == []


def test_nuitka_extra_args_custom(tmp_path, monkeypatch):
    """Test that nuitka-extra-args reads custom values from pyproject.toml."""
    pyproject_content = """\
[project]
name = "test-project"
version = "1.0.0"

[tool.repomatic]
nuitka-extra-args = [
  "--include-data-files=my_pkg/data/*.json=my_pkg/data/",
  "--include-package-data=my_pkg",
]
"""
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text(pyproject_content)
    monkeypatch.setattr(Metadata, "pyproject_path", pyproject_file)

    metadata = Metadata()
    assert metadata.config["nuitka-extra-args"] == [
        "--include-data-files=my_pkg/data/*.json=my_pkg/data/",
        "--include-package-data=my_pkg",
    ]


def test_load_repomatic_config_defaults(tmp_path, monkeypatch):
    """Test that load_repomatic_config returns defaults when no pyproject.toml."""
    monkeypatch.chdir(tmp_path)
    config = load_repomatic_config()
    # All Config dataclass fields should be present with defaults.
    from dataclasses import fields as dc_fields

    for f in dc_fields(Config):
        key = f.name.replace("_", "-")
        assert key in config, f"Missing config key: {key}"
    assert config["test-plan-file"] == "./tests/cli-test-plan.yaml"
    assert config["timeout"] is None
    assert config["test-plan"] is None
    assert config["dependency-graph-output"] == "./docs/assets/dependencies.mmd"
    assert config["dependency-graph-all-groups"] is True
    assert config["dependency-graph-all-extras"] is True
    assert config["dependency-graph-no-groups"] == []
    assert config["dependency-graph-no-extras"] == []
    assert config["dependency-graph-level"] is None
    assert config["nuitka"] is True
    assert config["nuitka-extra-args"] == []
    assert config["extra-label-files"] == []
    assert config["extra-file-rules"] == ""
    assert config["extra-content-rules"] == ""
    assert config["workflow-sync"] is True
    assert config["workflow-sync-exclude"] == []


def test_load_repomatic_config_custom_values(tmp_path, monkeypatch):
    """Test that load_repomatic_config reads custom values from pyproject.toml."""
    pyproject_content = """\
[project]
name = "test-project"
version = "1.0.0"

[tool.repomatic]
timeout = 120
test-plan-file = "./custom/test-plan.yaml"
dependency-graph-output = "./custom/deps.mmd"
nuitka = false
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_content)
    monkeypatch.chdir(tmp_path)

    config = load_repomatic_config()
    assert config["timeout"] == 120
    assert config["test-plan-file"] == "./custom/test-plan.yaml"
    assert config["dependency-graph-output"] == "./custom/deps.mmd"
    assert config["nuitka"] is False


def test_load_repomatic_config_with_preloaded_data():
    """Test that load_repomatic_config accepts pre-parsed pyproject data."""
    data = {
        "tool": {
            "repomatic": {
                "timeout": 60,
            },
        },
    }
    config = load_repomatic_config(data)
    assert config["timeout"] == 60
    # Other defaults are still present.
    assert config["test-plan-file"] == "./tests/cli-test-plan.yaml"


def test_get_project_name_from_cwd(tmp_path, monkeypatch):
    """Test that get_project_name reads from pyproject.toml in CWD."""
    pyproject_content = """\
[project]
name = "my-package"
version = "1.0.0"
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_content)
    monkeypatch.chdir(tmp_path)

    assert get_project_name() == "my-package"


def test_get_project_name_missing_pyproject(tmp_path, monkeypatch):
    """Test that get_project_name returns None when no pyproject.toml."""
    monkeypatch.chdir(tmp_path)
    assert get_project_name() is None


def test_get_project_name_no_project_section(tmp_path, monkeypatch):
    """Test that get_project_name returns None when no [project] section."""
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\n")
    monkeypatch.chdir(tmp_path)
    assert get_project_name() is None


def test_get_project_name_with_preloaded_data():
    """Test that get_project_name accepts pre-parsed pyproject data."""
    data = {"project": {"name": "preloaded-pkg"}}
    assert get_project_name(data) == "preloaded-pkg"
