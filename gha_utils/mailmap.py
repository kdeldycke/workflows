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
from functools import cached_property
from subprocess import run
from textwrap import dedent


class Mailmap:
    """Helpers to manipulate ``.mailmap`` file.

    The ``.mailmap`` files expected to be found in the root of repository.
    """

    def __init__(self, initial_mailmap: str | None = None) -> None:
        if not initial_mailmap:
            # Initialize empty .mailmap with pointers to reference documentation.
            self.content = dedent(
                """\
                # Format is:
                #   Preferred Name <preferred e-mail>  Other Name <other e-mail>
                #
                # Reference: https://git-scm.com/docs/git-blame#_mapping_authors
                """,
            )
        else:
            self.content = initial_mailmap
        logging.debug(f"Initial content set to:\n{self.content}")

    @cached_property
    def git_contributors(self) -> set[str]:
        """Returns the set of all constributors found in the Git commit history.

        No normalization happens: all variations of authors and committers strings attached to all commits are considered.

        For format output syntax, see:
        https://git-scm.com/docs/pretty-formats#Documentation/pretty-formats.txt-emaNem
        """
        contributors = set()

        git_cli = ("git", "log", "--pretty=format:%aN <%aE>%n%cN <%cE>")
        logging.debug(f"Run: {' '.join(git_cli)}")
        process = run(git_cli, capture_output=True, encoding="utf-8")

        # Parse git CLI output.
        if process.returncode:
            sys.exit(process.stderr)
        for line in process.stdout.splitlines():
            if line.strip():
                contributors.add(line)

        logging.debug(
            "Authors and committers found in Git history:\n"
            + "\n".join(sorted(contributors, key=str.casefold))
        )
        return contributors

    def updated_map(self):
        """Add all missing contributors from commit history to mailmap.

        This method will refrain from adding contributors already registered as aliases.
        """
        # Extract comments in .mailmap header and keep mapping lines.
        header_comments = []
        mappings = set()
        for line in self.content.splitlines():
            if line.startswith("#"):
                header_comments.append(line)
            elif line.strip():
                mappings.add(line)

        # Add all missing contributors to the mail mapping.
        for contributor in self.git_contributors:
            if contributor not in self.content:
                logging.debug(f"{contributor!r} not found in original content, add it.")
                mappings.add(contributor)

        # Render content in .mailmap format.
        return (
            "\n".join(header_comments)
            + "\n\n"
            + "\n".join(sorted(mappings, key=str.casefold))
        )
