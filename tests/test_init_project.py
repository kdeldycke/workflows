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

import re
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from repomatic.github.workflow_sync import ALL_WORKFLOW_FILES, REUSABLE_WORKFLOWS
from repomatic.init_project import (
    ALL_COMPONENTS,
    COMPONENT_FILES,
    DEFAULT_COMPONENTS,
    EXPORTABLE_FILES,
    INIT_CONFIGS,
    _file_id,
    _to_pyproject_format,
    _update_bumpversion_config,
    _valid_file_ids,
    default_version_pin,
    export_content,
    get_data_content,
    init_config,
    parse_exclude,
    run_init,
)

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]


# --- Bundled data and export tests ---


def test_supported_config_types() -> None:
    """Verify that expected config types are registered."""
    assert "mypy" in INIT_CONFIGS
    assert "ruff" in INIT_CONFIGS
    assert "pytest" in INIT_CONFIGS
    assert "bumpversion" in INIT_CONFIGS
    assert "typos" in INIT_CONFIGS


def test_config_type_has_required_fields() -> None:
    """Verify that each config type has all required fields."""
    for config in INIT_CONFIGS.values():
        assert config.filename
        assert config.tool_section
        assert config.description


@pytest.mark.parametrize("config_type", list(INIT_CONFIGS.keys()))
def test_returns_non_empty_string(config_type: str) -> None:
    """Verify that export_content returns a non-empty string."""
    config = INIT_CONFIGS[config_type]
    content = export_content(config.filename)
    assert isinstance(content, str)
    assert len(content) > 0


@pytest.mark.parametrize("config_type", list(INIT_CONFIGS.keys()))
def test_returns_valid_toml(config_type: str) -> None:
    """Verify that the returned content is valid TOML."""
    config = INIT_CONFIGS[config_type]
    content = export_content(config.filename)
    parsed = tomllib.loads(content)
    assert isinstance(parsed, dict)


@pytest.mark.parametrize("config_type", list(INIT_CONFIGS.keys()))
def test_native_format_no_tool_prefix(config_type: str) -> None:
    """Verify that native format does not have [tool.X] prefix."""
    config = INIT_CONFIGS[config_type]
    content = export_content(config.filename)
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


@pytest.mark.parametrize("config_type", list(INIT_CONFIGS.keys()))
def test_template_matches_own_pyproject(config_type: str) -> None:
    """Verify bundled template stays in sync with repomatic's own config.

    Template keys (minus intentional exclusions) must match the corresponding
    ``[tool.*]`` section. List keys marked as superset require every template
    entry to appear in own config, but own config may have extras.
    """
    config = INIT_CONFIGS[config_type]
    template = tomllib.loads(export_content(config.filename))

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
    # Read the root file and process it (same logic as _get_renovate_config).
    root_path = Path(__file__).parent.parent / "renovate.json5"
    assert root_path.exists(), "Root renovate.json5 not found"

    content = root_path.read_text(encoding="UTF-8")

    # Remove assignees line.
    content = re.sub(r"\s*assignees:\s*\[[^\]]*\],?\n", "\n", content)

    # Remove the self-referencing uv customManagers entry.
    content = re.sub(
        r'\n    \{\n      description: "Update uv version in postUpgradeTasks'
        r' download URL\.",\n.*?\n    \},',
        "",
        content,
        flags=re.DOTALL,
    )

    # Read the bundled file and compare.
    bundled_content = get_data_content("renovate.json5")

    assert bundled_content.strip() == content.strip(), (
        "Bundled renovate.json5 is out of sync with root file.\n"
        "Regenerate with: uv run repomatic init renovate"
        " --output-dir repomatic/data"
    )


