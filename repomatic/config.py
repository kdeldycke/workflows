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

"""Configuration schema and loading for ``[tool.repomatic]`` in ``pyproject.toml``.

Defines the ``Config`` dataclass, its TOML serialization helpers, and the
``load_repomatic_config`` function that reads, validates, and returns a typed
``Config`` instance.
"""

from __future__ import annotations

import ast
import inspect
import sys
import textwrap
from dataclasses import dataclass, field, fields
from pathlib import Path
from textwrap import dedent

from click_extra.config import flatten_config_keys, normalize_config_keys

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Any, Final


@dataclass
class Config:
    """Configuration schema for ``[tool.repomatic]`` in ``pyproject.toml``.

    This dataclass defines the structure and default values for repomatic configuration.
    Each field has a docstring explaining its purpose.
    """

    nuitka_enabled: bool = True
    """Whether Nuitka binary compilation is enabled for this project.

    Projects with ``[project.scripts]`` entries that are not intended to produce
    standalone binaries (e.g., libraries with convenience CLI wrappers) can set this
    to ``false`` to opt out of Nuitka compilation.
    """

    nuitka_extra_args: list[str] = field(default_factory=list)
    """Extra Nuitka CLI arguments for binary compilation.

    Project-specific flags (e.g., ``--include-data-files``,
    ``--include-package-data``) that are passed to the Nuitka build command.
    """

    pypi_package_history: list[str] = field(default_factory=list)
    """Former PyPI package names for projects that were renamed.

    When a project changes its PyPI name, older versions remain published under
    the previous name. List former names here so ``lint-changelog`` can fetch
    release metadata from all names and generate correct PyPI URLs.
    """

    nuitka_unstable_targets: list[str] = field(default_factory=list)
    """Nuitka build targets allowed to fail without blocking the release.

    List of target names (e.g., ``["linux-arm64", "windows-x64"]``) that are marked as
    unstable. Jobs for these targets will be allowed to fail without preventing the
    release workflow from succeeding.
    """

    notification_unsubscribe: bool = False
    """Whether the unsubscribe-threads workflow is enabled.

    Notifications are per-user across all repos. Enable on the single repo where
    you want scheduled cleanup of closed notification threads. Requires a classic
    PAT with ``notifications`` scope stored as ``REPOMATIC_NOTIFICATIONS_PAT``.
    """

    awesome_template_sync: bool = True
    """Whether awesome-template sync is enabled for this project.

    Repositories whose name starts with ``awesome-`` get their boilerplate synced
    from files bundled in ``repomatic``. Set to ``false`` to opt out.
    """

    bumpversion_sync: bool = True
    """Whether bumpversion config sync is enabled for this project.

    Projects that manage their own ``[tool.bumpversion]`` section and do not want
    the autofix job to overwrite it can set this to ``false``.
    """

    gitignore_sync: bool = True
    """Whether ``.gitignore`` sync is enabled for this project.

    Projects that manage their own ``.gitignore`` and do not want the autofix job
    to overwrite it can set this to ``false``.
    """

    labels_sync: bool = True
    """Whether label sync is enabled for this project.

    Projects that manage their own repository labels and do not want the
    labels workflow to overwrite them can set this to ``false``.
    """

    mailmap_sync: bool = True
    """Whether ``.mailmap`` sync is enabled for this project.

    Projects that manage their own ``.mailmap`` and do not want the autofix job
    to overwrite it can set this to ``false``.
    """

    dev_release_sync: bool = True
    """Whether dev pre-release sync is enabled for this project.

    Projects that do not want a rolling draft pre-release maintained on
    GitHub can set this to ``false``.
    """

    setup_guide: bool = True
    """Whether the setup guide issue is enabled for this project.

    Projects that do not need ``REPOMATIC_PAT`` or manage their
    own PAT setup can set this to ``false`` to suppress the setup guide issue.
    """

    uv_lock_sync: bool = True
    """Whether ``uv.lock`` sync is enabled for this project.

    Projects that manage their own lock file strategy and do not want the
    ``sync-uv-lock`` job to run ``uv lock --upgrade`` can set this to ``false``.
    """

    workflow_sync: bool = True
    """Whether workflow sync is enabled for this project.

    Projects that manage their own workflow files and do not want the autofix job
    to sync thin callers or headers can set this to ``false``.
    """

    exclude: list[str] = field(default_factory=list)
    """Additional components and files to exclude from repomatic operations.

    Additive to the default exclusions (``labels``, ``skills``). Bare names
    exclude an entire component (e.g., ``"workflows"``). Qualified
    ``component/identifier`` entries exclude a specific file within a component
    (e.g., ``"workflows/debug.yaml"``, ``"skills/repomatic-audit"``,
    ``"labels/labeller-content-based.yaml"``).

    Affects ``repomatic init``, ``workflow sync``, and ``workflow create``.
    Explicit CLI positional arguments override this list.
    """

    include: list[str] = field(default_factory=list)
    """Components and files to force-include, overriding default exclusions.

    Use this to opt into components that are excluded by default (``labels``,
    ``skills``). Each entry is subtracted from the effective exclude set
    (defaults + user ``exclude``). Same syntax as ``exclude``.
    """

    workflow_source_paths: list[str] | None = None
    """Source code directory names for workflow trigger ``paths:`` filters.

    When set, thin-caller and header-only workflows include ``paths:`` filters
    using these directory names (as ``name/**`` globs) alongside universal paths
    like ``pyproject.toml`` and ``uv.lock``.

    When ``None`` (default), source paths are auto-derived from
    ``[project.name]`` in ``pyproject.toml`` by replacing hyphens with
    underscores — the universal Python convention. For example,
    ``name = "extra-platforms"`` automatically uses ``["extra_platforms"]``.
    """

    test_plan_file: str = "./tests/cli-test-plan.yaml"
    """Path to the YAML test plan file for binary testing.

    The test plan file defines a list of test cases to run against compiled binaries.
    Each test case specifies command-line arguments and expected output patterns.
    """

    test_plan_timeout: int | None = None
    """Timeout in seconds for each binary test.

    If set, each test command will be terminated after this duration. ``None`` means no
    timeout (tests can run indefinitely).
    """

    test_plan_inline: str | None = None
    """Inline YAML test plan for binaries.

    Alternative to ``test_plan_file``. Allows specifying the test plan directly in
    ``pyproject.toml`` instead of a separate file.
    """

    gitignore_location: str = "./.gitignore"
    """File path of the ``.gitignore`` to update, relative to the root of the repository.
    """

    gitignore_extra_categories: list[str] = field(default_factory=list)
    """Additional gitignore template categories to fetch from gitignore.io.

    List of template names (e.g., ``["Python", "Node", "Terraform"]``) to combine
    with the generated ``.gitignore`` content.
    """

    gitignore_extra_content: str = field(
        default_factory=lambda: dedent(
            """
            junit.xml

            # Claude Code local settings.
            .claude/settings.local.json
            """
        ).strip()
    )
    """Additional content to append at the end of the generated ``.gitignore`` file.
    """

    dependency_graph_output: str = "./docs/assets/dependencies.mmd"
    """Path where the dependency graph Mermaid diagram should be written.

    The dependency graph visualizes the project's dependency tree in Mermaid format.
    """

    dependency_graph_all_groups: bool = True
    """Whether to include all dependency groups in the graph.

    When ``True``, the ``update-deps-graph`` command behaves as if
    ``--all-groups`` was passed. Projects that want to exclude development
    dependency groups (docs, test, typing) from their published graph can
    set this to ``false``.
    """

    dependency_graph_all_extras: bool = True
    """Whether to include all optional extras in the graph.

    When ``True``, the ``update-deps-graph`` command behaves as if
    ``--all-extras`` was passed.
    """

    dependency_graph_no_groups: list[str] = field(default_factory=list)
    """Dependency groups to exclude from the graph.

    Equivalent to passing ``--no-group`` for each entry. Takes precedence
    over ``dependency-graph.all-groups``.
    """

    dependency_graph_no_extras: list[str] = field(default_factory=list)
    """Optional extras to exclude from the graph.

    Equivalent to passing ``--no-extra`` for each entry. Takes precedence
    over ``dependency-graph.all-extras``.
    """

    dependency_graph_level: int | None = None
    """Maximum depth of the dependency graph.

    ``None`` means unlimited. ``1`` = primary deps only, ``2`` = primary +
    their deps, etc. Equivalent to ``--level``.
    """

    labels_extra_files: list[str] = field(default_factory=list)
    """URLs of additional label definition files (JSON, JSON5, TOML, or YAML).

    Each URL is downloaded and applied separately by ``labelmaker``.
    """

    labels_extra_file_rules: str = ""
    """Additional YAML rules appended to the file-based labeller configuration.

    Appended to the bundled ``labeller-file-based.yaml`` during export.
    """

    labels_extra_content_rules: str = ""
    """Additional YAML rules appended to the content-based labeller configuration.

    Appended to the bundled ``labeller-content-based.yaml`` during export.
    """


