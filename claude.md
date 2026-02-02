# `claude.md`

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
├── .github/workflows/     # Reusable GitHub Actions workflows
├── gha_utils/             # Python CLI package
│   ├── __main__.py        # CLI entry point
│   ├── bundled_config.py  # Bundled config, labels, and workflow templates
│   ├── changelog.py       # Changelog management
│   ├── cli.py             # Click-based CLI definitions
│   ├── deps_graph.py      # Dependency graph generation
│   ├── mailmap.py         # .mailmap synchronization
│   ├── matrix.py          # Build matrix generation
│   ├── metadata.py        # Project metadata extraction
│   ├── release_prep.py    # Release preparation
│   ├── sponsor.py         # GitHub sponsor detection
│   ├── test_plan.py       # Test plan execution
│   └── data/              # Bundled configuration files
├── requirements/          # Pinned dependencies for workflows
└── tests/                 # Test suite
```

### Module layout

| Module              | Purpose                                                             |
| ------------------- | ------------------------------------------------------------------- |
| `__main__.py`       | Entry point for the `gha-utils` CLI                                 |
| `bundled_config.py` | Access bundled config templates, labels, and workflow files         |
| `changelog.py`      | Changelog parsing, updating, and version management                 |
| `cli.py`            | Click-based command-line interface definitions                      |
| `deps_graph.py`     | Generate Mermaid dependency graphs from uv lockfiles                |
| `mailmap.py`        | Git `.mailmap` file synchronization with contributors               |
| `matrix.py`         | Generate build matrices for GitHub Actions                          |
| `metadata.py`       | Extract and combine metadata from Git, GitHub, and `pyproject.toml` |
| `release_prep.py`   | Prepare files for release (dates, URLs, warnings)                   |
| `sponsor.py`        | Check GitHub sponsorship and label issues/PRs from sponsors         |
| `test_plan.py`      | Run YAML-based test plans against compiled binaries                 |

### Workflows organization

Reusable workflows are organized by purpose:

- `autofix.yaml` - Auto-formatting and dependency syncing
- `autolock.yaml` - Auto-locking inactive issues
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

- **`changelog.md`**: Add a bullet point describing user-facing changes (new features, bug fixes, behavior changes).
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

### Comments and docstrings

- All comments in Python files must end with a period.
- Docstrings use reStructuredText format (vanilla style, not Google/NumPy).
- Documentation in `./docs/` uses MyST markdown format where possible. Fallback to reStructuredText if necessary.
- Keep lines within 88 characters in Python files, including docstrings and comments (ruff default). Markdown files have no line-length limit.
- Titles in markdown use sentence case.

### `TYPE_CHECKING` block

Place a module-level `TYPE_CHECKING` block immediately after the module docstring:

```python
TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Iterator
    from ._types import _T, _TNestedReferences
```

### Imports

- Import from the root package (`from gha_utils import cli`), not submodules when possible.
- Place imports at the top of the file, unless avoiding circular imports.

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

- **`tomllib` (Python 3.11+):** Use the `tomli` fallback pattern shown in the codebase.

### YAML workflows

When writing `run:` blocks in GitHub Actions workflows, use the folded block scalar (`>`) to split long commands across multiple lines:

```yaml
# ✅ Preferred: folded block scalar joins lines with spaces.
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

## Design principles

### Philosophy

1. Create something that works (to provide business value).
1. Create something that's beautiful (to lower maintenance costs).
1. Work on performance.

### Linting and formatting

[Linting](readme.md#githubworkflowslintyaml-jobs) and [formatting](readme.md#githubworkflowsautofixyyaml-jobs) are automated via GitHub workflows. Developers don't need to run these manually during development, but are still expected to do best effort. Push your changes and the workflows will catch any issues and perform the nitpicking.

### Metadata-driven workflow conditions

GitHub Actions lacks conditional step groups—you cannot conditionally skip multiple steps with a single condition. Rather than duplicating `if:` conditions on every step, augment the `gha-utils metadata` subcommand to compute the condition once and reference it from workflow steps.

**Why:** Python code in `gha_utils` is simpler to maintain, test, and debug than complex GitHub Actions workflow logic. Moving conditional checks into metadata extraction centralizes logic in one place.

Example: Instead of a separate "check" step followed by multiple steps with `if: steps.check.outputs.allowed == 'true'`, add the check to metadata output and reference `steps.metadata.outputs.some_check == 'true'`.

### Concurrency implementation

> [!NOTE]
> For user-facing documentation, see [`readme.md` § Concurrency and cancellation](readme.md#concurrency-and-cancellation).

All workflows use this concurrency group expression:

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

#### Why release commits need unique groups

Release commits must run to completion for tagging, PyPI publishing, and GitHub release creation. Using conditional `cancel-in-progress: false` doesn't work because it's evaluated on the *new* workflow, not the old one. If a regular commit is pushed while a release workflow is running, the new workflow would cancel the release because they share the same concurrency group.

The solution is to give each release workflow its own unique group using the commit SHA:

| Commit Message                          | Concurrency Group            | Behavior                     |
| :-------------------------------------- | :--------------------------- | :--------------------------- |
| `[changelog] Release v4.26.0`           | `{workflow}-{sha}`           | **Protected** — unique group |
| `[changelog] Post-release version bump` | `{workflow}-{sha}`           | **Protected** — unique group |
| Any other commit                        | `{workflow}-refs/heads/main` | Cancellable by newer commits |

#### Two-commit release push

When a release is pushed, the event contains **two commits bundled together**:

1. `[changelog] Release vX.Y.Z` — the release commit
1. `[changelog] Post-release version bump` — bumps version for next development cycle

Since `github.event.head_commit` refers to the most recent commit (the post-release bump), both commit patterns must be matched to ensure the release workflow gets its own unique group.

#### Event-specific behavior

| Event                 | `github.event.head_commit`             | Concurrency Group             | Cancel Behavior            |
| :-------------------- | :------------------------------------- | :---------------------------- | :------------------------- |
| `push` to `main`      | Set                                    | `{workflow}-refs/heads/main`  | Cancellable                |
| `push` (release)      | Starts with `[changelog] Release`      | `{workflow}-{sha}` *(unique)* | **Never cancelled**        |
| `push` (post-release) | Starts with `[changelog] Post-release` | `{workflow}-{sha}` *(unique)* | **Never cancelled**        |
| `pull_request`        | `null`                                 | `{workflow}-{pr-number}`      | Cancellable within same PR |
| `workflow_call`       | Inherited or `null`                    | Inherited from caller         | Usually cancellable        |
| `schedule`            | `null`                                 | `{workflow}-refs/heads/main`  | Cancellable                |
| `issues` / `opened`   | `null`                                 | `{workflow}-{issue-ref}`      | Cancellable                |

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
