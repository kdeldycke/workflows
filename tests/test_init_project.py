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
"""Tests for bundled configuration templates and repository initialization."""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from repomatic.init_project import (
    ALL_COMPONENTS,
    ALL_WORKFLOW_FILES,
    COMPONENT_FILES,
    DEFAULT_COMPONENTS,
    EXPORTABLE_FILES,
    FILE_COMPONENTS,
    OPT_IN_WORKFLOWS,
    REUSABLE_WORKFLOWS,
    SKILL_PHASES,
    TOOL_COMPONENTS,
    _strip_renovate_repo_settings,
    _to_pyproject_format,
    _update_bumpversion_config,
    default_version_pin,
    export_content,
    get_data_content,
    init_config,
    parse_component_entries,
    run_init,
    valid_file_ids,
)
from repomatic.registry import (
    COMPONENTS,
    BundledComponent,
    ToolConfigComponent,
    _BY_NAME,
)
from repomatic.tool_runner import TOOL_REGISTRY

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]


# --- Bundled data and export tests ---


def test_supported_config_types() -> None:
    """Verify that expected config types are registered as ToolConfigComponent."""
    for name in ("mypy", "ruff", "pytest", "bumpversion", "typos"):
        assert isinstance(_BY_NAME[name], ToolConfigComponent)


def test_config_type_has_required_fields() -> None:
    """Verify that each tool config component has all required fields."""
    for comp in COMPONENTS:
        if not isinstance(comp, ToolConfigComponent):
            continue
        assert comp.source_file
        assert comp.tool_section
        assert comp.description


@pytest.mark.parametrize("config_type", sorted(TOOL_COMPONENTS))
def test_returns_non_empty_string(config_type: str) -> None:
    """Verify that export_content returns a non-empty string."""
    comp = _BY_NAME[config_type]
    content = export_content(comp.source_file)
    assert isinstance(content, str)
    assert len(content) > 0


@pytest.mark.parametrize("config_type", sorted(TOOL_COMPONENTS))
def test_returns_valid_toml(config_type: str) -> None:
    """Verify that the returned content is valid TOML."""
    comp = _BY_NAME[config_type]
    content = export_content(comp.source_file)
    parsed = tomllib.loads(content)
    assert isinstance(parsed, dict)


@pytest.mark.parametrize("config_type", sorted(TOOL_COMPONENTS))
def test_native_format_no_tool_prefix(config_type: str) -> None:
    """Verify that native format does not have [tool.X] prefix."""
    comp = _BY_NAME[config_type]
    content = export_content(comp.source_file)
    parsed = tomllib.loads(content)
    # Native format should NOT have a "tool" key at the root.
    assert "tool" not in parsed


def test_unknown_file_raises_error() -> None:
    """Verify that an unknown file raises ValueError."""
    with pytest.raises(ValueError, match="Unknown file"):
        export_content("nonexistent.toml")


@pytest.mark.parametrize("filename", list(EXPORTABLE_FILES.keys()))
def test_exportable_file_loadable(filename: str) -> None:
    """Verify every registered data file can be loaded (no dangling symlinks)."""
    content = export_content(filename)
    assert len(content) > 0


# Keys intentionally different between template and repomatic's own pyproject.toml.
# - ``exclude``: key exists only in the template (for downstream), not in own config.
# - ``superset``: every template list entry must appear in own config, but own may
#   have extras.
_TEMPLATE_EXCLUDE_KEYS: dict[str, frozenset[str]] = {
    "bumpversion": frozenset({"current_version"}),
    "mypy": frozenset(),
    "pytest": frozenset({"addopts"}),
    "ruff": frozenset({"extend-include"}),
    "typos": frozenset(),
}
_TEMPLATE_SUPERSET_KEYS: dict[str, frozenset[str]] = {
    "bumpversion": frozenset({"files"}),
    "mypy": frozenset(),
    "pytest": frozenset(),
    "ruff": frozenset(),
    "typos": frozenset(),
}


@pytest.mark.parametrize("config_type", sorted(TOOL_COMPONENTS))
def test_template_matches_own_pyproject(config_type: str) -> None:
    """Verify bundled template stays in sync with repomatic's own config.

    Template keys (minus intentional exclusions) must match the corresponding
    ``[tool.*]`` section. List keys marked as superset require every template
    entry to appear in own config, but own config may have extras.
    """
    comp = _BY_NAME[config_type]
    template = tomllib.loads(export_content(comp.source_file))

    project_root = Path(__file__).resolve().parent.parent
    own_config = tomllib.loads(
        (project_root / "pyproject.toml").read_text(encoding="UTF-8")
    )["tool"][config_type]

    exclude = _TEMPLATE_EXCLUDE_KEYS.get(config_type, frozenset())
    superset = _TEMPLATE_SUPERSET_KEYS.get(config_type, frozenset())

    def assert_subset(tmpl: dict, own: dict, path: str = "") -> None:
        for key, value in tmpl.items():
            full = f"{path}.{key}" if path else key
            if key in exclude:
                continue
            if key in superset:
                for entry in value:
                    assert entry in own[key], (
                        f"Template entry missing from [tool.{config_type}] "
                        f"{full}: {entry}"
                    )
                continue
            assert key in own, (
                f"Template key {full!r} missing from "
                f"[tool.{config_type}] in pyproject.toml"
            )
            if isinstance(value, dict):
                assert_subset(value, own[key], full)
            else:
                assert own[key] == value, (
                    f"[tool.{config_type}] {full!r}: "
                    f"expected {value!r}, got {own[key]!r}"
                )

    assert_subset(template, own_config)


def test_bundled_renovate_matches_processed_root() -> None:
    """Verify bundled renovate.json5 matches processed root file.

    The root ``renovate.json5`` is the source of truth. The bundled version
    in ``repomatic/data/`` should match the root file with repo-specific
    settings (``assignees`` and the self-referencing uv ``customManagers``
    entry) removed.

    If this test fails, regenerate the bundled file by running:
        uv run repomatic init renovate --output-dir repomatic/data
    """
    root_path = Path(__file__).parent.parent / "renovate.json5"
    assert root_path.exists(), "Root renovate.json5 not found"

    content = root_path.read_text(encoding="UTF-8")
    processed = _strip_renovate_repo_settings(content)

    bundled_content = get_data_content("renovate.json5")

    assert bundled_content.strip() == processed.strip(), (
        "Bundled renovate.json5 is out of sync with root file.\n"
        "Regenerate with: uv run repomatic init renovate"
        " --output-dir repomatic/data"
    )


# --- Ruff config tests ---


def test_has_preview_enabled() -> None:
    """Verify that preview mode is enabled."""
    content = export_content("ruff.toml")
    parsed = tomllib.loads(content)
    assert parsed.get("preview") is True


def test_has_fix_settings() -> None:
    """Verify that fix settings are configured."""
    content = export_content("ruff.toml")
    parsed = tomllib.loads(content)

    assert parsed.get("fix") is True
    assert parsed.get("unsafe-fixes") is True
    assert parsed.get("show-fixes") is True


def test_has_lint_section() -> None:
    """Verify that the lint section exists with expected settings."""
    content = export_content("ruff.toml")
    parsed = tomllib.loads(content)

    assert "lint" in parsed
    lint = parsed["lint"]
    assert lint.get("future-annotations") is True
    assert "ignore" in lint
    assert isinstance(lint["ignore"], list)


@pytest.mark.parametrize("expected_ignore", ["D400", "ERA001"])
def test_has_expected_ignore_rules(expected_ignore: str) -> None:
    """Verify that expected rules are in the ignore list."""
    content = export_content("ruff.toml")
    parsed = tomllib.loads(content)
    ignore = parsed["lint"]["ignore"]
    assert expected_ignore in ignore


