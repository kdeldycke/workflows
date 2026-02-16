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
creating or updating the main issue. Both Lychee and Sphinx linkcheck results
are combined into a single "Broken links" issue.

Sphinx linkcheck parsing detects broken auto-generated links (intersphinx,
autodoc, type annotations) that Lychee cannot see because they only exist in
the rendered HTML output.

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
import tempfile
from dataclasses import dataclass
from itertools import groupby
from operator import attrgetter, itemgetter
from pathlib import Path
from subprocess import run

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any


# Issue title and author are hardcoded for this specific use case.
ISSUE_TITLE = "Broken links"
ISSUE_AUTHOR = "github-actions[bot]"


# ---------------------------------------------------------------------------
# Sphinx linkcheck parsing, filtering, and report generation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LinkcheckResult:
    """A single result entry from Sphinx linkcheck ``output.json``.

    Each line in the JSON-lines file corresponds to one checked URI.
    """

    filename: str
    lineno: int
    status: str
    code: int
    uri: str
    info: str


def parse_output_json(output_json: Path) -> list[LinkcheckResult]:
    """Parse the Sphinx linkcheck ``output.json`` file.

    The file uses JSON-lines format: one JSON object per line.
    Blank lines are skipped.

    :param output_json: Path to the ``output.json`` file.
    :return: List of parsed linkcheck results.
    """
    results: list[LinkcheckResult] = []
    content = output_json.read_text(encoding="UTF-8")
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        entry = json.loads(stripped)
        results.append(
            LinkcheckResult(
                filename=entry["filename"],
                lineno=entry["lineno"],
                status=entry["status"],
                code=entry["code"],
                uri=entry["uri"],
                info=entry.get("info", ""),
            )
        )
    logging.info(f"Parsed {len(results)} linkcheck entries from {output_json}")
    return results


def filter_broken(results: Iterable[LinkcheckResult]) -> list[LinkcheckResult]:
    """Filter results to only broken and timed-out links.

    :param results: Iterable of linkcheck results.
    :return: List of results with ``status`` of ``"broken"`` or ``"timeout"``.
    """
    broken = [r for r in results if r.status in ("broken", "timeout")]
    logging.info(f"Found {len(broken)} broken/timed-out links")
    return broken


def generate_markdown_report(
    broken: list[LinkcheckResult],
    source_url: str | None = None,
) -> str:
    """Generate a Markdown report of broken links grouped by source file.

    The report starts with H2 file headings, suitable for embedding as a
    section in the combined broken links issue body.

    :param broken: List of broken linkcheck results.
    :param source_url: Base URL for linking filenames and line numbers. When
        provided, file headers become clickable links and line numbers deep-link
        to the specific line.
    :return: Markdown-formatted report string.
    """
    if not broken:
        return ""

    lines: list[str] = []

    # Group by filename, sorted alphabetically.
    sorted_results = sorted(broken, key=attrgetter("filename", "lineno"))
    for filename, group_iter in groupby(sorted_results, key=attrgetter("filename")):
        group_list = list(group_iter)

        if source_url:
            file_url = f"{source_url}/{filename}"
            lines.append(f"## [`{filename}`]({file_url})\n")
        else:
            lines.append(f"## `{filename}`\n")

        lines.append("| Line | URI | Info |")
        lines.append("| ---: | --- | ---- |")
        for result in group_list:
            # Escape pipe characters in info to avoid breaking the table.
            escaped_info = result.info.replace("|", "\\|")
            if source_url:
                file_url = f"{source_url}/{result.filename}"
                line_cell = f"[{result.lineno}]({file_url}?plain=1#L{result.lineno})"
            else:
                line_cell = str(result.lineno)
            lines.append(f"| {line_cell} | {result.uri} | {escaped_info} |")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# GitHub issue lifecycle management via gh CLI
# ---------------------------------------------------------------------------


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


def create_issue(body_file: Path, labels: list[str], title: str = ISSUE_TITLE) -> int:
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
    _, issue_to_update, issues_to_close = triage_issues(issues, title, has_broken_links)

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


# ---------------------------------------------------------------------------
# Combined broken links issue (Lychee + Sphinx linkcheck)
# ---------------------------------------------------------------------------


def manage_combined_broken_links_issue(
    repo_name: str,
    lychee_exit_code: int | None = None,
    lychee_body_file: Path | None = None,
    sphinx_output_json: Path | None = None,
    sphinx_source_url: str | None = None,
) -> None:
    """Manage the combined broken links issue lifecycle.

    Combines results from Lychee and Sphinx linkcheck into a single "Broken
    links" issue. Each tool's results appear under its own heading. Tools that
    were not run are omitted from the report. Tools that found no broken links
    show a "No broken links found." message.

    :param repo_name: Repository name (for label selection).
    :param lychee_exit_code: Exit code from lychee (0=no broken links,
        2=broken links found). ``None`` if lychee was not run.
    :param lychee_body_file: Path to the lychee output file. ``None`` if
        lychee was not run.
    :param sphinx_output_json: Path to Sphinx linkcheck ``output.json``.
        ``None`` if Sphinx linkcheck was not run.
    :param sphinx_source_url: Base URL for linking filenames and line numbers
        in the Sphinx report.
    :raises ValueError: If lychee exit code is not 0, 2, or ``None``.
    """
    # Validate lychee exit code.
    lychee_has_broken = False
    if lychee_exit_code is not None:
        if lychee_exit_code not in (0, 2):
            msg = f"Unexpected lychee exit code: {lychee_exit_code}"
            raise ValueError(msg)
        lychee_has_broken = lychee_exit_code == 2
        logging.info(
            f"Lychee exit code {lychee_exit_code}: "
            f"{'broken links found' if lychee_has_broken else 'no broken links'}"
        )

    # Parse Sphinx linkcheck results.
    sphinx_has_broken = False
    sphinx_report = ""
    if sphinx_output_json is not None:
        results = parse_output_json(sphinx_output_json)
        broken = filter_broken(results)
        sphinx_has_broken = len(broken) > 0
        if sphinx_has_broken:
            sphinx_report = generate_markdown_report(
                broken, source_url=sphinx_source_url,
            )
        else:
            logging.info("No broken documentation links found.")

    # Build combined issue body.
    sections: list[str] = []

    if lychee_exit_code is not None:
        sections.append("## Lychee\n")
        if lychee_has_broken and lychee_body_file is not None:
            lychee_content = lychee_body_file.read_text(encoding="UTF-8").strip()
            sections.append(lychee_content)
        else:
            sections.append("No broken links found.")

    if sphinx_output_json is not None:
        sections.append("## Sphinx linkcheck\n")
        if sphinx_has_broken:
            sections.append(sphinx_report.strip())
        else:
            sections.append("No broken links found.")

    has_broken_links = lychee_has_broken or sphinx_has_broken
    body = "# Broken links\n\n" + "\n\n".join(sections) + "\n"

    # Write combined body to a temporary file.
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".md",
        delete=False,
        encoding="UTF-8",
    ) as tmp:
        tmp.write(body)
        body_file = Path(tmp.name)

    manage_issue_lifecycle(
        has_broken_links=has_broken_links,
        body_file=body_file,
        repo_name=repo_name,
        title=ISSUE_TITLE,
    )
