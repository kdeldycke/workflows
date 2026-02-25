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

"""Changelog parsing, updating, and release lifecycle management.

This module is the single source of truth for all changelog management
decisions and operations. It handles two phases of the release cycle:

**Post-release (unfreeze)** — :meth:`Changelog.update`:

1. Derive a new entry template from the latest release entry.
2. Replace the release date with ``(unreleased)``.
3. Retarget the comparison URL to ``...main``.
4. Replace the entry body with a ``[!IMPORTANT]`` development warning.
5. Prepend the new entry to the changelog.

**Release preparation (freeze)** — :meth:`Changelog.freeze`:

1. Replace ``(unreleased)`` with today's date (``YYYY-MM-DD``).
2. Freeze the comparison URL from ``...main`` to ``...vX.Y.Z``.
3. Remove the ``[!IMPORTANT]`` development warning.

Both operations are idempotent: re-running them produces the same result.
This is critical for CI workflows that may be retried.

.. note::
    This is a custom implementation. After evaluating all major
    alternatives — `towncrier <https://github.com/twisted/towncrier>`_,
    `commitizen <https://github.com/commitizen-tools/commitizen>`_,
    `python-semantic-release <https://github.com/python-semantic-release/python-semantic-release>`_,
    `generate-changelog <https://github.com/lob/generate-changelog>`_,
    `release-please <https://github.com/googleapis/release-please>`_,
    `scriv <https://github.com/nedbat/scriv>`_, and
    `git-changelog <https://github.com/pawamoy/git-changelog>`_
    (see `issue #94
    <https://github.com/kdeldycke/repomatic/issues/94>`_) — none
    were found to cover even half of the requirements.

Why not use an off-the-shelf tool?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Existing tools fall into two camps, neither of which fits:

**Commit-driven** tools (`python-semantic-release
<https://github.com/python-semantic-release/python-semantic-release>`_,
`commitizen <https://github.com/commitizen-tools/commitizen>`_,
`generate-changelog <https://github.com/lob/generate-changelog>`_,
`release-please <https://github.com/googleapis/release-please>`_)
auto-generate changelogs from Git history. This conflicts with the
project's philosophy of hand-curated changelogs: entries are written
for *users*, consolidated by hand, and summarize only changes worth
knowing about. Auto-generated logs from developer commits are too
noisy and don't account for back-and-forth during development.

**Fragment-driven** tools (`towncrier
<https://github.com/twisted/towncrier>`_, `scriv
<https://github.com/nedbat/scriv>`_) avoid merge conflicts by using
per-change files, but handle none of the release orchestration:
comparison URL management, GFM warning lifecycle, workflow action
reference freezing, or the two-commit freeze/unfreeze release cycle.
The multiplication of files across the repo adds complexity, and
there is no 1:1 mapping between fragments and changelog entries.

Specific gaps across all evaluated tools:

- **No comparison URL management.** None generate GitHub
  ``v1.0.0...v1.1.0`` diff links, or update them from ``...main``
  to ``...vX.Y.Z`` at release time.
- **No unreleased section lifecycle.** None manage the
  ``[!WARNING]`` GFM alert warning that the version is under
  active development, inserting it post-release and removing it at
  release time.
- **No workflow action reference freezing.** None handle the
  freeze/unfreeze cycle for ``@main`` ↔ ``@vX.Y.Z`` references
  in workflow files.
- **No two-commit release workflow.** None support the freeze
  commit (``[changelog] Release vX.Y.Z``) plus unfreeze commit
  (``[changelog] Post-release bump``) pattern that
  ``changelog.yaml`` uses.
- **No citation file integration.** None update ``citation.cff``
  release dates.
- **No version bump eligibility checks.** None prevent double
  version increments by comparing the current version against the
  latest Git tag with a commit-message fallback.

The custom implementation in this module is tightly integrated with the
release workflow. Adopting any external tool would require keeping most
of this code *and* adding a new dependency — more complexity, not less.

Related modules
^^^^^^^^^^^^^^^

- ``release_prep.py`` orchestrates the full release preparation
  across changelog, citation, and workflow files, delegating
  changelog operations to this module.
- ``metadata.py`` handles version bump eligibility checks and
  release commit identification.
- ``changelog.yaml`` workflow drives the two-commit release PR.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from textwrap import indent
from typing import NamedTuple
from urllib.error import URLError
from urllib.request import Request, urlopen

from packaging.version import Version

from .github.releases import GitHubRelease, get_github_releases

CHANGELOG_HEADER = "# Changelog\n"
"""Default changelog header for empty changelogs."""

CHANGELOG_BODY_PATTERN = re.compile(r"\n\n.*", re.MULTILINE | re.DOTALL)
"""Pattern matching the changelog entry body (everything after header)."""

SECTION_START = "##"
"""Markdown heading level for changelog version sections."""

UNRELEASED_LABEL = " (unreleased)"
"""Label with parentheses for unreleased versions in changelog headers."""

DATE_PATTERN = re.compile(r"\d{4}\-\d{2}\-\d{2}")
"""Pattern matching release dates in YYYY-MM-DD format."""

DATE_LABEL_PATTERN = re.compile(r" \(\d{4}\-\d{2}\-\d{2}\)")
"""Pattern matching release date with surrounding parentheses and space."""

VERSION_COMPARE_PATTERN = re.compile(r"v(\d+\.\d+\.\d+)\.\.\.v(\d+\.\d+\.\d+)")
"""Pattern matching GitHub comparison URLs like ``v1.0.0...v1.0.1``."""

RELEASED_VERSION_PATTERN = re.compile(
    rf"^{SECTION_START}\s*\[`?(\d+\.\d+\.\d+)`?\s+\((\d{{4}}-\d{{2}}-\d{{2}})\)\]",
    re.MULTILINE,
)
"""Pattern matching released version headings with dates.

