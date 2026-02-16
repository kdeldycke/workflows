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

from gha_utils.init_project import (
    COMPONENT_FILES,
    DEFAULT_COMPONENTS,
    INIT_CONFIGS,
    _to_pyproject_format,
    default_version_pin,
    export_content,
    get_data_content,
    init_config,
    run_init,
)
from gha_utils.github.workflow_sync import REUSABLE_WORKFLOWS

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


def test_config_type_has_required_fields() -> None:
    """Verify that each config type has all required fields."""
    for name, config in INIT_CONFIGS.items():
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


def test_bundled_renovate_matches_processed_root() -> None:
    """Verify bundled renovate.json5 matches processed root file.

    The root ``renovate.json5`` is the source of truth. The bundled version
    in ``gha_utils/data/`` should match the root file with repo-specific
    settings (``assignees``, ``customManagers``) removed.

    If this test fails, regenerate the bundled file by running:
        uv run gha-utils init renovate --output-dir gha_utils/data --overwrite
    """
    # Read the root file and process it (same logic as _get_renovate_config).
    root_path = Path(__file__).parent.parent / "renovate.json5"
    assert root_path.exists(), "Root renovate.json5 not found"

    content = root_path.read_text(encoding="UTF-8")

    # Remove assignees line.
    content = re.sub(r"\s*assignees:\s*\[[^\]]*\],?\n", "\n", content)

    # Remove customManagers section and its preceding comment.
    cm_match = re.search(
        r"\n\s*//[^\n]*[Cc]ustom [Mm]anagers[^\n]*\n\s*customManagers:", content
    )
    if cm_match:
        va_end = re.search(r"(vulnerabilityAlerts:\s*\{[^}]*\},?\s*)\n", content)
        if va_end:
            content = content[: va_end.end()].rstrip().rstrip(",") + "\n}\n"

    # Read the bundled file and compare.
    bundled_content = get_data_content("renovate.json5")

    assert bundled_content.strip() == content.strip(), (
        "Bundled renovate.json5 is out of sync with root file.\n"
        "Regenerate with: uv run gha-utils init renovate"
        " --output-dir gha_utils/data --overwrite"
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
    assert "workflows" in DEFAULT_COMPONENTS
    # Tool configs should not be in defaults.
    assert "ruff" not in DEFAULT_COMPONENTS
    assert "bumpversion" not in DEFAULT_COMPONENTS


def test_init_creates_all_default_files(tmp_path: Path):
    """Verify all default component files are created."""
    result = run_init(output_dir=tmp_path)

    # Default components: changelog, labels, renovate, workflows.
    # 10 workflows + 3 label files + 1 renovate + 1 changelog = 15.
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
    """Verify second run creates nothing and skips everything."""
    result1 = run_init(output_dir=tmp_path)
    assert len(result1.created) > 0
    assert len(result1.skipped) == 0

    result2 = run_init(output_dir=tmp_path)
    assert len(result2.created) == 0
    assert len(result2.skipped) == len(result1.created)


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


def test_init_overwrite(tmp_path: Path):
    """Verify --overwrite replaces existing files."""
    changelog = tmp_path / "changelog.md"
    changelog.write_text("# Old content\n", encoding="UTF-8")

    result = run_init(
        output_dir=tmp_path,
        components=("changelog",),
        overwrite=True,
    )

    assert "changelog.md" in result.created
    assert len(result.skipped) == 0
    # Content should be replaced.
    content = changelog.read_text(encoding="UTF-8")
    assert content.startswith("# Changelog")


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
