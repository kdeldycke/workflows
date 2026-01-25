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
"""Tests for bundled configuration templates."""

from __future__ import annotations

import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from gha_utils.bundled_config import (
    CONFIG_TYPES,
    TOOL_SECTION_ORDER,
    _to_pyproject_format,
    export_content,
    get_config_content,
    init_config,
    validate_tool_section_order,
)

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]


class TestConfigRegistry:
    """Tests for the configuration type registry."""

    def test_supported_config_types(self) -> None:
        """Verify that expected config types are registered."""
        assert "mypy" in CONFIG_TYPES
        assert "ruff" in CONFIG_TYPES
        assert "pytest" in CONFIG_TYPES
        assert "bumpversion" in CONFIG_TYPES

    def test_config_type_has_required_fields(self) -> None:
        """Verify that each config type has all required fields."""
        for name, config in CONFIG_TYPES.items():
            assert config.filename
            assert config.tool_section
            assert config.description


class TestExportContent:
    """Tests for export_content function (native format)."""

    @pytest.mark.parametrize("config_type", list(CONFIG_TYPES.keys()))
    def test_returns_non_empty_string(self, config_type: str) -> None:
        """Verify that export_content returns a non-empty string."""
        config = CONFIG_TYPES[config_type]
        content = export_content(config.filename)
        assert isinstance(content, str)
        assert len(content) > 0

    @pytest.mark.parametrize("config_type", list(CONFIG_TYPES.keys()))
    def test_returns_valid_toml(self, config_type: str) -> None:
        """Verify that the returned content is valid TOML."""
        config = CONFIG_TYPES[config_type]
        content = export_content(config.filename)
        parsed = tomllib.loads(content)
        assert isinstance(parsed, dict)

    @pytest.mark.parametrize("config_type", list(CONFIG_TYPES.keys()))
    def test_native_format_no_tool_prefix(self, config_type: str) -> None:
        """Verify that native format does not have [tool.X] prefix."""
        config = CONFIG_TYPES[config_type]
        content = export_content(config.filename)
        parsed = tomllib.loads(content)
        # Native format should NOT have a "tool" key at the root.
        assert "tool" not in parsed

    def test_unknown_file_raises_error(self) -> None:
        """Verify that an unknown file raises ValueError."""
        with pytest.raises(ValueError, match="Unknown file"):
            export_content("nonexistent.toml")


class TestToPyprojectFormat:
    """Tests for the _to_pyproject_format transformation."""

    def test_adds_root_section(self) -> None:
        """Verify that root section is added before first key."""
        native = "key = true\n"
        result = _to_pyproject_format(native, "tool.mypy")
        assert "[tool.mypy]" in result
        assert result.index("[tool.mypy]") < result.index("key = true")

    def test_transforms_subsections(self) -> None:
        """Verify that subsections get the tool prefix."""
        native = "[lint]\nrule = true\n"
        result = _to_pyproject_format(native, "tool.ruff")
        assert "[tool.ruff.lint]" in result

    def test_transforms_array_sections(self) -> None:
        """Verify that array sections get the tool prefix."""
        native = "[[files]]\nfilename = 'test.py'\n"
        result = _to_pyproject_format(native, "tool.bumpversion")
        assert "[[tool.bumpversion.files]]" in result

    def test_preserves_comments(self) -> None:
        """Verify that comments are preserved."""
        native = "# This is a comment\nkey = true\n"
        result = _to_pyproject_format(native, "tool.mypy")
        assert "# This is a comment" in result

    def test_full_ruff_transform(self) -> None:
        """Verify full transformation of ruff config."""
        native = export_content("ruff.toml")
        result = _to_pyproject_format(native, "tool.ruff")
        parsed = tomllib.loads(result)

        assert "tool" in parsed
        assert "ruff" in parsed["tool"]
        assert parsed["tool"]["ruff"].get("preview") is True
        assert "lint" in parsed["tool"]["ruff"]
        assert "format" in parsed["tool"]["ruff"]


