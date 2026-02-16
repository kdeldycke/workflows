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

"""Update SHA-256 checksums for direct binary downloads in workflow files.

Scans workflow files for GitHub release download URLs paired with
``sha256sum --check`` verification lines. Downloads each binary, computes
the SHA-256, and replaces stale hashes in-place.

Designed to be called by Renovate ``postUpgradeTasks`` after version bumps,
but also works standalone for manual checksum updates.
"""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from urllib.request import Request, urlopen

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Iterator

# Matches GitHub release download URLs in quoted strings.
_URL_PATTERN = re.compile(
    r"https://github\.com/[^\"]+/releases/download/[^\"]+",
)

# Matches a 64-character lowercase hex SHA-256 hash.
_HASH_PATTERN = re.compile(r"[a-f0-9]{64}")

# How many lines after a URL to search for the sha256sum check line.
_HASH_SEARCH_WINDOW = 5


def _download_sha256(url: str) -> str:
    """Download a URL and return its SHA-256 hex digest.

    :param url: The URL to download.
    :return: Lowercase hex SHA-256 digest of the response body.
    """
    request = Request(url)  # noqa: S310
    with urlopen(request) as response:  # noqa: S310
        digest = hashlib.sha256(response.read()).hexdigest()
    logging.debug(f"SHA-256 of {url}: {digest}")
    return digest


def _find_checksum_pairs(lines: list[str]) -> Iterator[tuple[str, int, str]]:
    """Find (url, hash_line_index, old_hash) triples in workflow file lines.

    For each GitHub release URL found, searches the next few lines for a
    ``sha256sum --check`` line containing a 64-char hex hash.

    :param lines: Lines of the workflow file.
    :return: Iterator of (url, hash_line_index, old_hash) triples.
    """
    for i, line in enumerate(lines):
        for url_match in _URL_PATTERN.finditer(line):
            url = url_match.group()
            # Search subsequent lines for a sha256sum check.
            for j in range(i + 1, min(i + 1 + _HASH_SEARCH_WINDOW, len(lines))):
                if "sha256sum" in lines[j]:
                    hash_match = _HASH_PATTERN.search(lines[j])
                    if hash_match:
                        yield url, j, hash_match.group()
                        break
                    # Hash may be on a continuation line (e.g. sha256sum --check <<< \).
                    if j + 1 < len(lines):
                        hash_match = _HASH_PATTERN.search(lines[j + 1])
                        if hash_match:
                            yield url, j + 1, hash_match.group()
                    break


def update_checksums(file_path: Path) -> list[tuple[str, str, str]]:
    """Update SHA-256 checksums in a workflow file.

    :param file_path: Path to the workflow YAML file.
    :return: List of (url, old_hash, new_hash) for each updated checksum.
        Empty if all checksums are already correct.
    """
    content = file_path.read_text(encoding="UTF-8")
    lines = content.splitlines()
    updated: list[tuple[str, str, str]] = []

    for url, hash_line_idx, old_hash in _find_checksum_pairs(lines):
        logging.info(f"Verifying checksum for {url}")
        new_hash = _download_sha256(url)

        if old_hash != new_hash:
            lines[hash_line_idx] = lines[hash_line_idx].replace(old_hash, new_hash)
            updated.append((url, old_hash, new_hash))
            logging.info(f"Updated checksum: {old_hash} -> {new_hash}")
        else:
            logging.info("Checksum unchanged.")

    if updated:
        file_path.write_text("\n".join(lines) + "\n", encoding="UTF-8")

    return updated
