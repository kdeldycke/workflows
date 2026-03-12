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

"""Tests for the unified tool runner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from repomatic.tool_runner import (
    TOOL_REGISTRY,
    ToolSpec,
    get_data_file_path,
    resolve_config,
    resolve_config_source,
    run_tool,
)


# ---------------------------------------------------------------------------
# ToolSpec and registry validation
# ---------------------------------------------------------------------------


def test_tool_registry_entries_have_required_fields():
    """Every registry entry has a name, version, and package."""
    for name, spec in TOOL_REGISTRY.items():
        assert spec.name == name
        assert spec.version
        assert spec.package


def test_tool_registry_default_configs_exist():
    """Every ToolSpec with a default_config references a real data file."""
    for spec in TOOL_REGISTRY.values():
        if spec.default_config:
            with get_data_file_path(spec.default_config) as path:
                assert path.exists(), f"{spec.default_config} not found in data/"


def test_tool_registry_config_flag_required_for_default_config():
    """Tools with a default_config must have a config_flag to pass it."""
    for spec in TOOL_REGISTRY.values():
        if spec.default_config:
            assert spec.config_flag, (
                f"{spec.name} has default_config but no config_flag"
            )


def test_tool_registry_sorted_alphabetically():
    """Registry keys are sorted alphabetically."""
    keys = list(TOOL_REGISTRY.keys())
    assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# Config resolution
# ---------------------------------------------------------------------------


def test_resolve_config_reads_pyproject_skips():
    """Tools with reads_pyproject=True return empty args immediately."""
    spec = ToolSpec(
        name="ruff",
        version="0.15.0",
        package="ruff",
        reads_pyproject=True,
    )
    args, tmp = resolve_config(spec, tool_config={})
    assert args == []
    assert tmp is None


def test_resolve_config_native_file_wins(tmp_path, monkeypatch):
    """Native config file takes precedence over everything else."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".yamllint.yaml").write_text("rules: {}")

    spec = TOOL_REGISTRY["yamllint"]
    args, tmp = resolve_config(spec, tool_config={"rules": {"line-length": {"max": 80}}})
    assert args == []
    assert tmp is None


def test_resolve_config_pyproject_section(tmp_path, monkeypatch):
    """[tool.X] in pyproject.toml produces a temp config file."""
    monkeypatch.chdir(tmp_path)

    spec = TOOL_REGISTRY["yamllint"]
    tool_config = {"rules": {"line-length": {"max": 80}}}
    args, tmp = resolve_config(spec, tool_config=tool_config)

    try:
        assert len(args) == 2
        assert args[0] == "--config-file"
        assert Path(args[1]).exists()

        # Verify content.
        content = Path(args[1]).read_text(encoding="UTF-8")
        parsed = yaml.safe_load(content)
        assert parsed == tool_config

        assert tmp is not None
        assert tmp.exists()
    finally:
        if tmp:
            tmp.unlink(missing_ok=True)


def test_resolve_config_bundled_default(tmp_path, monkeypatch):
    """Bundled default is used when no native file or pyproject section exists."""
    monkeypatch.chdir(tmp_path)

    spec = TOOL_REGISTRY["yamllint"]
    args, tmp = resolve_config(spec, tool_config={})
    assert args == ["__bundled__"]
    assert tmp is None


def test_resolve_config_bare_invocation(tmp_path, monkeypatch):
    """Tool with no config at all gets bare invocation."""
    monkeypatch.chdir(tmp_path)

    spec = ToolSpec(
        name="sometool",
        version="1.0.0",
        package="sometool",
        native_format="yaml",
    )
    args, tmp = resolve_config(spec, tool_config={})
    assert args == []
    assert tmp is None


def test_resolve_config_empty_tool_config_is_not_match(tmp_path, monkeypatch):
    """An empty [tool.X] dict does not count as a config match."""
    monkeypatch.chdir(tmp_path)

    spec = TOOL_REGISTRY["zizmor"]
    args, tmp = resolve_config(spec, tool_config={})
    assert args == ["__bundled__"]
    assert tmp is None


# ---------------------------------------------------------------------------
# resolve_config_source
# ---------------------------------------------------------------------------


