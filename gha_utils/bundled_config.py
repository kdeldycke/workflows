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

"""Bundled configuration templates for pyproject.toml.

This module provides a unified interface for accessing and merging bundled
configuration templates into ``pyproject.toml``. Each configuration type
(ruff, bumpversion, etc.) follows the same pattern:

1. **Export**: Dump the raw template to stdout or a file for inspection.
2. **Init**: Merge the template into ``pyproject.toml`` if the section doesn't exist.

The templates are stored in ``gha_utils/data/`` as TOML files with ``[tool.X]``
sections ready for direct insertion into ``pyproject.toml``.

Supported configuration types:

- ``ruff`` - Ruff linter/formatter configuration (``[tool.ruff]``)
- ``bumpversion`` - bump-my-version configuration (``[tool.bumpversion]``)

CLI usage::

    # Export raw template
    gha-utils config export ruff
    gha-utils config export bumpversion

    # Initialize/merge into pyproject.toml
    gha-utils config init ruff pyproject.toml
    gha-utils config init bumpversion pyproject.toml
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from importlib.resources import as_file, files
from pathlib import Path

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class ConfigType:
    """Metadata for a bundled configuration type."""

    name: str
    """Short identifier used in CLI commands."""

    filename: str
    """Filename in gha_utils/data/ directory."""

    tool_section: str
    """The [tool.X] section name to check for existence."""

    insert_after: Sequence[str]
    """Sections to insert after (in priority order)."""

    insert_before: Sequence[str]
    """Sections to insert before (if insert_after not found)."""

    description: str
    """Human-readable description for help text."""


# Registry of supported configuration types.
CONFIG_TYPES: dict[str, ConfigType] = {
    "ruff": ConfigType(
        name="ruff",
        filename="ruff.toml",
        tool_section="tool.ruff",
        insert_after=("tool.mypy", "tool.mypy.overrides"),
        insert_before=("tool.pytest",),
        description="Ruff linter/formatter configuration",
    ),
    "bumpversion": ConfigType(
        name="bumpversion",
        filename="bumpversion.toml",
        tool_section="tool.bumpversion",
        insert_after=("tool.pytest",),
        insert_before=("tool.typos",),
        description="bump-my-version configuration",
    ),
}


def get_config_content(config_type: str) -> str:
    """Get the content of a bundled configuration template.

    :param config_type: The configuration type (e.g., "ruff", "bumpversion").
    :return: Content of the template as a string.
    :raises ValueError: If the config type is not supported.
    :raises FileNotFoundError: If the template file doesn't exist.
    """
    if config_type not in CONFIG_TYPES:
        supported = ", ".join(CONFIG_TYPES.keys())
        msg = f"Unknown config type: {config_type!r}. Supported: {supported}"
        raise ValueError(msg)

    config = CONFIG_TYPES[config_type]
    data_files = files("gha_utils.data")
    with as_file(data_files.joinpath(config.filename)) as path:
        return path.read_text(encoding="UTF-8")


def init_config(config_type: str, pyproject_path: Path | None = None) -> str | None:
    """Initialize a configuration by merging it into pyproject.toml.

    Reads the pyproject.toml file, checks if the tool section already exists,
    and if not, inserts the bundled template at the appropriate location.

    This function works with the file as text to preserve comments and formatting.

    :param config_type: The configuration type (e.g., "ruff", "bumpversion").
    :param pyproject_path: Path to pyproject.toml. Defaults to ``./pyproject.toml``.
    :return: The modified pyproject.toml content, or ``None`` if no changes needed.
    :raises ValueError: If the config type is not supported.
    """
    if config_type not in CONFIG_TYPES:
        supported = ", ".join(CONFIG_TYPES.keys())
        msg = f"Unknown config type: {config_type!r}. Supported: {supported}"
        raise ValueError(msg)

    config = CONFIG_TYPES[config_type]

    if pyproject_path is None:
        pyproject_path = Path("pyproject.toml")

    if not pyproject_path.exists():
        logging.error(f"File not found: {pyproject_path}")
        return None

    content = pyproject_path.read_text(encoding="UTF-8")

    # Check if the config section already exists.
    section_pattern = rf"^\[{re.escape(config.tool_section)}\]"
    if re.search(section_pattern, content, re.MULTILINE):
        logging.info(
            f"[{config.tool_section}] already exists in {pyproject_path.name}"
        )
        return None

    # Get the template content.
    template = get_config_content(config_type)

    # Find insertion point using the config's preferences.
    insertion_index = _find_insertion_point(content, config)

    # Ensure proper spacing.
    before = content[:insertion_index].rstrip()
    after = content[insertion_index:].lstrip()

    # Build the new content with proper newlines.
    new_content = before + "\n\n" + template.strip() + "\n"
    if after:
        new_content += "\n" + after

    return new_content


def _find_insertion_point(content: str, config: ConfigType) -> int:
    """Find the best insertion point for a config section.

    :param content: The pyproject.toml content.
    :param config: The configuration type metadata.
    :return: The character index where the new section should be inserted.
    """
    # Pattern to match tool sections: [tool.xxx] or [[tool.xxx.yyy]].
    tool_section_pattern = re.compile(r"^\[+tool\.[^\]]+\]+", re.MULTILINE)

    # Find all tool sections and their positions.
    sections = list(tool_section_pattern.finditer(content))

    # Strategy 1: Find insert_after sections and insert after the last one.
    for target in config.insert_after:
        for i, match in enumerate(sections):
            section_name = match.group().strip("[]")
            if section_name == target or section_name.startswith(f"{target}."):
                # Find the next section that isn't a subsection of this one.
                for j in range(i + 1, len(sections)):
                    next_section = sections[j].group().strip("[]")
                    if not next_section.startswith(f"{target}."):
                        return sections[j].start()
                # No more sections, append at end.
                return len(content)

    # Strategy 2: Find insert_before sections and insert before the first one.
    for target in config.insert_before:
        for match in sections:
            section_name = match.group().strip("[]")
            if section_name == target or section_name.startswith(f"{target}."):
                return match.start()

    # Strategy 3: Append at the end.
    return len(content)


# Backwards compatibility aliases for existing code.
def get_bumpversion_content() -> str:
    """Get the content of the bumpversion.toml file.

    .. deprecated::
        Use ``get_config_content("bumpversion")`` instead.

    :return: Content of bumpversion.toml as a string.
    """
    return get_config_content("bumpversion")


def merge_bumpversion_config(pyproject_path: Path | None = None) -> str | None:
    """Merge the bumpversion template into pyproject.toml.

    .. deprecated::
        Use ``init_config("bumpversion", pyproject_path)`` instead.

    :param pyproject_path: Path to pyproject.toml. Defaults to ``./pyproject.toml``.
    :return: The modified pyproject.toml content, or ``None`` if no changes needed.
    """
    return init_config("bumpversion", pyproject_path)


def get_ruff_config_content() -> str:
    """Get the content of the ruff.toml file.

    .. deprecated::
        Use ``get_config_content("ruff")`` instead.

    :return: Content of ruff.toml as a string.
    """
    return get_config_content("ruff")
