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
"""Declarative registry of all components managed by the ``init`` subcommand.

Every resource the ``init`` subcommand can create, sync, or merge is declared
here as a :class:`Component` instance in the :data:`COMPONENTS` tuple. Each
component carries all its metadata: what kind it is, whether it is selected by
default, which files it manages, and any per-file properties like repo-scope
gating or opt-in keys.

All legacy constants (``ALL_COMPONENTS``, ``COMPONENT_FILES``,
``DEFAULT_EXCLUSIONS``, ``INIT_CONFIGS``, ``REUSABLE_WORKFLOWS``, etc.) are
computed from this single registry in :mod:`repomatic.init_project`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class ComponentKind(Enum):
    """How the component delivers files to the target repository."""

    BUNDLED = auto()
    """Files copied from ``repomatic/data/`` to target path."""

    TOOL_CONFIG = auto()
    """Merged into ``pyproject.toml``."""

    WORKFLOW = auto()
    """Thin-caller generation and header sync."""

    TEMPLATE = auto()
    """Directory tree (awesome-template)."""

    GENERATED = auto()
    """Produced from code (changelog)."""


class InitDefault(Enum):
    """How ``init`` treats the component when no explicit CLI args are given."""

    INCLUDE = auto()
    """Included by default (e.g., changelog, renovate, workflows)."""

    EXCLUDE = auto()
    """In default set but excluded unless explicitly included
    (e.g., labels, skills)."""

    AUTO = auto()
    """Auto-included only for matching repos (e.g., awesome-template)."""

    EXPLICIT = auto()
    """Only included when explicitly requested (e.g., tool configs)."""


class RepoScope(Enum):
    """Which repository types a file entry applies to."""

    ALL = auto()
    """Included in all repository types."""

    AWESOME_ONLY = auto()
    """Only for awesome-* repositories."""

    NON_AWESOME = auto()
    """Only for non-awesome repositories."""


@dataclass(frozen=True)
class FileEntry:
    """A single file managed within a component.

    :param source: Filename in ``repomatic/data/``.
    :param target: Relative output path in the target repository.
        Defaults to ``source`` (root-level file).
    :param file_id: Identifier for file-level ``--include``/``--exclude``.
        Defaults to the filename portion of ``target``.
    :param scope: Which repository types get this file.
    :param opt_in_key: ``[tool.repomatic]`` key that must be ``true`` to
        include this entry.
    :param reusable: Workflow-specific: supports ``workflow_call`` trigger.
    :param phase: Skill-specific: lifecycle phase for ``list-skills`` display.
    """

    source: str
    target: str = ""
    file_id: str = ""
    scope: RepoScope = RepoScope.ALL
    opt_in_key: str = ""
    reusable: bool = True
    phase: str = ""

    def __post_init__(self) -> None:
        """Derive ``target`` and ``file_id`` from ``source`` when omitted."""
        if not self.target:
            object.__setattr__(self, "target", self.source)
        if not self.file_id:
            object.__setattr__(
                self, "file_id", self.target.rsplit("/", 1)[-1]
            )


@dataclass(frozen=True)
class Component:
    """A group of related resources managed by the ``init`` subcommand.

    :param name: Component name used on the CLI (e.g., ``"skills"``).
    :param description: Human-readable description for help text.
    :param kind: How files are delivered to the target repository.
    :param init_default: How ``init`` treats this component when no explicit
        CLI selection is made.
    :param files: File entries this component manages.
    :param check_redundancy: Check files for byte-for-byte match with bundled
        defaults (labels, renovate). Skills excluded because they are
        user-facing documents, not machine configs.
    :param source_file: Filename in ``repomatic/data/``
        (``TOOL_CONFIG`` kind only).
    :param tool_section: The ``[tool.X]`` section name to check for
        existence (``TOOL_CONFIG`` kind only).
    :param insert_after: Sections to insert after in ``pyproject.toml``
        (``TOOL_CONFIG`` kind only, in priority order).
    :param insert_before: Sections to insert before in ``pyproject.toml``
        (``TOOL_CONFIG`` kind only, if ``insert_after`` not found).
    """

    name: str
    description: str
    kind: ComponentKind
    init_default: InitDefault = InitDefault.INCLUDE
    files: tuple[FileEntry, ...] = ()
    check_redundancy: bool = False
    source_file: str = ""
    tool_section: str = ""
    insert_after: tuple[str, ...] = ()
    insert_before: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# The registry.
# ---------------------------------------------------------------------------

COMPONENTS: tuple[Component, ...] = (
    # --- Bundled file components ---
    Component(
        name="labels",
        description="Label config files (labels.toml + labeller rules)",
        kind=ComponentKind.BUNDLED,
        init_default=InitDefault.EXCLUDE,
        check_redundancy=True,
        files=(
            FileEntry(
                "labeller-content-based.yaml",
                ".github/labeller-content-based.yaml",
            ),
            FileEntry(
                "labeller-file-based.yaml",
                ".github/labeller-file-based.yaml",
            ),
            FileEntry("labels.toml"),
        ),
    ),
    Component(
        name="renovate",
        description="Renovate config (renovate.json5)",
        kind=ComponentKind.BUNDLED,
        check_redundancy=True,
        files=(FileEntry("renovate.json5"),),
    ),
    Component(
        name="skills",
        description="Claude Code skill definitions (.claude/skills/)",
        kind=ComponentKind.BUNDLED,
        init_default=InitDefault.EXCLUDE,
        files=(
            FileEntry(
                "skill-awesome-triage.md",
                ".claude/skills/awesome-triage/SKILL.md",
                "awesome-triage",
                scope=RepoScope.AWESOME_ONLY,
                phase="Maintenance",
            ),
            FileEntry(
                "skill-repomatic-audit.md",
                ".claude/skills/repomatic-audit/SKILL.md",
                "repomatic-audit",
                phase="Maintenance",
            ),
            FileEntry(
                "skill-repomatic-changelog.md",
                ".claude/skills/repomatic-changelog/SKILL.md",
                "repomatic-changelog",
                phase="Release",
            ),
            FileEntry(
                "skill-repomatic-deps.md",
                ".claude/skills/repomatic-deps/SKILL.md",
                "repomatic-deps",
                phase="Development",
            ),
            FileEntry(
                "skill-repomatic-init.md",
                ".claude/skills/repomatic-init/SKILL.md",
                "repomatic-init",
                phase="Setup",
            ),
            FileEntry(
                "skill-repomatic-lint.md",
                ".claude/skills/repomatic-lint/SKILL.md",
                "repomatic-lint",
                phase="Quality",
            ),
            FileEntry(
                "skill-repomatic-release.md",
                ".claude/skills/repomatic-release/SKILL.md",
                "repomatic-release",
                phase="Release",
            ),
            FileEntry(
                "skill-repomatic-sync.md",
                ".claude/skills/repomatic-sync/SKILL.md",
                "repomatic-sync",
                phase="Setup",
            ),
            FileEntry(
                "skill-repomatic-test.md",
                ".claude/skills/repomatic-test/SKILL.md",
                "repomatic-test",
                phase="Quality",
            ),
            FileEntry(
                "skill-repomatic-topics.md",
                ".claude/skills/repomatic-topics/SKILL.md",
                "repomatic-topics",
                phase="Development",
            ),
            FileEntry(
                "skill-sphinx-docs-sync.md",
                ".claude/skills/sphinx-docs-sync/SKILL.md",
                "sphinx-docs-sync",
                phase="Maintenance",
            ),
            FileEntry(
                "skill-translation-sync.md",
                ".claude/skills/translation-sync/SKILL.md",
                "translation-sync",
                scope=RepoScope.AWESOME_ONLY,
                phase="Maintenance",
            ),
        ),
    ),
    # --- Workflow component ---
    Component(
        name="workflows",
        description="Thin-caller workflow files",
        kind=ComponentKind.WORKFLOW,
        files=(
            FileEntry("autofix.yaml", ".github/workflows/autofix.yaml"),
            FileEntry("autolock.yaml", ".github/workflows/autolock.yaml"),
            FileEntry(
                "cancel-runs.yaml", ".github/workflows/cancel-runs.yaml"
            ),
            FileEntry(
                "changelog.yaml",
                ".github/workflows/changelog.yaml",
                scope=RepoScope.NON_AWESOME,
            ),
            FileEntry(
                "debug.yaml",
                ".github/workflows/debug.yaml",
                scope=RepoScope.NON_AWESOME,
            ),
            FileEntry("docs.yaml", ".github/workflows/docs.yaml"),
            FileEntry("labels.yaml", ".github/workflows/labels.yaml"),
            FileEntry("lint.yaml", ".github/workflows/lint.yaml"),
            FileEntry(
                "release.yaml",
                ".github/workflows/release.yaml",
                scope=RepoScope.NON_AWESOME,
            ),
            FileEntry("renovate.yaml", ".github/workflows/renovate.yaml"),
            FileEntry(
                "tests.yaml",
                ".github/workflows/tests.yaml",
                reusable=False,
            ),
            FileEntry(
                "unsubscribe.yaml",
                ".github/workflows/unsubscribe.yaml",
                opt_in_key="notification.unsubscribe",
            ),
        ),
    ),
    # --- Special components ---
    Component(
        name="awesome-template",
        description="Boilerplate for awesome-* repositories",
        kind=ComponentKind.TEMPLATE,
        init_default=InitDefault.AUTO,
    ),
    Component(
        name="changelog",
        description="Minimal changelog.md",
        kind=ComponentKind.GENERATED,
    ),
    # --- Tool config components (merged into pyproject.toml) ---
    Component(
        name="ruff",
        description="Ruff linter/formatter configuration",
        kind=ComponentKind.TOOL_CONFIG,
        init_default=InitDefault.EXPLICIT,
        source_file="ruff.toml",
        tool_section="tool.ruff",
        insert_after=("tool.uv", "tool.uv.build-backend"),
        insert_before=("tool.pytest",),
    ),
    Component(
        name="pytest",
        description="Pytest test configuration",
        kind=ComponentKind.TOOL_CONFIG,
        init_default=InitDefault.EXPLICIT,
        source_file="pytest.toml",
        tool_section="tool.pytest",
        insert_after=("tool.ruff", "tool.ruff.format"),
        insert_before=("tool.mypy",),
    ),
    Component(
        name="mypy",
        description="Mypy type checking configuration",
        kind=ComponentKind.TOOL_CONFIG,
        init_default=InitDefault.EXPLICIT,
        source_file="mypy.toml",
        tool_section="tool.mypy",
        insert_after=("tool.pytest",),
        insert_before=("tool.nuitka", "tool.bumpversion"),
    ),
    Component(
        name="bumpversion",
        description="bump-my-version configuration",
        kind=ComponentKind.TOOL_CONFIG,
        init_default=InitDefault.EXPLICIT,
        source_file="bumpversion.toml",
        tool_section="tool.bumpversion",
        insert_after=("tool.nuitka", "tool.mypy"),
        insert_before=("tool.typos",),
    ),
    Component(
        name="typos",
        description="Typos spell checker configuration",
        kind=ComponentKind.TOOL_CONFIG,
        init_default=InitDefault.EXPLICIT,
        source_file="typos.toml",
        tool_section="tool.typos",
        insert_after=("tool.bumpversion",),
        insert_before=("tool.pytest",),
    ),
)
"""The component registry.

