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

"""GitHub Actions utilities.

This module provides utilities for working with GitHub Actions, including
output formatting for ``$GITHUB_OUTPUT``.
"""

from __future__ import annotations

from random import randint


def generate_delimiter() -> str:
    """Generate a unique delimiter for GitHub Actions multiline output.

    GitHub Actions requires a unique delimiter to encode multiline values in
    ``$GITHUB_OUTPUT``. This function generates a random delimiter that is
    extremely unlikely to appear in the output content.

    The delimiter format is ``GHA_DELIMITER_NNNNNNNNN`` where N is a digit,
    producing a 9-digit random suffix.

    :return: A unique delimiter string.

    .. seealso::
        https://github.com/orgs/community/discussions/26288#discussioncomment-3876281
    """
    return f"GHA_DELIMITER_{randint(10**8, (10**9) - 1)}"


def format_multiline_output(name: str, value: str) -> str:
    """Format a multiline value for GitHub Actions output.

    Produces output in the heredoc format required by ``$GITHUB_OUTPUT``:

    .. code-block:: text

        name<<GHA_DELIMITER_NNNNNNNNN
        value line 1
        value line 2
        GHA_DELIMITER_NNNNNNNNN

    :param name: The output variable name.
    :param value: The multiline value.
    :return: Formatted string for ``$GITHUB_OUTPUT``.
    """
    delimiter = generate_delimiter()
    return f"{name}<<{delimiter}\n{value}\n{delimiter}"
