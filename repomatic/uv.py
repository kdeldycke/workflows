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

"""uv lock file operations and vulnerability auditing.

This module provides utilities for managing ``uv.lock`` files: parsing versions,
detecting timestamp noise, computing diff tables, auditing for vulnerabilities,
and fetching release notes from GitHub.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from .pypi import get_source_url as get_pypi_source_url

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]


# ---------------------------------------------------------------------------
# Command builders
# ---------------------------------------------------------------------------


def uv_cmd(subcommand: str, *, frozen: bool = False) -> list[str]:
    """Build a ``uv <subcommand>`` command prefix with standard flags.

    Always includes ``--no-progress``.  Adds ``--frozen`` when requested
    (appropriate for ``run``, ``export``, ``sync`` — not for ``lock``).
    """
    cmd = ["uv", "--no-progress", subcommand]
    if frozen:
        cmd.append("--frozen")
    return cmd


def uvx_cmd() -> list[str]:
    """Build a ``uvx`` command prefix with standard flags."""
    return ["uvx", "--no-progress"]


GITHUB_API_RELEASE_BY_TAG_URL = (
    "https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
)
"""GitHub API URL for fetching a single release by tag name."""

RELEASE_NOTES_MAX_LENGTH = 2000
"""Maximum characters per package release body before truncation."""


# ---------------------------------------------------------------------------
# uv audit parsing
# ---------------------------------------------------------------------------

_AUDIT_PACKAGE_HEADER_RE = re.compile(
    r"^(\S+)\s+(\S+)\s+has\s+\d+\s+known\s+vulnerabilit"
)
"""Matches the package header line in ``uv audit`` output.

