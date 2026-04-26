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

"""Tests for the GitHub Advisory Database integration."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from repomatic.github.advisories import fetch_dependabot_alerts
from repomatic.uv import (
    AdvisorySource,
    VulnerablePackage,
    collect_vulnerable_packages,
    format_vulnerability_table,
)

ALERTS_FIXTURE = [
    {
        "number": 6,
        "state": "open",
        "dependency": {
            "package": {"ecosystem": "pip", "name": "raspberry"},
            "manifest_path": "uv.lock",
            "scope": "runtime",
        },
        "security_advisory": {
            "ghsa_id": "GHSA-fruit-1111-aaaa",
            "summary": "Raspberry juice leak under concurrent picking",
            "html_url": "https://github.com/advisories/GHSA-fruit-1111-aaaa",
        },
        "security_vulnerability": {
            "package": {"ecosystem": "pip", "name": "raspberry"},
            "first_patched_version": {"identifier": "3.1.47"},
            "vulnerable_version_range": "< 3.1.47",
            "severity": "high",
        },
    },
    {
        "number": 7,
        "state": "open",
        "dependency": {
            "package": {"ecosystem": "pip", "name": "raspberry"},
            "manifest_path": "uv.lock",
            "scope": "runtime",
        },
        "security_advisory": {
            "ghsa_id": "GHSA-fruit-2222-bbbb",
            "summary": "Raspberry seed validation bypass",
            "html_url": "https://github.com/advisories/GHSA-fruit-2222-bbbb",
        },
        "security_vulnerability": {
            "package": {"ecosystem": "pip", "name": "raspberry"},
            "first_patched_version": {"identifier": "3.1.47"},
            "vulnerable_version_range": ">= 3.1.30, < 3.1.47",
            "severity": "high",
        },
    },
]


def test_fetch_dependabot_alerts_parses_each_entry():
    """Each alert maps to one VulnerablePackage tagged with GHSA source."""
    with patch(
        "repomatic.github.advisories.run_gh_command",
        return_value=json.dumps(ALERTS_FIXTURE),
    ):
        result = fetch_dependabot_alerts("orchard/raspberry")

    assert len(result) == 2
    for v in result:
        assert v.name == "raspberry"
        assert v.fixed_version == "3.1.47"
        assert v.sources == {AdvisorySource.GITHUB_ADVISORIES}
        assert v.advisory_url.startswith("https://github.com/advisories/GHSA-")


def test_fetch_dependabot_alerts_skips_entries_without_fix():
    """Alerts lacking first_patched_version are filtered out."""
    no_fix = [
        {
            "security_advisory": {"ghsa_id": "GHSA-cookbook-7777-zzzz", "summary": "x"},
            "security_vulnerability": {
                "package": {"name": "muffin", "ecosystem": "pip"},
                "first_patched_version": None,
            },
            "dependency": {"manifest_path": "uv.lock"},
        },
    ]
    with patch(
        "repomatic.github.advisories.run_gh_command",
        return_value=json.dumps(no_fix),
    ):
        assert fetch_dependabot_alerts("orchard/raspberry") == []


def test_fetch_dependabot_alerts_returns_empty_on_api_error():
    """Network/auth failures must not break the autofix workflow."""
    with patch(
        "repomatic.github.advisories.run_gh_command",
        side_effect=RuntimeError("HTTP 403"),
    ):
        assert fetch_dependabot_alerts("orchard/raspberry") == []


def test_fetch_dependabot_alerts_handles_invalid_json():
    """Garbage responses degrade to an empty list."""
    with patch(
        "repomatic.github.advisories.run_gh_command",
        return_value="<<not json>>",
    ):
        assert fetch_dependabot_alerts("orchard/raspberry") == []


@pytest.fixture
def lock_with_raspberry(tmp_path):
    """Create a uv.lock containing a single 'raspberry' package."""
    lock = tmp_path / "uv.lock"
    lock.write_text(
        '[[package]]\nname = "raspberry"\nversion = "3.1.46"\n',
        encoding="UTF-8",
    )
    return lock


def test_collect_unions_uv_audit_and_ghsa(lock_with_raspberry):
    """Same package, different advisories: both kept, sources distinct."""
    audit_only = VulnerablePackage(
        name="raspberry",
        current_version="3.1.46",
        advisory_id="PYSEC-3333-cccc",
        advisory_title="Raspberry stem rot",
        fixed_version="3.1.47",
        advisory_url="https://example.com/PYSEC-3333-cccc",
        sources={AdvisorySource.UV_AUDIT},
    )
    with (
        patch("repomatic.uv._run_uv_audit", return_value=[audit_only]),
        patch(
            "repomatic.github.advisories.run_gh_command",
            return_value=json.dumps(ALERTS_FIXTURE),
        ),
    ):
        merged = collect_vulnerable_packages(
            lock_with_raspberry, repo="orchard/raspberry"
        )

    advisory_ids = sorted(v.advisory_id for v in merged)
    assert advisory_ids == [
        "GHSA-fruit-1111-aaaa",
        "GHSA-fruit-2222-bbbb",
        "PYSEC-3333-cccc",
    ]
    # GHSA-only entries must have current_version backfilled from the lock.
    for v in merged:
        assert v.current_version == "3.1.46"


def test_collect_dedupes_when_advisory_id_matches(lock_with_raspberry):
    """Same package + same advisory ID across sources: merged into one entry."""
    same_advisory_audit = VulnerablePackage(
        name="raspberry",
        current_version="3.1.46",
        advisory_id="GHSA-fruit-1111-aaaa",
        advisory_title="",  # missing in audit, filled from GHSA
        fixed_version="3.1.47",
        advisory_url="",
        sources={AdvisorySource.UV_AUDIT},
    )
    with (
        patch("repomatic.uv._run_uv_audit", return_value=[same_advisory_audit]),
        patch(
            "repomatic.github.advisories.run_gh_command",
            return_value=json.dumps(ALERTS_FIXTURE[:1]),
        ),
    ):
        merged = collect_vulnerable_packages(
            lock_with_raspberry, repo="orchard/raspberry"
        )

    assert len(merged) == 1
    only = merged[0]
    assert only.sources == {
        AdvisorySource.UV_AUDIT,
        AdvisorySource.GITHUB_ADVISORIES,
    }
    # Missing audit fields backfilled from the GHSA entry.
    assert only.advisory_title == "Raspberry juice leak under concurrent picking"
    assert only.advisory_url.endswith("GHSA-fruit-1111-aaaa")


def test_collect_skips_ghsa_when_repo_missing(lock_with_raspberry):
    """No repo argument means the GHSA source is skipped entirely."""
    with (
        patch("repomatic.uv._run_uv_audit", return_value=[]),
        patch("repomatic.github.advisories.run_gh_command") as gh,
    ):
        result = collect_vulnerable_packages(lock_with_raspberry, repo=None)

    assert result == []
    gh.assert_not_called()


def test_collect_respects_sources_filter(lock_with_raspberry):
    """Only the explicitly requested sources are queried."""
    with (
        patch("repomatic.uv._run_uv_audit") as audit,
        patch(
            "repomatic.github.advisories.run_gh_command",
            return_value=json.dumps(ALERTS_FIXTURE),
        ),
    ):
        result = collect_vulnerable_packages(
            lock_with_raspberry,
            repo="orchard/raspberry",
            sources=[AdvisorySource.GITHUB_ADVISORIES],
        )

    audit.assert_not_called()
    assert all(
        v.sources == {AdvisorySource.GITHUB_ADVISORIES} for v in result
    )


def test_collect_backfills_current_version_across_case_difference(tmp_path):
    """GHSA reports `GitPython`, lock stores `gitpython` — backfill must match."""
    lock = tmp_path / "uv.lock"
    lock.write_text(
        '[[package]]\nname = "gitpython"\nversion = "3.1.46"\n',
        encoding="UTF-8",
    )
    alert = [
        {
            "security_advisory": {"ghsa_id": "GHSA-orchard-aaaa-bbbb", "summary": "x"},
            "security_vulnerability": {
                "package": {"name": "GitPython", "ecosystem": "pip"},
                "first_patched_version": {"identifier": "3.1.47"},
            },
            "dependency": {"manifest_path": "uv.lock"},
        },
    ]
    with (
        patch("repomatic.uv._run_uv_audit", return_value=[]),
        patch(
            "repomatic.github.advisories.run_gh_command",
            return_value=json.dumps(alert),
        ),
    ):
        result = collect_vulnerable_packages(lock, repo="orchard/gitpython")

    assert len(result) == 1
    assert result[0].current_version == "3.1.46"


def test_format_vulnerability_table_includes_sources_column():
    """The rendered table credits each advisory's source(s)."""
    vulns = [
        VulnerablePackage(
            name="apricot",
            current_version="1.0",
            advisory_id="GHSA-orchard-9999-yyyy",
            advisory_title="Apricot pit cracking",
            fixed_version="1.1",
            advisory_url="https://example.com/orchard",
            sources={AdvisorySource.UV_AUDIT, AdvisorySource.GITHUB_ADVISORIES},
        ),
    ]
    table = format_vulnerability_table(vulns)
    assert "Sources" in table
    assert "`uv-audit`" in table
    assert "`github-advisories`" in table


