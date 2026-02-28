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
from unittest.mock import call, patch

from repomatic.github.dev_release import (
    cleanup_dev_releases,
    delete_dev_release,
    delete_release_by_tag,
    sync_dev_release,
)

UNRELEASED_CHANGELOG = """\
# Changelog

## [`6.1.1.dev0` (unreleased)](https://github.com/user/repo/compare/v6.1.0...main)

> [!WARNING]
> This version is **not released yet** and is under active development.

- New feature in progress.

## [`6.1.0` (2026-02-26)](https://github.com/user/repo/compare/v6.0.1...v6.1.0)

- Released feature.
"""

RELEASED_ONLY_CHANGELOG = """\
# Changelog

## [`6.1.0` (2026-02-26)](https://github.com/user/repo/compare/v6.0.1...v6.1.0)

- Released feature.

## [`6.0.1` (2026-02-24)](https://github.com/user/repo/compare/v6.0.0...v6.0.1)

- Bug fix.
"""


# --- sync_dev_release() tests ---


def test_sync_dev_release_dry_run(tmp_path):
    """Dry-run reports without calling gh."""
    changelog_path = tmp_path / "changelog.md"
    changelog_path.write_text(UNRELEASED_CHANGELOG, encoding="UTF-8")

    with patch(
        "repomatic.github.dev_release.run_gh_command",
    ) as mock_gh:
        result = sync_dev_release(
            changelog_path,
            "6.1.1.dev0",
            "user/repo",
            dry_run=True,
        )

    assert result is True
    mock_gh.assert_not_called()


def test_sync_dev_release_live(tmp_path):
    """Live mode cleans up existing releases and creates new draft pre-release."""
    changelog_path = tmp_path / "changelog.md"
    changelog_path.write_text(UNRELEASED_CHANGELOG, encoding="UTF-8")

    # gh release list returns no existing dev releases.
    with patch(
        "repomatic.github.dev_release.run_gh_command",
        side_effect=[json.dumps([]), None],
    ) as mock_gh:
        result = sync_dev_release(
            changelog_path,
            "6.1.1.dev0",
            "user/repo",
            dry_run=False,
        )

    assert result is True
    # First call: list releases for cleanup.
    assert mock_gh.call_args_list[0] == call([
        "release",
        "list",
        "--json",
        "tagName",
        "--repo",
        "user/repo",
    ])
    # Second call: create new draft pre-release.
    create_call = mock_gh.call_args_list[1]
    assert create_call[0][0][:3] == ["release", "create", "v6.1.1.dev0"]
    assert "--draft" in create_call[0][0]
    assert "--prerelease" in create_call[0][0]
    assert "--target" in create_call[0][0]


def test_sync_dev_release_cleans_stale_releases(tmp_path):
    """Stale dev releases from previous versions are cleaned up."""
    changelog_path = tmp_path / "changelog.md"
    changelog_path.write_text(UNRELEASED_CHANGELOG, encoding="UTF-8")

    # gh release list returns a stale dev release from a previous version.
    release_list = json.dumps([
        {"tagName": "v6.0.1.dev0"},
        {"tagName": "v6.1.0"},
    ])
    with patch(
        "repomatic.github.dev_release.run_gh_command",
        side_effect=[
            release_list,  # list releases
            None,  # delete v6.0.1.dev0
            None,  # create new release
        ],
    ) as mock_gh:
        result = sync_dev_release(
            changelog_path,
            "6.1.1.dev0",
            "user/repo",
            dry_run=False,
        )

    assert result is True
    # Should delete the stale dev release.
    assert mock_gh.call_args_list[1] == call([
        "release",
        "delete",
        "v6.0.1.dev0",
        "--cleanup-tag",
        "--yes",
        "--repo",
        "user/repo",
    ])
    # Should not delete the non-dev release.
    delete_tags = [
        c[0][0][2]
        for c in mock_gh.call_args_list
        if c[0][0][0:2] == ["release", "delete"]
    ]
    assert "v6.1.0" not in delete_tags


def test_sync_dev_release_empty_body(tmp_path):
    """Returns False when changelog section produces an empty body."""
    changelog_path = tmp_path / "changelog.md"
    # Version exists in changelog but has no content.
    changelog_path.write_text(RELEASED_ONLY_CHANGELOG, encoding="UTF-8")

    with patch(
        "repomatic.github.dev_release.run_gh_command",
    ) as mock_gh:
        result = sync_dev_release(
            changelog_path,
            "9.9.9",
            "user/repo",
            dry_run=False,
        )

    assert result is False
    mock_gh.assert_not_called()


