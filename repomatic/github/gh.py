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

"""Generic wrapper for the ``gh`` CLI."""

from __future__ import annotations

import logging
from subprocess import run


def run_gh_command(args: list[str]) -> str:
    """Run a ``gh`` CLI command and return stdout.

    :param args: Command arguments to pass to ``gh``.
    :return: The stdout output from the command.
    :raises RuntimeError: If the command fails.
    """
    cmd = ["gh", *args]
    logging.debug(f"Running: {' '.join(cmd)}")
    process = run(cmd, capture_output=True, encoding="UTF-8")

    if process.returncode:
        logging.debug(f"gh command failed: {process.stderr}")
        raise RuntimeError(process.stderr)

    return process.stdout
