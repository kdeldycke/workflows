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

"""Manage the Sphinx linkcheck issue lifecycle.

Parses the ``output.json`` file produced by Sphinx's ``linkcheck`` builder to
detect broken documentation links. Generates a Markdown report and manages the
corresponding GitHub issue via :func:`~gha_utils.broken_links.manage_issue_lifecycle`.

This catches broken auto-generated links (intersphinx, autodoc, type annotations)
that Lychee cannot see because they only exist in the rendered HTML output.
"""

from __future__ import annotations

import json
import logging
import tempfile
from dataclasses import dataclass
from itertools import groupby
from operator import attrgetter
from pathlib import Path

from .broken_links import manage_issue_lifecycle

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Iterable


# Distinct from Lychee's "Broken links" to avoid conflicts.
SPHINX_ISSUE_TITLE = "Broken documentation links"
"""Issue title used for Sphinx linkcheck results.

Both Lychee and Sphinx checkers manage their own issues independently, so the
titles must be different.
"""


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


def generate_markdown_report(broken: list[LinkcheckResult]) -> str:
    """Generate a Markdown report of broken links grouped by source file.

    :param broken: List of broken linkcheck results.
    :return: Markdown-formatted report string.
    """
    if not broken:
        return ""

    lines: list[str] = []
    lines.append("# Broken documentation links\n")
    lines.append("The following broken links were found by Sphinx linkcheck:\n")

    # Group by filename, sorted alphabetically.
    sorted_results = sorted(broken, key=attrgetter("filename", "lineno"))
    for filename, group_iter in groupby(sorted_results, key=attrgetter("filename")):
        group_list = list(group_iter)
        lines.append(f"## `{filename}`\n")
        lines.append("| Line | URI | Status | Info |")
        lines.append("| ---: | --- | ------ | ---- |")
        for result in group_list:
            # Escape pipe characters in info to avoid breaking the table.
            escaped_info = result.info.replace("|", "\\|")
            lines.append(
                f"| {result.lineno} | {result.uri} | {result.status} | {escaped_info} |"
            )
        lines.append("")

    return "\n".join(lines)


def manage_sphinx_linkcheck_issue(output_json: Path, repo_name: str) -> None:
    """Orchestrate Sphinx linkcheck issue management.

    Parses the ``output.json`` file, generates a Markdown report, and delegates
    to :func:`~gha_utils.broken_links.manage_issue_lifecycle` for issue
    creation, update, or closure.

    :param output_json: Path to the Sphinx linkcheck ``output.json`` file.
    :param repo_name: Repository name (for label selection).
    """
    results = parse_output_json(output_json)
    broken = filter_broken(results)
    has_broken_links = len(broken) > 0

    if has_broken_links:
        report = generate_markdown_report(broken)
    else:
        report = ""
        logging.info("No broken documentation links found.")

    # Write the report to a temporary file for the issue body.
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".md",
        delete=False,
        encoding="UTF-8",
    ) as tmp:
        tmp.write(report)
        body_file = Path(tmp.name)

    manage_issue_lifecycle(
        has_broken_links=has_broken_links,
        body_file=body_file,
        repo_name=repo_name,
        title=SPHINX_ISSUE_TITLE,
        no_broken_links_comment="No more broken documentation links.",
    )
