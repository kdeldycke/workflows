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
``repomatic/data/`` and orchestrates repository bootstrapping via
``repomatic init``.

Available components (``repomatic init <component>``):

- ``workflows`` - Thin-caller workflow files
- ``labels`` - Label definitions (labels.toml + labeller rules)
- ``renovate`` - Renovate dependency update configuration (renovate.json5)
- ``changelog`` - Minimal changelog.md
- ``ruff`` - Merges ``[tool.ruff]`` into pyproject.toml
- ``pytest`` - Merges ``[tool.pytest]`` into pyproject.toml
- ``mypy`` - Merges ``[tool.mypy]`` into pyproject.toml
- ``bumpversion`` - Merges ``[tool.bumpversion]`` into pyproject.toml
- ``skills`` - Claude Code skill definitions (.claude/skills/)
- ``awesome-template`` - Boilerplate for ``awesome-*`` repositories

Selectors use the same ``component[/file]`` syntax as the ``exclude``
config option in ``[tool.repomatic]``.  Qualified entries like
``skills/repomatic-topics`` select a single file within a component.
"""

from __future__ import annotations

import glob as globmod
import logging
import re
import sys
from dataclasses import dataclass, field
from importlib.resources import as_file, files
from pathlib import Path, PurePosixPath
from urllib.request import urlretrieve

from . import __version__
from .config import Config, load_repomatic_config
from .pyproject import resolve_source_paths
from .registry import (
    _BY_NAME,
    COMPONENTS,
    DEFAULT_REPO,
    REUSABLE_WORKFLOWS,
    BundledComponent,
    GeneratedComponent,
    InitDefault,
    RepoScope,
    TemplateComponent,
    ToolConfigComponent,
    WorkflowComponent,
    excluded_rel_path,
    parse_component_entries,
)
from .tool_runner import TOOL_REGISTRY, find_unmodified_configs

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Sequence
    from importlib.abc import Traversable


def _config_flag(config: Config, dotted_key: str, default: bool) -> bool:
    """Look up a boolean config value by its dotted TOML key.

    Converts a dotted kebab-case key (e.g. ``"labels.sync"``) to the
    corresponding ``Config`` field name (``labels_sync``) and returns the
    value via ``getattr``.
    """
    field_name = dotted_key.replace("-", "_").replace(".", "_")
    return getattr(config, field_name, default)


# Exportable files: all registry entries + tool runner bundled defaults.
EXPORTABLE_FILES: dict[str, str | None] = {
    **{f.source: f.target for c in COMPONENTS for f in c.files},
    **{c.source_file: None for c in COMPONENTS if isinstance(c, ToolConfigComponent)},
    # Standalone linter configs from the tool runner (yamllint, zizmor).
    # These are bundled defaults used at runtime, not init components.
    **{
        spec.default_config: None
        for spec in TOOL_REGISTRY.values()
        if spec.default_config
    },
}
"""Registry of all exportable files: maps filename to default output path.

