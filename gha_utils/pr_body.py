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
        f" maintainers, to bump the {part} part of the version number."
        " Version bumps are scheduled daily and also triggered after"
        " releases. See the [`bump-versions` job documentation]"
        "(https://github.com/kdeldycke/workflows"
        "?tab=readme-ov-file"
        "#githubworkflowschangelogyaml-jobs) for details.\n"
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
        "This PR is ready to be merged. See the"
        " [`prepare-release` job documentation]"
        "(https://github.com/kdeldycke/workflows"
        "?tab=readme-ov-file"
        "#githubworkflowschangelogyaml-jobs) for details."
        " The [merge event will trigger]"
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


def generate_update_gitignore_prefix() -> str:
    """Generate the PR body prefix for a ``.gitignore`` update PR.

    :return: A markdown string describing the PR and available
        ``pyproject.toml`` configuration options.
    """
    return (
        "### Description\n"
        "\n"
        "Regenerates `.gitignore` from"
        " [gitignore.io](https://github.com/toptal/gitignore.io)"
        " templates. See the [`update-gitignore` job documentation]"
        "(https://github.com/kdeldycke/workflows"
        "?tab=readme-ov-file"
        "#githubworkflowsautofixyyaml-jobs) for details.\n"
        "\n"
        "### Configuration\n"
        "\n"
        "Customize `.gitignore` generation in your"
        " `pyproject.toml`:\n"
        "\n"
        "```toml\n"
        "[tool.gha-utils]\n"
        'gitignore-location = "./.gitignore"'
        "          # File path (default)\n"
        'gitignore-extra-categories = ["terraform", "go"]'
        "  # Extra gitignore.io categories\n"
        'gitignore-extra-content = "my-file.txt"'
        "            # Content appended at the end\n"
        "```\n"
        "\n"
        "---"
    )


_AUTOFIX_DOCS_URL = (
    "https://github.com/kdeldycke/workflows"
    "?tab=readme-ov-file"
    "#githubworkflowsautofixyaml-jobs"
)
"""Base URL for the ``autofix.yaml`` job documentation in the readme."""


def generate_format_python_prefix() -> str:
    """Generate the PR body prefix for a Python formatting PR.

    :return: A markdown string describing the formatting tools used.
    """
    return (
        "### Description\n"
        "\n"
        "Auto-formats Python files with"
        " [autopep8](https://github.com/hhatto/autopep8) (comment wrapping)"
        " and [Ruff](https://docs.astral.sh/ruff/) (linting and formatting)."
        " A `[tool.ruff]` section is auto-initialized in `pyproject.toml`"
        " if missing. See the [`format-python` job documentation]"
        f"({_AUTOFIX_DOCS_URL}) for details.\n"
        "\n"
        "---"
    )


def generate_format_pyproject_prefix() -> str:
    """Generate the PR body prefix for a ``pyproject.toml`` formatting PR.

    :return: A markdown string describing the formatting tool used.
    """
    return (
        "### Description\n"
        "\n"
        "Auto-formats `pyproject.toml` with"
        " [pyproject-fmt](https://github.com/tox-dev/pyproject-fmt)."
        " See the [`format-pyproject` job documentation]"
        f"({_AUTOFIX_DOCS_URL}) for details.\n"
        "\n"
        "---"
    )


def generate_format_markdown_prefix() -> str:
    """Generate the PR body prefix for a Markdown formatting PR.

    :return: A markdown string describing the formatting tool used.
    """
    return (
        "### Description\n"
        "\n"
        "Auto-formats Markdown files with"
        " [mdformat](https://github.com/hukkin/mdformat)"
        " and its plugins."
        " See the [`format-markdown` job documentation]"
        f"({_AUTOFIX_DOCS_URL}) for details.\n"
        "\n"
        "---"
    )


def generate_format_json_prefix() -> str:
    """Generate the PR body prefix for a JSON formatting PR.

    :return: A markdown string describing the formatting tool used.
    """
    return (
        "### Description\n"
        "\n"
        "Auto-formats JSON files with"
        " [Biome](https://biomejs.dev/)."
        " See the [`format-json` job documentation]"
        f"({_AUTOFIX_DOCS_URL}) for details.\n"
        "\n"
        "---"
    )