def test_format_vulnerability_table_links_each_source_to_its_url():
    """Each source name in the Sources column links to its own advisory page."""
    vulns = [
        VulnerablePackage(
            name="apricot",
            current_version="1.0",
            advisory_id="GHSA-orchard-9999-yyyy",
            advisory_title="Apricot pit cracking",
            fixed_version="1.1",
            advisory_url="https://github.com/advisories/GHSA-orchard-9999-yyyy",
            sources={AdvisorySource.UV_AUDIT, AdvisorySource.GITHUB_ADVISORIES},
            source_urls={
                AdvisorySource.UV_AUDIT: "https://osv.dev/vulnerability/PYSEC",
                AdvisorySource.GITHUB_ADVISORIES: (
                    "https://github.com/advisories/GHSA-orchard-9999-yyyy"
                ),
            },
        ),
    ]
    table = format_vulnerability_table(vulns)
    assert "[`uv-audit`](https://osv.dev/vulnerability/PYSEC)" in table
    assert (
        "[`github-advisories`]"
        "(https://github.com/advisories/GHSA-orchard-9999-yyyy)"
    ) in table


def test_collect_keeps_distinct_per_source_urls(lock_with_raspberry):
    """Merging same advisory from two sources retains both URLs."""
    audit = VulnerablePackage(
        name="raspberry",
        current_version="3.1.46",
        advisory_id="GHSA-fruit-1111-aaaa",
        advisory_title="",
        fixed_version="3.1.47",
        advisory_url="https://osv.dev/vulnerability/PYSEC-raspberry",
        sources={AdvisorySource.UV_AUDIT},
        source_urls={
            AdvisorySource.UV_AUDIT: "https://osv.dev/vulnerability/PYSEC-raspberry",
        },
    )
    with (
        patch("repomatic.uv._run_uv_audit", return_value=[audit]),
        patch(
            "repomatic.github.advisories.run_gh_command",
            return_value=json.dumps(ALERTS_FIXTURE[:1]),
        ),
    ):
        merged = collect_vulnerable_packages(
            lock_with_raspberry, repo="orchard/raspberry"
        )

    assert len(merged) == 1
    only = merged[0]
    assert only.source_urls[AdvisorySource.UV_AUDIT].startswith("https://osv.dev/")
    assert only.source_urls[AdvisorySource.GITHUB_ADVISORIES].startswith(
        "https://github.com/advisories/"
    )
