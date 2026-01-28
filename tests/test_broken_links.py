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

"""Tests for broken links issue management."""

from __future__ import annotations

import pytest

from gha_utils.broken_links import get_label, triage_issues


TITLE = "Broken links"


@pytest.mark.parametrize(
    ("needed", "expected"),
    [
        (True, (True, None, set())),
        (False, (False, None, set())),
    ],
)
def test_no_matching_issues(needed, expected):
    """No issues match the title."""
    issues = [
        {"number": 1, "title": "Other issue", "createdAt": "2025-01-01T00:00:00Z"},
    ]
    assert triage_issues(issues, TITLE, needed) == expected


@pytest.mark.parametrize(
    ("needed", "expected"),
    [
        (True, (True, None, set())),
        (False, (False, None, set())),
    ],
)
def test_empty_issues(needed, expected):
    """Empty issue list returns no matches."""
    assert triage_issues([], TITLE, needed) == expected


def test_one_match_needed():
    """Single matching issue is kept when needed."""
    issues = [
        {"number": 42, "title": TITLE, "createdAt": "2025-01-01T00:00:00Z"},
    ]
    assert triage_issues(issues, TITLE, needed=True) == (True, 42, set())


def test_one_match_not_needed():
    """Single matching issue is closed when not needed."""
    issues = [
        {"number": 42, "title": TITLE, "createdAt": "2025-01-01T00:00:00Z"},
    ]
    assert triage_issues(issues, TITLE, needed=False) == (False, None, {42})


def test_multiple_matches_needed():
    """Most recent issue is kept, older ones are closed."""
    issues = [
        {"number": 10, "title": TITLE, "createdAt": "2024-06-01T00:00:00Z"},
        {"number": 42, "title": TITLE, "createdAt": "2025-01-01T00:00:00Z"},
        {"number": 5, "title": TITLE, "createdAt": "2024-01-01T00:00:00Z"},
    ]
    assert triage_issues(issues, TITLE, needed=True) == (True, 42, {10, 5})


def test_multiple_matches_not_needed():
    """All matching issues are closed when not needed."""
    issues = [
        {"number": 10, "title": TITLE, "createdAt": "2024-06-01T00:00:00Z"},
        {"number": 42, "title": TITLE, "createdAt": "2025-01-01T00:00:00Z"},
    ]
    assert triage_issues(issues, TITLE, needed=False) == (False, None, {10, 42})


def test_mixed_titles():
    """Non-matching issues are ignored."""
    issues = [
        {"number": 1, "title": "Other issue", "createdAt": "2025-06-01T00:00:00Z"},
        {"number": 42, "title": TITLE, "createdAt": "2025-01-01T00:00:00Z"},
        {"number": 10, "title": TITLE, "createdAt": "2024-06-01T00:00:00Z"},
        {"number": 2, "title": "Another issue", "createdAt": "2025-03-01T00:00:00Z"},
    ]
    assert triage_issues(issues, TITLE, needed=True) == (True, 42, {10})


class TestGetLabel:
    """Tests for get_label function."""

    def test_awesome_repo(self):
        """Awesome repos get the fix link label."""
        assert get_label("awesome-falsehood") == "🩹 fix link"

    def test_awesome_repo_prefix_only(self):
        """Only repos starting with awesome- get the fix link label."""
        assert get_label("awesome-") == "🩹 fix link"

    def test_regular_repo(self):
        """Regular repos get the documentation label."""
        assert get_label("workflows") == "📚 documentation"

    def test_repo_containing_awesome(self):
        """Repos containing but not starting with awesome get documentation label."""
        assert get_label("my-awesome-repo") == "📚 documentation"