Captures version and date from headings like
``## [`5.9.1` (2026-02-14)](...)``. Skips unreleased versions which
use ``(unreleased)`` instead of a date. Backticks around the version
are optional.
"""

VERSION_HEADING_PATTERN = re.compile(
    rf"^({SECTION_START}\s*\[`?\d+\.\d+\.\d+`?\s+\()[^)]+(\)\].*)$",
    re.MULTILINE,
)
"""Pattern matching a full version heading line for date replacement.

Captures the prefix up to ``(`` and the suffix from ``)`` onward,
allowing the date or ``unreleased`` label to be replaced. Backticks
around the version are optional.
"""

WARNING_PATTERN = re.compile(
    r"^> \[!(?:IMPORTANT|WARNING)\].+?\n\n", re.MULTILINE | re.DOTALL
)
"""Pattern matching the first ``[!WARNING]`` GFM alert block.

.. note::
    Also matches the legacy ``[!IMPORTANT]`` variant for migration.
"""

DEVELOPMENT_WARNING = (
    "\n\n"
    "> [!WARNING]\n"
    "> This version is **not released yet** and is under active development.\n\n"
)
"""GFM alert block warning that the version is under active development."""


AVAILABLE_VERB = "is available on"
"""Verb phrase for versions present on a platform."""

FIRST_AVAILABLE_VERB = "is the *first version* available on"
"""Verb phrase for the inaugural release on a platform."""

GITHUB_LABEL = "🐙 GitHub"
"""Display label for GitHub releases in admonitions."""

GITHUB_RELEASE_URL = "{repo_url}/releases/tag/v{version}"
"""GitHub release page URL for a specific version."""

NOT_AVAILABLE_VERB = "is **not available** on"
"""Verb phrase for versions missing from a platform."""

PYPI_API_URL = "https://pypi.org/pypi/{package}/json"
"""PyPI JSON API URL for fetching all release metadata for a package."""

PYPI_LABEL = "🐍 PyPI"
"""Display label for PyPI releases in admonitions."""

PYPI_PROJECT_URL = "https://pypi.org/project/{package}/{version}/"
"""PyPI project page URL for a specific version."""

AVAILABLE_ADMONITION = "> [!NOTE]\n> `{version}` {verb} {platforms}."
"""GFM admonition template for versions available on one or more platforms."""

UNAVAILABLE_ADMONITION = "> [!WARNING]\n> `{version}` {verb} {platforms}."
"""GFM admonition template for versions missing from one or more platforms."""

YANKED_ADMONITION = (
    "> [!CAUTION]\n"
    "> This release has been"
    " [yanked from PyPI](https://docs.pypi.org/project-management/yanking/)."
)
"""GFM admonition for a release that has been yanked from PyPI."""

YANKED_DEDUP_MARKER = "yanked from PyPI"
"""Dedup marker for the yanked admonition to prevent duplicate insertion."""


class Changelog:
    """Helpers to manipulate changelog files written in Markdown."""

    def __init__(
        self,
        initial_changelog: str | None = None,
        current_version: str | None = None,
    ) -> None:
        if not initial_changelog:
            self.content = CHANGELOG_HEADER
        else:
            self.content = initial_changelog
        self.current_version = current_version
        logging.debug(f"Initial content set to:\n{self.content}")

    def update(self) -> str:
        r"""Adds a new empty entry at the top of the changelog.

        Will return the same content as the current changelog if it has already
        been updated.

        This is designed to be used just after a new release has been tagged.
        And before a post-release version increment is applied with a call to:

        ```shell-session
        $ bump-my-version bump --verbose patch
        Starting BumpVersion 0.5.1.dev6
        Reading config file pyproject.toml:
        Specified version (2.17.5) does not match last tagged version (2.17.4)
        Parsing version '2.17.5' using '(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)'
        Parsed the following values: major=2, minor=17, patch=5
        Attempting to increment part 'patch'
        Values are now: major=2, minor=17, patch=6
        New version will be '2.17.6'
        Dry run active, won't touch any files.
        Asserting files ./changelog.md contain the version string...
        Found '[2.17.5 (unreleased)](' in ./changelog.md at line 2:
        ## [2.17.5 (unreleased)](https://github.com/kdeldycke/repomatic/compare/v2.17.4...main)
        Would change file ./changelog.md:
        *** before ./changelog.md
        --- after ./changelog.md
        ***************
        *** 1,6 ****
          # Changelog

        ! ## [2.17.5 (unreleased)](https://github.com/kdeldycke/repomatic/compare/v2.17.4...main)

          > [!WARNING]
          > This version is **not released yet** and is under active development.
        --- 1,6 ----
          # Changelog

        ! ## [2.17.6 (unreleased)](https://github.com/kdeldycke/repomatic/compare/v2.17.4...main)

          > [!WARNING]
          > This version is **not released yet** and is under active development.
        Would write to config file pyproject.toml:
        *** before pyproject.toml
        --- after pyproject.toml
        ***************
        *** 1,5 ****
          [tool.bumpversion]
        ! current_version = "2.17.5"
          allow_dirty = true

          [[tool.bumpversion.files]]
        --- 1,5 ----
          [tool.bumpversion]
        ! current_version = "2.17.6"
          allow_dirty = true

          [[tool.bumpversion.files]]
        Would not commit
        Would not tag since we are not committing
        ```
        """
        # Extract parts of the changelog or set default values.
        sections = self.content.split(SECTION_START, 2)
        changelog_header = sections[0] if len(sections) > 0 else f"{CHANGELOG_HEADER}\n"
        current_entry = f"{SECTION_START}{sections[1]}" if len(sections) > 1 else ""
        past_entries = f"{SECTION_START}{sections[2]}" if len(sections) > 2 else ""

        # Derive the release template from the last entry.
        # Replace the release date with the unreleased label.
        new_entry = DATE_LABEL_PATTERN.sub(UNRELEASED_LABEL, current_entry, count=1)

        # Update GitHub's comparison URL to target the main branch.
        new_entry = VERSION_COMPARE_PATTERN.sub(
            f"v{self.current_version}...main", new_entry, count=1
        )

        # Replace the whole paragraph of changes by a notice message. The paragraph is
        # identified as starting by a blank line, at which point everything gets
        # replaced.
        new_entry = CHANGELOG_BODY_PATTERN.sub(DEVELOPMENT_WARNING, new_entry)
        logging.info("New generated section:\n" + indent(new_entry, " " * 2))

        history = current_entry + past_entries
        if new_entry not in history:
            history = new_entry + history
        return (changelog_header + history).rstrip()

    def set_release_date(self, release_date: str) -> bool:
        """Replace ``(unreleased)`` with the release date.

        Only the first occurrence is replaced (the current release
        section).

        :param release_date: Date string in ``YYYY-MM-DD`` format.
        :return: True if the content was modified.
        """
        updated = self.content.replace(UNRELEASED_LABEL, f" ({release_date})", 1)
        if updated == self.content:
            return False
        self.content = updated
        return True

    def update_comparison_url(self, default_branch: str = "main") -> bool:
        """Freeze the comparison URL to the release tag.

        Replaces ``...{branch})`` with ``...vX.Y.Z)`` for the first
        occurrence (the current release section).

        :param default_branch: Branch name to replace in the URL.
        :return: True if the content was modified.
        """
        updated = self.content.replace(
            f"...{default_branch})", f"...v{self.current_version})", 1
        )
        if updated == self.content:
            return False
        self.content = updated
        return True

    def remove_warning(self) -> bool:
        """Remove the first ``[!WARNING]`` development alert block.

        Matches a multi-line block starting with ``> [!WARNING]``
        (or legacy ``> [!IMPORTANT]``) and ending at the first blank line.

        :return: True if the content was modified.
        """
        updated = WARNING_PATTERN.sub("", self.content, count=1)
        if updated == self.content:
            return False
        self.content = updated
        return True

    def freeze(
        self,
        release_date: str | None = None,
        default_branch: str = "main",
    ) -> bool:
        """Run all freeze operations for release preparation.

        Combines :meth:`set_release_date`,
        :meth:`update_comparison_url`, and :meth:`remove_warning`
        into a single call.

        :param release_date: Date in ``YYYY-MM-DD`` format.
            Defaults to today (UTC).
        :param default_branch: Branch name for comparison URL.
        :return: True if any content was modified.
        """
        if release_date is None:
            release_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        changed = self.set_release_date(release_date)
        changed |= self.update_comparison_url(default_branch)
        changed |= self.remove_warning()
        return changed

    @classmethod
    def freeze_file(
        cls,
        path: Path,
        version: str,
        release_date: str | None = None,
        default_branch: str = "main",
    ) -> bool:
        """Freeze a changelog file in place.

        Reads the file, applies all freeze operations via
        :meth:`freeze`, and writes the result back.

        :param path: Path to the changelog file.
        :param version: Current version string.
        :param release_date: Date in ``YYYY-MM-DD`` format.
            Defaults to today (UTC).
        :param default_branch: Branch name for comparison URL.
        :return: True if the file was modified.
        """
        if not path.exists():
            logging.warning(f"Changelog not found: {path}")
            return False

        original = path.read_text(encoding="UTF-8")
        changelog = cls(original, current_version=version)
        if not changelog.freeze(
            release_date=release_date, default_branch=default_branch
        ):
            logging.debug(f"No changes to {path}")
            return False

        path.write_text(changelog.content, encoding="UTF-8")
        logging.info(f"Updated {path}")
        return True

    def extract_version_url(self, version: str) -> str:
        """Extract the URL from the changelog heading for a specific version.

        :param version: Version string to look for (e.g. ``1.2.3``).
        :return: The URL from the heading, or empty string if not found.
        """
        match = re.search(
            rf"^{SECTION_START}"
            rf"\s*\[.*{re.escape(version)}.+?\]"
            rf"\((?P<url>[^)]+)\)",
            self.content,
            flags=re.MULTILINE,
        )
        if not match:
            return ""
        return match.group("url")

    def extract_version_notes(self, version: str) -> str:
        """Extract the changelog entry for a specific version.

        Parses the changelog content and returns the body text between
        the ``## [version ...]`` heading and the next ``##`` heading.

        :param version: Version string to look for (e.g. ``1.2.3``).
        :return: The changelog entry body, or empty string if not
            found.
        """
        match = re.search(
            rf"^{SECTION_START}"
            rf"(?P<title>.+{re.escape(version)}`? .+?)\n"
            rf"(?P<changes>.*?)(?:\n{SECTION_START}|\Z)",
            self.content,
            flags=re.MULTILINE | re.DOTALL,
        )
        if not match:
            return ""
        return match.groupdict().get("changes", "").strip()

    def extract_repo_url(self) -> str:
        """Extract the repository URL from changelog comparison links.

        Parses the first ``## [...](<repo_url>/compare/...)`` heading
        and returns the base repository URL (e.g.
        ``https://github.com/user/repo``).

        :return: The repository URL, or empty string if not found.
        """
        match = re.search(
            rf"^{SECTION_START}\s*\[.+?\]\((?P<repo>https?://[^/]+/[^/]+/[^/]+)/compare/",
            self.content,
            flags=re.MULTILINE,
        )
        if not match:
            return ""
        return match.group("repo")

    def extract_all_releases(self) -> list[tuple[str, str]]:
        """Extract all released versions and their dates from the changelog.

        Scans for headings matching ``## [X.Y.Z (YYYY-MM-DD)](...)``.
        Unreleased versions (with ``(unreleased)``) are skipped.

        :return: List of ``(version, date)`` tuples ordered as they
            appear in the changelog (newest first).
        """
        return RELEASED_VERSION_PATTERN.findall(self.content)

    def extract_all_version_headings(self) -> set[str]:
        """Extract all version strings from ``##`` headings.

        Includes both released and unreleased versions, so the caller
        can avoid false-positive orphan detection for the current
        development version.

        :return: Set of version strings found in headings.
        """
        return set(
            re.findall(
                rf"^{SECTION_START}\s*\[`?(\d+\.\d+\.\d+(?:\.\w+)?)`?\s",
                self.content,
                flags=re.MULTILINE,
            )
        )

    def fix_release_date(self, version: str, new_date: str) -> bool:
        """Replace the date in a specific version heading.

        :param version: Version string (e.g. ``1.2.3``).
        :param new_date: New date in ``YYYY-MM-DD`` format.
        :return: True if the content was modified.
        """
        pattern = re.compile(
            rf"^({SECTION_START}\s*\[`?{re.escape(version)}`?\s+\()[^)]+(\)\].*)$",
            re.MULTILINE,
        )
        updated = pattern.sub(rf"\g<1>{new_date}\g<2>", self.content, count=1)
        if updated == self.content:
            return False
        self.content = updated
        return True

    def add_admonition_after_heading(
        self,
        version: str,
        admonition: str,
        *,
        dedup_marker: str | None = None,
    ) -> bool:
        """Insert an admonition block after a version heading.

        Skips insertion if the dedup marker (or the full admonition) is
        already present in the version's section. The admonition is
        inserted on a new line after the heading, separated by a blank
        line.

        :param version: Version string to locate (e.g. ``1.2.3``).
        :param admonition: The full admonition block text (including
            ``>`` prefix lines).
        :param dedup_marker: A unique substring to check for duplicates
            instead of the full admonition. Useful when admonition
            formatting may vary slightly between runs.
        :return: True if the content was modified.
        """
        marker = dedup_marker or admonition
        # Extract the section for this version (heading to next heading).
        section_pattern = re.compile(
            rf"^({SECTION_START}\s*\[`?{re.escape(version)}`?\s[^\n]+)"
            rf"(.*?)(?=^{SECTION_START}|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        section_match = section_pattern.search(self.content)
        if not section_match:
            return False
        section_text = section_match.group(0)
        if marker in section_text:
            return False
        # Insert after the heading line.
        heading_end = section_match.start() + len(section_match.group(1))
        self.content = (
            self.content[:heading_end]
            + "\n\n"
            + admonition
            + self.content[heading_end:]
        )
        return True

    def remove_admonition_from_section(
        self,
        version: str,
        marker: str,
    ) -> bool:
        """Remove an admonition block from a version section.

        Finds the version's section and removes any GFM alert block
        containing the marker string. Cleans up surrounding blank lines.

        :param version: Version string to locate (e.g. ``1.2.3``).
        :param marker: A substring identifying the admonition to remove.
        :return: True if the content was modified.
        """
        section_pattern = re.compile(
            rf"^({SECTION_START}\s*\[`?{re.escape(version)}`?\s[^\n]+)"
            rf"(.*?)(?=^{SECTION_START}|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        section_match = section_pattern.search(self.content)
        if not section_match:
            return False
        section_text = section_match.group(0)
        if marker not in section_text:
            return False
        # Remove the full GFM alert block (consecutive lines starting
        # with "> ") that contains the marker, plus surrounding blanks.
        admonition_pattern = re.compile(
            r"\n*(?:^>.*$\n?)+",
            re.MULTILINE,
        )
        new_section = section_text
        for block_match in admonition_pattern.finditer(section_text):
            if marker in block_match.group(0):
                new_section = (
                    section_text[: block_match.start()]
                    + "\n\n"
                    + section_text[block_match.end() :]
                )
                break
        self.content = self.content.replace(section_text, new_section, 1)
        return True

    def strip_availability_admonitions(self, version: str) -> bool:
        """Remove all availability admonitions from a version section.

        Strips GFM alert blocks where the body matches
        ``> `{version}` is ...`` — covering NOTE (available), WARNING
        (not available), and any wording variant. Other admonitions
        (e.g. "not released yet", yanked) are preserved.

        :param version: Version string to locate (e.g. ``1.2.3``).
        :return: True if the content was modified.
        """
        section_pattern = re.compile(
            rf"^({SECTION_START}\s*\[`?{re.escape(version)}`?\s[^\n]+)"
            rf"(.*?)(?=^{SECTION_START}|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        section_match = section_pattern.search(self.content)
        if not section_match:
            return False
        section_text = section_match.group(0)

        # Find all GFM alert blocks (consecutive lines starting with "> ")
        # and remove those where any line matches "> `{version}` is ".
        # All availability verbs (AVAILABLE_VERB, FIRST_AVAILABLE_VERB,
        # NOT_AVAILABLE_VERB) share the "is " prefix, so this catches all.
        availability_marker = f"> `{version}` is "
        admonition_pattern = re.compile(
            r"(?:^>.*$\n?)+",
            re.MULTILINE,
        )
        new_section = section_text
        for block_match in reversed(list(admonition_pattern.finditer(section_text))):
            if availability_marker in block_match.group(0):
                start = block_match.start()
                end = block_match.end()
                new_section = new_section[:start] + new_section[end:]

        if new_section == section_text:
            return False

        # Collapse excess blank lines (3+ consecutive newlines → 2).
        new_section = re.sub(r"\n{3,}", "\n\n", new_section)
        self.content = self.content.replace(section_text, new_section, 1)
        return True

    def insert_version_section(
        self,
        version: str,
        date: str,
        repo_url: str,
        all_versions: list[str],
    ) -> bool:
        """Insert a placeholder section for a missing version.

        The section is placed at the correct position in descending
        version order. The comparison URL points from the next-lower
        version to this one. After insertion, the next-higher version's
        comparison URL base is updated to reference this version, keeping
        the timeline coherent.

        Idempotent: returns False if the version heading already exists.

        :param version: Version string (e.g. ``1.2.3``).
        :param date: Release date in ``YYYY-MM-DD`` format.
        :param repo_url: Repository URL for comparison links.
        :param all_versions: All known versions sorted descending.
        :return: True if the content was modified.
        """
        # Idempotent: skip if already present.
        if version in self.extract_all_version_headings():
            return False

        parsed = Version(version)

        # Find the next-lower version for the comparison URL base.
        lower_version = None
        for v in sorted(all_versions, key=Version, reverse=True):
            if Version(v) < parsed:
                lower_version = v
                break

        compare_base = f"v{lower_version}" if lower_version else "v0.0.0"
        heading = (
            f"## [`{version}` ({date})]"
            f"({repo_url}/compare/{compare_base}...v{version})\n"
        )

        # Find the right insertion point: before the first heading whose
        # version is lower than this one.
        insert_pos = None
        for match in re.finditer(
            rf"^{SECTION_START}\s*\[`?(\d+\.\d+\.\d+)`?\s",
            self.content,
            flags=re.MULTILINE,
        ):
            existing = Version(match.group(1))
            if existing < parsed:
                insert_pos = match.start()
                break

        if insert_pos is not None:
            self.content = (
                self.content[:insert_pos] + heading + "\n" + self.content[insert_pos:]
            )
        else:
            # Append at the end (oldest version).
            self.content = self.content.rstrip() + "\n\n" + heading

        # Update the next-higher version's comparison URL to point to
        # this newly inserted version.
        higher_version = None
        for v in sorted(all_versions, key=Version):
            if Version(v) > parsed:
                higher_version = v
                break
        if higher_version:
            self.update_comparison_base(higher_version, version)

        return True

    def update_comparison_base(self, version: str, new_base: str) -> bool:
        """Replace the base version in a version heading's comparison URL.

        Changes ``compare/vOLD...vX.Y.Z`` to ``compare/vNEW...vX.Y.Z``
        in the heading for the given version.

        :param version: The version whose heading to update.
        :param new_base: New base version (without ``v`` prefix).
        :return: True if the content was modified.
        """
        pattern = re.compile(
            rf"(^{SECTION_START}\s*\[`?{re.escape(version)}`?\s[^\n]*"
            rf"/compare/)v[^.]+\.[^.]+\.[^.]+(\.\.\.v{re.escape(version)}\))",
            re.MULTILINE,
        )
        updated = pattern.sub(rf"\g<1>v{new_base}\g<2>", self.content, count=1)
        if updated == self.content:
            return False
        self.content = updated
        return True


class PyPIRelease(NamedTuple):
    """Release metadata for a single version from PyPI."""

    date: str
    """Earliest upload date across all files in ``YYYY-MM-DD`` format."""

    yanked: bool
    """Whether all files for this version are yanked."""


def get_pypi_release_dates(package: str) -> dict[str, PyPIRelease]:
    """Get upload dates and yanked status for all versions from PyPI.

    Fetches the package metadata in a single API call. For each version,
    selects the **earliest** upload time across all distribution files as
    the canonical release date. A version is considered yanked only if
    **all** of its files are yanked.

    :param package: The PyPI package name.
    :return: Dict mapping version strings to :class:`PyPIRelease` tuples.
        Empty dict if the package is not found or the request fails.
    """
    url = PYPI_API_URL.format(package=package)
    request = Request(url, headers={"Accept": "application/json"})  # noqa: S310
    try:
        with urlopen(request, timeout=10) as response:  # noqa: S310
            data = json.loads(response.read())
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        logging.debug(f"PyPI lookup failed for {package}: {exc}")
        return {}

    result: dict[str, PyPIRelease] = {}
    for version, files in data.get("releases", {}).items():
        if not files:
            continue
        # Select the earliest upload time across all distribution files.
        dates = [f["upload_time"][:10] for f in files if f.get("upload_time")]
        if not dates:
            continue
        earliest_date = min(dates)
        # A version is yanked only if every file is yanked.
        all_yanked = all(f.get("yanked", False) for f in files)
        result[version] = PyPIRelease(date=earliest_date, yanked=all_yanked)

    return result


def build_release_admonition(
    version: str,
    *,
    pypi_url: str = "",
    github_url: str = "",
    first_on_all: bool = False,
) -> str:
    """Build a GFM release admonition with available distribution links.

    :param version: Version string (e.g. ``1.2.3``).
    :param pypi_url: PyPI project URL, or empty if not on PyPI.
    :param github_url: GitHub release URL, or empty if no release exists.
    :param first_on_all: Whether every listed platform is a first appearance.
        When ``True``, uses "is the *first version* available on" wording.
    :return: A ``> [!NOTE]`` admonition block, or empty string if neither
        URL is provided.
    """
    links: list[str] = []
    if pypi_url:
        links.append(f"[{PYPI_LABEL}]({pypi_url})")
    if github_url:
        links.append(f"[{GITHUB_LABEL}]({github_url})")
    if not links:
        return ""
    platforms = " and ".join(links)
    verb = FIRST_AVAILABLE_VERB if first_on_all else AVAILABLE_VERB
    return AVAILABLE_ADMONITION.format(version=version, verb=verb, platforms=platforms)


def build_unavailable_admonition(
    version: str,
    *,
    missing_pypi: bool = False,
    missing_github: bool = False,
) -> str:
    """Build a GFM warning admonition for platforms missing a version.

    :param version: Version string (e.g. ``1.2.3``).
    :param missing_pypi: Whether the version is missing from PyPI.
    :param missing_github: Whether the version is missing from GitHub.
    :return: A ``> [!WARNING]`` admonition block, or empty string if
        neither platform is missing.
    """
    names: list[str] = []
    if missing_pypi:
        names.append(PYPI_LABEL)
    if missing_github:
        names.append(GITHUB_LABEL)
    if not names:
        return ""
    platforms = " and ".join(names)
    return UNAVAILABLE_ADMONITION.format(
        version=version, verb=NOT_AVAILABLE_VERB, platforms=platforms
    )


def lint_changelog_dates(
    changelog_path: Path,
    package: str | None = None,
    *,
    fix: bool = False,
) -> int:
    """Verify that changelog release dates match canonical release dates.

    Uses PyPI upload dates as the canonical reference when the project
    is published to PyPI. Falls back to git tag dates for projects not
    on PyPI.

    Versions older than the first PyPI release are expected to be absent
    and logged at info level. Versions newer than the first PyPI release
    but missing from PyPI are unexpected and logged as warnings.

    Also detects **orphaned versions**: versions that exist as git tags,
    GitHub releases, or PyPI packages but have no corresponding changelog
    entry. Orphans are logged as warnings and cause a non-zero exit code.

    When ``fix`` is enabled, date mismatches are corrected in-place and
    admonitions are added to the changelog:

    - A ``[!NOTE]`` admonition listing available distribution links
      (PyPI, GitHub) for each version. Links are conditional: only
      sources where the version exists are included.
    - A ``[!WARNING]`` admonition listing platforms where the version
      is *not* available (missing from PyPI, GitHub, or both).
    - A ``[!CAUTION]`` admonition for yanked releases.
    - Placeholder sections for orphaned versions, with comparison URLs
      linking to adjacent versions.

    :param changelog_path: Path to the changelog file.
    :param package: PyPI package name. If ``None``, auto-detected from
        ``pyproject.toml``. If detection fails, falls back to git tags.
    :param fix: If True, fix dates and add admonitions to the file.
    :return: ``0`` if all dates match or references are missing,
        ``1`` if any date mismatch or orphan is found.
    """
    from .git_ops import get_all_version_tags, get_tag_date
    from .github.actions import AnnotationLevel, emit_annotation
    from .metadata import get_project_name

    content = changelog_path.read_text(encoding="UTF-8")
    changelog = Changelog(content)
    releases = changelog.extract_all_releases()

    if not releases:
        logging.info("No released versions found in changelog.")
        return 0

    # Auto-detect package name for PyPI lookups.
    if package is None:
        package = get_project_name()

    # Fetch all PyPI release dates in a single API call.
    pypi_data: dict[str, PyPIRelease] = {}
    if package:
        pypi_data = get_pypi_release_dates(package)
        if pypi_data:
            logging.info(
                f"Using PyPI as reference for {package!r}"
                f" ({len(pypi_data)} releases found)."
            )
        else:
            logging.info(
                f"Package {package!r} not found on PyPI, falling back to git tags."
            )
    else:
        logging.info("No package name detected, falling back to git tags.")

    use_pypi = bool(pypi_data)
    has_mismatch = False
    modified = False

    # Determine the first version published to PyPI for boundary detection.
    first_pypi_version: Version | None = None
    if use_pypi:
        first_pypi_version = min(Version(v) for v in pypi_data)
        logging.info(f"First PyPI version: {first_pypi_version}")

    # Extract repository URL and fetch GitHub releases.
    repo_url = changelog.extract_repo_url()
    github_releases: dict[str, GitHubRelease] = {}
    if repo_url:
        github_releases = get_github_releases(repo_url)
        if github_releases:
            logging.info(f"GitHub releases: {len(github_releases)} found.")

    # Determine the first version released on GitHub for boundary detection.
    first_github_version: Version | None = None
    if github_releases:
        first_github_version = min(Version(v) for v in github_releases)
        logging.info(f"First GitHub version: {first_github_version}")

    # Detect orphaned versions: present in external sources but missing
    # from the changelog.
    tag_versions = get_all_version_tags()
    changelog_headings = changelog.extract_all_version_headings()
    all_known = set(pypi_data) | set(github_releases) | set(tag_versions)
    orphans = all_known - changelog_headings
    if orphans:
        for orphan in sorted(orphans, key=Version):
            logging.warning(
                f"⚠ {orphan}: found in external sources but missing"
                " from changelog"
            )
            emit_annotation(
                AnnotationLevel.WARNING,
                (
                    f"Version {orphan} exists as a tag, GitHub release,"
                    " or PyPI package but has no changelog entry"
                ),
            )
        has_mismatch = True

        if fix and repo_url:
            # Insert orphans oldest-first so each insertion correctly
            # updates the adjacent section's comparison URL.
            all_versions = sorted(
                changelog_headings | orphans,
                key=Version,
                reverse=True,
            )
            for orphan in sorted(orphans, key=Version):
                # Determine date: prefer PyPI, then GitHub, then git tag.
                orphan_date = ""
                if orphan in pypi_data:
                    orphan_date = pypi_data[orphan].date
                elif orphan in github_releases:
                    orphan_date = github_releases[orphan].date
                elif orphan in tag_versions:
                    orphan_date = tag_versions[orphan]
                if not orphan_date:
                    orphan_date = "0000-00-00"
                modified |= changelog.insert_version_section(
                    orphan, orphan_date, repo_url, list(all_versions)
                )

            # Re-extract releases so the admonition loop below processes
            # the newly inserted sections.
            releases = changelog.extract_all_releases()

    for version, changelog_date in releases:
        if use_pypi:
            release = pypi_data.get(version)
            if release is None:
                parsed = Version(version)
                if first_pypi_version and parsed < first_pypi_version:
                    logging.info(
                        f"  {version}: predates PyPI (first: {first_pypi_version})"
                    )
                    continue
                logging.warning(f"⚠ {version}: not found on PyPI")
                emit_annotation(
                    AnnotationLevel.WARNING,
                    f"Version {version} not found on PyPI",
                )
                continue
            ref_date = release.date
            source = "PyPI"
        else:
            tag_date = get_tag_date(f"v{version}")
            source = "tag"
            if tag_date is None:
                logging.warning(f"⚠ {version}: not found on {source}")
                emit_annotation(
                    AnnotationLevel.WARNING,
                    f"Version {version} not found on {source}",
                )
                continue
            ref_date = tag_date

        if changelog_date == ref_date:
            logging.info(f"✓ {version}: {changelog_date} ({source})")
        else:
            logging.error(
                f"✗ {version}: changelog={changelog_date}, {source}={ref_date}"
            )
            emit_annotation(
                AnnotationLevel.ERROR,
                (
                    f"Date mismatch for {version}:"
                    f" changelog={changelog_date}, {source}={ref_date}"
                ),
            )
            has_mismatch = True
            if fix:
                modified |= changelog.fix_release_date(version, ref_date)

    # In fix mode, build release admonitions for all versions based on
    # availability in PyPI and GitHub (independently).
    if fix:
        for version, _date in releases:
            on_pypi = version in pypi_data
            on_github = version in github_releases

            # Build the NOTE admonition for platforms where available.
            pypi_url = (
                PYPI_PROJECT_URL.format(package=package, version=version)
                if on_pypi and package
                else ""
            )
            github_url = (
                GITHUB_RELEASE_URL.format(repo_url=repo_url, version=version)
                if on_github and repo_url
                else ""
            )

            # "First version" wording applies when every listed platform
            # is a first appearance for that platform.
            parsed = Version(version)
            is_first_pypi = (
                on_pypi
                and first_pypi_version is not None
                and parsed == first_pypi_version
            )
            is_first_github = (
                on_github
                and first_github_version is not None
                and parsed == first_github_version
            )
            first_on_all = (
                (is_first_pypi or not on_pypi)
                and (is_first_github or not on_github)
                and (is_first_pypi or is_first_github)
            )

            note = build_release_admonition(
                version,
                pypi_url=pypi_url,
                github_url=github_url,
                first_on_all=first_on_all,
            )

            # Build the WARNING admonition for platforms where missing.
            # Only warn about gaps: versions that postdate the first
            # release on that platform but are absent from it.
            pypi_gap = (
                not on_pypi
                and bool(package)
                and first_pypi_version is not None
                and parsed >= first_pypi_version
            )
            github_gap = (
                not on_github
                and bool(repo_url)
                and first_github_version is not None
                and parsed >= first_github_version
            )
            warning = build_unavailable_admonition(
                version,
                missing_pypi=pypi_gap,
                missing_github=github_gap,
            )

            # Strip all availability admonitions, then re-add current ones.
            # This is idempotent: stripping already-correct admonitions and
            # re-adding them produces the same content.
            snapshot = changelog.content
            changelog.strip_availability_admonitions(version)
            expected_admonitions = [a for a in (note, warning) if a]
            for admonition in expected_admonitions:
                changelog.add_admonition_after_heading(
                    version,
                    admonition,
                )
            if changelog.content != snapshot:
                modified = True

            if on_pypi and pypi_data[version].yanked:
                modified |= changelog.add_admonition_after_heading(
                    version,
                    YANKED_ADMONITION,
                    dedup_marker=YANKED_DEDUP_MARKER,
                )

    if fix and modified:
        changelog_path.write_text(changelog.content, encoding="UTF-8")
        logging.info(f"Updated {changelog_path}")

    # In fix mode, mismatches were corrected in-place, so return success
    # to let downstream workflow steps (e.g., PR creation) proceed.
    if fix and modified:
        return 0
    return 1 if has_mismatch else 0
