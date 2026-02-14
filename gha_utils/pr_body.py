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

"""Generate PR body with workflow metadata for auto-created pull requests.

Reads ``GITHUB_*`` environment variables to produce a collapsible ``<details>``
block containing a metadata table. This replaces the bash ``printf`` chain in the
``pr-metadata`` composite action with a readable Python template.
"""

from __future__ import annotations

import os

TYPE_CHECKING = False
if TYPE_CHECKING:
    pass


def extract_workflow_filename(workflow_ref: str) -> str:
    """Extract the workflow filename from ``GITHUB_WORKFLOW_REF``.

    :param workflow_ref: The full workflow reference, e.g.
        ``owner/repo/.github/workflows/name.yaml@refs/heads/branch``.
    :return: The workflow filename (e.g. ``name.yaml``), or an empty string
        if the reference is empty or malformed.
    """
    if not workflow_ref:
        return ""
    # Strip the @ref suffix, then take the basename.
    path_part = workflow_ref.split("@")[0]
    return path_part.rsplit("/", 1)[-1] if "/" in path_part else path_part


def generate_pr_metadata_block() -> str:
    """Generate a collapsible metadata block from GitHub Actions environment variables.

    Reads ``GITHUB_*`` environment variables and returns a markdown ``<details>``
    block containing a table of workflow metadata fields.

    :return: A markdown string with the metadata block.
    """
    run_id = os.getenv("GITHUB_RUN_ID", "")
    run_number = os.getenv("GITHUB_RUN_NUMBER", "")
    run_attempt = os.getenv("GITHUB_RUN_ATTEMPT", "")
    server_url = os.getenv("GITHUB_SERVER_URL", "")
    repository = os.getenv("GITHUB_REPOSITORY", "")
    job = os.getenv("GITHUB_JOB", "")
    sha = os.getenv("GITHUB_SHA", "")
    workflow_ref = os.getenv("GITHUB_WORKFLOW_REF", "")
    event_name = os.getenv("GITHUB_EVENT_NAME", "")
    actor = os.getenv("GITHUB_ACTOR", "")
    triggering_actor = os.getenv("GITHUB_TRIGGERING_ACTOR", "")
    ref_name = os.getenv("GITHUB_REF_NAME", "")

    workflow_file = extract_workflow_filename(workflow_ref)
    run_url = f"{server_url}/{repository}/actions/runs/{run_id}"
    workflow_url = (
        f"{server_url}/{repository}/blob/{sha}/.github/workflows/{workflow_file}"
    )

    rows = [
        f"| **Trigger** | `{event_name}` |",
        f"| **Actor** | @{actor} |",
    ]
    if triggering_actor and triggering_actor != actor:
        rows.append(f"| **Re-run by** | @{triggering_actor} |")
    rows += [
        f"| **Ref** | `{ref_name}` |",
        (f"| **Commit** | [`{sha[:8]}`]({server_url}/{repository}/commit/{sha}) |"),
        f"| **Job** | `{job}` |",
        f"| **Workflow** | [`{workflow_file}`]({workflow_url}) |",
        f"| **Run** | [#{run_number}.{run_attempt}]({run_url}) |",
    ]
    table = "\n".join(rows)

    return (
        "<details><summary><code>Workflow metadata</code></summary>\n"
        "\n"
        "| Field | Value |\n"
        "|---|---|\n"
        f"{table}\n"
        "\n"
        "</details>\n"
    )


def _repo_url() -> str:
    """Build repository URL from ``GITHUB_SERVER_URL`` and ``GITHUB_REPOSITORY``."""
    server_url = os.getenv("GITHUB_SERVER_URL", "")
    repository = os.getenv("GITHUB_REPOSITORY", "")
    return f"{server_url}/{repository}"