class TestRuffConfig:
    """Tests specific to the Ruff configuration (native format)."""

    def test_has_preview_enabled(self) -> None:
        """Verify that preview mode is enabled."""
        content = export_content("ruff.toml")
        parsed = tomllib.loads(content)
        assert parsed.get("preview") is True

    def test_has_fix_settings(self) -> None:
        """Verify that fix settings are configured."""
        content = export_content("ruff.toml")
        parsed = tomllib.loads(content)

        assert parsed.get("fix") is True
        assert parsed.get("unsafe-fixes") is True
        assert parsed.get("show-fixes") is True

    def test_has_lint_section(self) -> None:
        """Verify that the lint section exists with expected settings."""
        content = export_content("ruff.toml")
        parsed = tomllib.loads(content)

        assert "lint" in parsed
        lint = parsed["lint"]
        assert lint.get("future-annotations") is True
        assert "ignore" in lint
        assert isinstance(lint["ignore"], list)

    @pytest.mark.parametrize("expected_ignore", ["D400", "ERA001"])
    def test_has_expected_ignore_rules(self, expected_ignore: str) -> None:
        """Verify that expected rules are in the ignore list."""
        content = export_content("ruff.toml")
        parsed = tomllib.loads(content)
        ignore = parsed["lint"]["ignore"]
        assert expected_ignore in ignore

    def test_has_format_section(self) -> None:
        """Verify that the format section exists with docstring formatting enabled."""
        content = export_content("ruff.toml")
        parsed = tomllib.loads(content)

        assert "format" in parsed
        assert parsed["format"].get("docstring-code-format") is True


class TestMypyConfig:
    """Tests specific to the mypy configuration (native format)."""

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
    def test_has_expected_settings(self, setting: str) -> None:
        """Verify that expected settings are present."""
        content = export_content("mypy.toml")
        parsed = tomllib.loads(content)
        assert setting in parsed
        assert parsed[setting] is True


class TestPytestConfig:
    """Tests specific to the pytest configuration (native format)."""

    def test_has_addopts(self) -> None:
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
    def test_has_expected_addopts(self, expected_opt: str) -> None:
        """Verify that expected options are in addopts."""
        content = export_content("pytest.toml")
        parsed = tomllib.loads(content)
        addopts = parsed["addopts"]
        assert expected_opt in addopts

    def test_has_xfail_strict(self) -> None:
        """Verify that xfail_strict is enabled."""
        content = export_content("pytest.toml")
        parsed = tomllib.loads(content)
        assert parsed.get("xfail_strict") is True


class TestBumpversionConfig:
    """Tests specific to the bumpversion configuration (native format)."""

    def test_has_required_settings(self) -> None:
        """Verify that the configuration has required bumpversion settings."""
        content = export_content("bumpversion.toml")
        parsed = tomllib.loads(content)

        assert "current_version" in parsed
        assert "allow_dirty" in parsed
        assert "ignore_missing_files" in parsed

    def test_has_files_section(self) -> None:
        """Verify that the configuration has file patterns defined."""
        content = export_content("bumpversion.toml")
        parsed = tomllib.loads(content)

        assert "files" in parsed
        assert isinstance(parsed["files"], list)
        assert len(parsed["files"]) > 0