def test_has_format_section() -> None:
    """Verify that the format section exists with docstring formatting enabled."""
    content = export_content("ruff.toml")
    parsed = tomllib.loads(content)

    assert "format" in parsed
    assert parsed["format"].get("docstring-code-format") is True


# --- Mypy config tests ---


@pytest.mark.parametrize(
    "setting",
    [
        "warn_unused_configs",
        "warn_redundant_casts",
        "warn_unused_ignores",
        "warn_return_any",
        "warn_unreachable",
        "pretty",
    ],
)
def test_has_expected_settings(setting: str) -> None:
    """Verify that expected settings are present."""
    content = export_content("mypy.toml")
    parsed = tomllib.loads(content)
    assert setting in parsed
    assert parsed[setting] is True


# --- Pytest config tests ---


def test_has_addopts() -> None:
    """Verify that addopts list is present."""
    content = export_content("pytest.toml")
    parsed = tomllib.loads(content)

    assert "addopts" in parsed
    assert isinstance(parsed["addopts"], list)
    assert len(parsed["addopts"]) > 0


@pytest.mark.parametrize(
    "expected_opt",
    [
        "--durations=10",
        "--cov-branch",
        "--cov-report=term",
        "--cov-report=xml",
        "--junitxml=junit.xml",
    ],
)
def test_has_expected_addopts(expected_opt: str) -> None:
    """Verify that expected options are in addopts."""
    content = export_content("pytest.toml")
    parsed = tomllib.loads(content)
    addopts = parsed["addopts"]
    assert expected_opt in addopts


def test_has_xfail_strict() -> None:
    """Verify that xfail_strict is enabled."""
    content = export_content("pytest.toml")
    parsed = tomllib.loads(content)
    assert parsed.get("xfail_strict") is True


# --- Bumpversion config tests ---


def test_has_required_settings() -> None:
    """Verify that the configuration has required bumpversion settings."""
    content = export_content("bumpversion.toml")
    parsed = tomllib.loads(content)

    assert "current_version" in parsed
    assert "allow_dirty" in parsed
    assert "ignore_missing_files" in parsed


def test_has_files_section() -> None:
    """Verify that the configuration has file patterns defined."""
    content = export_content("bumpversion.toml")
    parsed = tomllib.loads(content)

    assert "files" in parsed
    assert isinstance(parsed["files"], list)
    assert len(parsed["files"]) > 0


# --- pyproject.toml merging tests ---


def test_adds_root_section() -> None:
    """Verify that root section is added before first key."""
    native = "key = true\n"
    result = _to_pyproject_format(native, "tool.mypy")
    assert "[tool.mypy]" in result
    assert result.index("[tool.mypy]") < result.index("key = true")


def test_transforms_subsections() -> None:
    """Verify that subsections get the tool prefix."""
    native = "[lint]\nrule = true\n"
    result = _to_pyproject_format(native, "tool.ruff")
    assert "[tool.ruff.lint]" in result


def test_transforms_array_sections() -> None:
    """Verify that array sections get the tool prefix."""
    native = "[[files]]\nfilename = 'test.py'\n"
    result = _to_pyproject_format(native, "tool.bumpversion")
    assert "[[tool.bumpversion.files]]" in result


def test_preserves_comments() -> None:
    """Verify that comments are preserved."""
    native = "# This is a comment\nkey = true\n"
    result = _to_pyproject_format(native, "tool.mypy")
    assert "# This is a comment" in result


def test_full_ruff_transform() -> None:
    """Verify full transformation of ruff config."""
    native = export_content("ruff.toml")
    result = _to_pyproject_format(native, "tool.ruff")
    parsed = tomllib.loads(result)

    assert "tool" in parsed
    assert "ruff" in parsed["tool"]
    assert parsed["tool"]["ruff"].get("preview") is True
    assert "lint" in parsed["tool"]["ruff"]
    assert "format" in parsed["tool"]["ruff"]


def test_adds_config_to_empty_pyproject() -> None:
    """Verify that config is added to a pyproject.toml without the section."""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('[project]\nname = "test"\n')
        f.flush()
        path = Path(f.name)

    try:
        result = init_config("ruff", path)
        assert result is not None
        assert "[tool.ruff]" in result
        assert "preview = true" in result
        # Verify dotted keys are preserved (ruff.toml uses dotted keys, not
        # sections).
        assert "lint.ignore" in result
        assert "format.docstring-code-format" in result
    finally:
        path.unlink()


def test_adds_bumpversion_with_array_sections() -> None:
    """Verify that bumpversion [[files]] sections are transformed."""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('[project]\nname = "test"\n')
        f.flush()
        path = Path(f.name)

    try:
        result = init_config("bumpversion", path)
        assert result is not None
        assert "[tool.bumpversion]" in result
        assert "[[tool.bumpversion.files]]" in result
    finally:
        path.unlink()


def test_returns_none_if_section_exists() -> None:
    """Verify that None is returned if the section already exists."""
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write('[project]\nname = "test"\n\n[tool.ruff]\npreview = false\n')
        f.flush()
        path = Path(f.name)

    try:
        result = init_config("ruff", path)
        assert result is None
    finally:
        path.unlink()


def test_preserves_existing_content() -> None:
    """Verify that existing content is preserved when adding config."""
    original = '[project]\nname = "test"\nversion = "1.0.0"\n'
    with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(original)
        f.flush()
        path = Path(f.name)

    try:
        result = init_config("mypy", path)
        assert result is not None
        assert 'name = "test"' in result
        assert 'version = "1.0.0"' in result
        assert "[tool.mypy]" in result
    finally:
        path.unlink()


def test_unknown_config_type_raises_error() -> None:
    """Verify that an unknown config type raises ValueError."""
    with pytest.raises(ValueError, match="Unknown config type"):
        init_config("nonexistent", Path("pyproject.toml"))


# --- Init orchestration tests ---


def test_default_version_pin():
    """Verify version pin is derived correctly."""
    pin = default_version_pin()
    assert pin.startswith("v")
    # Should not contain .dev suffix.
    assert ".dev" not in pin


def test_init_default_components():
    """Verify DEFAULT_COMPONENTS contains expected file components."""
    assert "changelog" in DEFAULT_COMPONENTS
    assert "labels" in DEFAULT_COMPONENTS
    assert "renovate" in DEFAULT_COMPONENTS
    assert "skills" in DEFAULT_COMPONENTS
    assert "workflows" in DEFAULT_COMPONENTS
    # Tool configs should not be in defaults.
    assert "ruff" not in DEFAULT_COMPONENTS
    assert "bumpversion" not in DEFAULT_COMPONENTS


def test_init_creates_all_default_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify all default component files are created (with no exclusions)."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.repomatic]\n"
        'include = ["labels", "skills"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    result = run_init(output_dir=tmp_path)

    # All components: changelog, labels, renovate, skills, workflows.
    # Opt-in workflows and awesome-triage skill are excluded by default.
    config_file_count = sum(len(v) for v in COMPONENT_FILES.values())
    default_workflows = len(REUSABLE_WORKFLOWS) - len(OPT_IN_WORKFLOWS)
    awesome_triage_auto_excluded = 2  # awesome-triage + translation-sync.
    expected_count = (
        default_workflows + config_file_count + 1 - awesome_triage_auto_excluded
    )
    assert len(result.created) == expected_count
    assert len(result.skipped) == 0
    assert len(result.warnings) == 0

    # Verify workflow files exist (excluding opt-in workflows).
    for filename in REUSABLE_WORKFLOWS:
        if filename not in OPT_IN_WORKFLOWS:
            assert (tmp_path / ".github" / "workflows" / filename).exists()

    # Verify config files exist.
    assert (tmp_path / "renovate.json5").exists()
    assert (tmp_path / "labels.toml").exists()
    assert (tmp_path / ".github" / "labeller-file-based.yaml").exists()
    assert (tmp_path / ".github" / "labeller-content-based.yaml").exists()

    # Verify changelog exists.
    assert (tmp_path / "changelog.md").exists()


