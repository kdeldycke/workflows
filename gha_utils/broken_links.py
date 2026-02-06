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

"""Manage the broken links issue lifecycle.

This module consolidates the entire broken links issue management into a single
workflow: listing open issues, triaging duplicates, closing old issues, and
creating or updating the main issue.

Uses the GitHub CLI (``gh``) to interact with issues.

We need to manually manage the life-cycle of issues created in this job because the
``create-issue-from-file`` action blindly creates issues ad-nauseam.

See:
- https://github.com/peter-evans/create-issue-from-file/issues/298
- https://github.com/lycheeverse/lychee-action/issues/74#issuecomment-1587089689
"""

from __future__ import annotations

import json
import logging
from operator import itemgetter
from pathlib import Path
from subprocess import run

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Any


# Issue title and author are hardcoded for this specific use case.
ISSUE_TITLE = "Broken links"
ISSUE_AUTHOR = "github-actions[bot]"


def run_gh_command(args: list[str]) -> str:
    """Run a gh CLI command and return stdout.

    :param args: Command arguments to pass to ``gh``.
    :return: The stdout output from the command.
    :raises RuntimeError: If the command fails.
    """
    cmd = ["gh", *args]
    logging.debug(f"Running: {' '.join(cmd)}")
    process = run(cmd, capture_output=True, encoding="UTF-8")

    if process.returncode:
        logging.debug(f"gh command failed: {process.stderr}")
        raise RuntimeError(process.stderr)

    return process.stdout


def list_open_issues() -> list[dict[str, Any]]:
    """List open issues by the bot author.

    :return: List of issue dicts with ``number``, ``title``, and ``createdAt``.
    """
    output = run_gh_command([
        "issue",
        "list",
        "--state",
        "open",
        "--author",
        ISSUE_AUTHOR,
        "--json",
        "number,title,createdAt",
    ])
    return json.loads(output)  # type: ignore[no-any-return]


def close_issue(number: int, comment: str) -> None:
    """Close an issue with a comment.

    :param number: The issue number to close.
    :param comment: The comment to add when closing.
    """
    run_gh_command([
        "issue",
        "close",
        str(number),
        "--comment",
        comment,
    ])
    logging.info(f"Closed issue #{number}")


def create_issue(
    body_file: Path, labels: list[str], title: str = ISSUE_TITLE
) -> int:
    """Create a new issue.

    :param body_file: Path to the file containing the issue body.
    :param labels: List of labels to apply.
    :param title: Issue title. Defaults to ``ISSUE_TITLE``.
    :return: The created issue number.
    """
    args = [
        "issue",
        "create",
        "--title",
        title,
        "--body-file",
        str(body_file),
    ]
    for label in labels:
        args.extend(["--label", label])

    output = run_gh_command(args)
    # gh issue create outputs the issue URL, extract the number from it.
    # Format: https://github.com/owner/repo/issues/123
    issue_url = output.strip()
    issue_number = int(issue_url.rstrip("/").split("/")[-1])
    logging.info(f"Created issue #{issue_number}")
    return issue_number


def update_issue(number: int, body_file: Path) -> None:
    """Update an existing issue body.

    :param number: The issue number to update.
    :param body_file: Path to the file containing the new issue body.
    """
    run_gh_command([
        "issue",
        "edit",
        str(number),
        "--body-file",
        str(body_file),
    ])
    logging.info(f"Updated issue #{number}")


def get_label(repo_name: str) -> str:
    """Return the appropriate label based on repository name.

    :param repo_name: The repository name.
    :return: ``"🩹 fix link"`` for ``awesome-*`` repos, else ``"📚 documentation"``.
    """
    if repo_name.startswith("awesome-"):
        return "🩹 fix link"
    return "📚 documentation"