Example: ``pygments 2.19.2 has 1 known vulnerability:``
"""

_AUDIT_ADVISORY_RE = re.compile(r"^-\s+((?:GHSA|CVE|PYSEC)-\S+):\s+(.+)$")
"""Matches advisory ID and title lines in ``uv audit`` output."""

_AUDIT_FIXED_RE = re.compile(r"^\s+Fixed in:\s+(.+)$")
"""Matches ``Fixed in:`` lines in ``uv audit`` output."""

_AUDIT_URL_RE = re.compile(r"^\s+Advisory information:\s+(\S+)$")
"""Matches advisory URL lines in ``uv audit`` output."""


@dataclass
class VulnerablePackage:
    """A single vulnerability advisory for a Python package."""

    name: str
    """Package name."""

    current_version: str
    """Currently resolved version."""

    advisory_id: str
    """Advisory identifier (e.g., ``GHSA-xxxx-xxxx-xxxx``)."""

    advisory_title: str
    """Short description of the vulnerability."""

    fixed_version: str
    """Version that contains the fix, or empty string if unknown."""

    advisory_url: str
    """URL to the advisory details."""


def parse_uv_audit_output(output: str) -> list[VulnerablePackage]:
    """Parse the text output of ``uv audit`` into structured vulnerability data.

    Handles multiple advisories per package and packages without a known fix
    version. Unrecognized lines are silently skipped.

    :param output: Combined stdout/stderr from ``uv audit``.
    :return: A list of :class:`VulnerablePackage` entries.
    """
    vulns: list[VulnerablePackage] = []
    current_name = ""
    current_version = ""
    current_advisory_id = ""
    current_advisory_title = ""
    current_fixed = ""
    current_url = ""

    def _flush() -> None:
        if current_advisory_id:
            vulns.append(
                VulnerablePackage(
                    name=current_name,
                    current_version=current_version,
                    advisory_id=current_advisory_id,
                    advisory_title=current_advisory_title,
                    fixed_version=current_fixed,
                    advisory_url=current_url,
                )
            )

    for line in output.splitlines():
        header = _AUDIT_PACKAGE_HEADER_RE.match(line)
        if header:
            _flush()
            current_name = header.group(1)
            current_version = header.group(2)
            current_advisory_id = ""
            current_advisory_title = ""
            current_fixed = ""
            current_url = ""
            continue

        advisory = _AUDIT_ADVISORY_RE.match(line)
        if advisory:
            # Flush previous advisory for the same package.
            _flush()
            current_advisory_id = advisory.group(1)
            current_advisory_title = advisory.group(2)
            current_fixed = ""
            current_url = ""
            continue

        fixed = _AUDIT_FIXED_RE.match(line)
        if fixed:
            current_fixed = fixed.group(1).strip()
            continue

        url = _AUDIT_URL_RE.match(line)
        if url:
            current_url = url.group(1).strip()
            continue

    _flush()
    return vulns


def format_vulnerability_table(vulns: list[VulnerablePackage]) -> str:
    """Format vulnerability data as a markdown table.

    :param vulns: List of :class:`VulnerablePackage` entries.
    :return: A markdown string with a ``### Vulnerabilities`` heading and table,
        or an empty string if no vulnerabilities are provided.
    """
    if not vulns:
        return ""
    lines = [
        "### Vulnerabilities",
        "",
        "| Package | Advisory | Current | Fixed |",
        "| :-- | :-- | :-- | :-- |",
    ]
    for v in vulns:
        pkg_link = f"[{v.name}](https://pypi.org/project/{v.name}/)"
        if v.advisory_url:
            adv_link = f"[{v.advisory_id}]({v.advisory_url})"
        else:
            adv_link = v.advisory_id
        fixed = f"`{v.fixed_version}`" if v.fixed_version else "unknown"
        lines.append(
            f"| {pkg_link} | {adv_link}: {v.advisory_title} "
            f"| `{v.current_version}` | {fixed} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Lock file noise detection
# ---------------------------------------------------------------------------

# Pattern matching exclude-newer timestamp lines in uv.lock diffs.
# These lines appear in the ``[options]`` section (``exclude-newer``) and the
# ``[options.exclude-newer-package]`` section (per-package entries) and represent
# no actual dependency changes.
_TIMESTAMP_LINE_RE = re.compile(
    r"^\s*("
    r'exclude-newer\s*=\s*"[^"]*"'
    r"|"
    r'\S+\s*=\s*\{[^}]*timestamp\s*=\s*"[^"]*"[^}]*\}'
    r")\s*$"
)
"""Matches ``exclude-newer`` and per-package timestamp lines in uv.lock diffs.

The first alternative matches the top-level ``exclude-newer = "<ISO datetime>"``
line from the ``[options]`` section. The second matches per-package lines like
``repomatic = { timestamp = "<ISO datetime>", span = "PT0S" }`` from the
``[options.exclude-newer-package]`` section. Both change on every ``uv lock``
run when a relative ``exclude-newer-package`` offset is configured.
"""


def is_lock_diff_only_timestamp_noise(lock_path: Path) -> bool:
    """Check whether the only changes in a lock file are timestamp noise.

    Runs ``git diff`` on the given path and inspects every added/removed
    content line. Returns ``True`` only when *all* changed lines match the
    ``exclude-newer-package`` timestamp pattern (``timestamp =`` / ``span =``).

    :param lock_path: Path to the lock file to inspect.
    :return: ``True`` if the diff contains only timestamp noise, ``False``
        if there are no changes or any real dependency change is present.
    """
    result = subprocess.run(
        ["git", "diff", "--", str(lock_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    diff_output = result.stdout
    if not diff_output:
        logging.debug(f"No diff output for {lock_path}.")
        return False

    changed_lines: list[str] = []
    for line in diff_output.splitlines():
        # Skip diff metadata lines.
        if line.startswith(("---", "+++", "@@", "diff ", "index ")):
            continue
        # Collect content lines (added or removed).
        if line.startswith(("+", "-")):
            changed_lines.append(line[1:])

    if not changed_lines:
        logging.debug("Diff contains only metadata, no content changes.")
        return False

    for line in changed_lines:
        if not _TIMESTAMP_LINE_RE.match(line):
            logging.debug(f"Non-timestamp change found: {line!r}")
            return False

    logging.info(
        f"All {len(changed_lines)} changed line(s) in {lock_path}"
        " are exclude-newer-package timestamp noise."
    )
    return True


def revert_lock_if_noise(lock_path: Path) -> bool:
    """Revert a lock file if its only changes are timestamp noise.

    Calls :func:`is_lock_diff_only_timestamp_noise` and, if ``True``,
    runs ``git checkout`` to discard the noise changes.

    .. note::
        In Renovate's ``postUpgradeTasks`` context, the revert is ineffective
        because Renovate captures file content after its own ``uv lock --upgrade``
        manager step *before* ``postUpgradeTasks`` run, and commits its cached
        content regardless of working tree changes.

    :param lock_path: Path to the lock file to inspect and potentially revert.
    :return: ``True`` if the file was reverted, ``False`` otherwise.
    """
    if not is_lock_diff_only_timestamp_noise(lock_path):
        return False

    logging.info(f"Reverting {lock_path}: only exclude-newer-package timestamp noise.")
    subprocess.run(
        ["git", "checkout", "--", str(lock_path)],
        check=True,
    )
    return True


# ---------------------------------------------------------------------------
# pyproject.toml exclude-newer-package management
# ---------------------------------------------------------------------------

_EXCLUDE_NEWER_PKG_RE = re.compile(
    r"^(exclude-newer-package\s*=\s*)\{([^}]*)\}\s*$",
    re.MULTILINE,
)
"""Matches the ``exclude-newer-package = { ... }`` inline table line.