def test_init_creates_changelog(tmp_path: Path):
    """Verify changelog is created with expected content."""
    result = run_init(output_dir=tmp_path, components=("changelog",))

    changelog = tmp_path / "changelog.md"
    assert changelog.exists()
    content = changelog.read_text(encoding="UTF-8")
    assert content.startswith("# Changelog")
    assert "## [Unreleased]" in content
    assert "changelog.md" in result.created


def test_init_creates_parent_dirs(tmp_path: Path):
    """Verify .github/workflows/ is created automatically."""
    assert not (tmp_path / ".github").exists()
    run_init(output_dir=tmp_path, components=("workflows",))
    assert (tmp_path / ".github" / "workflows").is_dir()


def test_init_existing_changelog_skipped(tmp_path: Path):
    """Verify existing changelog is not overwritten."""
    changelog = tmp_path / "changelog.md"
    changelog.write_text("# My existing changelog\n", encoding="UTF-8")

    result = run_init(output_dir=tmp_path, components=("changelog",))

    assert "changelog.md" in result.skipped
    # Content should not be overwritten.
    assert changelog.read_text(encoding="UTF-8") == "# My existing changelog\n"


def test_init_idempotent(tmp_path: Path):
    """Verify second run updates managed files, skips changelog, and
    detects identical init configs as unmodified."""
    result1 = run_init(output_dir=tmp_path)
    assert len(result1.created) > 0
    assert len(result1.updated) == 0
    assert len(result1.skipped) == 0

    result2 = run_init(output_dir=tmp_path)
    assert len(result2.created) == 0
    # Managed files are overwritten (reported as updated), except
    # init config files identical to bundled defaults (unmodified).
    managed_count = len(result1.created) - 1  # Minus changelog.
    unmodified_count = len(result2.unmodified_configs)
    assert unmodified_count > 0  # At least renovate.json5.
    assert len(result2.updated) == managed_count - unmodified_count
    # Only changelog is skipped (never overwritten).
    assert result2.skipped == ["changelog.md"]
    # Redundant init configs are reported.
    assert "renovate.json5" in result2.unmodified_configs


def test_init_only_labels(tmp_path: Path):
    """Verify only label files are created."""
    result = run_init(output_dir=tmp_path, components=("labels",))

    created_set = set(result.created)
    assert "labels.toml" in created_set
    assert ".github/labeller-file-based.yaml" in created_set
    assert ".github/labeller-content-based.yaml" in created_set

    # No workflows or changelog should be created.
    for filename in REUSABLE_WORKFLOWS:
        assert f".github/workflows/{filename}" not in created_set
    assert "changelog.md" not in created_set


def test_init_only_skills(tmp_path: Path):
    """Verify only skill files are created.

    awesome-triage is auto-excluded for non-awesome repos.
    """
    result = run_init(output_dir=tmp_path, components=("skills",))

    created_set = set(result.created)
    assert len(created_set) == 10

    # Verify all non-awesome skill files are created.
    for name in (
        "repomatic-audit",
        "repomatic-changelog",
        "repomatic-deps",
        "repomatic-init",
        "repomatic-lint",
        "repomatic-release",
        "repomatic-sync",
        "repomatic-test",
        "repomatic-topics",
        "sphinx-docs-sync",
    ):
        rel = f".claude/skills/{name}/SKILL.md"
        assert rel in created_set
        assert (tmp_path / ".claude" / "skills" / name / "SKILL.md").exists()

    # awesome-triage and translation-sync are auto-excluded for non-awesome repos.
    assert ".claude/skills/awesome-triage/SKILL.md" not in created_set
    assert ".claude/skills/translation-sync/SKILL.md" not in created_set

    # No workflows or changelog should be created.
    assert "changelog.md" not in created_set


def test_skills_consistency():
    """Verify all .claude/skills/ directories have matching entries in code.

    Guards against adding a skill definition to ``.claude/skills/`` without
    registering it in the component registry, ``SKILL_PHASES``, and the
    ``repomatic/data/`` symlinks.
    """
    # Collect skill directories from the filesystem.
    skills_dir = Path(__file__).resolve().parents[1] / ".claude" / "skills"
    fs_skills = {p.parent.name for p in skills_dir.glob("*/SKILL.md")}

    # Collect skills registered in the component registry.
    component_skills = {
        entry.file_id for entry in _BY_NAME["skills"].files
    }

    # Collect skills registered in SKILL_PHASES.
    phase_skills = set(SKILL_PHASES)

    # Collect data symlinks.
    data_dir = Path(__file__).resolve().parents[1] / "repomatic" / "data"
    data_skills = {p.stem.removeprefix("skill-") for p in data_dir.glob("skill-*.md")}

    assert fs_skills == component_skills, (
        f"Registry mismatch: "
        f"missing={fs_skills - component_skills}, "
        f"extra={component_skills - fs_skills}"
    )
    assert fs_skills == data_skills, (
        f"Data symlinks mismatch: "
        f"missing={fs_skills - data_skills}, "
        f"extra={data_skills - fs_skills}"
    )
    assert fs_skills == phase_skills, (
        f"SKILL_PHASES mismatch: "
        f"missing={fs_skills - phase_skills}, "
        f"stale={phase_skills - fs_skills}"
    )


def test_init_only_renovate(tmp_path: Path):
    """Verify only renovate config is created."""
    result = run_init(output_dir=tmp_path, components=("renovate",))

    assert "renovate.json5" in set(result.created)
    assert (tmp_path / "renovate.json5").exists()
    # No other default components.
    assert "changelog.md" not in set(result.created)


def test_init_only_workflows(tmp_path: Path):
    """Verify only workflow files are created."""
    result = run_init(output_dir=tmp_path, components=("workflows",))

    created_set = set(result.created)
    # Opt-in workflows are excluded by default.
    for filename in REUSABLE_WORKFLOWS:
        if filename in OPT_IN_WORKFLOWS:
            assert f".github/workflows/{filename}" not in created_set
        else:
            assert f".github/workflows/{filename}" in created_set

    # No config files or changelog.
    assert "renovate.json5" not in created_set
    assert "changelog.md" not in created_set


def test_init_always_overwrites_managed_files(tmp_path: Path):
    """Verify managed files are always replaced on re-run."""
    # Create a workflow file with old content.
    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    target = workflows_dir / "lint.yaml"
    target.write_text("# Old content\n", encoding="UTF-8")

    result = run_init(
        output_dir=tmp_path,
        components=("workflows",),
    )

    assert ".github/workflows/lint.yaml" in result.updated
    assert len(result.skipped) == 0
    # Content should be replaced.
    content = target.read_text(encoding="UTF-8")
    assert content != "# Old content\n"


def test_init_changelog_never_overwritten(tmp_path: Path):
    """Verify an existing changelog.md is never overwritten."""
    changelog = tmp_path / "changelog.md"
    changelog.write_text("# Old content\n", encoding="UTF-8")

    result = run_init(
        output_dir=tmp_path,
        components=("changelog",),
    )

    assert "changelog.md" in result.skipped
    assert len(result.created) == 0
    assert len(result.updated) == 0
    # Content should be preserved.
    content = changelog.read_text(encoding="UTF-8")
    assert content == "# Old content\n"


def test_init_tool_configs_no_pyproject(tmp_path: Path):
    """Verify warning when pyproject.toml is missing."""
    result = run_init(
        output_dir=tmp_path,
        components=("ruff",),
    )

    assert len(result.warnings) == 1
    assert "pyproject.toml not found" in result.warnings[0]


