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
import json
import re
import sys
import tarfile
from itertools import combinations
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

from repomatic.tool_runner import (
    TOOL_REGISTRY,
    VALID_PLATFORM_KEYS,
    ArchiveFormat,
    BinarySpec,
    NativeFormat,
    ToolSpec,
    _download_and_verify,
    _extract_binary,
    _get_platform_key,
    _install_binary,
    binary_tool_context,
    find_unmodified_configs,
    get_data_file_path,
    resolve_config,
    resolve_config_source,
    run_tool,
)

# ---------------------------------------------------------------------------
# ToolSpec and registry validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("name", "spec"), TOOL_REGISTRY.items())
def test_tool_spec_integrity(name, spec):
    """Each registry entry passes structural integrity checks."""
    # name matches registry key, is ASCII lowercase alphanumeric + hyphens.
    assert spec.name == name
    assert re.fullmatch(r"[a-z][a-z0-9-]*", name), f"{name}: invalid name format"

    # version is non-empty semver.
    assert re.fullmatch(r"\d+\.\d+\.\d+", spec.version), (
        f"{name}: version {spec.version!r} is not semver"
    )

    # package, when set, must differ from name (otherwise use None).
    if spec.package is not None:
        assert spec.package != spec.name, (
            f"{name}: package equals name — set package=None instead"
        )

    # config_flag uses the long-form double-dash convention.
    if spec.config_flag is not None:
        assert spec.config_flag.startswith("--"), (
            f"{name}: config_flag {spec.config_flag!r} must start with --"
        )

    # Flags in default_flags and ci_flags that begin with "-" must use long form:
    # either POSIX "--foo" or Go-style "-foo" (more than one char after the dash).
    # Bare values like "88" or "github" interspersed with flags are left unchecked.
    for flag in spec.default_flags:
        if flag.startswith("-"):
            assert flag.startswith("--") or len(flag) > 2, (
                f"{name}: short flag {flag!r} in default_flags — use long form"
            )
    for flag in spec.ci_flags:
        if flag.startswith("-"):
            assert flag.startswith("--") or len(flag) > 2, (
                f"{name}: short flag {flag!r} in ci_flags — use long form"
            )

    # computed_params must also produce long-form flags.
    if spec.computed_params:
        from repomatic.metadata import Metadata

        with patch.object(Metadata, "__init__", lambda self: None):
            m = Metadata()
            # Provide minimal stubs for mypy_params.
            m.pyproject = None
            params = spec.computed_params(m) or []
            for flag in params:
                if flag.startswith("-"):
                    assert flag.startswith("--") or len(flag) > 2, (
                        f"{name}: short flag {flag!r} from computed_params — use long form"
                    )

    # No flag should appear in more than one of the flag-carrying fields.
    flag_fields = {
        "config_flag": {spec.config_flag} if spec.config_flag else set(),
        "default_flags": {f for f in spec.default_flags if f.startswith("-")},
        "ci_flags": {f for f in spec.ci_flags if f.startswith("-")},
    }
    for (field_a, flags_a), (field_b, flags_b) in combinations(flag_fields.items(), 2):
        overlap = flags_a & flags_b
        assert not overlap, f"{name}: {field_a} and {field_b} share flags: {overlap}"

    # needs_venv and binary are mutually exclusive.
    assert not (spec.needs_venv and spec.binary is not None), (
        f"{name}: needs_venv and binary are mutually exclusive"
    )

    # with_packages is only meaningful for uvx-invoked tools.
    if spec.binary is not None:
        assert not spec.with_packages, f"{name}: binary tools cannot use with_packages"

    if spec.default_config:
        with get_data_file_path(spec.default_config) as path:
            assert path.exists(), f"{spec.default_config} not found in data/"
            content = path.read_text(encoding="UTF-8")
            if spec.native_format == NativeFormat.YAML:
                yaml.safe_load(content)
            elif spec.native_format == NativeFormat.TOML:
                tomllib.loads(content)
            elif spec.native_format == NativeFormat.JSON:
                json.loads(content)
        assert spec.config_flag, f"{name} has default_config but no config_flag"

    if spec.binary is not None:
        assert "linux-x64" in spec.binary.urls, f"{name} binary missing linux-x64 URL"
        assert "linux-x64" in spec.binary.checksums, (
            f"{name} binary missing linux-x64 checksum"
        )
        assert set(spec.binary.checksums.keys()) == set(spec.binary.urls.keys()), (
            f"{name}: checksum keys must match URL keys exactly"
        )

        # Platform keys must be from the known set.
        assert set(spec.binary.urls.keys()) <= VALID_PLATFORM_KEYS, (
            f"{name}: unknown platform keys: "
            f"{set(spec.binary.urls.keys()) - VALID_PLATFORM_KEYS}"
        )

        # Every URL must contain a {version} placeholder.
        for platform_key, url in spec.binary.urls.items():
            assert "{version}" in url, (
                f"{name}/{platform_key}: URL missing {{version}} placeholder"
            )

        # Checksums must be valid SHA-256 hex digests (64 lowercase hex chars).
        for platform_key, checksum in spec.binary.checksums.items():
            assert re.fullmatch(r"[0-9a-f]{64}", checksum), (
                f"{name}/{platform_key}: checksum is not a 64-char lowercase hex digest"
            )

        # URLs must be HTTPS.
        for platform_key, url in spec.binary.urls.items():
            assert url.startswith("https://"), (
                f"{name}/{platform_key}: URL must use HTTPS"
            )

        # strip_components only applies to tar archives.
        if spec.binary.strip_components:
            assert spec.binary.archive_format in (
                ArchiveFormat.TAR_GZ,
                ArchiveFormat.TAR_XZ,
            ), f"{name}: strip_components is only valid for tar archive formats"

        # RAW archives should not have path separators in archive_executable.
        if (
            spec.binary.archive_format == ArchiveFormat.RAW
            and spec.binary.archive_executable is not None
        ):
            assert "/" not in spec.binary.archive_executable, (
                f"{name}: RAW archive_executable must not contain path separators"
            )


