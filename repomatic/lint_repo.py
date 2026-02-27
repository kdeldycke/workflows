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

from .github.actions import AnnotationLevel, emit_annotation
from .github.gh import run_gh_command
from .renovate import check_dependabot_config_absent


def get_repo_metadata(repo: str) -> dict[str, str | None]:
    """Fetch repository metadata from GitHub API.

    :param repo: Repository in 'owner/repo' format.
    :return: Dictionary with 'homepageUrl' and 'description' keys.
    """
    try:
        output = run_gh_command([
            "repo",
            "view",
            repo,
            "--json",
            "homepageUrl,description",
        ])
        data = json.loads(output)
        return {
            "homepageUrl": data.get("homepageUrl") or None,
            "description": data.get("description") or None,
        }
    except RuntimeError as e:
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


def check_topics_subset_of_keywords(
    repo: str,
    keywords: list[str] | None = None,
) -> tuple[str | None, str]:
    """Check that GitHub repo topics are a subset of pyproject.toml keywords.

    :param repo: Repository in 'owner/repo' format.
    :param keywords: Keywords from pyproject.toml. If ``None``, check is skipped.
    :return: Tuple of (warning_message or None, info_message).
    """
    if not keywords:
        return None, "Topics check: skipped (no keywords in pyproject.toml)"

    try:
        output = run_gh_command(["api", f"repos/{repo}", "--jq", ".topics[]"])
    except RuntimeError as e:
        logging.warning(f"Could not fetch GitHub topics: {e}")
        return None, "Topics check: skipped (could not fetch GitHub topics)"

    topics = {t.strip() for t in output.splitlines() if t.strip()}
    if not topics:
        return None, "Topics check: skipped (no GitHub topics set)"

    extra = sorted(topics - set(keywords))
    if extra:
        msg = (
            f"GitHub topics not in pyproject.toml keywords: {', '.join(extra)}. "
            "Add them to [project] keywords or remove from repo topics."
        )
        return msg, msg
    return None, f"All {len(topics)} GitHub topics are in pyproject.toml keywords."


def run_repo_lint(
    package_name: str | None = None,
    repo_name: str | None = None,
    is_sphinx: bool = False,
    project_description: str | None = None,
    keywords: list[str] | None = None,
    repo: str | None = None,
) -> int:
    """Run all repository lint checks.

    Emits GitHub Actions annotations for each check result.

    :param package_name: The Python package name.
    :param repo_name: The repository name.
    :param is_sphinx: Whether the project uses Sphinx documentation.
    :param project_description: Description from pyproject.toml.
    :param keywords: Keywords list from pyproject.toml.
    :param repo: Repository in 'owner/repo' format.
    :return: Exit code (0 for success, 1 for errors).
    """
    fatal_error = False

    # Check 1: Dependabot config file (fatal).
    passed, msg = check_dependabot_config_absent()
    if passed:
        print(f"✓ {msg}")
    else:
        emit_annotation(AnnotationLevel.ERROR, msg)
        print(f"✗ {msg}")
        fatal_error = True

    # Fetch repo metadata once if we need it.
    repo_metadata: dict[str, str | None] | None = None
    if is_sphinx or project_description:
        if repo:
            repo_metadata = get_repo_metadata(repo)
        else:
            logging.warning("No repo specified, skipping API-based checks.")
            repo_metadata = {"homepageUrl": None, "description": None}

    # Check 2: Package name vs repo name.
    if package_name and repo_name:
        warning, msg = check_package_name_vs_repo(package_name, repo_name)
        if warning:
            emit_annotation(AnnotationLevel.WARNING, warning)
        print(f"{'⚠' if warning else '✓'} {msg}")

    # Check 3: Website for Sphinx projects.
    if is_sphinx:
        homepage_url = repo_metadata.get("homepageUrl") if repo_metadata else None
        warning, msg = check_website_for_sphinx(repo or "", is_sphinx, homepage_url)
        if warning:
            emit_annotation(AnnotationLevel.WARNING, warning)
        print(f"{'⚠' if warning else '✓'} {msg}")

    # Check 4: Description matches (fatal).
    if project_description:
        repo_description = repo_metadata.get("description") if repo_metadata else None
        error, msg = check_description_matches(
            repo or "", project_description, repo_description
        )
        if error:
            emit_annotation(AnnotationLevel.ERROR, error)
            fatal_error = True
        print(f"{'✗' if error else '✓'} {msg}")

    # Check 5: GitHub topics are a subset of pyproject.toml keywords.
    if keywords and repo:
        warning, msg = check_topics_subset_of_keywords(repo, keywords)
        if warning:
            emit_annotation(AnnotationLevel.WARNING, warning)
        print(f"{'⚠' if warning else '✓'} {msg}")

    return 1 if fatal_error else 0