def test_init_version_pinned(tmp_path: Path):
    """Verify generated workflows contain the specified version pin."""
    run_init(
        output_dir=tmp_path,
        components=("workflows",),
        version="v5.9.1",
    )

    # Check that generated workflow files contain the version pin.
    # Opt-in workflows are excluded by default.
    for filename in REUSABLE_WORKFLOWS:
        if filename in OPT_IN_WORKFLOWS:
            continue
        wf_path = tmp_path / ".github" / "workflows" / filename
        content = wf_path.read_text(encoding="UTF-8")
        assert "@v5.9.1" in content


def test_init_with_specific_tool_configs(tmp_path: Path):
    """Verify multiple tool configs are merged into pyproject.toml."""
    # Create a minimal pyproject.toml.
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test-project"\nversion = "0.1.0"\n',
        encoding="UTF-8",
    )

    result = run_init(
        output_dir=tmp_path,
        components=("ruff", "bumpversion"),
    )

    assert len(result.warnings) == 0

    # Verify requested tool sections were merged.
    content = pyproject.read_text(encoding="UTF-8")
    assert "[tool.ruff]" in content
    assert "[tool.bumpversion]" in content


def test_init_with_single_tool_config(tmp_path: Path):
    """Verify only requested tool config is merged."""
    # Create a minimal pyproject.toml.
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test-project"\nversion = "0.1.0"\n',
        encoding="UTF-8",
    )

    run_init(
        output_dir=tmp_path,
        components=("ruff",),
    )

    # Only ruff should be merged, not bumpversion.
    content = pyproject.read_text(encoding="UTF-8")
    assert "[tool.ruff]" in content
    assert "[tool.bumpversion]" not in content


# --- Bumpversion config update tests ---


# Minimal pyproject with existing bumpversion config (no dev versioning).
PYPROJECT_WITH_BUMPVERSION = """\
[project]
name = "test-project"
version = "7.5.3"

[tool.bumpversion]
current_version = "7.5.3"
allow_dirty = true

[[tool.bumpversion.files]]
filename = "./pyproject.toml"
search = 'version = "{current_version}"'
replace = 'version = "{new_version}"'

[[tool.bumpversion.files]]
filename = "./changelog.md"
search = "## [{current_version} (unreleased)]("
replace = "## [{new_version} (unreleased)]("
"""


def _make_pyproject_with_template_bumpversion(version: str = "7.5.3.dev0") -> str:
    """Generate a pyproject.toml with the bumpversion section from the template.

    Used as a fixture for tests that need an already-up-to-date config.
    """
    native = export_content("bumpversion.toml")
    bv_section = _to_pyproject_format(native, "tool.bumpversion")
    bv_section = bv_section.replace(
        'current_version = "0.0.0.dev0"',
        f'current_version = "{version}"',
    )
    return (
        f'[project]\nname = "test-project"\nversion = "{version}"\n\n'
        + bv_section.strip()
        + "\n"
    )


def test_updates_existing_bumpversion_config(tmp_path: Path) -> None:
    """Verify existing [tool.bumpversion] without parse gets dev config injected."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(PYPROJECT_WITH_BUMPVERSION, encoding="UTF-8")

    result = init_config("bumpversion", pyproject)

    assert result is not None
    assert "parse = " in result
    assert "serialize = [" in result
    assert "ignore_missing_files = true" in result
    assert "parts.dev.values = " in result


def test_updates_current_version_with_dev_suffix(tmp_path: Path) -> None:
    """Verify current_version "7.5.3" becomes "7.5.3.dev0"."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(PYPROJECT_WITH_BUMPVERSION, encoding="UTF-8")

    result = init_config("bumpversion", pyproject)

    assert result is not None
    assert 'current_version = "7.5.3.dev0"' in result


def test_updates_project_version_with_dev_suffix(tmp_path: Path) -> None:
    """Verify [project] version is also updated to dev0."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(PYPROJECT_WITH_BUMPVERSION, encoding="UTF-8")

    result = init_config("bumpversion", pyproject)

    assert result is not None
    assert 'version = "7.5.3.dev0"' in result


def test_replaces_bumpversion_files_from_template(tmp_path: Path) -> None:
    """Verify [[tool.bumpversion.files]] entries come from the template."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(PYPROJECT_WITH_BUMPVERSION, encoding="UTF-8")

    result = init_config("bumpversion", pyproject)

    assert result is not None
    assert "[[tool.bumpversion.files]]" in result
    # Template entries are present.
    assert 'filename = "./pyproject.toml"' in result
    assert 'filename = "./changelog.md"' in result
    assert 'filename = "./citation.cff"' in result
    assert 'glob = "./**/__init__.py"' in result


def test_preserves_other_pyproject_sections(tmp_path: Path) -> None:
    """Verify [project] and other sections are unchanged."""
    content = (
        '[project]\nname = "test-project"\nversion = "2.0.0"\n\n'
        "[tool.ruff]\npreview = true\n\n"
        "[tool.bumpversion]\n"
        'current_version = "2.0.0"\n'
        "allow_dirty = true\n\n"
        "[[tool.bumpversion.files]]\n"
        'filename = "./pyproject.toml"\n'
    )
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(content, encoding="UTF-8")

    result = init_config("bumpversion", pyproject)

    assert result is not None
    assert 'name = "test-project"' in result
    assert "[tool.ruff]" in result
    assert "preview = true" in result


def test_updates_managed_changelog(tmp_path: Path) -> None:
    """Verify changelog.md heading is updated via bumpversion file entries."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(PYPROJECT_WITH_BUMPVERSION, encoding="UTF-8")

    changelog = tmp_path / "changelog.md"
    changelog.write_text(
        "# Changelog\n\n## [7.5.3 (unreleased)](https://example.com)\n",
        encoding="UTF-8",
    )

    init_config("bumpversion", pyproject)

    # Changelog should be updated on disk.
    updated = changelog.read_text(encoding="UTF-8")
    assert "## [7.5.3.dev0 (unreleased)](" in updated


def test_updates_managed_init_py(tmp_path: Path) -> None:
    """Verify __init__.py version is updated via bumpversion glob entries."""
    content = (
        '[project]\nname = "test-project"\nversion = "1.0.0"\n\n'
        "[tool.bumpversion]\n"
        'current_version = "1.0.0"\n'
        "allow_dirty = true\n\n"
        "[[tool.bumpversion.files]]\n"
        'glob = "./**/__init__.py"\n'
        "ignore_missing_version = true\n"
    )
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(content, encoding="UTF-8")

    # Create a package with __init__.py.
    pkg_dir = tmp_path / "my_pkg"
    pkg_dir.mkdir()
    init_py = pkg_dir / "__init__.py"
    init_py.write_text('__version__ = "1.0.0"\n', encoding="UTF-8")

    init_config("bumpversion", pyproject)

    # __init__.py should be updated on disk.
    updated = init_py.read_text(encoding="UTF-8")
    assert '__version__ = "1.0.0.dev0"' in updated


def test_skips_already_migrated(tmp_path: Path) -> None:
    """Verify config matching the template returns None (no changes needed)."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(_make_pyproject_with_template_bumpversion(), encoding="UTF-8")

    result = init_config("bumpversion", pyproject)

    assert result is None


def test_replaces_old_changelog_pattern(tmp_path: Path) -> None:
    """Verify old changelog pattern without backticks is replaced by template."""
    content = (
        '[project]\nname = "test"\nversion = "1.0.0.dev0"\n\n'
        "[tool.bumpversion]\n"
        'current_version = "1.0.0.dev0"\n'
        "allow_dirty = true\n"
        "parse = '(?P<major>\\d+)'\n\n"
        "[[tool.bumpversion.files]]\n"
        'filename = "./changelog.md"\n'
        'search = "## [{current_version} (unreleased)]("\n'
        'replace = "## [{new_version} (unreleased)]("\n'
    )
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(content, encoding="UTF-8")

    result = init_config("bumpversion", pyproject)

    assert result is not None
    # Template has backtick-escaped pattern.
    assert "## [`{current_version}` (unreleased)](" in result
    assert "## [`{new_version}` (unreleased)](" in result