def test_resolve_config_source_native_file(tmp_path, monkeypatch):
    """Reports native config file when it exists."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "zizmor.yaml").write_text("rules: {}")

    result = resolve_config_source(TOOL_REGISTRY["zizmor"])
    assert result == "zizmor.yaml"


def test_resolve_config_source_bundled_default(tmp_path, monkeypatch):
    """Reports bundled default when no other config exists."""
    monkeypatch.chdir(tmp_path)

    result = resolve_config_source(TOOL_REGISTRY["yamllint"])
    assert result == "bundled default"


def test_resolve_config_source_pyproject_section(tmp_path, monkeypatch):
    """Reports [tool.X] when pyproject.toml has the section."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[tool.yamllint]\nrules = {line-length = {max = 80}}\n'
    )

    result = resolve_config_source(TOOL_REGISTRY["yamllint"])
    assert result == "[tool.yamllint] in pyproject.toml"


def test_resolve_config_source_bare(tmp_path, monkeypatch):
    """Reports (bare) for tool with no config anywhere."""
    monkeypatch.chdir(tmp_path)

    spec = ToolSpec(
        name="sometool",
        version="1.0.0",
        package="sometool",
    )
    result = resolve_config_source(spec)
    assert result == "(bare)"


# ---------------------------------------------------------------------------
# run_tool
# ---------------------------------------------------------------------------


def test_run_tool_unknown_tool():
    """Raise ValueError for unregistered tool names."""
    with pytest.raises(ValueError, match="Unknown tool"):
        run_tool("nonexistent-tool")


@patch("repomatic.tool_runner.subprocess.run")
@patch("repomatic.tool_runner.is_github_ci", return_value=False)
def test_run_tool_yamllint_bundled_default(mock_ci, mock_run, tmp_path, monkeypatch):
    """yamllint with bundled default builds the correct command."""
    monkeypatch.chdir(tmp_path)
    mock_run.return_value = MagicMock(returncode=0)

    exit_code = run_tool("yamllint", extra_args=(".",))

    assert exit_code == 0
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "uvx"
    assert "--no-progress" in cmd
    assert "yamllint==1.38.0" in " ".join(cmd)
    assert "--config-file" in cmd
    # default_flags are always present.
    assert "--strict" in cmd
    assert "." in cmd
    # Should not have CI flags.
    assert "--format" not in cmd


@patch("repomatic.tool_runner.subprocess.run")
@patch("repomatic.tool_runner.is_github_ci", return_value=True)
def test_run_tool_ci_flags(mock_ci, mock_run, tmp_path, monkeypatch):
    """CI flags are appended when GITHUB_ACTIONS is set."""
    monkeypatch.chdir(tmp_path)
    mock_run.return_value = MagicMock(returncode=0)

    run_tool("yamllint", extra_args=(".",))

    cmd = mock_run.call_args[0][0]
    # default_flags always present.
    assert "--strict" in cmd
    # CI flags should be present.
    assert "--format" in cmd
    idx = cmd.index("--format")
    assert cmd[idx + 1] == "github"


@patch("repomatic.tool_runner.subprocess.run")
@patch("repomatic.tool_runner.is_github_ci", return_value=False)
def test_run_tool_native_config_no_extra_flags(mock_ci, mock_run, tmp_path, monkeypatch):
    """Tool with native config file gets no config flags from repomatic."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "zizmor.yaml").write_text("rules: {}")
    mock_run.return_value = MagicMock(returncode=0)

    run_tool("zizmor", extra_args=(".",))

    cmd = mock_run.call_args[0][0]
    assert "--config" not in cmd
    # default_flags are always present even with native config.
    assert "--offline" in cmd


@patch("repomatic.tool_runner.subprocess.run")
@patch("repomatic.tool_runner.is_github_ci", return_value=False)
def test_run_tool_pyproject_section_temp_file(mock_ci, mock_run, tmp_path, monkeypatch):
    """[tool.X] translation creates a temp file and cleans it up."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        "[tool.zizmor]\n"
        "[tool.zizmor.rules.artipacked]\n"
        "disable = true\n"
    )
    mock_run.return_value = MagicMock(returncode=0)

    run_tool("zizmor", extra_args=(".",))

    cmd = mock_run.call_args[0][0]
    assert "--config" in cmd
    config_idx = cmd.index("--config")
    tmp_file = Path(cmd[config_idx + 1])
    # Temp file should have been cleaned up after run.
    assert not tmp_file.exists()


@patch("repomatic.tool_runner.subprocess.run")
@patch("repomatic.tool_runner.is_github_ci", return_value=False)
def test_run_tool_forwards_exit_code(mock_ci, mock_run, tmp_path, monkeypatch):
    """Tool's exit code is forwarded unchanged."""
    monkeypatch.chdir(tmp_path)
    mock_run.return_value = MagicMock(returncode=42)

    exit_code = run_tool("yamllint", extra_args=(".",))
    assert exit_code == 42


