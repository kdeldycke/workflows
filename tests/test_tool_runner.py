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

import hashlib
import io
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from repomatic.tool_runner import (
    TOOL_REGISTRY,
    ArchiveFormat,
    BinarySpec,
    ToolSpec,
    _download_and_verify,
    _extract_binary,
    _get_platform_key,
    _install_binary,
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


def test_tool_registry_binary_specs_have_matching_keys():
    """Every binary tool has matching URL and checksum platform keys."""
    for name, spec in TOOL_REGISTRY.items():
        if spec.binary is None:
            continue
        assert "linux-x64" in spec.binary.urls, f"{name} binary missing linux-x64 URL"
        assert "linux-x64" in spec.binary.checksums, (
            f"{name} binary missing linux-x64 checksum"
        )
        assert set(spec.binary.checksums.keys()) <= set(spec.binary.urls.keys()), (
            f"{name} has checksum keys without matching URL keys"
        )


def test_tool_registry_binary_tar_has_archive_executable():
    """Tar-based binary tools must specify archive_executable."""
    for name, spec in TOOL_REGISTRY.items():
        if spec.binary is None:
            continue
        if spec.binary.archive_format in (ArchiveFormat.TAR_GZ, ArchiveFormat.TAR_XZ):
            assert spec.binary.archive_executable is not None, (
                f"{name} uses tar format but has no archive_executable"
            )


def test_tool_registry_sorted_alphabetically():
    """Registry keys are sorted alphabetically."""
    keys = list(TOOL_REGISTRY.keys())
    assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# Binary download infrastructure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("platform", "macos", "x64", "arm64", "expected"),
    [
        ("linux", False, True, False, "linux-x64"),
        ("linux", False, False, True, "linux-arm64"),
        ("not-linux", True, True, False, "macos-x64"),
        ("not-linux", True, False, True, "macos-arm64"),
    ],
)
def test_get_platform_key(platform, macos, x64, arm64, expected):
    """Platform key reflects OS and architecture."""
    with (
        patch("repomatic.tool_runner.sys") as mock_sys,
        patch("repomatic.tool_runner.is_macos", return_value=macos),
        patch("repomatic.tool_runner.is_x86_64", return_value=x64),
        patch("repomatic.tool_runner.is_aarch64", return_value=arm64),
    ):
        mock_sys.platform = platform
        mock_sys.version_info = (3, 14)
        assert _get_platform_key() == expected


def test_get_platform_key_unsupported_os():
    """Unsupported OS raises RuntimeError."""
    with (
        patch("repomatic.tool_runner.sys") as mock_sys,
        patch("repomatic.tool_runner.is_macos", return_value=False),
    ):
        mock_sys.platform = "win32"
        with pytest.raises(RuntimeError, match="Linux and macOS"):
            _get_platform_key()


def test_get_platform_key_unsupported_arch():
    """Unsupported architecture raises RuntimeError."""
    with (
        patch("repomatic.tool_runner.sys") as mock_sys,
        patch("repomatic.tool_runner.is_x86_64", return_value=False),
        patch("repomatic.tool_runner.is_aarch64", return_value=False),
    ):
        mock_sys.platform = "linux"
        with pytest.raises(RuntimeError, match="x64 and arm64"):
            _get_platform_key()


def test_download_and_verify_success(tmp_path):
    """Successful download with matching checksum writes the file."""
    content = b"hello binary world"
    expected = hashlib.sha256(content).hexdigest()
    dest = tmp_path / "downloaded"

    mock_response = MagicMock()
    mock_response.read = MagicMock(side_effect=[content, b""])
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("repomatic.tool_runner.urlopen", return_value=mock_response):
        _download_and_verify("https://example.com/file", expected, dest)

    assert dest.exists()
    assert dest.read_bytes() == content


