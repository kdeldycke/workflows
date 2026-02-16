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

"""Bundled data files, configuration templates, and repository initialization.

Provides a unified interface for accessing bundled data files from
``gha_utils/data/`` and orchestrates repository bootstrapping via
``gha-utils init``.

Available components (``gha-utils init <component>``):

- ``workflows`` - Thin-caller workflow files
- ``labels`` - Label definitions (labels.toml + labeller rules)
- ``renovate`` - Renovate dependency update configuration (renovate.json5)
- ``changelog`` - Minimal changelog.md
- ``ruff`` - Merges ``[tool.ruff]`` into pyproject.toml
- ``pytest`` - Merges ``[tool.pytest]`` into pyproject.toml
- ``mypy`` - Merges ``[tool.mypy]`` into pyproject.toml
- ``bumpversion`` - Merges ``[tool.bumpversion]`` into pyproject.toml
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from importlib.resources import as_file, files
from pathlib import Path, PurePosixPath
from urllib.request import urlretrieve

from . import __version__

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Sequence

DEFAULT_REPO: str = "kdeldycke/workflows"
"""Default upstream repository for reusable workflows."""


# ---------------------------------------------------------------------------
# Bundled data access
# ---------------------------------------------------------------------------


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
    # Renovate configuration.
    "renovate.json5": "./renovate.json5",
    # Label configuration files.
    "labels.toml": "./labels.toml",
    "labeller-file-based.yaml": "./.github/labeller-file-based.yaml",
    "labeller-content-based.yaml": "./.github/labeller-content-based.yaml",
    # Workflow templates.
    "autofix.yaml": "./.github/workflows/autofix.yaml",
    "autolock.yaml": "./.github/workflows/autolock.yaml",
    "cancel-runs.yaml": "./.github/workflows/cancel-runs.yaml",
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
# The insert_after/insert_before values follow pyproject-fmt's section ordering.
INIT_CONFIGS: dict[str, InitConfig] = {
    "ruff": InitConfig(
        filename="ruff.toml",
        tool_section="tool.ruff",
        insert_after=("tool.uv", "tool.uv.build-backend"),
        insert_before=("tool.pytest",),
        description="Ruff linter/formatter configuration",
    ),
    "pytest": InitConfig(
        filename="pytest.toml",
        tool_section="tool.pytest",
        insert_after=("tool.ruff", "tool.ruff.format"),
        insert_before=("tool.mypy",),
        description="Pytest test configuration",
    ),
    "mypy": InitConfig(
        filename="mypy.toml",
        tool_section="tool.mypy",
        insert_after=("tool.pytest",),
        insert_before=("tool.nuitka", "tool.bumpversion"),
        description="Mypy type checking configuration",
    ),
    "bumpversion": InitConfig(
        filename="bumpversion.toml",
        tool_section="tool.bumpversion",
        insert_after=("tool.nuitka", "tool.mypy"),
        insert_before=("tool.typos",),
        description="bump-my-version configuration",
    ),
}


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


def _get_renovate_config() -> str:
    """Get Renovate config, with repo-specific settings stripped.

    When running from the source repository, reads the root ``renovate.json5``
    and removes repo-specific settings (``customManagers``, ``assignees``).

    When installed as a package, falls back to the pre-processed bundled file
    in ``gha_utils/data/renovate.json5``.

    :return: The clean Renovate configuration content.
    """
    root_path = Path(__file__).parent.parent / "renovate.json5"

    # When installed as a package, the root file won't exist.
    # Fall back to the bundled pre-processed version.
    if not root_path.exists():
        return get_data_content("renovate.json5")

    content = root_path.read_text(encoding="UTF-8")

    # Remove assignees line.
    content = re.sub(r"\s*assignees:\s*\[[^\]]*\],?\n", "\n", content)

    # Remove customManagers section and its preceding comment.
    # Find where customManagers starts (including its comment).
    cm_match = re.search(
        r"\n\s*//[^\n]*[Cc]ustom [Mm]anagers[^\n]*\n\s*customManagers:", content
    )
    if cm_match:
        # Find the closing of vulnerabilityAlerts (the section before customManagers).
        # Keep everything up to and including that closing brace and comma.
        va_end = re.search(r"(vulnerabilityAlerts:\s*\{[^}]*\},?\s*)\n", content)
        if va_end:
            # Keep content up to end of vulnerabilityAlerts, then close the object.
            content = content[: va_end.end()].rstrip().rstrip(",") + "\n}\n"

    return content


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

    # Special handling for renovate.json5: read from root and strip
    # repo-specific settings.
    if filename == "renovate.json5":
        return _get_renovate_config()

    return get_data_content(filename)


# ---------------------------------------------------------------------------
# pyproject.toml config merging
# ---------------------------------------------------------------------------


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
        logging.info(f"[{config.tool_section}] already exists in {pyproject_path.name}")
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
# Repository initialization
# ---------------------------------------------------------------------------


def default_version_pin() -> str:
    """Derive the default version pin from ``__version__``.

    Strips any ``.dev0`` suffix and prefixes with ``v``. For example,
    ``"5.10.0.dev0"`` becomes ``"v5.10.0"``.
    """
    version = re.sub(r"\.dev\d*$", "", __version__)
    return f"v{version}"


# Components that generate files (not tool config merges).
FILE_COMPONENTS: dict[str, str] = {
    "changelog": "Minimal changelog.md",
    "labels": "Label config files (labels.toml + labeller rules)",
    "renovate": "Renovate config (renovate.json5)",
    "workflows": "Thin-caller workflow files",
}
"""Components that create files during init, with descriptions."""

# Tool config components that merge into pyproject.toml.
TOOL_COMPONENTS: dict[str, str] = {
    k: v.description for k, v in INIT_CONFIGS.items()
}
"""Tool config components merged into pyproject.toml during init."""

ALL_COMPONENTS: dict[str, str] = {**FILE_COMPONENTS, **TOOL_COMPONENTS}
"""All available init components."""

DEFAULT_COMPONENTS: tuple[str, ...] = tuple(sorted(FILE_COMPONENTS.keys()))
"""Components included when no explicit selection is made."""

# Maps component names to (source filename, relative output path) tuples.
COMPONENT_FILES: dict[str, tuple[tuple[str, str], ...]] = {
    "labels": (
        ("labeller-content-based.yaml", ".github/labeller-content-based.yaml"),
        ("labeller-file-based.yaml", ".github/labeller-file-based.yaml"),
        ("labels.toml", "labels.toml"),
    ),
    "renovate": (
        ("renovate.json5", "renovate.json5"),
    ),
}
"""Bundled config files per component, with their output paths."""


@dataclass
class InitResult:
    """Result of a repository initialization run."""

    created: list[str] = field(default_factory=list)
    """Relative paths of created files."""

    skipped: list[str] = field(default_factory=list)
    """Relative paths of skipped (already existing) files."""

    warnings: list[str] = field(default_factory=list)
    """Warning messages emitted during initialization."""


def run_init(
    output_dir: Path,
    components: Sequence[str] = (),
    version: str | None = None,
    repo: str = DEFAULT_REPO,
    overwrite: bool = False,
) -> InitResult:
    """Bootstrap a repository for use with ``kdeldycke/workflows``.

    Creates thin-caller workflow files, exports configuration files, and
    generates a minimal ``changelog.md`` if missing. By default, existing
    files are skipped; use ``overwrite=True`` to replace them.

    :param output_dir: Root directory of the target repository.
    :param components: Components to initialize. Empty means all defaults.
    :param version: Version pin for upstream workflows (e.g., ``v5.10.0``).
    :param repo: Upstream repository containing reusable workflows.
    :param overwrite: Overwrite existing files instead of skipping.
    :return: Summary of created, skipped, and warned items.
    """
    if version is None:
        version = default_version_pin()

    selected = set(components) if components else set(DEFAULT_COMPONENTS)
    result = InitResult()

    # Workflows.
    if "workflows" in selected:
        _init_workflows(output_dir, repo, version, overwrite, result)

    # Config file components (labels, renovate).
    for component_name in ("labels", "renovate"):
        if component_name in selected:
            _init_config_files(output_dir, component_name, overwrite, result)

    # Fetch extra label files from [tool.gha-utils] config.
    if "labels" in selected:
        _fetch_extra_labels(output_dir, result)

    # Changelog.
    if "changelog" in selected:
        _init_changelog(output_dir, overwrite, result)

    # Tool configs (merged into pyproject.toml).
    tool_configs = selected & set(INIT_CONFIGS.keys())
    if tool_configs:
        _init_tool_configs(output_dir, sorted(tool_configs), result)

    return result


def _init_workflows(
    output_dir: Path,
    repo: str,
    version: str,
    overwrite: bool,
    result: InitResult,
) -> None:
    """Generate thin-caller workflow files."""
    # Lazy import to avoid circular dependency with workflow_sync.
    from .github.workflow_sync import REUSABLE_WORKFLOWS, generate_thin_caller

    workflows_dir = output_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    for filename in REUSABLE_WORKFLOWS:
        target = workflows_dir / filename
        rel = str(target.relative_to(output_dir))
        if target.exists() and not overwrite:
            result.skipped.append(rel)
            logging.debug(f"Skipped existing: {rel}")
            continue
        content = generate_thin_caller(filename, repo, version)
        target.write_text(content, encoding="UTF-8")
        result.created.append(rel)
        logging.info(f"Created: {rel}")


def _init_config_files(
    output_dir: Path,
    component_name: str,
    overwrite: bool,
    result: InitResult,
) -> None:
    """Export bundled config files for a component."""
    for source_name, rel_path in COMPONENT_FILES[component_name]:
        target = output_dir / rel_path
        rel = str(target.relative_to(output_dir))
        if target.exists() and not overwrite:
            result.skipped.append(rel)
            logging.debug(f"Skipped existing: {rel}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        content = export_content(source_name)
        target.write_text(content, encoding="UTF-8")
        result.created.append(rel)
        logging.info(f"Created: {rel}")


def _init_changelog(
    output_dir: Path,
    overwrite: bool,
    result: InitResult,
) -> None:
    """Create a minimal changelog.md."""
    changelog_path = output_dir / "changelog.md"
    rel = str(changelog_path.relative_to(output_dir))
    if changelog_path.exists() and not overwrite:
        result.skipped.append(rel)
        logging.debug(f"Skipped existing: {rel}")
        return
    changelog_content = (
        "# Changelog\n"
        "\n"
        "## [Unreleased](https://github.com/USER/REPO/compare/main...main)\n"
    )
    changelog_path.write_text(changelog_content, encoding="UTF-8")
    result.created.append(rel)
    logging.info(f"Created: {rel}")


def _fetch_extra_labels(
    output_dir: Path,
    result: InitResult,
) -> None:
    """Download extra label files from ``[tool.gha-utils]`` config.

    Reads ``extra-label-files`` URLs and downloads each file to an
    ``extra-labels/`` subdirectory under ``output_dir``.
    Does nothing if no URLs are configured.
    """
    # Lazy import to avoid circular dependency.
    from .metadata import load_gha_utils_config

    config = load_gha_utils_config()
    urls = config.get("extra-label-files", [])
    if not urls:
        logging.debug("No extra-label-files configured.")
        return

    target_dir = output_dir / "extra-labels"
    target_dir.mkdir(exist_ok=True)
    for url in urls:
        url = url.strip()
        if not url:
            continue
        filename = PurePosixPath(url).name
        target = target_dir / filename
        rel = str(target.relative_to(output_dir))
        logging.info(f"Downloading {url} -> {target}")
        urlretrieve(url, target)  # noqa: S310
        result.created.append(rel)


def _init_tool_configs(
    output_dir: Path,
    tool_configs: Sequence[str],
    result: InitResult,
) -> None:
    """Merge selected tool configs into pyproject.toml."""
    pyproject_path = output_dir / "pyproject.toml"
    if not pyproject_path.exists():
        result.warnings.append(
            "pyproject.toml not found; skipping tool config initialization."
        )
        logging.warning(result.warnings[-1])
        return
    for config_type in tool_configs:
        merged = init_config(config_type, pyproject_path)
        if merged is None:
            logging.info(
                f"[{INIT_CONFIGS[config_type].tool_section}] already exists, skipped."
            )
        else:
            pyproject_path.write_text(merged, encoding="UTF-8")
            logging.info(f"Merged [{INIT_CONFIGS[config_type].tool_section}].")
