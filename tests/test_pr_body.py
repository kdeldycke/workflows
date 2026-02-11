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

import pytest

from gha_utils.pr_body import (
    build_pr_body,
    extract_workflow_filename,
    generate_pr_metadata_block,
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


def test_build_pr_body_with_prefix():
    """Prefix is prepended with triple newline separator."""
    metadata = "<details>metadata</details>"
    result = build_pr_body("Fix formatting issues.", metadata)

    assert result.startswith("Fix formatting issues.")
    assert "\n\n\n<details>metadata</details>" in result


def test_build_pr_body_empty_prefix():
    """Empty prefix returns just the metadata block."""
    metadata = "<details>metadata</details>"
    result = build_pr_body("", metadata)

    assert result == metadata