def triage_issues(
    issues: list[dict],
    title: str,
    needed: bool,
) -> tuple[bool, int | None, set[int]]:
    """Triage issues matching a title for deduplication.

    :param issues: List of issue dicts from ``gh issue list --json
        number,title,createdAt``.
    :param title: Issue title to match against.
    :param needed: Whether an issue with this title should exist.
    :return: A tuple of ``(issue_needed, issue_to_update, issues_to_close)``.

    If ``needed`` is ``True``, the most recent matching issue is kept as
    ``issue_to_update`` and all older matching issues are collected in
    ``issues_to_close``. If ``needed`` is ``False``, all matching issues are
    placed in ``issues_to_close``.
    """
    issue_to_update: int | None = None
    issues_to_close: set[int] = set()

    for issue in sorted(issues, key=itemgetter("createdAt"), reverse=True):
        logging.debug(f"Processing {issue!r} ...")
        if issue["title"] != title:
            logging.debug(f"{issue!r} does not match title, skip.")
            continue
        if needed and issue_to_update is None:
            logging.debug(f"{issue!r} is the most recent matching issue.")
            issue_to_update = issue["number"]
        else:
            logging.debug(f"{issue!r} is a duplicate to close.")
            issues_to_close.add(issue["number"])

    return needed, issue_to_update, issues_to_close


def manage_issue_lifecycle(
    has_broken_links: bool,
    body_file: Path,
    repo_name: str,
    title: str,
    no_broken_links_comment: str = "No more broken links.",
) -> None:
    """Manage the generic issue lifecycle for broken link checkers.

    This function handles:
    1. Listing open issues via ``gh issue list``.
    2. Triaging matching issues (keep newest if needed, close duplicates).
    3. Closing duplicate issues via ``gh issue close``.
    4. Creating or updating the main issue via ``gh issue create`` or
       ``gh issue edit``.

    :param has_broken_links: Whether broken links were found.
    :param body_file: Path to the file containing the issue body.
    :param repo_name: Repository name (for label selection).
    :param title: Issue title to match and create.
    :param no_broken_links_comment: Comment to add when closing issues because
        no broken links remain.
    """
    # List open issues.
    issues = list_open_issues()
    logging.info(f"Found {len(issues)} open issues by {ISSUE_AUTHOR}")

    # Triage issues.
    _, issue_to_update, issues_to_close = triage_issues(
        issues, title, has_broken_links
    )

    # Close duplicate/obsolete issues.
    for issue_number in issues_to_close:
        if issue_to_update:
            comment = f"Superseded by #{issue_to_update}."
        else:
            comment = no_broken_links_comment
        close_issue(issue_number, comment)

    # Create or update issue if needed.
    if has_broken_links:
        label = get_label(repo_name)
        if issue_to_update:
            update_issue(issue_to_update, body_file)
        else:
            create_issue(body_file, [label], title=title)


def manage_broken_links_issue(
    lychee_exit_code: int,
    body_file: Path,
    repo_name: str,
) -> None:
    """Manage the full broken links issue lifecycle.

    Validates the lychee exit code, then delegates to
    :func:`manage_issue_lifecycle` for issue management.

    :param lychee_exit_code: Exit code from lychee (0=no broken links, 2=broken links).
    :param body_file: Path to the issue body file (lychee output).
    :param repo_name: Repository name (for label selection).
    :raises ValueError: If lychee exit code is not 0 or 2.
    """
    # Validate lychee exit code.
    if lychee_exit_code not in (0, 2):
        msg = f"Unexpected lychee exit code: {lychee_exit_code}"
        raise ValueError(msg)

    # Determine if an issue is needed (exit code 2 means broken links found).
    has_broken_links = lychee_exit_code == 2
    logging.info(
        f"Lychee exit code {lychee_exit_code}: "
        f"{'broken links found' if has_broken_links else 'no broken links'}"
    )

    manage_issue_lifecycle(
        has_broken_links=has_broken_links,
        body_file=body_file,
        repo_name=repo_name,
        title=ISSUE_TITLE,
    )
