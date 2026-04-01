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
from .github.token import check_all_pat_permissions


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


def check_pat_repository_scope(repo: str) -> tuple[str | None, str]:
    """Check that the PAT is scoped to only the current repository.

    Fine-grained PATs should use **Only select repositories** to follow
    the principle of least privilege. This check detects tokens configured
    with **All repositories** access.

    Two strategies are tried in order:

    1. ``GET /installation/repositories`` — returns the repos the token
       can access, including a ``repository_selection`` field.
    2. Cross-repo probe — check ``permissions.push`` on another repo
       owned by the same user. If the token can push to a repo it should
       not have access to, it is over-scoped.

    :param repo: Repository in 'owner/repo' format.
    :return: Tuple of (warning_message or None, info_message).
    """
    # Strategy A: installation/repositories endpoint.
    try:
        output = run_gh_command([
            "api",
            "/installation/repositories",
            "--jq",
            ".repository_selection",
        ])
    except RuntimeError:
        logging.debug(
            "installation/repositories not available, trying cross-repo probe."
        )
    else:
        selection = output.strip()
        if selection == "all":
            msg = (
                "PAT has 'All repositories' access."
                " Scope it to 'Only select repositories' for least privilege."
            )
            return msg, msg
        return None, "PAT scope: correctly limited to selected repositories."

    # Strategy B: cross-repo probe.
    owner = repo.split("/", 1)[0]
    try:
        output = run_gh_command([
            "api",
            f"/users/{owner}/repos",
            "--jq",
            ".[].full_name",
            "-f",
            "per_page=10",
            "-f",
            "type=owner",
        ])
    except RuntimeError:
        return None, "PAT scope check: skipped (could not list owner repos)."

    other_repos = [
        r.strip() for r in output.splitlines() if r.strip() and r.strip() != repo
    ]
    if not other_repos:
        return None, "PAT scope check: skipped (no other repos to probe)."

    probe_repo = other_repos[0]
    try:
        output = run_gh_command([
            "api",
            f"repos/{probe_repo}",
            "--jq",
            ".permissions.push",
        ])
        if output.strip() == "true":
            msg = (
                f"PAT has push access to {probe_repo}."
                " Token is likely scoped to 'All repositories'"
                " instead of 'Only select repositories'."
            )
            return msg, msg
    except RuntimeError:
        return None, "PAT scope check: skipped (probe request failed)."

    return None, f"PAT scope: no push access to {probe_repo} (correctly scoped)."


def check_tag_protection_rules(repo: str) -> tuple[str | None, str]:
    """Check that no tag rulesets could block the ``create-tag`` workflow job.

    Tag rulesets that restrict creation or require status checks can prevent
    ``REPOMATIC_PAT`` (or ``GITHUB_TOKEN``) from pushing release tags. This
    check queries the repository rulesets API and warns when any ruleset
    targets tags.

    :param repo: Repository in 'owner/repo' format.
    :return: Tuple of (warning_message or None, info_message).
    """
    try:
        output = run_gh_command([
            "api",
            f"repos/{repo}/rulesets",
            "-f",
            "includes_parents=true",
        ])
    except RuntimeError:
        return None, "Tag protection check: skipped (could not query rulesets API)."

    try:
        rulesets = json.loads(output)
    except json.JSONDecodeError:
        return None, "Tag protection check: skipped (invalid JSON from rulesets API)."

    tag_rulesets = [
        r["name"]
        for r in rulesets
        if isinstance(r, dict)
        and r.get("target") == "tag"
        and r.get("enforcement") == "active"
    ]
    if tag_rulesets:
        names = ", ".join(tag_rulesets)
        msg = (
            f"Active tag rulesets found: {names}."
            " These may block the create-tag job from pushing release tags."
            " Ensure the REPOMATIC_PAT token is in the bypass list,"
            " or remove the rulesets."
        )
        return msg, msg
    return None, "No active tag rulesets found."


