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

"""Tests for VirusTotal module."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from repomatic.virustotal import (
    VIRUSTOTAL_SECTION_HEADER,
    ScanResult,
    _compute_sha256,
    format_virustotal_section,
    update_release_body,
)


@pytest.fixture()
def sample_results():
    """Two scan results for testing."""
    return [
        ScanResult(
            filename="app-1.0.0-linux-x64.bin",
            sha256="abcd1234" * 8,
            analysis_url="https://www.virustotal.com/gui/file/" + "abcd1234" * 8,
        ),
        ScanResult(
            filename="app-1.0.0-windows-x64.exe",
            sha256="efgh5678" * 8,
            analysis_url="https://www.virustotal.com/gui/file/" + "efgh5678" * 8,
        ),
    ]


def test_compute_sha256(tmp_path):
    """Compute SHA-256 of a file with known content."""
    p = tmp_path / "test.bin"
    p.write_bytes(b"hello world")
    expected = hashlib.sha256(b"hello world").hexdigest()
    assert _compute_sha256(p) == expected


def test_format_virustotal_section(sample_results):
    """Format results as a markdown table."""
    section = format_virustotal_section(sample_results)
    assert VIRUSTOTAL_SECTION_HEADER in section
    assert "| `app-1.0.0-linux-x64.bin` |" in section
    assert "| `app-1.0.0-windows-x64.exe` |" in section
    assert "[View scan](" in section
    # Starts with horizontal rule.
    assert section.startswith("---\n")


def test_format_virustotal_section_empty():
    """Empty results produce an empty string."""
    assert format_virustotal_section([]) == ""


def test_update_release_body_appends(sample_results):
    """Append VirusTotal section to a release body."""
    existing_body = "## Release v1.0.0\n\nSome notes."

    with patch("repomatic.virustotal.run_gh_command") as mock_gh:
        mock_gh.return_value = json.dumps({"body": existing_body})
        result = update_release_body("owner/repo", "v1.0.0", sample_results)

    assert result is True
    # First call: view, second call: edit.
    assert mock_gh.call_count == 2
    edit_call = mock_gh.call_args_list[1]
    edit_args = edit_call[0][0]
    assert "edit" in edit_args
    # The new body must contain both the old text and the VT section.
    notes_idx = edit_args.index("--notes")
    new_body = edit_args[notes_idx + 1]
    assert existing_body.rstrip() in new_body
    assert VIRUSTOTAL_SECTION_HEADER in new_body


def test_update_release_body_idempotent(sample_results):
    """Skip update when VirusTotal section already present."""
    existing_body = f"## Release\n\n{VIRUSTOTAL_SECTION_HEADER}\n\n| Binary | Analysis |"

    with patch("repomatic.virustotal.run_gh_command") as mock_gh:
        mock_gh.return_value = json.dumps({"body": existing_body})
        result = update_release_body("owner/repo", "v1.0.0", sample_results)

    assert result is False
    # Only one call (view), no edit.
    assert mock_gh.call_count == 1


def test_update_release_body_no_results():
    """No results means no API calls."""
    with patch("repomatic.virustotal.run_gh_command") as mock_gh:
        result = update_release_body("owner/repo", "v1.0.0", [])

    assert result is False
    mock_gh.assert_not_called()
