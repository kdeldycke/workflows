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

"""Adds a new empty entry at the top of the changelog.

This is designed to be used just after a new release has been tagged. And before a
post-release version increment is applied with a call to:

```shell-sesssion
$ bump-my-version bump --verbose patch
Starting BumpVersion 0.5.1.dev6
Reading config file pyproject.toml:
Specified version (2.17.5) does not match last tagged version (2.17.4)
Parsing version '2.17.5' using regexp '(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<patch>\\d+)'
Parsed the following values: major=2, minor=17, patch=5
Attempting to increment part 'patch'
Values are now: major=2, minor=17, patch=6
New version will be '2.17.6'
Dry run active, won't touch any files.
Asserting files ./changelog.md contain the version string...
Found '[2.17.5 (unreleased)](' in ./changelog.md at line 2: ## [2.17.5 (unreleased)](https://github.com/kdeldycke/workflows/compare/v2.17.4...main)
Would change file ./changelog.md:
*** before ./changelog.md
--- after ./changelog.md
***************
*** 1,6 ****
  # Changelog

! ## [2.17.5 (unreleased)](https://github.com/kdeldycke/workflows/compare/v2.17.4...main)

  ```{important}
  This version is not released yet and is under active development.
--- 1,6 ----
  # Changelog

! ## [2.17.6 (unreleased)](https://github.com/kdeldycke/workflows/compare/v2.17.4...main)

  ```{important}
  This version is not released yet and is under active development.
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

from __future__ import annotations

import re
import sys
from pathlib import Path
from textwrap import indent

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import]

# Extract current version as defined by bump-my-version.
config_file = Path("./pyproject.toml").resolve()
print(f"Open {config_file}")
config = tomllib.loads(config_file.read_text())
current_version = config["tool"]["bumpversion"]["current_version"]
print(f"Current version: {current_version}")
assert current_version

# Open changelog.
changelog_file = Path("./changelog.md").resolve()
print(f"Open {changelog_file}")
content = changelog_file.read_text()
assert current_version in content

# Analyse the current changelog.
SECTION_START = "##"
changelog_header, last_entry, past_entries = content.split(SECTION_START, 2)

# Derive the release template from the last entry.
DATE_REGEX = r"\d{4}\-\d{2}\-\d{2}"
VERSION_REGEX = r"\d+\.\d+\.\d+"

# Replace the release date with the unreleased tag.
new_entry = re.sub(DATE_REGEX, "unreleased", last_entry, count=1)

# Update GitHub's comparison URL to target the main branch.
new_entry = re.sub(
    rf"v{VERSION_REGEX}\.\.\.v{VERSION_REGEX}",
    f"v{current_version}...main",
    new_entry,
    count=1,
)

# Replace the whole paragraph of changes by a notice message. The paragraph is
# identified as starting by a blank line, at which point everything gets replaced.
new_entry = re.sub(
    r"\n\n.*",
    "\n\n"
    "```{important}\n"
    "This version is not released yet and is under active development.\n"
    "```\n\n",
    new_entry,
    flags=re.MULTILINE | re.DOTALL,
)

# Prefix entries with section marker.
new_entry = f"{SECTION_START}{new_entry}"
history = f"{SECTION_START}{last_entry}{SECTION_START}{past_entries}"

print("New generated section:\n" + indent(new_entry, " " * 2))

# Recompose full changelog with new top entry.
changelog_file.write_text(f"{changelog_header}{new_entry}{history}")
