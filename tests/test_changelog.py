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

from textwrap import dedent

import pytest

from gha_utils.changelog import Changelog


SAMPLE_CHANGELOG = dedent(
    """\
    # Changelog

    ## [1.2.3 (unreleased)](https://github.com/user/repo/compare/v1.2.2...main)

    > [!IMPORTANT]
    > This version is not released yet and is under active development.

    - Add new feature.
    - Fix bug.

    ## [1.2.2 (2024-01-15)](https://github.com/user/repo/compare/v1.2.1...v1.2.2)

    - Previous release.
    """
)
"""Reusable changelog fixture for freeze tests."""


@pytest.mark.parametrize(
    ("version", "initial", "updated"),
    [
        ("1.1.1", None, "# Changelog"),
        ("1.1.1", "", "# Changelog"),
        (
            "1.2.1",
            dedent(
                """\
                # Changelog

                ## [1.2.1 (unreleased)](https://github.com/kdeldycke/extra-platforms/compare/v1.2.0...main)

                > [!IMPORTANT]
                > This version is not released yet and is under active development.

                - Fix changelog indention.


                """
            ),
            dedent(
                """\
                # Changelog

                ## [1.2.1 (unreleased)](https://github.com/kdeldycke/extra-platforms/compare/v1.2.0...main)

                > [!IMPORTANT]
                > This version is not released yet and is under active development.

                - Fix changelog indention."""
            ),
        ),
        (
            "1.0.0",
            dedent(
                """\
                # Changelog

                ## [1.0.0 (2024-08-20)](https://github.com/kdeldycke/extra-platforms/compare/v0.0.1...v1.0.0)

                - Add documentation.
                """
            ),
            dedent(
                """\
                # Changelog

                ## [1.0.0 (unreleased)](https://github.com/kdeldycke/extra-platforms/compare/v1.0.0...main)

                > [!IMPORTANT]
                > This version is not released yet and is under active development.

                ## [1.0.0 (2024-08-20)](https://github.com/kdeldycke/extra-platforms/compare/v0.0.1...v1.0.0)

                - Add documentation."""
            ),
        ),
    ],
)
def test_changelog_update(version, initial, updated):
    changelog = Changelog(initial, current_version=version)
    assert changelog.update() == updated


def test_set_release_date():
    """Test that (unreleased) is replaced with a date."""
    changelog = Changelog(SAMPLE_CHANGELOG)
    result = changelog.set_release_date("2026-02-14")

    assert result is True
    assert "(unreleased)" not in changelog.content
    assert "(2026-02-14)" in changelog.content
    # Only the first occurrence is replaced.
    assert changelog.content.count("2026-02-14") == 1


def test_set_release_date_already_released():
    """Test that nothing changes if no unreleased marker exists."""
    content = "# Changelog\n\n## [1.0.0 (2024-01-01)](https://example.com)\n"
    changelog = Changelog(content)
    result = changelog.set_release_date("2026-02-14")

    assert result is False
    assert changelog.content == content


def test_update_comparison_url():
    """Test that comparison URL is pinned to version tag."""
    changelog = Changelog(SAMPLE_CHANGELOG, current_version="1.2.3")
    result = changelog.update_comparison_url()

    assert result is True
    assert "...main)" not in changelog.content
    assert "...v1.2.3)" in changelog.content


def test_update_comparison_url_custom_branch():
    """Test comparison URL update with a non-default branch."""
    content = SAMPLE_CHANGELOG.replace("...main)", "...develop)")
    changelog = Changelog(content, current_version="1.2.3")
    result = changelog.update_comparison_url(default_branch="develop")

    assert result is True
    assert "...develop)" not in changelog.content
    assert "...v1.2.3)" in changelog.content


def test_remove_warning():
    """Test that the IMPORTANT warning block is removed."""
    changelog = Changelog(SAMPLE_CHANGELOG)
    result = changelog.remove_warning()

    assert result is True
    assert "[!IMPORTANT]" not in changelog.content
    assert "not released yet" not in changelog.content
    # Content after the warning is preserved.
    assert "- Add new feature." in changelog.content


