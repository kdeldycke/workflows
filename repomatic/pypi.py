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
"""PyPI API client for package metadata lookups.

Provides a shared HTTP client and domain-specific query functions used by
:mod:`repomatic.changelog` (release dates, yanked status) and
:mod:`repomatic.renovate` (source repository discovery).
"""

from __future__ import annotations

import json
import logging
from typing import NamedTuple
from urllib.error import URLError
from urllib.request import Request, urlopen

from .cache import get_cached_response, store_response
from .config import load_repomatic_config

PYPI_API_URL = "https://pypi.org/pypi/{package}/json"
"""PyPI JSON API URL for fetching all release metadata for a package."""

PYPI_PROJECT_URL = "https://pypi.org/project/{package}/{version}/"
"""PyPI project page URL for a specific version."""

PYPI_LABEL = "🐍 PyPI"
"""Display label for PyPI releases in admonitions."""

# Keys in PyPI ``project_urls`` that typically point to a changelog,
# checked in priority order.
_CHANGELOG_URL_KEYS = (
    "Changelog",
    "Changes",
    "Change Log",
    "Release Notes",
    "History",
)

# Keys in PyPI ``project_urls`` that typically point to a GitHub repository,
# checked in priority order.
_SOURCE_URL_KEYS = (
    "Source",
    "Source Code",
    "Source code",
    "Repository",
    "Code",
    "Homepage",
)


def _fetch_json(package: str) -> dict | None:
    """Fetch the full JSON metadata for a PyPI package.

    Results are cached under the ``pypi`` namespace. Freshness TTL is read
    from ``CacheConfig.pypi_ttl``.

    :param package: The PyPI package name.
    :return: Parsed JSON response, or ``None`` on any failure.
    """
    ttl = load_repomatic_config().cache.pypi_ttl
    cached = get_cached_response("pypi", package, ttl)
    if cached is not None:
        try:
            return json.loads(cached)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            pass

    url = PYPI_API_URL.format(package=package)
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=10) as response:
            raw = response.read()
            result: dict[str, object] = json.loads(raw)
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        logging.debug(f"PyPI lookup failed for {package}: {exc}")
        return None

    if ttl > 0:
        store_response("pypi", package, raw)
    return result


class PyPIRelease(NamedTuple):
    """Release metadata for a single version from PyPI."""

    date: str
    """Earliest upload date across all files in ``YYYY-MM-DD`` format."""

    yanked: bool
    """Whether all files for this version are yanked."""

    package: str
    """PyPI package name this release was fetched from.

    Needed for projects that were renamed: older versions live under a
    former package name and their PyPI URLs must point to that name, not
    the current one.
    """


def get_release_dates(package: str) -> dict[str, PyPIRelease]:
    """Get upload dates and yanked status for all versions from PyPI.

    Fetches the package metadata in a single API call. For each version,
    selects the **earliest** upload time across all distribution files as
    the canonical release date. A version is considered yanked only if
    **all** of its files are yanked.

    :param package: The PyPI package name.
    :return: Dict mapping version strings to :class:`PyPIRelease` tuples.
        Empty dict if the package is not found or the request fails.
    """
    data = _fetch_json(package)
    if data is None:
        return {}

    result: dict[str, PyPIRelease] = {}
    for version, files in data.get("releases", {}).items():
        if not files:
            continue
        # Select the earliest upload time across all distribution files.
        dates = [f["upload_time"][:10] for f in files if f.get("upload_time")]
        if not dates:
            continue
        earliest_date = min(dates)
        # A version is yanked only if every file is yanked.
        all_yanked = all(f.get("yanked", False) for f in files)
        result[version] = PyPIRelease(
            date=earliest_date, yanked=all_yanked, package=package
        )

    return result


def get_source_url(package: str) -> str | None:
    """Discover the GitHub repository URL for a PyPI package.

    Queries the PyPI JSON API and scans ``project_urls`` for keys that
    typically point to a source repository on GitHub.

    :param package: The PyPI package name.
    :return: The GitHub repository URL, or ``None`` if not found.
    """
    data = _fetch_json(package)
    if data is None:
        return None

    project_urls: dict[str, str] = data.get("info", {}).get("project_urls") or {}
    for key in _SOURCE_URL_KEYS:
        candidate = project_urls.get(key, "")
        if "github.com" in candidate:
            return candidate.rstrip("/").removesuffix(".git")
    # Fallback: scan all values for a GitHub URL.
    for candidate in project_urls.values():
        if "github.com" in candidate:
            return candidate.rstrip("/").removesuffix(".git")
    return None


def get_changelog_url(package: str) -> str | None:
    """Discover the changelog URL for a PyPI package.

    Queries the PyPI JSON API and scans ``project_urls`` for keys that
    typically point to a changelog or release notes page.

    :param package: The PyPI package name.
    :return: The changelog URL, or ``None`` if not found.
    """
    data = _fetch_json(package)
    if data is None:
        return None

    project_urls: dict[str, str] = data.get("info", {}).get("project_urls") or {}
    for key in _CHANGELOG_URL_KEYS:
        candidate = project_urls.get(key, "")
        if candidate:
            return candidate.rstrip("/")
    return None