@patch("repomatic.tool_runner.subprocess.run")
@patch("repomatic.tool_runner.is_github_ci", return_value=False)
def test_run_tool_autopep8_default_flags(mock_ci, mock_run, tmp_path, monkeypatch):
    """autopep8 runs with all default flags via uvx."""
    monkeypatch.chdir(tmp_path)
    mock_run.return_value = MagicMock(returncode=0)

    run_tool("autopep8", extra_args=("file.py",))

    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "uvx"
    assert "autopep8==2.3.2" in " ".join(cmd)
    assert "--recursive" in cmd
    assert "--in-place" in cmd
    assert "--max-line-length" in cmd
    assert "88" in cmd
    assert "--select" in cmd
    assert "E501" in cmd
    assert "--aggressive" in cmd
    assert "file.py" in cmd


@patch("repomatic.tool_runner.subprocess.run")
@patch("repomatic.tool_runner.is_github_ci", return_value=False)
def test_run_tool_pyproject_fmt_default_flags(mock_ci, mock_run, tmp_path, monkeypatch):
    """pyproject-fmt runs with --expand-tables flag via uvx."""
    monkeypatch.chdir(tmp_path)
    mock_run.return_value = MagicMock(returncode=0)

    run_tool("pyproject-fmt", extra_args=("pyproject.toml",))

    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "uvx"
    assert "pyproject-fmt==2.16.2" in " ".join(cmd)
    assert "--expand-tables" in cmd
    assert "pyproject.toml" in cmd


@patch("repomatic.tool_runner.subprocess.run")
@patch("repomatic.tool_runner.is_github_ci", return_value=False)
def test_run_tool_mdformat_with_packages(mock_ci, mock_run, tmp_path, monkeypatch):
    """mdformat runs via uvx with all plugin packages."""
    monkeypatch.chdir(tmp_path)
    mock_run.return_value = MagicMock(returncode=0)

    run_tool("mdformat", extra_args=("readme.md",))

    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "uvx"
    assert "mdformat==1.0.0" in " ".join(cmd)
    assert "--number" in cmd
    assert "--strict-front-matter" in cmd
    assert "readme.md" in cmd
    # Verify plugins are passed as --with flags.
    with_count = cmd.count("--with")
    spec = TOOL_REGISTRY["mdformat"]
    assert with_count == len(spec.with_packages)


@patch("repomatic.tool_runner.subprocess.run")
@patch("repomatic.metadata.Metadata")
@patch("repomatic.tool_runner.is_github_ci", return_value=False)
def test_run_tool_mypy_with_computed_params(
    mock_ci, mock_metadata_cls, mock_run, tmp_path, monkeypatch,
):
    """mypy runs via uv run with computed --python-version param."""
    monkeypatch.chdir(tmp_path)
    mock_metadata_cls.return_value.mypy_params = ["--python-version", "3.10"]
    mock_run.return_value = MagicMock(returncode=0)

    run_tool("mypy", extra_args=("repomatic/",))

    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "uv"
    assert "--no-progress" in cmd
    assert "run" in cmd
    assert "--frozen" in cmd
    assert "mypy==1.19.1" in " ".join(cmd)
    assert "--color-output" in cmd
    assert "--python-version" in cmd
    assert "3.10" in cmd
    assert "repomatic/" in cmd


@patch("repomatic.tool_runner.subprocess.run")
@patch("repomatic.metadata.Metadata")
@patch("repomatic.tool_runner.is_github_ci", return_value=False)
def test_run_tool_mypy_without_computed_params(
    mock_ci, mock_metadata_cls, mock_run, tmp_path, monkeypatch,
):
    """mypy runs without computed params when Metadata returns None."""
    monkeypatch.chdir(tmp_path)
    mock_metadata_cls.return_value.mypy_params = None
    mock_run.return_value = MagicMock(returncode=0)

    run_tool("mypy", extra_args=("repomatic/",))

    cmd = mock_run.call_args[0][0]
    assert "--color-output" in cmd
    assert "--python-version" not in cmd


# ---------------------------------------------------------------------------
# get_data_file_path
# ---------------------------------------------------------------------------


def test_get_data_file_path_existing():
    """Bundled data files are accessible via get_data_file_path."""
    with get_data_file_path("zizmor.yaml") as path:
        assert path.exists()
        content = path.read_text(encoding="UTF-8")
        assert "rules:" in content


def test_get_data_file_path_missing():
    """Missing data files raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="not found"):
        with get_data_file_path("nonexistent.yaml"):
            pass