def test_remove_warning_no_warning():
    """Test that nothing changes if no warning exists."""
    content = "# Changelog\n\n## [1.0.0 (2024-01-01)](url)\n\n- Change.\n"
    changelog = Changelog(content)
    result = changelog.remove_warning()

    assert result is False
    assert changelog.content == content


def test_freeze():
    """Test that freeze applies all three operations."""
    changelog = Changelog(SAMPLE_CHANGELOG, current_version="1.2.3")
    result = changelog.freeze(release_date="2026-02-14")

    assert result is True
    assert "(unreleased)" not in changelog.content
    assert "(2026-02-14)" in changelog.content
    assert "...main)" not in changelog.content
    assert "...v1.2.3)" in changelog.content
    assert "[!IMPORTANT]" not in changelog.content
    # Release notes are preserved.
    assert "- Add new feature." in changelog.content
    assert "- Fix bug." in changelog.content


def test_freeze_idempotent():
    """Test that freezing an already-frozen changelog is a no-op."""
    changelog = Changelog(SAMPLE_CHANGELOG, current_version="1.2.3")
    changelog.freeze(release_date="2026-02-14")
    frozen_content = changelog.content

    # Second freeze should not change anything.
    result = changelog.freeze(release_date="2026-02-14")
    assert result is False
    assert changelog.content == frozen_content


def test_freeze_file(tmp_path):
    """Test that freeze_file freezes a changelog on disk."""
    path = tmp_path / "changelog.md"
    path.write_text(SAMPLE_CHANGELOG, encoding="UTF-8")

    result = Changelog.freeze_file(path, version="1.2.3", release_date="2026-02-14")

    assert result is True
    content = path.read_text(encoding="UTF-8")
    assert "(unreleased)" not in content
    assert "(2026-02-14)" in content
    assert "...main)" not in content
    assert "...v1.2.3)" in content
    assert "[!IMPORTANT]" not in content
    assert "- Add new feature." in content


def test_freeze_file_already_released(tmp_path):
    """Test that freeze_file is a no-op for released changelogs."""
    path = tmp_path / "changelog.md"
    content = "# Changelog\n\n## [1.0.0 (2024-01-01)](https://example.com)\n"
    path.write_text(content, encoding="UTF-8")

    result = Changelog.freeze_file(path, version="1.0.0", release_date="2026-02-14")

    assert result is False
    assert path.read_text(encoding="UTF-8") == content


def test_freeze_file_missing(tmp_path):
    """Test that freeze_file handles missing files gracefully."""
    path = tmp_path / "nonexistent.md"
    result = Changelog.freeze_file(path, version="1.0.0", release_date="2026-02-14")
    assert result is False


def test_extract_version_url():
    """Test extracting URL for a specific released version."""
    changelog = Changelog(SAMPLE_CHANGELOG)
    url = changelog.extract_version_url("1.2.2")

    assert url == "https://github.com/user/repo/compare/v1.2.1...v1.2.2"


def test_extract_version_url_unreleased():
    """Test extracting URL for the unreleased version."""
    changelog = Changelog(SAMPLE_CHANGELOG)
    url = changelog.extract_version_url("1.2.3")

    assert url == "https://github.com/user/repo/compare/v1.2.2...main"


def test_extract_version_url_missing():
    """Test that missing version returns empty string."""
    changelog = Changelog(SAMPLE_CHANGELOG)
    url = changelog.extract_version_url("9.9.9")

    assert url == ""


def test_extract_version_notes():
    """Test extracting notes for a specific released version."""
    changelog = Changelog(SAMPLE_CHANGELOG)
    notes = changelog.extract_version_notes("1.2.2")

    assert "- Previous release." in notes


def test_extract_version_notes_unreleased():
    """Test extracting notes for the unreleased version."""
    changelog = Changelog(SAMPLE_CHANGELOG)
    notes = changelog.extract_version_notes("1.2.3")

    assert "[!IMPORTANT]" in notes
    assert "- Add new feature." in notes
    assert "- Fix bug." in notes


def test_extract_version_notes_missing():
    """Test that missing version returns empty string."""
    changelog = Changelog(SAMPLE_CHANGELOG)
    notes = changelog.extract_version_notes("9.9.9")

    assert notes == ""