def test_skips_already_dev_version(tmp_path: Path) -> None:
    """Verify version ending .dev0 is not double-suffixed."""
    content = (
        '[project]\nname = "test"\nversion = "1.0.0.dev0"\n\n'
        "[tool.bumpversion]\n"
        'current_version = "1.0.0.dev0"\n'
        "allow_dirty = true\n"
    )
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(content, encoding="UTF-8")

    result = _update_bumpversion_config(content, pyproject)

    assert result is not None
    # Version should not be double-suffixed.
    assert "1.0.0.dev0.dev0" not in result
    assert 'current_version = "1.0.0.dev0"' in result


def test_bumpversion_update_idempotent(tmp_path: Path) -> None:
    """Verify running update twice produces the same result."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(PYPROJECT_WITH_BUMPVERSION, encoding="UTF-8")

    # First run: should update.
    result1 = init_config("bumpversion", pyproject)
    assert result1 is not None
    pyproject.write_text(result1, encoding="UTF-8")

    # Second run: should be a no-op.
    result2 = init_config("bumpversion", pyproject)
    assert result2 is None


def test_bumpversion_update_valid_toml(tmp_path: Path) -> None:
    """Verify updated pyproject.toml is still valid TOML."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(PYPROJECT_WITH_BUMPVERSION, encoding="UTF-8")

    result = init_config("bumpversion", pyproject)

    assert result is not None
    parsed = tomllib.loads(result)
    bv = parsed["tool"]["bumpversion"]
    assert "parse" in bv
    assert "serialize" in bv
    assert "parts" in bv
    assert "dev" in bv["parts"]


# --- Init exclusion tests ---


def test_init_default_excludes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify default exclude skips labels and skills."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    result = run_init(output_dir=tmp_path)

    created_set = set(result.created)
    # Labels and skills are excluded by default.
    assert "labels.toml" not in created_set
    for _, rel_path in COMPONENT_FILES.get("skills", ()):
        assert rel_path not in created_set

    # Other default components should still be created.
    assert "changelog.md" in created_set
    assert "renovate.json5" in created_set

    assert result.excluded == ["labels", "skills"]


def test_init_respects_exclude_components(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify exclude config skips listed components."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.repomatic]\n"
        'exclude = ["skills", "labels"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    result = run_init(output_dir=tmp_path)

    created_set = set(result.created)
    # Labels and skill files should not be created.
    assert "labels.toml" not in created_set
    for _, rel_path in COMPONENT_FILES.get("skills", ()):
        assert rel_path not in created_set

    # Other default components should still be created.
    assert "changelog.md" in created_set
    assert "renovate.json5" in created_set

    assert result.excluded == ["labels", "skills"]


def test_init_respects_exclude_workflow_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify exclude config with workflow file entries skips those workflows."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.repomatic]\n"
        'exclude = ["workflows/debug.yaml", "workflows/docs.yaml"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    result = run_init(output_dir=tmp_path)

    created_set = set(result.created)
    # Excluded workflows should not be created.
    assert ".github/workflows/debug.yaml" not in created_set
    assert ".github/workflows/docs.yaml" not in created_set

    # Other workflows should still be created.
    assert ".github/workflows/lint.yaml" in created_set
    assert ".github/workflows/release.yaml" in created_set


def test_init_respects_exclude_skill_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify exclude config with skill file entries skips those skills."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.repomatic]\n"
        'include = ["skills"]\n'
        'exclude = ["skills/repomatic-audit", "skills/repomatic-topics"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    result = run_init(output_dir=tmp_path)

    created_set = set(result.created)
    # Excluded skills should not be created.
    assert ".claude/skills/repomatic-audit/SKILL.md" not in created_set
    assert ".claude/skills/repomatic-topics/SKILL.md" not in created_set

    # Other skills should still be created.
    assert ".claude/skills/repomatic-init/SKILL.md" in created_set


def test_init_awesome_triage_auto_excluded_for_non_awesome_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify awesome-triage skill is auto-excluded for non-awesome repos."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n[tool.repomatic]\ninclude = ["skills"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    result = run_init(output_dir=tmp_path, repo_slug="user/some-project")

    created_set = set(result.created)
    assert ".claude/skills/awesome-triage/SKILL.md" not in created_set
    assert ".claude/skills/translation-sync/SKILL.md" not in created_set
    assert ".claude/skills/repomatic-init/SKILL.md" in created_set


def test_init_awesome_triage_included_for_awesome_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify awesome-triage skill is included for awesome-* repos."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n[tool.repomatic]\ninclude = ["skills"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    result = run_init(output_dir=tmp_path, repo_slug="user/awesome-python")

    created_set = set(result.created)
    assert ".claude/skills/awesome-triage/SKILL.md" in created_set
    assert ".claude/skills/translation-sync/SKILL.md" in created_set
    assert ".claude/skills/repomatic-init/SKILL.md" in created_set


def test_init_respects_exclude_label_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify exclude config with label file entries skips those label files."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.repomatic]\n"
        'include = ["labels"]\n'
        'exclude = ["labels/labeller-content-based.yaml"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    result = run_init(output_dir=tmp_path)

    created_set = set(result.created)
    # Excluded label file should not be created.
    assert ".github/labeller-content-based.yaml" not in created_set

    # Other label files should still be created.
    assert "labels.toml" in created_set
    assert ".github/labeller-file-based.yaml" in created_set


def test_init_mixed_exclude(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify exclude with both component and file entries."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.repomatic]\n"
        'include = ["skills"]\n'
        'exclude = ["workflows/debug.yaml", "skills/repomatic-audit"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    result = run_init(output_dir=tmp_path)

    created_set = set(result.created)
    assert "labels.toml" not in created_set
    assert ".github/workflows/debug.yaml" not in created_set
    assert ".claude/skills/repomatic-audit/SKILL.md" not in created_set

    # Non-excluded items should be created.
    assert ".github/workflows/lint.yaml" in created_set
    assert ".claude/skills/repomatic-init/SKILL.md" in created_set


def test_init_detects_excluded_component_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify init reports excluded component files that still exist on disk."""
    # First init with labels included to create all files.
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n[tool.repomatic]\ninclude = ["labels"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)
    run_init(output_dir=tmp_path)

    labels_toml = tmp_path / "labels.toml"
    assert labels_toml.exists()

    # Now re-run without include — labels falls back to default exclusion.
    pyproject.write_text(
        '[project]\nname = "test"\n',
        encoding="UTF-8",
    )

    result = run_init(output_dir=tmp_path)

    # File is detected but not deleted (deletion requires --delete-excluded).
    assert labels_toml.exists()
    assert "labels.toml" in result.excluded_existing


def test_init_detects_excluded_skill_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify init reports a file-level excluded skill that still exists on disk."""
    # First create all skills (include overrides default exclusion).
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n[tool.repomatic]\ninclude = ["skills"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)
    run_init(output_dir=tmp_path, repo_slug="user/awesome-list")

    skill_file = tmp_path / ".claude" / "skills" / "awesome-triage" / "SKILL.md"
    assert skill_file.exists()

    # Now exclude just that skill and re-run.
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.repomatic]\n"
        'include = ["skills"]\n'
        'exclude = ["skills/awesome-triage"]\n',
        encoding="UTF-8",
    )

    result = run_init(output_dir=tmp_path, repo_slug="user/awesome-list")

    # File is detected but not deleted.
    assert skill_file.exists()
    assert ".claude/skills/awesome-triage/SKILL.md" in result.excluded_existing
    # Other skills should still exist.
    assert (tmp_path / ".claude" / "skills" / "repomatic-init" / "SKILL.md").exists()