def test_sync_dev_release_body_content(tmp_path):
    """Verifies the release body includes changelog changes."""
    changelog_path = tmp_path / "changelog.md"
    changelog_path.write_text(UNRELEASED_CHANGELOG, encoding="UTF-8")

    with patch(
        "repomatic.github.dev_release.run_gh_command",
        side_effect=[json.dumps([]), None],
    ) as mock_gh:
        sync_dev_release(
            changelog_path,
            "6.1.1.dev0",
            "user/repo",
            dry_run=False,
        )

    # The create call's --notes argument should contain changes.
    create_args = mock_gh.call_args_list[1][0][0]
    notes_idx = create_args.index("--notes")
    body = create_args[notes_idx + 1]
    assert "New feature in progress." in body


# --- cleanup_dev_releases() tests ---


def test_cleanup_dev_releases_deletes_all_dev_tags():
    """Deletes all releases whose tag ends with .dev0."""
    release_list = json.dumps([
        {"tagName": "v6.2.0.dev0"},
        {"tagName": "v6.1.1.dev0"},
        {"tagName": "v6.1.0"},
        {"tagName": "v6.0.1"},
    ])
    with patch(
        "repomatic.github.dev_release.run_gh_command",
        side_effect=[release_list, None, None],
    ) as mock_gh:
        cleanup_dev_releases("user/repo")

    # Should delete both dev releases, not the regular ones.
    assert mock_gh.call_count == 3
    assert mock_gh.call_args_list[1] == call([
        "release",
        "delete",
        "v6.2.0.dev0",
        "--cleanup-tag",
        "--yes",
        "--repo",
        "user/repo",
    ])
    assert mock_gh.call_args_list[2] == call([
        "release",
        "delete",
        "v6.1.1.dev0",
        "--cleanup-tag",
        "--yes",
        "--repo",
        "user/repo",
    ])


def test_cleanup_dev_releases_no_dev_releases():
    """No-op when no dev releases exist."""
    release_list = json.dumps([
        {"tagName": "v6.1.0"},
        {"tagName": "v6.0.1"},
    ])
    with patch(
        "repomatic.github.dev_release.run_gh_command",
        return_value=release_list,
    ) as mock_gh:
        cleanup_dev_releases("user/repo")

    # Only the list call, no deletions.
    mock_gh.assert_called_once()


def test_cleanup_dev_releases_list_failure():
    """Silently succeeds when release listing fails."""
    with patch(
        "repomatic.github.dev_release.run_gh_command",
        side_effect=RuntimeError("API error"),
    ):
        # Should not raise.
        cleanup_dev_releases("user/repo")


def test_cleanup_dev_releases_delete_failure():
    """Continues cleaning when individual deletions fail."""
    release_list = json.dumps([
        {"tagName": "v6.2.0.dev0"},
        {"tagName": "v6.1.1.dev0"},
    ])
    with patch(
        "repomatic.github.dev_release.run_gh_command",
        side_effect=[
            release_list,
            RuntimeError("immutable"),  # First delete fails.
            None,  # Second delete succeeds.
        ],
    ) as mock_gh:
        cleanup_dev_releases("user/repo")

    # Should attempt to delete both despite the first failure.
    assert mock_gh.call_count == 3


# --- delete_dev_release() tests ---


def test_delete_dev_release_success():
    """Calls gh release delete with correct arguments."""
    with patch(
        "repomatic.github.dev_release.run_gh_command",
    ) as mock_gh:
        delete_dev_release("6.1.1.dev0", "user/repo")

    mock_gh.assert_called_once_with([
        "release",
        "delete",
        "v6.1.1.dev0",
        "--cleanup-tag",
        "--yes",
        "--repo",
        "user/repo",
    ])


def test_delete_dev_release_missing():
    """Silently succeeds when no dev release exists."""
    with patch(
        "repomatic.github.dev_release.run_gh_command",
        side_effect=RuntimeError("release not found"),
    ):
        # Should not raise.
        delete_dev_release("6.1.1.dev0", "user/repo")


# --- delete_release_by_tag() tests ---


def test_delete_release_by_tag_success():
    """Calls gh release delete with the given tag."""
    with patch(
        "repomatic.github.dev_release.run_gh_command",
    ) as mock_gh:
        delete_release_by_tag("v6.1.1.dev0", "user/repo")

    mock_gh.assert_called_once_with([
        "release",
        "delete",
        "v6.1.1.dev0",
        "--cleanup-tag",
        "--yes",
        "--repo",
        "user/repo",
    ])


def test_delete_release_by_tag_immutable():
    """Silently succeeds for immutable published releases."""
    with patch(
        "repomatic.github.dev_release.run_gh_command",
        side_effect=RuntimeError("HTTP 422"),
    ):
        # Should not raise.
        delete_release_by_tag("v6.1.1.dev0", "user/repo")
