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

"""Tests for binary verification and artifact collection."""

from __future__ import annotations

import json
import re
from unittest.mock import patch

import pytest

from gha_utils.binary import (
    BINARY_ARCH_MAPPINGS,
    collect_and_rename_artifacts,
    extract_binary_names,
    format_github_output,
    verify_binary_arch,
)


@pytest.mark.parametrize(
    "target",
    [
        "linux-arm64",
        "linux-x64",
        "macos-arm64",
        "macos-x64",
        "windows-arm64",
        "windows-x64",
    ],
)
def test_all_targets_present(target):
    """All expected targets are in the mapping."""
    assert target in BINARY_ARCH_MAPPINGS


@pytest.mark.parametrize(
    ("target", "expected_field", "expected_substring"),
    [
        ("linux-arm64", "CPUType", "Arm 64-bits"),
        ("linux-x64", "CPUType", "AMD x86-64"),
        ("macos-arm64", "CPUType", "ARM 64-bit"),
        ("macos-x64", "CPUType", "x86 64-bit"),
        ("windows-arm64", "MachineType", "ARM64"),
        ("windows-x64", "MachineType", "AMD64"),
    ],
)
def test_mapping_values(target, expected_field, expected_substring):
    """Each target maps to correct field and substring."""
    field, substring = BINARY_ARCH_MAPPINGS[target]
    assert field == expected_field
    assert substring == expected_substring


def test_unknown_target(tmp_path):
    """Unknown target raises ValueError."""
    binary = tmp_path / "test.bin"
    binary.touch()
    with pytest.raises(ValueError, match="Unknown target"):
        verify_binary_arch("unknown-platform", binary)


@pytest.mark.parametrize(
    ("target", "field", "value"),
    [
        ("linux-arm64", "CPUType", "Arm 64-bits (Armv8/AArch64)"),
        ("linux-x64", "CPUType", "AMD x86-64"),
        ("macos-arm64", "CPUType", "ARM 64-bit"),
        ("macos-x64", "CPUType", "x86 64-bit"),
        ("windows-arm64", "MachineType", "ARM64 little endian"),
        ("windows-x64", "MachineType", "AMD AMD64"),
    ],
)
def test_matching_arch(tmp_path, target, field, value):
    """Binary with matching architecture passes verification."""
    binary = tmp_path / "test.bin"
    binary.touch()

    mock_output = [{field: value}]
    with patch("gha_utils.binary.run_exiftool", return_value=mock_output[0]):
        # Should not raise.
        verify_binary_arch(target, binary)


@pytest.mark.parametrize(
    ("target", "field", "wrong_value"),
    [
        ("linux-arm64", "CPUType", "AMD x86-64"),
        ("linux-x64", "CPUType", "Arm 64-bits"),
        ("macos-arm64", "CPUType", "x86 64-bit"),
        ("windows-x64", "MachineType", "ARM64"),
    ],
)
def test_mismatched_arch(tmp_path, target, field, wrong_value):
    """Binary with mismatched architecture raises AssertionError."""
    binary = tmp_path / "test.bin"
    binary.touch()

    mock_output = {field: wrong_value}
    with patch("gha_utils.binary.run_exiftool", return_value=mock_output):
        with pytest.raises(AssertionError, match="Binary architecture mismatch"):
            verify_binary_arch(target, binary)


def test_missing_field(tmp_path):
    """Missing exiftool field raises AssertionError."""
    binary = tmp_path / "test.bin"
    binary.touch()

    # Return empty metadata.
    mock_output = {}
    with patch("gha_utils.binary.run_exiftool", return_value=mock_output):
        with pytest.raises(AssertionError, match="Binary architecture mismatch"):
            verify_binary_arch("linux-arm64", binary)


def test_empty_string():
    """Empty string returns empty set."""
    assert extract_binary_names("") == set()


def test_whitespace_only():
    """Whitespace-only string returns empty set."""
    assert extract_binary_names("   \n  ") == set()


def test_valid_matrix():
    """Valid nuitka matrix extracts binary names."""
    matrix = {
        "include": [
            {"bin_name": "app-linux-arm64.bin", "target": "linux-arm64"},
            {"bin_name": "app-windows-x64.exe", "target": "windows-x64"},
            {"target": "macos-arm64"},  # Missing bin_name.
        ]
    }
    result = extract_binary_names(json.dumps(matrix))
    assert result == {"app-linux-arm64.bin", "app-windows-x64.exe"}


def test_empty_include():
    """Empty include array returns empty set."""
    matrix = {"include": []}
    result = extract_binary_names(json.dumps(matrix))
    assert result == set()