``None`` means stdout (for pyproject.toml templates that need merging).
"""


# ---------------------------------------------------------------------------
# Bundled data access
# ---------------------------------------------------------------------------


def get_data_content(filename: str) -> str:
    """Get the content of a bundled data file.

    This is the low-level function for reading any file from ``repomatic/data/``.

    :param filename: Name of the file to retrieve (e.g., "labels.toml").
    :return: Content of the file as a string.
    :raises FileNotFoundError: If the file doesn't exist.
    """
    data_files = files("repomatic.data")
    with as_file(data_files.joinpath(filename)) as path:
        if path.exists():
            return path.read_text(encoding="UTF-8")

    msg = f"Data file not found: {filename}"
    raise FileNotFoundError(msg)


def _strip_renovate_repo_settings(content: str) -> str:
    """Strip upstream repo-specific settings from a Renovate config.

    Removes ``assignees`` (repo-specific) and the self-referencing uv
    ``customManagers`` entry that targets ``renovate.json5`` itself.

    .. note::
        The self-referencing uv ``customManagers`` entry is excluded because it
        creates an endless update loop in downstream repos: Renovate bumps the
        pinned uv version, the merged PR triggers ``repomatic init``, which
        overwrites ``renovate.json5`` back to the bundled template (reverting
        the bump), and Renovate opens the same PR again — indefinitely. All
        other ``customManagers`` entries are included since they target workflow
        files, not ``renovate.json5`` itself.

    :param content: Raw Renovate config content.
    :return: The config with repo-specific settings removed.
    """
    # Remove assignees line (repo-specific).
    content = re.sub(r"\s*assignees:\s*\[[^\]]*\],?\n", "\n", content)

    # Remove the self-referencing uv customManagers entry (identified by its
    # unique description). This entry targets renovate.json5 itself and causes
    # an endless update loop when synced to downstream repos.
    return re.sub(
        r'\n    \{\n      description: "Update uv version in postUpgradeTasks'
        r' download URL\.",\n.*?\n    \},',
        "",
        content,
        flags=re.DOTALL,
    )


def _get_renovate_config() -> str:
    """Get Renovate config, with repo-specific settings stripped.

    When running from the source repository (via ``uv run``), reads the root
    ``renovate.json5`` and strips repo-specific settings. When installed as a
    package (via ``uvx``), falls back to the pre-processed bundled file in
    ``repomatic/data/renovate.json5``.

    :return: The clean Renovate configuration content.
    """
    root_path = Path(__file__).parent.parent / "renovate.json5"

    # When installed as a package, the root file won't exist.
    # Fall back to the bundled pre-processed version.
    if not root_path.exists():
        return get_data_content("renovate.json5")

    return _strip_renovate_repo_settings(
        root_path.read_text(encoding="UTF-8"),
    )


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


def _find_bumpversion_section_range(content: str) -> tuple[int, int] | None:
    """Find the character range of the entire ``[tool.bumpversion]`` section.

    Locates the section header and all its subsections
    (``[[tool.bumpversion.files]]``, ``[tool.bumpversion.parts.*]``), returning
    the start and end indices.

    :param content: The pyproject.toml content.
    :return: Tuple of (start, end) character indices, or ``None`` if not found.
    """
    header_match = re.search(r"^\[tool\.bumpversion\]\s*$", content, re.MULTILINE)
    if not header_match:
        return None

    start = header_match.start()

    # Find the next section header that is not part of bumpversion.
    # Skips both [tool.bumpversion.X] and [[tool.bumpversion.X]] headers.
    next_section = re.search(
        r"^\[{1,2}(?!tool\.bumpversion[\].])[a-z]",
        content[header_match.end() :],
        re.MULTILINE,
    )
    if next_section:
        end = header_match.end() + next_section.start()
    else:
        end = len(content)

    return start, end


def _update_bumpversion_config(
    content: str,
    pyproject_path: Path,
) -> str | None:
    """Replace an existing ``[tool.bumpversion]`` section from the template.

    Instead of applying incremental migrations, replaces the entire section
    with the canonical template from ``bumpversion.toml``. Only
    ``current_version`` is preserved from the existing config.

    If the existing config does not use dev versioning (no ``parse`` key),
    a ``.dev0`` suffix is appended to ``current_version`` and managed files
    are updated accordingly.

    :param content: The current pyproject.toml content.
    :param pyproject_path: Path to pyproject.toml (for resolving managed files).
    :return: Modified pyproject.toml content, or ``None`` if already up to date.
    """
    section_range = _find_bumpversion_section_range(content)
    if not section_range:
        return None

    # Parse existing config to extract current_version.
    parsed = tomllib.loads(content)
    bv_config = parsed.get("tool", {}).get("bumpversion", {})
    current_version = bv_config.get("current_version", "0.0.0.dev0")

    # Determine if dev versioning migration is needed.
    had_dev_versioning = "parse" in bv_config
    needs_dev_suffix = not had_dev_versioning and not re.search(
        r"\.dev\d+$", current_version
    )
    new_version = f"{current_version}.dev0" if needs_dev_suffix else current_version

    # Generate the replacement section from the template, stripping
    # file-level comments that only apply to the standalone format.
    native_template = export_content("bumpversion.toml")
    native_lines = native_template.splitlines()
    first_key = next(
        i for i, line in enumerate(native_lines) if line and not line.startswith("#")
    )
    native_template = "\n".join(native_lines[first_key:])
    template_section = _to_pyproject_format(native_template, "tool.bumpversion")

    # Replace the placeholder current_version with the project's version.
    template_section = template_section.replace(
        'current_version = "0.0.0.dev0"',
        f'current_version = "{new_version}"',
    )

    # Splice the new section into the content.
    start, end = section_range
    before = content[:start].rstrip()
    after = content[end:].lstrip()

    modified = before + "\n\n" + template_section.strip() + "\n"
    if after:
        modified += "\n" + after

    if modified.strip() == content.strip():
        logging.info("[tool.bumpversion] already up to date.")
        return None

    # If we just added dev versioning, update managed files.
    if needs_dev_suffix and current_version:
        files_entries = bv_config.get("files", [])
        modified = _update_managed_files(
            pyproject_path,
            files_entries,
            current_version,
            new_version,
            modified,
        )

    logging.info("Replaced [tool.bumpversion] from bundled template.")
    return modified


def _update_managed_files(
    pyproject_path: Path,
    files_entries: list[dict[str, str]],
    old_version: str,
    new_version: str,
    pyproject_content: str,
) -> str:
    """Apply version updates to files managed by bumpversion.

    Reads each file entry from ``[[tool.bumpversion.files]]``, interpolates
    ``{current_version}`` and ``{new_version}`` in the search/replace patterns,
    and applies the substitution.

    Updates to ``pyproject.toml`` are applied to ``pyproject_content`` in memory
    (since the caller writes the final content). All other files are written to
    disk directly.

    :param pyproject_path: Path to pyproject.toml.
    :param files_entries: List of file entry dicts from bumpversion config.
    :param old_version: The old version string.
    :param new_version: The new version string.
    :param pyproject_content: The in-memory pyproject.toml content.
    :return: The updated pyproject.toml content.
    """
    project_dir = pyproject_path.parent

    for entry in files_entries:
        search = entry.get("search", "{current_version}")
        replace = entry.get("replace", "{new_version}")

        # Interpolate version placeholders.
        search_str = search.replace("{current_version}", old_version)
        replace_str = replace.replace("{new_version}", new_version)

        # Resolve file paths.
        glob_pattern = entry.get("glob")
        filename = entry.get("filename")

        if glob_pattern:
            # Expand glob relative to project directory.
            paths = [
                Path(p)
                for p in globmod.glob(str(project_dir / glob_pattern), recursive=True)
            ]
        elif filename:
            paths = [project_dir / filename]
        else:
            continue

        for path in paths:
            # pyproject.toml is updated in memory, not on disk.
            if path.resolve() == pyproject_path.resolve():
                if search_str in pyproject_content:
                    pyproject_content = pyproject_content.replace(
                        search_str, replace_str
                    )
                    logging.info(
                        f"Updated version in {path} (in memory): "
                        f"{old_version!r} -> {new_version!r}"
                    )
                continue

            if not path.exists():
                logging.debug(f"Skipping missing file: {path}")
                continue
            file_content = path.read_text(encoding="UTF-8")
            if search_str in file_content:
                updated = file_content.replace(search_str, replace_str)
                path.write_text(updated, encoding="UTF-8")
                logging.info(
                    f"Updated version in {path}: {old_version!r} -> {new_version!r}"
                )

    return pyproject_content


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
    comp = _BY_NAME.get(config_type)
    if not isinstance(comp, ToolConfigComponent):
        supported = ", ".join(
            c.name for c in COMPONENTS if isinstance(c, ToolConfigComponent)
        )
        msg = f"Unknown config type: {config_type!r}. Supported: {supported}"
        raise TypeError(msg)

    if pyproject_path is None:
        pyproject_path = Path("pyproject.toml")

    if not pyproject_path.exists():
        logging.error(f"File not found: {pyproject_path}")
        return None

    content = pyproject_path.read_text(encoding="UTF-8")

    # Check if the config section already exists.
    section_pattern = rf"^\[{re.escape(comp.tool_section)}\]"
    if re.search(section_pattern, content, re.MULTILINE):
        # For bumpversion, try updating existing config with dev versioning.
        if config_type == "bumpversion":
            return _update_bumpversion_config(content, pyproject_path)
        logging.info(f"[{comp.tool_section}] already exists in {pyproject_path.name}")
        return None

    # Get the template content and transform to pyproject.toml format.
    native_template = export_content(comp.source_file)
    template = _to_pyproject_format(native_template, comp.tool_section)

    # Find insertion point using the config's preferences.
    insertion_index = _find_insertion_point(content, comp)

    # Ensure proper spacing.
    before = content[:insertion_index].rstrip()
    after = content[insertion_index:].lstrip()

    # Build the new content with proper newlines.
    new_content = before + "\n\n" + template.strip() + "\n"
    if after:
        new_content += "\n" + after

    return new_content


def _find_insertion_point(content: str, config: ToolConfigComponent) -> int:
    """Find the best insertion point for a config section.

    :param content: The pyproject.toml content.
    :param config: The component whose tool config is being inserted.
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