SUBCOMMAND_CONFIG_FIELDS: Final[frozenset[str]] = frozenset((
    "awesome_template_sync",
    "bumpversion_sync",
    "dependency_graph_all_extras",
    "dependency_graph_all_groups",
    "dependency_graph_level",
    "dependency_graph_no_extras",
    "dependency_graph_no_groups",
    "dependency_graph_output",
    "dev_release_sync",
    "exclude",
    "include",
    "gitignore_extra_categories",
    "gitignore_extra_content",
    "gitignore_location",
    "gitignore_sync",
    "labels_extra_content_rules",
    "labels_extra_file_rules",
    "labels_extra_files",
    "labels_sync",
    "mailmap_sync",
    "notification_unsubscribe",
    "pypi_package_history",
    "setup_guide",
    "test_plan_file",
    "test_plan_inline",
    "test_plan_timeout",
    "uv_lock_sync",
    "workflow_source_paths",
    "workflow_sync",
))
"""Config fields consumed directly by subcommands, not needed as metadata outputs.

The ``test-plan`` and ``deps-graph`` subcommands now read these values directly from
``[tool.repomatic]`` in ``pyproject.toml``, so they no longer need to be passed through
workflow metadata outputs.
"""


_NESTED_PREFIXES: Final[dict[str, str]] = {
    "awesome_template": "awesome-template",
    "bumpversion": "bumpversion",
    "dependency_graph": "dependency-graph",
    "dev_release": "dev-release",
    "gitignore": "gitignore",
    "labels": "labels",
    "mailmap": "mailmap",
    "notification": "notification",
    "nuitka": "nuitka",
    "renovate": "renovate",
    "test_plan": "test-plan",
    "uv_lock": "uv-lock",
    "workflow": "workflow",
}
"""Map Python field name prefixes to TOML sub-table names.

Fields whose name starts with ``{prefix}_`` are serialized as TOML dotted keys
under the corresponding sub-table (e.g., ``dependency_graph_output`` becomes
``dependency-graph.output``).

.. note::
    Only used for the reverse mapping (field → TOML key) in display and
    documentation. The forward mapping (TOML → field) is handled by
    ``flatten_config_keys`` + ``normalize_config_keys`` from click-extra.
"""


