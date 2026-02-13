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

"""Tests for workflow sync module."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from gha_utils.github import AnnotationLevel
from gha_utils.workflow_sync import (
    ALL_WORKFLOW_FILES,
    DEFAULT_REPO,
    NON_REUSABLE_WORKFLOWS,
    REUSABLE_WORKFLOWS,
    LintResult,
    WorkflowFormat,
    WorkflowTriggerInfo,
    check_has_workflow_dispatch,
    check_secrets_inherit,
    check_triggers_match,
    check_version_pinned,
    extract_trigger_info,
    generate_thin_caller,
    generate_workflows,
    identify_canonical_workflow,
    run_workflow_lint,
)


def test_reusable_workflows_sorted() -> None:
    """Verify reusable workflows are sorted."""
    assert list(REUSABLE_WORKFLOWS) == sorted(REUSABLE_WORKFLOWS)


def test_all_workflow_files_sorted() -> None:
    """Verify all workflow files are sorted."""
    assert list(ALL_WORKFLOW_FILES) == sorted(ALL_WORKFLOW_FILES)


def test_non_reusable_subset_of_all() -> None:
    """Verify non-reusable workflows are a subset of all workflows."""
    assert NON_REUSABLE_WORKFLOWS <= set(ALL_WORKFLOW_FILES)


def test_reusable_subset_of_all() -> None:
    """Verify reusable workflows are a subset of all workflows."""
    assert set(REUSABLE_WORKFLOWS) <= set(ALL_WORKFLOW_FILES)


def test_no_overlap() -> None:
    """Verify no overlap between reusable and non-reusable sets."""
    assert not (set(REUSABLE_WORKFLOWS) & NON_REUSABLE_WORKFLOWS)


def test_union_is_all() -> None:
    """Verify union of reusable and non-reusable equals all."""
    assert set(REUSABLE_WORKFLOWS) | NON_REUSABLE_WORKFLOWS == set(ALL_WORKFLOW_FILES)


@pytest.mark.parametrize("filename", REUSABLE_WORKFLOWS)
def test_reusable_has_workflow_call(filename: str) -> None:
    """Verify all reusable workflows have workflow_call trigger."""
    info = extract_trigger_info(filename)
    assert info.has_workflow_call is True


@pytest.mark.parametrize("filename", list(NON_REUSABLE_WORKFLOWS))
def test_non_reusable_no_workflow_call(filename: str) -> None:
    """Verify non-reusable workflows lack workflow_call trigger."""
    info = extract_trigger_info(filename)
    assert info.has_workflow_call is False


@pytest.mark.parametrize("filename", REUSABLE_WORKFLOWS)
def test_returns_trigger_info(filename: str) -> None:
    """Verify return type is WorkflowTriggerInfo."""
    info = extract_trigger_info(filename)
    assert isinstance(info, WorkflowTriggerInfo)
    assert info.filename == filename
    assert isinstance(info.name, str)
    assert len(info.name) > 0


def test_release_has_secrets() -> None:
    """Verify release.yaml defines secrets."""
    info = extract_trigger_info("release.yaml")
    assert "PYPI_TOKEN" in info.call_secrets


@pytest.mark.parametrize("filename", REUSABLE_WORKFLOWS)
def test_no_workflow_call_inputs(filename: str) -> None:
    """Verify no reusable workflow defines ``workflow_call`` inputs.

    All configurable options live in ``[tool.gha-utils]`` in ``pyproject.toml``.
    Workflows read config via ``gha-utils`` CLI instead of accepting inputs.
    """
    info = extract_trigger_info(filename)
    assert len(info.call_inputs) == 0, (
        f"{filename} still defines workflow_call inputs: "
        f"{sorted(info.call_inputs)}"
    )


def test_changelog_has_workflow_run() -> None:
    """Verify changelog.yaml has workflow_run trigger."""
    info = extract_trigger_info("changelog.yaml")
    assert "workflow_run" in info.non_call_triggers


def test_autolock_has_schedule() -> None:
    """Verify autolock.yaml has schedule trigger."""
    info = extract_trigger_info("autolock.yaml")
    assert "schedule" in info.non_call_triggers


def test_nonexistent_file() -> None:
    """Raise FileNotFoundError for missing workflow."""
    with pytest.raises(FileNotFoundError):
        extract_trigger_info("nonexistent.yaml")


@pytest.mark.parametrize("filename", REUSABLE_WORKFLOWS)
def test_generates_valid_yaml(filename: str) -> None:
    """Verify generated content is valid YAML."""
    content = generate_thin_caller(filename)
    data = yaml.safe_load(content)
    assert isinstance(data, dict)


@pytest.mark.parametrize("filename", REUSABLE_WORKFLOWS)
def test_includes_workflow_dispatch(filename: str) -> None:
    """Verify generated caller always includes workflow_dispatch."""
    content = generate_thin_caller(filename)
    data = yaml.safe_load(content)
    triggers = data.get(True) or data.get("on") or {}
    assert "workflow_dispatch" in triggers


@pytest.mark.parametrize("filename", REUSABLE_WORKFLOWS)
def test_correct_uses_ref(filename: str) -> None:
    """Verify correct uses reference in job."""
    content = generate_thin_caller(filename)
    expected = f"{DEFAULT_REPO}/.github/workflows/{filename}@main"
    assert expected in content


@pytest.mark.parametrize("filename", REUSABLE_WORKFLOWS)
def test_starts_with_document_marker(filename: str) -> None:
    """Verify generated YAML starts with --- document marker."""
    content = generate_thin_caller(filename)
    assert content.startswith("---\n")


@pytest.mark.parametrize("filename", REUSABLE_WORKFLOWS)
def test_quoted_on_key(filename: str) -> None:
    """Verify the on key is quoted as ``"on":``."""
    content = generate_thin_caller(filename)
    assert '"on":' in content


def test_release_has_secrets_inherit() -> None:
    """Verify release.yaml thin caller has secrets: inherit."""
    content = generate_thin_caller("release.yaml")
    assert "secrets: inherit" in content


def test_lint_no_secrets_inherit() -> None:
    """Verify lint.yaml thin caller has no secrets: inherit."""
    content = generate_thin_caller("lint.yaml")
    assert "secrets: inherit" not in content


def test_custom_version() -> None:
    """Verify custom version in uses reference."""
    content = generate_thin_caller("lint.yaml", version="v5.8.0")
    assert f"{DEFAULT_REPO}/.github/workflows/lint.yaml@v5.8.0" in content


def test_custom_repo() -> None:
    """Verify custom repo in uses reference."""
    content = generate_thin_caller("lint.yaml", repo="myorg/myworkflows")
    assert "myorg/myworkflows/.github/workflows/lint.yaml@main" in content


def test_non_reusable_raises() -> None:
    """Raise ValueError for non-reusable workflow."""
    with pytest.raises(ValueError, match="workflow_call"):
        generate_thin_caller("tests.yaml")


def test_has_jobs_section() -> None:
    """Verify generated YAML has jobs section."""
    content = generate_thin_caller("lint.yaml")
    data = yaml.safe_load(content)
    assert "jobs" in data


def test_has_name() -> None:
    """Verify generated YAML has name field."""
    content = generate_thin_caller("lint.yaml")
    data = yaml.safe_load(content)
    assert "name" in data


def test_identifies_thin_caller(tmp_path: Path) -> None:
    """Identify a thin caller workflow."""
    wf = tmp_path / "lint.yaml"
    wf.write_text(
        "---\nname: Lint\njobs:\n  lint:\n"
        f"    uses: {DEFAULT_REPO}/.github/workflows/lint.yaml@v5.8.0\n",
        encoding="UTF-8",
    )
    result = identify_canonical_workflow(wf)
    assert result == "lint.yaml"


def test_returns_none_for_non_caller(tmp_path: Path) -> None:
    """Return None for non-caller workflow."""
    wf = tmp_path / "custom.yaml"
    wf.write_text(
        "---\nname: Custom\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
        "    steps:\n      - run: echo hello\n",
        encoding="UTF-8",
    )
    result = identify_canonical_workflow(wf)
    assert result is None


def test_returns_none_for_invalid_yaml(tmp_path: Path) -> None:
    """Return None for invalid YAML file."""
    wf = tmp_path / "bad.yaml"
    wf.write_text("{{invalid yaml", encoding="UTF-8")
    result = identify_canonical_workflow(wf)
    assert result is None


def test_returns_none_for_missing_file(tmp_path: Path) -> None:
    """Return None for missing file."""
    wf = tmp_path / "missing.yaml"
    result = identify_canonical_workflow(wf)
    assert result is None


def test_identify_custom_repo(tmp_path: Path) -> None:
    """Match with custom repo."""
    wf = tmp_path / "lint.yaml"
    wf.write_text(
        "---\nname: Lint\njobs:\n  lint:\n"
        "    uses: myorg/myrepo/.github/workflows/lint.yaml@v1.0\n",
        encoding="UTF-8",
    )
    result = identify_canonical_workflow(wf, repo="myorg/myrepo")
    assert result == "lint.yaml"


def test_has_dispatch(tmp_path: Path) -> None:
    """Pass when workflow_dispatch is present."""
    wf = tmp_path / "test.yaml"
    wf.write_text(
        '---\n"on":\n  workflow_dispatch:\n  push:\n',
        encoding="UTF-8",
    )
    result = check_has_workflow_dispatch(wf)
    assert result.is_issue is False


def test_missing_dispatch(tmp_path: Path) -> None:
    """Fail when workflow_dispatch is missing."""
    wf = tmp_path / "test.yaml"
    wf.write_text('---\n"on":\n  push:\n', encoding="UTF-8")
    result = check_has_workflow_dispatch(wf)
    assert result.is_issue is True
    assert "missing" in result.message


def test_invalid_yaml(tmp_path: Path) -> None:
    """Error on invalid YAML."""
    wf = tmp_path / "bad.yaml"
    wf.write_text("{{invalid", encoding="UTF-8")
    result = check_has_workflow_dispatch(wf)
    assert result.is_issue is True
    assert result.level == AnnotationLevel.ERROR


def test_pinned_version(tmp_path: Path) -> None:
    """Pass when using a version tag."""
    wf = tmp_path / "lint.yaml"
    wf.write_text(
        f"    uses: {DEFAULT_REPO}/.github/workflows/lint.yaml@v5.8.0\n",
        encoding="UTF-8",
    )
    result = check_version_pinned(wf)
    assert result.is_issue is False


def test_uses_main(tmp_path: Path) -> None:
    """Fail when using @main."""
    wf = tmp_path / "lint.yaml"
    wf.write_text(
        f"    uses: {DEFAULT_REPO}/.github/workflows/lint.yaml@main\n",
        encoding="UTF-8",
    )
    result = check_version_pinned(wf)
    assert result.is_issue is True
    assert "@main" in result.message


def test_matching_triggers(tmp_path: Path) -> None:
    """Pass when triggers match canonical."""
    # lint.yaml has: workflow_dispatch, push, pull_request.
    wf = tmp_path / "lint.yaml"
    wf.write_text(
        '---\n"on":\n  workflow_dispatch:\n  push:\n  pull_request:\n',
        encoding="UTF-8",
    )
    result = check_triggers_match(wf, "lint.yaml")
    assert result.is_issue is False


def test_missing_trigger(tmp_path: Path) -> None:
    """Fail when a trigger is missing."""
    wf = tmp_path / "lint.yaml"
    wf.write_text(
        '---\n"on":\n  push:\n',
        encoding="UTF-8",
    )
    result = check_triggers_match(wf, "lint.yaml")
    assert result.is_issue is True
    assert "missing triggers" in result.message


def test_has_secrets_inherit(tmp_path: Path) -> None:
    """Pass when secrets: inherit is present."""
    wf = tmp_path / "release.yaml"
    wf.write_text(
        "---\njobs:\n  release:\n"
        f"    uses: {DEFAULT_REPO}/.github/workflows/release.yaml@v5.8.0\n"
        "    secrets: inherit\n",
        encoding="UTF-8",
    )
    result = check_secrets_inherit(wf, "release.yaml")
    assert result.is_issue is False


def test_missing_secrets_inherit(tmp_path: Path) -> None:
    """Fail when secrets: inherit is missing but required."""
    wf = tmp_path / "release.yaml"
    wf.write_text(
        "---\njobs:\n  release:\n"
        f"    uses: {DEFAULT_REPO}/.github/workflows/release.yaml@v5.8.0\n",
        encoding="UTF-8",
    )
    result = check_secrets_inherit(wf, "release.yaml")
    assert result.is_issue is True
    assert "secrets" in result.message


def test_no_secrets_needed(tmp_path: Path) -> None:
    """Pass when canonical workflow has no secrets."""
    wf = tmp_path / "lint.yaml"
    wf.write_text(
        "---\njobs:\n  lint:\n"
        f"    uses: {DEFAULT_REPO}/.github/workflows/lint.yaml@v5.8.0\n",
        encoding="UTF-8",
    )
    result = check_secrets_inherit(wf, "lint.yaml")
    assert result.is_issue is False


def test_clean_directory(tmp_path: Path) -> None:
    """Return 0 for clean workflows."""
    wf = tmp_path / "test.yaml"
    wf.write_text(
        '---\n"on":\n  workflow_dispatch:\n  push:\njobs:\n'
        "  build:\n    runs-on: ubuntu-latest\n",
        encoding="UTF-8",
    )
    exit_code = run_workflow_lint(tmp_path)
    assert exit_code == 0


def test_missing_directory(tmp_path: Path) -> None:
    """Return 1 for missing directory."""
    exit_code = run_workflow_lint(tmp_path / "nonexistent")
    assert exit_code == 1


def test_empty_directory(tmp_path: Path) -> None:
    """Return 0 for empty directory."""
    exit_code = run_workflow_lint(tmp_path)
    assert exit_code == 0


def test_warning_mode(tmp_path: Path) -> None:
    """Return 0 in warning mode even with issues."""
    wf = tmp_path / "test.yaml"
    wf.write_text('---\n"on":\n  push:\n', encoding="UTF-8")
    exit_code = run_workflow_lint(tmp_path, fatal=False)
    assert exit_code == 0


def test_fatal_mode(tmp_path: Path) -> None:
    """Return 1 in fatal mode when issues found."""
    wf = tmp_path / "test.yaml"
    wf.write_text('---\n"on":\n  push:\n', encoding="UTF-8")
    exit_code = run_workflow_lint(tmp_path, fatal=True)
    assert exit_code == 1


def test_create_thin_callers(tmp_path: Path) -> None:
    """Generate thin callers for all reusable workflows."""
    exit_code = generate_workflows(
        names=(),
        output_format=WorkflowFormat.THIN_CALLER,  # type: ignore[arg-type]
        version="main",
        repo=DEFAULT_REPO,
        output_dir=tmp_path,
        overwrite=False,
    )
    assert exit_code == 0
    for filename in REUSABLE_WORKFLOWS:
        assert (tmp_path / filename).exists()


def test_create_specific_workflow(tmp_path: Path) -> None:
    """Generate a single thin caller."""
    exit_code = generate_workflows(
        names=("lint.yaml",),
        output_format=WorkflowFormat.THIN_CALLER,  # type: ignore[arg-type]
        version="v5.8.0",
        repo=DEFAULT_REPO,
        output_dir=tmp_path,
        overwrite=False,
    )
    assert exit_code == 0
    assert (tmp_path / "lint.yaml").exists()
    content = (tmp_path / "lint.yaml").read_text(encoding="UTF-8")
    assert "v5.8.0" in content


def test_create_errors_if_exists(tmp_path: Path) -> None:
    """Error in create mode if file exists."""
    (tmp_path / "lint.yaml").write_text("existing", encoding="UTF-8")
    exit_code = generate_workflows(
        names=("lint.yaml",),
        output_format=WorkflowFormat.THIN_CALLER,  # type: ignore[arg-type]
        version="main",
        repo=DEFAULT_REPO,
        output_dir=tmp_path,
        overwrite=False,
    )
    assert exit_code == 1


def test_sync_overwrites(tmp_path: Path) -> None:
    """Overwrite in sync mode."""
    (tmp_path / "lint.yaml").write_text("old content", encoding="UTF-8")
    exit_code = generate_workflows(
        names=("lint.yaml",),
        output_format=WorkflowFormat.THIN_CALLER,  # type: ignore[arg-type]
        version="main",
        repo=DEFAULT_REPO,
        output_dir=tmp_path,
        overwrite=True,
    )
    assert exit_code == 0
    content = (tmp_path / "lint.yaml").read_text(encoding="UTF-8")
    assert content != "old content"


def test_skip_non_reusable_thin_caller(tmp_path: Path) -> None:
    """Skip non-reusable workflows in thin-caller mode."""
    exit_code = generate_workflows(
        names=("tests.yaml",),
        output_format=WorkflowFormat.THIN_CALLER,  # type: ignore[arg-type]
        version="main",
        repo=DEFAULT_REPO,
        output_dir=tmp_path,
        overwrite=False,
    )
    assert exit_code == 0
    assert not (tmp_path / "tests.yaml").exists()


def test_full_copy(tmp_path: Path) -> None:
    """Generate full copy of a workflow."""
    exit_code = generate_workflows(
        names=("lint.yaml",),
        output_format=WorkflowFormat.FULL_COPY,  # type: ignore[arg-type]
        version="main",
        repo=DEFAULT_REPO,
        output_dir=tmp_path,
        overwrite=False,
    )
    assert exit_code == 0
    assert (tmp_path / "lint.yaml").exists()
    content = (tmp_path / "lint.yaml").read_text(encoding="UTF-8")
    # Full copy should contain the original workflow content.
    assert "jobs:" in content


def test_creates_output_dir(tmp_path: Path) -> None:
    """Create output directory if it doesn't exist."""
    output_dir = tmp_path / "sub" / "dir"
    exit_code = generate_workflows(
        names=("lint.yaml",),
        output_format=WorkflowFormat.THIN_CALLER,  # type: ignore[arg-type]
        version="main",
        repo=DEFAULT_REPO,
        output_dir=output_dir,
        overwrite=False,
    )
    assert exit_code == 0
    assert (output_dir / "lint.yaml").exists()


def test_values() -> None:
    """Verify expected enum values."""
    assert WorkflowFormat.THIN_CALLER == "thin-caller"
    assert WorkflowFormat.FULL_COPY == "full-copy"
    assert WorkflowFormat.SYMLINK == "symlink"


def test_from_string() -> None:
    """Verify construction from string."""
    assert WorkflowFormat("thin-caller") == WorkflowFormat.THIN_CALLER
    assert WorkflowFormat("full-copy") == WorkflowFormat.FULL_COPY
    assert WorkflowFormat("symlink") == WorkflowFormat.SYMLINK


def test_default_level() -> None:
    """Verify default annotation level is WARNING."""
    result = LintResult(message="test", is_issue=True)
    assert result.level == AnnotationLevel.WARNING


def test_custom_level() -> None:
    """Verify custom annotation level."""
    result = LintResult(message="test", is_issue=True, level=AnnotationLevel.ERROR)
    assert result.level == AnnotationLevel.ERROR