class TestInitConfig:
    """Tests for init_config function."""

    def test_adds_config_to_empty_pyproject(self) -> None:
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
            # Verify subsections are transformed.
            assert "[tool.ruff.lint]" in result
            assert "[tool.ruff.format]" in result
        finally:
            path.unlink()

    def test_adds_bumpversion_with_array_sections(self) -> None:
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

    def test_returns_none_if_section_exists(self) -> None:
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

    def test_preserves_existing_content(self) -> None:
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

    def test_unknown_config_type_raises_error(self) -> None:
        """Verify that an unknown config type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown config type"):
            init_config("nonexistent", Path("pyproject.toml"))


class TestBackwardsCompatibility:
    """Tests for backwards compatibility aliases."""

    def test_get_config_content_alias(self) -> None:
        """Verify get_config_content works as alias."""
        content = get_config_content("ruff")
        assert isinstance(content, str)
        assert len(content) > 0


class TestToolSectionOrder:
    """Tests for TOOL_SECTION_ORDER constant."""

    def test_has_expected_sections(self) -> None:
        """Verify that expected sections are in the order list."""
        assert "tool.uv" in TOOL_SECTION_ORDER
        assert "tool.ruff" in TOOL_SECTION_ORDER
        assert "tool.pytest" in TOOL_SECTION_ORDER
        assert "tool.mypy" in TOOL_SECTION_ORDER
        assert "tool.nuitka" in TOOL_SECTION_ORDER
        assert "tool.bumpversion" in TOOL_SECTION_ORDER
        assert "tool.typos" in TOOL_SECTION_ORDER

    def test_order_is_correct(self) -> None:
        """Verify that sections are in the expected order."""
        expected = (
            "tool.uv",
            "tool.ruff",
            "tool.pytest",
            "tool.mypy",
            "tool.nuitka",
            "tool.bumpversion",
            "tool.typos",
        )
        assert TOOL_SECTION_ORDER == expected


class TestValidateToolSectionOrder:
    """Tests for validate_tool_section_order function."""

    def test_correct_order_returns_empty_list(self) -> None:
        """Verify that a correctly ordered file returns no violations."""
        content = """[project]
name = "test"

[tool.uv]
exclude-newer = "2026-01-01T00:00:00Z"

[tool.ruff]
preview = true

[tool.pytest]
xfail_strict = true

[tool.mypy]
warn_unused_configs = true

[tool.bumpversion]
current_version = "1.0.0"
"""
        with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            violations = validate_tool_section_order(path)
            assert violations == []
        finally:
            path.unlink()

    def test_incorrect_order_returns_violations(self) -> None:
        """Verify that incorrectly ordered sections return violations."""
        content = """[project]
name = "test"

[tool.mypy]
warn_unused_configs = true

[tool.ruff]
preview = true

[tool.uv]
exclude-newer = "2026-01-01T00:00:00Z"
"""
        with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            violations = validate_tool_section_order(path)
            assert len(violations) > 0
            # tool.ruff appears after tool.mypy but should come before it.
            violation_sections = [v.section for v in violations]
            assert "tool.ruff" in violation_sections
            assert "tool.uv" in violation_sections
        finally:
            path.unlink()

    def test_ignores_unknown_sections(self) -> None:
        """Verify that sections not in TOOL_SECTION_ORDER are ignored."""
        content = """[project]
name = "test"

[tool.unknown]
key = true

[tool.uv]
exclude-newer = "2026-01-01T00:00:00Z"

[tool.another_unknown]
key = false
"""
        with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            violations = validate_tool_section_order(path)
            assert violations == []
        finally:
            path.unlink()

    def test_handles_subsections(self) -> None:
        """Verify that subsections are grouped with their parent section."""
        content = """[project]
name = "test"

[tool.ruff]
preview = true

[tool.ruff.lint]
future-annotations = true

[tool.ruff.format]
docstring-code-format = true

[tool.pytest]
xfail_strict = true
"""
        with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            violations = validate_tool_section_order(path)
            assert violations == []
        finally:
            path.unlink()

    def test_missing_file_returns_empty_list(self) -> None:
        """Verify that a missing file returns an empty list."""
        violations = validate_tool_section_order(Path("/nonexistent/path/pyproject.toml"))
        assert violations == []

    def test_violation_includes_line_number(self) -> None:
        """Verify that violations include line numbers."""
        content = """[project]
name = "test"

[tool.mypy]
warn_unused_configs = true

[tool.ruff]
preview = true
"""
        with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            violations = validate_tool_section_order(path)
            assert len(violations) > 0
            # Line numbers should be present.
            for v in violations:
                assert v.line_number is not None
                assert v.line_number > 0
        finally:
            path.unlink()

    def test_violation_str_representation(self) -> None:
        """Verify that violations have a readable string representation."""
        content = """[project]
name = "test"

[tool.mypy]
warn_unused_configs = true

[tool.ruff]
preview = true
"""
        with NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)

        try:
            violations = validate_tool_section_order(path)
            assert len(violations) > 0
            for v in violations:
                msg = str(v)
                assert "[" in msg
                assert "]" in msg
                assert "should appear after" in msg
        finally:
            path.unlink()
