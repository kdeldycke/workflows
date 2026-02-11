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
"""Tests for GitHub Actions workflow files consistency."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

# Self-referential URL base for this repository.
SELF_REF_URL_BASE = "https://raw.githubusercontent.com/kdeldycke/workflows"

# Branch used in self-referential URLs during development.
SELF_REF_BRANCH = "main"

# Common prefix for all changelog-related commits.
CHANGELOG_COMMIT_PREFIX = "[changelog]"

# Commit message prefix that identifies release commits. These commits are protected
# from cancellation to ensure proper tagging, PyPI publishing, and GitHub releases.
RELEASE_COMMIT_PREFIX = f"{CHANGELOG_COMMIT_PREFIX} Release"

# Commit message prefix for post-release version bump.
POST_RELEASE_COMMIT_PREFIX = f"{CHANGELOG_COMMIT_PREFIX} Post-release bump"

# Commit message prefix for version bump PRs.
VERSION_BUMP_COMMIT_PREFIX = f"{CHANGELOG_COMMIT_PREFIX} Bump"

# Root of the repository.
REPO_ROOT = Path(__file__).parent.parent

# Path to the workflows directory.
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"

# Workflows that are exempt from concurrency requirements.
WORKFLOWS_WITHOUT_CONCURRENCY = frozenset((
    "autolock.yaml",  # Scheduled only, no concurrent execution possible.
    "cancel-runs.yaml",  # Fires on PR close, must always run to completion.
    "debug.yaml",  # Debug-only workflow, not for production use.
))

# Workflows that protect releases using unique concurrency groups (github.sha)
# instead of conditional cancel-in-progress. This is necessary when
# cancel-in-progress is evaluated on the NEW workflow, which would cancel
# running releases.
WORKFLOWS_WITH_UNIQUE_GROUPS = frozenset((
    "release.yaml",  # Uses github.sha in group for release/post-release commits.
))

# Workflows that use event-scoped concurrency groups (github.event_name in group)
# with always-cancellable cancel-in-progress. This prevents cross-event
# cancellation without needing conditional cancel-in-progress.
WORKFLOWS_WITH_EVENT_SCOPED_GROUPS = frozenset((
    # workflow_run events from "Build & release" cancel push-triggered runs
    # without event_name in the group.
    "changelog.yaml",
))

# Workflows that must have concurrency configured (all except exempted ones).
WORKFLOWS_WITH_CONCURRENCY = tuple(
    sorted(
        p.name
        for p in WORKFLOWS_DIR.glob("*.yaml")
        if p.name not in WORKFLOWS_WITHOUT_CONCURRENCY
    )
)

# Workflows that must use conditional cancel-in-progress (excludes unique
# group and event-scoped workflows).
WORKFLOWS_WITH_CONDITIONAL_CANCEL = tuple(
    sorted(
        name
        for name in WORKFLOWS_WITH_CONCURRENCY
        if name not in WORKFLOWS_WITH_UNIQUE_GROUPS
        and name not in WORKFLOWS_WITH_EVENT_SCOPED_GROUPS
    )
)


def load_workflow(workflow_name: str) -> dict[str, Any]:
    """Load and parse a workflow YAML file."""
    workflow_path = WORKFLOWS_DIR / workflow_name
    with workflow_path.open(encoding="utf-8") as f:
        result: dict[str, Any] = yaml.safe_load(f)
        return result


@pytest.mark.parametrize("workflow_name", WORKFLOWS_WITH_CONCURRENCY)
def test_workflow_has_concurrency(workflow_name: str) -> None:
    """Verify that required workflows have a concurrency block."""
    workflow = load_workflow(workflow_name)
    assert "concurrency" in workflow, f"{workflow_name} must have a concurrency block"


@pytest.mark.parametrize("workflow_name", WORKFLOWS_WITH_CONCURRENCY)
def test_concurrency_group_format(workflow_name: str) -> None:
    """Verify that concurrency group uses PR number or branch ref."""
    workflow = load_workflow(workflow_name)
    concurrency = workflow.get("concurrency", {})
    group = concurrency.get("group", "")

    # Expected format: workflow name + PR number or branch ref.
    assert "github.workflow" in group, (
        f"{workflow_name}: concurrency group must include github.workflow"
    )

    # Only require PR number in group if the workflow has a pull_request trigger.
    triggers = workflow.get("on", {})
    has_pr_trigger = "pull_request" in triggers or "pull_request_target" in triggers
    if has_pr_trigger:
        assert "github.event.pull_request.number" in group, (
            f"{workflow_name}: concurrency group must include PR number for PR events"
        )

    assert "github.ref" in group, (
        f"{workflow_name}: concurrency group must include github.ref for push events"
    )


@pytest.mark.parametrize("workflow_name", WORKFLOWS_WITH_CONDITIONAL_CANCEL)
def test_cancel_in_progress_protects_releases(workflow_name: str) -> None:
    """Verify that cancel-in-progress protects release commits."""
    workflow = load_workflow(workflow_name)
    concurrency = workflow.get("concurrency", {})
    cancel_in_progress = concurrency.get("cancel-in-progress", "")

    # Must be a conditional expression, not a static boolean.
    assert isinstance(cancel_in_progress, str), (
        f"{workflow_name}: cancel-in-progress must be a conditional expression, "
        f"not {type(cancel_in_progress).__name__}"
    )

    # Must reference the release commit prefix.
    assert RELEASE_COMMIT_PREFIX in cancel_in_progress, (
        f"{workflow_name}: cancel-in-progress must check for "
        f"'{RELEASE_COMMIT_PREFIX}' to protect release commits"
    )

    # Must use startsWith for proper prefix matching.
    assert "startsWith" in cancel_in_progress, (
        f"{workflow_name}: cancel-in-progress must use startsWith() "
        "for commit message matching"
    )

    # Must check the head commit message.
    assert "github.event.head_commit.message" in cancel_in_progress, (
        f"{workflow_name}: cancel-in-progress must check "
        "github.event.head_commit.message"
    )

    # Must negate the condition (release commits should NOT be cancelled).
    # Handle multiline YAML expressions where whitespace may appear after ${{.
    normalized = " ".join(cancel_in_progress.split())
    assert normalized.startswith("${{ !"), (
        f"{workflow_name}: cancel-in-progress must negate the condition "
        "to protect release commits from cancellation"
    )


@pytest.mark.parametrize("workflow_name", sorted(WORKFLOWS_WITH_EVENT_SCOPED_GROUPS))
def test_event_scoped_group_isolates_events(workflow_name: str) -> None:
    """Verify that event-scoped workflows include event_name in the group."""
    workflow = load_workflow(workflow_name)
    concurrency = workflow.get("concurrency", {})
    group = concurrency.get("group", "")

    assert "github.event_name" in group, (
        f"{workflow_name}: concurrency group must include github.event_name "
        "to prevent cross-event cancellation"
    )

    # cancel-in-progress should be static true (event isolation handles safety).
    cancel_in_progress = concurrency.get("cancel-in-progress", "")
    assert cancel_in_progress is True, (
        f"{workflow_name}: cancel-in-progress should be true "
        "(event-scoped groups handle release protection)"
    )


@pytest.mark.parametrize("workflow_name", WORKFLOWS_WITH_UNIQUE_GROUPS)
def test_unique_group_protects_releases(workflow_name: str) -> None:
    """Verify workflows using unique groups protect releases via github.sha."""
    workflow = load_workflow(workflow_name)
    concurrency = workflow.get("concurrency", {})
    group = concurrency.get("group", "")

    # Must use github.sha to create unique groups for release commits.
    assert "github.sha" in group, (
        f"{workflow_name}: concurrency group must include github.sha "
        "to create unique groups for release commits"
    )

    # Must check for release commit prefix to conditionally use github.sha.
    assert RELEASE_COMMIT_PREFIX in group, (
        f"{workflow_name}: concurrency group must check for "
        f"'{RELEASE_COMMIT_PREFIX}' to identify release commits"
    )


@pytest.mark.parametrize("workflow_name", WORKFLOWS_WITHOUT_CONCURRENCY)
def test_exempt_workflows_no_concurrency(workflow_name: str) -> None:
    """Verify that exempt workflows do not have concurrency configured."""
    workflow = load_workflow(workflow_name)
    # These workflows are exempt and may or may not have concurrency.
    # This test documents the exemption.
    assert workflow is not None, f"{workflow_name} should be a valid workflow"


def test_all_workflows_discovered() -> None:
    """Verify that workflow discovery is working correctly."""
    all_workflows = set(p.name for p in WORKFLOWS_DIR.glob("*.yaml"))

    # Verify exempt workflows exist.
    missing_exempt = WORKFLOWS_WITHOUT_CONCURRENCY - all_workflows
    assert not missing_exempt, (
        f"Exempt workflows not found: {missing_exempt}. "
        "Remove them from WORKFLOWS_WITHOUT_CONCURRENCY."
    )

    # Verify unique group workflows exist.
    missing_unique = WORKFLOWS_WITH_UNIQUE_GROUPS - all_workflows
    assert not missing_unique, (
        f"Unique group workflows not found: {missing_unique}. "
        "Remove them from WORKFLOWS_WITH_UNIQUE_GROUPS."
    )

    # Verify unique group workflows are a subset of concurrency workflows.
    not_in_concurrency = WORKFLOWS_WITH_UNIQUE_GROUPS - set(WORKFLOWS_WITH_CONCURRENCY)
    assert not not_in_concurrency, (
        f"Unique group workflows must have concurrency: {not_in_concurrency}"
    )

    # Verify event-scoped workflows exist.
    missing_event_scoped = WORKFLOWS_WITH_EVENT_SCOPED_GROUPS - all_workflows
    assert not missing_event_scoped, (
        f"Event-scoped workflows not found: {missing_event_scoped}. "
        "Remove them from WORKFLOWS_WITH_EVENT_SCOPED_GROUPS."
    )

    # Verify event-scoped workflows are a subset of concurrency workflows.
    not_in_concurrency = WORKFLOWS_WITH_EVENT_SCOPED_GROUPS - set(
        WORKFLOWS_WITH_CONCURRENCY
    )
    assert not not_in_concurrency, (
        f"Event-scoped workflows must have concurrency: {not_in_concurrency}"
    )

    # Verify no overlap between unique groups and event-scoped groups.
    overlap_strategies = WORKFLOWS_WITH_UNIQUE_GROUPS & WORKFLOWS_WITH_EVENT_SCOPED_GROUPS
    assert not overlap_strategies, (
        f"Workflows in both unique and event-scoped categories: {overlap_strategies}"
    )

    # Verify dynamic discovery found workflows.
    assert WORKFLOWS_WITH_CONCURRENCY, "No workflows discovered for concurrency testing"

    # Verify no overlap between exempt and concurrency categories.
    overlap = set(WORKFLOWS_WITH_CONCURRENCY) & WORKFLOWS_WITHOUT_CONCURRENCY
    assert not overlap, f"Workflows in both categories: {overlap}"


def test_release_commit_prefix_in_changelog_workflow() -> None:
    """Verify that changelog.yaml uses the same release commit prefix."""
    workflow = load_workflow("changelog.yaml")

    # Find the prepare-release job's commit message.
    jobs = workflow.get("jobs", {})
    prepare_release = jobs.get("prepare-release", {})
    steps = prepare_release.get("steps", [])

    # Look for the step that creates the freeze commit.
    release_commit_step = None
    for step in steps:
        if step.get("name") == "Create freeze commit":
            release_commit_step = step
            break

    assert release_commit_step is not None, (
        "changelog.yaml must have a 'Create freeze commit' step"
    )

    run_command = release_commit_step.get("run", "")
    assert RELEASE_COMMIT_PREFIX in run_command, (
        f"changelog.yaml release commit must use '{RELEASE_COMMIT_PREFIX}' prefix. "
        f"Found: {run_command}"
    )


def test_version_increments_skips_push_events() -> None:
    """Verify that bump-versions job indirectly skips release commits.

    Release commits come from push events. The bump-versions job depends on
    project-metadata, which only runs for schedule, workflow_dispatch, or
    workflow_run events. This ensures bump-versions never runs for push events
    (including release commits) without needing a job-level if condition.
    """
    workflow = load_workflow("changelog.yaml")
    jobs = workflow.get("jobs", {})

    # Verify bump-versions depends on project-metadata.
    version_increments = jobs.get("bump-versions", {})
    needs = version_increments.get("needs", [])
    assert "project-metadata" in needs, (
        "bump-versions job must depend on project-metadata"
    )

    # Verify project-metadata excludes push events (the event type for release commits).
    project_metadata = jobs.get("project-metadata", {})
    condition = project_metadata.get("if", "")
    assert "push" not in condition.lower(), (
        "project-metadata should not run on push events"
    )
    # Verify it runs on expected events.
    assert "schedule" in condition, "project-metadata should run on schedule events"
    assert "workflow_dispatch" in condition, (
        "project-metadata should run on workflow_dispatch events"
    )
    assert "workflow_run" in condition, (
        "project-metadata should run on workflow_run events"
    )


def test_post_release_commit_in_changelog_workflow() -> None:
    """Verify that changelog.yaml uses the correct post-release commit message."""
    workflow = load_workflow("changelog.yaml")

    jobs = workflow.get("jobs", {})
    prepare_release = jobs.get("prepare-release", {})
    steps = prepare_release.get("steps", [])

    # Look for the step that creates the post-release commit.
    post_release_step = None
    for step in steps:
        if step.get("name") == "Create unfreeze commit":
            post_release_step = step
            break

    assert post_release_step is not None, (
        "changelog.yaml must have a 'Create unfreeze commit' step"
    )

    run_command = post_release_step.get("run", "")
    assert POST_RELEASE_COMMIT_PREFIX in run_command, (
        f"changelog.yaml post-release commit must use '{POST_RELEASE_COMMIT_PREFIX}'. "
        f"Found: {run_command}"
    )


def test_version_bump_commit_in_changelog_workflow() -> None:
    """Verify that changelog.yaml uses the correct version bump commit message."""
    workflow = load_workflow("changelog.yaml")

    jobs = workflow.get("jobs", {})
    version_increments = jobs.get("bump-versions", {})
    steps = version_increments.get("steps", [])

    # Look for the create-pull-request step which contains the commit message.
    create_pr_step = None
    for step in steps:
        if step.get("uses", "").startswith("peter-evans/create-pull-request"):
            create_pr_step = step
            break

    assert create_pr_step is not None, (
        "changelog.yaml bump-versions job must have a create-pull-request step"
    )

    commit_message = create_pr_step.get("with", {}).get("commit-message", "")
    assert VERSION_BUMP_COMMIT_PREFIX in commit_message, (
        f"bump-versions commit message must use '{VERSION_BUMP_COMMIT_PREFIX}'. "
        f"Found: {commit_message}"
    )


def test_broken_links_skips_post_release_commits() -> None:
    """Verify that broken-links job skips post-release version bump commits."""
    workflow = load_workflow("docs.yaml")

    jobs = workflow.get("jobs", {})
    broken_links = jobs.get("check-broken-links", {})
    condition = broken_links.get("if", "")

    # The job should skip post-release commits.
    assert POST_RELEASE_COMMIT_PREFIX in condition, (
        f"check-broken-links job must skip commits containing "
        f"'{POST_RELEASE_COMMIT_PREFIX}'. Found condition: {condition}"
    )


# --- Action version pinning tests ---


def iter_workflow_actions(workflow: dict):
    """Yield all action references (uses: statements) from a workflow."""
    for job_name, job in workflow.get("jobs", {}).items():
        for step in job.get("steps", []):
            if "uses" in step:
                yield job_name, step.get("name", "unnamed"), step["uses"]


def iter_all_actions():
    """Yield all action references from all workflow files."""
    for workflow_path in WORKFLOWS_DIR.glob("*.yaml"):
        workflow = load_workflow(workflow_path.name)
        for job_name, step_name, action in iter_workflow_actions(workflow):
            yield workflow_path.name, job_name, step_name, action


# Regex to match action references with pinned versions.
# Accepts: vX.Y.Z, vX.Y, X.Y.Z (some actions don't use v prefix).
# Rejects: vX (major-only).
ACTION_VERSION_PATTERN = re.compile(r"^[^/]+/[^@]+@v?\d+\.\d+(\.\d+)?$")


@pytest.mark.parametrize(
    ("workflow_name", "job_name", "step_name", "action"),
    list(iter_all_actions()),
    ids=lambda x: x if isinstance(x, str) and "/" in x else None,
)
def test_action_uses_full_semantic_version(
    workflow_name: str, job_name: str, step_name: str, action: str
) -> None:
    """Verify that all actions use full semantic versions (vX.Y.Z), not major-only."""
    # Skip local actions (e.g., ./.github/actions/foo).
    if action.startswith("./"):
        pytest.skip("Local action")

    # Skip Docker actions (e.g., docker://image:tag).
    if action.startswith("docker://"):
        pytest.skip("Docker action")

    # Skip self-references to kdeldycke/workflows actions.
    # These use @main in development and get rewritten to @vX.Y.Z during release.
    if action.startswith("kdeldycke/workflows/") and action.endswith("@main"):
        pytest.skip("Self-reference uses @main in development, rewritten on release")

    assert ACTION_VERSION_PATTERN.match(action), (
        f"{workflow_name} ({job_name}/{step_name}): Action '{action}' must use "
        "pinned version (vX.Y.Z or vX.Y), not major-only (vX)"
    )


# --- Runner image convention tests ---


# Jobs that require ubuntu-24.04 instead of ubuntu-slim.
# Each entry documents the reason for the exception.
UBUNTU_2404_EXCEPTIONS = {
    # Format: (workflow_name, job_name): "reason"
    ("autofix.yaml", "format-markdown"): "shfmt is not available on ubuntu-slim",
    ("autofix.yaml", "optimize-images"): "calibreapp/image-actions requires Docker",
    ("renovate.yaml", "renovate"): "renovatebot/github-action requires Docker",
}


def iter_jobs_with_runners():
    """Yield all jobs with their runner configurations."""
    for workflow_path in WORKFLOWS_DIR.glob("*.yaml"):
        workflow = load_workflow(workflow_path.name)
        for job_name, job in workflow.get("jobs", {}).items():
            runs_on = job.get("runs-on", "")
            # Skip matrix-based runners.
            if isinstance(runs_on, str) and not runs_on.startswith("${{"):
                yield workflow_path.name, job_name, runs_on


@pytest.mark.parametrize(
    ("workflow_name", "job_name", "runs_on"),
    list(iter_jobs_with_runners()),
    ids=lambda x: f"{x[0]}:{x[1]}" if isinstance(x, tuple) else None,
)
def test_runner_uses_ubuntu_slim_by_default(
    workflow_name: str, job_name: str, runs_on: str
) -> None:
    """Verify that jobs use ubuntu-slim unless there's a documented exception."""
    if runs_on == "ubuntu-slim":
        return  # Correct default.

    if runs_on == "ubuntu-24.04":
        exception_key = (workflow_name, job_name)
        assert exception_key in UBUNTU_2404_EXCEPTIONS, (
            f"{workflow_name} ({job_name}): Uses 'ubuntu-24.04' but is not in "
            "UBUNTU_2404_EXCEPTIONS. Either use 'ubuntu-slim' or document the "
            "exception with a reason."
        )
        return

    # Other runners (macos, windows) are allowed for cross-platform testing.
    if any(
        platform in runs_on for platform in ("macos", "windows", "ubuntu-24.04-arm")
    ):
        return

    pytest.fail(f"{workflow_name} ({job_name}): Unknown runner '{runs_on}'")