def test_tool_registry_sorted_alphabetically():
    """Registry keys are sorted alphabetically."""
    keys = list(TOOL_REGISTRY.keys())
    assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# Binary download infrastructure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("linux", "macos", "windows", "x64", "arm64", "expected"),
    [
        (True, False, False, True, False, "linux-x64"),
        (True, False, False, False, True, "linux-arm64"),
        (False, True, False, True, False, "macos-x64"),
        (False, True, False, False, True, "macos-arm64"),
        (False, False, True, True, False, "windows-x64"),
        (False, False, True, False, True, "windows-arm64"),
    ],
)
def test_get_platform_key(linux, macos, windows, x64, arm64, expected):
    """Platform key reflects OS and architecture."""
    with (
        patch("repomatic.tool_runner.is_linux", return_value=linux),
        patch("repomatic.tool_runner.is_macos", return_value=macos),
        patch("repomatic.tool_runner.is_windows", return_value=windows),
        patch("repomatic.tool_runner.is_x86_64", return_value=x64),
        patch("repomatic.tool_runner.is_aarch64", return_value=arm64),
    ):
        assert _get_platform_key() == expected


def test_get_platform_key_unsupported_os():
    """Unsupported OS raises RuntimeError."""
    with (
        patch("repomatic.tool_runner.is_linux", return_value=False),
        patch("repomatic.tool_runner.is_macos", return_value=False),
        patch("repomatic.tool_runner.is_windows", return_value=False),
        pytest.raises(RuntimeError, match="Unsupported OS"),
    ):
        _get_platform_key()


def test_get_platform_key_unsupported_arch():
    """Unsupported architecture raises RuntimeError."""
    with (
        patch("repomatic.tool_runner.is_linux", return_value=True),
        patch("repomatic.tool_runner.is_x86_64", return_value=False),
        patch("repomatic.tool_runner.is_aarch64", return_value=False),
        pytest.raises(RuntimeError, match="x64 and arm64"),
    ):
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
    result = _extract_binary(archive, spec, tmp_path, "testtool")

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
    result = _extract_binary(archive, spec, tmp_path, "testtool")

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
    result = _extract_binary(archive, spec, tmp_path, "testtool")

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
    result = _extract_binary(archive_path, spec, tmp_path, "testtool")

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
        _extract_binary(archive, spec, tmp_path, "testtool")


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
        _extract_binary(archive, spec, tmp_path, "testtool")


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


@patch("repomatic.tool_runner.subprocess.run")
@patch("repomatic.tool_runner.is_github_ci", return_value=False)
def test_run_tool_ruff_bundled_default(mock_ci, mock_run, tmp_path, monkeypatch):
    """ruff uses bundled default config when no config exists."""
    monkeypatch.chdir(tmp_path)
    mock_run.return_value = MagicMock(returncode=0)

    run_tool("ruff", extra_args=("check", "--output-format", "github"))

    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "uvx"
    assert "ruff==0.15.5" in " ".join(cmd)
    assert "--config" in cmd
    assert "check" in cmd
    assert "--output-format" in cmd
    assert "github" in cmd


