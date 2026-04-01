# Development guide

## Downstream repositories

This repository serves as the **canonical reference** for conventions and best practices. When Claude is used in any repository that uses the `repomatic` CLI and its [`[tool.repomatic]` configuration](readme.md#toolrepomatic-configuration), it should follow the same conventions defined here—including the structure and guidelines of this `claude.md` file itself.

In other words, downstream repositories should mirror the patterns established here for code style, documentation, testing, and design principles.

**Contributing upstream:** If Claude spots inefficiencies, potential improvements, performance bottlenecks, missing features, or opportunities for better adaptability in the `repomatic` CLI, its configuration, the reusable workflows, or this `claude.md` file itself, it should propose these changes upstream via a pull request or issue at [`kdeldycke/repomatic`](https://github.com/kdeldycke/repomatic/issues). This benefits all downstream repositories.

**Upstream runtime dependency boundary:** Downstream repos must have only **one runtime dependency** on the upstream repository: reusable workflow `uses:` calls (e.g., `kdeldycke/repomatic/.github/workflows/autofix.yaml@vX.Y.Z`). These are version-pinned to a git tag, giving downstream repos control over when to upgrade. All other references to the upstream (documentation links in PR body templates, footer attribution) are **informational only** — they do not affect functionality if the upstream is unavailable. Do not introduce new runtime dependencies on the upstream repo (e.g., Renovate shareable presets, remote config extends, API calls to upstream) as they create unversioned coupling where an upstream breakage would cascade to all downstream repos simultaneously.

## Commands

### Testing

```shell-session
# Run all tests with coverage.
$ uv run --group test pytest

# Run a single test file.
$ uv run --group test pytest tests/test_changelog.py

# Run a specific test.
$ uv run --group test pytest tests/test_changelog.py::test_function_name

# Run tests in parallel.
$ uv run --group test pytest -n auto
```

### Type checking

```shell-session
$ uv run --group typing mypy repomatic
```

### Running the CLI

```shell-session
# Run locally during development.
$ uv run repomatic --help

# Try without installation using uvx.
$ uvx -- repomatic --help
```

## Documentation requirements

### Scope of `claude.md` vs `readme.md`

- **`claude.md`**: Contributor and Claude-focused directives—code style, testing guidelines, design principles, and internal development guidance.
- **`readme.md`**: User-facing documentation for the `repomatic` CLI and `[tool.repomatic]` configuration—installation, usage, and the workflows that implement them.

When adding new content, consider whether it benefits end users (`readme.md`) or contributors/Claude working on the codebase (`claude.md`).

### Keeping `claude.md` lean

`claude.md` must contain only conventions, policies, rationale, and non-obvious rules that Claude cannot discover by reading the codebase. Actively remove:

- **Structural inventories** — project trees, module tables, workflow lists. Claude can discover these via `Glob`/`Read`.
- **Code examples that duplicate source files** — YAML snippets copied from workflows, Python patterns visible in every module. Reference the source file instead.
- **General programming knowledge** — standard Python idioms, well-known library usage, tool descriptions derivable from imports.
- **Implementation details readable from code** — what a function does, what a workflow's concurrency block looks like. Only the *rationale* for non-obvious choices belongs here.

### Changelog and readme updates

Always update documentation when making changes:

- **`changelog.md`**: Add a bullet point describing **what** changed (new features, bug fixes, behavior changes), not **why**. Keep entries concise and actionable. Justifications and rationale belong in documentation (`readme.md`, Sphinx docs) or code comments, not in the changelog.
- **`readme.md`**: Update relevant sections when adding/modifying workflow jobs, CLI commands, or configuration options.

### Documentation sync

The following documentation artifacts must stay in sync with the code. When changing any of these, update the others:

- **CLI output in `readme.md`**: The inline `uvx -- repomatic` help block, `--version` output, and development version output must match actual CLI output. Re-run the commands and update the pasted text.
- **Version references in `readme.md`**: The `--version` examples and example workflow `@vX.Y.Z` reference must reflect the latest released version.
- **Workflow job descriptions in `readme.md`**: Each `.github/workflows/*.yaml` workflow section must document all jobs by their actual job ID, with accurate descriptions of what they do, their requirements, and skip conditions.
- **Binary download URLs in `readme.md`**: The download table URLs are automatically frozen during releases (`/releases/latest/download/` → `/releases/download/vX.Y.Z/` with versioned filenames). No manual update needed.
- **`[tool.repomatic]` configuration table in `readme.md`**: Generated by `repomatic --table-format github show-config` from the `Config` dataclass docstrings. Re-run the command and update the pasted table when adding, removing, or modifying config fields.
- **PAT permissions**: `REQUIRED_PAT_PERMISSIONS` in `repomatic/github/token.py` is the single source of truth. When changing permissions, update all consumers: the constant and module docstring, the permission table and pre-filled URL in `repomatic/templates/setup-guide.md`, PAT check functions in `repomatic/lint_repo.py`, the `lint-repo` CLI docstring in `repomatic/cli.py`, and the `lint-repo` job description in `readme.md`.
- **Repository configuration expectations**: The `lint-repo` job enforces repo settings described in the setup guide. When adding new setup steps, add a corresponding check to `run_repo_lint()` in `repomatic/lint_repo.py`. If the check cannot be automated, document the limitation in a comment.
- **PAT permission review**: When adding or removing workflow jobs that use `REPOMATIC_PAT`, review `REQUIRED_PAT_PERMISSIONS` to verify the permission set is still minimal and complete. Check `secrets.REPOMATIC_PAT` references across all workflow files to audit actual usage.

### Knowledge placement

Each piece of knowledge has one canonical home, chosen by audience. Other locations get a brief pointer ("See `module.py` for rationale.").

| Audience              | Home                      | Content                                                    |
| :-------------------- | :------------------------ | :--------------------------------------------------------- |
| End users             | `readme.md`               | Installation, configuration, usage.                        |
| Setup walkthroughs    | `setup-guide.md` issue    | Step-by-step setup with deep links to repo settings pages. |
| Developers            | Python docstrings         | Design decisions, trade-offs, "why" explanations.          |
| Workflow maintainers  | YAML comments             | Brief "what" + pointer to Python code for "why."           |
| Bug reporters         | `.github/ISSUE_TEMPLATE/` | Reproduction steps, version commands.                      |
| Contributors / Claude | `claude.md`               | Conventions, policies, non-obvious rules.                  |

**YAML → Python distillation:** When workflow YAML files contain lengthy "why" explanations, migrate the rationale to Python module, class, or constant docstrings (using reST admonitions like `.. note::` and `.. warning::`). Trim the YAML comment to a one-line "what" plus a pointer: `# See repomatic/module.py for rationale.`

### Documenting code decisions

Document design decisions, trade-offs, and non-obvious implementation choices directly in the code using docstring admonitions (reST `.. warning::`, `.. note::`, `.. caution::`), inline comments, and module-level docstrings for constants that need context.

## File naming conventions

### Extensions: prefer long form

Use the longest, most explicit file extension available. For YAML, that means `.yaml` (not `.yml`). Apply the same principle to all extensions (e.g., `.html` not `.htm`, `.jpeg` not `.jpg`).

### Filenames: lowercase

Use lowercase filenames everywhere. Avoid shouting-case names like `FUNDING.YML` or `README.MD`.

### GitHub exceptions

GitHub silently ignores certain files unless they use the exact name it expects. These are the known hard constraints where you **cannot** use `.yaml` or lowercase:

| File                     | Required name                       | Why                                               |
| ------------------------ | ----------------------------------- | ------------------------------------------------- |
| Issue form templates     | `.github/ISSUE_TEMPLATE/*.yml`      | `.yaml` is not recognized for issue forms         |
| Issue template config    | `.github/ISSUE_TEMPLATE/config.yml` | `.yaml` not recognized                            |
| Funding config           | `.github/funding.yml`               | Only `.yml` documented; no evidence `.yaml` works |
| Release notes config     | `.github/release.yml`               | Only `.yml` documented                            |
| Issue template directory | `.github/ISSUE_TEMPLATE/`           | Must be uppercase; GitHub ignores lowercase       |
| Code owners              | `CODEOWNERS`                        | Must be uppercase; no extension                   |

Workflows (`.github/workflows/*.yaml`) and action metadata (`action.yaml`) officially support both `.yml` and `.yaml` — use `.yaml`.

## Code style

### Terminology and spelling

Use correct capitalization for proper nouns and trademarked names:

<!-- typos:off -->

- **PyPI** (not ~~PyPi~~) — the Python Package Index. The "I" is capitalized because it stands for "Index". See [PyPI trademark guidelines](https://pypi.org/trademarks/).
- **GitHub** (not ~~Github~~)
- **GitHub Actions** (not ~~Github Actions~~ or ~~GitHub actions~~)
- **JavaScript** (not ~~Javascript~~)
- **TypeScript** (not ~~Typescript~~)
- **macOS** (not ~~MacOS~~ or ~~macos~~)
- **iOS** (not ~~IOS~~ or ~~ios~~)

<!-- typos:on -->

### Version formatting

The version string is always bare (e.g., `1.2.3`). The `v` prefix is a **tag namespace** — it only appears when the reference is to a git tag or something derived from a tag (action ref, comparison URL, commit message). This aligns with PEP 440, PyPI, and semver conventions.

**Rules:**

1. **No `v` prefix on package versions.** Anywhere the version identifies the *package* (PyPI, changelog heading, CLI output, `pyproject.toml`), use the bare version: `1.2.3`.
2. **`v` prefix on tag references.** Anywhere the version identifies a *git tag* (comparison URLs, action refs, commit messages, PR titles), use `v1.2.3`.
3. **Always backtick-escape versions in prose.** Both `v1.2.3` (tag) and `1.2.3` (package) are identifiers, not natural language. In markdown, wrap them in backticks: `` `v1.2.3` ``, `` `1.2.3` ``. In reST docstrings, use double backticks: ``` ``v1.2.3`` ```.
4. **Development versions** follow PEP 440: `1.2.3.dev0` with optional `+{short_sha}` local identifier.

### Comments and docstrings

- All comments in Python files must end with a period.
- Docstrings use reStructuredText format (vanilla style, not Google/NumPy).
- Documentation in `./docs/` uses MyST markdown format where possible. Fallback to reStructuredText if necessary.
- Keep lines within 88 characters in Python files, including docstrings and comments (ruff default). Markdown files have no line-length limit — do not hard-wrap prose in markdown. Each sentence or logical clause should flow as a single long line; let the renderer handle wrapping.
- Titles in markdown use sentence case.
- **Dataclass field docs:** In dataclasses, document fields with attribute docstrings (a string literal immediately after the field declaration), not `:param:` entries in the class docstring. Attribute docstrings are co-located with the field they describe, recognized by Sphinx, and stay in sync when fields are added or reordered. The class docstring should contain only a summary of the class purpose.
- **CLI help text:** Click command docstrings serve double duty (Sphinx docs and terminal help). Click renders them as plain text, so avoid reST markup in the prose sections that appear in `--help` output. Use plain text for command names, option names, file paths, and tool names. reST markup (double backticks, `:param:`, admonitions) belongs in non-CLI docstrings only.

### `__init__.py` files

Keep `__init__.py` files minimal. They are easy to overlook when scanning a codebase, so avoid placing logic, constants, or re-exports in them. Acceptable content: license headers, package docstrings, `from __future__ import annotations`, and `__version__` (standard Python convention for the root package). Anything else belongs in a named module.

### Imports

- Import from the root package (`from repomatic import cli`), not submodules when possible.
- Place imports at the top of the file, unless avoiding circular imports. **Never use local imports inside functions** — move them to the module level. Local imports hide dependencies, bypass ruff's import sorting, and make it harder to see what a module depends on.
- **Version-dependent imports** (e.g., `tomllib` fallback for Python 3.10) should be placed **after all normal imports** but **before the `TYPE_CHECKING` block**. This allows ruff to freely sort and organize the normal imports above without interference.

### `TYPE_CHECKING` block

Place a module-level `TYPE_CHECKING` block after all imports (including version-dependent conditional imports). Use `TYPE_CHECKING = False` (not `from typing import TYPE_CHECKING`) to avoid importing `typing` at runtime. See existing modules for the canonical pattern.

**Only add `TYPE_CHECKING = False` when there is a corresponding `if TYPE_CHECKING:` block.** If all type-checking imports are removed, remove the `TYPE_CHECKING = False` assignment too — a bare assignment with no consumer is dead code.

### Modern `typing` practices

Use modern equivalents from `collections.abc` and built-in types instead of `typing` imports. Use `X | Y` instead of `Union` and `X | None` instead of `Optional`. New modules should include `from __future__ import annotations` ([PEP 563](https://peps.python.org/pep-0563/)).

### Minimal inline type annotations

Omit type annotations on local variables, loop variables, and assignments when mypy can infer the type from the right-hand side. Add an explicit annotation only when mypy reports an error — e.g., empty collections needing a specific element type (`items: list[Package] = []`), `None` initializations where the intended type is ambiguous, or narrowing a union mypy cannot resolve. Function signatures are unaffected — always annotate parameters and return types.

### Python 3.10 compatibility

This project supports Python 3.10+. Unavailable syntax: multi-line f-string expressions (3.12+; split into concatenated strings instead), exception groups / `except*` (3.11+), `Self` type hint (3.11+; use `from typing_extensions import Self`).

### YAML workflows

For single-line commands, use plain inline `run:`. For multi-line, use the folded block scalar (`>`) which joins lines with spaces — no backslash continuations needed. Use literal block scalar (`|`) only when preserved newlines are required (multi-statement scripts, heredocs).

### Naming conventions for automated operations

CLI commands, workflow job IDs, PR branch names, and PR body template names must all agree on the same verb prefix. This consistency makes the conventions learnable and grepable across all four dimensions.

| Prefix     | Semantics                                       | Source of truth      | Idempotent? | Examples                                          |
| :--------- | :---------------------------------------------- | :------------------- | :---------- | :------------------------------------------------ |
| `sync-X`   | Regenerate from a canonical or external source. | Template, API, repo  | Yes         | `sync-gitignore`, `sync-mailmap`, `sync-uv-lock`  |
| `update-X` | Compute from project state.                     | Lockfile, git log    | Yes         | `update-deps-graph`, `update-checksums`           |
| `format-X` | Rewrite to enforce canonical style.             | Formatter rules      | Yes         | `format-json`, `format-markdown`, `format-python` |
| `fix-X`    | Correct content (auto-fix).                     | Linter/checker rules | Yes         | `fix-typos`                                       |
| `lint-X`   | Check content without modifying it.             | Linter rules         | Yes         | `lint-changelog`                                  |

**Rules:**

1. **Pick the verb that matches the data source.** If the operation pulls from an external template, API, or canonical reference, it is a `sync`. If it computes from local project state (lockfiles, git history, source code), it is an `update`. If it reformats existing content, it is a `format`.
2. **Name the specific tool or file, not a generic category.** The noun in `verb-noun` must identify the concrete tool, file, or resource the operation targets (e.g., `sync-zizmor`, `sync-gitignore`, `sync-mailmap`). Do not use abstract groupings like `sync-linter-configs` or `sync-vcs-configs`. If a second tool is added to a category, create a separate operation for it.
3. **All four dimensions must agree.** When adding a file-modifying operation, the CLI command, workflow job ID, PR branch name, and PR body template file name must all use the same `verb-noun` identifier (e.g., `sync-gitignore` everywhere). For read-only operations (`lint-*`), only the CLI command and workflow job ID apply.
4. **Function names follow the CLI name.** The Python function backing a CLI command uses the underscore equivalent of the CLI name (e.g., `sync_gitignore` for `sync-gitignore`). Exception: when the function name would collide with an imported module, use the Click `name=` parameter to override (e.g., `@repomatic.command(name="update-deps-graph")` on a function named `deps_graph`) or append a `_cmd` suffix (e.g., `sync_uv_lock_cmd` to avoid collision with `from .renovate import sync_uv_lock`).

### Automated operation contracts

Every automated operation follows the [naming conventions](#naming-conventions-for-automated-operations) and is [idempotent](#idempotency-by-default). For the detailed checklists of required properties, invariants, and optional elements for each operation type (sync, update, format/fix, lint, PR body templates), see [`.claude/docs/operation-contracts.md`](.claude/docs/operation-contracts.md).

### Ordering conventions

Keep definitions sorted for readability and to minimize merge conflicts:

- **Workflow jobs**: Ordered by execution dependency (upstream jobs first), then alphabetically within the same dependency level.
- **Python module-level constants and variables**: Alphabetically, unless there is a logical grouping or dependency order. Hard-coded domain constants (e.g., `NOT_ON_PYPI_ADMONITION`, `SKIP_BRANCHES`) should be placed at the top of the file, immediately after imports. These constants encode domain assertions and business rules — surfacing them early gives readers an immediate sense of the assumptions the module operates under.
- **YAML configuration keys**: Alphabetically within each mapping level.
- **Documentation lists and tables**: Alphabetically, unless a logical order (e.g., chronological in changelog) takes precedence.

### Named constants

Do not inline named constants during refactors. If a constant has a name and a docstring, it exists for readability and grep-ability — preserve both. When moving code between modules, carry the constant with it rather than replacing it with a literal.

## Release checklist

See `.claude/skills/repomatic-release/SKILL.md` § Release checklist for the complete list (git tag, GitHub release, binaries, PyPI, changelog).

## Testing guidelines

- Use `@pytest.mark.parametrize` when testing the same logic for multiple inputs. Prefer parametrize over copy-pasted test functions that differ only in their data — it deduplicates test logic, improves readability, and makes it trivial to add new cases.
- Keep test logic simple with straightforward asserts.
- Tests should be sorted logically and alphabetically where applicable.
- Test coverage is tracked with `pytest-cov` and reported to Codecov.
- Do not use classes for grouping tests. Write test functions as top-level module functions. Only use test classes when they provide shared fixtures, setup/teardown methods, or class-level state.
- **`@pytest.mark.once` for run-once tests.** Downstream repos can define a custom `once` marker (in `[tool.pytest].markers`) to tag tests that only need to run once — not across the full CI matrix. Typical candidates: CLI entry point invocability, plugin registration, package metadata checks. The main test matrix filters them out with `pytest -m "not once"`, while a dedicated `once-tests` job runs them on a single runner. This avoids wasting CI minutes on redundant cross-platform runs.
- **CI-only pytest flags belong in workflow steps, not `[tool.pytest].addopts`.** Flags like `--cov-report=xml`, `--junitxml=junit.xml`, and `--override-ini=junit_family=legacy` produce artifacts only needed in CI. Placing them in `addopts` pollutes local test runs with `junit.xml` files and XML coverage reports. Keep `addopts` for flags that apply everywhere (`--cov`, `--cov-report=term`, `--durations`, `--numprocesses`). Pass CI-specific flags in the workflow `run:` step.
- **Coverage configuration belongs in `[tool.coverage]`.** Use the `[tool.coverage]` section in `pyproject.toml` for `run.branch`, `run.source`, and `report.precision` instead of `--cov=<source>`, `--cov-branch`, and `--cov-precision` flags in `addopts`. This keeps coverage configuration canonical and `addopts` clean. The pytest `addopts` should only contain `--cov` (to activate the plugin) and `--cov-report=term` (for local feedback).

## Agent conventions

This repository uses two Claude Code agents defined in `.claude/agents/`. Their definitions should be lean — if a rule belongs in `CLAUDE.md`, put it here and reference it from the agent file. Do not duplicate.

### Source of truth hierarchy

`CLAUDE.md` defines the rules. The codebase and GitHub (issues, PRs, CI logs) are what you measure against those rules. When they disagree, fix the code to match the rules. If the rules are wrong, fix `CLAUDE.md`.

### Common maintenance pitfalls

Patterns that recur across sessions — watch for these proactively:

- **Documentation drift** is the most frequent issue. CLI output, version references, and workflow job descriptions in `readme.md` go stale after every release or refactor. Always verify docs against actual output after changes.
- **CI debugging starts from the URL.** When a workflow fails, fetch the run logs first (`gh run view --log-failed`). Do not guess at the cause. When the user points to a specific failure, diagnose that exact error — do not wander into adjacent or speculative issues (e.g., analyzing Python 3.15 compatibility warnings when the user asked about mypy errors).
- **Type-checking divergence.** Code that passes `mypy` locally may fail in CI where `--python-version 3.10` is used. Always consider the minimum supported Python version.
- **Simplify before adding.** When asked to improve something, first ask whether existing code or tools already cover the case. Remove dead code and unused abstractions before introducing new ones.

### Agent behavior policy

- Agents make fixes in the working tree only. Never commit, push, or create PRs.
- Prefer mechanical enforcement (tests, autofix jobs, linting checks) over prose rules. If a rule can be checked by code, it should be.
- Agent definitions should reference `CLAUDE.md` sections, not restate them.
- qa-engineer is the gatekeeper for agent definition changes.

### Skills

Skills in `.claude/skills/` are user-invocable only (`disable-model-invocation: true`) and follow agent conventions: lean definitions, no duplication with `CLAUDE.md`, reference sections instead of restating rules. Run `repomatic list-skills` to see all skills with descriptions.

### Mechanical vs analytical work

The `repomatic` ecosystem has two layers: a **mechanical layer** (CLI commands and CI workflows that deterministically sync, lint, format, and fix files on every push to `main`) and an **analytical layer** (judgment-based tasks requiring context comparison and trade-off analysis).

Skills should focus on the analytical gaps: custom job content analysis, cross-repo pattern comparison, judgment calls on intentional vs stale divergence, and interactive guidance. Do not duplicate what CI already handles mechanically — see [§ Automated operation contracts](#automated-operation-contracts) for what the mechanical layer covers.

## Design principles

### Philosophy

1. Create something that works (to provide business value).
2. Create something that's beautiful (to lower maintenance costs).
3. Work on performance.

### CLI and configuration as primary abstractions

The `repomatic` CLI and its `[tool.repomatic]` configuration in `pyproject.toml` are the project's primary interfaces. Everything else — reusable workflows, templates, label definitions — is a delivery mechanism. New features should be implemented in the CLI first; workflows should call the CLI, not the other way around. Documentation should lead with what the CLI does and how to configure it.

### Linting and formatting

[Linting](readme.md#githubworkflowslintyaml-jobs) and [formatting](readme.md#githubworkflowsautofixyaml-jobs) are automated via GitHub workflows. Developers don't need to run these manually during development, but are still expected to do best effort. Push your changes and the workflows will catch any issues and perform the nitpicking.

### Metadata-driven workflow conditions

Rather than duplicating `if:` conditions on every workflow step, augment the `repomatic metadata` subcommand to compute the condition once and reference it from workflow steps. Python code in `repomatic` is simpler to maintain, test, and debug than complex GitHub Actions workflow logic.

### Defensive workflow design

GitHub Actions workflows run in an environment where race conditions, eventual consistency, and partial failures are common. Prefer a **belt-and-suspenders** approach: use multiple independent mechanisms to ensure correctness rather than relying on a single guarantee. If a job depends on external state (tags, published packages, API availability), add a fallback or a graceful default. When possible, make operations [idempotent](#idempotency-by-default) so re-runs are safe.

Release-specific workflow design rationale (`workflow_run` checkout pitfall, immutable releases, concurrency strategies, freeze/unfreeze commit structure) is documented in `.claude/skills/repomatic-release/SKILL.md` § Release workflow design.

### Idempotency by default

Workflows and CLI commands must be safe to re-run. Running the same command or workflow twice with the same inputs should produce the same result without errors or unwanted side effects (e.g., duplicate tags, duplicate PR comments, redundant file modifications).

**In practice:**

- Use `--skip-existing` or equivalent guards when creating resources (tags, releases, published packages).
- Check for existing state before writing (e.g., skip adding an admonition if it's already present, skip creating a PR if one already exists for the branch).
- Prefer upsert semantics over create-only semantics.
- Make file-modifying operations convergent: applying the same transformation to an already-transformed file should be a no-op.

**When idempotency is not achievable**, document the reason in a comment or docstring explaining what side effects occur on re-runs and why they are acceptable or unavoidable.

### Skip and move forward, don't rewrite history

When a release goes wrong — squash merge, broken artifact, bad metadata — prefer **skipping the version and releasing the next one** over reverting commits, force-pushing, or rewriting `main`. A burned version number is cheap; a botched automated recovery is not. This mirrors PyPI's [yank](https://peps.python.org/pep-0592/) model: preserve immutability, signal consumers to upgrade.

When designing new workflow safeguards, default to **detection + notification** rather than **detection + automated fix**. The blast radius of a missed notification is zero; the blast radius of a bad automated fix can be catastrophic.

### Command-line options

Always prefer long-form options over short-form for readability in workflow files and scripts (e.g., `--output` not `-o`, `--verbose` not `-v`).

### CLI commands that accept a `--lockfile` or similar path

When a CLI command accepts a path to a project file (e.g., `--lockfile path/to/uv.lock`), any subprocess that needs the project context (like `uv lock`, `uv audit`) must run with `cwd=path.parent`. Otherwise the subprocess resolves against the caller's working directory, not the target project.

### CLI output conventions

CLI commands that produce structured output should separate terminal display from file output:

- **Terminal:** Use `ctx.find_root().print_table(rows, headers)` which respects the global `--table-format` option (github, json, csv, etc.).
- **File output (`--output`):** Write markdown for PR bodies and CI consumption. Use `--output-format` to control transport encoding (e.g., `github-actions` for `$GITHUB_OUTPUT` heredoc wrapping) rather than detecting environment variables implicitly.
- **Boolean feature flags** (e.g., `--release-notes`) should use the `--flag/--no-flag` pattern so both directions are explicitly invocable from workflows.

### Tool runner: flags vs config

When adding or modifying a tool in `TOOL_REGISTRY`, choose the right mechanism for each default based on whether downstream repos should be able to override it:

**`default_flags`** — for operational and cosmetic flags that are always applied and should not be overridable. These are non-negotiable aspects of how repomatic invokes the tool.

- Output formatting: `--color`, `--color-output`.
- Operational mode: `--write-changes`, `--in-place`, `--recursive`.
- Enforcement level: `--strict`, `--strict-front-matter`.
- Network policy: `--offline`.
- Tool-specific quirks with no config-file equivalent (plugin CLI flags).

**`default_config`** (bundled file in `repomatic/data/`) — for behavioral preferences that a downstream repo might legitimately want to override via its own config file or `[tool.X]` section.

- Lint rule selection: which rules to enable/disable/ignore.
- Formatting preferences: numbering style, line length, wrapping.
- Spell-checking dictionaries and exceptions.
- Tool-specific rule configuration (severity, thresholds).

The test: if a downstream repo might reasonably want the opposite setting, it belongs in a config file, not a flag. CLI flags take precedence over config files in most tools, so putting an overridable preference in `default_flags` silently prevents downstream customization.

**Config delivery has two paths** depending on whether the tool accepts a `--config` flag:

- Tools with `config_flag`: the bundled default is passed via that flag at invocation time.
- Tools without `config_flag` (CWD-discovery only): the bundled default is written to the first `native_config_files` path in CWD and cleaned up after invocation.

### Prefer `uv` over `pip` in documentation

Documentation and install pages must use `uv` as the default package installer. When showing how to install the package, use `uv tool install` (for CLI tools) or `uv pip install` (for libraries/extras). Alternative installers (`pip`, `pipx`, etc.) may appear as secondary options in tab sets or dedicated sections, but `uv` must be the primary/default command shown.

### uv flags in CI workflows

When invoking `uv` and `uvx` commands in GitHub Actions workflows:

- **`--no-progress`** on all CI commands (uv-level flag, placed before the subcommand). Progress bars render poorly in CI logs.
- **`--frozen`** on `uv run` commands (run-level flag, placed after `run`). Lockfile should be immutable in CI.
- **Flag placement:** `uv --no-progress run --frozen -- command` (not `uv run --no-progress`).
- **Exceptions:** Omit `--frozen` for `uvx` with pinned versions, `uv tool install`, CLI invocability tests, and local development examples.
- **Prefer explicit flags over environment variables** (`UV_NO_PROGRESS`, `UV_FROZEN`). Flags are self-documenting, visible in logs, avoid conflicts (e.g., `UV_FROZEN` vs `--locked`), and align with the long-form option principle.
- **Per-group `requires-python` in `[tool.uv]`:** Downstream repos whose docs or other dependency groups require newer Python features can restrict specific groups with `dependency-groups.docs = { requires-python = ">= 3.14" }`. This prevents uv from installing incompatible dependencies when running on older Python versions.