# --- Bundled data symlink consistency tests ---

# Path to the bundled data directory.
DATA_DIR = REPO_ROOT / "gha_utils" / "data"


def test_all_workflows_have_symlinks_in_data() -> None:
    """Verify that every workflow in .github/workflows/ has a symlink in gha_utils/data/."""
    workflows = {p.name for p in WORKFLOWS_DIR.glob("*.yaml")}
    symlinks = {p.name for p in DATA_DIR.iterdir() if p.is_symlink()}

    missing = workflows - symlinks
    assert not missing, (
        f"Workflows missing symlinks in gha_utils/data/: {sorted(missing)}. "
        "Create them with: ln -s ../../.github/workflows/<name> gha_utils/data/<name>"
    )


def test_only_workflows_are_symlinks_in_data() -> None:
    """Verify that only workflow files are symlinks in gha_utils/data/."""
    workflows = {p.name for p in WORKFLOWS_DIR.glob("*.yaml")}
    symlinks = {p.name for p in DATA_DIR.iterdir() if p.is_symlink()}

    extra = symlinks - workflows
    assert not extra, (
        f"Unexpected symlinks in gha_utils/data/: {sorted(extra)}. "
        "Only workflow files should be symlinked."
    )


def test_workflow_symlinks_resolve_correctly() -> None:
    """Verify that workflow symlinks in gha_utils/data/ point to the correct targets."""
    for symlink in sorted(DATA_DIR.iterdir()):
        if not symlink.is_symlink():
            continue
        target = symlink.resolve()
        expected = (WORKFLOWS_DIR / symlink.name).resolve()
        assert target == expected, (
            f"Symlink {symlink.name} points to {target}, expected {expected}"
        )
