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
including package names, website fields, descriptions, and funding configuration.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml

from .github.actions import AnnotationLevel, emit_annotation
from .github.gh import run_gh_command
from .renovate import (
    check_commit_statuses_permission,
    check_dependabot_config_absent,
    check_dependabot_security_disabled,
    check_renovate_config_exists,
)


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


def _funding_file_exists() -> bool:
    """Check whether a ``.github/FUNDING.yml`` file exists (case-insensitive).

    GitHub accepts any casing of the filename.
    """
    github_dir = Path(".github")
    if not github_dir.is_dir():
        return False
    return any(
        f.name.upper() == "FUNDING.YML" for f in github_dir.iterdir() if f.is_file()
    )


def check_funding_file(repo: str) -> tuple[str | None, str]:
    """Check that repos with GitHub Sponsors have a ``FUNDING.yml``.

    Skips forks (they inherit the parent's sponsor button) and owners
    without a Sponsors listing. Uses the GraphQL API because the REST API
    does not expose ``hasSponsorsListing``.

    :param repo: Repository in 'owner/repo' format.
    :return: Tuple of (warning_message or None, info_message).
    """
    if _funding_file_exists():
        return None, "Funding file found."

    owner, name = repo.split("/", 1)

    # Single GraphQL query for both isFork and hasSponsorsListing.
    query = (
        f"{{ repository(owner: {json.dumps(owner)}, name: {json.dumps(name)}) {{ isFork }}"
        f" repositoryOwner(login: {json.dumps(owner)}) {{"
        " ... on Sponsorable { hasSponsorsListing } } }"
    )

    try:
        output = run_gh_command(["api", "graphql", "--field", f"query={query}"])
    except RuntimeError as e:
        logging.warning(f"Could not query GitHub Sponsors status: {e}")
        return None, "Funding check: skipped (could not query GitHub API)"

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return None, "Funding check: skipped (could not parse API response)"

    repo_data = data.get("data", {}).get("repository", {})
    owner_data = data.get("data", {}).get("repositoryOwner", {})

    if repo_data.get("isFork"):
        return None, "Funding check: skipped (repository is a fork)"

    if not owner_data.get("hasSponsorsListing"):
        return None, "Funding check: skipped (owner has no GitHub Sponsors listing)"

    msg = (
        "Owner has GitHub Sponsors enabled but .github/FUNDING.yml is missing."
        " Create it to display the Sponsor button on the repository."
    )
    return msg, msg


def check_stale_draft_releases(repo: str) -> tuple[str | None, str]:
    """Check for draft releases that are not dev pre-releases.

    Draft releases whose tag does not end with ``.dev0`` are likely
    leftovers from abandoned or failed release attempts. The only
    expected drafts are the rolling dev pre-releases managed by
    ``sync-dev-release``.

    :param repo: Repository in 'owner/repo' format.
    :return: Tuple of (warning_message or None, info_message).
    """
    try:
        output = run_gh_command([
            "release",
            "list",
            "--json",
            "tagName,isDraft",
            "--repo",
            repo,
        ])
    except RuntimeError:
        return None, "Stale draft releases check: skipped (API call failed)."

    try:
        releases = json.loads(output)
    except json.JSONDecodeError:
        return None, "Stale draft releases check: skipped (invalid JSON)."

    stale_drafts = [
        r["tagName"]
        for r in releases
        if r.get("isDraft") and not r["tagName"].endswith(".dev0")
    ]
    if stale_drafts:
        tags = ", ".join(stale_drafts)
        msg = f"Stale draft releases found: {tags}. Delete these leftover drafts."
        return msg, msg
    return None, "No stale draft releases."


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


def check_pat_contents_permission(repo: str) -> tuple[bool, str]:
    """Check that the token has contents permission.

    Tests read access via ``GET /repos/{owner}/{repo}/contents/.github``.

    :param repo: Repository in 'owner/repo' format.
    :return: Tuple of (passed, message).
    """
    try:
        run_gh_command([
            "api",
            f"repos/{repo}/contents/.github",
            "--silent",
        ])
    except RuntimeError:
        msg = (
            "Cannot access repository contents. "
            "Ensure the token has 'Contents: Read and Write' permission."
        )
        return False, msg
    return True, "Contents: token has access"


