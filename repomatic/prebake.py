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
"""Pre-bake development versions with Git commit hashes.

Rewrites ``__version__`` in Python source files so that ``.dev`` versions
include a `PEP 440 local version identifier
<https://peps.python.org/pep-0440/#local-version-identifiers>`_ with the
Git short hash.  This is intended to run **before** Nuitka compilation so
that standalone binaries report the exact commit they were built from, even
though ``git`` is unavailable at runtime.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

# Matches: __version__ = "1.2.3.dev0"  (with optional single/double quotes)
_VERSION_RE = re.compile(
    r'^(?P<prefix>__version__\s*=\s*["\'])(?P<version>[^"\']+)(?P<suffix>["\'])$',
    re.MULTILINE,
)


def prebake_version(file_path: Path, git_hash: str) -> str | None:
    """Pre-bake a ``__version__`` string with a Git hash.

    Reads *file_path*, finds the ``__version__`` assignment, and — if the
    version contains ``.dev`` and does not already contain ``+`` — appends
    ``+<git_hash>``.

    Returns the new version string on success, or ``None`` if no change was
    made (release version, already pre-baked, or no ``__version__`` found).
    """
    source = file_path.read_text(encoding="utf-8")

    match = _VERSION_RE.search(source)
    if not match:
        logging.warning(f"No __version__ found in {file_path}")
        return None

    version = match.group("version")

    if ".dev" not in version:
        logging.info(f"Release version {version!r} in {file_path} — skipping.")
        return None

    if "+" in version:
        logging.info(
            f"Version {version!r} in {file_path} already has a local identifier"
            " — skipping."
        )
        return None

    new_version = f"{version}+{git_hash}"
    new_line = f"{match.group('prefix')}{new_version}{match.group('suffix')}"
    new_source = source[: match.start()] + new_line + source[match.end() :]
    file_path.write_text(new_source, encoding="utf-8")

    logging.info(f"Pre-baked {file_path}: {version!r} → {new_version!r}")
    return new_version
