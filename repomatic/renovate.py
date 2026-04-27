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

This module provides utilities for managing Renovate prerequisites and
migrating from Dependabot to Renovate. uv lock file operations (version
parsing, noise detection, vulnerability auditing) live in {mod}`repomatic.uv`.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from click_extra import TableFormat, render_table

RENOVATE_CONFIG_PATH = Path("renovate.json5")
"""Canonical path to the Renovate configuration file."""

from .github.actions import AnnotationLevel, emit_annotation
from .github.gh import run_gh_command
from .github.pr_body import render_template
from .github.token import check_all_pat_permissions

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from backports.strenum import StrEnum


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

    contents_permission: bool = True
    """Whether the token has contents permission."""

    issues_permission: bool = True
    """Whether the token has issues permission."""

    pull_requests_permission: bool = True
    """Whether the token has pull requests permission."""

    vulnerability_alerts_permission: bool = True
    """Whether the token has Dependabot alerts permission."""

    workflows_permission: bool = True
    """Whether the token has workflows permission."""

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
            f"contents_permission={str(self.contents_permission).lower()}",
            f"issues_permission={str(self.issues_permission).lower()}",
            f"pull_requests_permission={str(self.pull_requests_permission).lower()}",
            "vulnerability_alerts_permission="
            f"{str(self.vulnerability_alerts_permission).lower()}",
            f"workflows_permission={str(self.workflows_permission).lower()}",
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
        if self.dependabot_config_path:
            changes.append(f"- Remove `{self.dependabot_config_path}`")
        if not changes:
            changes.append("- No changes needed")
        changes_list = "\n".join(changes)

        # Build prerequisites status table.
        settings_url = f"https://github.com/{self.repo}/settings/security_analysis"
        docs_url = "https://github.com/kdeldycke/repomatic#permissions-and-token"

        # Permission check rows: (label, field_value).
        perm_checks = [
            ("Commit statuses permission", self.commit_statuses_permission),
            ("Contents permission", self.contents_permission),
            ("Issues permission", self.issues_permission),
            ("Pull requests permission", self.pull_requests_permission),
            ("Vulnerability alerts permission", self.vulnerability_alerts_permission),
            ("Workflows permission", self.workflows_permission),
        ]

        table_data = [
            [
                "`renovate.json5` exists",
                "✅ Already exists"
                if self.renovate_config_exists
                else "ℹ️ Materialized at runtime",
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
            *[
                [
                    label,
                    "✅ Token has access" if passed else "⚠️ Cannot verify",
                    "—" if passed else f"[Check PAT permissions]({docs_url})",
                ]
                for label, passed in perm_checks
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


def check_renovate_config_exists() -> tuple[bool, str]:
    """Check if renovate.json5 configuration file exists.

    :return: Tuple of (exists, message).
    """
    if RENOVATE_CONFIG_PATH.exists():
        return True, f"Renovate config: {RENOVATE_CONFIG_PATH} exists"

    msg = (
        f"{RENOVATE_CONFIG_PATH} not found. Run `repomatic init renovate` to create it."
    )
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

    # Check 4-9: PAT permissions (shared code path with lint-repo/setup-guide).
    pat = check_all_pat_permissions(repo, sha)

    return RenovateCheckResult(
        renovate_config_exists=renovate_exists,
        dependabot_config_path=dependabot_path.as_posix() if dependabot_path else "",
        dependabot_security_disabled=security_disabled,
        commit_statuses_permission=pat.commit_statuses[0]
        if pat.commit_statuses
        else True,
        contents_permission=pat.contents[0],
        issues_permission=pat.issues[0],
        pull_requests_permission=pat.pull_requests[0],
        vulnerability_alerts_permission=pat.vulnerability_alerts[0],
        workflows_permission=pat.workflows[0],
        repo=repo,
    )


def run_migration_checks(repo: str, sha: str) -> int:
    """Run Renovate migration prerequisite checks with console output.

    Checks for:

    - Missing renovate.json5 configuration
    - Existing Dependabot configuration
    - Dependabot security updates enabled
    - PAT permissions: commit statuses, contents, issues, pull requests,
      vulnerability alerts, workflows

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

    # PAT permission checks (shared code path, all non-fatal warnings).
    pat = check_all_pat_permissions(repo, sha)
    for passed, msg in pat.iter_results():
        if passed:
            print(f"✓ {msg}")
        else:
            emit_annotation(AnnotationLevel.WARNING, msg)

    return 1 if fatal_error else 0
