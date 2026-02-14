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

"""Tests for PR body generation."""

from __future__ import annotations

import re
from importlib.resources import files
from pathlib import Path

import pytest

from gha_utils.pr_body import (
    build_pr_body,
    extract_workflow_filename,
    generate_pr_metadata_block,
    generate_refresh_tip,
    get_template_names,
    load_template,
    render_commit_message,
    render_template,
    render_title,
    template_args,
)

# Full set of GITHUB_* environment variables for testing.
GITHUB_ENV_VARS = {
    "GITHUB_RUN_ID": "123456789",
    "GITHUB_RUN_NUMBER": "42",
    "GITHUB_RUN_ATTEMPT": "1",
    "GITHUB_SERVER_URL": "https://github.com",
    "GITHUB_REPOSITORY": "owner/repo",
    "GITHUB_JOB": "autofix",
    "GITHUB_SHA": "abc12345def67890",
    "GITHUB_WORKFLOW_REF": "owner/repo/.github/workflows/autofix.yaml@refs/heads/main",
    "GITHUB_EVENT_NAME": "push",
    "GITHUB_ACTOR": "dependabot[bot]",
    "GITHUB_TRIGGERING_ACTOR": "dependabot[bot]",
    "GITHUB_REF_NAME": "main",
}


@pytest.mark.parametrize(
    ("workflow_ref", "expected"),
    [
        (
            "owner/repo/.github/workflows/autofix.yaml@refs/heads/main",
            "autofix.yaml",
        ),
        (
            "owner/repo/.github/workflows/release.yaml@refs/tags/v1.0.0",
            "release.yaml",
        ),
        ("", ""),
        ("just-a-filename.yaml", "just-a-filename.yaml"),
    ],
)
def test_extract_workflow_filename(workflow_ref, expected):
    """Extract workflow filename from various reference formats."""
    assert extract_workflow_filename(workflow_ref) == expected


def test_generate_metadata_block_all_vars(monkeypatch):
    """Metadata block includes all expected fields when env vars are set."""
    for key, value in GITHUB_ENV_VARS.items():
        monkeypatch.setenv(key, value)

    block = generate_pr_metadata_block()

    assert "<details>" in block
    assert "<summary><code>Workflow metadata</code></summary>" in block
    assert "| **Trigger** | `push` |" in block
    assert "| **Actor** | @dependabot[bot] |" in block
    assert "| **Ref** | `main` |" in block
    assert "| **Commit** |" in block
    assert "[`abc12345`]" in block
    assert "| **Job** | `autofix` |" in block
    assert "| **Workflow** | [`autofix.yaml`]" in block
    assert "| **Run** | [#42.1]" in block
    assert "</details>" in block
    # Same actor, no re-run row.
    assert "Re-run by" not in block


def test_generate_metadata_block_rerun(monkeypatch):
    """Re-run by row appears when triggering actor differs from actor."""
    for key, value in GITHUB_ENV_VARS.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("GITHUB_TRIGGERING_ACTOR", "admin-user")

    block = generate_pr_metadata_block()

    assert "| **Re-run by** | @admin-user |" in block


def test_generate_metadata_block_minimal_vars(monkeypatch):
    """Graceful degradation when most env vars are unset."""
    # Clear all GITHUB_ vars that might be set.
    for key in GITHUB_ENV_VARS:
        monkeypatch.delenv(key, raising=False)

    block = generate_pr_metadata_block()

    # Should still produce a valid details block without crashing.
    assert "<details>" in block
    assert "</details>" in block
    assert "| **Trigger** | `` |" in block


def test_generate_refresh_tip_with_workflow_ref(monkeypatch):
    """Tip includes workflow dispatch URL when env vars are set."""
    for key, value in GITHUB_ENV_VARS.items():
        monkeypatch.setenv(key, value)

    tip = generate_refresh_tip()

    assert "> [!TIP]" in tip
    assert "Run workflow" in tip
    assert "https://github.com/owner/repo/actions/workflows/autofix.yaml" in tip


def test_generate_refresh_tip_without_workflow_ref(monkeypatch):
    """Tip is empty when workflow ref is unavailable."""
    for key in GITHUB_ENV_VARS:
        monkeypatch.delenv(key, raising=False)

    assert generate_refresh_tip() == ""


def test_get_template_names():
    """All expected template names are discovered."""
    names = get_template_names()

    assert "bump-version" in names
    assert "prepare-release" in names
    assert "fix-typos" in names
    assert "format-json" in names
    assert "format-markdown" in names
    assert "format-pyproject" in names
    assert "format-python" in names
    assert "sync-bumpversion" in names
    assert "update-deps-graph" in names
    assert "update-docs" in names
    assert "update-gitignore" in names
    assert "update-mailmap" in names
    assert len(names) == 12


def test_load_template_frontmatter():
    """Frontmatter is parsed correctly from a parameterized template."""
    meta, body = load_template("bump-version")

    assert meta["args"] == ["version", "part"]
    assert body.startswith("### Description")


