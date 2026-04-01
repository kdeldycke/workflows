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

from __future__ import annotations

import functools
import logging
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

from boltons.iterutils import unique
from click_extra import (
    UNPROCESSED,
    Choice,
    ClickException,
    Context,
    EnumChoice,
    FloatRange,
    IntRange,
    ParamType,
    Section,
    UsageError,
    argument,
    dir_path,
    echo,
    file_path,
    group,
    option,
    option_group,
    pass_context,
    style,
)
from click_extra.config import get_tool_config
from click_extra.envvar import merge_envvar_ids
from extra_platforms import ALL_IDS, is_github_ci

from . import __version__
from .binary import (
    BINARY_ARCH_MAPPINGS,
    verify_binary_arch,
)
from .broken_links import manage_combined_broken_links_issue
from .changelog import Changelog, lint_changelog_dates
from .checksums import update_checksums, update_registry_checksums
from .config import CONFIG_REFERENCE_HEADERS, Config, config_reference
from .deps_graph import (
    generate_dependency_graph,
    get_available_extras,
    get_available_groups,
)
from .git_ops import create_and_push_tag
from .github import token as _token_mod, unsubscribe as _unsub_mod
from .github.actions import format_multiline_output
from .github.dev_release import (
    cleanup_dev_releases as _cleanup_dev_releases,
    sync_dev_release as _sync_dev_release,
)
from .github.gh import run_gh_command
from .github.issue import manage_issue_lifecycle
from .github.pr_body import (
    _repo_url,
    build_pr_body,
    generate_pr_metadata_block,
    get_template_names,
    render_commit_message,
    render_template,
    render_title,
    template_args,
)
from .github.release_sync import (
    render_sync_report as _render_sync_report,
    sync_github_releases as _sync_github_releases,
)
from .github.unsubscribe import (
    render_report as _render_report,
    unsubscribe_threads as _unsubscribe_threads,
)
from .github.workflow_sync import run_workflow_lint
from .images import (
    DEFAULT_MIN_SAVINGS_PCT,
    generate_markdown_summary,
    optimize_images,
)
from .init_project import export_content, run_init
from .lint_repo import run_repo_lint
from .mailmap import Mailmap
from .metadata import (
    METADATA_KEYS_HEADERS,
    Dialect,
    Metadata,
    all_metadata_keys,
    is_version_bump_allowed,
    metadata_keys_reference,
)
from .pyproject import get_project_name
from .registry import (
    _BY_NAME,
    ALL_COMPONENTS,
    COMPONENT_HELP_TABLE,
    DEFAULT_REPO,
    FILE_SELECTOR_COMPONENTS,
    SKILL_PHASE_ORDER,
    SKILL_PHASES,
    valid_file_ids,
)
from .release_prep import ReleasePrep
from .renovate import (
    CheckFormat,
    collect_check_results,
    run_migration_checks,
)
from .sponsor import (
    add_sponsor_label,
    get_default_author,
    get_default_number,
    get_default_owner,
    is_pull_request,
    is_sponsor,
)
from .test_plan import DEFAULT_TEST_PLAN, SkippedTest, parse_test_plan
from .tool_runner import (
    TOOL_REGISTRY,
    binary_tool_context,
    resolve_config_source,
    run_tool,
)
from .uv import (
    fix_vulnerable_deps as _fix_vulnerable_deps,
    sync_uv_lock as _sync_uv_lock,
)

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import IO


def is_stdout(filepath: Path) -> bool:
    """Check if a file path is set to stdout.

    Prevents the creation of a ``-`` file in the current directory.
    """
    return str(filepath) == "-"


def prep_path(filepath: Path) -> IO:
    """Prepare the output file parameter for Click's echo function.

    Always returns a UTF-8 encoded file object, including for stdout. This avoids
    ``UnicodeEncodeError`` on Windows where the default stdout encoding is ``cp1252``.

    For non-stdout paths, parent directories are created automatically if they don't
    exist. This absorbs the ``mkdir -p`` step that workflows previously had to do.
    """
    if is_stdout(filepath):
        return open(sys.stdout.fileno(), "w", encoding="UTF-8", closefd=False)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    return filepath.open("w", encoding="UTF-8")


def generate_header(ctx: Context) -> str:
    """Generate metadata to be left as comments to the top of a file generated by
    this CLI.
    """
    header = (
        f"# Generated by {ctx.command_path} v{__version__}"
        " - https://github.com/kdeldycke/repomatic\n"
        f"# Timestamp: {datetime.now(tz=timezone.utc).isoformat()}\n"
    )
    logging.debug(f"Generated header:\n{header}")
    return header


def remove_header(content: str) -> str:
    """Return content without blank lines and header metadata from above."""
    logging.debug(f"Removing header from:\n{content}")
    lines = []
    still_in_header = True
    for line in content.splitlines():
        if still_in_header:
            # We are still in the header as long as we have blank lines or we have
            # comment lines matching the format produced by the method above.
            if not line.strip() or line.startswith((
                "# Generated by ",
                "# Timestamp: ",
            )):
                continue
            else:
                still_in_header = False
        # We are past the header, so keep all the lines: we have nothing left to remove.
        lines.append(line)

    headerless_content = "\n".join(lines)
    logging.debug(f"Result of header removal:\n{headerless_content}")
    return headerless_content