@dataclass
class InitResult:
    """Result of a repository initialization run."""

    created: list[str] = field(default_factory=list)
    """Relative paths of newly created files."""

    updated: list[str] = field(default_factory=list)
    """Relative paths of existing files overwritten with new content."""

    skipped: list[str] = field(default_factory=list)
    """Relative paths of skipped (already existing) files."""

    excluded: list[str] = field(default_factory=list)
    """Exclude entries that were applied."""

    excluded_existing: list[str] = field(default_factory=list)
    """Relative paths of excluded files that still exist on disk."""

    unmodified_configs: list[str] = field(default_factory=list)
    """Relative paths of config files identical to bundled defaults."""

    warnings: list[str] = field(default_factory=list)
    """Warning messages emitted during initialization."""


def run_init(
    output_dir: Path,
    components: Sequence[str] = (),
    version: str | None = None,
    repo: str = DEFAULT_REPO,
    repo_slug: str | None = None,
    config: Config | None = None,
) -> InitResult:
    """Bootstrap a repository for use with ``kdeldycke/repomatic``.

    Creates thin-caller workflow files, exports configuration files, and
    generates a minimal ``changelog.md`` if missing. Managed files (workflows,
    configs, skills) are always overwritten. User-owned files
    (``changelog.md``, ``zizmor.yaml``) are created once and never overwritten.

    For ``awesome-*`` repositories, the ``awesome-template`` component is
    auto-included when no explicit component selection is made.

    :param output_dir: Root directory of the target repository.
    :param components: Components to initialize. Empty means all defaults.
    :param version: Version pin for upstream workflows (e.g., ``v5.10.0``).
    :param repo: Upstream repository containing reusable workflows.
    :param repo_slug: Repository ``owner/name`` slug for awesome-template URL
        rewriting. Auto-detected via :class:`Metadata` if not provided.
    :return: Summary of created, updated, skipped, and warned items.
    """
    if version is None:
        version = default_version_pin()

    # Parse CLI selection.  Entries may be bare component names (e.g.,
    # "skills") or qualified component/file selectors (e.g.,
    # "skills/repomatic-topics").
    if components:
        selected_full, selected_files = parse_component_entries(
            list(components), context="selection"
        )
        # Bare component name overrides file-level selection for the same
        # component — "skills" means all skills even if "skills/x" also
        # appears.
        for comp in selected_full:
            selected_files.pop(comp, None)
        selected = selected_full | set(selected_files.keys())
    else:
        selected_full = set()
        selected_files = {}
        selected = {
            c.name
            for c in COMPONENTS
            if c.init_default in (InitDefault.INCLUDE, InitDefault.EXCLUDE)
        }
    result = InitResult()

    # Auto-include awesome-template for awesome-* repositories.
    if not repo_slug:
        from .metadata import Metadata

        repo_slug = Metadata().repo_slug
    is_awesome_repo = bool(
        repo_slug and repo_slug.split("/")[-1].startswith("awesome-")
    )
    if is_awesome_repo and not components:
        selected.add("awesome-template")

    # Load config for source path resolution and exclusion rules.
    if config is None:
        config = load_repomatic_config()
    source_paths = resolve_source_paths(config)

    # Parse exclude/include config. User exclude is additive to defaults;
    # user include overrides both.
    user_exclude: list[str] = config.exclude
    user_include: list[str] = config.include
    if user_include:
        parse_component_entries(user_include, context="include")
    default_exclusions = {
        c.name for c in COMPONENTS if c.init_default == InitDefault.EXCLUDE
    }
    exclude_entries = sorted(
        (default_exclusions | set(user_exclude)) - set(user_include)
    )
    excluded_components, excluded_files = parse_component_entries(
        exclude_entries, context="exclude"
    )

    # Apply user-configured exclusions when no explicit components given.
    if not components:
        actually_excluded = excluded_components & selected
        selected -= excluded_components
        result.excluded = sorted(
            list(actually_excluded)
            + [
                f"{c}/{f}"
                for c, fs in sorted(excluded_files.items())
                if c not in actually_excluded
                for f in sorted(fs)
            ]
        )

        # Expand component-level exclusions into file-level entries so
        # detection below is a single unified pass.
        for excl_name in actually_excluded:
            excl_comp = _BY_NAME.get(excl_name)
            if excl_comp and excl_comp.files:
                ids = {e.file_id for e in excl_comp.files}
                excluded_files.setdefault(excl_name, set()).update(ids)

    # Auto-exclude components and files that don't belong in this repository.
    # Added after reporting so they don't appear in "Excluded by config" —
    # they only surface in excluded_existing when the file is actually on
    # disk.  Skip auto-exclusion in the upstream source repo — it is the
    # origin of all bundled files (skills, opt-in workflows, configs).
    scope_excluded_targets: list[str] = []
    if _is_source_repo(output_dir):
        # Bundled components are the source of truth in the upstream repo.
        # Remove them from excluded_files so they are never flagged for
        # deletion.
        for reg_comp in COMPONENTS:
            if reg_comp.files:
                excluded_files.pop(reg_comp.name, None)
    else:
        for reg_comp in COMPONENTS:
            # Component-level scope (e.g., changelog is NON_AWESOME).
            comp_out_of_scope = (
                is_awesome_repo
                and reg_comp.scope == RepoScope.NON_AWESOME
                or (not is_awesome_repo and reg_comp.scope == RepoScope.AWESOME_ONLY)
            )
            if comp_out_of_scope:
                selected.discard(reg_comp.name)
                # For generated components, record the target path so we can
                # detect stale copies on disk below.
                if isinstance(reg_comp, GeneratedComponent) and reg_comp.target:
                    scope_excluded_targets.append(reg_comp.target)
                continue

            # File-level scope and opt-in status.
            for entry in reg_comp.files:
                if (
                    is_awesome_repo
                    and entry.scope == RepoScope.NON_AWESOME
                    or (not is_awesome_repo and entry.scope == RepoScope.AWESOME_ONLY)
                ):
                    excluded_files.setdefault(reg_comp.name, set()).add(entry.file_id)
                if entry.config_key and not _config_flag(
                    config, entry.config_key, entry.config_default
                ):
                    excluded_files.setdefault(reg_comp.name, set()).add(entry.file_id)

    # Detect excluded files that still exist on disk.
    for comp_name, file_ids in sorted(excluded_files.items()):
        for fid in sorted(file_ids):
            rel = excluded_rel_path(comp_name, fid)
            if rel and (output_dir / rel).exists():
                result.excluded_existing.append(rel)
    for rel in sorted(scope_excluded_targets):
        if (output_dir / rel).exists():
            result.excluded_existing.append(rel)

    # Filter out components whose config_key is disabled.
    for reg_comp in COMPONENTS:
        if (
            reg_comp.name in selected
            and reg_comp.config_key
            and not _config_flag(config, reg_comp.config_key, reg_comp.config_default)
        ):
            selected.discard(reg_comp.name)
            logging.info(
                f"[tool.repomatic] {reg_comp.config_key} is disabled."
                f" Skipping {reg_comp.name}."
            )

    # Dispatch by component type.
    tool_configs_to_merge: list[str] = []

    for comp in COMPONENTS:
        if comp.name not in selected:
            continue

        file_exclude = frozenset(excluded_files.get(comp.name, set()))
        file_include = (
            frozenset(selected_files[comp.name])
            if comp.name in selected_files
            else None
        )

        if isinstance(comp, WorkflowComponent):
            _init_workflows(
                output_dir,
                repo,
                version,
                result,
                exclude=file_exclude,
                include=file_include,
                source_paths=source_paths,
                config=config,
            )

        elif isinstance(comp, BundledComponent):
            _init_config_files(
                output_dir,
                comp.name,
                result,
                exclude_ids=file_exclude,
                include_ids=file_include,
            )
            # Labels have extra files fetched from [tool.repomatic] config.
            if comp.name == "labels":
                _fetch_extra_labels(output_dir, result, config=config)

        elif isinstance(comp, TemplateComponent):
            if not repo_slug:
                from .metadata import Metadata

                repo_slug = Metadata().repo_slug
            if repo_slug:
                init_awesome_template(output_dir, repo_slug, result)

        elif isinstance(comp, GeneratedComponent):
            _init_changelog(output_dir, result)

        elif isinstance(comp, ToolConfigComponent):
            tool_configs_to_merge.append(comp.name)

    # Merge tool configs into pyproject.toml (batched for efficiency).
    if tool_configs_to_merge:
        _init_tool_configs(output_dir, tool_configs_to_merge, result)

    # Check for native tool config files identical to bundled defaults.
    # Init-managed files (labels, renovate) are already handled inline by
    # _init_config_files, so only check tool_runner configs here.
    for _tool_name, rel_path in find_unmodified_configs():
        result.unmodified_configs.append(rel_path)
        logging.warning(f"Unmodified config (matches bundled default): {rel_path}")

    return result


