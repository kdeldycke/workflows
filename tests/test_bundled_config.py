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
import re

from gha_utils.bundled_config import get_data_content
from gha_utils.bundled_config import (
    CONFIG_TYPES,
    _to_pyproject_format,
    export_content,
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
            # Verify dotted keys are preserved (ruff.toml uses dotted keys, not
            # sections).
            assert "lint.ignore" in result
            assert "format.docstring-code-format" in result
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


class TestRenovateConfigSync:
    """Tests to ensure bundled renovate.json5 stays in sync with root file."""

    def test_bundled_renovate_matches_processed_root(self) -> None:
        """Verify bundled renovate.json5 matches processed root file.

        The root ``renovate.json5`` is the source of truth. The bundled version
        in ``gha_utils/data/`` should match the root file with repo-specific
        settings (``assignees``, ``customManagers``) removed.

        If this test fails, regenerate the bundled file by running:
            uv run gha-utils bundled export renovate.json5 - > gha_utils/data/renovate.json5
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
            "Regenerate with: uv run gha-utils bundled export renovate.json5 - "
            "> gha_utils/data/renovate.json5"
        )


class TestBackwardsCompatibility:
    """Tests for backwards compatibility aliases."""

    def test_get_config_content_alias(self) -> None:
        """Verify get_config_content works as alias."""
        content = get_config_content("ruff")
        assert isinstance(content, str)
        assert len(content) > 0