def generate_bump_version_prefix(version: str, part: str) -> str:
    """Generate the PR body prefix for a version bump PR.

    :param version: The new version number (e.g. ``1.2.0``).
    :param part: The version part being bumped (e.g. ``minor``, ``major``).
    :return: A markdown string with description and merge instructions.
    """
    return (
        "### Description\n"
        "\n"
        "Ready to be merged into `main` branch, at the discretion of the"
        f" maintainers, to bump the {part} part of the version number.\n"
        "\n"
        f"### To bump version to v{version}\n"
        "\n"
        "1. **Click `Ready for review`** button below, to get this PR"
        " out of `Draft` mode\n"
        "\n"
        "1. **Click `Rebase and merge`** button below\n"
        "\n"
        "---"
    )


def generate_prepare_release_prefix(version: str) -> str:
    """Generate the PR body prefix for a release preparation PR.

    :param version: The current version being released (e.g. ``5.8.1``).
    :return: A markdown string with description and merge instructions.
    """
    repo_url = _repo_url()
    return (
        "### Description\n"
        "\n"
        "This PR is ready to be merged. The [merge event will trigger]"
        "(https://github.com/kdeldycke/workflows"
        "?tab=readme-ov-file#githubworkflowsreleaseyaml-jobs) the:\n"
        "\n"
        f"1. Creation of a [`v{version}` tag on `main`]"
        f"({repo_url}/tree/v{version}) branch\n"
        "\n"
        "1. Build and release of the Python package to"
        " [PyPI](https://pypi.org)\n"
        "\n"
        "1. Compilation of the project's binaries\n"
        "\n"
        f"1. Publication of a [GitHub `v{version}` release]"
        f"({repo_url}/releases/tag/v{version})"
        " with all artifacts above attached\n"
        "\n"
        f"### How-to release `v{version}`\n"
        "\n"
        "1. **Click `Ready for review`** button below, to get this PR"
        " out of `Draft` mode\n"
        "\n"
        "1. **Click `Rebase and merge`** button below\n"
        "\n"
        "   > [!CAUTION]\n"
        "   > Do not `Squash and merge`: [we need the 2 distinct commits]"
        "(https://github.com/kdeldycke/workflows/blob/main/"
        "claude.md#release-pr-freeze-and-unfreeze-commits) in this PR.\n"
        "\n"
        "---"
    )


TEMPLATES = {
    "bump-version": generate_bump_version_prefix,
    "prepare-release": generate_prepare_release_prefix,
}
"""Available PR body templates.

Keys are template names passed via ``--template``. Values are callables that
accept keyword arguments and return a markdown prefix string.
"""


def generate_refresh_tip() -> str:
    """Generate a tip admonition inviting users to refresh the PR manually.

    Uses ``GITHUB_SERVER_URL``, ``GITHUB_REPOSITORY``, and
    ``GITHUB_WORKFLOW_REF`` to build the workflow dispatch URL.

    :return: A GitHub-flavored markdown ``[!TIP]`` blockquote, or an empty
        string if the workflow reference is unavailable.
    """
    server_url = os.getenv("GITHUB_SERVER_URL", "")
    repository = os.getenv("GITHUB_REPOSITORY", "")
    workflow_ref = os.getenv("GITHUB_WORKFLOW_REF", "")
    workflow_file = extract_workflow_filename(workflow_ref)
    if not workflow_file:
        return ""
    workflow_dispatch_url = (
        f"{server_url}/{repository}/actions/workflows/{workflow_file}"
    )
    return (
        "> [!TIP]\n"
        "> If you suspect the PR content is outdated, "
        f"**[click `Run workflow`]({workflow_dispatch_url})** "
        "to refresh it manually before merging."
    )


def build_pr_body(prefix: str, metadata_block: str) -> str:
    """Concatenate prefix, refresh tip, and metadata block into a PR body.

    :param prefix: Content to prepend before the metadata block. Can be empty.
    :param metadata_block: The collapsible metadata block from
        :func:`generate_pr_metadata_block`.
    :return: The complete PR body string.
    """
    parts: list[str] = []
    if prefix:
        parts.append(prefix)
    tip = generate_refresh_tip()
    if tip:
        parts.append(tip)
    parts.append(metadata_block)
    return "\n\n\n".join(parts)