def check_pat_issues_permission(repo: str) -> tuple[bool, str]:
    """Check that the token has issues permission.

    Tests read access via ``GET /repos/{owner}/{repo}/issues``.

    :param repo: Repository in 'owner/repo' format.
    :return: Tuple of (passed, message).
    """
    try:
        run_gh_command([
            "api",
            f"repos/{repo}/issues?per_page=1&state=all",
            "--silent",
        ])
    except RuntimeError:
        msg = (
            "Cannot access repository issues. "
            "Ensure the token has 'Issues: Read and Write' permission."
        )
        return False, msg
    return True, "Issues: token has access"


def check_pat_pull_requests_permission(repo: str) -> tuple[bool, str]:
    """Check that the token has pull requests permission.

    Tests read access via ``GET /repos/{owner}/{repo}/pulls``.

    :param repo: Repository in 'owner/repo' format.
    :return: Tuple of (passed, message).
    """
    try:
        run_gh_command([
            "api",
            f"repos/{repo}/pulls?per_page=1&state=all",
            "--silent",
        ])
    except RuntimeError:
        msg = (
            "Cannot access repository pull requests. "
            "Ensure the token has 'Pull requests: Read and Write' permission."
        )
        return False, msg
    return True, "Pull requests: token has access"


def check_pat_vulnerability_alerts_permission(repo: str) -> tuple[bool, str]:
    """Check that the token has Dependabot alerts permission and alerts are enabled.

    Tests access via ``GET /repos/{owner}/{repo}/vulnerability-alerts``.
    Returns 204 when alerts are enabled (pass). Fails on 403 (token lacks
    the ``vulnerability_alerts`` permission) or 404 (alerts not enabled).

    :param repo: Repository in 'owner/repo' format.
    :return: Tuple of (passed, message).
    """
    try:
        run_gh_command([
            "api",
            f"repos/{repo}/vulnerability-alerts",
            "--silent",
        ])
    except RuntimeError:
        msg = (
            "Cannot access vulnerability alerts. "
            "Either the token lacks 'Dependabot alerts: Read-only' permission "
            "or vulnerability alerts are not enabled on the repository."
        )
        return False, msg
    return True, "Dependabot alerts: token has access, alerts enabled"


