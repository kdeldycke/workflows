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
    get_config_content,
    init_config,
)

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]


class TestConfigRegistry:
    """Tests for the configuration type registry."""

    def test_supported_config_types(self) -> None:
        """Verify that expected config types are registered."""
        assert "ruff" in CONFIG_TYPES
        assert "bumpversion" in CONFIG_TYPES

    def test_config_type_has_required_fields(self) -> None:
        """Verify that each config type has all required fields."""
        for name, config in CONFIG_TYPES.items():
            assert config.name == name
            assert config.filename
            assert config.tool_section
            assert config.description


class TestGetConfigContent:
    """Tests for get_config_content function."""

    @pytest.mark.parametrize("config_type", list(CONFIG_TYPES.keys()))
    def test_returns_non_empty_string(self, config_type: str) -> None:
        """Verify that get_config_content returns a non-empty string."""
        content = get_config_content(config_type)
        assert isinstance(content, str)
        assert len(content) > 0

    @pytest.mark.parametrize("config_type", list(CONFIG_TYPES.keys()))
    def test_returns_valid_toml(self, config_type: str) -> None:
        """Verify that the returned content is valid TOML."""
        content = get_config_content(config_type)
        parsed = tomllib.loads(content)
        assert isinstance(parsed, dict)

    @pytest.mark.parametrize("config_type", list(CONFIG_TYPES.keys()))
    def test_has_tool_section(self, config_type: str) -> None:
        """Verify that the config has the expected [tool.X] section."""
        content = get_config_content(config_type)
        parsed = tomllib.loads(content)
        config = CONFIG_TYPES[config_type]

        assert "tool" in parsed
        # Extract the tool name from "tool.ruff" -> "ruff".
        tool_name = config.tool_section.split(".", 1)[1]
        assert tool_name in parsed["tool"]

    def test_unknown_config_type_raises_error(self) -> None:
        """Verify that an unknown config type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown config type"):
            get_config_content("nonexistent")


class TestRuffConfig:
    """Tests specific to the Ruff configuration."""

    def test_has_preview_enabled(self) -> None:
        """Verify that preview mode is enabled."""
        content = get_config_content("ruff")
        parsed = tomllib.loads(content)
        ruff = parsed["tool"]["ruff"]
        assert ruff.get("preview") is True

    def test_has_fix_settings(self) -> None:
        """Verify that fix settings are configured."""
        content = get_config_content("ruff")
        parsed = tomllib.loads(content)
        ruff = parsed["tool"]["ruff"]

        assert ruff.get("fix") is True
        assert ruff.get("unsafe-fixes") is True
        assert ruff.get("show-fixes") is True

    def test_has_lint_section(self) -> None:
        """Verify that the lint section exists with expected settings."""
        content = get_config_content("ruff")
        parsed = tomllib.loads(content)
        ruff = parsed["tool"]["ruff"]

        assert "lint" in ruff
        lint = ruff["lint"]
        assert lint.get("future-annotations") is True
        assert "ignore" in lint
        assert isinstance(lint["ignore"], list)

    @pytest.mark.parametrize("expected_ignore", ["D400", "ERA001"])
    def test_has_expected_ignore_rules(self, expected_ignore: str) -> None:
        """Verify that expected rules are in the ignore list."""
        content = get_config_content("ruff")
        parsed = tomllib.loads(content)
        ignore = parsed["tool"]["ruff"]["lint"]["ignore"]
        assert expected_ignore in ignore

    def test_has_format_section(self) -> None:
        """Verify that the format section exists with docstring formatting enabled."""
        content = get_config_content("ruff")
        parsed = tomllib.loads(content)
        ruff = parsed["tool"]["ruff"]

        assert "format" in ruff
        assert ruff["format"].get("docstring-code-format") is True


class TestMypyConfig:
    """Tests specific to the mypy configuration."""

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
        content = get_config_content("mypy")
        parsed = tomllib.loads(content)
        mypy = parsed["tool"]["mypy"]
        assert setting in mypy
        assert mypy[setting] is True


class TestPytestConfig:
    """Tests specific to the pytest configuration."""

    def test_has_addopts(self) -> None:
        """Verify that addopts list is present."""
        content = get_config_content("pytest")
        parsed = tomllib.loads(content)
        pytest_config = parsed["tool"]["pytest"]

        assert "addopts" in pytest_config
        assert isinstance(pytest_config["addopts"], list)
        assert len(pytest_config["addopts"]) > 0

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
        content = get_config_content("pytest")
        parsed = tomllib.loads(content)
        addopts = parsed["tool"]["pytest"]["addopts"]
        assert expected_opt in addopts

    def test_has_xfail_strict(self) -> None:
        """Verify that xfail_strict is enabled."""
        content = get_config_content("pytest")
        parsed = tomllib.loads(content)
        pytest_config = parsed["tool"]["pytest"]
        assert pytest_config.get("xfail_strict") is True


class TestBumpversionConfig:
    """Tests specific to the bumpversion configuration."""

    def test_has_required_settings(self) -> None:
        """Verify that the configuration has required bumpversion settings."""
        content = get_config_content("bumpversion")
        parsed = tomllib.loads(content)
        bumpversion = parsed["tool"]["bumpversion"]

        assert "current_version" in bumpversion
        assert "allow_dirty" in bumpversion
        assert "ignore_missing_files" in bumpversion

    def test_has_files_section(self) -> None:
        """Verify that the configuration has file patterns defined."""
        content = get_config_content("bumpversion")
        parsed = tomllib.loads(content)
        bumpversion = parsed["tool"]["bumpversion"]

        assert "files" in bumpversion
        assert isinstance(bumpversion["files"], list)
        assert len(bumpversion["files"]) > 0


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
            result = init_config("bumpversion", path)
            assert result is not None
            assert 'name = "test"' in result
            assert 'version = "1.0.0"' in result
            assert "[tool.bumpversion]" in result
        finally:
            path.unlink()

    def test_unknown_config_type_raises_error(self) -> None:
        """Verify that an unknown config type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown config type"):
            init_config("nonexistent", Path("pyproject.toml"))