@patch("repomatic.tool_runner.subprocess.run")
@patch("repomatic.tool_runner.is_github_ci", return_value=False)
def test_run_tool_ruff_reads_pyproject_natively(
    mock_ci, mock_run, tmp_path, monkeypatch
):
    """ruff gets no --config flag when [tool.ruff] exists in pyproject.toml."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test"\n\n[tool.ruff]\npreview = true\n'
    )
    mock_run.return_value = MagicMock(returncode=0)

    run_tool("ruff", extra_args=("check",))

    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "uvx"
    assert "--config" not in cmd
    assert "check" in cmd


@patch("repomatic.tool_runner.subprocess.run")
@patch("repomatic.tool_runner.is_github_ci", return_value=False)
def test_run_tool_bump_my_version_via_uvx(mock_ci, mock_run, tmp_path, monkeypatch):
    """bump-my-version runs via uvx with subcommand extra_args."""
    monkeypatch.chdir(tmp_path)
    mock_run.return_value = MagicMock(returncode=0)

    run_tool("bump-my-version", extra_args=("bump", "--verbose", "patch"))

    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "uvx"
    assert "bump-my-version==1.2.7" in " ".join(cmd)
    assert "bump" in cmd
    assert "--verbose" in cmd
    assert "patch" in cmd


# ---------------------------------------------------------------------------
# binary_tool_context
# ---------------------------------------------------------------------------


@patch("repomatic.tool_runner._install_binary")
def test_binary_tool_context_yields_path(mock_install, tmp_path):
    """binary_tool_context yields the installed binary path."""
    bin_path = tmp_path / "labelmaker"
    bin_path.touch()
    mock_install.return_value = bin_path

    with binary_tool_context("labelmaker") as lm:
        assert lm == bin_path
        assert lm.exists()


def test_binary_tool_context_no_binary_spec():
    """binary_tool_context raises for tools without a binary spec."""
    with (
        pytest.raises(AssertionError, match="no binary spec"),
        binary_tool_context("ruff"),
    ):
        pass


# ---------------------------------------------------------------------------
# Config resolution
# ---------------------------------------------------------------------------


def test_resolve_config_reads_pyproject_with_section():
    """Tools with reads_pyproject=True skip translation when [tool.X] exists."""
    spec = ToolSpec(
        name="testool",
        version="1.0.0",
        config_flag="--config",
        default_config="testool.toml",
        reads_pyproject=True,
    )
    args, tmp = resolve_config(spec, tool_config={"preview": True})
    assert args == []
    assert tmp is None


def test_resolve_config_reads_pyproject_falls_through_to_bundled(tmp_path, monkeypatch):
    """Tools with reads_pyproject=True use bundled default when no config exists."""
    monkeypatch.chdir(tmp_path)
    spec = ToolSpec(
        name="testool",
        version="1.0.0",
        config_flag="--config",
        native_format=NativeFormat.TOML,
        default_config="ruff.toml",
        reads_pyproject=True,
    )
    args, tmp = resolve_config(spec, tool_config={})
    assert args == ["__bundled__"]
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


def test_resolve_config_toml_translation(tmp_path, monkeypatch):
    """[tool.X] with native_format='toml' produces a valid TOML temp file."""
    monkeypatch.chdir(tmp_path)

    spec = ToolSpec(
        name="lychee",
        version="0.23.0",
        package="lychee",
        config_flag="--config",
        native_format=NativeFormat.TOML,
    )
    tool_config = {"max_redirects": 5, "exclude": ["example.com"]}
    args, tmp = resolve_config(spec, tool_config=tool_config)

    try:
        assert len(args) == 2
        assert args[0] == "--config"
        content = Path(args[1]).read_text(encoding="UTF-8")
        assert "max_redirects = 5" in content
        assert '"example.com"' in content
    finally:
        if tmp:
            tmp.unlink(missing_ok=True)


def test_resolve_config_toml_nested_tables(tmp_path, monkeypatch):
    """Nested dicts in [tool.X] produce TOML table sections."""
    monkeypatch.chdir(tmp_path)

    spec = ToolSpec(
        name="lychee",
        version="0.23.0",
        package="lychee",
        config_flag="--config",
        native_format=NativeFormat.TOML,
    )
    tool_config = {"cache": {"enable": True, "max_age": 3600}}
    args, tmp = resolve_config(spec, tool_config=tool_config)

    try:
        content = Path(args[1]).read_text(encoding="UTF-8")
        assert "[cache]" in content
        assert "enable = true" in content
        assert "max_age = 3600" in content
    finally:
        if tmp:
            tmp.unlink(missing_ok=True)


def test_resolve_config_json_translation(tmp_path, monkeypatch):
    """[tool.X] with native_format='json' produces a valid JSON temp file."""
    monkeypatch.chdir(tmp_path)

    spec = ToolSpec(
        name="biome",
        version="2.4.5",
        package="biome",
        config_flag="--config-path",
        native_format=NativeFormat.JSON,
    )
    tool_config = {"formatter": {"indentStyle": "space", "indentWidth": 2}}
    args, tmp = resolve_config(spec, tool_config=tool_config)

    try:
        assert len(args) == 2
        assert args[0] == "--config-path"
        content = Path(args[1]).read_text(encoding="UTF-8")
        parsed = json.loads(content)
        assert parsed == tool_config
    finally:
        if tmp:
            tmp.unlink(missing_ok=True)


def test_resolve_config_no_config_flag_raises(tmp_path, monkeypatch):
    """Tools without config_flag raise NotImplementedError on [tool.X] translation."""
    monkeypatch.chdir(tmp_path)

    spec = ToolSpec(
        name="mdformat",
        version="1.0.0",
        package="mdformat",
        native_config_files=(".mdformat.toml",),
        native_format=NativeFormat.TOML,
    )
    with pytest.raises(NotImplementedError, match="no config_flag"):
        resolve_config(spec, tool_config={"number": True})


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
        native_format=NativeFormat.YAML,
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


def test_resolve_config_source_reads_pyproject_bundled_fallback(tmp_path, monkeypatch):
    """Reports bundled default for reads_pyproject tool when no config exists."""
    monkeypatch.chdir(tmp_path)

    result = resolve_config_source(TOOL_REGISTRY["ruff"])
    assert result == "bundled default"


def test_resolve_config_source_reads_pyproject_native(tmp_path, monkeypatch):
    """Reports [tool.X] for reads_pyproject tool when pyproject section exists."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test"\n\n[tool.ruff]\npreview = true\n'
    )

    result = resolve_config_source(TOOL_REGISTRY["ruff"])
    assert result == "[tool.ruff] in pyproject.toml"


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


