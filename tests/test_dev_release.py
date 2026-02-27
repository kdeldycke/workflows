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

from unittest.mock import call, patch

from repomatic.github.dev_release import delete_dev_release, sync_dev_release

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
    """Live mode deletes existing release and creates new pre-release."""
    changelog_path = tmp_path / "changelog.md"
    changelog_path.write_text(UNRELEASED_CHANGELOG, encoding="UTF-8")

    with patch(
        "repomatic.github.dev_release.run_gh_command",
    ) as mock_gh:
        result = sync_dev_release(
            changelog_path,
            "6.1.1.dev0",
            "user/repo",
            dry_run=False,
        )

    assert result is True
    # First call: delete existing release.
    assert mock_gh.call_args_list[0] == call([
        "release",
        "delete",
        "v6.1.1.dev0",
        "--cleanup-tag",
        "--yes",
        "--repo",
        "user/repo",
    ])
    # Second call: create new pre-release.
    create_call = mock_gh.call_args_list[1]
    assert create_call[0][0][:3] == ["release", "create", "v6.1.1.dev0"]
    assert "--prerelease" in create_call[0][0]
    assert "--target" in create_call[0][0]


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
