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
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from repomatic.virustotal import (
    DETECTION_PENDING,
    VIRUSTOTAL_SECTION_HEADER,
    DetectionStats,
    ScanResult,
    _compute_sha256,
    _extract_results_from_body,
    format_virustotal_section,
    poll_detection_stats,
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


@pytest.fixture()
def sample_enriched_results():
    """Two scan results with detection statistics."""
    return [
        ScanResult(
            filename="app-1.0.0-linux-x64.bin",
            sha256="abcd1234" * 8,
            analysis_url="https://www.virustotal.com/gui/file/" + "abcd1234" * 8,
            detection_stats=DetectionStats(
                malicious=0, suspicious=0, undetected=65, harmless=7
            ),
        ),
        ScanResult(
            filename="app-1.0.0-windows-x64.exe",
            sha256="efgh5678" * 8,
            analysis_url="https://www.virustotal.com/gui/file/" + "efgh5678" * 8,
            detection_stats=DetectionStats(
                malicious=3, suspicious=1, undetected=60, harmless=8
            ),
        ),
    ]


# --- DetectionStats ---


def test_detection_stats_clean():
    """Clean file: zero flagged out of total engines."""
    stats = DetectionStats(malicious=0, suspicious=0, undetected=65, harmless=7)
    assert stats.flagged == 0
    assert stats.total == 72
    assert str(stats) == "0 / 72"


def test_detection_stats_flagged():
    """File with detections: malicious + suspicious count."""
    stats = DetectionStats(malicious=3, suspicious=1, undetected=60, harmless=8)
    assert stats.flagged == 4
    assert stats.total == 72
    assert str(stats) == "4 / 72"


# --- _compute_sha256 ---


def test_compute_sha256(tmp_path):
    """Compute SHA-256 of a file with known content."""
    p = tmp_path / "test.bin"
    p.write_bytes(b"hello world")
    expected = hashlib.sha256(b"hello world").hexdigest()
    assert _compute_sha256(p) == expected


# --- format_virustotal_section ---


def test_format_virustotal_section(sample_results):
    """Format results as a two-column markdown table (no detection stats)."""
    section = format_virustotal_section(sample_results)
    assert VIRUSTOTAL_SECTION_HEADER in section
    assert "| `app-1.0.0-linux-x64.bin` |" in section
    assert "| `app-1.0.0-windows-x64.exe` |" in section
    assert "[View scan](" in section
    assert section.startswith("---\n")
    # Two-column format: no Detections header.
    assert "| Binary | Analysis |" in section
    assert "Detections" not in section
    # Without repo/tag, binary names are not linked.
    assert "releases/download" not in section


def test_format_virustotal_section_with_download_links(sample_results):
    """Binary names link to GitHub release assets when repo and tag are provided."""
    section = format_virustotal_section(sample_results, repo="owner/repo", tag="v1.0.0")
    assert (
        "[`app-1.0.0-linux-x64.bin`]"
        "(https://github.com/owner/repo/releases/download/v1.0.0/"
        "app-1.0.0-linux-x64.bin)"
    ) in section
    assert (
        "[`app-1.0.0-windows-x64.exe`]"
        "(https://github.com/owner/repo/releases/download/v1.0.0/"
        "app-1.0.0-windows-x64.exe)"
    ) in section


def test_format_virustotal_section_with_detections(sample_enriched_results):
    """Three-column table when detection stats are present."""
    section = format_virustotal_section(sample_enriched_results)
    assert "| Binary | Detections | Analysis |" in section
    assert "| 0 / 72 |" in section
    assert "| 4 / 72 |" in section


def test_format_virustotal_section_mixed_detections():
    """Mix of complete and pending detection stats."""
    results = [
        ScanResult(
            filename="app-linux.bin",
            sha256="a" * 64,
            analysis_url="https://www.virustotal.com/gui/file/" + "a" * 64,
            detection_stats=DetectionStats(
                malicious=0, suspicious=0, undetected=65, harmless=7
            ),
        ),
        ScanResult(
            filename="app-windows.exe",
            sha256="b" * 64,
            analysis_url="https://www.virustotal.com/gui/file/" + "b" * 64,
        ),
    ]
    section = format_virustotal_section(results)
    # Three-column because at least one has stats.
    assert "| Binary | Detections | Analysis |" in section
    assert "| 0 / 72 |" in section
    assert f"| {DETECTION_PENDING} |" in section


def test_format_virustotal_section_empty():
    """Empty results produce an empty string."""
    assert format_virustotal_section([]) == ""


# --- _extract_results_from_body ---


def test_extract_results_from_body():
    """Extract SHA-256s and filenames from an existing VT table."""
    sha1 = "a" * 64
    sha2 = "b" * 64
    body = (
        "## Release\n\n"
        "---\n\n"
        f"{VIRUSTOTAL_SECTION_HEADER}\n\n"
        "| Binary | Analysis |\n"
        "| --- | --- |\n"
        f"| `app-linux.bin` | [View scan]"
        f"(https://www.virustotal.com/gui/file/{sha1}) |\n"
        f"| [`app-win.exe`](https://example.com/dl) | [View scan]"
        f"(https://www.virustotal.com/gui/file/{sha2}) |\n"
    )
    results = _extract_results_from_body(body)
    assert len(results) == 2
    assert results[0].filename == "app-linux.bin"
    assert results[0].sha256 == sha1
    assert results[1].filename == "app-win.exe"
    assert results[1].sha256 == sha2


def test_extract_results_from_body_no_section():
    """No VT section returns empty list."""
    body = "## Release\n\nSome notes."
    assert _extract_results_from_body(body) == []


# --- update_release_body ---


def test_update_release_body_appends(sample_results):
    """Append VirusTotal section to a release body with download links."""
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
    # Binary names are linked to download URLs.
    assert "releases/download/v1.0.0/app-1.0.0-linux-x64.bin" in new_body


def test_update_release_body_idempotent(sample_results):
    """Skip update when VirusTotal section already present."""
    existing_body = (
        f"## Release\n\n{VIRUSTOTAL_SECTION_HEADER}\n\n| Binary | Analysis |"
    )

    with patch("repomatic.virustotal.run_gh_command") as mock_gh:
        mock_gh.return_value = json.dumps({"body": existing_body})
        result = update_release_body("owner/repo", "v1.0.0", sample_results)

    assert result is False
    # Only one call (view), no edit.
    assert mock_gh.call_count == 1


def test_update_release_body_replaces_section(sample_enriched_results):
    """Replace existing VT section with enriched version."""
    existing_body = (
        "## Release\n\n---\n\n"
        f"{VIRUSTOTAL_SECTION_HEADER}\n\n"
        "| Binary | Analysis |\n| --- | --- |\n"
        "| `app.bin` | [View scan](https://vt.com/x) |\n"
    )

    with patch("repomatic.virustotal.run_gh_command") as mock_gh:
        mock_gh.return_value = json.dumps({"body": existing_body})
        result = update_release_body(
            "owner/repo", "v1.0.0", sample_enriched_results, replace=True
        )

    assert result is True
    assert mock_gh.call_count == 2
    edit_args = mock_gh.call_args_list[1][0][0]
    notes_idx = edit_args.index("--notes")
    new_body = edit_args[notes_idx + 1]
    # Old table rows are gone.
    assert "app.bin" not in new_body
    # New enriched content is present.
    assert "Detections" in new_body
    assert "0 / 72" in new_body
    # Release notes before VT section are preserved.
    assert "## Release" in new_body


def test_update_release_body_no_results():
    """No results means no API calls."""
    with patch("repomatic.virustotal.run_gh_command") as mock_gh:
        result = update_release_body("owner/repo", "v1.0.0", [])

    assert result is False
    mock_gh.assert_not_called()


# --- poll_detection_stats ---


def test_poll_detection_stats():
    """Poll returns enriched results when analysis is complete."""
    results = [
        ScanResult(
            filename="app.bin",
            sha256="a" * 64,
            analysis_url="https://www.virustotal.com/gui/file/" + "a" * 64,
        ),
    ]

    mock_file_obj = SimpleNamespace(
        last_analysis_stats={
            "malicious": 0,
            "suspicious": 0,
            "undetected": 65,
            "harmless": 7,
            "type-unsupported": 5,
            "timeout": 0,
            "confirmed-timeout": 0,
            "failure": 0,
        }
    )

    mock_client = MagicMock()
    mock_client.get_object.return_value = mock_file_obj
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    with (
        patch("repomatic.virustotal.vt.Client", return_value=mock_client),
        patch("repomatic.virustotal.time.sleep"),
    ):
        enriched = poll_detection_stats("key", results, timeout=60)

    assert len(enriched) == 1
    assert enriched[0].detection_stats is not None
    assert enriched[0].detection_stats.flagged == 0
    assert enriched[0].detection_stats.total == 72


def test_poll_detection_stats_timeout():
    """Polling timeout produces results with None detection_stats."""
    results = [
        ScanResult(
            filename="app.bin",
            sha256="a" * 64,
            analysis_url="https://www.virustotal.com/gui/file/" + "a" * 64,
        ),
    ]

    # Simulate analysis not ready (all zeros).
    mock_file_obj = SimpleNamespace(
        last_analysis_stats={
            "malicious": 0,
            "suspicious": 0,
            "undetected": 0,
            "harmless": 0,
            "type-unsupported": 0,
            "timeout": 0,
            "confirmed-timeout": 0,
            "failure": 0,
        }
    )

    mock_client = MagicMock()
    mock_client.get_object.return_value = mock_file_obj
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    # Make time.monotonic() advance past the deadline after first attempt.
    start = time.monotonic()
    times = iter([start, start, start + 1000, start + 1000])

    with (
        patch("repomatic.virustotal.vt.Client", return_value=mock_client),
        patch("repomatic.virustotal.time.sleep"),
        patch("repomatic.virustotal.time.monotonic", side_effect=times),
    ):
        enriched = poll_detection_stats("key", results, timeout=60)

    assert len(enriched) == 1
    assert enriched[0].detection_stats is None


def test_poll_detection_stats_empty():
    """Polling with no results returns empty list."""
    assert poll_detection_stats("key", []) == []
