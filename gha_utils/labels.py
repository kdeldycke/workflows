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

"""Access bundled label configuration files.

This module provides access to label definitions and labeller rules that are
bundled with the package. The source files live in ``.github/`` for linting
and formatting, but are copied into the package at build time.

Files available:

- ``labels.toml`` - Label definitions for labelmaker
- ``labeller-file-based.yaml`` - Rules for actions/labeler (file-based PR labelling)
- ``labeller-content-based.yaml`` - Rules for github/issue-labeler (content-based labelling)
"""

from __future__ import annotations

from importlib.resources import as_file, files
from pathlib import Path


def _get_data_content(filename: str) -> str:
    """Get the content of a bundled data file.

    During development (editable install), falls back to reading from ``.github/``.

    :param filename: Name of the file to retrieve.
    :return: Content of the file as a string.
    :raises FileNotFoundError: If the file doesn't exist.
    """
    # Try to get from package data first (installed package).
    try:
        data_files = files("gha_utils.data")
        with as_file(data_files.joinpath(filename)) as path:
            if path.exists():
                # Read inside context manager before path becomes invalid.
                return path.read_text(encoding="UTF-8")
    except (ModuleNotFoundError, TypeError):
        pass

    # Fall back to .github/ directory (development/editable install).
    # Map data filenames back to their .github/ locations.
    github_mapping = {
        "labels.toml": ".github/labels.toml",
        "labeller-file-based.yaml": ".github/labeller-file-based.yaml",
        "labeller-content-based.yaml": ".github/labeller-content-based.yaml",
    }

    if filename in github_mapping:
        # Find the repository root by looking for pyproject.toml.
        current = Path(__file__).resolve().parent
        for _ in range(5):  # Limit search depth.
            candidate = current / github_mapping[filename]
            if candidate.exists():
                return candidate.read_text(encoding="UTF-8")
            current = current.parent

    msg = f"Data file not found: {filename}"
    raise FileNotFoundError(msg)


def get_labels_content() -> str:
    """Get the content of the labels.toml file.

    :return: Content of labels.toml as a string.
    """
    return _get_data_content("labels.toml")


def get_file_labeller_rules() -> str:
    """Get the content of the file-based labeller rules.

    :return: Content of labeller-file-based.yaml as a string.
    """
    return _get_data_content("labeller-file-based.yaml")


def get_content_labeller_rules() -> str:
    """Get the content of the content-based labeller rules.

    :return: Content of labeller-content-based.yaml as a string.
    """
    return _get_data_content("labeller-content-based.yaml")