def check_branch_ruleset_on_default(repo: str) -> tuple[bool, str]:
    """Check that at least one active branch ruleset exists.

    Queries the same ``GET /repos/{repo}/rulesets`` endpoint as
    :func:`check_tag_protection_rules` and looks for active rulesets with
    ``target == "branch"``. The presence of any such ruleset is taken as
    evidence that the default branch is protected (restrict deletions and
    block force pushes).

    .. note::

        This is a heuristic: it does not verify the ruleset targets the
        default branch specifically, nor that it enables the exact rules
        recommended by the setup guide. A deeper check would require
        fetching each ruleset's conditions via
        ``GET /repos/{repo}/rulesets/{id}``, adding N+1 API calls.

    :param repo: Repository in 'owner/repo' format.
    :return: Tuple of (passed, message).
    """
    try:
        output = run_gh_command([
            "api",
            f"repos/{repo}/rulesets",
            "-f",
            "includes_parents=true",
        ])
    except RuntimeError:
        return False, "Branch ruleset check: skipped (could not query rulesets API)."

    try:
        rulesets = json.loads(output)
    except json.JSONDecodeError:
        return False, "Branch ruleset check: skipped (invalid JSON from rulesets API)."

    branch_rulesets = [
        r["name"]
        for r in rulesets
        if isinstance(r, dict)
        and r.get("target") == "branch"
        and r.get("enforcement") == "active"
    ]
    if branch_rulesets:
        names = ", ".join(branch_rulesets)
        return True, f"Active branch rulesets found: {names}."
    return False, "No active branch rulesets found protecting the default branch."


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

    # Check 4: GitHub topics are a subset of pyproject.toml keywords.
    if keywords and repo:
        warning, msg = check_topics_subset_of_keywords(repo, keywords)
        if warning:
            emit_annotation(AnnotationLevel.WARNING, warning)
        print(f"{'⚠' if warning else '✓'} {msg}")

    # Check 5: Funding file present when owner has GitHub Sponsors.
    if repo:
        warning, msg = check_funding_file(repo)
        if warning:
            emit_annotation(AnnotationLevel.WARNING, warning)
        print(f"{'⚠' if warning else '✓'} {msg}")

    # Check 6: Stale draft releases (warning).
    if repo:
        warning, msg = check_stale_draft_releases(repo)
        if warning:
            emit_annotation(AnnotationLevel.WARNING, warning)
        print(f"{'⚠' if warning else '✓'} {msg}")

    # Check 7: Tag protection rules (warning).
    if repo:
        warning, msg = check_tag_protection_rules(repo)
        if warning:
            emit_annotation(AnnotationLevel.WARNING, warning)
        print(f"{'⚠' if warning else '✓'} {msg}")

    # Check 8: Workflow permissions declared on custom-step workflows.
    for warning, msg in check_workflow_permissions():
        if warning:
            emit_annotation(AnnotationLevel.WARNING, warning)
        print(f"{'⚠' if warning else '✓'} {msg}")

    # PAT capability checks (only when REPOMATIC_PAT is configured).
    if not has_pat or not repo:
        if not has_pat:
            print("ℹ PAT capability checks: skipped (no REPOMATIC_PAT)")
        return 1 if fatal_error else 0

    results = check_all_pat_permissions(repo, sha)
    if not sha:
        print("ℹ Commit statuses check: skipped (no SHA provided)")

    for passed, msg in results.iter_results():
        if passed:
            print(f"✓ {msg}")
        else:
            emit_annotation(AnnotationLevel.ERROR, msg)
            print(f"✗ {msg}")
            fatal_error = True

    # Check PAT repository scope (warning, not fatal).
    warning, msg = check_pat_repository_scope(repo)
    if warning:
        emit_annotation(AnnotationLevel.WARNING, warning)
    print(f"{'⚠' if warning else '✓'} {msg}")

    return 1 if fatal_error else 0