Single source of truth for all resources managed by the ``init`` subcommand.
Every component declares its kind, selection default, file entries, and
behavioral flags. All legacy constants are derived from this tuple.
"""

_BY_NAME: dict[str, Component] = {c.name: c for c in COMPONENTS}
"""Index for O(1) component lookup by name."""

DEFAULT_REPO: str = "kdeldycke/repomatic"
"""Default upstream repository for reusable workflows."""

UPSTREAM_SOURCE_GLOB: str = "repomatic/**"
"""Path glob for the upstream source directory in canonical workflows.

Canonical workflow ``paths:`` filters use this glob to match source code
changes. In downstream repos, this is replaced with the project's own source
directory.
"""

UPSTREAM_SOURCE_PREFIX: str = "repomatic/"
"""Path prefix for upstream-specific files in canonical workflows.

Paths starting with this prefix (but not matching
:data:`UPSTREAM_SOURCE_GLOB`) are dropped in downstream thin callers because
they reference files that only exist in the upstream repository (e.g.,
``repomatic/data/renovate.json5``).
"""

SKILL_PHASE_ORDER: tuple[str, ...] = (
    "Setup",
    "Development",
    "Quality",
    "Maintenance",
    "Release",
)
"""Canonical display order for lifecycle phases in ``list-skills`` output."""