Captures two groups: the key prefix (including ``=``) and the inner content
of the braces, so the line can be rebuilt with additional entries.
"""


def add_exclude_newer_packages(
    pyproject_path: Path,
    packages: set[str],
) -> bool:
    """Add packages to ``[tool.uv].exclude-newer-package`` in ``pyproject.toml``.

    Persists ``"0 day"`` exemptions for the given packages so that subsequent
    ``uv lock --upgrade`` runs (e.g. from the ``sync-uv-lock`` job) do not
    downgrade security-fixed packages back to versions within the
    ``exclude-newer`` cooldown window.

    Skips packages that already have an entry. Returns ``True`` if the file
    was modified.

    :param pyproject_path: Path to the ``pyproject.toml`` file.
    :param packages: Package names to add.
    :return: ``True`` if the file was updated, ``False`` if no changes were needed.
    """
    content = pyproject_path.read_text(encoding="UTF-8")
    pyproject_data = tomllib.loads(content)

    # Determine which packages already have an entry.
    existing = set(
        pyproject_data.get("tool", {}).get("uv", {}).get("exclude-newer-package", {})
    )
    to_add = packages - existing
    if not to_add:
        logging.debug("All packages already in exclude-newer-package, nothing to add.")
        return False

    match = _EXCLUDE_NEWER_PKG_RE.search(content)
    if match:
        # Append new entries to the existing inline table.
        prefix = match.group(1)
        inner = match.group(2).rstrip().rstrip(",")
        new_entries = ", ".join(
            f'"{pkg}" = "0 day"' for pkg in sorted(to_add)
        )
        updated_line = f"{prefix}{{ {inner}, {new_entries} }}"
        content = content[: match.start()] + updated_line + content[match.end() :]
    else:
        # No existing line; insert after exclude-newer if present.
        newer_match = re.search(
            r'^(exclude-newer\s*=\s*"[^"]*")\s*$',
            content,
            re.MULTILINE,
        )
        new_entries = ", ".join(
            f'"{pkg}" = "0 day"' for pkg in sorted(to_add)
        )
        new_line = f"exclude-newer-package = {{ {new_entries} }}"
        if newer_match:
            insert_pos = newer_match.end()
            content = content[:insert_pos] + "\n" + new_line + content[insert_pos:]
        else:
            logging.warning(
                "No [tool.uv] exclude-newer or exclude-newer-package found in"
                f" {pyproject_path}. Cannot persist cooldown exemptions."
            )
            return False

    pyproject_path.write_text(content, encoding="UTF-8")
    logging.info(
        f"Added {', '.join(sorted(to_add))} to exclude-newer-package"
        f" in {pyproject_path}."
    )
    return True


# ---------------------------------------------------------------------------
# Lock file version parsing
# ---------------------------------------------------------------------------


def parse_lock_versions(lock_path: Path) -> dict[str, str]:
    """Parse a ``uv.lock`` file and return a mapping of package names to versions.

    :param lock_path: Path to the ``uv.lock`` file.
    :return: A dict mapping normalized package names to their version strings.
    """
    if not lock_path.exists():
        return {}
    with lock_path.open("rb") as f:
        data = tomllib.load(f)
    return {
        pkg["name"]: pkg["version"]
        for pkg in data.get("package", [])
        if "name" in pkg and "version" in pkg
    }


def parse_lock_upload_times(lock_path: Path) -> dict[str, str]:
    """Parse a ``uv.lock`` file and return a mapping of package names to upload times.

    Extracts the ``upload-time`` field from each package's ``sdist`` entry.

    :param lock_path: Path to the ``uv.lock`` file.
    :return: A dict mapping normalized package names to ISO 8601 upload-time
        strings. Packages without an ``sdist`` or ``upload-time`` are omitted.
    """
    if not lock_path.exists():
        return {}
    with lock_path.open("rb") as f:
        data = tomllib.load(f)
    result = {}
    for pkg in data.get("package", []):
        name = pkg.get("name", "")
        upload_time = pkg.get("sdist", {}).get("upload-time", "")
        if name and upload_time:
            result[name] = upload_time
    return result


def parse_lock_exclude_newer(lock_path: Path) -> str:
    """Parse the ``exclude-newer`` timestamp from a ``uv.lock`` file.

    :param lock_path: Path to the ``uv.lock`` file.
    :return: The ``exclude-newer`` ISO 8601 datetime string, or an empty string
        if not present.
    """
    if not lock_path.exists():
        return ""
    with lock_path.open("rb") as f:
        data = tomllib.load(f)
    result: str = data.get("options", {}).get("exclude-newer", "")
    return result


def parse_lock_specifiers(
    lock_path: Path | None = None,
) -> dict[str, dict[str, str]]:
    """Parse uv.lock to extract dependency specifiers.

    Specifiers are found in ``[package.metadata].requires-dist`` for main
    dependencies and ``[package.metadata.requires-dev].<group>`` for dev groups.

    :param lock_path: Path to uv.lock file. If None, looks in current directory.
    :return: Nested dict mapping package_name -> {dep_name -> specifier}.
    """
    if lock_path is None:
        lock_path = Path("uv.lock")

    if not lock_path.exists():
        return {}

    with lock_path.open("rb") as f:
        lock_data = tomllib.load(f)

    specifiers: dict[str, dict[str, str]] = {}

    for package in lock_data.get("package", []):
        pkg_name = package.get("name", "")
        if not pkg_name:
            continue

        pkg_deps: dict[str, str] = {}
        metadata = package.get("metadata", {})

        # Parse requires-dist for main dependencies.
        for dep in metadata.get("requires-dist", []):
            if isinstance(dep, dict):
                dep_name = dep.get("name", "")
                specifier = dep.get("specifier", "")
                if dep_name and specifier:
                    pkg_deps[dep_name] = specifier

        # Parse requires-dev for dev group dependencies.
        requires_dev = metadata.get("requires-dev", {})
        for group_deps in requires_dev.values():
            for dep in group_deps:
                if isinstance(dep, dict):
                    dep_name = dep.get("name", "")
                    specifier = dep.get("specifier", "")
                    if dep_name and specifier:
                        pkg_deps[dep_name] = specifier

        if pkg_deps:
            specifiers[pkg_name] = pkg_deps

    return specifiers


def parse_lock_subgraph_specifiers(
    lock_path: Path | None = None,
) -> dict[str, dict[str, str]]:
    """Parse uv.lock to extract primary dependency specifiers per group and extra.

    Returns specifiers organized by subgraph name (group or extra), mapping
    each to its primary dependencies (explicitly declared in pyproject.toml)
    with their specifiers.

    :param lock_path: Path to uv.lock file. If None, looks in current directory.
    :return: Dict mapping subgraph_name -> {dep_name -> specifier}.
    """
    if lock_path is None:
        lock_path = Path("uv.lock")

    if not lock_path.exists():
        return {}

    with lock_path.open("rb") as f:
        lock_data = tomllib.load(f)

    result: dict[str, dict[str, str]] = {}

    for package in lock_data.get("package", []):
        metadata = package.get("metadata", {})
        if not metadata:
            continue

        # Parse requires-dev for group specifiers.
        requires_dev = metadata.get("requires-dev", {})
        for group_name, group_deps in requires_dev.items():
            group_specs: dict[str, str] = {}
            for dep in group_deps:
                if isinstance(dep, dict):
                    dep_name = dep.get("name", "")
                    specifier = dep.get("specifier", "")
                    if dep_name:
                        group_specs[dep_name] = specifier
            if group_specs:
                result[group_name] = group_specs

        # Parse requires-dist for extra specifiers.
        for dep in metadata.get("requires-dist", []):
            if not isinstance(dep, dict):
                continue
            marker = dep.get("marker", "")
            # Match entries like: marker = "extra == 'xml'".
            match = re.match(r"extra\s*==\s*'([^']+)'", marker)
            if not match:
                continue
            extra_name = match.group(1)
            dep_name = dep.get("name", "")
            specifier = dep.get("specifier", "")
            if dep_name:
                result.setdefault(extra_name, {})[dep_name] = specifier

    return result


# ---------------------------------------------------------------------------
# Lock file diff formatting
# ---------------------------------------------------------------------------


def _format_upload_date(iso_datetime: str) -> str:
    """Format an ISO 8601 datetime as a human-readable date string.

    :param iso_datetime: An ISO 8601 datetime string (e.g.,
        ``"2026-03-13T12:00:00Z"``).
    :return: A formatted date like ``2026-03-13``, or the raw string if parsing
        fails.
    """
    try:
        # Truncate fractional seconds to 6 digits (microseconds) for Python
        # 3.10 compatibility. fromisoformat on 3.10 rejects nanosecond
        # precision (9+ digits) that tools like uv emit.
        normalized = re.sub(
            r"(\.\d{6})\d+",
            r"\1",
            iso_datetime.replace("Z", "+00:00"),
        )
        dt = datetime.fromisoformat(normalized)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return iso_datetime


def diff_lock_versions(
    before: dict[str, str],
    after: dict[str, str],
) -> list[tuple[str, str, str]]:
    """Compare two version mappings and return the list of changes.

    :param before: Package versions before the upgrade.
    :param after: Package versions after the upgrade.
    :return: A sorted list of ``(name, old_version, new_version)`` tuples.
        ``old_version`` is empty for added packages; ``new_version`` is empty
        for removed packages.
    """
    changes = []
    for name in sorted(set(before) | set(after)):
        old = before.get(name, "")
        new = after.get(name, "")
        if old != new:
            changes.append((name, old, new))
    return changes


def format_diff_table(
    changes: list[tuple[str, str, str]],
    upload_times: dict[str, str] | None = None,
    exclude_newer: str = "",
) -> str:
    """Format version changes as a markdown table with heading.

    When ``upload_times`` is provided, a "Released" column is added so
    reviewers can visually verify that all updated packages respect the
    ``exclude-newer`` cutoff. The cutoff itself is shown above the table
    when ``exclude_newer`` is non-empty.

    :param changes: List of ``(name, old_version, new_version)`` tuples
        as returned by :func:`diff_lock_versions`.
    :param upload_times: Optional mapping of package names to ISO 8601
        upload-time strings, as returned by :func:`parse_lock_upload_times`.
    :param exclude_newer: Optional ``exclude-newer`` ISO 8601 datetime from
        the lock file, as returned by :func:`parse_lock_exclude_newer`.
    :return: A markdown string with a ``### Updated packages`` heading and
        table, or an empty string if there are no changes.
    """
    if not changes:
        return ""
    show_uploaded = bool(upload_times)
    lines = ["### Updated packages", ""]
    if exclude_newer:
        cutoff = _format_upload_date(exclude_newer)
        lines.append(
            f"Resolved with [`exclude-newer`]"
            f"(https://docs.astral.sh/uv/reference/settings/#exclude-newer)"
            f" cutoff: `{cutoff}`."
        )
        lines.append("")
    if show_uploaded:
        lines.append("| Package | Change | Released |")
        lines.append("| :-- | :-- | :-- |")
    else:
        lines.append("| Package | Change |")
        lines.append("| :-- | :-- |")
    for name, old, new in changes:
        link = f"[{name}](https://pypi.org/project/{name}/)"
        if old and new:
            change = f"`{old}` -> `{new}`"
        elif new:
            change = f"(new) `{new}`"
        else:
            change = f"`{old}` (removed)"
        if show_uploaded:
            raw_time = upload_times.get(name, "")  # type: ignore[union-attr]
            uploaded = _format_upload_date(raw_time) if raw_time else ""
            lines.append(f"| {link} | {change} | {uploaded} |")
        else:
            lines.append(f"| {link} | {change} |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# GitHub release notes
# ---------------------------------------------------------------------------


def _github_api_request(url: str) -> Request:
    """Build a GitHub API request with optional token authentication.

    Uses ``GITHUB_TOKEN`` or ``GH_TOKEN`` from the environment when available
    to raise the rate limit from 60 to 1000 requests/hour.
    """
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return Request(url, headers=headers)


def _parse_github_owner_repo(repo_url: str) -> tuple[str, str] | None:
    """Extract ``(owner, repo)`` from a GitHub URL.

    :param repo_url: A GitHub repository URL (e.g.,
        ``https://github.com/nedbat/coveragepy``).
    :return: A tuple of ``(owner, repo)``, or ``None`` if parsing fails.
    """
    parts = repo_url.rstrip("/").removesuffix(".git").split("/")
    if len(parts) < 2:
        return None
    return parts[-2], parts[-1]


def get_github_release_body(repo_url: str, version: str) -> tuple[str, str]:
    """Fetch the release notes body for a specific version from GitHub.

    Tries ``v{version}`` first (most common for Python packages), then
    the bare ``{version}`` tag.

    :param repo_url: GitHub repository URL.
    :param version: The version string (e.g., ``7.13.5``).
    :return: A tuple of ``(tag, body)`` where ``tag`` is the matched tag name
        and ``body`` is the release notes markdown. Both are empty strings if
        no release is found.
    """
    parsed = _parse_github_owner_repo(repo_url)
    if not parsed:
        return "", ""
    owner, repo = parsed

    for tag in (f"v{version}", version):
        url = GITHUB_API_RELEASE_BY_TAG_URL.format(
            owner=owner,
            repo=repo,
            tag=tag,
        )
        request = _github_api_request(url)
        try:
            with urlopen(request, timeout=10) as response:
                data = json.loads(response.read())
        except (URLError, TimeoutError, json.JSONDecodeError):
            continue
        else:
            body = data.get("body", "")
            return tag, body
    logging.debug(f"No GitHub release found for {repo_url} version {version}.")
    return "", ""


def fetch_release_notes(
    changes: list[tuple[str, str, str]],
) -> dict[str, tuple[str, str, str]]:
    """Fetch release notes for all updated packages.

    For each package with a new version, discovers the GitHub repository via
    PyPI and fetches the release notes from GitHub Releases.

    :param changes: List of ``(name, old_version, new_version)`` tuples.
    :return: A dict mapping package names to ``(repo_url, tag, body)`` tuples.
        Only packages with non-empty release bodies are included.
    """
    notes: dict[str, tuple[str, str, str]] = {}
    for name, _old, new in changes:
        if not new:
            # Skip removed packages.
            continue
        repo_url = get_pypi_source_url(name)
        if not repo_url:
            logging.debug(f"No GitHub URL found for {name}.")
            continue
        tag, body = get_github_release_body(repo_url, new)
        if body:
            notes[name] = (repo_url, tag, body)
        else:
            logging.debug(f"No release body for {name} {new}.")
    return notes


def format_release_notes(notes: dict[str, tuple[str, str, str]]) -> str:
    """Render release notes as collapsible ``<details>`` blocks.

    Follows Renovate's visual pattern: a "Release notes" heading with one
    collapsible section per package. Long release bodies are truncated to
    :data:`RELEASE_NOTES_MAX_LENGTH` characters with a link to the full release.

    :param notes: A dict mapping package names to ``(repo_url, tag, body)``
        tuples, as returned by :func:`fetch_release_notes`.
    :return: A markdown string with the release notes section, or an empty
        string if no notes are available.
    """
    if not notes:
        return ""
    lines = ["### Release notes", ""]
    for name, (repo_url, tag, body) in sorted(notes.items()):
        parsed = _parse_github_owner_repo(repo_url)
        if not parsed:
            continue
        owner, repo = parsed
        release_url = f"{repo_url}/releases/tag/{tag}"
        lines.append("<details>")
        lines.append(f"<summary>{owner}/{repo} ({name})</summary>")
        lines.append("")
        lines.append(f"#### [`{tag}`]({release_url})")
        lines.append("")
        if len(body) > RELEASE_NOTES_MAX_LENGTH:
            truncated = body[:RELEASE_NOTES_MAX_LENGTH].rsplit("\n", 1)[0]
            lines.append(truncated)
            lines.append("")
            lines.append(f"... [Full release notes]({release_url})")
        else:
            lines.append(body)
        lines.append("")
        lines.append("</details>")
        lines.append("")
    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# High-level operations
# ---------------------------------------------------------------------------


def fix_vulnerable_deps(lock_path: Path) -> tuple[bool, str]:
    """Detect vulnerable packages and upgrade them in the lock file.

    Runs ``uv audit`` to detect vulnerabilities, then upgrades each fixable
    package with ``uv lock --upgrade-package`` using ``--exclude-newer-package``
    to bypass the ``exclude-newer`` cooldown for security fixes. Also persists
    the exemptions in ``pyproject.toml`` so that subsequent ``uv lock --upgrade``
    runs (e.g. from the ``sync-uv-lock`` job) do not downgrade the fixed
    packages back within the cooldown window.

    :param lock_path: Path to the ``uv.lock`` file.
    :return: A tuple of ``(has_fixes, diff_table)``. ``has_fixes`` is ``True``
        when at least one vulnerable package was upgraded. ``diff_table`` is a
        markdown-formatted string with vulnerability details and version changes,
        or an empty string if no fixable vulnerabilities were found.
    """
    # Step 1: Run uv audit and capture output.
    result = subprocess.run(
        [*uv_cmd("audit"), "--frozen"],
        capture_output=True,
        text=True,
        check=False,
    )
    audit_output = result.stdout + "\n" + result.stderr

    # Step 2: Parse vulnerabilities.
    vulns = parse_uv_audit_output(audit_output)
    if not vulns:
        logging.info("No vulnerabilities found.")
        return False, ""

    # Deduplicate packages: multiple advisories can target the same package.
    fixable_packages = {v.name for v in vulns if v.fixed_version}
    if not fixable_packages:
        logging.warning(
            f"Found {len(vulns)} vulnerabilities but none have a known fix version."
        )
        return False, ""

    logging.info(
        f"Found {len(vulns)} vulnerabilities across"
        f" {len(fixable_packages)} fixable packages: {', '.join(sorted(fixable_packages))}."
    )

    # Step 3: Snapshot versions before upgrading.
    before = parse_lock_versions(lock_path)

    # Step 4: Upgrade all fixable packages in a single resolution pass.
    # Running one command avoids sequential re-resolution undoing earlier upgrades.
    cmd = [*uv_cmd("lock")]
    for pkg in sorted(fixable_packages):
        cmd.extend([
            "--upgrade-package",
            pkg,
            "--exclude-newer-package",
            f"{pkg}=0 day",
        ])
    logging.info(f"Upgrading: {', '.join(sorted(fixable_packages))}...")
    subprocess.run(cmd, check=True)

    # Step 5: Check if the lock file actually changed.
    if revert_lock_if_noise(lock_path):
        logging.info("Lock file changes were only timestamp noise.")
        return False, ""

    # Step 6: Compute version diff.
    after = parse_lock_versions(lock_path)
    changes = diff_lock_versions(before, after)
    if not changes:
        logging.info("No version changes after upgrading vulnerable packages.")
        return False, ""

    # Step 7: Persist cooldown exemptions in pyproject.toml so sync-uv-lock
    # does not revert the security upgrades.
    pyproject_path = lock_path.parent / "pyproject.toml"
    if pyproject_path.exists():
        upgraded = {name for name, _old, _new in changes}
        add_exclude_newer_packages(pyproject_path, upgraded)

    # Step 8: Build the combined output.
    vuln_table = format_vulnerability_table(vulns)
    upload_times = parse_lock_upload_times(lock_path)
    diff_table = format_diff_table(changes, upload_times)

    # Fetch and append release notes.
    notes = fetch_release_notes(changes)
    notes_section = format_release_notes(notes)

    sections = [vuln_table, diff_table]
    if notes_section:
        sections.append(notes_section)
    combined = "\n\n".join(s for s in sections if s)

    return True, combined


def sync_uv_lock(lock_path: Path) -> tuple[bool, str]:
    """Re-lock with ``--upgrade`` and revert if only timestamp noise changed.

    Runs ``uv lock --upgrade`` to update transitive dependencies to their
    latest allowed versions, replacing Renovate's ``lockFileMaintenance``
    which cannot reliably revert noise-only changes. If the resulting diff
    contains only ``exclude-newer-package`` timestamp noise, it reverts
    ``uv.lock`` so ``peter-evans/create-pull-request`` sees no diff and
    skips creating a PR.

    When real changes exist, computes a diff table comparing package versions
    before and after the upgrade.

    :param lock_path: Path to the ``uv.lock`` file.
    :return: A tuple of ``(reverted, diff_table)``. ``reverted`` is ``True``
        if the lock file was reverted (noise only). ``diff_table`` is a
        markdown-formatted table of version changes, or an empty string if
        reverted or no version changes were found.
    """
    # Step 1: Snapshot versions before upgrading.
    before = parse_lock_versions(lock_path)

    # Step 2: Run uv lock --upgrade.
    logging.info("Running uv lock --upgrade...")
    subprocess.run([*uv_cmd("lock"), "--upgrade"], check=True)

    # Step 3: Revert uv.lock if only timestamp noise changed.
    if revert_lock_if_noise(lock_path):
        return True, ""

    # Step 4: Compute and format the version diff.
    after = parse_lock_versions(lock_path)
    changes = diff_lock_versions(before, after)
    upload_times = parse_lock_upload_times(lock_path)
    exclude_newer = parse_lock_exclude_newer(lock_path)
    diff_table = format_diff_table(changes, upload_times, exclude_newer)

    # Step 5: Fetch and append release notes.
    if changes:
        notes = fetch_release_notes(changes)
        notes_section = format_release_notes(notes)
        if notes_section:
            diff_table = diff_table + "\n\n" + notes_section

    return False, diff_table