def test_init_detects_auto_excluded_awesome_triage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify awesome-triage is detected as excluded for non-awesome repos."""
    # Create skills including awesome-triage (as an awesome repo).
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n[tool.repomatic]\ninclude = ["skills"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)
    run_init(output_dir=tmp_path, repo_slug="user/awesome-list")

    skill_file = tmp_path / ".claude" / "skills" / "awesome-triage" / "SKILL.md"
    assert skill_file.exists()

    # Re-run as a non-awesome repo.
    result = run_init(output_dir=tmp_path, repo_slug="user/regular-project")

    # File is detected but not deleted.
    assert skill_file.exists()
    assert ".claude/skills/awesome-triage/SKILL.md" in result.excluded_existing


def test_init_detects_disabled_opt_in_workflow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify disabled opt-in workflows on disk are detected as excluded."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.repomatic]\n"
        "notification.unsubscribe = true\n",
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    # Create the opt-in workflow while it's enabled.
    result = run_init(output_dir=tmp_path)
    wf = tmp_path / ".github" / "workflows" / "unsubscribe.yaml"
    assert wf.exists()
    assert ".github/workflows/unsubscribe.yaml" not in result.excluded_existing

    # Disable the opt-in workflow and re-run.
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.repomatic]\n"
        "notification.unsubscribe = false\n",
        encoding="UTF-8",
    )

    result = run_init(output_dir=tmp_path)

    # File is detected as stale but not deleted.
    assert wf.exists()
    assert ".github/workflows/unsubscribe.yaml" in result.excluded_existing
    # Disabled opt-in workflows should not appear in "Excluded by config".
    assert "workflows/unsubscribe.yaml" not in result.excluded


def test_init_cli_delete_excluded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify --delete-excluded deletes excluded files and cleans empty dirs."""
    from click.testing import CliRunner

    from repomatic.cli import repomatic

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n[tool.repomatic]\ninclude = ["skills"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)
    run_init(output_dir=tmp_path, repo_slug="user/awesome-list")

    skill_file = tmp_path / ".claude" / "skills" / "awesome-triage" / "SKILL.md"
    assert skill_file.exists()

    # Exclude awesome-triage and re-run with --delete-excluded.
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.repomatic]\n"
        'include = ["skills"]\n'
        'exclude = ["skills/awesome-triage"]\n',
        encoding="UTF-8",
    )

    runner = CliRunner()
    cli_result = runner.invoke(
        repomatic,
        ["init", "--output-dir", str(tmp_path), "--delete-excluded"],
    )

    assert cli_result.exit_code == 0
    assert not skill_file.exists()
    # Empty parent directory should also be removed.
    assert not skill_file.parent.exists()
    assert "Deleted" in cli_result.output
    assert "excluded" in cli_result.output


