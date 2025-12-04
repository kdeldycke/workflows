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

from __future__ import annotations

import logging
import re
import sys
from functools import cached_property
from pathlib import Path
from textwrap import indent

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]


class Changelog:
    """Helpers to manipulate changelog files written in Markdown."""

    def __init__(self, initial_changelog: str | None = None) -> None:
        if not initial_changelog:
            self.content = "# Changelog\n"
        else:
            self.content = initial_changelog
        logging.debug(f"Initial content set to:\n{self.content}")

    @cached_property
    def current_version(self) -> str | None:
        # Extract current version as defined by bump-my-version.
        config_file = Path("./pyproject.toml").resolve()
        logging.info(f"Open {config_file}")
        config = tomllib.loads(config_file.read_text(encoding="UTF-8"))
        current_version = config["tool"]["bumpversion"]["current_version"]
        logging.info(f"Current version: {current_version}")
        return current_version if current_version else None

    def update(self) -> str:
        r"""Adds a new empty entry at the top of the changelog.

        Will return the same content as the current changelog if it has already been updated.

        This is designed to be used just after a new release has been tagged. And before a
        post-release version increment is applied with a call to:

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
        SECTION_START = "##"
        sections = self.content.split(SECTION_START, 2)
        changelog_header = sections[0] if len(sections) > 0 else "# Changelog\n\n"
        current_entry = f"{SECTION_START}{sections[1]}" if len(sections) > 1 else ""
        past_entries = f"{SECTION_START}{sections[2]}" if len(sections) > 2 else ""

        # Derive the release template from the last entry.
        DATE_REGEX = r"\d{4}\-\d{2}\-\d{2}"
        VERSION_REGEX = r"\d+\.\d+\.\d+"

        # Replace the release date with the unreleased tag.
        new_entry = re.sub(DATE_REGEX, "unreleased", current_entry, count=1)

        # Update GitHub's comparison URL to target the main branch.
        new_entry = re.sub(
            rf"v{VERSION_REGEX}\.\.\.v{VERSION_REGEX}",
            f"v{self.current_version}...main",
            new_entry,
            count=1,
        )

        # Replace the whole paragraph of changes by a notice message. The paragraph is
        # identified as starting by a blank line, at which point everything gets
        # replaced.
        new_entry = re.sub(
            r"\n\n.*",
            "\n\n"
            "> [!IMPORTANT]\n"
            "> This version is not released yet and is under active development.\n\n",
            new_entry,
            flags=re.MULTILINE | re.DOTALL,
        )
        logging.info("New generated section:\n" + indent(new_entry, " " * 2))

        history = current_entry + past_entries
        if new_entry not in history:
            history = new_entry + history
        return (changelog_header + history).rstrip()
