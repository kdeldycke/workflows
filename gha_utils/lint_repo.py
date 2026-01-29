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

"""Repository linting for GitHub Actions workflows.

This module provides consistency checks for repository metadata,
including package names, website fields, and descriptions.
"""

from __future__ import annotations

import json
import logging
import subprocess

from .github import AnnotationLevel, emit_annotation


def get_repo_metadata(repo: str) -> dict[str, str | None]:
    """Fetch repository metadata from GitHub API.

    :param repo: Repository in 'owner/repo' format.
    :return: Dictionary with 'homepageUrl' and 'description' keys.
    """
    try:
        result = subprocess.run(
            [
                "gh",
                "repo",
                "view",
                repo,
                "--json",
                "homepageUrl,description",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        return {
            "homepageUrl": data.get("homepageUrl") or None,
            "description": data.get("description") or None,
        }
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to fetch repo metadata: {e}")
        return {"homepageUrl": None, "description": None}
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse repo metadata: {e}")
        return {"homepageUrl": None, "description": None}


def check_package_name_vs_repo(
    package_name: str | None, repo_name: str
) -> tuple[str | None, str]:
    """Check if package name matches repository name.

    :param package_name: The Python package name.
    :param repo_name: The repository name.
    :return: Tuple of (warning_message or None, info_message).
    """
    if not package_name:
        return None, "Package name check: skipped (no package name provided)"

    if package_name != repo_name:
        msg = (
            f"Package name '{package_name}' differs from repository name '{repo_name}'."
        )
        return msg, msg
    return None, f"Package name '{package_name}' matches repository name."


def check_website_for_sphinx(
    repo: str, is_sphinx: bool, homepage_url: str | None = None
) -> tuple[str | None, str]:
    """Check that Sphinx projects have a website set.

    :param repo: Repository in 'owner/repo' format.
    :param is_sphinx: Whether the project uses Sphinx documentation.
    :param homepage_url: The homepage URL from API (to avoid duplicate calls).
    :return: Tuple of (warning_message or None, info_message).
    """
    if not is_sphinx:
        return None, "Website check: skipped (not a Sphinx project)"

    if homepage_url is None:
        metadata = get_repo_metadata(repo)
        homepage_url = metadata.get("homepageUrl")

    if not homepage_url:
        msg = "Sphinx documentation detected but repository website field is not set."
        return msg, msg
    return None, f"Website field is set: {homepage_url}"


def check_description_matches(
    repo: str,
    project_description: str | None,
    repo_description: str | None = None,
) -> tuple[str | None, str]:
    """Check that repository description matches project description.

    :param repo: Repository in 'owner/repo' format.
    :param project_description: Description from pyproject.toml.
    :param repo_description: Description from API (to avoid duplicate calls).
    :return: Tuple of (error_message or None, info_message).
    """
    if not project_description:
        return None, "Description check: skipped (no project description provided)"

    if repo_description is None:
        metadata = get_repo_metadata(repo)
        repo_description = metadata.get("description")

    if project_description != repo_description:
        msg = (
            f"Repo description '{repo_description}' != "
            f"project description '{project_description}'."
        )
        return msg, msg
    return None, "Repository description matches project description."


def run_repo_lint(
    package_name: str | None = None,
    repo_name: str | None = None,
    is_sphinx: bool = False,
    project_description: str | None = None,
    repo: str | None = None,
) -> int:
    """Run all repository lint checks.

    Emits GitHub Actions annotations for each check result.

    :param package_name: The Python package name.
    :param repo_name: The repository name.
    :param is_sphinx: Whether the project uses Sphinx documentation.
    :param project_description: Description from pyproject.toml.
    :param repo: Repository in 'owner/repo' format.
    :return: Exit code (0 for success, 1 for errors).
    """
    fatal_error = False

    # Fetch repo metadata once if we need it.
    repo_metadata: dict[str, str | None] | None = None
    if is_sphinx or project_description:
        if repo:
            repo_metadata = get_repo_metadata(repo)
        else:
            logging.warning("No repo specified, skipping API-based checks.")
            repo_metadata = {"homepageUrl": None, "description": None}

    # Check 1: Package name vs repo name.
    if package_name and repo_name:
        warning, msg = check_package_name_vs_repo(package_name, repo_name)
        if warning:
            emit_annotation(AnnotationLevel.WARNING, warning)
        print(f"{'⚠' if warning else '✓'} {msg}")

    # Check 2: Website for Sphinx projects.
    if is_sphinx:
        homepage_url = repo_metadata.get("homepageUrl") if repo_metadata else None
        warning, msg = check_website_for_sphinx(repo or "", is_sphinx, homepage_url)
        if warning:
            emit_annotation(AnnotationLevel.WARNING, warning)
        print(f"{'⚠' if warning else '✓'} {msg}")

    # Check 3: Description matches (fatal).
    if project_description:
        repo_description = repo_metadata.get("description") if repo_metadata else None
        error, msg = check_description_matches(
            repo or "", project_description, repo_description
        )
        if error:
            emit_annotation(AnnotationLevel.ERROR, error)
            fatal_error = True
        print(f"{'✗' if error else '✓'} {msg}")

    return 1 if fatal_error else 0
