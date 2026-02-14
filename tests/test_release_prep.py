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

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

import pytest

from gha_utils.release_prep import ReleasePrep


@pytest.fixture
def temp_changelog(tmp_path: Path) -> Path:
    """Create a temporary changelog file."""
    changelog = tmp_path / "changelog.md"
    changelog.write_text(
        dedent("""\
            # Changelog

            ## [1.2.3 (unreleased)](https://github.com/user/repo/compare/v1.2.2...main)

            > [!IMPORTANT]
            > This version is not released yet and is under active development.

            - Add new feature.
            - Fix bug.

            ## [1.2.2 (2024-01-15)](https://github.com/user/repo/compare/v1.2.1...v1.2.2)

            - Previous release.
            """),
        encoding="UTF-8",
    )
    return changelog


@pytest.fixture
def temp_citation(tmp_path: Path) -> Path:
    """Create a temporary citation file."""
    citation = tmp_path / "citation.cff"
    citation.write_text(
        dedent("""\
            cff-version: 1.2.0
            title: My Project
            version: 1.2.3
            date-released: 2024-01-01
            authors:
              - name: Test Author
            """),
        encoding="UTF-8",
    )
    return citation


@pytest.fixture
def temp_workflows(tmp_path: Path) -> Path:
    """Create a temporary workflows directory with sample files."""
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)

    (workflow_dir / "release.yaml").write_text(
        dedent("""\
            name: Release
            on: push
            jobs:
              build:
                uses: kdeldycke/workflows/main/.github/workflows/release.yaml
            """),
        encoding="UTF-8",
    )

    (workflow_dir / "lint.yaml").write_text(
        dedent("""\
            name: Lint
            on: push
            jobs:
              lint:
                uses: kdeldycke/workflows/main/.github/workflows/lint.yaml
            """),
        encoding="UTF-8",
    )

    return workflow_dir


@pytest.fixture
def temp_workflows_with_actions(tmp_path: Path) -> Path:
    """Create workflows with composite action references."""
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)

    (workflow_dir / "autofix.yaml").write_text(
        dedent("""\
            name: Autofix
            on: push
            jobs:
              format:
                steps:
                  - id: pr-metadata
                    uses: kdeldycke/workflows/.github/actions/pr-metadata@main
                  - uses: peter-evans/create-pull-request@v8
                    with:
                      body: ${{ steps.pr-metadata.outputs.body }}
            """),
        encoding="UTF-8",
    )

    return workflow_dir


@pytest.fixture
def temp_workflows_with_cli(tmp_path: Path) -> Path:
    """Create workflows with ``--from . gha-utils`` CLI invocations."""
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)

    (workflow_dir / "lint.yaml").write_text(
        dedent("""\
            name: Lint
            on: push
            jobs:
              metadata:
                steps:
                  - run: >
                      uvx --no-progress --from . gha-utils
                      metadata --output "$GITHUB_OUTPUT"
              lint:
                steps:
                  - run: >
                      uvx --no-progress --from . gha-utils
                      lint-repo --repo-name "test"
            """),
        encoding="UTF-8",
    )

    (workflow_dir / "autofix.yaml").write_text(
        dedent("""\
            name: Autofix
            on: push
            jobs:
              format:
                steps:
                  - run: >
                      uvx --no-progress --from . gha-utils
                      metadata --output "$GITHUB_OUTPUT"
                  - run: uvx --no-progress --from . gha-utils pr-body
            """),
        encoding="UTF-8",
    )

    return workflow_dir