def test_download_and_verify_mismatch(tmp_path):
    """Checksum mismatch raises ValueError and cleans up."""
    content = b"hello binary world"
    dest = tmp_path / "downloaded"

    mock_response = MagicMock()
    mock_response.read = MagicMock(side_effect=[content, b""])
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)

    with (
        patch("repomatic.tool_runner.urlopen", return_value=mock_response),
        pytest.raises(ValueError, match="SHA-256 mismatch"),
    ):
        _download_and_verify("https://example.com/file", "bad" * 16, dest)

    assert not dest.exists()


def test_extract_binary_raw(tmp_path):
    """RAW format renames the archive to the executable name."""
    archive = tmp_path / "biome-linux-x64"
    archive.write_bytes(b"\x7fELF fake binary")

    spec = BinarySpec(
        urls={},
        checksums={},
        archive_format=ArchiveFormat.RAW,
        archive_executable="biome",
    )
    result = _extract_binary(archive, spec, tmp_path)

    assert result == tmp_path / "biome"
    assert result.exists()
    assert result.stat().st_mode & 0o755


def _create_tar_gz(tmp_path, member_name, content=b"#!/bin/sh\necho hi"):
    """Create a tar.gz archive with a single member."""
    archive_path = tmp_path / "tool.tar.gz"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo(name=member_name)
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    archive_path.write_bytes(buf.getvalue())
    return archive_path


def test_extract_binary_tar_gz(tmp_path):
    """TAR_GZ extracts the named executable and makes it executable."""
    archive = _create_tar_gz(tmp_path, "actionlint")

    spec = BinarySpec(
        urls={},
        checksums={},
        archive_format=ArchiveFormat.TAR_GZ,
        archive_executable="actionlint",
    )
    result = _extract_binary(archive, spec, tmp_path)

    assert result == tmp_path / "actionlint"
    assert result.exists()
    assert result.stat().st_mode & 0o755


def test_extract_binary_tar_gz_with_strip_components(tmp_path):
    """TAR_GZ with strip_components strips leading path components."""
    archive = _create_tar_gz(tmp_path, "subdir/bin/mytool")

    spec = BinarySpec(
        urls={},
        checksums={},
        archive_format=ArchiveFormat.TAR_GZ,
        archive_executable="bin/mytool",
        strip_components=1,
    )
    result = _extract_binary(archive, spec, tmp_path)

    assert result.name == "mytool"
    assert result.exists()
    assert result.stat().st_mode & 0o755


def test_extract_binary_tar_xz(tmp_path):
    """TAR_XZ extracts the named executable."""
    archive_path = tmp_path / "tool.tar.xz"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:xz") as tar:
        content = b"#!/bin/sh\necho hi"
        info = tarfile.TarInfo(name="lychee")
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
    archive_path.write_bytes(buf.getvalue())

    spec = BinarySpec(
        urls={},
        checksums={},
        archive_format=ArchiveFormat.TAR_XZ,
        archive_executable="lychee",
    )
    result = _extract_binary(archive_path, spec, tmp_path)

    assert result == tmp_path / "lychee"
    assert result.exists()


def test_extract_binary_tar_missing_executable(tmp_path):
    """Missing executable in tar archive raises FileNotFoundError."""
    archive = _create_tar_gz(tmp_path, "other_binary")

    spec = BinarySpec(
        urls={},
        checksums={},
        archive_format=ArchiveFormat.TAR_GZ,
        archive_executable="nonexistent",
    )
    with pytest.raises(FileNotFoundError, match="not found in archive"):
        _extract_binary(archive, spec, tmp_path)


def test_extract_binary_tar_unsafe_path(tmp_path):
    """Archive member with path traversal raises ValueError."""
    archive = _create_tar_gz(tmp_path, "../../../etc/passwd")

    spec = BinarySpec(
        urls={},
        checksums={},
        archive_format=ArchiveFormat.TAR_GZ,
        archive_executable="../../../etc/passwd",
    )
    with pytest.raises(ValueError, match="Unsafe archive member"):
        _extract_binary(archive, spec, tmp_path)