def check_workflow_permissions() -> list[tuple[str | None, str]]:
    """Check that workflows with custom jobs declare ``permissions: {}``.

    Thin-caller workflows (all jobs use ``uses:`` to call a reusable workflow)
    inherit permissions from the called workflow and do not need a top-level
    ``permissions`` key. Workflows that define their own ``steps:`` should
    declare ``permissions: {}`` to follow the principle of least privilege.

    :return: List of (warning_message or None, info_message) tuples.
    """
    results: list[tuple[str | None, str]] = []
    workflows_dir = Path(".github/workflows")
    if not workflows_dir.is_dir():
        return [(None, "Workflow permissions check: skipped (no .github/workflows/)")]

    for wf_path in sorted(workflows_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(wf_path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as e:
            logging.warning(f"Could not parse {wf_path}: {e}")
            continue

        if not isinstance(data, dict) or "jobs" not in data:
            continue

        # Determine if this is a thin-caller workflow (all jobs use reusable
        # workflows via "uses:" with no "steps:").
        jobs = data.get("jobs", {})
        has_custom_steps = any(
            "steps" in job for job in jobs.values() if isinstance(job, dict)
        )
        if not has_custom_steps:
            continue

        if "permissions" not in data:
            msg = (
                f"Workflow {wf_path.name} defines custom job steps but has no"
                " top-level `permissions` key. Add `permissions: {{}}` for"
                " least-privilege security."
            )
            results.append((msg, msg))
        else:
            results.append((None, f"Workflow {wf_path.name}: permissions declared."))

    if not results:
        results.append((
            None,
            "Workflow permissions check: no custom-step workflows found.",
        ))
    return results


def run_repo_lint(
    package_name: str | None = None,
    repo_name: str | None = None,
    is_sphinx: bool = False,
    project_description: str | None = None,
    keywords: list[str] | None = None,
    repo: str | None = None,
    has_pat: bool = False,
    sha: str | None = None,
) -> int:
    """Run all repository lint checks.

    Emits GitHub Actions annotations for each check result.

    :param package_name: The Python package name.
    :param repo_name: The repository name.
    :param is_sphinx: Whether the project uses Sphinx documentation.
    :param project_description: Description from pyproject.toml.
    :param keywords: Keywords list from pyproject.toml.
    :param repo: Repository in 'owner/repo' format.
    :param has_pat: Whether ``GH_TOKEN`` contains ``REPOMATIC_PAT``.
    :param sha: Commit SHA for permission checks.
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

    # Check 2: Renovate config exists (fatal).
    passed, msg = check_renovate_config_exists()
    if passed:
        print(f"✓ {msg}")
    else:
        emit_annotation(AnnotationLevel.ERROR, msg)
        print(f"✗ {msg}")
        fatal_error = True

    # Check 3: Dependabot security updates disabled (fatal).
    if repo:
        passed, msg = check_dependabot_security_disabled(repo)
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

    # Check 4: Package name vs repo name.
    if package_name and repo_name:
        warning, msg = check_package_name_vs_repo(package_name, repo_name)
        if warning:
            emit_annotation(AnnotationLevel.WARNING, warning)
        print(f"{'⚠' if warning else '✓'} {msg}")

    # Check 5: Website for Sphinx projects.
    if is_sphinx:
        homepage_url = repo_metadata.get("homepageUrl") if repo_metadata else None
        warning, msg = check_website_for_sphinx(repo or "", is_sphinx, homepage_url)
        if warning:
            emit_annotation(AnnotationLevel.WARNING, warning)
        print(f"{'⚠' if warning else '✓'} {msg}")

    # Check 6: Description matches (fatal).
    if project_description:
        repo_description = repo_metadata.get("description") if repo_metadata else None
        error, msg = check_description_matches(
            repo or "", project_description, repo_description
        )
        if error:
            emit_annotation(AnnotationLevel.ERROR, error)
            fatal_error = True
        print(f"{'✗' if error else '✓'} {msg}")

    # Check 7: GitHub topics are a subset of pyproject.toml keywords.
    if keywords and repo:
        warning, msg = check_topics_subset_of_keywords(repo, keywords)
        if warning:
            emit_annotation(AnnotationLevel.WARNING, warning)
        print(f"{'⚠' if warning else '✓'} {msg}")

    # Check 8: Funding file present when owner has GitHub Sponsors.
    if repo:
        warning, msg = check_funding_file(repo)
        if warning:
            emit_annotation(AnnotationLevel.WARNING, warning)
        print(f"{'⚠' if warning else '✓'} {msg}")

    # Check 9: Stale draft releases (warning).
    if repo:
        warning, msg = check_stale_draft_releases(repo)
        if warning:
            emit_annotation(AnnotationLevel.WARNING, warning)
        print(f"{'⚠' if warning else '✓'} {msg}")

    # Check 10: Workflow permissions declared on custom-step workflows.
    for warning, msg in check_workflow_permissions():
        if warning:
            emit_annotation(AnnotationLevel.WARNING, warning)
        print(f"{'⚠' if warning else '✓'} {msg}")

    # PAT capability checks (only when REPOMATIC_PAT is configured).
    if not has_pat or not repo:
        if not has_pat:
            print("ℹ PAT capability checks: skipped (no REPOMATIC_PAT)")
        return 1 if fatal_error else 0

    pat_checks: list[tuple[bool, str]] = [
        check_pat_contents_permission(repo),
        check_pat_issues_permission(repo),
        check_pat_pull_requests_permission(repo),
        check_pat_vulnerability_alerts_permission(repo),
    ]
    if sha:
        pat_checks.append(check_commit_statuses_permission(repo, sha))
    else:
        print("ℹ Commit statuses check: skipped (no SHA provided)")

    for passed, msg in pat_checks:
        if passed:
            print(f"✓ {msg}")
        else:
            emit_annotation(AnnotationLevel.ERROR, msg)
            print(f"✗ {msg}")
            fatal_error = True

    return 1 if fatal_error else 0
