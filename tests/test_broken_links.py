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

"""Tests for issue lifecycle management (triage, broken links, setup guide) and
Sphinx linkcheck parsing and report generation.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from repomatic.broken_links import (
    LinkcheckResult,
    filter_broken,
    generate_markdown_report,
    get_label,
    parse_output_json,
)
from repomatic.cli import setup_guide
from repomatic.github.issue import triage_issues


TITLE = "Broken links"


# ---------------------------------------------------------------------------
# Issue triage tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("needed", "expected"),
    [
        (True, (True, None, None, set())),
        (False, (False, None, None, set())),
    ],
)
def test_no_matching_issues(needed, expected):
    """No issues match the title."""
    issues = [
        {
            "number": 1,
            "title": "Other issue",
            "createdAt": "2025-01-01T00:00:00Z",
            "state": "OPEN",
        },
    ]
    assert triage_issues(issues, TITLE, needed) == expected


@pytest.mark.parametrize(
    ("needed", "expected"),
    [
        (True, (True, None, None, set())),
        (False, (False, None, None, set())),
    ],
)
def test_empty_issues(needed, expected):
    """Empty issue list returns no matches."""
    assert triage_issues([], TITLE, needed) == expected


def test_one_match_needed():
    """Single matching open issue is kept when needed."""
    issues = [
        {
            "number": 42,
            "title": TITLE,
            "createdAt": "2025-01-01T00:00:00Z",
            "state": "OPEN",
        },
    ]
    assert triage_issues(issues, TITLE, needed=True) == (True, 42, "OPEN", set())


def test_one_match_not_needed():
    """Single matching open issue is closed when not needed."""
    issues = [
        {
            "number": 42,
            "title": TITLE,
            "createdAt": "2025-01-01T00:00:00Z",
            "state": "OPEN",
        },
    ]
    assert triage_issues(issues, TITLE, needed=False) == (False, None, None, {42})


def test_one_closed_match_needed():
    """Single matching closed issue is returned for reopening when needed."""
    issues = [
        {
            "number": 42,
            "title": TITLE,
            "createdAt": "2025-01-01T00:00:00Z",
            "state": "CLOSED",
        },
    ]
    assert triage_issues(issues, TITLE, needed=True) == (True, 42, "CLOSED", set())


def test_one_closed_match_not_needed():
    """Single matching closed issue is skipped when not needed."""
    issues = [
        {
            "number": 42,
            "title": TITLE,
            "createdAt": "2025-01-01T00:00:00Z",
            "state": "CLOSED",
        },
    ]
    assert triage_issues(issues, TITLE, needed=False) == (False, None, None, set())


def test_multiple_matches_needed():
    """Most recent issue is kept, older open ones are closed."""
    issues = [
        {
            "number": 10,
            "title": TITLE,
            "createdAt": "2024-06-01T00:00:00Z",
            "state": "OPEN",
        },
        {
            "number": 42,
            "title": TITLE,
            "createdAt": "2025-01-01T00:00:00Z",
            "state": "OPEN",
        },
        {
            "number": 5,
            "title": TITLE,
            "createdAt": "2024-01-01T00:00:00Z",
            "state": "OPEN",
        },
    ]
    assert triage_issues(issues, TITLE, needed=True) == (True, 42, "OPEN", {10, 5})


def test_multiple_matches_not_needed():
    """All open matching issues are closed when not needed."""
    issues = [
        {
            "number": 10,
            "title": TITLE,
            "createdAt": "2024-06-01T00:00:00Z",
            "state": "OPEN",
        },
        {
            "number": 42,
            "title": TITLE,
            "createdAt": "2025-01-01T00:00:00Z",
            "state": "OPEN",
        },
    ]
    assert triage_issues(issues, TITLE, needed=False) == (False, None, None, {10, 42})


def test_multiple_matches_closed_not_needed():
    """Already-closed issues are skipped when not needed."""
    issues = [
        {
            "number": 10,
            "title": TITLE,
            "createdAt": "2024-06-01T00:00:00Z",
            "state": "CLOSED",
        },
        {
            "number": 42,
            "title": TITLE,
            "createdAt": "2025-01-01T00:00:00Z",
            "state": "OPEN",
        },
    ]
    assert triage_issues(issues, TITLE, needed=False) == (False, None, None, {42})


def test_mixed_titles():
    """Non-matching issues are ignored."""
    issues = [
        {
            "number": 1,
            "title": "Other issue",
            "createdAt": "2025-06-01T00:00:00Z",
            "state": "OPEN",
        },
        {
            "number": 42,
            "title": TITLE,
            "createdAt": "2025-01-01T00:00:00Z",
            "state": "OPEN",
        },
        {
            "number": 10,
            "title": TITLE,
            "createdAt": "2024-06-01T00:00:00Z",
            "state": "OPEN",
        },
        {
            "number": 2,
            "title": "Another issue",
            "createdAt": "2025-03-01T00:00:00Z",
            "state": "OPEN",
        },
    ]
    assert triage_issues(issues, TITLE, needed=True) == (True, 42, "OPEN", {10})


def test_state_defaults_to_open():
    """Issues without a state field default to OPEN for backward compatibility."""
    issues = [
        {"number": 42, "title": TITLE, "createdAt": "2025-01-01T00:00:00Z"},
    ]
    assert triage_issues(issues, TITLE, needed=True) == (True, 42, "OPEN", set())


# ---------------------------------------------------------------------------
# Label selection tests
# ---------------------------------------------------------------------------


def test_awesome_repo():
    """Awesome repos get the fix link label."""
    assert get_label("awesome-falsehood") == "🩹 fix link"


def test_awesome_repo_prefix_only():
    """Only repos starting with awesome- get the fix link label."""
    assert get_label("awesome-") == "🩹 fix link"


def test_regular_repo():
    """Regular repos get the documentation label."""
    assert get_label("workflows") == "📚 documentation"


def test_repo_containing_awesome():
    """Repos containing but not starting with awesome get documentation label."""
    assert get_label("my-awesome-repo") == "📚 documentation"


# ---------------------------------------------------------------------------
# Sphinx linkcheck parsing tests
# ---------------------------------------------------------------------------


def test_empty_file(tmp_path):
    """Empty file returns no results."""
    output = tmp_path / "output.json"
    output.write_text("", encoding="UTF-8")
    assert parse_output_json(output) == []


def test_blank_lines_skipped(tmp_path):
    """Blank lines in the file are skipped."""
    entry = {
        "filename": "index.rst",
        "lineno": 1,
        "status": "working",
        "code": 200,
        "uri": "https://example.com",
        "info": "",
    }
    content = "\n" + json.dumps(entry) + "\n\n"
    output = tmp_path / "output.json"
    output.write_text(content, encoding="UTF-8")
    results = parse_output_json(output)
    assert len(results) == 1
    assert results[0].filename == "index.rst"


def test_single_entry(tmp_path):
    """Single entry is parsed correctly."""
    entry = {
        "filename": "api.rst",
        "lineno": 42,
        "status": "broken",
        "code": 404,
        "uri": "https://example.com/missing",
        "info": "404 Not Found",
    }
    output = tmp_path / "output.json"
    output.write_text(json.dumps(entry) + "\n", encoding="UTF-8")
    results = parse_output_json(output)
    assert len(results) == 1
    assert results[0] == LinkcheckResult(
        filename="api.rst",
        lineno=42,
        status="broken",
        code=404,
        uri="https://example.com/missing",
        info="404 Not Found",
    )


def test_multiple_entries(tmp_path):
    """Multiple entries are parsed correctly."""
    entries = [
        {
            "filename": "index.rst",
            "lineno": 1,
            "status": "working",
            "code": 200,
            "uri": "https://example.com",
            "info": "",
        },
        {
            "filename": "api.rst",
            "lineno": 10,
            "status": "broken",
            "code": 404,
            "uri": "https://example.com/gone",
            "info": "404 Not Found",
        },
    ]
    content = "\n".join(json.dumps(e) for e in entries) + "\n"
    output = tmp_path / "output.json"
    output.write_text(content, encoding="UTF-8")
    results = parse_output_json(output)
    assert len(results) == 2


def test_missing_info_field(tmp_path):
    """Missing info field defaults to empty string."""
    entry = {
        "filename": "index.rst",
        "lineno": 1,
        "status": "working",
        "code": 200,
        "uri": "https://example.com",
    }
    output = tmp_path / "output.json"
    output.write_text(json.dumps(entry) + "\n", encoding="UTF-8")
    results = parse_output_json(output)
    assert results[0].info == ""


# ---------------------------------------------------------------------------
# Sphinx linkcheck filtering tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "expected_count"),
    [
        ("broken", 1),
        ("timeout", 1),
        ("working", 0),
        ("redirected", 0),
        ("unchecked", 0),
    ],
)
def test_filter_by_status(status, expected_count):
    """Only broken and timeout statuses are kept."""
    results = [
        LinkcheckResult(
            filename="index.rst",
            lineno=1,
            status=status,
            code=0,
            uri="https://example.com",
            info="",
        ),
    ]
    assert len(filter_broken(results)) == expected_count


def test_mixed_statuses():
    """Only broken and timeout are kept from a mixed list."""
    results = [
        LinkcheckResult("a.rst", 1, "working", 200, "https://a.com", ""),
        LinkcheckResult("b.rst", 2, "broken", 404, "https://b.com", "Not Found"),
        LinkcheckResult("c.rst", 3, "redirected", 301, "https://c.com", ""),
        LinkcheckResult("d.rst", 4, "timeout", 0, "https://d.com", "Timed out"),
        LinkcheckResult("e.rst", 5, "unchecked", 0, "https://e.com", ""),
    ]
    broken = filter_broken(results)
    assert len(broken) == 2
    assert broken[0].uri == "https://b.com"
    assert broken[1].uri == "https://d.com"


def test_filter_empty_input():
    """Empty input returns empty list."""
    assert filter_broken([]) == []


# ---------------------------------------------------------------------------
# Sphinx linkcheck report generation tests
# ---------------------------------------------------------------------------


def test_report_empty_list():
    """Empty list returns empty string."""
    assert generate_markdown_report([]) == ""


def test_report_single_broken_link():
    """Single broken link generates a valid report."""
    broken = [
        LinkcheckResult(
            filename="index.rst",
            lineno=10,
            status="broken",
            code=404,
            uri="https://example.com/missing",
            info="404 Not Found",
        ),
    ]
    report = generate_markdown_report(broken)
    # Report is a section (no H1 heading), ready for embedding.
    assert "# Broken documentation links" not in report
    assert "## `index.rst`" in report
    assert "| Line " in report
    assert "| URI " in report
    assert "| Info " in report
    assert "10" in report
    assert "https://example.com/missing" in report
    assert "404 Not Found" in report
    # Status column should not be present.
    assert "Status" not in report


def test_report_groups_by_file_alphabetically():
    """Results are grouped by filename in alphabetical order."""
    broken = [
        LinkcheckResult("z_file.rst", 1, "broken", 404, "https://z.com", ""),
        LinkcheckResult("a_file.rst", 5, "broken", 404, "https://a.com", ""),
        LinkcheckResult("a_file.rst", 2, "broken", 404, "https://a2.com", ""),
    ]
    report = generate_markdown_report(broken)
    a_pos = report.index("## `a_file.rst`")
    z_pos = report.index("## `z_file.rst`")
    assert a_pos < z_pos


def test_report_escapes_pipe_chars_in_info():
    """Pipe characters in info are escaped to avoid breaking tables."""
    broken = [
        LinkcheckResult(
            filename="index.rst",
            lineno=1,
            status="broken",
            code=0,
            uri="https://example.com",
            info="Error | Details",
        ),
    ]
    report = generate_markdown_report(broken)
    assert "Error \\| Details" in report


def test_report_source_url_links_filenames_and_lines():
    """When source_url is provided, filenames and line numbers are linked."""
    broken = [
        LinkcheckResult(
            filename="architectures.md",
            lineno=4,
            status="broken",
            code=404,
            uri="https://example.com/missing",
            info="404 Not Found",
        ),
    ]
    source_url = "https://github.com/owner/repo/blob/abc123/docs"
    report = generate_markdown_report(broken, source_url=source_url)

    # File header should be a link.
    assert (
        "## [`architectures.md`]"
        "(https://github.com/owner/repo/blob/abc123/docs/architectures.md)"
    ) in report

    # Line number should be a deep link.
    assert (
        "[4](https://github.com/owner/repo/blob/abc123/docs/architectures.md?plain=1#L4)"
    ) in report


def test_report_no_source_url_plain_text():
    """Without source_url, filenames and line numbers are plain text."""
    broken = [
        LinkcheckResult(
            filename="architectures.md",
            lineno=4,
            status="broken",
            code=404,
            uri="https://example.com/missing",
            info="404 Not Found",
        ),
    ]
    report = generate_markdown_report(broken)

    # File header should be plain text.
    assert "## `architectures.md`" in report
    assert "## [`architectures.md`](" not in report

    # Line number should be plain text, not a link.
    assert " 4 " in report
    assert "[4](" not in report


# ---------------------------------------------------------------------------
# Setup guide CLI tests
# ---------------------------------------------------------------------------


@patch("repomatic.github.token.validate_gh_token_env")
@patch("repomatic.github.issue.manage_issue_lifecycle")
def test_setup_guide_missing_pat_opens_issue(mock_lifecycle, _mock_token):
    """When PAT is missing, manage_issue_lifecycle is called with has_issues=True."""
    runner = CliRunner()
    result = runner.invoke(setup_guide, [])
    assert result.exit_code == 0
    mock_lifecycle.assert_called_once()
    kwargs = mock_lifecycle.call_args[1]
    assert kwargs["has_issues"] is True
    assert kwargs["labels"] == ["🤖 ci"]
    assert "WORKFLOW_UPDATE_GITHUB_PAT" in kwargs["title"]


@patch("repomatic.github.token.validate_gh_token_env")
@patch("repomatic.github.issue.manage_issue_lifecycle")
def test_setup_guide_configured_pat_closes_issue(mock_lifecycle, _mock_token):
    """When PAT is configured, manage_issue_lifecycle is called with has_issues=False."""
    runner = CliRunner()
    result = runner.invoke(setup_guide, ["--has-pat"])
    assert result.exit_code == 0
    mock_lifecycle.assert_called_once()
    kwargs = mock_lifecycle.call_args[1]
    assert kwargs["has_issues"] is False


@patch("repomatic.github.token.validate_gh_token_env")
@patch("repomatic.github.issue.manage_issue_lifecycle")
def test_setup_guide_body_contains_template(mock_lifecycle, _mock_token):
    """The body file passed to manage_issue_lifecycle contains the template."""
    runner = CliRunner()
    runner.invoke(setup_guide, [])
    body_file = mock_lifecycle.call_args[1]["body_file"]
    content = body_file.read_text(encoding="UTF-8")
    assert "WORKFLOW_UPDATE_GITHUB_PAT" in content
    assert "Fine-grained tokens" in content
