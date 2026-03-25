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

"""Renovate-related utilities for GitHub Actions workflows.

This module provides utilities for managing Renovate prerequisites,
migrating from Dependabot to Renovate, and reverting lock file noise
caused by ``exclude-newer-package`` timestamp churn.

.. note::
    This module also contains general dependency management utilities
    (e.g., ``sync_uv_lock``) that are not strictly Renovate-specific.
    If more non-Renovate dependency code accumulates here, consider
    renaming this module to ``dependencies.py`` or similar.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from click_extra import TableFormat, render_table

from .github.actions import AnnotationLevel, emit_annotation
from .github.gh import run_gh_command
from .github.pr_body import render_template
from .tool_runner import uv_cmd

if sys.version_info >= (3, 11):
    from enum import StrEnum

    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]
    from backports.strenum import StrEnum  # type: ignore[import-not-found]


class CheckFormat(StrEnum):
    """Output format for Renovate prerequisite checks."""

    github = "github"
    json = "json"
    text = "text"


@dataclass
class RenovateCheckResult:
    """Result of all Renovate prerequisite checks.

    This dataclass holds the results of each check, allowing workflows to
    consume the data and build dynamic PR bodies or conditional logic.
    """

    renovate_config_exists: bool
    """Whether renovate.json5 exists in the repository."""

    dependabot_config_path: str
    """Path to Dependabot config file, or empty string if not found."""

    dependabot_security_disabled: bool
    """Whether Dependabot security updates are disabled."""

    commit_statuses_permission: bool
    """Whether the token has commit statuses permission."""

    repo: str = ""
    """Repository in 'owner/repo' format, used for generating settings links."""

    def to_github_output(self) -> str:
        """Format results for GitHub Actions output.

        :return: Multi-line string in key=value format for $GITHUB_OUTPUT.
        """
        lines = [
            f"renovate_config_exists={str(self.renovate_config_exists).lower()}",
            f"dependabot_config_path={self.dependabot_config_path}",
            "dependabot_security_disabled="
            f"{str(self.dependabot_security_disabled).lower()}",
            "commit_statuses_permission="
            f"{str(self.commit_statuses_permission).lower()}",
            f"pr_body<<EOF\n{self.to_pr_body()}\nEOF",
        ]
        return "\n".join(lines)

    def to_json(self) -> str:
        """Format results as JSON.

        :return: JSON string representation of the check results.
        """
        return json.dumps(asdict(self), indent=2)

    def to_pr_body(self) -> str:
        """Generate PR body for the migration PR.

        :return: Markdown-formatted PR body with changes and prerequisites table.
        """
        # Build changes bullet list.
        changes = []
        if not self.renovate_config_exists:
            changes.append("- Export `renovate.json5` configuration file")
        if self.dependabot_config_path:
            changes.append(f"- Remove `{self.dependabot_config_path}`")
        if self.renovate_config_exists and not self.dependabot_config_path:
            changes.append("- No changes needed")
        changes_list = "\n".join(changes)

        # Build prerequisites status table.
        settings_url = f"https://github.com/{self.repo}/settings/security_analysis"
        docs_url = "https://github.com/kdeldycke/repomatic#permissions-and-token"

        table_data = [
            [
                "`renovate.json5` exists",
                "✅ Already exists"
                if self.renovate_config_exists
                else "🔧 Created by this PR",
                "—",
            ],
            [
                "Dependabot config removed",
                "✅ Not present"
                if not self.dependabot_config_path
                else "🔧 Removed by this PR",
                "—",
            ],
            [
                "Dependabot security updates",
                "✅ Disabled" if self.dependabot_security_disabled else "⚠️ Enabled",
                "—"
                if self.dependabot_security_disabled
                else f"[Disable in Settings]({settings_url})",
            ],
            [
                "Commit statuses permission",
                "✅ Token has access"
                if self.commit_statuses_permission
                else "⚠️ Cannot verify",
                "—"
                if self.commit_statuses_permission
                else f"[Check PAT permissions]({docs_url})",
            ],
        ]

        prerequisites_table = render_table(
            table_data,
            headers=["Check", "Status", "Action"],
            table_format=TableFormat.GITHUB,
        )

        return render_template(
            "renovate-migration",
            changes_list=changes_list,
            prerequisites_table=prerequisites_table,
        )


def get_dependabot_config_path() -> Path | None:
    """Get the path to the Dependabot configuration file if it exists.

    :return: Path to the Dependabot config file, or None if not found.
    """
    for filename in (".github/dependabot.yaml", ".github/dependabot.yml"):
        path = Path(filename)
        if path.exists():
            return path
    return None


def check_dependabot_config_absent() -> tuple[bool, str]:
    """Check that no Dependabot version updates config file exists.

    Renovate handles dependency updates, so Dependabot should be disabled.

    :return: Tuple of (passed, message).
    """
    path = get_dependabot_config_path()
    if path:
        msg = (
            f"Dependabot config found at {path}. "
            "Remove it and migrate to Renovate: "
            "run `repomatic init renovate` to get a starter config, "
            "then use the reusable renovate.yaml workflow."
        )
        return False, msg

    return True, "Dependabot version updates: disabled (no config file)"


def check_dependabot_security_disabled(repo: str) -> tuple[bool, str]:
    """Check that Dependabot security updates are disabled.

    Renovate creates security PRs instead.

    :param repo: Repository in 'owner/repo' format.
    :return: Tuple of (passed, message).
    """
    try:
        output = run_gh_command([
            "api",
            f"repos/{repo}",
            "--jq",
            '.security_and_analysis.dependabot_security_updates.status // "disabled"',
        ])
        status = output.strip()
    except RuntimeError as e:
        logging.warning(f"Failed to check Dependabot security status: {e}")
        return True, "Could not verify Dependabot security updates status."

    if status == "enabled":
        msg = (
            "Dependabot security updates are enabled. Disable them in "
            "Settings > Advanced Security > Dependabot > Dependabot security updates."
        )
        return False, msg

    return True, "Dependabot security updates: disabled (Renovate handles security PRs)"


def check_commit_statuses_permission(repo: str, sha: str) -> tuple[bool, str]:
    """Check that the token has commit statuses permission.

    Required for Renovate to set stability-days status checks.

    :param repo: Repository in 'owner/repo' format.
    :param sha: Commit SHA to check.
    :return: Tuple of (passed, message).
    """
    try:
        run_gh_command([
            "api",
            f"repos/{repo}/commits/{sha}/statuses",
            "--silent",
        ])
    except RuntimeError:
        msg = (
            "Cannot verify commit statuses permission. "
            "Ensure the token has 'Commit statuses: Read and Write' permission."
        )
        return False, msg
    else:
        return True, "Commit statuses: token has access"


def run_renovate_prereq_checks(repo: str, sha: str) -> int:
    """Run all Renovate prerequisite checks.

    Emits GitHub Actions annotations for each check result.

    :param repo: Repository in 'owner/repo' format.
    :param sha: Commit SHA for permission checks.
    :return: Exit code (0 for success, 1 for fatal errors).
    """
    fatal_error = False

    # Check 1: Dependabot config file.
    passed, msg = check_dependabot_config_absent()
    if passed:
        print(f"✓ {msg}")
    else:
        emit_annotation(AnnotationLevel.ERROR, msg)
        fatal_error = True

    # Check 2: Dependabot security updates.
    passed, msg = check_dependabot_security_disabled(repo)
    if passed:
        print(f"✓ {msg}")
    else:
        emit_annotation(AnnotationLevel.ERROR, msg)
        fatal_error = True

    # Check 3: Commit statuses permission (non-fatal).
    passed, msg = check_commit_statuses_permission(repo, sha)
    if passed:
        print(f"✓ {msg}")
    else:
        emit_annotation(AnnotationLevel.WARNING, msg)

    return 1 if fatal_error else 0


def check_renovate_config_exists() -> tuple[bool, str]:
    """Check if renovate.json5 configuration file exists.

    :return: Tuple of (exists, message).
    """
    if Path("renovate.json5").exists():
        return True, "Renovate config: renovate.json5 exists"

    msg = "renovate.json5 not found. Run `repomatic init renovate` to create it."
    return False, msg


def collect_check_results(repo: str, sha: str) -> RenovateCheckResult:
    """Collect all Renovate prerequisite check results.

    Runs all checks and returns structured results that can be formatted
    as JSON or GitHub Actions output.

    :param repo: Repository in 'owner/repo' format.
    :param sha: Commit SHA for permission checks.
    :return: RenovateCheckResult with all check outcomes.
    """
    # Check 1: Renovate config exists.
    renovate_exists, _ = check_renovate_config_exists()

    # Check 2: Dependabot config path.
    dependabot_path = get_dependabot_config_path()

    # Check 3: Dependabot security updates disabled.
    security_disabled, _ = check_dependabot_security_disabled(repo)

    # Check 4: Commit statuses permission.
    statuses_permission, _ = check_commit_statuses_permission(repo, sha)

    return RenovateCheckResult(
        renovate_config_exists=renovate_exists,
        dependabot_config_path=dependabot_path.as_posix() if dependabot_path else "",
        dependabot_security_disabled=security_disabled,
        commit_statuses_permission=statuses_permission,
        repo=repo,
    )


def run_migration_checks(repo: str, sha: str) -> int:
    """Run Renovate migration prerequisite checks with console output.

    Checks for:
    - Missing renovate.json5 configuration
    - Existing Dependabot configuration
    - Dependabot security updates enabled
    - Token commit statuses permission

    :param repo: Repository in 'owner/repo' format.
    :param sha: Commit SHA for permission checks.
    :return: Exit code (0 for success, 1 for fatal errors).
    """
    fatal_error = False

    # Check 1: Renovate config exists.
    renovate_exists, renovate_msg = check_renovate_config_exists()
    if renovate_exists:
        print(f"✓ {renovate_msg}")
    else:
        emit_annotation(AnnotationLevel.ERROR, renovate_msg)
        fatal_error = True

    # Check 2: Dependabot config absent.
    passed, msg = check_dependabot_config_absent()
    if passed:
        print(f"✓ {msg}")
    else:
        emit_annotation(AnnotationLevel.ERROR, msg)
        fatal_error = True

    # Check 3: Dependabot security updates disabled.
    passed, msg = check_dependabot_security_disabled(repo)
    if passed:
        print(f"✓ {msg}")
    else:
        emit_annotation(AnnotationLevel.ERROR, msg)
        fatal_error = True

    # Check 4: Commit statuses permission (non-fatal).
    passed, msg = check_commit_statuses_permission(repo, sha)
    if passed:
        print(f"✓ {msg}")
    else:
        emit_annotation(AnnotationLevel.WARNING, msg)

    return 1 if fatal_error else 0


GITHUB_API_RELEASE_BY_TAG_URL = (
    "https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
)
"""GitHub API URL for fetching a single release by tag name."""

PYPI_JSON_API_URL = "https://pypi.org/pypi/{package}/json"
"""PyPI JSON API URL for fetching package metadata."""

RELEASE_NOTES_MAX_LENGTH = 2000
"""Maximum characters per package release body before truncation."""

# Keys in PyPI ``project_urls`` that typically point to a GitHub repository,
# checked in priority order.
_PYPI_SOURCE_URL_KEYS = (
    "Source",
    "Source Code",
    "Source code",
    "Repository",
    "Code",
    "Homepage",
)


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


def _format_upload_date(iso_datetime: str) -> str:
    """Format an ISO 8601 datetime as a human-readable date string.

    :param iso_datetime: An ISO 8601 datetime string (e.g.,
        ``"2026-03-13T12:00:00Z"``).
    :return: A formatted date like ``2026-03-13``, or the raw string if parsing
        fails.
    """
    try:
        dt = datetime.fromisoformat(iso_datetime.replace("Z", "+00:00"))
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
        lines.append(f"Resolved with `exclude-newer` cutoff: `{cutoff}`.")
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


def get_pypi_source_url(package: str) -> str | None:
    """Discover the GitHub repository URL for a PyPI package.

    Queries the PyPI JSON API and scans ``project_urls`` for keys that
    typically point to a source repository on GitHub.

    :param package: The PyPI package name.
    :return: The GitHub repository URL, or ``None`` if not found.
    """
    url = PYPI_JSON_API_URL.format(package=package)
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=10) as response:
            data = json.loads(response.read())
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        logging.debug(f"PyPI lookup failed for {package}: {exc}")
        return None

    project_urls: dict[str, str] = data.get("info", {}).get("project_urls") or {}
    for key in _PYPI_SOURCE_URL_KEYS:
        candidate = project_urls.get(key, "")
        if "github.com" in candidate:
            return candidate.rstrip("/").removesuffix(".git")
    # Fallback: scan all values for a GitHub URL.
    for candidate in project_urls.values():
        if "github.com" in candidate:
            return candidate.rstrip("/").removesuffix(".git")
    return None


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
            owner=owner, repo=repo, tag=tag,
        )
        request = _github_api_request(url)
        try:
            with urlopen(request, timeout=10) as response:
                data = json.loads(response.read())
            body = data.get("body", "")
            return tag, body
        except (URLError, TimeoutError, json.JSONDecodeError):
            continue
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