def _init_workflows(
    output_dir: Path,
    repo: str,
    version: str,
    result: InitResult,
    *,
    exclude: frozenset[str] = frozenset(),
    include: frozenset[str] | None = None,
    source_paths: list[str] | None = None,
    config: Config | None = None,
) -> None:
    """Generate thin-caller workflows and sync non-reusable workflow headers.

    :param include: When not ``None``, only generate files in this set.
    """
    # Lazy import to avoid circular dependency with workflow_sync.
    from .github.workflow_sync import (
        generate_thin_caller,
        generate_workflow_header,
    )

    workflows = REUSABLE_WORKFLOWS
    if include is not None:
        workflows = tuple(w for w in workflows if w in include)
    if exclude:
        workflows = tuple(w for w in workflows if w not in exclude)

    # Exclude config-gated workflows whose toggle is off.
    if config is None:
        config = load_repomatic_config()
    for entry in _BY_NAME["workflows"].files:
        if (
            entry.config_key
            and entry.file_id in workflows
            and not _config_flag(config, entry.config_key, entry.config_default)
        ):
            workflows = tuple(w for w in workflows if w != entry.file_id)

    workflows_dir = output_dir / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)

    # Generate thin-caller workflows for reusable workflows.
    for filename in workflows:
        target = workflows_dir / filename
        rel = target.relative_to(output_dir).as_posix()
        existed = target.exists()
        content = generate_thin_caller(
            filename, repo, version, source_paths=source_paths
        )
        target.write_text(content, encoding="UTF-8")
        if existed:
            result.updated.append(rel)
            logging.info(f"Updated: {rel}")
        else:
            result.created.append(rel)
            logging.info(f"Created: {rel}")

    # Sync headers for non-reusable workflows that already exist on disk.
    non_reusable = sorted(
        f.file_id for f in _BY_NAME["workflows"].files if not f.reusable
    )
    for filename in non_reusable:
        if include is not None and filename not in include:
            continue
        if exclude and filename in exclude:
            continue
        target = workflows_dir / filename
        if not target.exists():
            continue
        rel = target.relative_to(output_dir).as_posix()
        try:
            canonical_header = generate_workflow_header(
                filename, source_paths=source_paths
            )
        except (ValueError, FileNotFoundError):
            logging.warning(f"Cannot extract header for {filename}. Skipping.")
            continue
        existing = target.read_text(encoding="UTF-8")
        jobs_match = re.search(r"^jobs:", existing, re.MULTILINE)
        if jobs_match is None:
            continue
        content = canonical_header + existing[jobs_match.start() :]
        target.write_text(content, encoding="UTF-8")
        result.updated.append(rel)
        logging.info(f"Synced header: {rel}")