@pytest.fixture
def temp_pyproject(tmp_path: Path) -> Path:
    """Create a temporary pyproject.toml with bumpversion config."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        dedent("""\
            [project]
            name = "test-project"
            version = "1.2.3"

            [tool.bumpversion]
            current_version = "1.2.3"
            """),
        encoding="UTF-8",
    )
    return pyproject


def test_current_version_from_pyproject(
    tmp_path: Path, temp_pyproject: Path, monkeypatch
) -> None:
    """Test that current version is read from pyproject.toml."""
    monkeypatch.chdir(tmp_path)

    prep = ReleasePrep()

    assert prep.current_version == "1.2.3"


def test_freeze_action_reference(
    tmp_path: Path,
    temp_workflows_with_actions: Path,
    temp_pyproject: Path,
    monkeypatch,
) -> None:
    """Test that composite action references are frozen to versioned tag."""
    monkeypatch.chdir(tmp_path)

    prep = ReleasePrep(workflow_dir=temp_workflows_with_actions)
    count = prep.freeze_workflow_urls()

    assert count == 1
    content = (temp_workflows_with_actions / "autofix.yaml").read_text(encoding="UTF-8")
    assert "@main" not in content
    assert "@v1.2.3" in content
    assert "kdeldycke/workflows/.github/actions/pr-metadata@v1.2.3" in content


def test_freeze_cli_version(
    tmp_path: Path,
    temp_workflows_with_cli: Path,
    temp_pyproject: Path,
    monkeypatch,
) -> None:
    """Test that ``--from . gha-utils`` is frozen to a PyPI version."""
    monkeypatch.chdir(tmp_path)

    prep = ReleasePrep(workflow_dir=temp_workflows_with_cli)
    count = prep.freeze_cli_version("1.0.0")

    assert count == 2
    for workflow_file in temp_workflows_with_cli.glob("*.yaml"):
        content = workflow_file.read_text(encoding="UTF-8")
        assert "--from . gha-utils" not in content
        assert "'gha-utils==1.0.0'" in content


def test_freeze_workflow_urls(
    tmp_path: Path,
    temp_workflows: Path,
    temp_pyproject: Path,
    monkeypatch,
) -> None:
    """Test that workflow URLs are frozen to versioned tag."""
    monkeypatch.chdir(tmp_path)

    prep = ReleasePrep(workflow_dir=temp_workflows)
    count = prep.freeze_workflow_urls()

    assert count == 2
    for workflow_file in temp_workflows.glob("*.yaml"):
        content = workflow_file.read_text(encoding="UTF-8")
        assert "/workflows/main/" not in content
        assert "/workflows/v1.2.3/" in content


def test_post_release(
    tmp_path: Path,
    temp_workflows: Path,
    temp_pyproject: Path,
    monkeypatch,
) -> None:
    """Test post-release workflow unfreezing."""
    monkeypatch.chdir(tmp_path)

    # First freeze for release.
    prep = ReleasePrep(workflow_dir=temp_workflows)
    prep.freeze_workflow_urls()

    # Then run post-release.
    modified = prep.post_release(update_workflows=True)

    assert len(modified) == 2
    for workflow_file in temp_workflows.glob("*.yaml"):
        content = workflow_file.read_text(encoding="UTF-8")
        assert "/workflows/main/" in content


def test_post_release_unfreezes_cli(
    tmp_path: Path,
    temp_workflows_with_cli: Path,
    temp_pyproject: Path,
    monkeypatch,
) -> None:
    """Test that post-release unfreezes CLI invocations back to local source."""
    monkeypatch.chdir(tmp_path)

    # First freeze CLI.
    prep = ReleasePrep(workflow_dir=temp_workflows_with_cli)
    prep.freeze_cli_version("1.0.0")
    for workflow_file in temp_workflows_with_cli.glob("*.yaml"):
        content = workflow_file.read_text(encoding="UTF-8")
        assert "'gha-utils==1.0.0'" in content

    # Then run post-release.
    prep.modified_files = []
    modified = prep.post_release(update_workflows=True)

    assert len(modified) == 2
    for workflow_file in temp_workflows_with_cli.glob("*.yaml"):
        content = workflow_file.read_text(encoding="UTF-8")
        assert "'gha-utils==" not in content
        assert "--from . gha-utils" in content


def test_prepare_release_full(
    tmp_path: Path,
    temp_changelog: Path,
    temp_citation: Path,
    temp_workflows: Path,
    temp_pyproject: Path,
    monkeypatch,
) -> None:
    """Test full release preparation with all options."""
    monkeypatch.chdir(tmp_path)

    prep = ReleasePrep(
        changelog_path=temp_changelog,
        citation_path=temp_citation,
        workflow_dir=temp_workflows,
    )
    modified = prep.prepare_release(update_workflows=True)

    # Changelog once, citation once, 2 workflows for URLs.
    # CLI freeze doesn't match (no --from . gha-utils in temp_workflows).
    assert len(modified) == 4
    assert len(set(modified)) == 4

    # Verify changelog changes.
    changelog_content = temp_changelog.read_text(encoding="UTF-8")
    assert "(unreleased)" not in changelog_content
    assert "...main)" not in changelog_content
    assert "[!IMPORTANT]" not in changelog_content

    # Verify citation changes.
    citation_content = temp_citation.read_text(encoding="UTF-8")
    assert f"date-released: {prep.release_date}" in citation_content

    # Verify workflow changes.
    for workflow_file in temp_workflows.glob("*.yaml"):
        content = workflow_file.read_text(encoding="UTF-8")
        assert "/workflows/v1.2.3/" in content


def test_prepare_release_freezes_cli(
    tmp_path: Path,
    temp_changelog: Path,
    temp_citation: Path,
    temp_workflows_with_cli: Path,
    temp_pyproject: Path,
    monkeypatch,
) -> None:
    """Test that prepare_release freezes CLI invocations to current version."""
    monkeypatch.chdir(tmp_path)

    prep = ReleasePrep(
        changelog_path=temp_changelog,
        citation_path=temp_citation,
        workflow_dir=temp_workflows_with_cli,
    )
    prep.prepare_release(update_workflows=True)

    for workflow_file in temp_workflows_with_cli.glob("*.yaml"):
        content = workflow_file.read_text(encoding="UTF-8")
        assert "--from . gha-utils" not in content
        assert "'gha-utils==1.2.3'" in content


def test_prepare_release_without_workflows(
    tmp_path: Path,
    temp_changelog: Path,
    temp_citation: Path,
    temp_pyproject: Path,
    monkeypatch,
) -> None:
    """Test release preparation without workflow updates."""
    monkeypatch.chdir(tmp_path)

    prep = ReleasePrep(
        changelog_path=temp_changelog,
        citation_path=temp_citation,
    )
    modified = prep.prepare_release(update_workflows=False)

    # Changelog once, citation once.
    assert len(modified) == 2
    assert len(set(modified)) == 2


def test_release_date_format(tmp_path: Path, temp_pyproject: Path, monkeypatch) -> None:
    """Test that release date is in correct format."""
    monkeypatch.chdir(tmp_path)

    prep = ReleasePrep()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    assert prep.release_date == today


def test_set_citation_release_date(
    tmp_path: Path, temp_citation: Path, temp_pyproject: Path, monkeypatch
) -> None:
    """Test that release date is set in citation file."""
    monkeypatch.chdir(tmp_path)

    prep = ReleasePrep(citation_path=temp_citation)
    result = prep.set_citation_release_date()

    assert result is True
    content = temp_citation.read_text(encoding="UTF-8")
    assert "date-released: 2024-01-01" not in content
    assert f"date-released: {prep.release_date}" in content


def test_set_citation_release_date_missing_file(
    tmp_path: Path, temp_pyproject: Path, monkeypatch
) -> None:
    """Test that missing citation file is handled gracefully."""
    monkeypatch.chdir(tmp_path)

    prep = ReleasePrep(citation_path=tmp_path / "nonexistent.cff")
    result = prep.set_citation_release_date()

    assert result is False


def test_unfreeze_action_reference(
    tmp_path: Path,
    temp_workflows_with_actions: Path,
    temp_pyproject: Path,
    monkeypatch,
) -> None:
    """Test that composite action references are unfrozen to default branch."""
    monkeypatch.chdir(tmp_path)

    # First freeze the version.
    prep = ReleasePrep(workflow_dir=temp_workflows_with_actions)
    prep.freeze_workflow_urls()

    # Verify version is frozen.
    content = (temp_workflows_with_actions / "autofix.yaml").read_text(encoding="UTF-8")
    assert "@v1.2.3" in content

    # Then unfreeze to main.
    del prep.__dict__["current_version"]
    count = prep.unfreeze_workflow_urls()

    assert count == 1
    content = (temp_workflows_with_actions / "autofix.yaml").read_text(encoding="UTF-8")
    assert "@v1.2.3" not in content
    assert "@main" in content
    assert "kdeldycke/workflows/.github/actions/pr-metadata@main" in content


def test_unfreeze_cli_version(
    tmp_path: Path,
    temp_workflows_with_cli: Path,
    temp_pyproject: Path,
    monkeypatch,
) -> None:
    """Test that frozen PyPI version is unfrozen back to local source."""
    monkeypatch.chdir(tmp_path)

    # First freeze CLI.
    prep = ReleasePrep(workflow_dir=temp_workflows_with_cli)
    prep.freeze_cli_version("1.0.0")
    for workflow_file in temp_workflows_with_cli.glob("*.yaml"):
        content = workflow_file.read_text(encoding="UTF-8")
        assert "'gha-utils==1.0.0'" in content

    # Then unfreeze.
    prep.modified_files = []
    count = prep.unfreeze_cli_version()

    assert count == 2
    for workflow_file in temp_workflows_with_cli.glob("*.yaml"):
        content = workflow_file.read_text(encoding="UTF-8")
        assert "'gha-utils==" not in content
        assert "--from . gha-utils" in content


def test_unfreeze_workflow_urls(
    tmp_path: Path,
    temp_workflows: Path,
    temp_pyproject: Path,
    monkeypatch,
) -> None:
    """Test that workflow URLs are unfrozen back to default branch."""
    monkeypatch.chdir(tmp_path)

    # First freeze the version.
    prep = ReleasePrep(workflow_dir=temp_workflows)
    prep.freeze_workflow_urls()

    # Then unfreeze to main.
    # Need to clear cached property to re-read version.
    del prep.__dict__["current_version"]
    count = prep.unfreeze_workflow_urls()

    assert count == 2
    for workflow_file in temp_workflows.glob("*.yaml"):
        content = workflow_file.read_text(encoding="UTF-8")
        assert "/workflows/v1.2.3/" not in content
        assert "/workflows/main/" in content
