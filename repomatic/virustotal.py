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

Submits compiled binaries (`.bin`, `.exe`) to the VirusTotal API for malware
scanning, then appends analysis links to the GitHub release body so users can
verify scan results.

Supports two-phase operation: phase 1 uploads files and writes an initial table
with scan links, phase 2 polls for analysis completion and replaces the table
with detection statistics.

```{note}

The free-tier API allows 4 requests per minute. All API calls (uploads and
polls) are rate-limited with a sleep between each request.
```
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
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
is not modified (unless `replace=True` is passed to `update_release_body`).
"""

DETECTION_PENDING = "*pending*"
"""Placeholder text for the Detections column when analysis is not yet complete."""

_VT_SHA256_RE = re.compile(
    r"https://www\.virustotal\.com/gui/file/([a-f0-9]{64})",
)
"""Regex to extract SHA-256 hashes from VirusTotal GUI URLs in release bodies."""

_VT_ROW_RE = re.compile(
    r"\|\s*\[?`([^`]+)`\]?"  # Binary name (with or without link).
    r".*?"
    r"https://www\.virustotal\.com/gui/file/([a-f0-9]{64})"  # SHA-256 from URL.
)
"""Regex to extract filename and SHA-256 from a VirusTotal table row."""


@dataclass(frozen=True)
class DetectionStats:
    """Detection statistics from a completed VirusTotal analysis.

    Stores only the four categories that constitute a definitive verdict.
    `type-unsupported`, `timeout`, and `failure` from the API response
    are excluded from the total.
    """

    malicious: int
    """Number of engines that flagged the file as malicious."""

    suspicious: int
    """Number of engines that flagged the file as suspicious."""

    undetected: int
    """Number of engines that found no threat."""

    harmless: int
    """Number of engines that classified the file as harmless."""

    @property
    def flagged(self) -> int:
        """Total engines that flagged the file (malicious + suspicious)."""
        return self.malicious + self.suspicious

    @property
    def total(self) -> int:
        """Total engines that produced a definitive verdict."""
        return self.malicious + self.suspicious + self.undetected + self.harmless

    def __str__(self) -> str:
        return f"{self.flagged} / {self.total}"


@dataclass(frozen=True)
class ScanResult:
    """Result of uploading a single file to VirusTotal."""

    filename: str
    """Original filename of the uploaded binary."""

    sha256: str
    """SHA-256 hash of the file content."""

    analysis_url: str
    """VirusTotal web GUI URL for the file analysis."""

    detection_stats: DetectionStats | None = None
    """Detection statistics, or `None` if analysis is still pending."""


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

    Uses the synchronous `vt.Client` API. Sleeps between uploads to respect
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
                logging.info(f"Rate limiting: waiting {delay:.0f}s before next upload.")
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


def poll_detection_stats(
    api_key: str,
    results: list[ScanResult],
    rate_limit: int = 4,
    timeout: int = 600,
) -> list[ScanResult]:
    """Poll VirusTotal for detection statistics of previously uploaded files.

    Queries ``GET /files/{sha256}`` for each file until analysis completes or
    the timeout is reached. Respects the free-tier rate limit for all API calls.

    :param api_key: VirusTotal API key.
    :param results: Scan results from a previous upload.
    :param rate_limit: Maximum API requests per minute (shared with uploads).
    :param timeout: Maximum seconds to wait for all analyses to complete.
    :return: Results with `detection_stats` populated (or `None` for
        files whose analysis did not complete before the timeout).
    """
    if not results:
        return []

    delay = 60.0 / rate_limit
    deadline = time.monotonic() + timeout
    # Map SHA-256 to result for lookup.
    by_sha = {r.sha256: r for r in results}
    stats: dict[str, DetectionStats] = {}
    pending = set(by_sha)
    request_count = 0

    with vt.Client(api_key) as client:
        while pending and time.monotonic() < deadline:
            for sha256 in list(pending):
                if time.monotonic() >= deadline:
                    break

                if request_count > 0:
                    logging.info(
                        f"Rate limiting: waiting {delay:.0f}s before next poll."
                    )
                    time.sleep(delay)
                request_count += 1

                try:
                    file_obj = client.get_object(f"/files/{sha256}")
                    raw_stats = file_obj.last_analysis_stats
                    # A freshly uploaded file may return all zeros before
                    # analysis begins.
                    if sum(raw_stats.values()) > 0:
                        stats[sha256] = DetectionStats(
                            malicious=raw_stats.get("malicious", 0),
                            suspicious=raw_stats.get("suspicious", 0),
                            undetected=raw_stats.get("undetected", 0),
                            harmless=raw_stats.get("harmless", 0),
                        )
                        pending.discard(sha256)
                        r = by_sha[sha256]
                        logging.info(
                            f"Analysis complete for {r.filename}: {stats[sha256]}"
                        )
                except vt.APIError:
                    logging.debug(f"File {sha256[:12]}... not yet indexed, will retry.")

    if pending:
        filenames = [by_sha[s].filename for s in pending]
        logging.warning(
            f"Polling timed out after {timeout}s. Missing results for: {filenames}"
        )

    return [
        ScanResult(
            filename=r.filename,
            sha256=r.sha256,
            analysis_url=r.analysis_url,
            detection_stats=stats.get(r.sha256),
        )
        for r in results
    ]


def _extract_results_from_body(body: str) -> list[ScanResult]:
    """Extract scan results from the VirusTotal section in a release body.

    Parses table rows to recover filenames and SHA-256 hashes, enabling the
    poll phase to run without access to the original binaries.

    :param body: GitHub release body text.
    :return: Scan results reconstructed from the body, or empty list if no
        VirusTotal section is found.
    """
    if VIRUSTOTAL_SECTION_HEADER not in body:
        return []

    results = []
    # Only parse lines after the VT header.
    in_section = False
    for line in body.splitlines():
        if VIRUSTOTAL_SECTION_HEADER in line:
            in_section = True
            continue
        if not in_section:
            continue
        m = _VT_ROW_RE.search(line)
        if m:
            filename, sha256 = m.group(1), m.group(2)
            results.append(
                ScanResult(
                    filename=filename,
                    sha256=sha256,
                    analysis_url=VIRUSTOTAL_GUI_URL.format(sha256=sha256),
                )
            )

    return results


def format_virustotal_section(
    results: list[ScanResult],
    repo: str = "",
    tag: str = "",
) -> str:
    """Format scan results as a markdown section for a GitHub release body.

    When any result has `detection_stats`, a three-column table is rendered
    with a Detections column. Otherwise the simpler two-column format is used.

    :param results: Scan results to format.
    :param repo: Repository in `owner/repo` format. When provided along with
        `tag`, binary names are linked to their GitHub release download URLs.
    :param tag: Release tag (e.g., `v6.11.1`).
    :return: Markdown string, or empty string if no results.
    """
    if not results:
        return ""

    has_detections = any(r.detection_stats is not None for r in results)

    lines = [
        "---",
        "",
        VIRUSTOTAL_SECTION_HEADER,
        "",
    ]
    if has_detections:
        lines.append("| Binary | Detections | Analysis |")
        lines.append("| --- | --- | --- |")
    else:
        lines.append("| Binary | Analysis |")
        lines.append("| --- | --- |")

    for r in results:
        if repo and tag:
            download_url = (
                f"https://github.com/{repo}/releases/download/{tag}/{r.filename}"
            )
            binary_cell = f"[`{r.filename}`]({download_url})"
        else:
            binary_cell = f"`{r.filename}`"

        if has_detections:
            det_cell = (
                str(r.detection_stats) if r.detection_stats else DETECTION_PENDING
            )
            lines.append(
                f"| {binary_cell} | {det_cell} | [View scan]({r.analysis_url}) |"
            )
        else:
            lines.append(f"| {binary_cell} | [View scan]({r.analysis_url}) |")

    return "\n".join(lines) + "\n"


def update_release_body(
    repo: str,
    tag: str,
    results: list[ScanResult],
    replace: bool = False,
) -> bool:
    """Append or replace VirusTotal scan links in a GitHub release body.

    :param repo: Repository in `owner/repo` format.
    :param tag: Release tag (e.g., `v6.11.1`).
    :param results: Scan results to write.
    :param replace: When `True`, replace an existing VirusTotal section
        instead of skipping. When `False` (default), skip if the section
        is already present.
    :return: `True` if the body was updated, `False` if skipped.
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

    section = format_virustotal_section(results, repo=repo, tag=tag)

    if VIRUSTOTAL_SECTION_HEADER in current_body:
        if not replace:
            logging.info(
                f"VirusTotal section already present in {tag}, skipping update."
            )
            return False
        # Replace: find the horizontal rule before the VT header and remove
        # everything from there to the end of the body.
        header_idx = current_body.index(VIRUSTOTAL_SECTION_HEADER)
        # Walk backwards to find the preceding "---" separator.
        prefix = current_body[:header_idx]
        rule_idx = prefix.rfind("---")
        if rule_idx >= 0:
            new_body = current_body[:rule_idx].rstrip() + "\n\n" + section
        else:
            new_body = current_body[:header_idx].rstrip() + "\n\n" + section
    else:
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