def _is_source_repo(output_dir: Path) -> bool:
    """Detect whether ``output_dir`` is the repomatic source repository root.

    Returns ``True`` when ``output_dir`` contains the ``repomatic`` Python
    package source tree (``repomatic/__init__.py`` and ``repomatic/data/``).
    Only the upstream source repo has these. This prevents auto-exclusion from
    deleting files that are the source of truth (skills, opt-in workflows,
    bundled configs).

    .. note::
        Detection is based on ``output_dir`` contents, not on ``__file__``,
        because ``uvx --from .`` installs the package into a temp venv where
        ``__file__`` no longer points to the source checkout.
    """
    resolved = output_dir.resolve()
    return (resolved / "repomatic" / "__init__.py").exists() and (
        resolved / "repomatic" / "data"
    ).is_dir()


def _is_renovate_source_repo(output_dir: Path) -> bool:
    """Detect whether ``output_dir`` has the upstream renovate config pair.

    Returns ``True`` when the directory is the source repo and contains the
    root ``renovate.json5``. Used by :func:`_init_config_files` to regenerate
    the bundled copy instead of overwriting the root config.
    """
    resolved = output_dir.resolve()
    return _is_source_repo(output_dir) and (resolved / "renovate.json5").exists()


def _init_config_files(
    output_dir: Path,
    component_name: str,
    result: InitResult,
    *,
    exclude_ids: frozenset[str] = frozenset(),
    include_ids: frozenset[str] | None = None,
) -> None:
    """Export bundled config files for a component.

    For components without ``keep_unmodified``, files already on disk that
    are identical to the bundled template are flagged as unmodified and not
    overwritten.

    **Upstream renovate handling:** When running in the repomatic source
    repository, the root ``renovate.json5`` is the authoritative config (it
    contains ``assignees`` and self-referencing ``customManagers``). Instead
    of overwriting it with the stripped template, this function regenerates
    ``repomatic/data/renovate.json5`` — the bundled copy shipped to downstream
    repos.

    :param exclude_ids: File identifiers to skip within this component.
    :param include_ids: When not ``None``, only export files in this set.
    """
    comp = _BY_NAME[component_name]
    for entry in comp.files:
        if include_ids is not None and entry.file_id not in include_ids:
            continue
        if exclude_ids and entry.file_id in exclude_ids:
            continue
        target = output_dir / entry.target
        rel = target.relative_to(output_dir).as_posix()

        # In the repomatic source repo, the root renovate.json5 is
        # authoritative. Read it from output_dir (not __file__-relative,
        # which breaks under uvx), strip repo-specific settings, and
        # regenerate the bundled data copy instead of overwriting the root.
        if component_name == "renovate" and _is_renovate_source_repo(output_dir):
            root_content = (output_dir / entry.source).read_text(encoding="UTF-8")
            normalized = _strip_renovate_repo_settings(root_content).rstrip() + "\n"
            bundled = output_dir / "repomatic" / "data" / entry.source
            existing = bundled.read_text(encoding="UTF-8").rstrip() + "\n"
            bundled_rel = f"repomatic/data/{entry.source}"
            if existing == normalized:
                # Do not mark as unmodified — it is package data, not a
                # user-facing config that can be safely deleted.
                logging.info(f"Bundled config up to date: {bundled_rel}")
            else:
                bundled.write_text(normalized, encoding="UTF-8")
                result.updated.append(bundled_rel)
                logging.info(f"Regenerated bundled config: {bundled_rel}")
            continue

        content = export_content(entry.source)
        # Normalize trailing whitespace to a single newline, matching the
        # convention used by sync commands (echo(content.rstrip(), ...)).
        normalized = content.rstrip() + "\n"

        if target.exists():
            existing = target.read_text(encoding="UTF-8").rstrip() + "\n"
            if not comp.keep_unmodified and existing == normalized:
                result.unmodified_configs.append(rel)
                logging.info(f"Unmodified (matches bundled default): {rel}")
                continue
            target.write_text(normalized, encoding="UTF-8")
            result.updated.append(rel)
            logging.info(f"Updated: {rel}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(normalized, encoding="UTF-8")
            result.created.append(rel)
            logging.info(f"Created: {rel}")


AWESOME_TEMPLATE_SLUG = "kdeldycke/awesome-template"
"""Source slug embedded in bundled awesome-template files, rewritten at sync time."""


def _copy_template_tree(root: Traversable, dest: Path) -> tuple[int, int]:
    """Recursively copy files from a traversable resource tree to disk.

    Skips ``__init__.py`` and ``__pycache__`` entries. Returns
    ``(created, updated)`` counts.
    """
    created = 0
    updated = 0
    for entry in root.iterdir():
        if entry.name in ("__init__.py", "__pycache__"):
            continue
        if entry.is_dir():
            c, u = _copy_template_tree(entry, dest / entry.name)
            created += c
            updated += u
        else:
            target = dest / entry.name
            existed = target.exists()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(entry.read_bytes())
            if existed:
                updated += 1
                logging.info(f"Updated: {target}")
            else:
                created += 1
                logging.info(f"Created: {target}")
    return created, updated


def init_awesome_template(
    output_dir: Path,
    repo_slug: str,
    result: InitResult,
) -> None:
    """Copy bundled awesome-template files and rewrite URLs.

    Copies all files from the ``repomatic/data/awesome_template/`` bundle into
    *output_dir* and rewrites ``kdeldycke/awesome-template`` URLs in
    ``.github/`` markdown and YAML files to match *repo_slug*.

    :param output_dir: Root directory of the target repository.
    :param repo_slug: Target ``owner/name`` slug for URL rewriting.
    :param result: :class:`InitResult` accumulator for created/updated files.
    """
    template_root = files("repomatic.data").joinpath("awesome_template")
    created, updated = _copy_template_tree(template_root, output_dir)
    if created:
        result.created.append(f"awesome-template ({created} files)")
    if updated:
        result.updated.append(f"awesome-template ({updated} files)")

    # Rewrite template URLs in .github/ markdown and YAML files.
    github_dir = output_dir / ".github"
    if github_dir.is_dir():
        for path in github_dir.rglob("*"):
            if not path.is_file() or path.suffix not in (".md", ".yaml", ".yml"):
                continue
            content = path.read_text(encoding="UTF-8")
            new_content = content.replace(
                f"/{AWESOME_TEMPLATE_SLUG}/", f"/{repo_slug}/"
            )
            if new_content != content:
                path.write_text(new_content, encoding="UTF-8")
                logging.info(f"Rewrote URLs in: {path}")


def find_unmodified_init_files() -> list[tuple[str, str]]:
    """Find init-managed config files identical to their bundled defaults.

    Checks bundled components without ``keep_unmodified`` for files on disk
    whose content matches the bundled template (via :func:`export_content`)
    after trailing-whitespace normalization (``.rstrip() + "\\n"``).

    Mirrors the API of :func:`tool_runner.find_unmodified_configs`, returning
    ``(component_name, relative_path)`` tuples.

    :return: List of ``(component_name, relative_path)`` tuples for each
        unmodified file found.
    """
    unmodified: list[tuple[str, str]] = []
    for comp in COMPONENTS:
        if not isinstance(comp, BundledComponent):
            continue
        if comp.keep_unmodified or not comp.files:
            continue
        for entry in comp.files:
            path = Path(entry.target)
            if not path.exists():
                continue
            bundled = export_content(entry.source).rstrip() + "\n"
            on_disk = path.read_text(encoding="UTF-8").rstrip() + "\n"
            if on_disk == bundled:
                unmodified.append((comp.name, entry.target))
    return unmodified


def find_all_unmodified_configs() -> list[tuple[str, str]]:
    """Find all config files identical to their bundled defaults.

    Combines tool configs (yamllint, zizmor, etc.) from
    :func:`tool_runner.find_unmodified_configs` and init-managed configs
    (labels, renovate) from :func:`find_unmodified_init_files`.

    :return: List of ``(label, relative_path)`` tuples for each unmodified
        file found.
    """
    return find_unmodified_configs() + find_unmodified_init_files()


def _init_changelog(
    output_dir: Path,
    result: InitResult,
) -> None:
    """Create a minimal changelog.md if it doesn't exist.

    The changelog stub is only useful for bootstrapping new repositories.
    An existing ``changelog.md`` is never overwritten — it contains real
    release history that would be destroyed by the stub template.
    """
    changelog_path = output_dir / "changelog.md"
    rel = changelog_path.relative_to(output_dir).as_posix()
    if changelog_path.exists():
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
    config: Config | None = None,
) -> None:
    """Download extra label files from ``[tool.repomatic]`` config.

    Reads ``labels.extra-files`` URLs and downloads each file to an
    ``extra-labels/`` subdirectory under ``output_dir``.
    Does nothing if no URLs are configured.
    """
    if config is None:
        config = load_repomatic_config()
    urls = config.labels_extra_files
    if not urls:
        logging.debug("No labels.extra-files configured.")
        return

    target_dir = output_dir / "extra-labels"
    target_dir.mkdir(exist_ok=True)
    for url in urls:
        url = url.strip()
        if not url:
            continue
        filename = PurePosixPath(url).name
        target = target_dir / filename
        rel = target.relative_to(output_dir).as_posix()
        logging.info(f"Downloading {url} -> {target}")
        urlretrieve(url, target)
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
    rel = pyproject_path.relative_to(output_dir).as_posix()
    for config_type in tool_configs:
        tc = _BY_NAME[config_type]
        assert isinstance(tc, ToolConfigComponent)
        section = tc.tool_section
        had_section = re.search(
            rf"^\[{re.escape(section)}\]",
            pyproject_path.read_text(encoding="UTF-8"),
            re.MULTILINE,
        )
        merged = init_config(config_type, pyproject_path)
        if merged is None:
            logging.info(f"[{section}] already up to date, skipped.")
        else:
            pyproject_path.write_text(merged, encoding="UTF-8")
            if had_section:
                logging.info(f"Updated [{section}].")
                if rel not in result.updated:
                    result.updated.append(rel)
            else:
                logging.info(f"Merged [{section}].")
                if rel not in result.created:
                    result.created.append(rel)
