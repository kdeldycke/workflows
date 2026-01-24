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

.. note::
    This module is named ``version_config`` instead of ``bumpversion`` to avoid
    shadowing the external ``bumpversion`` package from ``bump-my-version``. When
    compiled with Nuitka, a local ``bumpversion.py`` would take precedence over
    the installed package, breaking imports like ``from bumpversion.config import ...``.
"""

from __future__ import annotations

import logging
import re
from importlib.resources import as_file, files
from pathlib import Path


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


def merge_bumpversion_config(pyproject_path: Path | None = None) -> str | None:
    """Merge the bumpversion template into pyproject.toml.

    Reads the pyproject.toml file, checks if ``[tool.bumpversion]`` already exists,
    and if not, inserts the bundled template at the appropriate location (after
    ``[tool.pytest]`` and before ``[tool.typos]``).

    This function works with the file as text to preserve comments and formatting.

    :param pyproject_path: Path to pyproject.toml. Defaults to ``./pyproject.toml``.
    :return: The modified pyproject.toml content, or ``None`` if no changes needed.
    """
    if pyproject_path is None:
        pyproject_path = Path("pyproject.toml")

    if not pyproject_path.exists():
        logging.error(f"File not found: {pyproject_path}")
        return None

    content = pyproject_path.read_text(encoding="UTF-8")

    # Check if bumpversion config already exists.
    if re.search(r"^\[tool\.bumpversion\]", content, re.MULTILINE):
        logging.info("Bumpversion configuration already exists in pyproject.toml")
        return None

    # Get the template content.
    template = get_bumpversion_content()

    # Find insertion point. Priority order:
    # 1. After [tool.pytest] section (before the next [tool.*] or [[tool.*]] section)
    # 2. Before [tool.typos] section
    # 3. At the end of the file

    # Pattern to match tool sections: [tool.xxx] or [[tool.xxx.yyy]].
    tool_section_pattern = re.compile(r"^\[+tool\.[^\]]+\]+", re.MULTILINE)

    # Find all tool sections and their positions.
    sections = list(tool_section_pattern.finditer(content))

    insertion_index = None

    # Strategy 1: Find [tool.pytest] and insert after its section.
    for i, match in enumerate(sections):
        if match.group().startswith("[tool.pytest]"):
            # Insert before the next section.
            if i + 1 < len(sections):
                insertion_index = sections[i + 1].start()
            else:
                # [tool.pytest] is the last section, append at end.
                insertion_index = len(content)
            break

    # Strategy 2: If no [tool.pytest], find [tool.typos] and insert before it.
    if insertion_index is None:
        for match in sections:
            if match.group().startswith("[tool.typos]"):
                insertion_index = match.start()
                break

    # Strategy 3: Append at the end.
    if insertion_index is None:
        insertion_index = len(content)

    # Ensure proper spacing.
    before = content[:insertion_index].rstrip()
    after = content[insertion_index:].lstrip()

    # Build the new content with proper newlines.
    new_content = before + "\n\n" + template.strip() + "\n"
    if after:
        new_content += "\n" + after

    return new_content