def test_install_binary_missing_platform():
    """Missing platform key in binary spec raises RuntimeError."""
    spec = ToolSpec(
        name="testtool",
        version="1.0.0",
        package="testtool",
        binary=BinarySpec(
            urls={"linux-arm64": "https://example.com/{version}/tool"},
            checksums={"linux-arm64": "a" * 64},
            archive_format=ArchiveFormat.RAW,
            archive_executable="testtool",
        ),
    )
    with (
        patch("repomatic.tool_runner._get_platform_key", return_value="linux-x64"),
        pytest.raises(RuntimeError, match="No binary available"),
    ):
        _install_binary(spec, Path("/tmp"))


# ---------------------------------------------------------------------------
# run_tool with binary tools
# ---------------------------------------------------------------------------


@patch("repomatic.tool_runner.subprocess.run")
@patch("repomatic.tool_runner._install_binary")
@patch("repomatic.tool_runner.is_github_ci", return_value=False)
def test_run_tool_binary_uses_direct_path(
    mock_ci,
    mock_install,
    mock_run,
    tmp_path,
    monkeypatch,
):
    """Binary tools use the downloaded binary path, not uvx."""
    monkeypatch.chdir(tmp_path)
    bin_path = tmp_path / "typos"
    bin_path.touch()
    mock_install.return_value = bin_path
    mock_run.return_value = MagicMock(returncode=0)

    exit_code = run_tool("typos")

    assert exit_code == 0
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == str(bin_path)
    assert "uvx" not in cmd
    assert "--write-changes" in cmd


@patch("repomatic.tool_runner.subprocess.run")
@patch("repomatic.tool_runner._install_binary")
@patch("repomatic.tool_runner.is_github_ci", return_value=False)
def test_run_tool_binary_forwards_extra_args(
    mock_ci,
    mock_install,
    mock_run,
    tmp_path,
    monkeypatch,
):
    """Extra args are appended after default flags for binary tools."""
    monkeypatch.chdir(tmp_path)
    bin_path = tmp_path / "biome"
    bin_path.touch()
    mock_install.return_value = bin_path
    mock_run.return_value = MagicMock(returncode=0)

    run_tool("biome", extra_args=("format", "--write", "file.json"))

    cmd = mock_run.call_args[0][0]
    assert cmd[0] == str(bin_path)
    assert "format" in cmd
    assert "--write" in cmd
    assert "file.json" in cmd


@patch("repomatic.tool_runner.subprocess.run")
@patch("repomatic.tool_runner._install_binary")
@patch("repomatic.tool_runner.is_github_ci", return_value=False)
def test_run_tool_binary_default_flags(
    mock_ci,
    mock_install,
    mock_run,
    tmp_path,
    monkeypatch,
):
    """Binary tools include default_flags in the command."""
    monkeypatch.chdir(tmp_path)
    bin_path = tmp_path / "actionlint"
    bin_path.touch()
    mock_install.return_value = bin_path
    mock_run.return_value = MagicMock(returncode=0)

    run_tool("actionlint")

    cmd = mock_run.call_args[0][0]
    assert "-color" in cmd


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
    args, tmp = resolve_config(
        spec, tool_config={"rules": {"line-length": {"max": 80}}}
    )
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
        "[tool.yamllint]\nrules = {line-length = {max = 80}}\n"
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
def test_run_tool_native_config_no_extra_flags(
    mock_ci, mock_run, tmp_path, monkeypatch
):
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
        "[tool.zizmor]\n[tool.zizmor.rules.artipacked]\ndisable = true\n"
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
    mock_ci,
    mock_metadata_cls,
    mock_run,
    tmp_path,
    monkeypatch,
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
    mock_ci,
    mock_metadata_cls,
    mock_run,
    tmp_path,
    monkeypatch,
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
    with (
        pytest.raises(FileNotFoundError, match="not found"),
        get_data_file_path("nonexistent.yaml"),
    ):
        pass