def test_init_cli_no_delete_excluded_warns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify excluded files are reported but not deleted without --delete-excluded."""
    from click.testing import CliRunner

    from repomatic.cli import repomatic

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n[tool.repomatic]\ninclude = ["skills"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)
    run_init(output_dir=tmp_path, repo_slug="user/awesome-list")

    skill_file = tmp_path / ".claude" / "skills" / "awesome-triage" / "SKILL.md"
    assert skill_file.exists()

    # Exclude awesome-triage and re-run without --delete-excluded.
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.repomatic]\n"
        'include = ["skills"]\n'
        'exclude = ["skills/awesome-triage"]\n',
        encoding="UTF-8",
    )

    runner = CliRunner()
    cli_result = runner.invoke(
        repomatic,
        ["init", "--output-dir", str(tmp_path)],
    )

    assert cli_result.exit_code == 0
    # File is still on disk.
    assert skill_file.exists()
    assert "--delete-excluded" in cli_result.output


def test_init_explicit_components_bypass_exclude(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify explicit CLI components override exclusion."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.repomatic]\n"
        'exclude = ["labels", "skills", "changelog"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    # Explicitly request excluded components.
    result = run_init(output_dir=tmp_path, components=("labels", "changelog"))

    created_set = set(result.created)
    # Explicitly requested components should be created despite exclusion.
    assert "labels.toml" in created_set
    assert "changelog.md" in created_set

    # Exclusion list should be empty when explicit components given.
    assert result.excluded == []


def test_init_exclude_unknown_component_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify unknown component name in exclude raises ValueError."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.repomatic]\n"
        'exclude = ["nonexistent-component"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="Unknown exclude"):
        run_init(output_dir=tmp_path)


def test_init_exclude_unknown_file_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify unknown file identifier in exclude raises ValueError."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.repomatic]\n"
        'exclude = ["workflows/nonexistent.yaml"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="Unknown file"):
        run_init(output_dir=tmp_path)


def test_init_include_unknown_component_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify unknown component name in include raises ValueError."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.repomatic]\n"
        'include = ["nonexistent-component"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="Unknown include"):
        run_init(output_dir=tmp_path)


def test_init_include_overrides_default_exclusions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify include overrides default exclusions additively."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n[tool.repomatic]\ninclude = ["labels"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    result = run_init(output_dir=tmp_path)

    created_set = set(result.created)
    # Labels included via include, skills still excluded by default.
    assert "labels.toml" in created_set
    for _, rel_path in COMPONENT_FILES.get("skills", ()):
        assert rel_path not in created_set
    # skills is the only remaining default exclusion.
    assert result.excluded == ["skills"]


def test_init_exclude_additive_to_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify user exclude is additive to default exclusions."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.repomatic]\n"
        'exclude = ["workflows/debug.yaml"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    result = run_init(output_dir=tmp_path)

    created_set = set(result.created)
    # Default exclusions (labels, skills) still apply.
    assert "labels.toml" not in created_set
    for _, rel_path in COMPONENT_FILES.get("skills", ()):
        assert rel_path not in created_set
    # User exclude is additive.
    assert ".github/workflows/debug.yaml" not in created_set
    assert "labels" in result.excluded
    assert "skills" in result.excluded
    assert "workflows/debug.yaml" in result.excluded


# --- Data file registry and exclude validation tests ---


def test_all_data_files_registered_in_exportable_files() -> None:
    """Every non-infrastructure file in data/ must appear in EXPORTABLE_FILES."""
    from importlib.resources import as_file, files

    data_dir = files("repomatic.data")
    with as_file(data_dir) as data_path:
        on_disk = {
            p.name
            for p in Path(data_path).iterdir()
            if p.name != "__init__.py"
            and not p.name.startswith(".")
            and not p.name.startswith("__")
            and not p.is_dir()
        }

    registered = set(EXPORTABLE_FILES.keys())
    unregistered = on_disk - registered
    assert not unregistered, (
        f"Data files not in EXPORTABLE_FILES: {sorted(unregistered)}"
    )


def test_every_data_file_maps_to_a_component() -> None:
    """Every file in EXPORTABLE_FILES belongs to a registry component or tool runner."""
    # Collect all source filenames from the registry.
    registry_filenames: set[str] = set()
    for comp in COMPONENTS:
        for entry in comp.files:
            registry_filenames.add(entry.source)
        if isinstance(comp, ToolConfigComponent):
            registry_filenames.add(comp.source_file)

    # Collect bundled default configs used by the tool runner at runtime.
    bundled_defaults = {
        spec.default_config for spec in TOOL_REGISTRY.values() if spec.default_config
    }

    covered = registry_filenames | bundled_defaults
    uncovered = set(EXPORTABLE_FILES.keys()) - covered
    assert not uncovered, (
        f"EXPORTABLE_FILES entries not mapped to any component: {sorted(uncovered)}"
    )


def test_no_data_file_claimed_by_multiple_components() -> None:
    """Each data filename must belong to at most one component."""
    seen: dict[str, str] = {}
    duplicates: list[str] = []

    for comp in COMPONENTS:
        sources: list[str] = [e.source for e in comp.files]
        if isinstance(comp, ToolConfigComponent):
            sources.append(comp.source_file)
        for source_filename in sources:
            if source_filename in seen:
                duplicates.append(
                    f"{source_filename!r} claimed by both"
                    f" {seen[source_filename]!r} and {comp.name!r}"
                )
            seen[source_filename] = comp.name

    assert not duplicates, f"Duplicate file mappings: {duplicates}"


def testvalid_file_ids_cover_all_multi_file_components() -> None:
    """Components with multiple files must report valid file identifiers."""
    for component in ("workflows", "labels", "skills"):
        ids = valid_file_ids(component)
        assert ids, f"valid_file_ids({component!r}) returned empty set"


def test_workflow_file_ids_match_all_workflow_files() -> None:
    """valid_file_ids('workflows') must match ALL_WORKFLOW_FILES."""
    assert valid_file_ids("workflows") == frozenset(ALL_WORKFLOW_FILES)


def test_component_file_ids_match_registry() -> None:
    """valid_file_ids must return identifiers matching registry entries."""
    for comp in COMPONENTS:
        if not comp.files:
            continue
        expected = frozenset(entry.file_id for entry in comp.files)
        assert valid_file_ids(comp.name) == expected


def test_tool_components_have_no_file_ids() -> None:
    """Tool components (ruff, pytest, etc.) do not support file-level exclusion."""
    for name in TOOL_COMPONENTS:
        assert valid_file_ids(name) == frozenset()


def test_workflow_files_target_workflow_dir() -> None:
    """All workflow file entries must target .github/workflows/."""
    for entry in _BY_NAME["workflows"].files:
        assert entry.target.startswith(".github/workflows/"), (
            f"Workflow entry {entry.file_id!r} targets {entry.target!r},"
            " expected .github/workflows/ prefix"
        )


def test_workflow_sources_are_yaml() -> None:
    """All workflow source files must be .yaml."""
    for entry in _BY_NAME["workflows"].files:
        assert entry.source.endswith(".yaml"), (
            f"Workflow entry {entry.file_id!r} source {entry.source!r}"
            " is not a .yaml file"
        )


def test_skill_files_target_skill_dir() -> None:
    """All skill file entries must target .claude/skills/{id}/SKILL.md."""
    for entry in _BY_NAME["skills"].files:
        assert entry.target.startswith(".claude/skills/"), (
            f"Skill entry {entry.file_id!r} targets {entry.target!r},"
            " expected .claude/skills/ prefix"
        )
        assert entry.target.endswith("/SKILL.md"), (
            f"Skill entry {entry.file_id!r} targets {entry.target!r},"
            " expected /SKILL.md suffix"
        )


def test_skill_sources_follow_naming_convention() -> None:
    """Skill source files must be named skill-{id}.md."""
    for entry in _BY_NAME["skills"].files:
        expected_source = f"skill-{entry.file_id}.md"
        assert entry.source == expected_source, (
            f"Skill {entry.file_id!r}: source is {entry.source!r},"
            f" expected {expected_source!r}"
        )


def test_skill_file_id_matches_target_dir() -> None:
    """Skill file_id must match the directory name in the target path."""
    for entry in _BY_NAME["skills"].files:
        parts = entry.target.split("/")
        # .claude/skills/{id}/SKILL.md → parts[2] is the id.
        assert parts[2] == entry.file_id, (
            f"Skill {entry.file_id!r}: target dir is {parts[2]!r}"
        )


def test_no_target_prefix_mixing_within_component() -> None:
    """Files within a component must not mix unrelated target directories."""
    for comp in COMPONENTS:
        if not comp.files:
            continue
        prefixes = {entry.target.split("/")[0] for entry in comp.files}
        # Allow mixing root files (no slash) with dotdir files within
        # a component (e.g., labels has both .github/ and root files).
        prefixes.discard(
            next(
                (entry.target for entry in comp.files if "/" not in entry.target),
                None,
            )
        )
        assert len(prefixes) <= 1, (
            f"Component {comp.name!r} mixes target prefixes: {sorted(prefixes)}"
        )


def test_tool_config_rejects_missing_source_file() -> None:
    """ToolConfigComponent raises ValueError without source_file."""
    with pytest.raises(ValueError, match="requires source_file"):
        ToolConfigComponent(
            name="bad",
            description="test",
            tool_section="tool.bad",
        )


def test_tool_config_rejects_missing_tool_section() -> None:
    """ToolConfigComponent raises ValueError without tool_section."""
    with pytest.raises(ValueError, match="requires tool_section"):
        ToolConfigComponent(
            name="bad",
            description="test",
            source_file="bad.toml",
        )


def test_tool_config_rejects_files() -> None:
    """ToolConfigComponent raises ValueError with file entries."""
    from repomatic.registry import FileEntry

    with pytest.raises(ValueError, match="must not have files"):
        ToolConfigComponent(
            name="bad",
            description="test",
            source_file="bad.toml",
            tool_section="tool.bad",
            files=(FileEntry("bad.toml"),),
        )


def test_file_ids_unique_within_component() -> None:
    """File IDs must be unique within each component."""
    for comp in COMPONENTS:
        ids = [entry.file_id for entry in comp.files]
        assert len(ids) == len(set(ids)), (
            f"Component {comp.name!r} has duplicate file_ids:"
            f" {sorted(fid for fid in ids if ids.count(fid) > 1)}"
        )


def test_component_names_unique() -> None:
    """Component names must be unique across the registry."""
    names = [c.name for c in COMPONENTS]
    assert len(names) == len(set(names)), (
        f"Duplicate component names:"
        f" {sorted(n for n in names if names.count(n) > 1)}"
    )


def test_config_key_has_config_default() -> None:
    """Entries with config_key must have an intentional config_default.

    File entries default to ``False`` (opt-in). Component entries default
    to ``True`` (opt-out). This test verifies the pairing exists — not the
    specific default value.
    """
    for comp in COMPONENTS:
        if comp.config_key:
            # Component-level config_key exists; config_default is declared.
            assert isinstance(comp.config_default, bool)
        for entry in comp.files:
            if entry.config_key:
                assert isinstance(entry.config_default, bool)


def test_tools_with_bundled_defaults_not_init_components() -> None:
    """Tools with a bundled default_config must not also be init components.

    The tool runner already falls back to the bundled config at runtime when no
    native config exists (Level 3 in resolve_config). Copying the same file
    into downstream repos via init would be redundant pollution.
    """
    tools_with_defaults = {
        name for name, spec in TOOL_REGISTRY.items() if spec.default_config
    }
    overlap = tools_with_defaults & set(FILE_COMPONENTS)
    assert not overlap, (
        f"Tools with default_config should not be FILE_COMPONENTS: {sorted(overlap)}."
        " The tool runner already uses the bundled config as a fallback."
    )


def test_init_reports_unmodified_configs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Init reports native config files that match bundled defaults."""
    from repomatic.tool_runner import get_data_file_path

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"\n', encoding="UTF-8")
    monkeypatch.chdir(tmp_path)

    with get_data_file_path("yamllint.yaml") as bundled:
        content = bundled.read_text(encoding="UTF-8")
    (tmp_path / ".yamllint.yaml").write_text(content, encoding="UTF-8")

    result = run_init(output_dir=tmp_path)
    assert ".yamllint.yaml" in result.unmodified_configs