def test_load_template_title_only_frontmatter():
    """Static templates have frontmatter with title but no args."""
    meta, body = load_template("fix-typos")

    assert "title" in meta
    assert "args" not in meta
    assert body.startswith("### Description")


def test_template_args_parameterized():
    """Parameterized templates report their required arguments."""
    assert template_args("bump-version") == ["version", "part"]
    assert template_args("prepare-release") == ["version"]


def test_template_args_static():
    """Static templates report no required arguments."""
    assert template_args("fix-typos") == []
    assert template_args("format-json") == []


def test_render_title_static():
    """Static templates have a literal title."""
    assert render_title("fix-typos") == "Typo"
    assert render_title("format-python") == "Format Python"


def test_render_title_parameterized():
    """Parameterized templates substitute variables in the title."""
    title = render_title("bump-version", version="1.2.0", part="minor")
    assert title == "Bump minor version to `v1.2.0`"

    title = render_title("prepare-release", version="5.8.1")
    assert title == "Release `v5.8.1`"


def test_render_commit_message_falls_back_to_title():
    """Templates without explicit commit_message fall back to title."""
    assert render_commit_message("fix-typos") == "Typo"
    assert render_commit_message("format-markdown") == "Format Markdown"


def test_render_commit_message_explicit():
    """Templates without explicit commit_message fall back to title with backticks."""
    msg = render_commit_message("format-pyproject")
    assert msg == "Format `pyproject.toml`"

    msg = render_commit_message("update-gitignore")
    assert msg == "Update `.gitignore`"


def test_render_commit_message_parameterized():
    """Parameterized templates substitute variables in commit_message."""
    msg = render_commit_message("bump-version", version="1.2.0", part="minor")
    assert msg == "Bump minor version to `v1.2.0`"

    msg = render_commit_message("prepare-release", version="5.8.1")
    assert msg == "Release `v5.8.1`"


def test_render_bump_version():
    """Bump version template includes part, version, and merge instructions."""
    result = render_template("bump-version", version="1.2.0", part="minor")

    assert "bump the minor part" in result
    assert "### To bump version to v1.2.0" in result
    assert "Ready for review" in result
    assert "Rebase and merge" in result
    assert "bump-versions" in result
    assert "changelogyaml-jobs" in result


def test_render_prepare_release(monkeypatch):
    """Prepare release template includes version, links, and caution admonition."""
    for key, value in GITHUB_ENV_VARS.items():
        monkeypatch.setenv(key, value)

    result = render_template(
        "prepare-release",
        version="5.8.1",
    )

    assert "### How-to release `v5.8.1`" in result
    assert "`v5.8.1` tag on `main`" in result
    assert "`v5.8.1` release" in result
    assert "[!CAUTION]" in result
    assert "Squash and merge" in result
    assert "PyPI" in result
    assert "prepare-release" in result
    assert "changelogyaml-jobs" in result
    assert "releaseyaml-jobs" in result


def test_render_update_gitignore():
    """Update gitignore template includes description, config options, and docs link."""
    result = render_template("update-gitignore")

    assert "### Description" in result
    assert "gitignore.io" in result
    assert "update-gitignore" in result
    assert "### Configuration" in result
    assert "gitignore-extra-categories" in result
    assert "gitignore-extra-content" in result
    assert "gitignore-location" in result
    assert "[tool.gha-utils]" in result


def test_render_fix_typos():
    """Fix typos template includes description and docs link."""
    result = render_template("fix-typos")

    assert "### Description" in result
    assert "typos" in result
    assert "autofixyaml-jobs" in result


def test_render_format_json():
    """Format JSON template includes description and docs link."""
    result = render_template("format-json")

    assert "### Description" in result
    assert "Biome" in result
    assert "autofixyaml-jobs" in result


def test_render_format_markdown():
    """Format Markdown template includes description and docs link."""
    result = render_template("format-markdown")

    assert "### Description" in result
    assert "mdformat" in result
    assert "autofixyaml-jobs" in result


def test_render_format_pyproject():
    """Format pyproject template includes description and docs link."""
    result = render_template("format-pyproject")

    assert "### Description" in result
    assert "pyproject-fmt" in result
    assert "autofixyaml-jobs" in result


def test_render_format_python():
    """Format Python template includes description, tools, and docs link."""
    result = render_template("format-python")

    assert "### Description" in result
    assert "autopep8" in result
    assert "Ruff" in result
    assert "[tool.ruff]" in result
    assert "autofixyaml-jobs" in result


def test_render_sync_bumpversion():
    """Sync bumpversion template includes description and docs link."""
    result = render_template("sync-bumpversion")

    assert "### Description" in result
    assert "bumpversion" in result
    assert "autofixyaml-jobs" in result


def test_render_update_deps_graph():
    """Update deps graph template includes description, config options, and docs link."""
    result = render_template("update-deps-graph")

    assert "### Description" in result
    assert "Mermaid" in result
    assert "autofixyaml-jobs" in result
    assert "### Configuration" in result
    assert "dependency-graph-output" in result
    assert "[tool.gha-utils]" in result