def _field_to_key(name: str) -> str:
    """Convert a ``Config`` field name to its TOML config key.

    Matches the longest prefix in ``_NESTED_PREFIXES`` to produce dotted
    sub-keys (e.g., ``dependency_graph_output`` → ``dependency-graph.output``).
    Falls back to simple kebab-case for flat fields (e.g.,
    ``pypi_package_history`` → ``pypi-package-history``).
    """
    for prefix, toml_prefix in _NESTED_PREFIXES.items():
        if name.startswith(prefix + "_"):
            suffix = name[len(prefix) + 1 :].replace("_", "-")
            return f"{toml_prefix}.{suffix}"
    return name.replace("_", "-")


def _extract_field_docstrings() -> dict[str, str]:
    """Extract attribute docstrings from the ``Config`` dataclass via AST.

    Attribute docstrings are string literals immediately following an annotated
    assignment in a class body (PEP 257 convention). Returns a mapping of field
    name to the first paragraph of its docstring (stripped and dedented).
    """
    source = inspect.getsource(Config)
    tree = ast.parse(textwrap.dedent(source))
    cls_node = tree.body[0]
    assert isinstance(cls_node, ast.ClassDef)

    docstrings: dict[str, str] = {}
    current_field = None
    for node in cls_node.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            current_field = node.target.id
        elif (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            if current_field:
                # Take the first paragraph only.
                full = textwrap.dedent(node.value.value).strip()
                first_para = full.split("\n\n")[0]
                # Collapse internal newlines into a single space.
                docstrings[current_field] = " ".join(first_para.split())
                current_field = None
        else:
            current_field = None

    return docstrings


def _format_default(value: object) -> str:
    """Format a ``Config`` field default for the reference table."""
    if value is None:
        return "*(none)*"
    if isinstance(value, bool):
        return f"`{str(value).lower()}`"
    if isinstance(value, int):
        return f"`{value}`"
    if isinstance(value, str):
        if "\n" in value:
            return "*(see example)*"
        return f'`"{value}"`'
    if isinstance(value, list):
        if not value:
            return "`[]`"
        return f"`{value!r}`"
    return str(value)


def _format_type(annotation: str) -> str:
    """Simplify a type annotation string for the reference table.

    Strips ``| None`` suffixes since the default column already shows whether
    ``None`` is the default.
    """
    return annotation.replace(" | None", "")


CONFIG_REFERENCE_HEADERS = ("Option", "Type", "Default", "Description")
"""Column headers for the ``[tool.repomatic]`` configuration reference table."""


def config_reference() -> list[tuple[str, str, str, str]]:
    """Build the ``[tool.repomatic]`` configuration reference as table rows.

    Introspects the ``Config`` dataclass fields, their type annotations,
    defaults, and attribute docstrings. Returns a list of
    ``(option, type, default, description)`` tuples suitable for
    ``click_extra.table.print_table``.
    """
    schema = Config()
    docstrings = _extract_field_docstrings()
    sorted_fields = sorted(fields(Config), key=lambda f: _field_to_key(f.name))

    rows = []
    for f in sorted_fields:
        key = f"`{_field_to_key(f.name)}`"
        ftype = _format_type(Config.__annotations__[f.name])
        default = _format_default(getattr(schema, f.name))
        # Convert reST double backticks to markdown single backticks.
        desc = docstrings.get(f.name, "").replace("``", "`")
        rows.append((key, ftype, default, desc))

    return rows


def load_repomatic_config(
    pyproject_data: dict[str, Any] | None = None,
) -> Config:
    """Load ``[tool.repomatic]`` config merged with ``Config`` defaults.

    Uses ``flatten_config_keys`` and ``normalize_config_keys`` from click-extra
    to convert nested TOML sub-tables (e.g. ``[tool.repomatic.dependency-graph]``)
    into flat snake_case field names matching the ``Config`` dataclass.

    :param pyproject_data: Pre-parsed ``pyproject.toml`` dict. If ``None``,
        reads and parses ``pyproject.toml`` from the current working directory.
    """
    if pyproject_data is None:
        pyproject_path = Path() / "pyproject.toml"
        if pyproject_path.exists() and pyproject_path.is_file():
            pyproject_data = tomllib.loads(pyproject_path.read_text(encoding="UTF-8"))
        else:
            pyproject_data = {}

    tool_section = pyproject_data.get("tool", {})
    user_config: dict[str, Any] = tool_section.get("repomatic", {})

    flat_user = flatten_config_keys(normalize_config_keys(user_config))
    known = {f.name for f in fields(Config)}
    unknown = sorted(set(flat_user) - known)
    if unknown:
        msg = (
            f"Unknown [tool.repomatic] option(s): "
            f"{', '.join(sorted(unknown))}. "
            f"Valid options: {', '.join(sorted(known))}"
        )
        raise ValueError(msg)

    return Config(**{k: v for k, v in flat_user.items() if k in known})
