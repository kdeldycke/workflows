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
import textwrap

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

    return textwrap.dedent(f"""\
        <details><summary><code>Workflow metadata</code></summary>

        | Field | Value |
        |---|---|
        {table}

        </details>
    """)


def build_pr_body(prefix: str, metadata_block: str) -> str:
    """Concatenate a prefix and metadata block into a complete PR body.

    :param prefix: Content to prepend before the metadata block. Can be empty.
    :param metadata_block: The collapsible metadata block from
        :func:`generate_pr_metadata_block`.
    :return: The complete PR body string.
    """
    if prefix:
        return f"{prefix}\n\n\n{metadata_block}"
    return metadata_block