def test_init_no_unmodified_when_different(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Init does not flag modified config files as unmodified."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"\n', encoding="UTF-8")
    monkeypatch.chdir(tmp_path)

    (tmp_path / ".yamllint.yaml").write_text(
        "rules:\n  line-length:\n    max: 80\n", encoding="UTF-8"
    )

    result = run_init(output_dir=tmp_path)
    assert result.unmodified_configs == []


# ---------------------------------------------------------------------------
# find_unmodified_init_files
# ---------------------------------------------------------------------------


def test_find_unmodified_init_files_detects_identical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Init-managed file matching bundled default is flagged as unmodified."""
    monkeypatch.chdir(tmp_path)
    content = export_content("labels.toml")
    (tmp_path / "labels.toml").write_text(content.rstrip() + "\n", encoding="UTF-8")

    from repomatic.init_project import find_unmodified_init_files

    result = find_unmodified_init_files()
    paths = [p for _, p in result]
    assert "labels.toml" in paths


def test_find_unmodified_init_files_ignores_modified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Modified init-managed file is not flagged."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "labels.toml").write_text("# custom labels\n", encoding="UTF-8")

    from repomatic.init_project import find_unmodified_init_files

    result = find_unmodified_init_files()
    paths = [p for _, p in result]
    assert "labels.toml" not in paths


def test_find_unmodified_init_files_skips_skills(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Skills are not checked for redundancy."""
    monkeypatch.chdir(tmp_path)
    content = export_content("skill-repomatic-audit.md")
    skill_dir = tmp_path / ".claude" / "skills" / "repomatic-audit"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(content.rstrip() + "\n", encoding="UTF-8")

    from repomatic.init_project import find_unmodified_init_files

    result = find_unmodified_init_files()
    paths = [p for _, p in result]
    assert not any("skills" in p for p in paths)


def test_find_unmodified_init_files_renovate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Renovate redundancy check uses export_content (with stripping)."""
    monkeypatch.chdir(tmp_path)
    content = export_content("renovate.json5")
    (tmp_path / "renovate.json5").write_text(content.rstrip() + "\n", encoding="UTF-8")

    from repomatic.init_project import find_unmodified_init_files

    result = find_unmodified_init_files()
    paths = [p for _, p in result]
    assert "renovate.json5" in paths


def test_find_unmodified_init_files_multiple(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Redundant files across multiple components are all detected."""
    monkeypatch.chdir(tmp_path)

    for source_name, rel_path in (
        ("labels.toml", "labels.toml"),
        ("labeller-file-based.yaml", ".github/labeller-file-based.yaml"),
        ("labeller-content-based.yaml", ".github/labeller-content-based.yaml"),
    ):
        path = tmp_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        content = export_content(source_name)
        path.write_text(content.rstrip() + "\n", encoding="UTF-8")

    from repomatic.init_project import find_unmodified_init_files

    result = find_unmodified_init_files()
    paths = [p for _, p in result]
    assert "labels.toml" in paths
    assert ".github/labeller-file-based.yaml" in paths
    assert ".github/labeller-content-based.yaml" in paths


def test_init_skips_identical_config(tmp_path: Path):
    """Init skips writing when downstream file matches bundled content."""
    result1 = run_init(output_dir=tmp_path, components=("renovate",))
    assert "renovate.json5" in result1.created

    result2 = run_init(output_dir=tmp_path, components=("renovate",))
    assert "renovate.json5" not in result2.updated
    assert "renovate.json5" not in result2.created
    assert "renovate.json5" in result2.unmodified_configs


@pytest.mark.parametrize(
    "entry",
    [
        "workflows/debug.yaml",
        "workflows/tests.yaml",
        "workflows/autofix.yaml",
        "skills/repomatic-audit",
        "labels/labels.toml",
        "labels/labeller-content-based.yaml",
    ],
)
def test_parse_component_entries_accepts_valid_qualified_entries(entry: str) -> None:
    """Qualified component/file entries are accepted by parse_component_entries."""
    components, files = parse_component_entries([entry])
    assert not components
    component = entry.split("/")[0]
    file_id = entry.split("/")[1]
    assert file_id in files[component]


@pytest.mark.parametrize("component", sorted(ALL_COMPONENTS.keys()))
def test_parse_component_entries_accepts_all_bare_components(component: str) -> None:
    """Every component name is accepted as a bare exclude entry."""
    components, files = parse_component_entries([component])
    assert component in components
    assert not files


def test_parse_component_entries_bare_filename_without_component_fails() -> None:
    """Bare filenames like 'debug.yaml' must fail — qualified form required."""
    with pytest.raises(ValueError, match="Unknown entry"):
        parse_component_entries(["debug.yaml"])


def test_parse_component_entries_bare_skill_name_without_component_fails() -> None:
    """Bare skill identifiers like 'repomatic-audit' must fail."""
    with pytest.raises(ValueError, match="Unknown entry"):
        parse_component_entries(["repomatic-audit"])


@pytest.mark.parametrize(
    ("entry", "match"),
    [
        ("nonexistent", "Unknown entry"),
        ("workflows/nonexistent.yaml", "Unknown file"),
        ("labels/nonexistent.toml", "Unknown file"),
        ("skills/nonexistent-skill", "Unknown file"),
        ("ruff/something", "does not support file-level"),
        ("pytest/something", "does not support file-level"),
    ],
)
def test_parse_component_entries_rejects_invalid_entries(
    entry: str, match: str
) -> None:
    """Invalid entries produce hard ValueError failures."""
    with pytest.raises(ValueError, match=match):
        parse_component_entries([entry])


# --- Qualified CLI selection tests ---


def test_init_single_skill(tmp_path: Path):
    """Qualified entry creates only the specified skill."""
    result = run_init(output_dir=tmp_path, components=("skills/repomatic-topics",))
    assert result.created == [".claude/skills/repomatic-topics/SKILL.md"]


def test_init_multiple_qualified_same_component(tmp_path: Path):
    """Multiple qualified entries for same component creates all specified."""
    result = run_init(
        output_dir=tmp_path,
        components=("skills/repomatic-topics", "skills/repomatic-audit"),
    )
    created_set = set(result.created)
    assert created_set == {
        ".claude/skills/repomatic-topics/SKILL.md",
        ".claude/skills/repomatic-audit/SKILL.md",
    }


def test_init_bare_overrides_qualified(tmp_path: Path):
    """Bare component name includes all files, ignoring qualified filter."""
    result = run_init(
        output_dir=tmp_path,
        components=("skills", "skills/repomatic-topics"),
    )
    # All skills created (minus auto-excluded awesome-triage and
    # translation-sync for non-awesome).
    total_skills = len(COMPONENT_FILES["skills"])
    assert len(result.created) == total_skills - 2


def test_init_mixed_bare_and_qualified(tmp_path: Path):
    """Bare + qualified for different components work independently."""
    result = run_init(
        output_dir=tmp_path,
        components=("labels", "skills/repomatic-topics"),
    )
    created_set = set(result.created)
    assert "labels.toml" in created_set
    assert ".github/labeller-file-based.yaml" in created_set
    assert ".github/labeller-content-based.yaml" in created_set
    assert ".claude/skills/repomatic-topics/SKILL.md" in created_set
    assert len(created_set) == 4


def test_init_qualified_workflow(tmp_path: Path):
    """Single workflow file selection."""
    result = run_init(
        output_dir=tmp_path,
        components=("workflows/autofix.yaml",),
    )
    assert len(result.created) == 1
    assert result.created[0] == ".github/workflows/autofix.yaml"


def test_init_qualified_auto_exclusion_still_applies(tmp_path: Path):
    """awesome-triage is auto-excluded even when explicitly selected on non-awesome repo."""
    result = run_init(
        output_dir=tmp_path,
        components=("skills/awesome-triage",),
        repo_slug="user/some-project",
    )
    assert not result.created


def test_init_qualified_selection_context_in_error():
    """Qualified selection uses 'selection' context in error messages."""
    with pytest.raises(ValueError, match="Unknown selection"):
        run_init(output_dir=Path("/tmp"), components=("nonexistent",))


def test_init_awesome_template_not_auto_included_with_explicit_components(
    tmp_path: Path,
):
    """awesome-template is not auto-included when explicit components are given."""
    result = run_init(
        output_dir=tmp_path,
        components=("skills/repomatic-topics",),
        repo_slug="user/awesome-list",
    )
    created_set = set(result.created)
    assert created_set == {".claude/skills/repomatic-topics/SKILL.md"}
