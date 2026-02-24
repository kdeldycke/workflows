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

import logging
from textwrap import dedent

import pytest

from repomatic.changelog import (
    Changelog,
    PyPIRelease,
    YANKED_ADMONITION,
    build_release_admonition,
    build_unavailable_admonition,
    lint_changelog_dates,
)


SAMPLE_CHANGELOG = dedent(
    """\
    # Changelog

    ## [1.2.3 (unreleased)](https://github.com/user/repo/compare/v1.2.2...main)

    > [!WARNING]
    > This version is **not released yet** and is under active development.

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

                > [!WARNING]
                > This version is **not released yet** and is under active development.

                - Fix changelog indention.


                """
            ),
            dedent(
                """\
                # Changelog

                ## [1.2.1 (unreleased)](https://github.com/kdeldycke/extra-platforms/compare/v1.2.0...main)

                > [!WARNING]
                > This version is **not released yet** and is under active development.

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

                > [!WARNING]
                > This version is **not released yet** and is under active development.

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
    """Test that the WARNING block is removed."""
    changelog = Changelog(SAMPLE_CHANGELOG)
    result = changelog.remove_warning()

    assert result is True
    assert "[!WARNING]" not in changelog.content
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
    assert "[!WARNING]" not in changelog.content
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
    assert "[!WARNING]" not in content
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

    assert "[!WARNING]" in notes
    assert "- Add new feature." in notes
    assert "- Fix bug." in notes


def test_extract_version_notes_missing():
    """Test that missing version returns empty string."""
    changelog = Changelog(SAMPLE_CHANGELOG)
    notes = changelog.extract_version_notes("9.9.9")

    assert notes == ""


MULTI_RELEASE_CHANGELOG = dedent(
    """\
    # Changelog

    ## [2.0.0 (unreleased)](https://github.com/user/repo/compare/v1.1.0...main)

    > [!WARNING]
    > This version is **not released yet** and is under active development.

    ## [1.1.0 (2026-02-10)](https://github.com/user/repo/compare/v1.0.0...v1.1.0)

    - Second release.

    ## [1.0.0 (2025-12-01)](https://github.com/user/repo/compare/v0.9.0...v1.0.0)

    - Initial release.
    """
)
"""Changelog with multiple released versions and one unreleased."""


def test_extract_all_releases():
    """Test extraction of multiple released versions."""
    changelog = Changelog(MULTI_RELEASE_CHANGELOG)
    releases = changelog.extract_all_releases()

    assert releases == [("1.1.0", "2026-02-10"), ("1.0.0", "2025-12-01")]


def test_extract_all_releases_no_releases():
    """Test extraction when only an unreleased version exists."""
    content = dedent(
        """\
        # Changelog

        ## [1.0.0 (unreleased)](https://github.com/user/repo/compare/v0.0.1...main)

        > [!WARNING]
        > This version is **not released yet** and is under active development.
        """
    )
    changelog = Changelog(content)
    releases = changelog.extract_all_releases()

    assert releases == []


def test_extract_all_releases_empty():
    """Test extraction from an empty changelog."""
    changelog = Changelog("# Changelog\n")
    releases = changelog.extract_all_releases()

    assert releases == []


def _pypi_mock(releases):
    """Build a monkeypatch-compatible mock for ``get_pypi_release_dates``."""
    return lambda pkg: {v: PyPIRelease(*args) for v, args in releases.items()}


def _github_mock(versions):
    """Build a monkeypatch-compatible mock for ``get_github_releases``."""
    return lambda repo_url: set(versions)


def test_lint_changelog_dates_pypi_all_match(tmp_path, monkeypatch):
    """Test that lint returns 0 when all PyPI dates match."""
    path = tmp_path / "changelog.md"
    path.write_text(MULTI_RELEASE_CHANGELOG, encoding="UTF-8")

    monkeypatch.setattr(
        "repomatic.changelog.get_pypi_release_dates",
        _pypi_mock({
            "1.1.0": ("2026-02-10", False),
            "1.0.0": ("2025-12-01", False),
        }),
    )
    monkeypatch.setattr(
        "repomatic.metadata.get_project_name",
        lambda: "my-package",
    )
    monkeypatch.setattr(
        "repomatic.changelog.get_github_releases",
        _github_mock(["1.1.0", "1.0.0"]),
    )

    assert lint_changelog_dates(path) == 0


def test_lint_changelog_dates_pypi_mismatch(tmp_path, monkeypatch):
    """Test that lint returns 1 when a PyPI date differs."""
    path = tmp_path / "changelog.md"
    path.write_text(MULTI_RELEASE_CHANGELOG, encoding="UTF-8")

    monkeypatch.setattr(
        "repomatic.changelog.get_pypi_release_dates",
        _pypi_mock({
            "1.1.0": ("2026-02-09", False),
            "1.0.0": ("2025-12-01", False),
        }),
    )
    monkeypatch.setattr(
        "repomatic.metadata.get_project_name",
        lambda: "my-package",
    )
    monkeypatch.setattr(
        "repomatic.changelog.get_github_releases",
        _github_mock(["1.1.0", "1.0.0"]),
    )

    assert lint_changelog_dates(path) == 1


def test_lint_changelog_dates_fallback_to_tags(tmp_path, monkeypatch):
    """Test that lint falls back to git tags when not on PyPI."""
    path = tmp_path / "changelog.md"
    path.write_text(MULTI_RELEASE_CHANGELOG, encoding="UTF-8")

    # PyPI returns empty dict (not published).
    monkeypatch.setattr(
        "repomatic.changelog.get_pypi_release_dates",
        lambda pkg: {},
    )
    monkeypatch.setattr(
        "repomatic.metadata.get_project_name",
        lambda: "my-package",
    )
    monkeypatch.setattr(
        "repomatic.git_ops.get_tag_date",
        lambda tag: {"v1.1.0": "2026-02-10", "v1.0.0": "2025-12-01"}.get(tag),
    )
    monkeypatch.setattr(
        "repomatic.changelog.get_github_releases",
        _github_mock([]),
    )

    assert lint_changelog_dates(path) == 0


def test_lint_changelog_dates_fallback_no_package(tmp_path, monkeypatch):
    """Test that lint falls back to git tags when no package name is detected."""
    path = tmp_path / "changelog.md"
    path.write_text(MULTI_RELEASE_CHANGELOG, encoding="UTF-8")

    monkeypatch.setattr(
        "repomatic.metadata.get_project_name",
        lambda: None,
    )
    monkeypatch.setattr(
        "repomatic.git_ops.get_tag_date",
        lambda tag: {"v1.1.0": "2026-02-10", "v1.0.0": "2025-12-01"}.get(tag),
    )
    monkeypatch.setattr(
        "repomatic.changelog.get_github_releases",
        _github_mock([]),
    )

    assert lint_changelog_dates(path) == 0


def test_lint_changelog_dates_warns_missing_pypi(tmp_path, monkeypatch, caplog):
    """Test that versions not on PyPI get a warning if they postdate the first
    PyPI release, and an info log if they predate it."""
    path = tmp_path / "changelog.md"
    path.write_text(MULTI_RELEASE_CHANGELOG, encoding="UTF-8")

    # Only the oldest version is on PyPI; 1.1.0 is an unexpected gap.
    monkeypatch.setattr(
        "repomatic.changelog.get_pypi_release_dates",
        _pypi_mock({"1.0.0": ("2025-12-01", False)}),
    )
    monkeypatch.setattr(
        "repomatic.metadata.get_project_name",
        lambda: "my-package",
    )
    monkeypatch.setattr(
        "repomatic.changelog.get_github_releases",
        _github_mock([]),
    )

    with caplog.at_level(logging.WARNING):
        # Should return 0: 1.0.0 matches, 1.1.0 warned but non-fatal.
        assert lint_changelog_dates(path) == 0

    assert "1.1.0: not found on PyPI" in caplog.text


def test_lint_changelog_dates_skips_pre_pypi(tmp_path, monkeypatch, caplog):
    """Test that versions older than the first PyPI release are skipped."""
    path = tmp_path / "changelog.md"
    path.write_text(MULTI_RELEASE_CHANGELOG, encoding="UTF-8")

    # Only the newest version is on PyPI; 1.0.0 predates publication.
    monkeypatch.setattr(
        "repomatic.changelog.get_pypi_release_dates",
        _pypi_mock({"1.1.0": ("2026-02-10", False)}),
    )
    monkeypatch.setattr(
        "repomatic.metadata.get_project_name",
        lambda: "my-package",
    )
    monkeypatch.setattr(
        "repomatic.changelog.get_github_releases",
        _github_mock([]),
    )

    with caplog.at_level(logging.INFO):
        assert lint_changelog_dates(path) == 0

    assert "predates PyPI" in caplog.text


def test_lint_fix_corrects_date(tmp_path, monkeypatch):
    """Test that --fix corrects mismatched dates in the changelog."""
    path = tmp_path / "changelog.md"
    path.write_text(MULTI_RELEASE_CHANGELOG, encoding="UTF-8")

    monkeypatch.setattr(
        "repomatic.changelog.get_pypi_release_dates",
        _pypi_mock({
            "1.1.0": ("2026-02-11", False),
            "1.0.0": ("2025-12-01", False),
        }),
    )
    monkeypatch.setattr(
        "repomatic.metadata.get_project_name",
        lambda: "my-package",
    )
    monkeypatch.setattr(
        "repomatic.changelog.get_github_releases",
        _github_mock(["1.1.0", "1.0.0"]),
    )

    # Mismatch on 1.1.0: changelog says 2026-02-10, PyPI says 2026-02-11.
    # fix=True corrects it in-place, so return 0 to let downstream steps proceed.
    result = lint_changelog_dates(path, fix=True)
    assert result == 0

    content = path.read_text(encoding="UTF-8")
    assert "(2026-02-11)" in content
    assert "(2026-02-10)" not in content


def test_lint_fix_adds_release_admonition(tmp_path, monkeypatch):
    """Test that --fix adds conditional release admonitions."""
    path = tmp_path / "changelog.md"
    path.write_text(MULTI_RELEASE_CHANGELOG, encoding="UTF-8")

    monkeypatch.setattr(
        "repomatic.changelog.get_pypi_release_dates",
        _pypi_mock({
            "1.1.0": ("2026-02-10", False),
            "1.0.0": ("2025-12-01", False),
        }),
    )
    monkeypatch.setattr(
        "repomatic.metadata.get_project_name",
        lambda: "my-package",
    )
    monkeypatch.setattr(
        "repomatic.changelog.get_github_releases",
        _github_mock(["1.1.0", "1.0.0"]),
    )

    lint_changelog_dates(path, fix=True)
    content = path.read_text(encoding="UTF-8")

    # Both sources available — NOTE only, no WARNINGs.
    assert "[🐍 PyPI](https://pypi.org/project/my-package/1.1.0/)" in content
    assert "[🐙 GitHub](https://github.com/user/repo/releases/tag/v1.1.0)" in content
    assert "is **not available** on" not in content
    # 1.0.0 is the first on both platforms — "first version" wording.
    assert "`1.0.0` is the *first version* available on" in content
    # 1.1.0 is not the first on either — normal wording.
    assert "`1.1.0` is available on" in content


def test_lint_fix_github_only(tmp_path, monkeypatch):
    """Test that --fix adds GitHub-only admonition when not on PyPI."""
    path = tmp_path / "changelog.md"
    path.write_text(MULTI_RELEASE_CHANGELOG, encoding="UTF-8")

    # 1.0.0 on PyPI, 1.1.0 only on GitHub (not on PyPI).
    monkeypatch.setattr(
        "repomatic.changelog.get_pypi_release_dates",
        _pypi_mock({"1.0.0": ("2025-12-01", False)}),
    )
    monkeypatch.setattr(
        "repomatic.metadata.get_project_name",
        lambda: "my-package",
    )
    monkeypatch.setattr(
        "repomatic.changelog.get_github_releases",
        _github_mock(["1.1.0", "1.0.0"]),
    )

    lint_changelog_dates(path, fix=True)
    content = path.read_text(encoding="UTF-8")

    # 1.1.0: GitHub only — NOTE for GitHub, WARNING for missing PyPI.
    assert "[🐙 GitHub](https://github.com/user/repo/releases/tag/v1.1.0)" in content
    assert "is **not available** on 🐍 PyPI." in content
    assert "my-package/1.1.0" not in content
    # 1.0.0: both sources, first on both — "first version" wording.
    assert "`1.0.0` is the *first version* available on" in content
    assert "[🐍 PyPI](https://pypi.org/project/my-package/1.0.0/)" in content
    assert "[🐙 GitHub](https://github.com/user/repo/releases/tag/v1.0.0)" in content


THREE_RELEASE_CHANGELOG = dedent(
    """\
    # Changelog

    ## [3.0.0 (unreleased)](https://github.com/user/repo/compare/v2.0.0...main)

    > [!WARNING]
    > This version is **not released yet** and is under active development.

    ## [2.0.0 (2026-02-10)](https://github.com/user/repo/compare/v1.0.0...v2.0.0)

    - Second release.

    ## [1.0.0 (2025-12-01)](https://github.com/user/repo/compare/v0.9.0...v1.0.0)

    - First release.

    ## [0.5.0 (2025-06-01)](https://github.com/user/repo/compare/v0.4.0...v0.5.0)

    - Pre-PyPI release.
    """
)
"""Changelog with three released versions for first-version testing."""


def test_lint_fix_first_version_admonition(tmp_path, monkeypatch):
    """Test that --fix uses 'first version' wording for inaugural releases."""
    path = tmp_path / "changelog.md"
    path.write_text(THREE_RELEASE_CHANGELOG, encoding="UTF-8")

    # 0.5.0: GitHub only (predates PyPI).
    # 1.0.0: first on both PyPI and GitHub.
    # 2.0.0: on both, but not first on either.
    monkeypatch.setattr(
        "repomatic.changelog.get_pypi_release_dates",
        _pypi_mock({
            "2.0.0": ("2026-02-10", False),
            "1.0.0": ("2025-12-01", False),
        }),
    )
    monkeypatch.setattr(
        "repomatic.metadata.get_project_name",
        lambda: "my-package",
    )
    monkeypatch.setattr(
        "repomatic.changelog.get_github_releases",
        _github_mock(["2.0.0", "1.0.0", "0.5.0"]),
    )

    lint_changelog_dates(path, fix=True)
    content = path.read_text(encoding="UTF-8")

    # 0.5.0: GitHub only, first on GitHub — "first version" wording.
    assert "`0.5.0` is the *first version* available on" in content
    assert "[🐙 GitHub](https://github.com/user/repo/releases/tag/v0.5.0)" in content
    # 1.0.0: first on PyPI but not first on GitHub — normal wording.
    assert "`1.0.0` is available on" in content
    # 2.0.0: not first on either — normal wording.
    assert "`2.0.0` is available on" in content


def test_lint_fix_pypi_only(tmp_path, monkeypatch):
    """Test that --fix adds PyPI NOTE and GitHub WARNING when only on PyPI."""
    path = tmp_path / "changelog.md"
    path.write_text(MULTI_RELEASE_CHANGELOG, encoding="UTF-8")

    # 1.1.0 on PyPI only, not on GitHub.
    monkeypatch.setattr(
        "repomatic.changelog.get_pypi_release_dates",
        _pypi_mock({
            "1.1.0": ("2026-02-10", False),
            "1.0.0": ("2025-12-01", False),
        }),
    )
    monkeypatch.setattr(
        "repomatic.metadata.get_project_name",
        lambda: "my-package",
    )
    monkeypatch.setattr(
        "repomatic.changelog.get_github_releases",
        _github_mock(["1.0.0"]),
    )

    lint_changelog_dates(path, fix=True)
    content = path.read_text(encoding="UTF-8")

    # 1.1.0: PyPI NOTE, GitHub WARNING.
    assert "[🐍 PyPI](https://pypi.org/project/my-package/1.1.0/)" in content
    assert "is **not available** on 🐙 GitHub." in content
    assert "releases/tag/v1.1.0" not in content
    # 1.0.0: both sources.
    assert "[🐍 PyPI](https://pypi.org/project/my-package/1.0.0/)" in content
    assert "[🐙 GitHub](https://github.com/user/repo/releases/tag/v1.0.0)" in content


def test_lint_fix_no_warning_predates_github(tmp_path, monkeypatch):
    """Test that --fix skips GitHub WARNING for versions predating the first
    GitHub release."""
    path = tmp_path / "changelog.md"
    path.write_text(MULTI_RELEASE_CHANGELOG, encoding="UTF-8")

    # Both on PyPI; only 1.1.0 on GitHub (1.0.0 predates GitHub releases).
    monkeypatch.setattr(
        "repomatic.changelog.get_pypi_release_dates",
        _pypi_mock({
            "1.1.0": ("2026-02-10", False),
            "1.0.0": ("2025-12-01", False),
        }),
    )
    monkeypatch.setattr(
        "repomatic.metadata.get_project_name",
        lambda: "my-package",
    )
    monkeypatch.setattr(
        "repomatic.changelog.get_github_releases",
        _github_mock(["1.1.0"]),
    )

    lint_changelog_dates(path, fix=True)
    content = path.read_text(encoding="UTF-8")

    # 1.0.0 predates first GitHub release (1.1.0) — no GitHub WARNING.
    assert "is **not available** on" not in content
    # 1.0.0: PyPI NOTE only (no GitHub link, no warning).
    assert "[🐍 PyPI](https://pypi.org/project/my-package/1.0.0/)" in content
    # 1.1.0: both sources.
    assert "[🐍 PyPI](https://pypi.org/project/my-package/1.1.0/)" in content
    assert "[🐙 GitHub](https://github.com/user/repo/releases/tag/v1.1.0)" in content


def test_lint_fix_adds_yanked_admonition(tmp_path, monkeypatch):
    """Test that --fix adds a CAUTION admonition for yanked releases."""
    path = tmp_path / "changelog.md"
    path.write_text(MULTI_RELEASE_CHANGELOG, encoding="UTF-8")

    monkeypatch.setattr(
        "repomatic.changelog.get_pypi_release_dates",
        _pypi_mock({
            "1.1.0": ("2026-02-10", True),
            "1.0.0": ("2025-12-01", False),
        }),
    )
    monkeypatch.setattr(
        "repomatic.metadata.get_project_name",
        lambda: "my-package",
    )
    monkeypatch.setattr(
        "repomatic.changelog.get_github_releases",
        _github_mock(["1.1.0", "1.0.0"]),
    )

    lint_changelog_dates(path, fix=True)
    content = path.read_text(encoding="UTF-8")

    assert YANKED_ADMONITION in content


def test_lint_fix_no_admonition_when_nowhere(tmp_path, monkeypatch):
    """Test that --fix adds WARNINGs for both platforms when version is on
    neither PyPI nor GitHub."""
    path = tmp_path / "changelog.md"
    path.write_text(MULTI_RELEASE_CHANGELOG, encoding="UTF-8")

    # 1.0.0 on PyPI; 1.1.0 on neither.
    monkeypatch.setattr(
        "repomatic.changelog.get_pypi_release_dates",
        _pypi_mock({"1.0.0": ("2025-12-01", False)}),
    )
    monkeypatch.setattr(
        "repomatic.metadata.get_project_name",
        lambda: "my-package",
    )
    monkeypatch.setattr(
        "repomatic.changelog.get_github_releases",
        _github_mock(["1.0.0"]),
    )

    lint_changelog_dates(path, fix=True)
    content = path.read_text(encoding="UTF-8")

    # 1.1.0: WARNING listing both missing platforms.
    assert ("is **not available** on 🐍 PyPI and 🐙 GitHub.") in content
    assert "releases/tag/v1.1.0" not in content
    assert "my-package/1.1.0" not in content
    # 1.0.0 has both.
    assert "[🐍 PyPI](https://pypi.org/project/my-package/1.0.0/)" in content


def test_lint_fix_idempotent(tmp_path, monkeypatch):
    """Test that running --fix twice produces the same result."""
    path = tmp_path / "changelog.md"
    path.write_text(MULTI_RELEASE_CHANGELOG, encoding="UTF-8")

    mock = _pypi_mock({
        "1.1.0": ("2026-02-10", False),
        "1.0.0": ("2025-12-01", False),
    })
    monkeypatch.setattr("repomatic.changelog.get_pypi_release_dates", mock)
    monkeypatch.setattr(
        "repomatic.metadata.get_project_name",
        lambda: "my-package",
    )
    monkeypatch.setattr(
        "repomatic.changelog.get_github_releases",
        _github_mock(["1.1.0", "1.0.0"]),
    )

    lint_changelog_dates(path, fix=True)
    first_content = path.read_text(encoding="UTF-8")

    lint_changelog_dates(path, fix=True)
    second_content = path.read_text(encoding="UTF-8")

    assert first_content == second_content


def test_fix_release_date():
    """Test fixing a specific version's date in the changelog."""
    changelog = Changelog(MULTI_RELEASE_CHANGELOG)
    result = changelog.fix_release_date("1.1.0", "2026-02-11")

    assert result is True
    assert "(2026-02-11)" in changelog.content
    assert "1.1.0 (2026-02-10)" not in changelog.content


def test_add_admonition_after_heading():
    """Test inserting an admonition after a version heading."""
    changelog = Changelog(MULTI_RELEASE_CHANGELOG)
    admonition = "> [!NOTE]\n> `1.1.0` is available on [🐍 PyPI](https://example.com)."
    result = changelog.add_admonition_after_heading("1.1.0", admonition)

    assert result is True
    assert admonition in changelog.content


def test_add_admonition_idempotent():
    """Test that adding the same admonition twice is a no-op."""
    changelog = Changelog(MULTI_RELEASE_CHANGELOG)
    admonition = "> [!NOTE]\n> `1.1.0` is available on [🐍 PyPI](https://example.com)."
    changelog.add_admonition_after_heading("1.1.0", admonition)
    result = changelog.add_admonition_after_heading("1.1.0", admonition)

    assert result is False


def test_remove_admonition_from_section():
    """Test removing an admonition block from a version section."""
    changelog = Changelog(MULTI_RELEASE_CHANGELOG)
    admonition = build_release_admonition(
        "1.0.0",
        github_url="https://github.com/user/repo/releases/tag/v1.0.0",
    )
    changelog.add_admonition_after_heading(
        "1.0.0",
        admonition,
        dedup_marker="is available on",
    )
    assert "is available on" in changelog.content

    result = changelog.remove_admonition_from_section(
        "1.0.0",
        "is available on",
    )

    assert result is True
    assert "is available on" not in changelog.content
    # Heading and content are preserved.
    assert "1.0.0" in changelog.content
    assert "Initial release." in changelog.content


def test_remove_admonition_no_match():
    """Test that removing a non-existent admonition is a no-op."""
    changelog = Changelog(MULTI_RELEASE_CHANGELOG)
    result = changelog.remove_admonition_from_section(
        "1.0.0",
        "is available on",
    )

    assert result is False


def test_strip_availability_admonitions():
    """Test that strip removes NOTE and WARNING availability admonitions while
    preserving the 'not released yet' WARNING and YANKED CAUTION."""
    content = dedent(
        """\
        # Changelog

        ## [2.0.0 (unreleased)](https://github.com/user/repo/compare/v1.1.0...main)

        > [!WARNING]
        > This version is **not released yet** and is under active development.

        ## [1.1.0 (2026-02-10)](https://github.com/user/repo/compare/v1.0.0...v1.1.0)

        > [!NOTE]
        > `1.1.0` is available on [🐍 PyPI](https://pypi.org/project/pkg/1.1.0/).

        > [!WARNING]
        > `1.1.0` is **not available** on 🐙 GitHub.

        - Second release.

        ## [1.0.0 (2025-12-01)](https://github.com/user/repo/compare/v0.9.0...v1.0.0)

        > [!NOTE]
        > `1.0.0` is the *first version* available on [🐍 PyPI](https://pypi.org/project/pkg/1.0.0/).

        > [!CAUTION]
        > This release has been [yanked from PyPI](https://docs.pypi.org/project-management/yanking/).

        - Initial release.
        """
    )
    changelog = Changelog(content)

    result = changelog.strip_availability_admonitions("1.1.0")
    assert result is True
    # Availability admonitions for 1.1.0 are removed.
    assert "`1.1.0` is available on" not in changelog.content
    assert "`1.1.0` is **not available**" not in changelog.content
    # Content is preserved.
    assert "- Second release." in changelog.content
    # Other versions' admonitions are untouched.
    assert "`1.0.0` is the *first version* available on" in changelog.content
    # "Not released yet" WARNING is preserved (uses "This version", not version string).
    assert "not released yet" in changelog.content
    # YANKED CAUTION is preserved (uses "This release has been").
    assert "yanked from PyPI" in changelog.content


def test_strip_availability_admonitions_no_match():
    """Test that strip is a no-op when no availability admonitions exist."""
    changelog = Changelog(MULTI_RELEASE_CHANGELOG)
    result = changelog.strip_availability_admonitions("1.1.0")
    assert result is False


def test_lint_fix_removes_stale_unavailable_warning(tmp_path, monkeypatch):
    """Test that --fix removes stale 'is **not available** on' warnings when
    the version becomes available."""
    # Pre-seed 1.0.0 with a stale unavailable warning.
    stale = build_unavailable_admonition(
        "1.0.0",
        missing_pypi=True,
    )
    content = MULTI_RELEASE_CHANGELOG.replace(
        "- Initial release.",
        stale + "\n\n- Initial release.",
    )
    path = tmp_path / "changelog.md"
    path.write_text(content, encoding="UTF-8")

    # Now 1.0.0 is on both PyPI and GitHub — stale warning should go.
    monkeypatch.setattr(
        "repomatic.changelog.get_pypi_release_dates",
        _pypi_mock({
            "1.1.0": ("2026-02-10", False),
            "1.0.0": ("2025-12-01", False),
        }),
    )
    monkeypatch.setattr(
        "repomatic.metadata.get_project_name",
        lambda: "my-package",
    )
    monkeypatch.setattr(
        "repomatic.changelog.get_github_releases",
        _github_mock(["1.1.0", "1.0.0"]),
    )

    lint_changelog_dates(path, fix=True)
    result = path.read_text(encoding="UTF-8")

    assert "is **not available** on" not in result
    # NOTE admonitions should be present.
    assert "[🐍 PyPI](https://pypi.org/project/my-package/1.0.0/)" in result
    assert "[🐙 GitHub](https://github.com/user/repo/releases/tag/v1.0.0)" in result
    assert "Initial release." in result
