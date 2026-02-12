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

"""Tests for repository linting module."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch


from gha_utils.lint_repo import (
    check_description_matches,
    check_package_name_vs_repo,
    check_website_for_sphinx,
    get_repo_metadata,
    run_repo_lint,
)


def test_successful_fetch():
    """Fetch and parse repo metadata."""
    with patch("gha_utils.lint_repo.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout='{"homepageUrl": "https://example.com", "description": "A package"}',
            returncode=0,
        )
        result = get_repo_metadata("owner/repo")
        assert result == {
            "homepageUrl": "https://example.com",
            "description": "A package",
        }


def test_empty_fields():
    """Handle empty fields."""
    with patch("gha_utils.lint_repo.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout='{"homepageUrl": "", "description": ""}',
            returncode=0,
        )
        result = get_repo_metadata("owner/repo")
        assert result == {"homepageUrl": None, "description": None}


def test_api_failure():
    """Handle API failure."""
    with patch("gha_utils.lint_repo.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "gh")
        result = get_repo_metadata("owner/repo")
        assert result == {"homepageUrl": None, "description": None}


def test_json_parse_error():
    """Handle JSON parse error."""
    with patch("gha_utils.lint_repo.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="not json", returncode=0)
        result = get_repo_metadata("owner/repo")
        assert result == {"homepageUrl": None, "description": None}


def test_names_match():
    """No warning when names match."""
    warning, msg = check_package_name_vs_repo("my-package", "my-package")
    assert warning is None
    assert "matches" in msg


def test_names_differ():
    """Warning when names differ."""
    warning, msg = check_package_name_vs_repo("my-package", "my-repo")
    assert warning is not None
    assert "differs" in warning
    assert "my-package" in warning
    assert "my-repo" in warning


def test_no_package_name():
    """Skip when no package name."""
    warning, msg = check_package_name_vs_repo(None, "my-repo")
    assert warning is None
    assert "skipped" in msg


def test_not_sphinx():
    """Skip when not a Sphinx project."""
    warning, msg = check_website_for_sphinx("owner/repo", is_sphinx=False)
    assert warning is None
    assert "skipped" in msg


def test_sphinx_with_website():
    """No warning when Sphinx project has website."""
    warning, msg = check_website_for_sphinx(
        "owner/repo", is_sphinx=True, homepage_url="https://docs.example.com"
    )
    assert warning is None
    assert "https://docs.example.com" in msg


def test_sphinx_without_website():
    """Warning when Sphinx project has no website."""
    warning, msg = check_website_for_sphinx(
        "owner/repo", is_sphinx=True, homepage_url=None
    )
    assert warning is not None
    assert "Sphinx" in warning
    assert "not set" in warning


def test_sphinx_fetches_metadata():
    """Fetch metadata when homepage_url not provided."""
    with patch("gha_utils.lint_repo.get_repo_metadata") as mock_get:
        mock_get.return_value = {"homepageUrl": "https://example.com"}
        warning, msg = check_website_for_sphinx("owner/repo", is_sphinx=True)
        assert warning is None
        mock_get.assert_called_once_with("owner/repo")


def test_descriptions_match():
    """No error when descriptions match."""
    error, msg = check_description_matches(
        "owner/repo",
        project_description="A cool package",
        repo_description="A cool package",
    )
    assert error is None
    assert "matches" in msg


def test_descriptions_differ():
    """Error when descriptions differ."""
    error, msg = check_description_matches(
        "owner/repo",
        project_description="A cool package",
        repo_description="Different description",
    )
    assert error is not None
    assert "!=" in error


def test_no_project_description():
    """Skip when no project description."""
    error, msg = check_description_matches(
        "owner/repo", project_description=None, repo_description="Something"
    )
    assert error is None
    assert "skipped" in msg


def test_fetches_metadata():
    """Fetch metadata when repo_description not provided."""
    with patch("gha_utils.lint_repo.get_repo_metadata") as mock_get:
        mock_get.return_value = {"description": "A cool package"}
        error, msg = check_description_matches(
            "owner/repo", project_description="A cool package"
        )
        assert error is None
        mock_get.assert_called_once_with("owner/repo")


def test_all_checks_pass(capsys):
    """Return 0 when all checks pass."""
    with patch("gha_utils.lint_repo.get_repo_metadata") as mock_get:
        mock_get.return_value = {
            "homepageUrl": "https://example.com",
            "description": "A cool package",
        }
        exit_code = run_repo_lint(
            package_name="my-package",
            repo_name="my-package",
            is_sphinx=True,
            project_description="A cool package",
            repo="owner/repo",
        )
        assert exit_code == 0


def test_description_mismatch(capsys):
    """Return 1 when description mismatches."""
    with patch("gha_utils.lint_repo.get_repo_metadata") as mock_get:
        mock_get.return_value = {
            "homepageUrl": None,
            "description": "Different description",
        }
        exit_code = run_repo_lint(
            project_description="A cool package",
            repo="owner/repo",
        )
        assert exit_code == 1
        captured = capsys.readouterr()
        assert "::error::" in captured.out


def test_package_name_warning(capsys):
    """Emit warning for package name mismatch but still pass."""
    exit_code = run_repo_lint(
        package_name="my-package",
        repo_name="different-repo",
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "::warning::" in captured.out


def test_website_warning(capsys):
    """Emit warning for missing website but still pass."""
    with patch("gha_utils.lint_repo.get_repo_metadata") as mock_get:
        mock_get.return_value = {"homepageUrl": None, "description": None}
        exit_code = run_repo_lint(
            is_sphinx=True,
            repo="owner/repo",
        )
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "::warning::" in captured.out


def test_minimal_run(capsys):
    """Run with no checks enabled."""
    exit_code = run_repo_lint()
    assert exit_code == 0
