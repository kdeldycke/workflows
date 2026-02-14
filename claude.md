# Development guide

## Project overview

This repository contains two main components:

1. **`gha-utils` CLI** - A command-line utility for GitHub Actions workflows
1. **Reusable GitHub workflows** - A collection of automated workflows for CI/CD

The CLI provides tools for:

- Changelog management and version bumping
- `.mailmap` synchronization
- Project metadata extraction
- Test plan execution against compiled binaries

The reusable workflows automate:

- Formatting, linting, and type checking
- Version management and releases
- Documentation building and deployment
- Label management and auto-locking
- Binary compilation for multiple platforms

## Downstream repositories

This repository serves as the **canonical reference** for conventions and best practices. When Claude is used in any repository that reuses workflows from [`kdeldycke/workflows`](https://github.com/kdeldycke/workflows), it should follow the same conventions defined here—including the structure and guidelines of this `claude.md` file itself.

In other words, downstream repositories should mirror the patterns established here for code style, documentation, testing, and design principles.

**Contributing upstream:** If Claude spots inefficiencies, potential improvements, performance bottlenecks, missing features, or opportunities for better adaptability in the reusable workflows, `gha-utils` CLI, or this `claude.md` file itself, it should propose these changes upstream via a pull request or issue at [`kdeldycke/workflows`](https://github.com/kdeldycke/workflows/issues). This benefits all downstream repositories.

## Commands

### Testing

```shell-session
# Run all tests with coverage.
$ uv run --group test pytest

# Run a single test file.
$ uv run --group test pytest tests/test_changelog.py

# Run a specific test.
$ uv run --group test pytest tests/test_changelog.py::test_function_name
```

### Type checking

```shell-session
$ uv run --group typing mypy gha_utils
```

### Running the CLI

```shell-session
# Run locally during development.
$ uv run gha-utils --help

# Try without installation using uvx.
$ uvx -- gha-utils --help
```

## Architecture

### Project structure

```
workflows/
├── .github/
│   └── workflows/     # Reusable GitHub Actions workflows
├── docs/              # Assets (images, Mermaid diagrams)
├── gha_utils/         # Python CLI package (see module table below)
│   └── data/          # Bundled configuration files
└── tests/             # Test suite
```

### `gha_utils` modules

| Module                | Purpose                                                             |
| --------------------- | ------------------------------------------------------------------- |
| `__init__.py`         | Package-wide exports                                                |
| `__main__.py`         | Entry point for the `gha-utils` CLI                                 |
| `binary.py`           | Binary verification and artifact collection                         |
| `broken_links.py`     | Broken links issue lifecycle management                             |
| `bundled_config.py`   | Access bundled config templates, labels, and workflow files         |
| `changelog.py`        | Changelog parsing, updating, and release lifecycle management       |
| `cli.py`              | Click-based command-line interface definitions                      |
| `deps_graph.py`       | Generate Mermaid dependency graphs from uv lockfiles                |
| `git_ops.py`          | Idempotent Git operations for CI/CD contexts                        |
| `github.py`           | GitHub Actions output formatting and workflow annotations           |
| `lint_repo.py`        | Repository metadata consistency checks                              |
| `mailmap.py`          | Git `.mailmap` file synchronization with contributors               |
| `matrix.py`           | Generate build matrices for GitHub Actions                          |
| `metadata.py`         | Extract and combine metadata from Git, GitHub, and `pyproject.toml` |
| `pr_body.py`          | Generate PR body with workflow metadata for auto-created PRs        |
| `release_prep.py`     | Orchestrate release preparation across citation and workflow files  |
| `renovate.py`         | Renovate prerequisites, migration, and `exclude-newer` updates      |
| `sphinx_linkcheck.py` | Parse Sphinx linkcheck output and manage documentation link issues  |
| `sponsor.py`          | Check GitHub sponsorship and label issues/PRs from sponsors         |
| `test_plan.py`        | Run YAML-based test plans against compiled binaries                 |
| `workflow_sync.py`    | Thin-caller generation, sync, and lint for downstream workflows     |

### Workflows organization

Reusable workflows are organized by purpose:

- `autofix.yaml` - Auto-formatting and dependency syncing
- `autolock.yaml` - Auto-locking inactive issues
- `cancel-runs.yaml` - Cancelling workflow runs on PR close
- `changelog.yaml` - Version bumping and release preparation
- `debug.yaml` - Debugging utilities
- `docs.yaml` - Documentation building and deployment
- `labels.yaml` - Label management and PR auto-labeling
- `lint.yaml` - Linting and type checking
- `release.yaml` - Package building, binary compilation, and publishing
- `renovate.yaml` - Dependency update automation
- `tests.yaml` - Test execution

## Documentation requirements

### Scope of `claude.md` vs `readme.md`

- **`claude.md`**: Contributor and Claude-focused directives—code style, testing guidelines, design principles, and internal development guidance.
- **`readme.md`**: User-facing documentation for the reusable workflows and `gha-utils` CLI—installation, usage, configuration, and workflow job descriptions.

When adding new content, consider whether it benefits end users (`readme.md`) or contributors/Claude working on the codebase (`claude.md`).

### Changelog and readme updates

Always update documentation when making changes:

- **`changelog.md`**: Add a bullet point describing **what** changed (new features, bug fixes, behavior changes), not **why**. Keep entries concise and actionable. Justifications and rationale belong in documentation (`readme.md`, Sphinx docs) or code comments, not in the changelog.
- **`readme.md`**: Update relevant sections when adding/modifying workflow jobs, CLI commands, or configuration options.

### Documenting code decisions

Document design decisions, trade-offs, and non-obvious implementation choices directly in the code:

- Use **docstring admonitions** for important notes in module/class/function docstrings:

  ```python
  """Extract metadata from repository.

  .. warning::
      This method temporarily modifies repository state during execution.

  .. note::
      The commit range is inclusive on both ends.

  .. caution::
      The default SHA length is subject to change based on repository size.
  """
  ```

- Use **inline comments** for explaining specific code blocks:

  ```python
  # We use a frozenset for O(1) lookups and immutability.
  SKIP_BRANCHES: Final[frozenset[str]] = frozenset(("branch-a", "branch-b"))
  ```

- Use **module-level docstrings** for constants that need context:

  ```python
  SOME_CONSTANT = 42
  """Why this value was chosen and how it's used.

  Additional context about edge cases or related constants.
  """
  ```

This ensures future maintainers (including Claude) understand the reasoning behind implementation choices.

## Code style

### Terminology and spelling

Use correct capitalization for proper nouns and trademarked names:

- **PyPI** (not ~~PyPi~~) — the Python Package Index. The "I" is capitalized because it stands for "Index". See [PyPI trademark guidelines](https://pypi.org/trademarks/).
- **GitHub** (not ~~Github~~)
- **JavaScript** (not ~~Javascript~~)
- **TypeScript** (not ~~Typescript~~)
- **macOS** (not ~~MacOS~~ or ~~macos~~)
- **iOS** (not ~~IOS~~ or ~~ios~~)

### Comments and docstrings

- All comments in Python files must end with a period.
- Docstrings use reStructuredText format (vanilla style, not Google/NumPy).
- Documentation in `./docs/` uses MyST markdown format where possible. Fallback to reStructuredText if necessary.
- Keep lines within 88 characters in Python files, including docstrings and comments (ruff default). Markdown files have no line-length limit.
- Titles in markdown use sentence case.

### Imports

- Import from the root package (`from gha_utils import cli`), not submodules when possible.
- Place imports at the top of the file, unless avoiding circular imports.
- **Version-dependent imports** (e.g., `tomllib` fallback for Python 3.10) should be placed **after all normal imports** but **before the `TYPE_CHECKING` block**. This allows ruff to freely sort and organize the normal imports above without interference.

### `TYPE_CHECKING` block

Place a module-level `TYPE_CHECKING` block after all imports (including version-dependent conditional imports):

```python
"""Module docstring."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Version-dependent imports come after normal imports.
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

# TYPE_CHECKING block comes last in the import section.
TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Iterator
    from ._types import _T
```

### Modern `typing` practices

Do not import types from `typing` when a modern equivalent exists in the standard library. Since Python 3.9, built-in types like `list`, `dict`, and `tuple` support subscripting directly, and abstract types like `Iterable` and `Sequence` should come from `collections.abc` instead of `typing`. Since Python 3.10, use `X | Y` instead of `typing.Union` and `X | None` instead of `typing.Optional`. For example, use `from collections.abc import Iterator` not `from typing import Iterator`.

New modules should include `from __future__ import annotations` to enable postponed evaluation of annotations ([PEP 563](https://peps.python.org/pep-0563/)). This allows using the latest annotation syntax (e.g., `X | Y`) regardless of the runtime Python version and avoids unnecessary imports of types only needed for annotations.

### Python 3.10 compatibility

This project supports Python 3.10+. Be aware of syntax features that are **not** available in Python 3.10:

- **Multi-line f-string expressions (Python 3.12+):** You cannot break an f-string after the `{` character and continue the expression on the next line.

  ```python
  # fmt: off
  # ❌ Fails on Python 3.10 (only works in Python 3.12+)
  message = f"value={
      some_long_expression
  }"

  # ✅ Works on Python 3.10+: split into concatenated strings.
  message = (
      "value="
      f"{some_long_expression}"
  )
  # fmt: on
  ```

- **Exception groups and `except*` (Python 3.11+).**

- **`Self` type hint (Python 3.11+):** Use `from typing_extensions import Self` instead.

- **`tomllib` (Python 3.11+):** Use the `tomli` fallback pattern:

  ```python
  if sys.version_info >= (3, 11):
      import tomllib
  else:
      import tomli as tomllib  # type: ignore[import-not-found]
  ```

  Place this conditional import **after all normal imports** and **before the `TYPE_CHECKING` block** to allow ruff to sort the normal imports freely.

### YAML workflows

For single-line commands that fit on one line, use plain inline `run:` without any block scalar indicator:

```yaml
# ✅ Preferred for short commands: plain inline.
  - name: Check out repository
    run: git checkout main
```

When a command is too long for a single line, use the folded block scalar (`>`) to split it across multiple lines:

```yaml
# ✅ Preferred for long commands: folded block scalar joins lines with spaces.
  - name: Run linter
    run: >
      uvx --no-progress 'yamllint==1.38.0' --strict --format github
      --config-data "{rules: {line-length: {max: 120}}}" .

# ❌ Avoid: literal block scalar with backslash continuations.
  - name: Run linter
    run: |
      uvx --no-progress 'yamllint==1.38.0' --strict --format github \
        --config-data "{rules: {line-length: {max: 120}}}" .
```

**Why:** The `>` scalar folds newlines into spaces, producing a single command without needing backslash escapes. This is cleaner and avoids issues with trailing whitespace after `\`.

**When to use `|`:** Use literal block scalar (`|`) only when the command requires preserved newlines (e.g., multi-statement scripts, heredocs).

## Testing guidelines

- Use `@pytest.mark.parametrize` when testing the same logic for multiple inputs.
- Keep test logic simple with straightforward asserts.
- Tests should be sorted logically and alphabetically where applicable.
- Test coverage is tracked with `pytest-cov` and reported to Codecov.
- Do not use classes for grouping tests. Write test functions as top-level module functions. Only use test classes when they provide shared fixtures, setup/teardown methods, or class-level state.

## Design principles

### Philosophy

1. Create something that works (to provide business value).
1. Create something that's beautiful (to lower maintenance costs).
1. Work on performance.

### Linting and formatting

[Linting](readme.md#githubworkflowslintyaml-jobs) and [formatting](readme.md#githubworkflowsautofixyaml-jobs) are automated via GitHub workflows. Developers don't need to run these manually during development, but are still expected to do best effort. Push your changes and the workflows will catch any issues and perform the nitpicking.

### Metadata-driven workflow conditions

GitHub Actions lacks conditional step groups—you cannot conditionally skip multiple steps with a single condition. Rather than duplicating `if:` conditions on every step, augment the `gha-utils metadata` subcommand to compute the condition once and reference it from workflow steps.

**Why:** Python code in `gha_utils` is simpler to maintain, test, and debug than complex GitHub Actions workflow logic. Moving conditional checks into metadata extraction centralizes logic in one place.

Example: Instead of a separate "check" step followed by multiple steps with `if: steps.check.outputs.allowed == 'true'`, add the check to metadata output and reference `steps.metadata.outputs.some_check == 'true'`.

### Defensive workflow design

GitHub Actions workflows run in an environment where race conditions, eventual consistency, and partial failures are common. Prefer a **belt-and-suspenders** approach: use multiple independent mechanisms to ensure correctness rather than relying on a single guarantee.

For example, `changelog.yaml`'s `bump-versions` job needs to know the latest released version. Rather than trusting that git tags are always available:

1. **Belt** — The `workflow_run` trigger ensures the job runs *after* the release workflow completes, so tags exist by then.
1. **Suspenders** — The `is_version_bump_allowed()` function falls back to commit message parsing (`[changelog] Release vX.Y.Z`) when tags aren't found.

Apply the same philosophy elsewhere: avoid single points of failure in workflow logic. If a job depends on external state (tags, published packages, API availability), add a fallback or a graceful default. When possible, make operations idempotent (e.g., `--skip-existing` on tag creation) so re-runs are safe.

#### `workflow_run` checkout pitfall

When `workflow_run` fires, `github.event.workflow_run.head_sha` points to the commit that *triggered* the upstream workflow — not the latest commit on `main`. If the release cycle added commits after that trigger (freeze + unfreeze), checking out `head_sha` produces a stale tree and the resulting PR will conflict with current `main`.

**Fix:** Use `github.sha` instead, which for `workflow_run` events resolves to the latest commit on the default branch. The `workflow_run` trigger's purpose is *timing* (ensuring tags exist), not pinning to a specific commit. This applies to any job that needs the current state of `main` after an upstream workflow completes.

### Concurrency implementation

> [!NOTE]
> For user-facing documentation, see [`readme.md` § Concurrency and cancellation](readme.md#concurrency-and-cancellation).

Workflows use two concurrency strategies depending on whether they perform critical release operations.

#### `release.yaml` — SHA-based unique groups

`release.yaml` handles tagging, PyPI publishing, and GitHub release creation. These operations must run to completion. Using conditional `cancel-in-progress: false` doesn't work because it's evaluated on the *new* workflow, not the old one. If a regular commit is pushed while a release workflow is running, the new workflow would cancel the release because they share the same concurrency group.

The solution is to give each release run its own unique group using the commit SHA:

```yaml
concurrency:
  group: >-
    ${{ github.workflow }}-${{
      github.event.pull_request.number
      || (
        (startsWith(github.event.head_commit.message, '[changelog] Release')
        || startsWith(github.event.head_commit.message, '[changelog] Post-release'))
        && github.sha
      )
      || github.ref
    }}
  cancel-in-progress: true
```

| Commit Message                                  | Concurrency Group            | Behavior                     |
| :---------------------------------------------- | :--------------------------- | :--------------------------- |
| `[changelog] Release v4.26.0`                   | `{workflow}-{sha}`           | **Protected** — unique group |
| `[changelog] Post-release bump vX.Y.Z → vX.Y.Z` | `{workflow}-{sha}`           | **Protected** — unique group |
| Any other commit                                | `{workflow}-refs/heads/main` | Cancellable by newer commits |

Both `[changelog] Release` and `[changelog] Post-release` patterns must be matched because when a release is pushed, the event contains **two commits bundled together** and `github.event.head_commit` refers to the most recent one (the post-release bump).

#### Release PR: freeze and unfreeze commits

The `prepare-release` job in `changelog.yaml` creates a PR with exactly **two commits** that must be merged via "Rebase and merge" (never squash):

1. **Freeze commit** (`[changelog] Release vX.Y.Z`) — Freezes everything to the release version: finalizes the changelog date and comparison URL, removes the "unreleased" warning, freezes workflow action references to `@vX.Y.Z`, and freezes CLI invocations to a PyPI version.
1. **Unfreeze commit** (`[changelog] Post-release bump vX.Y.Z → vX.Y.Z`) — Unfreezes for the next development cycle: reverts action references back to `@main`, reverts CLI invocations back to local source (`--from . gha-utils`), adds a new unreleased changelog section, and bumps the version to the next patch.

The auto-tagging job in `release.yaml` depends on these being **separate commits** — it uses `release_commits_matrix` to identify and tag only the freeze commit. Squashing would merge both into one, breaking the tagging logic.

**Squash merge safeguards:** Two mechanisms in `release.yaml` protect against accidental squash merges:

1. **`merge-method-notice` job** — Runs on `pull_request` events when `head_ref == 'prepare-release'`. The job name (`⚠️ Merge with: Rebase and merge`) appears as a visible reminder in the PR checks tab.
1. **`revert-squash-merge` job** — Runs on `push` to `main`. Detects squash merges by checking if the head commit message starts with `` Release `v `` (the PR title pattern) rather than `[changelog] Release v` (the canonical freeze commit pattern). When detected, it automatically reverts the squash commit. The resulting push to `main` re-triggers `prepare-release`, which recreates the release PR with the correct two-commit structure.

On `main`, workflows use `--from . gha-utils` to run the CLI from local source (dogfooding). The freeze commit freezes these to `'gha-utils==X.Y.Z'` (the version being released) so tagged releases reference a published package. This is safe because `release.yaml` runs from the unfreeze commit (HEAD after rebase merge), which has `--from . gha-utils`, and by the time downstream repos use the tagged freeze commit, `publish-pypi` has already published the version. The unfreeze commit reverts them back to `--from . gha-utils` for the next development cycle.

#### Other workflows — simple groups

All other workflows (`lint.yaml`, `autofix.yaml`, `docs.yaml`, `labels.yaml`, `tests.yaml`, `renovate.yaml`) use a simpler pattern. They don't perform irreversible release operations, so a conditional `cancel-in-progress` is sufficient:

```yaml
concurrency:
  group: >-
    ${{ github.workflow }}-${{
      github.event.pull_request.number
      || github.ref
    }}
  cancel-in-progress: >-
    ${{ !startsWith(github.event.head_commit.message,
      '[changelog] Release') }}
```

This pauses cancellation when a release commit triggers the workflow. While this approach has the theoretical flaw of being evaluated on the new workflow, in practice these workflows run fast enough that it's not an issue.

#### `changelog.yaml` — event-scoped groups

`changelog.yaml` includes `github.event_name` in its concurrency group to prevent cross-event cancellation:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event_name }}-${{ github.ref }}
  cancel-in-progress: true
```

**Why `event_name` is required:** `changelog.yaml` has both `push` and `workflow_run` triggers. The `workflow_run` fires when "Build & release" completes. For non-release commits, "Build & release" finishes quickly (most jobs are skipped), firing `workflow_run` before `prepare-release` completes. Without `event_name` in the group, the `workflow_run` event cancels the `push` event's `prepare-release` job — but then skips `prepare-release` itself (due to `if: github.event_name != 'workflow_run'`). The net effect is that `prepare-release` never runs.

Adding `event_name` ensures:

- Push events only cancel other push events (same-event deduplication).
- `workflow_run` events only cancel other `workflow_run` events.
- `prepare-release` (push-triggered) runs to completion uninterrupted.
- There is no `pull_request` trigger, so `github.event.pull_request.number` is omitted from the group expression.

#### Event-specific behavior for `release.yaml`

| Event                 | `github.event.head_commit`             | Concurrency Group             | Cancel Behavior            |
| :-------------------- | :------------------------------------- | :---------------------------- | :------------------------- |
| `push` to `main`      | Set                                    | `{workflow}-refs/heads/main`  | Cancellable                |
| `push` (release)      | Starts with `[changelog] Release`      | `{workflow}-{sha}` *(unique)* | **Never cancelled**        |
| `push` (post-release) | Starts with `[changelog] Post-release` | `{workflow}-{sha}` *(unique)* | **Never cancelled**        |
| `pull_request`        | `null`                                 | `{workflow}-{pr-number}`      | Cancellable within same PR |
| `workflow_call`       | Inherited or `null`                    | Inherited from caller         | Usually cancellable        |

#### `cancel-runs.yaml` — active cancellation on PR close

Passive concurrency groups only cancel runs when a *new* run enters the same group. Closing a PR doesn't fire a new `pull_request` event (for workflows using default activity types: `opened`, `synchronize`, `reopened`), so in-progress and queued runs continue wasting CI resources.

`cancel-runs.yaml` fills this gap with **active cancellation**: it triggers on `pull_request: closed` and uses the GitHub API to cancel all in-progress and queued workflow runs for the PR's branch. This is especially valuable for long-running jobs like Nuitka binary builds (~20 min each across 6 platforms).

The workflow uses `actions/github-script` to list runs by branch and status, then cancels each one. It filters out its own run ID to avoid self-cancellation.

### CLI design

The CLI uses Click Extra for:

- Automatic config file loading
- Colored output and table formatting
- Consistent parameter handling across commands

### Command-line options

Always prefer long-form options over short-form for readability when invoking commands:

- Use `--output` instead of `-o`.
- Use `--verbose` instead of `-v`.
- Use `--recursive` instead of `-r`.

The `gha-utils` CLI defines both short and long-form options for convenience, but workflow files and scripts should use long-form options for clarity.

### uv flags in CI workflows

When invoking `uv` and `uvx` commands in GitHub Actions workflows, use specific flags to ensure reproducible builds and clean logs.

#### `--no-progress` for all CI commands

Always use `--no-progress` in CI environments:

```shell-session
# For uvx
$ uvx --no-progress 'package==1.0.0' command

# For uv subcommands
$ uv --no-progress sync
$ uv --no-progress build
```

**Why:** Progress bars and spinners render poorly in CI logs, producing ANSI escape sequences and fragmented output. Suppressing them results in cleaner, more readable logs.

#### `--frozen` for `uv run` commands

Use `--frozen` with `uv run` to prevent lockfile modifications:

```shell-session
$ uv run --frozen --no-progress -- pytest
$ uv run --frozen --no-progress -- mypy src/
```

**Why:** In CI, the lockfile should be treated as immutable. If dependencies drift from `pyproject.toml`, the workflow should fail early rather than silently resolving different versions. This ensures reproducible builds across runs.

#### When NOT to add these flags

- **`uvx` with pinned versions:** `--frozen` is unnecessary for `uvx 'pkg==1.0.0'` since there's no project lockfile involved—the version is already explicit.
- **`uv tool install`:** Tool installation commands don't use these flags.
- **CLI invocability tests:** When testing that the CLI can be invoked by end users (e.g., `uvx -- gha-utils --version`), omit the flags to test the actual user experience.
- **Local development examples:** Documentation showing local development commands should omit `--frozen` to avoid friction when dependencies change.

#### Flag placement

Place uv-level flags (`--no-progress`) before the subcommand, and run-level flags (`--frozen`) after `run`:

```shell-session
# Correct
$ uv --no-progress run --frozen -- command
$ uvx --no-progress 'package==1.0.0' command

# Incorrect
$ uv run --no-progress --frozen -- command  # --no-progress is a uv flag, not a run flag
```

#### Why explicit flags over environment variables

uv supports environment variables (`UV_NO_PROGRESS=1`, `UV_FROZEN=1`) that could replace
these flags globally. We intentionally avoid them in favor of explicit flags.

**Reasons to prefer explicit flags:**

- **Self-documenting:** Anyone reading the workflow immediately understands the behavior without needing to search for environment variable definitions.
- **Visible in logs:** The exact command with all flags appears in CI output, making debugging easier.
- **No conflicts:** `UV_FROZEN` conflicts with `--locked` in some commands, requiring workarounds like `env -u UV_FROZEN uv lock --check`.
- **Consistent with long-form option principle:** Explicit flags align with our preference for readable, long-form options over terse shortcuts.

Environment variables create "action at a distance"—behavior changes without visible
cause at the point of execution. The verbosity of explicit flags is a feature, not a bug.
