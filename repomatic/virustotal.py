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

"""Upload release binaries to VirusTotal and update GitHub release notes.

Submits compiled binaries (``.bin``, ``.exe``) to the VirusTotal API for malware
scanning, then appends analysis links to the GitHub release body so users can
verify scan results.

.. note::

    The free-tier API allows 4 requests per minute. Uploads are rate-limited
    with a sleep between each request.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import vt

from .github.gh import run_gh_command

VIRUSTOTAL_GUI_URL = "https://www.virustotal.com/gui/file/{sha256}"
"""URL template for the VirusTotal file analysis page."""

VIRUSTOTAL_SECTION_HEADER = "### \U0001f6e1\ufe0f VirusTotal scans"
"""Markdown header identifying the VirusTotal section in release bodies.

Used for idempotency: if this header is already present, the release body
is not modified.
"""


@dataclass(frozen=True)
class ScanResult:
    """Result of uploading a single file to VirusTotal."""

    filename: str
    """Original filename of the uploaded binary."""

    sha256: str
    """SHA-256 hash of the file content."""

    analysis_url: str
    """VirusTotal web GUI URL for the file analysis."""


def _compute_sha256(path: Path) -> str:
    """Compute the SHA-256 hex digest of a file.

    :param path: Path to the file.
    :return: Lowercase hex digest string.
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_files(
    api_key: str,
    file_paths: list[Path],
    rate_limit: int = 4,
) -> list[ScanResult]:
    """Upload files to VirusTotal and return scan results.

    Uses the synchronous ``vt.Client`` API. Sleeps between uploads to respect
    the free-tier rate limit.

    :param api_key: VirusTotal API key.
    :param file_paths: Paths to binary files to upload.
    :param rate_limit: Maximum requests per minute (free tier: 4).
    :return: List of scan results with analysis URLs.
    """
    results: list[ScanResult] = []
    delay = 60.0 / rate_limit

    with vt.Client(api_key) as client:
        for i, path in enumerate(sorted(file_paths)):
            if i > 0:
                logging.info(
                    f"Rate limiting: waiting {delay:.0f}s before next upload."
                )
                time.sleep(delay)

            sha256 = _compute_sha256(path)
            analysis_url = VIRUSTOTAL_GUI_URL.format(sha256=sha256)

            try:
                logging.info(f"Uploading {path.name} to VirusTotal...")
                with path.open("rb") as f:
                    client.scan_file(f)
                logging.info(f"Uploaded {path.name}: {analysis_url}")
                results.append(
                    ScanResult(
                        filename=path.name,
                        sha256=sha256,
                        analysis_url=analysis_url,
                    )
                )
            except vt.APIError:
                logging.exception(f"Failed to upload {path.name}, skipping.")

    return results


def format_virustotal_section(results: list[ScanResult]) -> str:
    """Format scan results as a markdown section for a GitHub release body.

    :param results: Scan results to format.
    :return: Markdown string, or empty string if no results.
    """
    if not results:
        return ""

    lines = [
        "---",
        "",
        VIRUSTOTAL_SECTION_HEADER,
        "",
        "| Binary | Analysis |",
        "| --- | --- |",
    ]
    for r in results:
        lines.append(f"| `{r.filename}` | [View scan]({r.analysis_url}) |")

    return "\n".join(lines) + "\n"


def update_release_body(
    repo: str,
    tag: str,
    results: list[ScanResult],
) -> bool:
    """Append VirusTotal scan links to a GitHub release body.

    Idempotent: skips the update if the VirusTotal section is already present.

    :param repo: Repository in ``owner/repo`` format.
    :param tag: Release tag (e.g., ``v6.11.1``).
    :param results: Scan results to append.
    :return: ``True`` if the body was updated, ``False`` if skipped.
    """
    if not results:
        logging.info("No scan results to add to release body.")
        return False

    raw = run_gh_command([
        "release",
        "view",
        tag,
        "--repo",
        repo,
        "--json",
        "body",
    ])
    current_body = json.loads(raw).get("body", "")

    if VIRUSTOTAL_SECTION_HEADER in current_body:
        logging.info(
            f"VirusTotal section already present in {tag}, skipping update."
        )
        return False

    section = format_virustotal_section(results)
    new_body = current_body.rstrip() + "\n\n" + section

    run_gh_command([
        "release",
        "edit",
        tag,
        "--repo",
        repo,
        "--notes",
        new_body,
    ])
    logging.info(f"Updated release body for {tag} with VirusTotal scan links.")
    return True
