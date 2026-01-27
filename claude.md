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
- Keep lines within 88 characters.
- Titles in markdown use sentence case.

### Type checking

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

## Testing guidelines

- Use `@pytest.mark.parametrize` when testing the same logic for multiple inputs.
- Keep test logic simple with straightforward asserts.
- Tests should be sorted logically and alphabetically where applicable.
- Test coverage is tracked with `pytest-cov` and reported to Codecov.

## Design principles

### Dependency pinning

All dependencies are pinned to specific versions for stability and reproducibility:

- Python CLIs in `requirements/*.txt` files (updated by Renovate)
- GitHub Actions versions in YAML files (updated by Renovate)
- Project dependencies in `uv.lock` (updated by Renovate)
- 7-day cooldown via `uv --exclude-newer` option

### Self-referential workflows

Workflows reference themselves via GitHub URLs:

- Development: points to `main` branch
- Released: points to tagged version (e.g., `v4.25.6`)
- The `prepare-release` job rewrites URLs from `main` to the release tag

### Metadata extraction

The `project-metadata` job runs first in most workflows to:

- Extract and combine data from Git, GitHub, and `pyproject.toml`
- Share complex data across jobs (like build matrices)
- Fix GitHub Actions quirks and limitations

### Metadata-driven workflow conditions

GitHub Actions lacks conditional step groups—you cannot conditionally skip multiple
steps with a single condition. Rather than duplicating `if:` conditions on every step,
augment the `gha-utils metadata` subcommand to compute the condition once and reference
it from workflow steps.

**Why:** Python code in `gha_utils` is simpler to maintain, test, and debug than
complex GitHub Actions workflow logic. Moving conditional checks into metadata
extraction centralizes logic in one place.

Example: Instead of a separate "check" step followed by multiple steps with
`if: steps.check.outputs.allowed == 'true'`, add the check to metadata output
and reference `steps.metadata.outputs.some_check == 'true'`.

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