def test_missing_include_key():
    """Missing include key returns empty set."""
    matrix = {"other": "data"}
    result = extract_binary_names(json.dumps(matrix))
    assert result == set()


def test_empty_folder(tmp_path):
    """Empty folder returns empty list."""
    result = collect_and_rename_artifacts(tmp_path, "abc1234")
    assert result == []


def test_non_binary_artifacts(tmp_path):
    """Non-binary artifacts are collected as-is."""
    (tmp_path / "package.whl").touch()
    (tmp_path / "package.tar.gz").touch()

    result = collect_and_rename_artifacts(tmp_path, "abc1234")
    names = {p.name for p in result}
    assert names == {"package.whl", "package.tar.gz"}


def test_binary_rename(tmp_path):
    """Binaries are renamed to strip SHA suffix."""
    (tmp_path / "app-linux-arm64-abc1234.bin").touch()

    matrix = {"include": [{"bin_name": "app-linux-arm64-abc1234.bin"}]}
    result = collect_and_rename_artifacts(tmp_path, "abc1234", json.dumps(matrix))

    assert len(result) == 1
    assert result[0].name == "app-linux-arm64.bin"
    assert result[0].exists()


def test_mixed_artifacts(tmp_path):
    """Mixed binaries and packages are handled correctly."""
    (tmp_path / "app-linux-arm64-abc1234.bin").touch()
    (tmp_path / "app-windows-x64-abc1234.exe").touch()
    (tmp_path / "package-abc1234.whl").touch()

    matrix = {
        "include": [
            {"bin_name": "app-linux-arm64-abc1234.bin"},
            {"bin_name": "app-windows-x64-abc1234.exe"},
        ]
    }
    result = collect_and_rename_artifacts(tmp_path, "abc1234", json.dumps(matrix))

    names = {p.name for p in result}
    assert names == {
        "app-linux-arm64.bin",
        "app-windows-x64.exe",
        "package-abc1234.whl",
    }


def test_target_exists_error(tmp_path):
    """Raises error if renamed file already exists."""
    (tmp_path / "app-linux-arm64-abc1234.bin").touch()
    (tmp_path / "app-linux-arm64.bin").touch()  # Conflict.

    matrix = {"include": [{"bin_name": "app-linux-arm64-abc1234.bin"}]}
    with pytest.raises(FileExistsError, match="already exists"):
        collect_and_rename_artifacts(tmp_path, "abc1234", json.dumps(matrix))


def test_skips_directories(tmp_path):
    """Directories are skipped."""
    (tmp_path / "subdir").mkdir()
    (tmp_path / "file.txt").touch()

    result = collect_and_rename_artifacts(tmp_path, "abc1234")
    assert len(result) == 1
    assert result[0].name == "file.txt"


def test_empty_list():
    """Empty artifact list produces valid output."""
    result = format_github_output([])
    assert result.startswith("artifacts_path<<GHA_DELIMITER_")
    assert result.endswith(result.split("<<")[1].split("\n")[0])


def test_single_artifact(tmp_path):
    """Single artifact path is formatted correctly."""
    artifact = tmp_path / "app.bin"
    result = format_github_output([artifact])

    # Check structure.
    lines = result.split("\n")
    assert lines[0].startswith("artifacts_path<<GHA_DELIMITER_")
    assert lines[1] == str(artifact)
    assert lines[2].startswith("GHA_DELIMITER_")


def test_multiple_artifacts(tmp_path):
    """Multiple artifact paths are formatted correctly."""
    artifacts = [tmp_path / "app1.bin", tmp_path / "app2.bin", tmp_path / "pkg.whl"]
    result = format_github_output(artifacts)

    lines = result.split("\n")
    assert len(lines) == 5  # Header, 3 paths, footer.
    assert str(artifacts[0]) in lines[1]
    assert str(artifacts[1]) in lines[2]
    assert str(artifacts[2]) in lines[3]


def test_delimiter_format():
    """Delimiter follows expected format."""
    result = format_github_output([])
    delimiter_match = re.search(r"GHA_DELIMITER_(\d+)", result)
    assert delimiter_match
    # Delimiter is 9 digits.
    assert 10**8 <= int(delimiter_match.group(1)) < 10**9


def test_delimiter_uniqueness():
    """Delimiters vary between calls."""
    results = {
        format_github_output([]).split("<<")[1].split("\n")[0] for _ in range(10)
    }
    # With random generation, we expect some variation.
    assert len(results) > 1
