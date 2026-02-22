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

"""Tests for binary verification."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from gha_utils.binary import (
    BINARY_ARCH_MAPPINGS,
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