def _require_token(module, attr):
    """Decorator that runs a token validator before the Click command body.

    Uses late-bound ``getattr(module, attr)`` so that
    ``unittest.mock.patch`` can replace the module attribute after import
    and the decorator sees the mock at call time.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                getattr(module, attr)()
            except RuntimeError as exc:
                raise ClickException(str(exc))
            return func(*args, **kwargs)

        return wrapper

    return decorator


# included_params=() disables merge_default_map: all [tool.repomatic] keys are
# config-only (not CLI params), so merging them would collide with subcommand
# names (e.g., "setup-guide" is both a config key and a subcommand). Config
# access goes exclusively through config_schema + get_tool_config().
@group(config_schema=Config, schema_strict=True, included_params=())
def repomatic():
    pass


_section_github = Section("GitHub issues & PRs")
_section_lint = Section("Linting & checks")
_section_release = Section("Release & versioning")
_section_setup = Section("Project setup")
_section_sync = Section("Sync")


class ComponentSelector(ParamType):
    """Accepts bare component names or qualified ``component/file`` selectors.

    Bare names (e.g., ``skills``) select an entire component.  Qualified
    entries (e.g., ``skills/repomatic-topics``) select a single file within
    a component.  The same syntax is used by the ``exclude`` config option
    in ``[tool.repomatic]``.
    """

    name = "selector"

    def get_metavar(self, param):
        return "[COMPONENT[/FILE]]"

    def convert(self, value, param, ctx):
        # --- bare component name ---
        if "/" not in value:
            for key in ALL_COMPONENTS:
                if key.lower() == value.lower():
                    return key
            choices = ", ".join(sorted(ALL_COMPONENTS))
            self.fail(
                f"Unknown component {value!r}. Choose from: {choices}",
                param,
                ctx,
            )

        # --- qualified component/file entry ---
        component_part, file_id = value.split("/", 1)
        component = None
        for key in ALL_COMPONENTS:
            if key.lower() == component_part.lower():
                component = key
                break
        if component is None:
            choices = ", ".join(sorted(ALL_COMPONENTS))
            self.fail(
                f"Unknown component {component_part!r} in {value!r}."
                f" Choose from: {choices}",
                param,
                ctx,
            )
        valid = valid_file_ids(component)
        if not valid:
            self.fail(
                f"Component {component!r} does not support file-level selection.",
                param,
                ctx,
            )
        if file_id not in valid:
            self.fail(
                f"Unknown file {file_id!r} for {component!r}."
                f" Choose from: {', '.join(sorted(valid))}",
                param,
                ctx,
            )
        return f"{component}/{file_id}"

    def shell_complete(self, ctx, param, incomplete):
        from click.shell_completion import CompletionItem

        completions: list[CompletionItem] = [
            CompletionItem(name)
            for name in sorted(ALL_COMPONENTS)
            if name.startswith(incomplete)
        ]
        if "/" in incomplete:
            comp_part = incomplete.split("/", 1)[0]
            for key in ALL_COMPONENTS:
                if key.lower() == comp_part.lower():
                    for fid in sorted(valid_file_ids(key)):
                        qualified = f"{key}/{fid}"
                        if qualified.startswith(incomplete):
                            completions.append(CompletionItem(qualified))
        return completions


@repomatic.command(
    name="init",
    short_help="Bootstrap a repository to use reusable workflows",
    section=_section_setup,
)
@argument(
    "components",
    nargs=-1,
    type=ComponentSelector(),
)
@option(
    "--version",
    "version_pin",
    default=None,
    help="Version pin for upstream workflows (e.g., v5.10.0). "
    "Defaults to the latest release derived from the package version.",
)
@option(
    "--repo",
    default=DEFAULT_REPO,
    help="Upstream repository containing reusable workflows.",
)
@option(
    "--output-dir",
    type=dir_path(resolve_path=True),
    default=".",
    help="Root directory of the target repository.",
)
@option(
    "--delete-excluded",
    is_flag=True,
    default=False,
    help="Delete files that are excluded by config but still on disk.",
)
@option(
    "--delete-unmodified",
    is_flag=True,
    default=False,
    help="Delete config files identical to bundled defaults.",
)
def init_project(
    components,
    version_pin,
    repo,
    output_dir,
    delete_excluded,
    delete_unmodified,
):
    r"""Bootstrap a repository to use reusable workflows from kdeldycke/repomatic.

    With no arguments, generates thin-caller workflow files, exports
    configuration files (Renovate, labels, labeller rules), and creates a
    minimal changelog. Specify COMPONENTS to initialize only selected parts.

    Selectors use the same syntax as the ``exclude`` config in
    ``[tool.repomatic]``: bare names select an entire component, qualified
    ``component/file`` entries select a single file.

    \b
    Components:
    {component_table}

    \b
    File-level selectors ({file_selector_names}):
        workflows/autofix.yaml    A single workflow
        skills/repomatic-topics   A single skill
        labels/labels.toml        A single label config file

    \b
    Examples:
        # Full bootstrap (workflows + labels + renovate + changelog)
        repomatic init

    \b
        # Pin to a specific version
        repomatic init --version v5.9.1

    \b
        # Install a single skill
        repomatic init skills/repomatic-topics

    \b
        # One workflow + all labels
        repomatic init workflows/autofix.yaml labels

    \b
        # Only merge ruff config into pyproject.toml
        repomatic init ruff

    \b
        # Multiple components
        repomatic init ruff bumpversion

    """
    result = run_init(
        output_dir=output_dir,
        components=components,
        version=version_pin,
        repo=repo,
        config=get_tool_config(),
    )

    # Print summary.
    if result.excluded:
        echo(
            style("Excluded by config: ", dim=True)
            + ", ".join(style(e, fg="yellow") for e in result.excluded)
        )
    if result.created:
        echo(style(f"Created {len(result.created)} file(s):", fg="green", bold=True))
        for path in result.created:
            echo(f"  {style(path, fg='green')}")
    if result.updated:
        echo(
            style(
                f"Updated {len(result.updated)} existing file(s):",
                fg="yellow",
                bold=True,
            )
        )
        for path in result.updated:
            echo(f"  {style(path, fg='yellow')}")
    if result.skipped:
        echo(
            style(
                f"Skipped {len(result.skipped)} existing file(s) (never overwritten):",
                dim=True,
            )
        )
        for path in result.skipped:
            echo(f"  {style(path, dim=True)}")
    if result.excluded_existing:
        if delete_excluded:
            for path in result.excluded_existing:
                target = output_dir / path
                target.unlink()
                # Remove empty parent directories up to output_dir.
                parent = target.parent
                while parent != output_dir:
                    try:
                        parent.rmdir()
                    except OSError:
                        break
                    parent = parent.parent
            echo(
                style(
                    f"Deleted {len(result.excluded_existing)} excluded"
                    " file(s) still on disk:",
                    fg="red",
                    bold=True,
                )
            )
        else:
            echo(
                style(
                    f"Excluded: {len(result.excluded_existing)} file(s) still on disk",
                    fg="red",
                )
                + style(" (use --delete-excluded to remove):", dim=True)
            )
        for path in result.excluded_existing:
            echo(f"  {style(path, fg='red')}")
    if result.unmodified_configs:
        if delete_unmodified:
            for path in result.unmodified_configs:
                (output_dir / path).unlink()
            echo(
                style(
                    f"Deleted {len(result.unmodified_configs)} unmodified"
                    " file(s) identical to bundled defaults:",
                    fg="red",
                    bold=True,
                )
            )
        else:
            echo(
                style(
                    f"Unmodified: {len(result.unmodified_configs)} file(s)"
                    " identical to bundled defaults",
                    fg="cyan",
                )
                + style(" (use --delete-unmodified to remove):", dim=True)
            )
        for path in result.unmodified_configs:
            echo(f"  {style(path, fg='cyan' if not delete_unmodified else 'red')}")
    if result.warnings:
        for warning in result.warnings:
            echo(style("Warning: ", fg="yellow", bold=True) + warning)

    has_changes = result.created or result.updated
    if has_changes:
        echo("")
        echo(style("Next steps:", bold=True))
        step = 1
        echo(f"  {step}. Commit the generated files and push.")
        step += 1
        workflows_touched = any(
            p.startswith(".github/workflows/")
            for p in (*result.created, *result.updated)
        )
        if workflows_touched:
            echo(
                f"  {step}. On first push, workflows will detect missing"
                " configuration and open issues"
            )
            echo("     with setup instructions.")


# Format the init_project docstring with registry-generated content.
assert init_project.__doc__ is not None
init_project.__doc__ = init_project.__doc__.format(
    component_table=COMPONENT_HELP_TABLE,
    file_selector_names=", ".join(FILE_SELECTOR_COMPONENTS),
)


@repomatic.command(short_help="Output project metadata", section=_section_setup)
@option(
    "--format",
    type=EnumChoice(Dialect),
    default=Dialect.github,
    help="Rendering format of the metadata.",
)
@option(
    "--overwrite/--no-overwrite",
    "--force/--no-force",
    "--replace/--no-replace",
    default=True,
    help="Overwrite output file if it already exists.",
)
@option(
    "-o",
    "--output",
    type=file_path(writable=True, resolve_path=True, allow_dash=True),
    default="-",
    help="Output file path. Defaults to stdout.",
)
@option(
    "--list-keys",
    is_flag=True,
    default=False,
    help="List all available metadata keys with descriptions and exit.",
)
@argument("keys", nargs=-1)
@pass_context
def metadata(ctx, format, overwrite, output, list_keys, keys):
    """Dump project metadata to a file.

    By default the metadata produced are displayed directly to the console output.
    To have the results written in a file on disk, specify the output file like so:
    `repomatic metadata --output dump.txt`.

    You can filter the output to specific keys by passing them as arguments:

        $ repomatic metadata current_version is_python_project

    To list all available keys with descriptions:

        $ repomatic metadata --list-keys

    For GitHub Actions, use the `github-json` format to bundle all requested keys into a
    single `metadata` output. Downstream jobs access values via
    `fromJSON(needs.metadata.outputs.metadata).key_name`:

        $ repomatic metadata --format github-json --output "$GITHUB_OUTPUT" current_version is_python_project
    """
    if list_keys:
        ctx.find_root().print_table(metadata_keys_reference(), METADATA_KEYS_HEADERS)
        ctx.exit(0)

    # Validate requested keys.
    if keys:
        valid_keys = all_metadata_keys()
        unknown = sorted(set(keys) - valid_keys)
        if unknown:
            raise UsageError(
                f"Unknown metadata key(s): {', '.join(unknown)}. "
                "Use --list-keys to see all available keys."
            )

    if is_stdout(output):
        if overwrite:
            logging.warning("Ignore the --overwrite/--force/--replace option.")
        logging.info(f"Print metadata to {sys.stdout.name}")
    else:
        logging.info(f"Dump all metadata to {output}")

        if output.exists():
            msg = "Target file exists and will be overwritten."
            if overwrite:
                logging.warning(msg)
            else:
                logging.critical(msg)
                ctx.exit(2)

    meta = Metadata()

    # Output a warning in GitHub runners if metadata are not saved to $GITHUB_OUTPUT.
    if is_github_ci():
        env_file = os.getenv("GITHUB_OUTPUT")
        if env_file and Path(env_file) != output:
            logging.warning(
                "Output path is not the same as $GITHUB_OUTPUT environment variable,"
                " which is generally what we're looking to do in GitHub CI runners for"
                " other jobs to consume the produced metadata."
            )

    content = meta.dump(dialect=format, keys=keys)

    # When writing to a file, copy the content to stderr so the computed
    # metadata is visible in CI logs without an extra debug step.
    if not is_stdout(output):
        echo(content, err=True)

    echo(content, file=prep_path(output))


@repomatic.command(
    name="show-config",
    short_help="Print [tool.repomatic] configuration reference",
    section=_section_setup,
)
@pass_context
def show_config(ctx):
    """Print the ``[tool.repomatic]`` configuration reference table.

    Renders a table of all available options, their types, defaults,
    and descriptions — generated from the ``Config`` dataclass docstrings.
    Respects the global ``--table-format`` option.
    """
    ctx.find_root().print_table(config_reference(), CONFIG_REFERENCE_HEADERS)


@repomatic.command(
    short_help="Maintain a Markdown-formatted changelog", section=_section_release
)
@option(
    "--source",
    type=file_path(exists=True, readable=True, resolve_path=True),
    default="changelog.md",
    help="Changelog source file in Markdown format.",
)
@argument(
    "changelog_path",
    type=file_path(writable=True, resolve_path=True, allow_dash=True),
    default="-",
)
@pass_context
def changelog(ctx, source, changelog_path):
    initial_content = None
    if source:
        logging.info(f"Read initial changelog from {source}")
        initial_content = source.read_text(encoding="UTF-8")

    changelog = Changelog(initial_content, Metadata.get_current_version())
    content = changelog.update()
    if content == initial_content:
        logging.warning("Changelog already up to date. Do nothing.")
        ctx.exit()

    if is_stdout(changelog_path):
        logging.info(f"Print updated results to {sys.stdout.name}")
    else:
        logging.info(f"Save updated results to {changelog_path}")
    echo(content, file=prep_path(changelog_path))


@repomatic.command(short_help="Prepare files for a release", section=_section_release)
@option(
    "--changelog",
    "changelog_path",
    type=file_path(exists=True, readable=True, writable=True, resolve_path=True),
    default="changelog.md",
    help="Path to the changelog file.",
)
@option(
    "--citation",
    "citation_path",
    type=file_path(readable=True, writable=True, resolve_path=True),
    default="citation.cff",
    help="Path to the citation file.",
)
@option(
    "--workflow-dir",
    type=dir_path(resolve_path=True),
    default=".github/workflows",
    help="Path to the GitHub workflows directory.",
)
@option(
    "--default-branch",
    default="main",
    help="Name of the default branch for workflow URL updates.",
)
@option(
    "--update-workflows/--no-update-workflows",
    default=None,
    help="Update workflow URLs to use versioned tag instead of default branch."
    " Defaults to True when $GITHUB_REPOSITORY is the canonical workflows repo.",
)
@option(
    "--post-release",
    is_flag=True,
    default=False,
    help="Run post-release steps (retarget workflow URLs to default branch).",
)
@pass_context
def release_prep(
    ctx,
    changelog_path,
    citation_path,
    workflow_dir,
    default_branch,
    update_workflows,
    post_release,
):
    """Prepare files for a release or post-release version bump.

    This command consolidates all release preparation steps:

    \b
    - Set release date in changelog (replaces "(unreleased)" with today's date).
    - Set release date in citation.cff.
    - Update changelog comparison URL from "...main" to "...v{version}".
    - Remove the "[!WARNING]" development warning block from changelog.
    - Optionally update workflow URLs to use versioned tag.

    \b
    When running in GitHub Actions, --update-workflows is auto-detected:
    it defaults to True when $GITHUB_REPOSITORY matches the canonical
    workflows repository (kdeldycke/repomatic).

    For post-release (after the release commit), use --post-release to retarget
    workflow URLs back to the default branch.

    Examples:

    \b
        # Prepare release (changelog + citation)
        repomatic release-prep

    \b
        # In GitHub Actions on kdeldycke/repomatic (auto-detects --update-workflows)
        repomatic release-prep

    \b
        # Post-release: retarget workflows to main branch
        repomatic release-prep --post-release
    """
    # Auto-detect --update-workflows from CI context.
    if update_workflows is None:
        repo_slug = Metadata().repo_slug
        update_workflows = repo_slug == DEFAULT_REPO
        if update_workflows:
            logging.info(
                f"Auto-detected --update-workflows: repo_slug={repo_slug!r}"
                f" matches canonical repo {DEFAULT_REPO!r}"
            )

    prep = ReleasePrep(
        changelog_path=changelog_path,
        citation_path=citation_path if citation_path.exists() else None,
        workflow_dir=workflow_dir,
        default_branch=default_branch,
    )

    if post_release:
        modified = prep.post_release(update_workflows=update_workflows)
        action = "Post-release"
    else:
        modified = prep.prepare_release(update_workflows=update_workflows)
        action = "Release preparation"

    if modified:
        logging.info(f"{action} complete. Modified {len(modified)} file(s):")
        for path in modified:
            echo(f"  {path}")
    else:
        logging.warning(f"{action}: no files were modified.")


@repomatic.command(
    short_help="Check if a version bump is allowed", section=_section_release
)
@option(
    "--part",
    type=Choice(["minor", "major"], case_sensitive=False),
    required=True,
    help="The version part to check for bump eligibility.",
)
def version_check(part: str) -> None:
    """Check if a version bump is allowed for the specified part.

    This command prevents double version increments within a development cycle.
    It compares the current version from pyproject.toml against the latest Git tag
    to determine if a bump has already been applied but not released.

    \b
    Examples:
        # Check if minor version bump is allowed
        repomatic version-check --part minor

        # Check if major version bump is allowed
        repomatic version-check --part major

    \b
    Output:
        - Prints "true" if the bump is allowed
        - Prints "false" if a bump of this type was already applied

    \b
    Use in GitHub Actions:
        allowed=$( repomatic version-check --part minor )
        if [ "$allowed" = "true" ]; then
            bump-my-version bump minor
        fi
    """
    allowed = is_version_bump_allowed(part)  # type: ignore[arg-type]
    echo("true" if allowed else "false")


GITIGNORE_BASE_CATEGORIES: tuple[str, ...] = (
    "certificates",
    "emacs",
    "git",
    "gpg",
    "linux",
    "macos",
    "node",
    "nohup",
    "python",
    "rust",
    "ssh",
    "vim",
    "virtualenv",
    "visualstudiocode",
    "windows",
)
"""Base gitignore.io template categories included in every generated ``.gitignore``.

These cover common development environments, operating systems, and tools.
Downstream projects can add more via ``gitignore-extra-categories`` in
``[tool.repomatic]``.
"""

GITIGNORE_IO_URL = "https://www.toptal.com/developers/gitignore/api"
"""gitignore.io API endpoint for fetching ``.gitignore`` templates."""


@repomatic.command(
    short_help="Sync .gitignore from gitignore.io templates", section=_section_sync
)
@option(
    "--output",
    "output_path",
    type=file_path(writable=True, resolve_path=True, allow_dash=True),
    default=None,
    help=("Output path. Defaults to gitignore-location from [tool.repomatic] config."),
)
@pass_context
def sync_gitignore(ctx: Context, output_path: Path | None) -> None:
    """Sync a ``.gitignore`` file from gitignore.io templates.

    Fetches templates for a base set of categories plus any extras from
    ``[tool.repomatic]`` config, then appends ``gitignore-extra-content``.
    Writes to the path specified by ``gitignore-location`` (default
    ``./.gitignore``).

    \b
    Examples:
        # Generate .gitignore using config from pyproject.toml
        repomatic sync-gitignore

    \b
        # Write to custom location
        repomatic sync-gitignore --output ./custom/.gitignore

    \b
        # Preview on stdout
        repomatic sync-gitignore --output -
    """
    config = get_tool_config(ctx)
    if not config.gitignore_sync:
        logging.info(
            "[tool.repomatic] gitignore.sync is disabled. Skipping .gitignore sync."
        )
        ctx.exit(0)

    # Combine base and extra categories, preserving order and deduplicating.
    all_categories = list(
        dict.fromkeys((*GITIGNORE_BASE_CATEGORIES, *config.gitignore_extra_categories))
    )

    # Fetch from gitignore.io API.
    url = f"{GITIGNORE_IO_URL}/{','.join(all_categories)}"
    logging.info(f"Fetching {url}")
    request = Request(url, headers={"User-Agent": f"repomatic/{__version__}"})
    with urlopen(request) as response:
        content = response.read().decode("UTF-8")

    # Append extra content.
    if config.gitignore_extra_content:
        content += "\n" + config.gitignore_extra_content + "\n"

    # Resolve output path.
    if output_path is None:
        output_path = Path(config.gitignore_location)

    if is_stdout(output_path):
        logging.info(f"Print to {sys.stdout.name}")
    else:
        logging.info(f"Write to {output_path}")

    echo(content.rstrip(), file=prep_path(output_path))


@repomatic.command(
    short_help="Sync GitHub release notes from changelog",
    section=_section_sync,
)
@option(
    "--dry-run/--live",
    default=True,
    help="Report what would be done without making changes.",
)
def sync_github_releases(dry_run: bool) -> None:
    """Sync GitHub release notes from ``changelog.md``.

    Compares each GitHub release body against the corresponding
    ``changelog.md`` section and updates any that have drifted.

    \b
    Examples:
        # Dry run to preview what would be updated
        repomatic sync-github-releases --dry-run

    \b
        # Update drifted release notes
        repomatic sync-github-releases --live
    """
    changelog_path = Path("./changelog.md")
    if not changelog_path.exists():
        logging.warning("changelog.md not found.")
        return

    changelog = Changelog(changelog_path.read_text(encoding="UTF-8"))
    repo_url = changelog.extract_repo_url()
    if not repo_url:
        logging.warning("Could not extract repository URL from changelog.")
        return

    result = _sync_github_releases(repo_url, changelog_path, dry_run)
    echo(_render_sync_report(result))


@repomatic.command(
    short_help="Sync rolling dev pre-release on GitHub",
    section=_section_sync,
)
@option(
    "--dry-run/--live",
    default=True,
    help="Report what would be done without making changes.",
)
@option(
    "--delete/--no-delete",
    default=False,
    help="Delete-only mode: remove the dev pre-release without recreating.",
)
@option(
    "--upload-assets",
    type=dir_path(exists=True, resolve_path=True),
    default=None,
    help="Directory containing assets (binaries, packages) to upload.",
)
@pass_context
def sync_dev_release(
    ctx: Context,
    dry_run: bool,
    delete: bool,
    upload_assets: Path | None,
) -> None:
    """Sync a rolling dev pre-release on GitHub.

    Maintains a single pre-release that mirrors the unreleased changelog
    section. The dev tag is force-updated to point to the latest ``main``
    commit.

    In ``--delete`` mode, removes the dev pre-release without recreating
    it. This is used during real releases to clean up.

    \b
    Examples:
        # Dry run to preview what would be synced
        repomatic sync-dev-release --dry-run

    \b
        # Create or update the dev pre-release
        repomatic sync-dev-release --live

    \b
        # Create or update with asset upload
        repomatic sync-dev-release --live --upload-assets release_assets/

    \b
        # Delete the dev pre-release (e.g. during a real release)
        repomatic sync-dev-release --live --delete
    """
    config = get_tool_config(ctx)
    if not config.dev_release_sync:
        logging.info(
            "[tool.repomatic] dev-release.sync is disabled. Skipping dev release sync."
        )
        ctx.exit(0)

    if delete and upload_assets:
        raise UsageError("--delete and --upload-assets are mutually exclusive.")
    version = Metadata.get_current_version()
    if not version:
        logging.warning("Could not determine current version.")
        return

    changelog_path = Path("./changelog.md")
    if not changelog_path.exists():
        logging.warning("changelog.md not found.")
        return

    changelog = Changelog(changelog_path.read_text(encoding="UTF-8"))
    repo_url = changelog.extract_repo_url()
    if not repo_url:
        logging.warning("Could not extract repository URL from changelog.")
        return

    # Parse owner/repo for gh CLI.
    parts = repo_url.rstrip("/").split("/")
    nwo = f"{parts[-2]}/{parts[-1]}" if len(parts) >= 2 else ""

    if delete:
        if dry_run:
            echo("[dry-run] Would delete all dev releases.")
            return
        _cleanup_dev_releases(nwo)
        echo("Deleted all dev releases.")
        return

    if _sync_dev_release(
        changelog_path, version, nwo, dry_run, asset_dir=upload_assets
    ):
        mode = "dry-run" if dry_run else "live"
        echo(f"[{mode}] Dev release v{version} synced.")


@repomatic.group(
    short_help="Lint downstream workflow caller files", section=_section_setup
)
def workflow():
    """Lint downstream workflow caller files.

    Check thin caller workflows that delegate to the canonical reusable
    workflows in ``kdeldycke/repomatic``. Use ``repomatic init workflows``
    to generate or sync workflow files.
    """


@workflow.command(short_help="Lint workflow files for common issues")
@option(
    "--workflow-dir",
    type=dir_path(exists=True, resolve_path=True),
    default=".github/workflows",
    help="Directory containing workflow YAML files.",
)
@option(
    "--repo",
    default=DEFAULT_REPO,
    help="Upstream repository to match thin callers against.",
)
@option(
    "--fatal/--warning",
    default=False,
    help="Exit with code 1 if issues are found (default: warning only).",
)
@pass_context
def lint(ctx, workflow_dir, repo, fatal):
    """Lint workflow files for common issues.

    Checks all YAML files in the workflow directory for:

    \b
    - Missing ``workflow_dispatch`` trigger.
    - Thin callers using ``@main`` instead of a version tag.
    - Thin callers with mismatched triggers vs canonical workflows.
    - Thin callers missing ``secrets: inherit`` when required.

    \b
    Examples:
        # Lint workflows in default location
        repomatic workflow lint

    \b
        # Lint with fatal mode (exit 1 on issues)
        repomatic workflow lint --fatal

    \b
        # Lint a custom directory
        repomatic workflow lint --workflow-dir ./my-workflows
    """
    exit_code = run_workflow_lint(
        workflow_dir=workflow_dir,
        repo=repo,
        fatal=fatal,
    )
    ctx.exit(exit_code)


@repomatic.command(
    short_help="Sync Git's .mailmap file with missing contributors",
    section=_section_sync,
)
@option(
    "--source",
    type=file_path(readable=True, resolve_path=True),
    default=".mailmap",
    help="Mailmap source file to use as reference for contributors identities that "
    "are already grouped.",
)
@option(
    "--create-if-missing/--skip-if-missing",
    is_flag=True,
    default=True,
    help="If not found, either create the missing destination mailmap file, or skip "
    "the update process entirely. This option is ignored if the destination is to print "
    f"the result to {sys.stdout.name}.",
)
@argument(
    "destination_mailmap",
    type=file_path(writable=True, resolve_path=True, allow_dash=True),
    default=None,
)
@pass_context
def sync_mailmap(ctx, source, create_if_missing, destination_mailmap):
    """Update a ``.mailmap`` file with all missing contributors found in Git commit
    history.

    By default the ``.mailmap`` at the root of the repository is read and its content
    is reused as reference, so identities already aliased in there are preserved and
    used as initial mapping. Only missing contributors not found in this initial mapping
    are added.

    The destination defaults to the source file path (in-place update). Pass ``-``
    explicitly to print to stdout instead.

    The updated results are sorted. But no attempts are made at regrouping new
    contributors. So you have to edit entries by hand to regroup them.
    """
    config = get_tool_config(ctx)
    if not config.mailmap_sync:
        logging.info(
            "[tool.repomatic] mailmap.sync is disabled. Skipping .mailmap sync."
        )
        ctx.exit(0)

    # Default destination to source path (in-place update).
    if destination_mailmap is None:
        destination_mailmap = source

    mailmap = Mailmap()

    if source.exists():
        logging.info(f"Read initial mapping from {source}")
        content = remove_header(source.read_text(encoding="UTF-8"))
        mailmap.parse(content)
    else:
        logging.debug(f"Mailmap source file {source} does not exist.")

    mailmap.update_from_git()
    new_content = mailmap.render()

    if is_stdout(destination_mailmap):
        logging.info(f"Print updated results to {sys.stdout.name}.")
        logging.debug(
            "Ignore the "
            + ("--create-if-missing" if create_if_missing else "--skip-if-missing")
            + " option."
        )
    else:
        logging.info(f"Save updated results to {destination_mailmap}")
        if not create_if_missing and not destination_mailmap.exists():
            logging.warning(
                f"{destination_mailmap} does not exist, stop the sync process."
            )
            ctx.exit()
        if content == new_content:
            logging.warning("Nothing to update, stop the sync process.")
            ctx.exit()

    echo(generate_header(ctx) + new_content, file=prep_path(destination_mailmap))


@repomatic.command(
    short_help="Run a test plan from a file against a binary", section=_section_lint
)
@option(
    "--command",
    "--binary",
    required=True,
    metavar="COMMAND",
    help="Path to the binary file to test, or a command line to be executed.",
)
@option(
    "-F",
    "--plan-file",
    type=file_path(exists=True, readable=True, resolve_path=True),
    multiple=True,
    metavar="FILE_PATH",
    help="Path to a test plan file in YAML. This option can be repeated to run "
    "multiple test plans in sequence. If not provided, a default test plan will be "
    "executed.",
)
@option(
    "-E",
    "--plan-envvar",
    multiple=True,
    metavar="ENVVAR_NAME",
    help="Name of an environment variable containing a test plan in YAML. This "
    "option can be repeated to collect multiple test plans.",
)
@option(
    "-t",
    "--select-test",
    type=IntRange(min=1),
    multiple=True,
    metavar="INTEGER",
    help="Only run the tests matching the provided test case numbers. This option can "
    "be repeated to run multiple test cases. If not provided, all test cases will be "
    "run.",
)
@option(
    "-s",
    "--skip-platform",
    type=Choice(sorted(ALL_IDS), case_sensitive=False),
    multiple=True,
    help="Skip tests for the specified platforms. This option can be repeated to "
    "skip multiple platforms.",
)
@option(
    "-x",
    "--exit-on-error",
    is_flag=True,
    default=False,
    help="Exit instantly on first failed test.",
)
@option(
    "-T",
    "--timeout",
    # Timeout passed to subprocess.run() is a float that is silently clamped to
    # 0.0 if negative values are provided, so we mimic this behavior here:
    # https://github.com/python/cpython/blob/5740b95076b57feb6293cda4f5504f706a7d622d/Lib/subprocess.py#L1596-L1597
    type=FloatRange(min=0, clamp=True),
    metavar="SECONDS",
    help="Set the default timeout for each CLI call, if not specified in the "
    "test plan.",
)
@option(
    "--show-trace-on-error/--hide-trace-on-error",
    default=True,
    help="Show execution trace of failed tests.",
)
@option(
    "--stats/--no-stats",
    is_flag=True,
    default=True,
    help="Print per-manager package statistics.",
)
@pass_context
def test_plan(
    ctx: Context,
    command: str,
    plan_file: tuple[Path, ...] | None,
    plan_envvar: tuple[str, ...] | None,
    select_test: tuple[int, ...] | None,
    skip_platform: tuple[str, ...] | None,
    exit_on_error: bool,
    timeout: float | None,
    show_trace_on_error: bool,
    stats: bool,
) -> None:
    # Load [tool.repomatic] config for fallback values.
    config = get_tool_config(ctx)

    # Load test plan: CLI args > pyproject.toml config > DEFAULT_TEST_PLAN.
    test_list = []
    if plan_file or plan_envvar:
        # CLI-provided sources take precedence.
        for file in unique(plan_file):
            logging.info(f"Get test plan from {file} file")
            tests = list(parse_test_plan(file.read_text(encoding="UTF-8")))
            logging.info(f"{len(tests)} test cases found.")
            test_list.extend(tests)
        for envvar_id in merge_envvar_ids(plan_envvar):
            logging.info(f"Get test plan from {envvar_id!r} environment variable")
            tests = list(parse_test_plan(os.getenv(envvar_id)))
            logging.info(f"{len(tests)} test cases found.")
            test_list.extend(tests)

    else:
        # Fall back to [tool.repomatic] config.
        if config.test_plan_inline:
            logging.info("Get test plan from [tool.repomatic] test-plan.inline config.")
            tests = list(parse_test_plan(config.test_plan_inline))
            logging.info(f"{len(tests)} test cases found.")
            test_list.extend(tests)

        if config.test_plan_file:
            plan_path = Path(config.test_plan_file)
            if plan_path.exists():
                logging.info(f"Get test plan from config path: {plan_path}")
                tests = list(parse_test_plan(plan_path.read_text(encoding="UTF-8")))
                logging.info(f"{len(tests)} test cases found.")
                test_list.extend(tests)

        if not test_list:
            logging.warning(
                "No test plan provided through CLI options or"
                " [tool.repomatic] config: use default test plan."
            )
            test_list = DEFAULT_TEST_PLAN

    # Fall back to config timeout if not provided via CLI.
    if timeout is None and config.test_plan_timeout is not None:
        timeout = float(config.test_plan_timeout)

    logging.debug(f"Test plan: {test_list}")

    counter = Counter(total=len(test_list), skipped=0, failed=0)

    for index, test_case in enumerate(test_list):
        test_number = index + 1
        test_name = f"#{test_number}"
        logging.info(f"Run test {test_name}...")

        if select_test and test_number not in select_test:
            logging.warning(f"Test {test_name} skipped by user request.")
            counter["skipped"] += 1
            continue

        try:
            logging.debug(f"Test case parameters: {test_case}")
            test_case.run_cli_test(
                command,
                additional_skip_platforms=skip_platform,
                default_timeout=timeout,
            )
        except SkippedTest as ex:
            counter["skipped"] += 1
            logging.warning(f"Test {test_name} skipped: {ex}")
        except Exception as ex:  # noqa: BLE001
            counter["failed"] += 1
            logging.error(f"Test {test_name} failed: {ex}")
            if show_trace_on_error and test_case.execution_trace:
                echo(test_case.execution_trace)
            if exit_on_error:
                logging.debug("Don't continue testing, a failed test was found.")
                ctx.exit(1)

    if stats:
        echo(
            "Test plan results - "
            + ", ".join((f"{k.title()}: {v}" for k, v in counter.items()))
        )

    if counter["failed"]:
        ctx.exit(1)


@repomatic.command(
    short_help="Label issues/PRs from GitHub sponsors", section=_section_github
)
@option(
    "--owner",
    envvar="GITHUB_REPOSITORY_OWNER",
    help="GitHub username or organization to check sponsorship for. "
    "Defaults to $GITHUB_REPOSITORY_OWNER.",
)
@option(
    "--author",
    help="GitHub username of the issue/PR author to check. "
    "Defaults to author from $GITHUB_EVENT_PATH.",
)
@option(
    "--repo",
    envvar="GITHUB_REPOSITORY",
    help="Repository in 'owner/repo' format. Defaults to $GITHUB_REPOSITORY.",
)
@option(
    "--number",
    type=IntRange(min=1),
    help="Issue or PR number. Defaults to number from $GITHUB_EVENT_PATH.",
)
@option(
    "--label",
    default="💖 sponsors",
    help="Label to add if author is a sponsor.",
)
@option(
    "--pr/--issue",
    "is_pr",
    default=None,
    help="Specify issue or pull request. Auto-detected from $GITHUB_EVENT_PATH.",
)
@_require_token(_token_mod, "validate_gh_token_env")
def sponsor_label(
    owner: str | None,
    author: str | None,
    repo: str | None,
    number: int | None,
    label: str,
    is_pr: bool | None,
) -> None:
    """Add a label to issues or PRs from GitHub sponsors.

    Checks if the author of an issue or PR is a sponsor of the repository owner.
    If they are, adds the specified label.

    This command requires the ``gh`` CLI to be installed and authenticated.

    When run in GitHub Actions, all parameters are auto-detected from environment
    variables ($GITHUB_REPOSITORY_OWNER, $GITHUB_REPOSITORY) and the event payload
    ($GITHUB_EVENT_PATH). You can override any auto-detected value by passing it
    explicitly.

    \b
    Examples:
        # In GitHub Actions (all defaults auto-detected)
        repomatic sponsor-label

    \b
        # Override specific values
        repomatic sponsor-label --label "sponsor"

    \b
        # Manual invocation with all values
        repomatic sponsor-label --owner kdeldycke --author some-user \\
            --repo kdeldycke/repomatic --number 123 --issue
    """
    # Apply defaults from GitHub Actions environment.
    if owner is None:
        owner = get_default_owner()
    if author is None:
        author = get_default_author()
    if number is None:
        number = get_default_number()
    if is_pr is None:
        is_pr = is_pull_request()

    # Validate required parameters.
    missing = []
    if not owner:
        missing.append("--owner")
    if not author:
        missing.append("--author")
    if not repo:
        missing.append("--repo")
    if not number:
        missing.append("--number")

    if missing:
        raise UsageError(
            f"Missing required parameters: {', '.join(missing)}. "
            "These could not be auto-detected from the environment."
        )

    # Type narrowing for mypy.
    assert owner and author and repo and number

    if is_sponsor(owner, author):
        if add_sponsor_label(repo, number, label, is_pr=is_pr):
            echo(f"Added {label!r} label to {'PR' if is_pr else 'issue'} #{number}")
        else:
            raise ClickException("Failed to add sponsor label")
    else:
        echo(f"Author {author!r} is not a sponsor of {owner!r}")


@repomatic.command(
    name="update-deps-graph",
    short_help="Generate dependency graph from uv lockfile",
    section=_section_setup,
)
@option(
    "-p",
    "--package",
    help="Focus on a specific package's dependency tree.",
)
@option_group(
    "Group filtering",
    option(
        "-g",
        "--group",
        "groups",
        multiple=True,
        help="Include dependencies from the specified group (e.g., test, typing). "
        "Can be repeated.",
    ),
    option(
        "--all-groups",
        is_flag=True,
        default=False,
        help="Include all dependency groups from pyproject.toml.",
    ),
    option(
        "--no-group",
        "excluded_groups",
        multiple=True,
        help="Exclude the specified group. Takes precedence over --all-groups "
        "and --group. Can be repeated.",
    ),
    option(
        "--only-group",
        "only_groups",
        multiple=True,
        help="Only include dependencies from the specified group, excluding main "
        "dependencies. Can be repeated.",
    ),
)
@option_group(
    "Extra filtering",
    option(
        "-e",
        "--extra",
        "extras",
        multiple=True,
        help="Include dependencies from the specified extra (e.g., xml, json5). "
        "Can be repeated.",
    ),
    option(
        "--all-extras",
        is_flag=True,
        default=False,
        help="Include all optional extras from pyproject.toml.",
    ),
    option(
        "--no-extra",
        "excluded_extras",
        multiple=True,
        help="Exclude the specified extra, if --all-extras is supplied. "
        "Can be repeated.",
    ),
    option(
        "--only-extra",
        "only_extras",
        multiple=True,
        help="Only include dependencies from the specified extra, excluding main "
        "dependencies. Can be repeated.",
    ),
)
@option(
    "--frozen/--no-frozen",
    default=True,
    help="Use --frozen to skip lock file updates.",
)
@option(
    "-l",
    "--level",
    type=IntRange(min=1),
    default=None,
    help="Maximum depth of the dependency graph. "
    "1 = primary deps only, 2 = primary + their deps, etc.",
)
@option(
    "-o",
    "--output",
    type=file_path(writable=True, resolve_path=True, allow_dash=True),
    default=None,
    help="Output file path. Defaults to [tool.repomatic] config or stdout.",
)
def deps_graph(
    package: str | None,
    groups: tuple[str, ...],
    all_groups: bool,
    excluded_groups: tuple[str, ...],
    only_groups: tuple[str, ...],
    extras: tuple[str, ...],
    all_extras: bool,
    excluded_extras: tuple[str, ...],
    only_extras: tuple[str, ...],
    frozen: bool,
    level: int | None,
    output: Path | None,
) -> None:
    """Generate a Mermaid dependency graph from the project's uv lockfile.

    Parses the CycloneDX SBOM export from uv and renders it as a Mermaid
    flowchart for documentation. Version specifiers from uv.lock are shown
    as edge labels.

    \b
    Examples:
        # Generate Mermaid graph
        repomatic update-deps-graph

    \b
        # Include test dependencies
        repomatic update-deps-graph --group test

    \b
        # Include all groups and extras
        repomatic update-deps-graph --all-groups --all-extras

    \b
        # Include all groups except typing
        repomatic update-deps-graph --all-groups --no-group typing

    \b
        # Include all extras except one
        repomatic update-deps-graph --all-extras --no-extra json5

    \b
        # Show only test group dependencies (no main deps)
        repomatic update-deps-graph --only-group test

    \b
        # Show only a specific extra's dependencies
        repomatic update-deps-graph --only-extra xml

    \b
        # Focus on a specific package
        repomatic update-deps-graph --package click-extra

    \b
        # Limit graph depth to 2 levels
        repomatic update-deps-graph --level 2

    \b
        # Save to file
        repomatic update-deps-graph --output docs/dependency-graph.md
    """
    config = get_tool_config()

    # Auto-detect package name from [project].name.
    if package is None:
        package = get_project_name()
        if package:
            logging.info(f"Auto-detected package from pyproject.toml: {package}")

    # Resolve output: CLI > config > stdout.
    if output is None:
        if config.dependency_graph_output:
            output = Path(config.dependency_graph_output).resolve()
        else:
            output = Path("-")

    # Apply config defaults when CLI flags are not explicitly provided.
    if not all_groups and not groups and not only_groups:
        all_groups = config.dependency_graph_all_groups
    if not all_extras and not extras and not only_extras:
        all_extras = config.dependency_graph_all_extras
    if not excluded_groups and config.dependency_graph_no_groups:
        excluded_groups = tuple(config.dependency_graph_no_groups)
    if not excluded_extras and config.dependency_graph_no_extras:
        excluded_extras = tuple(config.dependency_graph_no_extras)
    if level is None:
        level = config.dependency_graph_level

    # Resolve --only-group/--only-extra (exclusive mode: no main deps).
    exclude_base = bool(only_groups or only_extras)
    if only_groups:
        groups = only_groups
    if only_extras:
        extras = only_extras

    # Resolve --all-groups and --all-extras flags.
    resolved_groups: tuple[str, ...] | None = groups if groups else None
    if all_groups:
        resolved_groups = get_available_groups()
        logging.info(f"Discovered groups: {', '.join(resolved_groups)}")

    resolved_extras: tuple[str, ...] | None = extras if extras else None
    if all_extras:
        resolved_extras = get_available_extras()
        logging.info(f"Discovered extras: {', '.join(resolved_extras)}")

    # Apply --no-group and --no-extra exclusions.
    if excluded_groups and resolved_groups:
        resolved_groups = tuple(g for g in resolved_groups if g not in excluded_groups)
        logging.info(f"After exclusions, groups: {', '.join(resolved_groups)}")
    if excluded_extras and resolved_extras:
        resolved_extras = tuple(e for e in resolved_extras if e not in excluded_extras)
        logging.info(f"After exclusions, extras: {', '.join(resolved_extras)}")

    graph = generate_dependency_graph(
        package=package,
        groups=resolved_groups,
        extras=resolved_extras,
        frozen=frozen,
        depth=level,
        exclude_base=exclude_base,
    )

    if is_stdout(output):
        logging.info(f"Print graph to {sys.stdout.name}")
    else:
        logging.info(f"Write graph to {output}")

    echo(graph, file=prep_path(output))


@repomatic.command(
    short_help="Manage broken links issue lifecycle", section=_section_github
)
@option(
    "--lychee-exit-code",
    type=int,
    default=None,
    help="Exit code from lychee (0=no broken links, 2=broken links found).",
)
@option(
    "--body-file",
    type=file_path(exists=True, readable=True, resolve_path=True),
    default=None,
    help="Path to the issue body file (lychee output).",
)
@option(
    "--output-json",
    type=file_path(exists=True, readable=True, resolve_path=True),
    default=None,
    help="Path to Sphinx linkcheck output.json file.",
)
@option(
    "--source-url",
    default=None,
    help="Base URL for linking filenames and line numbers in the Sphinx report. "
    "Example: https://github.com/owner/repo/blob/<sha>/docs",
)
@option(
    "--repo-name",
    default=None,
    help="Repository name (for label selection)."
    " Defaults to $GITHUB_REPOSITORY name component.",
)
@_require_token(_token_mod, "validate_gh_token_env")
def broken_links(
    lychee_exit_code: int | None,
    body_file: Path | None,
    output_json: Path | None,
    source_url: str | None,
    repo_name: str | None,
) -> None:
    """Manage the broken links issue lifecycle.

    Combines Lychee and Sphinx linkcheck results into a single "Broken links"
    issue. Each tool's results appear under its own heading.

    \b
    In GitHub Actions, most options are auto-detected:
    - --repo-name defaults to $GITHUB_REPOSITORY name component.
    - --body-file defaults to ./lychee/out.md when --lychee-exit-code is set.
    - --output-json defaults to ./docs/linkcheck/output.json if the file exists.
    - --source-url is composed from $GITHUB_SERVER_URL, $GITHUB_REPOSITORY,
      and $GITHUB_SHA when --output-json is set.

    \b
    This command:
    1. Auto-detects missing options from environment and file paths.
    2. Validates inputs (lychee exit code must be 0 or 2 if provided).
    3. Parses Sphinx linkcheck output.json if provided.
    4. Builds a combined report with sections for each tool.
    5. Lists open issues by github-actions[bot].
    6. Triages matching "Broken links" issues (keep newest, close duplicates).
    7. Creates or updates the main issue.

    This command requires the ``gh`` CLI to be installed and authenticated.

    \b
    Examples:
        # In GitHub Actions (auto-detection)
        repomatic broken-links --lychee-exit-code 2

    \b
        # Explicit options
        repomatic broken-links \\
            --lychee-exit-code 2 \\
            --body-file ./lychee/out.md \\
            --repo-name "my-repo"

    \b
        # Both tools combined (explicit)
        repomatic broken-links \\
            --lychee-exit-code 2 \\
            --body-file ./lychee/out.md \\
            --output-json ./docs/linkcheck/output.json \\
            --repo-name "my-repo" \\
            --source-url "https://github.com/owner/repo/blob/abc123/docs"
    """
    manage_combined_broken_links_issue(
        repo_name=repo_name,
        lychee_exit_code=lychee_exit_code,
        lychee_body_file=body_file,
        sphinx_output_json=output_json,
        sphinx_source_url=source_url,
    )


@repomatic.command(
    short_help="Manage setup guide issue lifecycle", section=_section_github
)
@option(
    "--has-pat",
    is_flag=True,
    default=False,
    envvar="HAS_REPOMATIC_PAT",
    help="Whether REPOMATIC_PAT is configured.",
)
@option(
    "--repo",
    default=None,
    envvar="GITHUB_REPOSITORY",
    help="Repository in 'owner/repo' format. Defaults to $GITHUB_REPOSITORY.",
)
@option(
    "--sha",
    default=None,
    envvar="GITHUB_SHA",
    help="Commit SHA for permission checks. Defaults to $GITHUB_SHA.",
)
@_require_token(_token_mod, "validate_gh_token_env")
@pass_context
def setup_guide(
    ctx: Context,
    has_pat: bool,
    repo: str | None,
    sha: str | None,
) -> None:
    """Manage the setup guide issue lifecycle.

    Handles three states:

    - **No PAT**: opens a setup guide issue with full instructions.
    - **PAT configured but incomplete**: keeps the issue open with a
      section listing the missing permissions.
    - **PAT configured and complete**: closes the issue.

    The flag can also be set via the ``HAS_REPOMATIC_PAT`` environment variable
    (any non-empty value is truthy). Workflows set this env var at the workflow
    level so individual steps don't need to repeat the ``secrets.*`` ternary.

    When ``--has-pat`` is set and ``--repo`` is provided, the command runs the
    same granular PAT permission checks as ``lint-repo`` (via
    :func:`~repomatic.github.token.check_all_pat_permissions`). If any check
    fails, the issue stays open with details about which permissions are missing.

    This command requires the ``gh`` CLI to be installed and authenticated.

    \b
    Examples:
        # No secret — create or reopen the setup issue
        repomatic setup-guide

    \b
        # Secret configured — close the issue if all permissions pass
        repomatic setup-guide --has-pat
    """
    config = get_tool_config(ctx)
    if not config.setup_guide:
        logging.info("[tool.repomatic] setup-guide is disabled. Skipping setup guide.")
        ctx.exit(0)

    # Resolve repo identity for template variables.
    md = Metadata()
    repo_name = md.repo_name
    repo_owner = md.repo_owner
    repo_slug = md.repo_slug
    repo_url = _repo_url()

    # Run granular PAT permission checks when the PAT is present.
    missing_permissions_section = ""
    has_permission_failures = False
    if has_pat and repo:
        pat_results = _token_mod.check_all_pat_permissions(repo, sha)
        failures = pat_results.failed()
        if failures:
            has_permission_failures = True
            rows = []
            for _field_name, message in failures:
                rows.append(f"| {message} |")
            table = "\n".join(rows)
            missing_permissions_section = (
                "> [!WARNING]\n"
                "> Your `REPOMATIC_PAT` secret is configured but missing"
                " some permissions.\n"
                "> Update the token using the pre-filled link in Step 1"
                " below.\n\n"
                "| Permission issue |\n"
                "| :-- |\n"
                f"{table}\n"
            )

    # Include immutable releases step only when a changelog exists.
    has_changelog = Path("./changelog.md").exists()
    immutable_releases_step = (
        render_template("immutable-releases", repo_url=repo_url)
        if has_changelog
        else ""
    )

    # Detect if the repository owner is an organization.
    org_tip = ""
    owner = repo_owner
    if owner:
        try:
            owner_type = run_gh_command(
                ["api", f"users/{owner}", "--jq", ".type"],
            ).strip()
            if owner_type == "Organization":
                org_tip = (
                    "> \U0001f4a1 **For organizations**: Consider using a"
                    " [machine user account](https://docs.github.com/en/"
                    "get-started/learning-about-github/types-of-github-accounts"
                    "#personal-accounts) or a dedicated service account to own"
                    " the PAT, rather than tying it to an individual's account."
                )
        except RuntimeError:
            logging.debug(f"Failed to detect owner type for {owner!r}.")

    # --- Setup guide issue ---
    setup_body = render_template(
        "setup-guide",
        repo_url=repo_url,
        repo_name=repo_name,
        repo_owner=repo_owner,
        repo_slug=repo_slug,
        immutable_releases_step=immutable_releases_step,
        org_tip=org_tip,
        missing_permissions_section=missing_permissions_section,
    )
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".md",
        delete=False,
        encoding="UTF-8",
    ) as tmp:
        tmp.write(setup_body)
        setup_body_file = Path(tmp.name)

    # Keep issue open when PAT is missing OR when permissions are incomplete.
    needs_issue = not has_pat or has_permission_failures

    manage_issue_lifecycle(
        has_issues=needs_issue,
        body_file=setup_body_file,
        labels=["🤖 ci"],
        title="Set up `REPOMATIC_PAT` to enable workflow auto-updates",
        no_issues_comment="PAT secret detected, all permissions verified.",
    )


@repomatic.command(
    short_help="Unsubscribe from closed, inactive notification threads",
    section=_section_github,
)
@option(
    "--months",
    type=IntRange(min=1),
    default=3,
    help="Inactivity threshold in months. Threads updated more recently are kept.",
)
@option(
    "--batch-size",
    type=IntRange(min=1),
    default=200,
    help="Maximum number of threads/items to process per phase.",
)
@option(
    "--dry-run/--live",
    default=True,
    help="Report what would be done without making changes.",
)
@_require_token(_unsub_mod, "_validate_notifications_token")
def unsubscribe_threads(months: int, batch_size: int, dry_run: bool) -> None:
    """Unsubscribe from closed, inactive GitHub notification threads.

    Processes notifications in two phases:

    \b
    Phase 1 — REST notification threads:
      Fetches Issue/PullRequest notification threads, inspects each for
      closed + stale status, and unsubscribes via DELETE + PATCH.

    \b
    Phase 2 — GraphQL threadless subscriptions:
      Searches for closed issues/PRs the user is involved in and
      unsubscribes via the updateSubscription mutation.

    \b
    Examples:
        # Dry run to preview what would be unsubscribed
        repomatic unsubscribe-threads --dry-run

    \b
        # Unsubscribe from threads inactive for 6+ months
        repomatic unsubscribe-threads --months 6

    \b
        # Process at most 50 threads per phase
        repomatic unsubscribe-threads --batch-size 50
    """
    result = _unsubscribe_threads(months, batch_size, dry_run)
    echo(_render_report(result))


@repomatic.command(
    short_help="Verify binary architecture using exiftool", section=_section_lint
)
@option(
    "--target",
    type=Choice(sorted(BINARY_ARCH_MAPPINGS.keys()), case_sensitive=False),
    required=True,
    help="Target platform (e.g., linux-arm64, macos-x64, windows-x64).",
)
@option(
    "--binary",
    "binary_path",
    type=file_path(exists=True, readable=True, resolve_path=True),
    required=True,
    help="Path to the binary file to verify.",
)
def verify_binary(target: str, binary_path: Path) -> None:
    """Verify that a compiled binary matches the expected architecture.

    Uses exiftool to inspect the binary and validates that its architecture
    matches what is expected for the specified target platform.

    Requires exiftool to be installed and available in PATH.

    \b
    Examples:
        # Verify a Linux ARM64 binary
        repomatic verify-binary --target linux-arm64 --binary ./mpm-linux-arm64.bin

    \b
        # Verify a Windows x64 binary
        repomatic verify-binary --target windows-x64 --binary ./mpm-windows-x64.exe
    """
    verify_binary_arch(target, binary_path)
    echo(f"Binary architecture verified for {target}: {binary_path}")


@repomatic.command(
    short_help="Upgrade packages with known vulnerabilities",
    section=_section_sync,
)
@option(
    "--lockfile",
    type=file_path(resolve_path=True),
    default="uv.lock",
    help="Path to the uv.lock file.",
)
@option(
    "--output",
    type=file_path(writable=True, resolve_path=True, allow_dash=True),
    default=None,
    help="Output file for the diff table (e.g., $GITHUB_OUTPUT).",
)
@pass_context
def fix_vulnerable_deps_cmd(
    ctx: Context,
    lockfile: Path,
    output: Path | None,
) -> None:
    """Detect and upgrade packages with known security vulnerabilities.

    Runs ``uv audit`` to detect vulnerabilities in the lock file, then
    upgrades each fixable package with ``uv lock --upgrade-package``. Uses
    ``--exclude-newer-package`` to bypass the ``exclude-newer`` cooldown so
    that security fixes are resolved immediately.

    When no fixable vulnerabilities are found, exits cleanly so
    ``peter-evans/create-pull-request`` sees no diff and skips creating a PR.

    \b
    Examples:
        # Standard usage (from autofix.yaml fix-vulnerable-deps job)
        repomatic fix-vulnerable-deps

    \b
        # Write diff table to $GITHUB_OUTPUT
        repomatic fix-vulnerable-deps --output "$GITHUB_OUTPUT"
    """
    has_fixes, diff_table = _fix_vulnerable_deps(lockfile)

    if not has_fixes:
        echo("No fixable vulnerabilities found.")
        ctx.exit(0)

    echo("Upgraded vulnerable packages.")
    if diff_table:
        echo(diff_table)

    if output and diff_table:
        github_output_path = os.getenv("GITHUB_OUTPUT", "")
        if (
            not is_stdout(output)
            and github_output_path
            and str(output) == github_output_path
        ):
            content = format_multiline_output("diff_table", diff_table)
        else:
            content = diff_table
        echo(content, file=prep_path(output))


@repomatic.command(
    short_help="Re-lock and revert if only timestamp noise changed",
    section=_section_sync,
)
@option(
    "--lockfile",
    type=file_path(resolve_path=True),
    default="uv.lock",
    help="Path to the uv.lock file.",
)
@option(
    "--output",
    type=file_path(writable=True, resolve_path=True, allow_dash=True),
    default=None,
    help="Output file for the diff table (e.g., $GITHUB_OUTPUT).",
)
@pass_context
def sync_uv_lock_cmd(ctx: Context, lockfile: Path, output: Path | None) -> None:
    """Run ``uv lock --upgrade`` and revert if only timestamp noise changed.

    Runs ``uv lock --upgrade`` to update transitive dependencies to their
    latest allowed versions. If the resulting ``uv.lock`` diff contains only
    ``exclude-newer-package`` timestamp changes, reverts the lock file so
    ``peter-evans/create-pull-request`` sees no diff and skips creating a PR.

    When real changes exist, prints a markdown table of updated package
    versions. Use ``--output "$GITHUB_OUTPUT"`` to write the table as a
    ``diff_table`` output variable for use in subsequent workflow steps.

    \b
    Examples:
        # Standard usage (from renovate.yaml sync-uv-lock job)
        repomatic sync-uv-lock

    \b
        # Write diff table to $GITHUB_OUTPUT
        repomatic sync-uv-lock --output "$GITHUB_OUTPUT"

    \b
        # Check a different lock file
        repomatic sync-uv-lock --lockfile path/to/uv.lock
    """
    config = get_tool_config(ctx)
    if not config.uv_lock_sync:
        logging.info(
            "[tool.repomatic] uv-lock.sync is disabled. Skipping uv.lock sync."
        )
        ctx.exit(0)

    reverted, diff_table = _sync_uv_lock(lockfile)

    if reverted:
        echo("Reverted uv.lock: only exclude-newer-package timestamp noise.")
    else:
        echo("Kept uv.lock: contains real dependency changes.")
        if diff_table:
            echo(diff_table)

    if output and diff_table:
        github_output_path = os.getenv("GITHUB_OUTPUT", "")
        if (
            not is_stdout(output)
            and github_output_path
            and str(output) == github_output_path
        ):
            content = format_multiline_output("diff_table", diff_table)
        else:
            content = diff_table
        echo(content, file=prep_path(output))


@repomatic.command(
    short_help="Sync bumpversion config from bundled template", section=_section_sync
)
@pass_context
def sync_bumpversion(ctx: Context) -> None:
    """Sync ``[tool.bumpversion]`` config in ``pyproject.toml`` from the bundled
    template.

    Overwrites the ``[tool.bumpversion]`` section with the canonical template
    bundled in ``repomatic``. Designed for the ``sync-bumpversion`` autofix job.
    The ``repomatic init bumpversion`` command remains available for interactive
    bootstrapping.
    """
    config = get_tool_config(ctx)
    if not config.bumpversion_sync:
        logging.info(
            "[tool.repomatic] bumpversion.sync is disabled."
            " Skipping bumpversion config sync."
        )
        ctx.exit(0)

    result = run_init(
        output_dir=Path("."),
        components=("bumpversion",),
        config=config,
    )
    changed = [*result.created, *result.updated]
    if changed:
        for path in changed:
            echo(f"Updated: {path}")
    else:
        echo("bumpversion config is up to date.")


@repomatic.command(
    short_help="Remove config files that match bundled defaults",
    section=_section_sync,
)
def clean_unmodified_configs() -> None:
    """Remove config files identical to their bundled defaults.

    Scans both tool configs (yamllint, zizmor, etc.) and init-managed
    configs (labels, renovate) and deletes any file whose content matches
    the bundled default after whitespace normalization.

    Designed for standalone use. The ``sync-repomatic`` autofix job uses
    ``repomatic init --delete-unmodified`` instead.
    """
    from .init_project import find_all_unmodified_configs

    unmodified = find_all_unmodified_configs()
    if not unmodified:
        echo("No unmodified config files found.")
        return

    for label, rel_path in unmodified:
        Path(rel_path).unlink()
        echo(f"Removed: {rel_path} (unmodified {label} config)")


@repomatic.command(
    short_help="Sync repository labels via labelmaker", section=_section_sync
)
@option(
    "--repo",
    "repository",
    default=None,
    help="GitHub repository (owner/name). Auto-detected if omitted.",
)
@pass_context
def sync_labels(ctx: Context, repository: str | None) -> None:
    """Sync repository labels from bundled definitions using ``labelmaker``.

    Exports label definitions via ``repomatic init labels``, then applies them
    to the repository using ``labelmaker``. Applies the ``default`` profile to
    all repositories, plus the ``awesome`` profile for ``awesome-*`` repos.

    Requires ``GITHUB_TOKEN`` in the environment. Downloads ``labelmaker``
    automatically via the tool registry.
    """
    config = get_tool_config(ctx)
    if not config.labels_sync:
        logging.info("[tool.repomatic] labels.sync is disabled. Skipping label sync.")
        ctx.exit(0)

    # Auto-detect repository.
    meta = Metadata()
    if repository is None:
        repository = meta.repo_slug
    if not repository:
        raise ClickException("Cannot detect repository.")

    # Dump label files.
    result = run_init(output_dir=Path("."), components=("labels",), config=config)
    for path in [*result.created, *result.updated]:
        logging.info(f"Exported: {path}")

    with binary_tool_context("labelmaker") as lm:
        # Apply default profile.
        _run_labelmaker(lm, "apply", "labels.toml", "--profile", "default", repository)

        # Apply awesome profile for awesome-* repos.
        if meta.is_awesome:
            _run_labelmaker(
                lm, "apply", "labels.toml", "--profile", "awesome", repository
            )

        # Apply extra label files.
        extra_dir = Path("extra-labels")
        if extra_dir.is_dir():
            for label_file in sorted(extra_dir.iterdir()):
                if label_file.is_file():
                    _run_labelmaker(lm, "apply", str(label_file), repository)

    echo("Labels synced.")


def _run_labelmaker(labelmaker_path: Path, *args: str) -> None:
    """Run a ``labelmaker`` command.

    :param labelmaker_path: Path to the labelmaker binary.
    :param args: Arguments to pass to labelmaker.
    :raises ClickException: If labelmaker fails.
    """
    cmd = [str(labelmaker_path), *args]
    logging.info(f"Running: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        capture_output=True,
        encoding="UTF-8",
        check=False,
    )
    if result.returncode:
        raise ClickException(f"labelmaker failed: {result.stderr}")
    if result.stdout:
        logging.debug(result.stdout)


def _parse_skill_frontmatter(content: str) -> dict[str, str]:
    """Extract YAML frontmatter fields from a skill definition file.

    Parses the ``---``-delimited frontmatter block and returns a dict of
    key-value pairs. Only handles simple ``key: value`` lines (no nested
    structures).
    """
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    result = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


@repomatic.command(
    short_help="List available Claude Code skills",
    section=_section_setup,
)
def list_skills() -> None:
    """List all bundled Claude Code skills grouped by lifecycle phase.

    Reads skill definitions from the bundled data files and displays them
    in a table grouped by phase: Setup, Development, Quality, and Release.
    """
    # Collect skill metadata from bundled files.
    skills_comp = _BY_NAME["skills"]
    skills = []
    for entry in skills_comp.files:
        content = export_content(entry.source)
        meta = _parse_skill_frontmatter(content)
        name = meta.get("name", entry.file_id)
        description = meta.get("description", "")
        # Strip trailing period for table display.
        description = description.removesuffix(".")
        phase = SKILL_PHASES.get(name, "Other")
        skills.append((phase, name, description))

    # Group by phase in canonical order.
    for phase in SKILL_PHASE_ORDER:
        phase_skills = [(n, d) for p, n, d in skills if p == phase]
        if not phase_skills:
            continue
        echo(f"\n{phase}:")
        for name, description in phase_skills:
            echo(f"  /{name:<24s} {description}")

    echo("")


@repomatic.command(
    short_help="Check Renovate migration prerequisites", section=_section_lint
)
@option(
    "--repo",
    default=None,
    envvar="GITHUB_REPOSITORY",
    help="Repository in 'owner/repo' format. Defaults to $GITHUB_REPOSITORY.",
)
@option(
    "--sha",
    default=None,
    envvar="GITHUB_SHA",
    help="Commit SHA for permission checks. Defaults to $GITHUB_SHA.",
)
@option(
    "--format",
    "output_format",
    type=EnumChoice(CheckFormat),
    default=CheckFormat.text,
    help="Output format: text (human-readable), json (structured), "
    "or github (for $GITHUB_OUTPUT).",
)
@option(
    "-o",
    "--output",
    type=file_path(writable=True, resolve_path=True, allow_dash=True),
    default="-",
    help="Output file path. Defaults to stdout.",
)
@pass_context
def check_renovate(
    ctx: Context,
    repo: str | None,
    sha: str | None,
    output_format: CheckFormat,
    output: Path,
) -> None:
    """Check prerequisites for Renovate migration.

    Validates that:

    \b
    - renovate.json5 configuration exists
    - No Dependabot version updates config exists (.github/dependabot.yaml)
    - Dependabot security updates are disabled
    - Token has required PAT permissions (commit statuses, contents, issues,
      pull requests, vulnerability alerts, workflows)

    Use --format=github to output results for $GITHUB_OUTPUT, allowing
    workflows to use the values in conditional steps.

    \b
    Examples:
        # Human-readable output (default)
        repomatic check-renovate

    \b
        # JSON output for parsing
        repomatic check-renovate --format=json

    \b
        # GitHub Actions output format
        repomatic check-renovate --format=github --output "$GITHUB_OUTPUT"

    \b
        # Manual invocation
        repomatic check-renovate --repo owner/repo --sha abc123
    """
    if not repo:
        raise UsageError("No repository specified. Set --repo or $GITHUB_REPOSITORY.")
    if not sha:
        raise UsageError("No SHA specified. Set --sha or $GITHUB_SHA.")

    # For text format, use the original function with console output.
    if output_format == CheckFormat.text:
        exit_code = run_migration_checks(repo, sha)
        ctx.exit(exit_code)

    # For json/github formats, collect results and output structured data.
    results = collect_check_results(repo, sha)

    if output_format == CheckFormat.json:
        content = results.to_json()
    else:  # github format.
        content = results.to_github_output()

    echo(content, file=prep_path(output))


@repomatic.command(
    short_help="Run repository consistency checks", section=_section_lint
)
@option(
    "--repo-name",
    default=None,
    help="Repository name. Defaults to $GITHUB_REPOSITORY name component.",
)
@option(
    "--repo",
    default=None,
    envvar="GITHUB_REPOSITORY",
    help="Repository in 'owner/repo' format. Defaults to $GITHUB_REPOSITORY.",
)
@option(
    "--has-pat",
    is_flag=True,
    default=False,
    envvar="HAS_REPOMATIC_PAT",
    help="Whether GH_TOKEN contains REPOMATIC_PAT. Enables PAT capability checks.",
)
@option(
    "--sha",
    default=None,
    envvar="GITHUB_SHA",
    help="Commit SHA for permission checks. Defaults to $GITHUB_SHA.",
)
@pass_context
def lint_repo(
    ctx: Context,
    repo_name: str | None,
    repo: str | None,
    has_pat: bool,
    sha: str | None,
) -> None:
    """Run consistency checks on repository metadata.

    Reads ``package_name``, ``is_sphinx``, and ``project_description`` directly
    from ``pyproject.toml`` in the current directory.

    Checks:
    - Dependabot config file absent (error).
    - Renovate config exists (error).
    - Dependabot security updates disabled (error).
    - Package name vs repository name (warning).
    - Website field set for Sphinx projects (warning).
    - Repository description matches project description (error).
    - GitHub topics subset of pyproject.toml keywords (warning).
    - Funding file present when owner has GitHub Sponsors (warning).
    - Stale draft releases (non-.dev0 drafts) (warning).

    When ``--has-pat`` is set, additional PAT capability checks are run:
    - Contents permission (error).
    - Issues permission (error).
    - Pull requests permission (error).
    - Dependabot alerts permission and alerts enabled (error).
    - Workflows permission (error).
    - Commit statuses permission (error, requires ``--sha``).

    \b
    Examples:
        # In GitHub Actions (reads pyproject.toml automatically)
        repomatic lint-repo --repo-name my-package

    \b
        # Local run (derives repo from $GITHUB_REPOSITORY or --repo)
        repomatic lint-repo --repo owner/repo

    \b
        # With PAT capability checks
        repomatic lint-repo --has-pat --sha abc123
    """
    if repo_name is None and repo:
        # Extract repo name from owner/repo format.
        repo_name = repo.split("/")[-1] if "/" in repo else repo

    # Derive package_name, is_sphinx, project_description, keywords from pyproject.toml.
    metadata = Metadata()
    package_name = get_project_name()
    is_sphinx = metadata.is_sphinx
    project_description = metadata.project_description
    keywords = metadata.pyproject_toml.get("project", {}).get("keywords")

    exit_code = run_repo_lint(
        package_name=package_name,
        repo_name=repo_name,
        is_sphinx=is_sphinx,
        project_description=project_description,
        keywords=keywords,
        repo=repo if repo else None,
        has_pat=has_pat,
        sha=sha,
    )
    ctx.exit(exit_code)


@repomatic.command(
    short_help="Check changelog dates against release dates", section=_section_lint
)
@option(
    "--changelog",
    "changelog_path",
    type=file_path(exists=True, readable=True, resolve_path=True),
    default="changelog.md",
    help="Path to the changelog file.",
)
@option(
    "--package",
    default=None,
    help="PyPI package name for date lookups. Auto-detected from pyproject.toml.",
)
@option(
    "--fix",
    is_flag=True,
    default=False,
    help="Fix date mismatches and add PyPI admonitions to the changelog.",
)
@pass_context
def lint_changelog(
    ctx: Context,
    changelog_path: Path,
    package: str | None,
    fix: bool,
) -> None:
    """Verify that changelog release dates match canonical release dates.

    Uses PyPI upload dates as the canonical reference when the project is
    published to PyPI. Falls back to git tag dates for non-PyPI projects.

    PyPI timestamps are immutable and reflect the actual publication date,
    making them more reliable than git tags which can be recreated.

    Also detects orphaned versions: versions that exist as git tags,
    GitHub releases, or PyPI packages but have no corresponding changelog
    entry. Orphans cause a non-zero exit code.

    Reads ``pypi-package-history`` from ``[tool.repomatic]`` to fetch
    releases published under former package names (for renamed projects).

    \b
    Output symbols:
        ✓  Dates match
        ⚠  Version not found on reference source (warning, non-fatal)
        ✗  Date mismatch (error, fatal)

    \b
    With --fix, the command also:
        - Corrects mismatched dates to match the canonical source.
        - Adds a PyPI link admonition under each released version.
        - Adds a CAUTION admonition for yanked releases.
        - Adds a WARNING admonition for versions not on PyPI.
        - Inserts placeholder sections for orphaned versions.

    \b
    Examples:
        # Check the default changelog.md (auto-detects PyPI package)
        repomatic lint-changelog

    \b
        # Fix dates and add admonitions
        repomatic lint-changelog --fix

    \b
        # Explicit package name
        repomatic lint-changelog --package repomatic
    """
    config = get_tool_config(ctx)
    exit_code = lint_changelog_dates(
        changelog_path,
        package=package,
        fix=fix,
        pypi_package_history=config.pypi_package_history,
    )
    ctx.exit(exit_code)


TOOL_LIST_HEADERS: tuple[str, ...] = ("Tool", "Version", "Config source")
"""Column headers for the ``repomatic run --list`` table."""


@repomatic.command(
    name="run",
    short_help="Run an external tool with managed config",
    section=_section_lint,
    context_settings={"ignore_unknown_options": True},
)
@argument("tool_name", required=False, default=None)
@argument("extra_args", nargs=-1, type=UNPROCESSED)
@option("--list", "list_tools", is_flag=True, help="List all managed tools.")
@pass_context
def run_cmd(ctx, tool_name, extra_args, list_tools):
    """Run an external tool with managed configuration.

    Installs the tool at a pinned version, resolves config through a 4-level
    precedence chain (native config file, ``[tool.X]`` in ``pyproject.toml``,
    bundled default, bare invocation), and invokes the tool.

    \b
    Pass extra arguments to the tool after ``--``:
        repomatic run yamllint -- --strict .
        repomatic run zizmor -- --offline .

    \b
    List all managed tools and their resolved config source:
        repomatic run --list
    """
    if list_tools:
        rows = [
            (spec.name, spec.version, resolve_config_source(spec))
            for spec in sorted(TOOL_REGISTRY.values(), key=lambda s: s.name)
        ]
        ctx.find_root().print_table(rows, TOOL_LIST_HEADERS)
        ctx.exit(0)

    if tool_name is None:
        raise UsageError(
            "Missing argument 'TOOL_NAME'. Use --list to see available tools."
        )

    exit_code = run_tool(tool_name, extra_args=extra_args)
    ctx.exit(exit_code)


@repomatic.command(short_help="Create and push a Git tag", section=_section_release)
@option(
    "--tag",
    required=True,
    help="Tag name to create (e.g., v1.2.3).",
)
@option(
    "--commit",
    default=None,
    help="Commit to tag. Defaults to HEAD.",
)
@option(
    "--push/--no-push",
    default=True,
    help="Push the tag to remote after creation.",
)
@option(
    "--skip-existing/--error-existing",
    default=True,
    help="Skip silently if tag exists, or fail with an error.",
)
@option(
    "-o",
    "--output",
    type=file_path(writable=True, resolve_path=True, allow_dash=True),
    default=None,
    help="Output file for created=true/false (e.g., $GITHUB_OUTPUT).",
)
def git_tag(
    tag: str,
    commit: str | None,
    push: bool,
    skip_existing: bool,
    output: Path | None,
) -> None:
    """Create and optionally push a Git tag.

    This command is idempotent: if the tag already exists and --skip-existing
    is used, it exits successfully without making changes. This allows safe
    re-runs of workflows interrupted after tag creation.

    \b
    Examples:
        # Create and push a tag
        repomatic git-tag --tag v1.2.3

    \b
        # Tag a specific commit
        repomatic git-tag --tag v1.2.3 --commit abc123def

    \b
        # Create tag without pushing
        repomatic git-tag --tag v1.2.3 --no-push

    \b
        # Fail if tag exists
        repomatic git-tag --tag v1.2.3 --error-existing

    \b
        # Output result for GitHub Actions
        repomatic git-tag --tag v1.2.3 --output "$GITHUB_OUTPUT"
    """
    try:
        created = create_and_push_tag(
            tag=tag,
            commit=commit,
            push=push,
            skip_existing=skip_existing,
        )
    except ValueError as e:
        raise ClickException(str(e))
    except subprocess.CalledProcessError as e:
        msg = f"Failed to create/push tag: {e}"
        if e.stderr:
            msg += f"\n{e.stderr.strip()}"
        raise ClickException(msg)

    if created:
        echo(f"Created{' and pushed' if push else ''} tag {tag!r}")
    else:
        echo(f"Tag {tag!r} already exists, skipped.")

    if output:
        echo(f"created={'true' if created else 'false'}", file=prep_path(output))


@repomatic.command(
    short_help="Generate PR body with workflow metadata", section=_section_github
)
@option(
    "--prefix",
    envvar="GHA_PR_BODY_PREFIX",
    default="",
    help="Content to prepend before the metadata details block. "
    "Can also be set via the GHA_PR_BODY_PREFIX environment variable.",
)
@option(
    "--template",
    type=Choice(get_template_names(), case_sensitive=False),
    default=None,
    help="Use a built-in prefix template instead of --prefix.",
)
@option(
    "--version",
    "version",
    default=None,
    help="Version string passed to the template (e.g. 1.2.0).",
)
@option(
    "--part",
    default=None,
    help="Version part passed to bump-version template (e.g. minor, major).",
)
@option(
    "--pr-ref",
    "pr_ref",
    default=None,
    help="PR reference passed to detect-squash-merge template (e.g. #2316).",
)
@option(
    "-o",
    "--output",
    type=file_path(writable=True, resolve_path=True, allow_dash=True),
    default="-",
    help="Output file path. Defaults to stdout.",
)
def pr_body(
    prefix: str,
    template: str | None,
    version: str | None,
    part: str | None,
    pr_ref: str | None,
    output: Path,
) -> None:
    """Generate a PR body with a collapsible workflow metadata block.

    Reads ``GITHUB_*`` environment variables to produce a ``<details>`` block
    containing a metadata table (trigger, actor, ref, commit, job, workflow, run).

    When ``--output`` points to ``$GITHUB_OUTPUT``, the body is written in the
    heredoc format required by GitHub Actions multiline outputs.

    The prefix can be set via ``--template`` (built-in templates) or ``--prefix``
    (arbitrary content, also via ``GHA_PR_BODY_PREFIX`` env var). If both are
    given, ``--prefix`` is prepended before the rendered template content.

    \b
    Examples:
        # Preview metadata block locally
        repomatic pr-body

    \b
        # Write to $GITHUB_OUTPUT for use in a workflow
        repomatic pr-body --output "$GITHUB_OUTPUT"

    \b
        # Use a built-in template
        repomatic pr-body --template bump-version --version 1.2.0 --part minor

    \b
        # With a prefix via environment variable
        GHA_PR_BODY_PREFIX="Fix formatting" repomatic pr-body
    """

    def _auto_version() -> str:
        """Read current_version from bumpversion config and strip .dev suffix."""
        ver = Metadata.get_current_version()
        if not ver:
            msg = "Cannot auto-detect version: no bumpversion config found."
            raise ClickException(msg)
        ver = re.sub(r"\.dev\d*$", "", ver)
        logging.info(f"Auto-detected version: {ver}")
        return ver

    # Map argument names to their values or callables.
    arg_sources: dict[str, str | None | Callable[[], str | None]] = {
        "diff_table": os.getenv("REPOMATIC_DIFF_TABLE", ""),
        "part": part,
        "pr_ref": pr_ref,
        "repo_url": _repo_url,  # Callable, will be invoked if needed.
        "version": version if version is not None else _auto_version,
    }

    title_str = ""
    commit_msg_str = ""

    if template:
        kwargs: dict[str, str | None] = {}
        for arg in template_args(template):
            value = arg_sources.get(arg)
            if value is None:
                msg = f"--{arg} is required for template '{template}'"
                raise UsageError(msg)
            # Call if callable, otherwise use the value directly.
            kwargs[arg] = value() if callable(value) else value

        template_content = render_template(template, **kwargs)
        # Combine prefix (e.g. from GHA_PR_BODY_PREFIX) with template content.
        if prefix:
            prefix = prefix + "\n\n" + template_content
        else:
            prefix = template_content
        title_str = render_title(template, **kwargs)
        commit_msg_str = render_commit_message(template, **kwargs)

    metadata_block = generate_pr_metadata_block()
    body = build_pr_body(prefix, metadata_block)

    github_output_path = os.getenv("GITHUB_OUTPUT", "")
    is_github_output = (
        not is_stdout(output)
        and github_output_path
        and str(output) == github_output_path
    )

    if is_github_output:
        # Write in heredoc format for $GITHUB_OUTPUT.
        parts = [format_multiline_output("body", body)]
        if title_str:
            parts.append(f"title={title_str}")
        if commit_msg_str:
            parts.append(f"commit_message={commit_msg_str}")
        content = "\n".join(parts)
    else:
        content = body

    if is_stdout(output):
        logging.info(f"Print PR body to {sys.stdout.name}")
    else:
        logging.info(f"Write PR body to {output}")

    echo(content, file=prep_path(output))


@repomatic.command(
    short_help="Update SHA-256 checksums for binary downloads", section=_section_setup
)
@argument(
    "workflow_file",
    type=file_path(exists=True, readable=True, writable=True, resolve_path=True),
    required=False,
)
@option(
    "--registry",
    is_flag=True,
    default=False,
    help="Update checksums in the tool runner registry instead of a workflow file.",
)
def update_checksums_cmd(workflow_file: Path | None, registry: bool) -> None:
    """Update SHA-256 checksums for direct binary downloads.

    By default, scans a workflow YAML file for GitHub release download URLs
    paired with ``sha256sum --check`` verification lines. Downloads each binary,
    computes the SHA-256, and replaces stale hashes in-place.

    With ``--registry``, updates checksums in the ``repomatic run`` tool registry
    for all binary-distributed tools.

    \b
    Designed for Renovate ``postUpgradeTasks``: after a version bump changes a
    download URL, this command downloads the new binary and updates the hash.

    \b
    Examples:
        # Update checksums in a single workflow file
        repomatic update-checksums .github/workflows/docs.yaml

    \b
        # Update checksums in the tool runner registry
        repomatic update-checksums --registry
    """
    if registry:
        registry_path = Path(__file__).parent / "tool_runner.py"
        updated = update_registry_checksums(registry_path)
    elif workflow_file is not None:
        updated = update_checksums(workflow_file)
    else:
        msg = "Either a workflow file argument or --registry flag is required."
        raise UsageError(msg)

    for url, old_hash, new_hash in updated:
        echo(f"Updated: {url}")
        echo(f"  Old: {old_hash}")
        echo(f"  New: {new_hash}")
    if not updated:
        logging.info("All checksums are up to date.")


@repomatic.command(
    name="format-images",
    short_help="Format images with lossless optimization",
    section=_section_setup,
)
@option(
    "--min-savings",
    type=FloatRange(0, 100),
    default=DEFAULT_MIN_SAVINGS_PCT,
    show_default=True,
    help="Minimum percentage savings to keep an optimized file.",
)
@option(
    "-o",
    "--output",
    type=file_path(writable=True, resolve_path=True, allow_dash=True),
    default="-",
    help="Output file path. Defaults to stdout.",
)
def format_images_cmd(min_savings: float, output: Path) -> None:
    """Format images by losslessly optimizing them with external CLI tools.

    Discovers PNG and JPEG files and compresses them losslessly in-place using
    ``oxipng`` and ``jpegoptim``. Produces a markdown summary table showing
    before/after sizes and savings.

    Only lossless optimizers are used so that results are idempotent — running
    the command twice produces no further changes. See ``repomatic.images`` for
    the rationale on excluding WebP and AVIF.

    When ``--output`` points to ``$GITHUB_OUTPUT``, the markdown summary is
    written as a ``markdown`` output variable in heredoc format.

    \b
    Required tools (install via apt):
        sudo apt-get install oxipng jpegoptim

    \b
    Examples:
        # Format images and print summary
        repomatic format-images

    \b
        # Write markdown output for GitHub Actions
        repomatic format-images --output "$GITHUB_OUTPUT"

    \b
        # Use a 10% minimum savings threshold
        repomatic format-images --min-savings 10
    """
    image_files = Metadata().image_files
    if not image_files:
        echo("No image files found.")
        return

    logging.info(f"Found {len(image_files)} image file(s) to optimize.")
    results = optimize_images(image_files, min_savings_pct=min_savings)
    markdown = generate_markdown_summary(results)

    github_output_path = os.getenv("GITHUB_OUTPUT", "")
    is_github_output = (
        not is_stdout(output)
        and github_output_path
        and str(output) == github_output_path
    )

    if is_github_output:
        content = format_multiline_output("markdown", markdown)
    else:
        content = markdown

    if is_stdout(output):
        logging.info(f"Print image optimization summary to {sys.stdout.name}")
    else:
        logging.info(f"Write image optimization summary to {output}")

    echo(content, file=prep_path(output))
