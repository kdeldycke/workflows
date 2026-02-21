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
"""Expose package-wide elements."""

from __future__ import annotations

import subprocess

__version__ = "5.11.1"


def _dev_version() -> str:
    """Return version string with git SHA appended for dev versions.

    For development versions (containing ``.dev``), appends the short git
    commit hash as a PEP 440 local version identifier (e.g.,
    ``5.1.0.dev0+abc1234``). For release versions, returns the version
    as-is.

    .. todo::
        Contribute this as a generic feature for Click Extra, and reuse it here.
    """
    if ".dev" not in __version__:
        return __version__
    try:
        result = subprocess.run(
            ("git", "rev-parse", "--short", "HEAD"),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return f"{__version__}+{result.stdout.strip()}"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return __version__
