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

"""Access bundled bumpversion configuration template.

This module provides access to a default ``[tool.bumpversion]`` configuration
that can be added to ``pyproject.toml``. The source file lives in ``.github/``
for organization, but is copied into the package at build time.

Files available:

- ``bumpversion.toml`` - Default bumpversion configuration for bump-my-version
"""

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 9):
    from importlib.resources import as_file, files
else:
    from importlib_resources import as_file, files  # type: ignore[import-not-found]


def _get_data_path() -> Path:
    """Get the path to the bundled bumpversion.toml file.

    During development (editable install), falls back to reading from ``.github/``.

    :return: Path to the file.
    :raises FileNotFoundError: If the file doesn't exist.
    """
    # Try to get from package data first (installed package).
    try:
        data_files = files("gha_utils.data")
        with as_file(data_files.joinpath("bumpversion.toml")) as path:
            if path.exists():
                return path
    except (ModuleNotFoundError, TypeError):
        pass

    # Fall back to .github/ directory (development/editable install).
    current = Path(__file__).resolve().parent
    for _ in range(5):  # Limit search depth.
        candidate = current / ".github" / "bumpversion.toml"
        if candidate.exists():
            return candidate
        current = current.parent

    msg = "Data file not found: bumpversion.toml"
    raise FileNotFoundError(msg)


def get_bumpversion_content() -> str:
    """Get the content of the bumpversion.toml file.

    :return: Content of bumpversion.toml as a string.
    """
    return _get_data_path().read_text(encoding="UTF-8")
