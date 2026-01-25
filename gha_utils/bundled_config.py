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

"""Bundled data files and configuration templates.

This module provides a unified interface for accessing bundled data files
from ``gha_utils/data/``. All files can be exported via ``gha-utils config export``.

Exportable files (``gha-utils config export <type>``):

- ``ruff`` - Ruff linter/formatter configuration
- ``bumpversion`` - bump-my-version configuration
- ``labels`` - Label definitions for labelmaker
- ``labeller-file-based`` - Rules for actions/labeler
- ``labeller-content-based`` - Rules for github/issue-labeler
- ``autofix.yaml``, ``autolock.yaml``, ``changelog.yaml``, ``debug.yaml``,
  ``docs.yaml``, ``labels.yaml``, ``lint.yaml``, ``release.yaml``,
  ``renovate.yaml``, ``tests.yaml`` - GitHub Actions workflow templates

Initializable configs (``gha-utils config init <type>``):

Only pyproject.toml-mergeable configs support ``init``:

- ``ruff`` - Merges ``[tool.ruff]`` section
- ``bumpversion`` - Merges ``[tool.bumpversion]`` section
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
class InitConfig:
    """Metadata for configs that can be merged into pyproject.toml."""

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


# Registry of all exportable files: maps filename to default output path.
# None means stdout (for pyproject.toml templates that need merging).
EXPORTABLE_FILES: dict[str, str | None] = {
    # pyproject.toml config templates (no default path, output to stdout for merging).
    "mypy.toml": None,
    "ruff.toml": None,
    "pytest.toml": None,
    "bumpversion.toml": None,
    # Label configuration files.
    "labels.toml": "./labels.toml",
    "labeller-file-based.yaml": "./.github/labeller-file-based.yaml",
    "labeller-content-based.yaml": "./.github/labeller-content-based.yaml",
    # Workflow templates.
    "autofix.yaml": "./.github/workflows/autofix.yaml",
    "autolock.yaml": "./.github/workflows/autolock.yaml",
    "changelog.yaml": "./.github/workflows/changelog.yaml",
    "debug.yaml": "./.github/workflows/debug.yaml",
    "docs.yaml": "./.github/workflows/docs.yaml",
    "labels.yaml": "./.github/workflows/labels.yaml",
    "lint.yaml": "./.github/workflows/lint.yaml",
    "release.yaml": "./.github/workflows/release.yaml",
    "renovate.yaml": "./.github/workflows/renovate.yaml",
    "tests.yaml": "./.github/workflows/tests.yaml",
}

# Registry of configs that support `init` (merging into pyproject.toml).
INIT_CONFIGS: dict[str, InitConfig] = {
    "mypy": InitConfig(
        filename="mypy.toml",
        tool_section="tool.mypy",
        insert_after=("tool.uv",),
        insert_before=("tool.ruff", "tool.pytest"),
        description="Mypy type checking configuration",
    ),
    "ruff": InitConfig(
        filename="ruff.toml",
        tool_section="tool.ruff",
        insert_after=("tool.mypy", "tool.mypy.overrides"),
        insert_before=("tool.pytest",),
        description="Ruff linter/formatter configuration",
    ),
    "pytest": InitConfig(
        filename="pytest.toml",
        tool_section="tool.pytest",
        insert_after=("tool.ruff", "tool.ruff.format"),
        insert_before=("tool.bumpversion",),
        description="Pytest test configuration",
    ),
    "bumpversion": InitConfig(
        filename="bumpversion.toml",
        tool_section="tool.bumpversion",
        insert_after=("tool.pytest",),
        insert_before=("tool.typos",),
        description="bump-my-version configuration",
    ),
}

# Backwards compatibility alias.
CONFIG_TYPES = INIT_CONFIGS


def get_data_content(filename: str) -> str:
    """Get the content of a bundled data file.

    This is the low-level function for reading any file from ``gha_utils/data/``.

    :param filename: Name of the file to retrieve (e.g., "labels.toml").
    :return: Content of the file as a string.
    :raises FileNotFoundError: If the file doesn't exist.
    """
    data_files = files("gha_utils.data")
    with as_file(data_files.joinpath(filename)) as path:
        if path.exists():
            return path.read_text(encoding="UTF-8")

    msg = f"Data file not found: {filename}"
    raise FileNotFoundError(msg)


def export_content(filename: str) -> str:
    """Get the content of any exportable bundled file.

    :param filename: The filename (e.g., "ruff.toml", "labels.toml", "release.yaml").
    :return: Content of the file as a string.
    :raises ValueError: If the file is not in the registry.
    :raises FileNotFoundError: If the file doesn't exist.
    """
    if filename not in EXPORTABLE_FILES:
        supported = ", ".join(EXPORTABLE_FILES.keys())
        msg = f"Unknown file: {filename!r}. Supported: {supported}"
        raise ValueError(msg)

    return get_data_content(filename)


def get_default_output_path(filename: str) -> str | None:
    """Get the default output path for an exportable file.

    :param filename: The filename (e.g., "labels.toml", "release.yaml").
    :return: Default output path, or None if stdout is the default.
    :raises ValueError: If the file is not in the registry.
    """
    if filename not in EXPORTABLE_FILES:
        supported = ", ".join(EXPORTABLE_FILES.keys())
        msg = f"Unknown file: {filename!r}. Supported: {supported}"
        raise ValueError(msg)

    return EXPORTABLE_FILES[filename]


def _to_pyproject_format(template: str, tool_section: str) -> str:
    """Transform native config format to pyproject.toml format.

    Adds the [tool.X] prefix to all sections in the template.

    :param template: The native format template content.
    :param tool_section: The tool section name (e.g., "tool.ruff").
    :return: The transformed content with [tool.X] prefixes.
    """
    lines = template.splitlines()
    result = []
    has_root_section = False

    for line in lines:
        # Match section headers: [section] or [[section]].
        section_match = re.match(r"^(\[+)([^\]]+)(\]+)\s*$", line)
        if section_match:
            brackets_open = section_match.group(1)
            section_name = section_match.group(2)
            brackets_close = section_match.group(3)

            # Transform section name to include tool prefix.
            new_section = f"{tool_section}.{section_name}"
            result.append(f"{brackets_open}{new_section}{brackets_close}")
        else:
            # Non-section line: check if we need to add root section first.
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not has_root_section:
                # First non-comment, non-empty line - add root section.
                result.append(f"[{tool_section}]")
                has_root_section = True
            result.append(line)

    return "\n".join(result)


def init_config(config_type: str, pyproject_path: Path | None = None) -> str | None:
    """Initialize a configuration by merging it into pyproject.toml.

    Reads the pyproject.toml file, checks if the tool section already exists,
    and if not, inserts the bundled template at the appropriate location.

    The template is stored in native format (without [tool.X] prefix) and is
    transformed to pyproject.toml format during insertion.

    This function works with the file as text to preserve comments and formatting.

    :param config_type: The configuration type (e.g., "ruff", "bumpversion").
    :param pyproject_path: Path to pyproject.toml. Defaults to ``./pyproject.toml``.
    :return: The modified pyproject.toml content, or ``None`` if no changes needed.
    :raises ValueError: If the config type is not supported.
    """
    if config_type not in INIT_CONFIGS:
        supported = ", ".join(INIT_CONFIGS.keys())
        msg = f"Unknown config type: {config_type!r}. Supported: {supported}"
        raise ValueError(msg)

    config = INIT_CONFIGS[config_type]

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

    # Get the template content and transform to pyproject.toml format.
    native_template = export_content(config.filename)
    template = _to_pyproject_format(native_template, config.tool_section)

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


def _find_insertion_point(content: str, config: InitConfig) -> int:
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


# ---------------------------------------------------------------------------
# Backwards compatibility aliases (deprecated)
# ---------------------------------------------------------------------------


def get_bumpversion_content() -> str:
    """Get the content of the bumpversion.toml file.

    .. deprecated::
        Use ``export_content("bumpversion.toml")`` instead.
    """
    return export_content("bumpversion.toml")


def merge_bumpversion_config(pyproject_path: Path | None = None) -> str | None:
    """Merge the bumpversion template into pyproject.toml.

    .. deprecated::
        Use ``init_config("bumpversion", pyproject_path)`` instead.
    """
    return init_config("bumpversion", pyproject_path)


def get_ruff_config_content() -> str:
    """Get the content of the ruff.toml file.

    .. deprecated::
        Use ``export_content("ruff.toml")`` instead.
    """
    return export_content("ruff.toml")


def get_labels_content() -> str:
    """Get the content of the labels.toml file.

    .. deprecated::
        Use ``export_content("labels.toml")`` instead.
    """
    return export_content("labels.toml")


def get_file_labeller_rules() -> str:
    """Get the content of the file-based labeller rules.

    .. deprecated::
        Use ``export_content("labeller-file-based.yaml")`` instead.
    """
    return export_content("labeller-file-based.yaml")


def get_content_labeller_rules() -> str:
    """Get the content of the content-based labeller rules.

    .. deprecated::
        Use ``export_content("labeller-content-based.yaml")`` instead.
    """
    return export_content("labeller-content-based.yaml")


def get_config_content(config_type: str) -> str:
    """Get the content of a bundled configuration template.

    .. deprecated::
        Use ``export_content(f"{config_type}.toml")`` instead.
    """
    # Map old-style names to new filenames.
    filename = f"{config_type}.toml"
    return export_content(filename)


# Workflow files constant for backwards compatibility.
WORKFLOW_FILES = tuple(k for k in EXPORTABLE_FILES if k.endswith(".yaml"))


def list_workflows() -> tuple[str, ...]:
    """List all available workflow templates.

    .. deprecated::
        Use ``EXPORTABLE_FILES`` and filter for .yaml files instead.
    """
    return WORKFLOW_FILES


def get_workflow_content(filename: str) -> str:
    """Get the content of a workflow template.

    .. deprecated::
        Use ``export_content(filename)`` instead.
    """
    return export_content(filename)
