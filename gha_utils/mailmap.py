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
import sys
from dataclasses import dataclass, field
from functools import cached_property
from subprocess import run

from boltons.iterutils import unique  # type: ignore[import-untyped]


@dataclass(order=True, frozen=True)
class Record:
    """A mailmap identity mapping entry."""

    # Mapping is define as the first field so we have natural sorting,
    # whatever the value of the pre_comment is.
    canonical: str = ""
    aliases: set[str] = field(default_factory=set)
    pre_comment: str = ""

    def __str__(self) -> str:
        """Render the record with pre-comments first, followed by the identity mapping.

        Sort all entries in the mapping without case-sensitivity, but keep the first in
        its place as the canonical identity.
        """
        lines = []
        if self.pre_comment:
            lines.append(self.pre_comment)
        if self.canonical:
            lines.append(
                " ".join((self.canonical, *sorted(self.aliases, key=str.casefold)))
            )
        return "\n".join(lines)


class Mailmap:
    """Helpers to manipulate ``.mailmap`` files.

    ``.mailmap`` `file format is documented on Git website
    <https://git-scm.com/docs/gitmailmap>`_.
    """

    records: list[Record] = list()

    @staticmethod
    def split_identities(mapping: str) -> tuple[str, set[str]]:
        """Split a mapping of identities and normalize them."""
        identities = []
        for identity in map(str.strip, mapping.split(">")):
            # Skip blank strings produced by uneven spaces.
            if not identity:
                continue
            assert identity.count("<") == 1, f"Unexpected email format in {identity!r}"
            name, email = identity.split("<", maxsplit=1)
            identities.append(f"{name.strip()} <{email}>")

        assert len(identities), f"No identities found in {mapping!r}"

        identities = list(unique(identities))
        return identities[0], set(identities[1:])

    def parse(self, content: str) -> None:
        """Parse mailmap content and add it to the current list of records.

        Each non-empty, non-comment line is considered a mapping entry.

        The preceding lines of a mapping entry are kept attached to it as pre-comments,
        so the layout will be preserved on rendering, during which records are sorted.
        """
        logging.debug(f"Parsing:\n{content}")
        pre_lines = []
        for line in map(str.strip, content.splitlines()):
            # Comment lines are added as-is.
            if line.startswith("#"):
                pre_lines.append(line)
            # Blank lines are added as-is.
            elif not line:
                pre_lines.append(line)
            # Mapping entry, which mark the end of a block, so add it to the list
            # mailmap records.
            else:
                canonical, aliases = self.split_identities(line)
                record = Record(
                    pre_comment="\n".join(pre_lines),
                    canonical=canonical,
                    aliases=aliases,
                )
                logging.debug(record)
                pre_lines = []
                self.records.append(record)

    def find(self, identity: str) -> bool:
        """Returns ``True`` if the provided identity matched any record."""
        identity_token = identity.lower()
        for record in self.records:
            # Identity matching is case insensitive:
            # https://git-scm.com/docs/gitmailmap#_syntax
            if identity_token in map(str.lower, (record.canonical, *record.aliases)):
                return True
        return False

    @cached_property
    def git_contributors(self) -> set[str]:
        """Returns the set of all constributors found in the Git commit history.

        No normalization happens: all variations of authors and committers strings
        attached to all commits are considered.

        For format output syntax, see:
        https://git-scm.com/docs/pretty-formats#Documentation/pretty-formats.txt-emaNem
        """
        contributors = set()

        git_cli = ("git", "log", "--pretty=format:%aN <%aE>%n%cN <%cE>")
        logging.debug(f"Run: {' '.join(git_cli)}")
        process = run(git_cli, capture_output=True, encoding="UTF-8")

        # Parse git CLI output.
        if process.returncode:
            sys.exit(process.stderr)
        for line in map(str.strip, process.stdout.splitlines()):
            if line:
                contributors.add(line)

        logging.debug(
            "Authors and committers found in Git history:\n"
            + "\n".join(sorted(contributors, key=str.casefold))
        )
        return contributors

    def update_from_git(self) -> None:
        """Add to internal records all missing contributors found in commit history.

        This method will refrain from adding contributors already registered as aliases.
        """
        for contributor in self.git_contributors:
            if not self.find(contributor):
                record = Record(canonical=contributor)
                logging.info(f"Add new identity {record}")
                self.records.append(record)
            else:
                logging.debug(f"Ignore existing identity {contributor}")

    def render(self) -> str:
        """Render internal records in Mailmap format."""
        return "\n".join(
            map(str, sorted(self.records, key=lambda r: r.canonical.casefold()))
        )