def test_bundled_zizmor_matches_root() -> None:
    """Verify bundled zizmor.yaml matches the root config file.

    The root ``zizmor.yaml`` is the source of truth. The bundled version must
    be identical.
    """
    root_path = Path(__file__).parent.parent / "zizmor.yaml"
    assert root_path.exists(), "Root zizmor.yaml not found"

    root_content = root_path.read_text(encoding="UTF-8")
    bundled_content = get_data_content("zizmor.yaml")

    assert bundled_content.strip() == root_content.strip(), (
        "Bundled zizmor.yaml is out of sync with root file."
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
        '[project]\nname = "test"\n\n[tool.repomatic]\nexclude = []\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    result = run_init(output_dir=tmp_path)

    # All components: changelog, labels, renovate, skills, workflows, zizmor.
    config_file_count = sum(len(v) for v in COMPONENT_FILES.values())
    expected_count = len(REUSABLE_WORKFLOWS) + config_file_count + 1
    assert len(result.created) == expected_count
    assert len(result.skipped) == 0
    assert len(result.warnings) == 0

    # Verify workflow files exist.
    for filename in REUSABLE_WORKFLOWS:
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
    run_init(output_dir=tmp_path)
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
    """Verify second run updates managed files and skips changelog."""
    result1 = run_init(output_dir=tmp_path)
    assert len(result1.created) > 0
    assert len(result1.updated) == 0
    assert len(result1.skipped) == 0

    result2 = run_init(output_dir=tmp_path)
    assert len(result2.created) == 0
    # Managed files are always overwritten (reported as updated).
    managed_count = len(result1.created) - 1  # Minus changelog.
    assert len(result2.updated) == managed_count
    # Only changelog is skipped (never overwritten).
    assert result2.skipped == ["changelog.md"]


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
    """Verify only skill files are created."""
    result = run_init(output_dir=tmp_path, components=("skills",))

    created_set = set(result.created)
    assert len(created_set) == 9

    # Verify all skill files are created.
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
    ):
        rel = f".claude/skills/{name}/SKILL.md"
        assert rel in created_set
        assert (tmp_path / ".claude" / "skills" / name / "SKILL.md").exists()

    # No workflows or changelog should be created.
    assert "changelog.md" not in created_set