def generate_fix_typos_prefix() -> str:
    """Generate the PR body prefix for a typo-fixing PR.

    :return: A markdown string describing the typo-checking tool used.
    """
    return (
        "### Description\n"
        "\n"
        "Fixes typos detected by"
        " [typos](https://github.com/crate-ci/typos)."
        " See the [`fix-typos` job documentation]"
        f"({_AUTOFIX_DOCS_URL}) for details.\n"
        "\n"
        "---"
    )


def generate_sync_bumpversion_prefix() -> str:
    """Generate the PR body prefix for a bumpversion config sync PR.

    :return: A markdown string describing the sync operation.
    """
    return (
        "### Description\n"
        "\n"
        "Initializes the `[tool.bumpversion]` configuration in"
        " `pyproject.toml` from the bundled template."
        " See the [`sync-bumpversion` job documentation]"
        f"({_AUTOFIX_DOCS_URL}) for details.\n"
        "\n"
        "---"
    )


def generate_update_mailmap_prefix() -> str:
    """Generate the PR body prefix for a ``.mailmap`` update PR.

    :return: A markdown string describing the mailmap sync operation.
    """
    return (
        "### Description\n"
        "\n"
        "Synchronizes the `.mailmap` file with the project's Git"
        " contributors."
        " See the [`update-mailmap` job documentation]"
        f"({_AUTOFIX_DOCS_URL}) for details.\n"
        "\n"
        "---"
    )


def generate_update_deps_graph_prefix() -> str:
    """Generate the PR body prefix for a dependency graph update PR.

    :return: A markdown string describing the graph generation and
        available ``pyproject.toml`` configuration options.
    """
    return (
        "### Description\n"
        "\n"
        "Regenerates the Mermaid dependency graph from the `uv` lockfile."
        " See the [`update-deps-graph` job documentation]"
        f"({_AUTOFIX_DOCS_URL}) for details.\n"
        "\n"
        "### Configuration\n"
        "\n"
        "Customize dependency graph generation in your"
        " `pyproject.toml`:\n"
        "\n"
        "```toml\n"
        "[tool.gha-utils]\n"
        'dependency-graph-output = "docs/dependency-graph.md"'
        "  # Output file path\n"
        "```\n"
        "\n"
        "---"
    )


def generate_update_docs_prefix() -> str:
    """Generate the PR body prefix for a documentation update PR.

    :return: A markdown string describing the docs generation tools.
    """
    return (
        "### Description\n"
        "\n"
        "Regenerates API documentation with"
        " [sphinx-apidoc](https://www.sphinx-doc.org/en/master/"
        "man/sphinx-apidoc.html) and runs the project's"
        " `docs/docs_update.py` script if present."
        " See the [`update-docs` job documentation]"
        f"({_AUTOFIX_DOCS_URL}) for details.\n"
        "\n"
        "---"
    )


# No-arg templates that can be dispatched without additional CLI options.
NO_ARG_TEMPLATES = frozenset((
    "format-json",
    "format-markdown",
    "format-pyproject",
    "format-python",
    "fix-typos",
    "sync-bumpversion",
    "update-deps-graph",
    "update-docs",
    "update-gitignore",
    "update-mailmap",
))
"""Template names that require no extra CLI arguments (``--version``, ``--part``)."""


TEMPLATES = {
    "bump-version": generate_bump_version_prefix,
    "fix-typos": generate_fix_typos_prefix,
    "format-json": generate_format_json_prefix,
    "format-markdown": generate_format_markdown_prefix,
    "format-pyproject": generate_format_pyproject_prefix,
    "format-python": generate_format_python_prefix,
    "prepare-release": generate_prepare_release_prefix,
    "sync-bumpversion": generate_sync_bumpversion_prefix,
    "update-deps-graph": generate_update_deps_graph_prefix,
    "update-docs": generate_update_docs_prefix,
    "update-gitignore": generate_update_gitignore_prefix,
    "update-mailmap": generate_update_mailmap_prefix,
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
