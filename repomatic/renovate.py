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
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from click_extra import TableFormat, render_table

from .github.actions import AnnotationLevel, emit_annotation
from .github.gh import run_gh_command

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
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
        lines = ["Migrate from Dependabot to Renovate.", ""]

        # Changes section.
        lines.append("## Changes")
        if not self.renovate_config_exists:
            lines.append("- Export `renovate.json5` configuration file")
        if self.dependabot_config_path:
            lines.append(f"- Remove `{self.dependabot_config_path}`")
        if self.renovate_config_exists and not self.dependabot_config_path:
            lines.append("- No changes needed")
        lines.append("")

        # Prerequisites status table.
        lines.append("## Prerequisites Status")
        lines.append("")

        # Build table rows.
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

        lines.append(
            render_table(
                table_data,
                headers=["Check", "Status", "Action"],
                table_format=TableFormat.GITHUB,
            )
        )
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(
            "🤖 Generated with [repomatic](https://github.com/kdeldycke/repomatic)"
        )

        return "\n".join(lines)


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
    :return: Tuple of (passed, message). This check never fails fatally.
    """
    try:
        run_gh_command([
            "api",
            f"repos/{repo}/commits/{sha}/statuses",
            "--silent",
        ])
        return True, "Commit statuses: token has access"
    except RuntimeError:
        msg = (
            "Cannot verify commit statuses permission. "
            "Ensure the token has 'Commit statuses: Read and Write' permission."
        )
        return True, msg  # Non-fatal.


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


def sync_uv_lock(lock_path: Path) -> bool:
    """Re-lock with ``--upgrade`` and revert if only timestamp noise changed.

    Runs ``uv lock --upgrade`` to update transitive dependencies to their
    latest allowed versions, replacing Renovate's ``lockFileMaintenance``
    which cannot reliably revert noise-only changes. If the resulting diff
    contains only ``exclude-newer-package`` timestamp noise, it reverts
    ``uv.lock`` so ``peter-evans/create-pull-request`` sees no diff and
    skips creating a PR.

    :param lock_path: Path to the ``uv.lock`` file.
    :return: ``True`` if the lock file was reverted (noise only),
        ``False`` if it contains real dependency changes.
    """
    # Step 1: Run uv lock --upgrade.
    logging.info("Running uv lock --upgrade...")
    subprocess.run(["uv", "--no-progress", "lock", "--upgrade"], check=True)

    # Step 2: Revert uv.lock if only timestamp noise changed.
    return revert_lock_if_noise(lock_path)