# ---------------------------------------------------------------------------
# find_unmodified_configs
# ---------------------------------------------------------------------------


def test_find_unmodified_configs_exact_match(tmp_path, monkeypatch):
    """Native config file matching bundled default is flagged as unmodified."""
    monkeypatch.chdir(tmp_path)

    with get_data_file_path("yamllint.yaml") as bundled:
        bundled_content = bundled.read_text(encoding="UTF-8")

    (tmp_path / ".yamllint.yaml").write_text(bundled_content, encoding="UTF-8")

    result = find_unmodified_configs()
    paths = [p for _, p in result]
    assert ".yamllint.yaml" in paths


def test_find_unmodified_configs_trailing_whitespace(tmp_path, monkeypatch):
    """Trailing whitespace differences are normalized away."""
    monkeypatch.chdir(tmp_path)

    with get_data_file_path("yamllint.yaml") as bundled:
        bundled_content = bundled.read_text(encoding="UTF-8")

    (tmp_path / ".yamllint.yaml").write_text(
        bundled_content.rstrip() + "\n\n\n", encoding="UTF-8"
    )

    result = find_unmodified_configs()
    paths = [p for _, p in result]
    assert ".yamllint.yaml" in paths


def test_find_unmodified_configs_modified_content(tmp_path, monkeypatch):
    """Native config with different content is not flagged."""
    monkeypatch.chdir(tmp_path)

    (tmp_path / ".yamllint.yaml").write_text(
        "rules:\n  line-length:\n    max: 80\n", encoding="UTF-8"
    )

    result = find_unmodified_configs()
    paths = [p for _, p in result]
    assert ".yamllint.yaml" not in paths


def test_find_unmodified_configs_no_file(tmp_path, monkeypatch):
    """No native config on disk returns empty list."""
    monkeypatch.chdir(tmp_path)

    result = find_unmodified_configs()
    assert result == []


def test_find_unmodified_configs_multiple_tools(tmp_path, monkeypatch):
    """Redundant files for multiple tools are all detected."""
    monkeypatch.chdir(tmp_path)

    for data_name, native_name in (
        ("yamllint.yaml", ".yamllint.yaml"),
        ("zizmor.yaml", "zizmor.yaml"),
    ):
        with get_data_file_path(data_name) as bundled:
            content = bundled.read_text(encoding="UTF-8")
        (tmp_path / native_name).write_text(content, encoding="UTF-8")

    result = find_unmodified_configs()
    tools = {t for t, _ in result}
    assert "yamllint" in tools
    assert "zizmor" in tools


def test_find_unmodified_configs_alternative_filename(tmp_path, monkeypatch):
    """Alternative native config filename (.yamllint.yml) is also checked."""
    monkeypatch.chdir(tmp_path)

    with get_data_file_path("yamllint.yaml") as bundled:
        bundled_content = bundled.read_text(encoding="UTF-8")

    (tmp_path / ".yamllint.yml").write_text(bundled_content, encoding="UTF-8")

    result = find_unmodified_configs()
    paths = [p for _, p in result]
    assert ".yamllint.yml" in paths