def test_skills_consistency():
    """Verify all .claude/skills/ directories have matching entries in code.

    Guards against adding a skill definition to ``.claude/skills/`` without
    registering it in ``COMPONENT_FILES``, ``_SKILL_PHASES``, and the
    ``repomatic/data/`` symlinks.
    """
    from repomatic.cli import _SKILL_PHASES

    # Collect skill directories from the filesystem.
    skills_dir = Path(__file__).resolve().parents[1] / ".claude" / "skills"
    fs_skills = {p.parent.name for p in skills_dir.glob("*/SKILL.md")}

    # Collect skills registered in COMPONENT_FILES.
    component_skills = {
        rel_path.split("/")[2] for _, rel_path in COMPONENT_FILES.get("skills", ())
    }

    # Collect skills registered in _SKILL_PHASES.
    phase_skills = set(_SKILL_PHASES)

    # Collect data symlinks.
    data_dir = Path(__file__).resolve().parents[1] / "repomatic" / "data"
    data_skills = {
        p.stem.removeprefix("skill-") for p in data_dir.glob("skill-repomatic-*.md")
    }

    assert fs_skills == component_skills, (
        f"COMPONENT_FILES mismatch: "
        f"missing={fs_skills - component_skills}, "
        f"extra={component_skills - fs_skills}"
    )
    assert fs_skills == data_skills, (
        f"Data symlinks mismatch: "
        f"missing={fs_skills - data_skills}, "
        f"extra={data_skills - fs_skills}"
    )
    assert fs_skills == phase_skills, (
        f"_SKILL_PHASES mismatch: "
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
    for filename in REUSABLE_WORKFLOWS:
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


def test_init_zizmor_never_overwritten(tmp_path: Path):
    """Verify an existing zizmor.yaml is never overwritten."""
    zizmor = tmp_path / "zizmor.yaml"
    zizmor.write_text("# Custom config\n", encoding="UTF-8")

    result = run_init(
        output_dir=tmp_path,
        components=("zizmor",),
    )

    assert "zizmor.yaml" in result.skipped
    assert len(result.created) == 0
    assert len(result.updated) == 0
    # Content should be preserved.
    content = zizmor.read_text(encoding="UTF-8")
    assert content == "# Custom config\n"


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
    for filename in REUSABLE_WORKFLOWS:
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
    """Verify default exclude skips labels, skills, and zizmor."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    result = run_init(output_dir=tmp_path)

    created_set = set(result.created)
    # Labels, skills, yamllint, and zizmor are excluded by default.
    assert ".yamllint.yaml" not in created_set
    assert "labels.toml" not in created_set
    assert "zizmor.yaml" not in created_set
    for _, rel_path in COMPONENT_FILES.get("skills", ()):
        assert rel_path not in created_set

    # Other default components should still be created.
    assert "changelog.md" in created_set
    assert "renovate.json5" in created_set

    assert result.excluded == ["labels", "skills", "yamllint", "zizmor"]


def test_init_respects_exclude_components(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify exclude config skips listed components."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.repomatic]\n"
        'exclude = ["skills", "zizmor"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    result = run_init(output_dir=tmp_path)

    created_set = set(result.created)
    # Zizmor and skill files should not be created.
    assert "zizmor.yaml" not in created_set
    for _, rel_path in COMPONENT_FILES.get("skills", ()):
        assert rel_path not in created_set

    # Other default components should still be created.
    assert "changelog.md" in created_set
    assert "renovate.json5" in created_set

    assert result.excluded == ["skills", "zizmor"]


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


def test_init_respects_exclude_label_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify exclude config with label file entries skips those label files."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.repomatic]\n"
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
        'exclude = ["zizmor", "workflows/debug.yaml", "skills/repomatic-audit"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    result = run_init(output_dir=tmp_path)

    created_set = set(result.created)
    assert "zizmor.yaml" not in created_set
    assert ".github/workflows/debug.yaml" not in created_set
    assert ".claude/skills/repomatic-audit/SKILL.md" not in created_set

    # Non-excluded items should be created.
    assert ".github/workflows/lint.yaml" in created_set
    assert ".claude/skills/repomatic-init/SKILL.md" in created_set


def test_init_explicit_components_bypass_exclude(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Verify explicit CLI components override exclusion."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test"\n\n'
        "[tool.repomatic]\n"
        'exclude = ["zizmor", "skills", "changelog"]\n',
        encoding="UTF-8",
    )
    monkeypatch.chdir(tmp_path)

    # Explicitly request excluded components.
    result = run_init(output_dir=tmp_path, components=("zizmor", "changelog"))

    created_set = set(result.created)
    # Explicitly requested components should be created despite exclusion.
    assert "zizmor.yaml" in created_set
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

    with pytest.raises(ValueError, match="Unknown exclude entry"):
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
        "Data files not in EXPORTABLE_FILES: "
        f"{sorted(unregistered)}"
    )


def test_every_data_file_maps_to_a_component() -> None:
    """Every file in EXPORTABLE_FILES belongs to exactly one component or INIT_CONFIGS."""
    # Collect all filenames claimed by FILE_COMPONENTS.
    component_filenames: set[str] = set()
    for entries in COMPONENT_FILES.values():
        for source_filename, _ in entries:
            component_filenames.add(source_filename)

    # Collect all filenames claimed by INIT_CONFIGS (tool components).
    tool_filenames = {cfg.filename for cfg in INIT_CONFIGS.values()}

    # Collect workflow filenames from EXPORTABLE_FILES.
    workflow_filenames = {
        fname
        for fname, path in EXPORTABLE_FILES.items()
        if path and path.startswith("./.github/workflows/")
    }

    covered = component_filenames | tool_filenames | workflow_filenames
    uncovered = set(EXPORTABLE_FILES.keys()) - covered
    assert not uncovered, (
        "EXPORTABLE_FILES entries not mapped to any component: "
        f"{sorted(uncovered)}"
    )


def test_no_data_file_claimed_by_multiple_components() -> None:
    """Each data filename must belong to at most one component."""
    seen: dict[str, str] = {}
    duplicates: list[str] = []

    # Check FILE_COMPONENTS.
    for component, entries in COMPONENT_FILES.items():
        for source_filename, _ in entries:
            if source_filename in seen:
                duplicates.append(
                    f"{source_filename!r} claimed by both"
                    f" {seen[source_filename]!r} and {component!r}"
                )
            seen[source_filename] = component

    # Check INIT_CONFIGS.
    for component, cfg in INIT_CONFIGS.items():
        if cfg.filename in seen:
            duplicates.append(
                f"{cfg.filename!r} claimed by both"
                f" {seen[cfg.filename]!r} and {component!r}"
            )
        seen[cfg.filename] = component

    assert not duplicates, f"Duplicate file mappings: {duplicates}"


def test_valid_file_ids_cover_all_multi_file_components() -> None:
    """Components with multiple files must report valid file identifiers."""
    for component in ("workflows", "labels", "skills"):
        ids = _valid_file_ids(component)
        assert ids, f"_valid_file_ids({component!r}) returned empty set"


def test_workflow_file_ids_match_all_workflow_files() -> None:
    """_valid_file_ids('workflows') must match ALL_WORKFLOW_FILES."""
    assert _valid_file_ids("workflows") == frozenset(ALL_WORKFLOW_FILES)


def test_component_file_ids_match_component_files() -> None:
    """_valid_file_ids must return identifiers matching COMPONENT_FILES entries."""
    for component in COMPONENT_FILES:
        expected = frozenset(
            _file_id(component, rel) for _, rel in COMPONENT_FILES[component]
        )
        assert _valid_file_ids(component) == expected


def test_tool_components_have_no_file_ids() -> None:
    """Tool components (ruff, pytest, etc.) do not support file-level exclusion."""
    for component in INIT_CONFIGS:
        assert _valid_file_ids(component) == frozenset()


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
def test_parse_exclude_accepts_valid_qualified_entries(entry: str) -> None:
    """Qualified component/file entries are accepted by parse_exclude."""
    components, files = parse_exclude([entry])
    assert not components
    component = entry.split("/")[0]
    file_id = entry.split("/")[1]
    assert file_id in files[component]


@pytest.mark.parametrize("component", sorted(ALL_COMPONENTS.keys()))
def test_parse_exclude_accepts_all_bare_components(component: str) -> None:
    """Every component name is accepted as a bare exclude entry."""
    components, files = parse_exclude([component])
    assert component in components
    assert not files


def test_parse_exclude_bare_filename_without_component_fails() -> None:
    """Bare filenames like 'debug.yaml' must fail — qualified form required."""
    with pytest.raises(ValueError, match="Unknown exclude entry"):
        parse_exclude(["debug.yaml"])


def test_parse_exclude_bare_skill_name_without_component_fails() -> None:
    """Bare skill identifiers like 'repomatic-audit' must fail."""
    with pytest.raises(ValueError, match="Unknown exclude entry"):
        parse_exclude(["repomatic-audit"])


@pytest.mark.parametrize(
    ("entry", "match"),
    [
        ("nonexistent", "Unknown exclude entry"),
        ("workflows/nonexistent.yaml", "Unknown file"),
        ("labels/nonexistent.toml", "Unknown file"),
        ("skills/nonexistent-skill", "Unknown file"),
        ("ruff/something", "does not support file-level"),
        ("pytest/something", "does not support file-level"),
    ],
)
def test_parse_exclude_rejects_invalid_entries(entry: str, match: str) -> None:
    """Invalid exclude entries produce hard ValueError failures."""
    with pytest.raises(ValueError, match=match):
        parse_exclude([entry])
