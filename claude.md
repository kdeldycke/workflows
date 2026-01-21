# CLAUDE.md

This file provides guidance to [Claude Code](https://claude.ai/code) when working with code in this repository.

## Project overview

This repository contains two main components:

1. **`gha-utils` CLI** - A command-line utility for GitHub Actions workflows
2. **Reusable GitHub workflows** - A collection of automated workflows for CI/CD

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
│   ├── cli.py             # Click-based CLI definitions
│   ├── changelog.py       # Changelog management
│   ├── mailmap.py         # .mailmap synchronization
│   ├── metadata.py        # Project metadata extraction
│   ├── test_plan.py       # Test plan execution
│   └── matrix.py          # Build matrix generation
├── requirements/          # Pinned dependencies for workflows
└── tests/                 # Test suite
```

### Module layout

| Module | Purpose |
|--------|---------|
| `__main__.py` | Entry point for the `gha-utils` CLI |
| `cli.py` | Click-based command-line interface definitions |
| `changelog.py` | Changelog parsing, updating, and version management |
| `mailmap.py` | Git `.mailmap` file synchronization with contributors |
| `metadata.py` | Extract and combine metadata from Git, GitHub, and `pyproject.toml` |
| `test_plan.py` | Run YAML-based test plans against compiled binaries |
| `matrix.py` | Generate build matrices for GitHub Actions |

### Workflows organization

Reusable workflows are organized by purpose:

- `autofix.yaml` - Auto-formatting and dependency syncing
- `autolock.yaml` - Auto-locking inactive issues
- `changelog.yaml` - Version bumping and release preparation
- `docs.yaml` - Documentation building and deployment
- `labels.yaml` - Label management and PR auto-labeling
- `lint.yaml` - Linting and type checking
- `release.yaml` - Package building, binary compilation, and publishing
- `tests.yaml` - Test execution

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

- Python CLIs in `requirements/*.txt` files (updated by Dependabot)
- GitHub Actions versions in YAML files (updated by Dependabot)
- Project dependencies in `uv.lock` (updated by `sync-uv-lock` workflow)
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

### CLI design

The CLI uses Click Extra for:

- Automatic config file loading
- Colored output and table formatting
- Consistent parameter handling across commands
