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
2. Pin the comparison URL from ``...main`` to ``...vX.Y.Z``.
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
    <https://github.com/kdeldycke/workflows/issues/94>`_) — none
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
reference pinning, or the two-commit freeze/unfreeze release cycle.
The multiplication of files across the repo adds complexity, and
there is no 1:1 mapping between fragments and changelog entries.

Specific gaps across all evaluated tools:

- **No comparison URL management.** None generate GitHub
  ``v1.0.0...v1.1.0`` diff links, or update them from ``...main``
  to ``...vX.Y.Z`` at release time.
- **No unreleased section lifecycle.** None manage the
  ``[!IMPORTANT]`` GFM alert warning that the version is under
  active development, inserting it post-release and removing it at
  release time.
- **No workflow action reference pinning.** None handle the
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

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from textwrap import indent

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

WARNING_PATTERN = re.compile(r"^> \[!IMPORTANT\].+?\n\n", re.MULTILINE | re.DOTALL)
"""Pattern matching the first ``[!IMPORTANT]`` GFM alert block."""

DEVELOPMENT_WARNING = (
    "\n\n"
    "> [!IMPORTANT]\n"
    "> This version is not released yet and is under active development.\n\n"
)
"""GFM alert block warning that the version is under active development."""


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
        ## [2.17.5 (unreleased)](https://github.com/kdeldycke/workflows/compare/v2.17.4...main)
        Would change file ./changelog.md:
        *** before ./changelog.md
        --- after ./changelog.md
        ***************
        *** 1,6 ****
          # Changelog

        ! ## [2.17.5 (unreleased)](https://github.com/kdeldycke/workflows/compare/v2.17.4...main)

          > [!IMPORTANT]
          > This version is not released yet and is under active development.
        --- 1,6 ----
          # Changelog

        ! ## [2.17.6 (unreleased)](https://github.com/kdeldycke/workflows/compare/v2.17.4...main)

          > [!IMPORTANT]
          > This version is not released yet and is under active development.
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
        """Pin the comparison URL to the release tag.

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
        """Remove the first ``[!IMPORTANT]`` GFM alert block.

        Matches a multi-line block starting with ``> [!IMPORTANT]``
        and ending at the first blank line.

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
            rf"(?P<title>.+{re.escape(version)} .+?)\n"
            rf"(?P<changes>.*?)(?:\n{SECTION_START}|\Z)",
            self.content,
            flags=re.MULTILINE | re.DOTALL,
        )
        if not match:
            return ""
        return match.groupdict().get("changes", "").strip()