def test_render_update_docs():
    """Update docs template includes description and docs link."""
    result = render_template("update-docs")

    assert "### Description" in result
    assert "sphinx-apidoc" in result
    assert "docs_update.py" in result
    assert "autofixyaml-jobs" in result


def test_render_update_mailmap():
    """Update mailmap template includes description and docs link."""
    result = render_template("update-mailmap")

    assert "### Description" in result
    assert ".mailmap" in result
    assert "autofixyaml-jobs" in result


def test_build_pr_body_with_prefix(monkeypatch):
    """Prefix is prepended with triple newline separator."""
    for key in GITHUB_ENV_VARS:
        monkeypatch.delenv(key, raising=False)

    metadata = "<details>metadata</details>"
    result = build_pr_body("Fix formatting issues.", metadata)

    assert result.startswith("Fix formatting issues.")
    assert "\n\n\n<details>metadata</details>" in result


def test_build_pr_body_with_tip(monkeypatch):
    """Tip is inserted between prefix and metadata when env vars are set."""
    for key, value in GITHUB_ENV_VARS.items():
        monkeypatch.setenv(key, value)

    metadata = "<details>metadata</details>"
    result = build_pr_body("Description.", metadata)

    assert result.startswith("Description.")
    assert "> [!TIP]" in result
    assert result.index("Description.") < result.index("[!TIP]")
    assert result.index("[!TIP]") < result.index("<details>")


def test_build_pr_body_empty_prefix(monkeypatch):
    """Empty prefix without tip returns just the metadata block."""
    for key in GITHUB_ENV_VARS:
        monkeypatch.delenv(key, raising=False)

    metadata = "<details>metadata</details>"
    result = build_pr_body("", metadata)

    assert result == metadata


# ---------------------------------------------------------------------------
# Template file policy validation
# ---------------------------------------------------------------------------

REFERENCE_WORKFLOWS = (
    ".github/workflows/autofix.yaml",
    ".github/workflows/changelog.yaml",
)
"""Workflow files that reference PR body templates via ``--template``."""


def _collect_template_references() -> set[str]:
    """Scan reference workflows for all ``--template <name>`` arguments."""
    repo_root = Path(__file__).resolve().parent.parent
    pattern = re.compile(r"--template\s+([\w-]+)")
    refs: set[str] = set()
    for rel_path in REFERENCE_WORKFLOWS:
        content = (repo_root / rel_path).read_text(encoding="UTF-8")
        refs.update(pattern.findall(content))
    return refs


def _template_package_items() -> list[tuple[str, str]]:
    """Return ``(filename, name)`` pairs for every file in the templates package."""
    items = []
    for item in files("gha_utils.templates").iterdir():
        filename = getattr(item, "name", str(item))
        if filename.startswith("__"):
            continue
        name = filename.removesuffix(".md") if filename.endswith(".md") else filename
        items.append((filename, name))
    return sorted(items)


@pytest.mark.parametrize(
    ("filename", "name"),
    _template_package_items(),
    ids=[pair[1] for pair in _template_package_items()],
)
def test_template_file_policy(filename, name):
    """Each template file must be a valid ``.md`` file with correct frontmatter."""
    # Must be a markdown file.
    assert filename.endswith(".md"), f"Template file {filename!r} is not a .md file"

    # Must parse without errors.
    meta, body = load_template(name)

    # Frontmatter must have a non-empty 'title'.
    assert "title" in meta, f"Template {name!r} is missing 'title' in frontmatter"
    assert meta["title"], f"Template {name!r} has an empty 'title'"

    # If frontmatter has 'args', it must be a list with matching $variables in body
    # or any other frontmatter field.
    if "args" in meta:
        assert isinstance(meta["args"], list), (
            f"Template {name!r} 'args' must be a list, got {type(meta['args'])}"
        )
        # Collect all string-valued frontmatter fields for variable reference checks.
        frontmatter_text = " ".join(
            v for k, v in meta.items() if k != "args" and isinstance(v, str)
        )
        for arg in meta["args"]:
            marker = f"${arg}"
            assert marker in body or marker in frontmatter_text, (
                f"Template {name!r} declares arg {arg!r}"
                f" but neither body nor frontmatter contains {marker}"
            )

    # Body must start with a markdown heading.
    assert body.startswith("###"), (
        f"Template {name!r} body must start with a '###' heading"
    )


def test_templates_match_workflow_references():
    """Every template must be referenced by ``--template`` in a workflow file."""
    template_names = set(get_template_names())
    workflow_refs = _collect_template_references()

    unreferenced = template_names - workflow_refs
    assert not unreferenced, "Templates not referenced in any workflow: " + ", ".join(
        sorted(unreferenced)
    )

    missing_templates = workflow_refs - template_names
    assert not missing_templates, (
        "Workflow --template references with no template file: "
        + ", ".join(sorted(missing_templates))
    )
