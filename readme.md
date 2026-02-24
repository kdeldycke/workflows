# `gha-utils` CLI + reusable workflows

[![Last release](https://img.shields.io/pypi/v/gha-utils.svg)](https://pypi.org/project/gha-utils/)
[![Python versions](https://img.shields.io/pypi/pyversions/gha-utils.svg)](https://pypi.org/project/gha-utils/)
[![Downloads](https://static.pepy.tech/badge/gha_utils/month)](https://pepy.tech/projects/gha_utils)
[![Unittests status](https://github.com/kdeldycke/workflows/actions/workflows/tests.yaml/badge.svg?branch=main)](https://github.com/kdeldycke/workflows/actions/workflows/tests.yaml?query=branch%3Amain)
[![Coverage status](https://codecov.io/gh/kdeldycke/workflows/branch/main/graph/badge.svg)](https://app.codecov.io/gh/kdeldycke/workflows)

> [!CAUTION]
> **This project has been renamed.** The `gha-utils` package is now
> [`repokit`](https://pypi.org/project/repokit/). This is the **final release**
> under the `gha-utils` name. Please migrate:
>
> ```shell-session
> $ uvx -- repokit --help
> ```
>
> The GitHub repository moves from
> [`kdeldycke/workflows`](https://github.com/kdeldycke/workflows) to
> [`kdeldycke/repokit`](https://github.com/kdeldycke/repokit).

[Reusable workflows](#reusable-workflows-collection) and a standalone [CLI (`gha-utils`)](#gha-utils-cli) that let you **release Python packages multiple times a day with only 2-clicks**. Designed for `uv`-based Python projects, but usable for other projects too.

[**Maintainer-in-the-loop**](#maintainer-in-the-loop): nothing is done behind your back. A PR or issue is created every time a change is proposed or action is needed.

Automates:

- Version bumping
- Changelog management
- Formatting autofix for: Python, Markdown, JSON, typos
- Linting: Python types with `mypy`, YAML, `zsh`, GitHub Actions, workflow security, URLS & redirects, Awesome lists, secrets
- Compiling of Python binaries for Linux / macOS / Windows on `x86_64` & `arm64`
- Building of Python packages and upload to PyPI
- Produce attestations
- Git version tagging and GitHub release creation
- Synchronization of: `uv.lock`, `.gitignore`, `.mailmap` and Mermaid dependency graph
- Auto-locking of inactive closed issues
- Static image optimization
- Sphinx documentation building & deployment, and `autodoc` updates
- Label management, with file-based and content-based rules
- Awesome list template synchronization
- Address [GitHub Actions limitations](#github-actions-limitations)

## GitHub Actions limitations

GitHub Actions has several design limitations. This repository works around most of them:

| Limitation                                                  | Status             | Addressed by                                                                                                                                                      |
| :---------------------------------------------------------- | :----------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| No conditional step groups                                  | ✅ Addressed       | [`project-metadata` job](#what-is-this-project-metadata-job) + [`gha-utils metadata`](#gha-utils-cli)                                                             |
| Workflow inputs only accept strings                         | ✅ Addressed       | String parsing in [`gha-utils`](#gha-utils-cli)                                                                                                                   |
| Matrix outputs not cumulative                               | ✅ Addressed       | [`project-metadata`](#what-is-this-project-metadata-job) pre-computes matrices                                                                                    |
| `cancel-in-progress` evaluated on new run, not old          | ✅ Addressed       | [SHA-based concurrency groups](#concurrency-and-cancellation) in [`release.yaml`](#githubworkflowsreleaseyaml-jobs)                                               |
| Cross-event concurrency cancellation                        | ✅ Addressed       | [`event_name` in `changelog.yaml` concurrency group](#concurrency-and-cancellation)                                                                               |
| PR close doesn't cancel runs                                | ✅ Addressed       | [`cancel-runs.yaml`](#githubworkflowscancel-runsyaml-jobs)                                                                                                        |
| `GITHUB_TOKEN` can't modify workflow files                  | ✅ Addressed       | [`WORKFLOW_UPDATE_GITHUB_PAT` fine-grained PAT](#solution-fine-grained-personal-access-token)                                                                     |
| Tag pushes from Actions don't trigger workflows             | ✅ Addressed       | [Custom PAT](#solution-fine-grained-personal-access-token) for tag operations                                                                                     |
| Default input values not propagated across events           | ✅ Addressed       | Manual defaults in `env:` section                                                                                                                                 |
| `head_commit` only has latest commit in multi-commit pushes | ✅ Addressed       | [`gha-utils metadata`](#what-is-this-project-metadata-job) extracts full commit range                                                                             |
| `actions/checkout` uses merge commit for PRs                | ✅ Addressed       | Explicit `ref: github.event.pull_request.head.sha`                                                                                                                |
| Multiline output encoding fragile                           | ✅ Addressed       | Random delimiters in `gha_utils/github.py`                                                                                                                        |
| Branch deletion doesn't cancel runs                         | ❌ Not addressed   | Same root cause as PR close; partially mitigated by [`cancel-runs.yaml`](#githubworkflowscancel-runsyaml-jobs) since branch deletion typically follows PR closure |
| No native way to depend on all matrix jobs completing       | ❌ Not addressed   | GitHub limitation; use `needs:` with a summary job as workaround                                                                                                  |
| `actionlint` false positives for runtime env vars           | 🚫 Not addressable | Linter limitation, not GitHub's                                                                                                                                   |

## Quick start

```shell-session
$ cd my-project
$ uvx -- gha-utils init
$ git add . && git commit -m "Bootstrap reusable workflows" && git push
```

That's it. The workflows will start running and guide you through any remaining setup (like [creating a `WORKFLOW_UPDATE_GITHUB_PAT` secret](#solution-fine-grained-personal-access-token)) via issues and PRs in your repository.

Run `gha-utils init --help` to see available components and options.

## `gha-utils` CLI

`gha-utils` stands for *GitHub Actions workflows utilities*.

### Try it

Thanks to `uv`, you can run it in one command, without installation or venv:

```shell-session
$ uvx -- gha-utils
Usage: gha-utils [OPTIONS] COMMAND [ARGS]...

Options:
  --time / --no-time    Measure and print elapsed execution time.  [default:
                        no-time]
  --color, --ansi / --no-color, --no-ansi
                        Strip out all colors and all ANSI codes from output.
                        [default: color]
  --config CONFIG_PATH  Location of the configuration file. Supports local path
                        with glob patterns or remote URL.  [default:
                        ~/Library/Application Support/gha-
                        utils/*.toml|*.yaml|*.yml|*.json|*.ini]
  --no-config           Ignore all configuration files and only use command
                        line parameters and environment variables.
  --show-params         Show all CLI parameters, their provenance, defaults and
                        value, then exit.
  --table-format [aligned|asciidoc|csv|csv-excel|csv-excel-tab|csv-unix|double-grid|double-outline|fancy-grid|fancy-outline|github|grid|heavy-grid|heavy-outline|html|jira|latex|latex-booktabs|latex-longtable|latex-raw|mediawiki|mixed-grid|mixed-outline|moinmoin|orgtbl|outline|pipe|plain|presto|pretty|psql|rounded-grid|rounded-outline|rst|simple|simple-grid|simple-outline|textile|tsv|unsafehtml|vertical|youtrack]
                        Rendering style of tables.  [default: rounded-outline]
  --verbosity LEVEL     Either CRITICAL, ERROR, WARNING, INFO, DEBUG.
                        [default: WARNING]
  -v, --verbose         Increase the default WARNING verbosity by one level for
                        each additional repetition of the option.  [default: 0]
  --version             Show the version and exit.
  -h, --help            Show this message and exit.

Commands:
  broken-links       Manage broken links issue lifecycle
  changelog          Maintain a Markdown-formatted changelog
  check-renovate     Check Renovate migration prerequisites
  git-tag              Create and push a Git tag
  init                 Bootstrap a repository to use reusable workflows
  lint-changelog       Check changelog dates against release dates
  lint-repo            Run repository consistency checks
  metadata             Output project metadata
  pr-body              Generate PR body with workflow metadata
  release-prep         Prepare files for a release
  setup-guide          Manage setup guide issue lifecycle
  sponsor-label        Label issues/PRs from GitHub sponsors
  sync-bumpversion     Sync bumpversion config from bundled template
  sync-gitignore       Sync .gitignore from gitignore.io templates
  sync-linter-configs  Sync linter config files from bundled definitions
  sync-mailmap         Sync Git's .mailmap file with missing contributors
  sync-renovate        Sync Renovate config from canonical reference
  sync-skills          Sync Claude Code skills from bundled definitions
  sync-uv-lock         Re-lock and revert if only timestamp noise changed
  test-plan            Run a test plan from a file against a binary
  update-checksums     Update SHA-256 checksums for binary downloads
  update-deps-graph    Generate dependency graph from uv lockfile
  verify-binary        Verify binary architecture using exiftool
  version-check      Check if a version bump is allowed
  workflow           Manage downstream workflow caller files
```

```shell-session
$ uvx -- gha-utils --version
gha-utils, version 5.9.1
```

That's the best way to get started with `gha-utils` and experiment with it.

> [!TIP]
> Development versions use a `.devN` suffix per [PEP 440](https://peps.python.org/pep-0440/#developmental-releases). When running from a Git clone, the short commit hash is appended as a local version identifier (e.g., `5.9.2.dev0+abc1234`).

### Executables

To ease deployment, standalone executables of `gha-utils`'s latest version are available as direct downloads for several platforms and architectures:

| Platform    | `arm64`                                                                                                                               | `x86_64`                                                                                                                          |
| :---------- | ------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **Linux**   | [Download `gha-utils-linux-arm64.bin`](https://github.com/kdeldycke/workflows/releases/latest/download/gha-utils-linux-arm64.bin)     | [Download `gha-utils-linux-x64.bin`](https://github.com/kdeldycke/workflows/releases/latest/download/gha-utils-linux-x64.bin)     |
| **macOS**   | [Download `gha-utils-macos-arm64.bin`](https://github.com/kdeldycke/workflows/releases/latest/download/gha-utils-macos-arm64.bin)     | [Download `gha-utils-macos-x64.bin`](https://github.com/kdeldycke/workflows/releases/latest/download/gha-utils-macos-x64.bin)     |
| **Windows** | [Download `gha-utils-windows-arm64.exe`](https://github.com/kdeldycke/workflows/releases/latest/download/gha-utils-windows-arm64.exe) | [Download `gha-utils-windows-x64.exe`](https://github.com/kdeldycke/workflows/releases/latest/download/gha-utils-windows-x64.exe) |

That way you have a chance to try it out without installing Python or `uv`. Or embed it in your CI/CD pipelines running on minimal images. Or run it on old platforms without worrying about dependency hell.

> [!NOTE]
> ABI targets:
>
> ```shell-session
> $ file ./gha-utils-*
> ./gha-utils-linux-arm64.bin:   ELF 64-bit LSB pie executable, ARM aarch64, version 1 (SYSV), dynamically linked, interpreter /lib/ld-linux-aarch64.so.1, BuildID[sha1]=520bfc6f2bb21f48ad568e46752888236552b26a, for GNU/Linux 3.7.0, stripped
> ./gha-utils-linux-x64.bin:     ELF 64-bit LSB pie executable, x86-64, version 1 (SYSV), dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, BuildID[sha1]=56ba24bccfa917e6ce9009223e4e83924f616d46, for GNU/Linux 3.2.0, stripped
> ./gha-utils-macos-arm64.bin:   Mach-O 64-bit executable arm64
> ./gha-utils-macos-x64.bin:     Mach-O 64-bit executable x86_64
> ./gha-utils-windows-arm64.exe: PE32+ executable (console) Aarch64, for MS Windows
> ./gha-utils-windows-x64.exe:   PE32+ executable (console) x86-64, for MS Windows
> ```

### Development version

To play with the latest development version of `gha-utils`, you can run it directly from the repository:

```shell-session
$ uvx --from git+https://github.com/kdeldycke/workflows -- gha-utils --version
gha-utils, version 5.9.2.dev0+3eb8894
```

## Reusable workflows collection

This repository contains workflows to automate most of the boring tasks in the form of [reusable GitHub Actions workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows).

### Example usage

The fastest way to adopt these workflows is with `gha-utils init` (see [Quick start](#quick-start)). It generates all the thin-caller workflow files for you.

If you prefer to set up a single workflow manually, create a `.github/workflows/lint.yaml` file [using the `uses` syntax](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows#calling-a-reusable-workflow):

```yaml
name: Lint
on:
  push:
  pull_request:

jobs:
  lint:
    uses: kdeldycke/workflows/.github/workflows/lint.yaml@v5.9.1
```

> [!IMPORTANT]
> [Concurrency is already configured](#concurrency-and-cancellation) in the reusable workflows—you don't need to re-specify it in your calling workflow.

### `[tool.gha-utils]` configuration

Downstream projects can customize workflow behavior by adding a `[tool.gha-utils]` section in their `pyproject.toml`:

```toml
[tool.gha-utils]
nuitka = false
nuitka-extra-args = [
  "--include-data-files=my_pkg/data/*.json=my_pkg/data/",
]
unstable-targets = ["linux-arm64", "windows-arm64"]
test-plan-file = "./tests/cli-test-plan.yaml"
timeout = 120
test-plan = "- args: --version"
gitignore-location = "./.gitignore"
gitignore-extra-categories = ["terraform", "go"]
gitignore-extra-content = '''
junit.xml

# Claude Code
.claude/
'''
dependency-graph-output = "./docs/assets/dependencies.mmd"
dependency-graph-all-groups = true
dependency-graph-all-extras = true
dependency-graph-no-groups = []
dependency-graph-no-extras = []
dependency-graph-level = 0
extra-label-files = ["https://example.com/my-labels.toml"]
extra-file-rules = "docs:\n  - docs/**"
extra-content-rules = "security:\n  - '(CVE|vulnerability)'"
renovate-sync = false
workflow-sync = false
workflow-sync-exclude = ["debug.yaml", "autolock.yaml"]
```

| Option                        | Type      | Default                                           | Description                                                                                                                                          |
| :---------------------------- | :-------- | :------------------------------------------------ | :--------------------------------------------------------------------------------------------------------------------------------------------------- |
| `nuitka`                      | bool      | `true`                                            | Enable [Nuitka binary compilation](#githubworkflowsreleaseyaml-jobs). Set to `false` for projects with `[project.scripts]` that don't need binaries. |
| `nuitka-extra-args`           | list[str] | `[]`                                              | Extra Nuitka CLI arguments for binary compilation (e.g., `--include-data-files`, `--include-package-data`). Passed via the build matrix.             |
| `unstable-targets`            | list[str] | `[]`                                              | Nuitka build targets allowed to fail without blocking the release (e.g., `["linux-arm64"]`).                                                         |
| `test-plan-file`              | str       | `"./tests/cli-test-plan.yaml"`                    | Path to the YAML test plan file for binary testing. Read directly by `test-plan` subcommand; CLI args override.                                      |
| `timeout`                     | int       | *(none)*                                          | Timeout in seconds for each binary test. Read directly by `test-plan` subcommand; CLI `--timeout` overrides.                                         |
| `test-plan`                   | str       | *(none)*                                          | Inline YAML test plan for binary testing. Read directly by `test-plan` subcommand; CLI `--plan-file`/`--plan-envvar` override.                       |
| `gitignore-location`          | str       | `"./.gitignore"`                                  | File path of the `.gitignore` to update.                                                                                                             |
| `gitignore-extra-categories`  | list[str] | `[]`                                              | Additional categories to add to the `.gitignore` file (e.g., `["terraform", "go"]`).                                                                 |
| `gitignore-extra-content`     | str       | See [example above](#toolgha-utils-configuration) | Additional content to append to the generated `.gitignore`. Supports TOML multi-line literal strings (`'''...'''`).                                  |
| `dependency-graph-output`     | str       | `"./docs/assets/dependencies.mmd"`                | Location of the generated dependency graph file. Read directly by `update-deps-graph` subcommand; CLI `--output` overrides.                          |
| `dependency-graph-all-groups` | bool      | `true`                                            | Include all dependency groups in the graph. Set to `false` to exclude development groups (docs, test, typing). CLI `--all-groups` overrides.         |
| `dependency-graph-all-extras` | bool      | `true`                                            | Include all optional extras in the graph. CLI `--all-extras` overrides.                                                                              |
| `dependency-graph-no-groups`  | list[str] | `[]`                                              | Dependency groups to exclude from the graph. Equivalent to `--no-group` for each entry. Takes precedence over `dependency-graph-all-groups`.         |
| `dependency-graph-no-extras`  | list[str] | `[]`                                              | Optional extras to exclude from the graph. Equivalent to `--no-extra` for each entry. Takes precedence over `dependency-graph-all-extras`.           |
| `dependency-graph-level`      | int       | *(none)*                                          | Maximum depth of the dependency graph. `1` = primary deps only, `2` = primary + their deps, etc. CLI `--level` overrides.                            |
| `extra-label-files`           | list[str] | `[]`                                              | URLs of additional label definition files (JSON, JSON5, TOML, or YAML) downloaded and applied by `labelmaker`.                                       |
| `extra-file-rules`            | str       | `""`                                              | Additional YAML rules appended to the bundled file-based labeller configuration.                                                                     |
| `extra-content-rules`         | str       | `""`                                              | Additional YAML rules appended to the bundled content-based labeller configuration.                                                                  |
| `renovate-sync`               | bool      | `true`                                            | Enable Renovate config sync. Set to `false` to skip `sync-renovate` in the autofix workflow.                                                         |
| `workflow-sync`               | bool      | `true`                                            | Enable workflow sync. Set to `false` to skip `workflow create` and `workflow sync` when no explicit filenames are given.                             |
| `workflow-sync-exclude`       | list[str] | `[]`                                              | Workflow filenames to exclude from sync/create (e.g., `["debug.yaml"]`). Explicit CLI positional arguments override this list.                       |

### 🪄 [`.github/workflows/autofix.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/autofix.yaml)

*Setup* — guide new users through initial configuration:

- 📖 **Setup guide** (`setup-guide`)

  - Detects missing `WORKFLOW_UPDATE_GITHUB_PAT` secret and opens an issue with step-by-step setup instructions
  - Automatically closes the issue once the secret is configured
  - **Skip**: upstream `kdeldycke/workflows` repo, `workflow_call` events

*Formatters* — rewrite files to enforce canonical style:

- 🐍 **Format Python** (`format-python`)

  - Auto-formats Python code using [`autopep8`](https://github.com/hhatto/autopep8) and [`ruff`](https://github.com/astral-sh/ruff)
  - **Requires**:
    - Python files (`**/*.{py,pyi,pyw,pyx,ipynb}`) in the repository, or
    - documentation files (`**/*.{markdown,mdown,mkdn,mdwn,mkd,md,mdtxt,mdtext,mdx,rst,tex}`)

- 📐 **Format `pyproject.toml`** (`format-pyproject`)

  - Auto-formats `pyproject.toml` using [`pyproject-fmt`](https://github.com/tox-dev/pyproject-fmt)
  - **Requires**:
    - Python package with a `pyproject.toml` file

- ✍️ **Format Markdown** (`format-markdown`)

  - Auto-formats Markdown files using [`mdformat`](https://github.com/hukkin/mdformat)
  - **Requires**:
    - Markdown files (`**/*.{markdown,mdown,mkdn,mdwn,mkd,md,mdtxt,mdtext,mdx}`) in the repository

- 🔧 **Format JSON** (`format-json`)

  - Auto-formats JSON, JSONC, and JSON5 files using [Biome](https://github.com/biomejs/biome)
  - **Requires**:
    - JSON files (`**/*.{json,jsonc,json5}`, `**/.code-workspace`, `!**/package-lock.json`) in the repository

*Fixers* — correct or improve existing content in-place:

- ✏️ **Fix typos** (`fix-typos`)

  - Automatically fixes typos in the codebase using [`typos`](https://github.com/crate-ci/typos)

- 📋 **Lint changelog** (`lint-changelog`)

  - Checks and fixes changelog dates and admonitions using [`gha-utils lint-changelog`](https://github.com/kdeldycke/workflows/blob/main/gha_utils/changelog.py)

- 🖼️ **Optimize images** (`optimize-images`)

  - Compresses images in the repository using [`image-actions`](https://github.com/calibreapp/image-actions)
  - **Requires**:
    - Image files (`**/*.{jpeg,jpg,png,webp,avif}`) in the repository

*Syncers* — regenerate files from external sources or project state:

- 🙈 **Sync `.gitignore`** (`sync-gitignore`)

  - Regenerates `.gitignore` from [gitignore.io](https://github.com/toptal/gitignore.io) templates using [`gha-utils sync-gitignore`](https://github.com/kdeldycke/workflows/blob/main/gha_utils/cli.py)
  - **Requires**:
    - A `.gitignore` file in the repository

- 🔄 **Sync bumpversion config** (`sync-bumpversion`)

  - Syncs the `[tool.bumpversion]` configuration in `pyproject.toml` using [`gha-utils sync-bumpversion`](https://github.com/kdeldycke/workflows/blob/main/gha_utils/cli.py)
  - **Skipped if**:
    - `[tool.bumpversion]` section already exists in `pyproject.toml`

- 🔄 **Sync linter configs** (`sync-linter-configs`)

  - Syncs linter configuration files (`.github/zizmor.yml`) with the canonical references from [`gha-utils`](https://github.com/kdeldycke/workflows/blob/main/gha_utils/data/zizmor.yml)

- 🔄 **Sync `renovate.json5`** (`sync-renovate`)

  - Syncs the local `renovate.json5` with the canonical reference from [`gha-utils`](https://github.com/kdeldycke/workflows/blob/main/gha_utils/init_project.py), stripping repo-specific settings (`customManagers`, `assignees`)
  - **Skipped if**:
    - Repository is [`kdeldycke/workflows`](https://github.com/kdeldycke/workflows) itself (the upstream source)
    - No `renovate.json5` file in the repository root
    - `renovate-sync = false` in `[tool.gha-utils]`

- 🪢 **Sync workflows** (`sync-workflows`)

  - Syncs [workflows from the upstream `kdeldycke/workflows`](https://github.com/kdeldycke/workflows/tree/main/.github/workflows) repository using [`gha-utils workflow sync`](https://github.com/kdeldycke/workflows/blob/main/gha_utils/github/workflow_sync.py)
  - **Skipped if**:
    - Repository is [`kdeldycke/workflows`](https://github.com/kdeldycke/workflows) itself (the upstream source)

- 📬 **Sync `.mailmap`** (`sync-mailmap`)

  - Keeps `.mailmap` file up to date with contributors using [`gha-utils sync-mailmap`](https://github.com/kdeldycke/workflows/blob/main/gha_utils/mailmap.py)
  - **Requires**:
    - A `.mailmap` file in the repository root

- 🕸️ **Update dependency graph** (`update-deps-graph`)

  - Generates a Mermaid dependency graph of the Python project using [`gha-utils update-deps-graph`](https://github.com/kdeldycke/workflows/blob/main/gha_utils/deps_graph.py)
  - **Requires**:
    - Python package with a `uv.lock` file

- 📚 **Update docs** (`update-docs`)

  - Regenerates Sphinx autodoc files using [`sphinx-apidoc`](https://github.com/sphinx-doc/sphinx)
  - Runs `docs/docs_update.py` if present to generate dynamic content (tables, diagrams, Sphinx directives)
  - **Requires**:
    - Python package with a `pyproject.toml` file
    - `docs` dependency group
    - Sphinx autodoc enabled (checks for `sphinx.ext.autodoc` in `docs/conf.py`)

- 🌟 **Sync awesome template** (`sync-awesome-template`)

  - Syncs awesome list projects from the [`awesome-template`](https://github.com/kdeldycke/awesome-template) repository using [`actions-template-sync`](https://github.com/AndreasAugustin/actions-template-sync)
  - **Requires**:
    - Repository name starts with `awesome-`
    - Repository is not [`awesome-template`](https://github.com/kdeldycke/awesome-template) itself

### 🔒 [`.github/workflows/autolock.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/autolock.yaml)

- 🔒 **Lock inactive threads** (`lock`)

  - Automatically locks closed issues and PRs after 90 days of inactivity using [`lock-threads`](https://github.com/dessant/lock-threads)

### 🩺 [`.github/workflows/debug.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/debug.yaml)

- 🩺 **Dump context** (`dump-context`)

  - Dumps GitHub Actions context and runner environment info across all build targets using [`ghaction-dump-context`](https://github.com/crazy-max/ghaction-dump-context)
  - Useful for debugging runner differences and CI environment issues
  - **Runs on**:
    - Push to `main` (only when `debug.yaml` itself changes)
    - Monthly schedule
    - Manual dispatch
    - `workflow_call` from downstream repositories

### ✂️ [`.github/workflows/cancel-runs.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/cancel-runs.yaml)

- ✂️ **Cancel PR runs** (`cancel-runs`)

  - Cancels all in-progress and queued workflow runs for a PR's branch when the PR is closed
  - Prevents wasted CI resources from long-running jobs (e.g. Nuitka binary builds) that continue after a PR is closed
  - GitHub Actions does not natively cancel runs on PR close — the `concurrency` mechanism only triggers cancellation when a *new* run enters the same group

### 🆙 [`.github/workflows/changelog.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/changelog.yaml)

- 🆙 **Bump versions** (`bump-versions`)

  - Creates PRs for minor and major version bumps using [`bump-my-version`](https://github.com/callowayproject/bump-my-version)
  - Syncs `uv.lock` to include the new version in the same commit
  - Uses commit message parsing as fallback when tags aren't available yet
  - **Requires**:
    - `bump-my-version` configuration in `pyproject.toml`
    - A `changelog.md` file
  - **Runs on**:
    - Schedule (daily at 6:00 UTC)
    - Manual dispatch
    - After `release.yaml` workflow completes successfully (via `workflow_run` trigger, to ensure tags exist before checking bump eligibility). Checks out the latest `main` HEAD, not the triggering workflow's commit.

- 🎬 **Prepare release** (`prepare-release`)

  - Creates a release PR with two commits: a **freeze commit** that freezes everything to the release version, and an **unfreeze commit** that reverts to development references and bumps the patch version
  - Uses [`bump-my-version`](https://github.com/callowayproject/bump-my-version) and [`gha-utils changelog`](https://github.com/kdeldycke/workflows/blob/main/gha_utils/changelog.py)
  - Must be merged with "Rebase and merge" (not squash) — the auto-tagging job needs both commits separate
  - **Requires**:
    - `bump-my-version` configuration in `pyproject.toml`
    - A `changelog.md` file
  - **Runs on**:
    - Push to `main` (when `changelog.md`, `pyproject.toml`, or workflow files change)
    - Manual dispatch
    - `workflow_call` from downstream repositories

### 📚 [`.github/workflows/docs.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/docs.yaml)

These jobs require a `docs` [dependency group](https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-groups) in `pyproject.toml` so they can determine the right Sphinx version to install and its dependencies:

```toml
[dependency-groups]
docs = [
    "furo",
    "myst-parser",
    "sphinx",
    …
]
```

- 📖 **Deploy Sphinx doc** (`deploy-docs`)

  - Builds Sphinx-based documentation and publishes it to GitHub Pages using [`sphinx`](https://github.com/sphinx-doc/sphinx) and [`gh-pages`](https://github.com/peaceiris/actions-gh-pages)
  - **Requires**:
    - Python package with a `pyproject.toml` file
    - `docs` dependency group
    - Sphinx configuration file at `docs/conf.py`

- 🔗 **Sphinx linkcheck** (`check-sphinx-links`)

  - Runs Sphinx's built-in [`linkcheck`](https://www.sphinx-doc.org/en/master/usage/builders/index.html#sphinx.builders.linkcheck.CheckExternalLinksBuilder) builder to detect broken auto-generated links (intersphinx, autodoc, type annotations) that Lychee cannot see
  - Creates/updates issues for broken documentation links found
  - **Requires**:
    - Python package with a `pyproject.toml` file
    - `docs` dependency group
    - Sphinx configuration file at `docs/conf.py`
  - **Skipped for**:
    - Pull requests
    - `prepare-release` branch
    - Post-release version bump commits

- 💔 **Check broken links** (`check-broken-links`)

  - Checks for broken links in documentation using [`lychee`](https://github.com/lycheeverse/lychee)
  - Creates/updates issues for broken links found
  - **Requires**:
    - Documentation files (`**/*.{markdown,mdown,mkdn,mdwn,mkd,md,mdtxt,mdtext,mdx,rst,tex}`) in the repository
  - **Skipped for**:
    - All PRs (only runs on push to main)
    - `prepare-release` branch
    - Post-release bump commits

### 🏷️ [`.github/workflows/labels.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/labels.yaml)

- 🔄 **Sync labels** (`sync-labels`)

  - Synchronizes repository labels using [`labelmaker`](https://github.com/jwodder/labelmaker)
  - Uses [`labels.toml`](https://github.com/kdeldycke/workflows/blob/main/gha_utils/data/labels.toml) with multiple profiles:
    - `default` profile applied to all repositories
    - `awesome` profile additionally applied to `awesome-*` repositories

- 📁 **File-based PR labeller** (`file-labeller`)

  - Automatically labels PRs based on changed file paths using [`labeler`](https://github.com/actions/labeler)
  - **Skipped for**:
    - `prepare-release` branch
    - Bot-created PRs

- 📝 **Content-based labeller** (`content-labeller`)

  - Automatically labels issues and PRs based on title and body content using [`issue-labeler`](https://github.com/github/issue-labeler)
  - **Skipped for**:
    - `prepare-release` branch
    - Bot-created PRs

- 💝 **Tag sponsors** (`sponsor-labeller`)

  - Adds a `💖 sponsors` label to issues and PRs from sponsors using the GitHub GraphQL API
  - **Skipped for**:
    - `prepare-release` branch
    - Bot-created PRs

### 🧹 [`.github/workflows/lint.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/lint.yaml)

- 🏠 **Lint repository metadata** (`lint-repo`)

  - Validates repository metadata (package name, Sphinx docs, project description) using [`gha-utils lint-repo`](https://github.com/kdeldycke/workflows/blob/main/gha_utils/cli.py). Reads `pyproject.toml` directly.
  - **Requires**:
    - Python package (with a `pyproject.toml` file)

- 🔤 **Lint types** (`lint-types`)

  - Type-checks Python code using [`mypy`](https://github.com/python/mypy)
  - **Requires**:
    - Python files (`**/*.{py,pyi,pyw,pyx,ipynb}`) in the repository
  - **Skipped for**:
    - `prepare-release` branch

- 📄 **Lint YAML** (`lint-yaml`)

  - Lints YAML files using [`yamllint`](https://github.com/adrienverge/yamllint)
  - **Requires**:
    - YAML files (`**/*.{yaml,yml}`) in the repository
  - **Skipped for**:
    - `prepare-release` branch
    - Bot-created PRs

- 🐚 **Lint Zsh** (`lint-zsh`)

  - Syntax-checks Zsh scripts using `zsh --no-exec`
  - **Requires**:
    - Zsh files (`**/*.zsh`) in the repository
  - **Skipped for**:
    - `prepare-release` branch
    - Bot-created PRs

- ⚡ **Lint GitHub Actions** (`lint-github-actions`)

  - Lints workflow files using [`actionlint`](https://github.com/rhysd/actionlint) and [`shellcheck`](https://github.com/koalaman/shellcheck)
  - **Requires**:
    - Workflow files (`.github/workflows/**/*.{yaml,yml}`) in the repository
  - **Skipped for**:
    - `prepare-release` branch
    - Bot-created PRs

- 🔒 **Lint workflow security** (`lint-workflow-security`)

  - Audits workflow files for security issues using [`zizmor`](https://github.com/woodruffw/zizmor) (template injection, excessive permissions, supply chain risks, etc.)
  - **Requires**:
    - Workflow files (`.github/workflows/**/*.{yaml,yml}`) in the repository
  - **Skipped for**:
    - `prepare-release` branch
    - Bot-created PRs

- 🌟 **Lint Awesome list** (`lint-awesome`)

  - Lints awesome lists using [`awesome-lint`](https://github.com/sindresorhus/awesome-lint)
  - **Requires**:
    - Repository name starts with `awesome-`
    - Repository is not [`awesome-template`](https://github.com/kdeldycke/awesome-template) itself
  - **Skipped for**:
    - `prepare-release` branch

- 🔐 **Lint secrets** (`lint-secrets`)

  - Scans for leaked secrets using [`gitleaks`](https://github.com/gitleaks/gitleaks)
  - **Skipped for**:
    - `prepare-release` branch
    - Bot-created PRs

### 🚀 [`.github/workflows/release.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/release.yaml)

[Release Engineering is a full-time job, and full of edge-cases](https://web.archive.org/web/20250126113318/https://blog.axo.dev/2023/02/cargo-dist) that nobody wants to deal with. This workflow automates most of it for Python projects.

**Cross-platform binaries** — Targets 6 platform/architecture combinations (Linux/macOS/Windows × `x86_64`/`arm64`). Unstable targets use `continue-on-error` so builds don't fail on experimental platforms. Job names are prefixed with ✅ (stable, must pass) or ⁉️ (unstable, allowed to fail) for quick visual triage in the GitHub Actions UI.

- 🧯 **Detect squash merge** (`detect-squash-merge`)

  - Detects squash-merged release PRs, opens a GitHub issue to notify the maintainer, and fails the workflow
  - The release is effectively skipped: `create-tag` only matches commits with the `[changelog] Release v` prefix, so no tag, PyPI publish, or GitHub release is created from a squash merge
  - The net effect of squashing freeze + unfreeze leaves `main` in a valid state for the next development cycle; the maintainer just releases the next version when ready
  - **Runs on**:
    - Push to `main` only

- 📦 **Build package** (`build-package`)

  - Builds Python wheel and sdist packages using [`uv build`](https://github.com/astral-sh/uv)
  - **Requires**:
    - Python package with a `pyproject.toml` file

- ✅ **Compile binaries** (`compile-binaries`)

  - Compiles standalone binaries using [`Nuitka`](https://github.com/Nuitka/Nuitka) for Linux/macOS/Windows on `x64`/`arm64`
  - On release pushes, each binary generates an attestation and uploads itself to the GitHub release as its build completes
  - **Requires**:
    - Python package with [CLI entry points](https://docs.astral.sh/uv/concepts/projects/config/#entry-points) defined in `pyproject.toml`
  - **Skipped if** `[tool.gha-utils] nuitka = false` is set in `pyproject.toml` (for projects with CLI entry points that don't need standalone binaries)
  - **Skipped for** branches that don't affect code:
    - `format-json` (JSON formatting)
    - `format-markdown` (documentation formatting)
    - `optimize-images` (image optimization)
    - `sync-gitignore` (`.gitignore` sync)
    - `sync-mailmap` (`.mailmap` sync)
    - `update-deps-graph` (dependency graph docs)

- ✅ **Test binaries** (`test-binaries`)

  - Runs test plans against compiled binaries using [`gha-utils test-plan`](https://github.com/kdeldycke/workflows/blob/main/gha_utils/test_plan.py)
  - **Requires**:
    - Compiled binaries from `compile-binaries` job
    - Test plan file (default: `./tests/cli-test-plan.yaml`)
  - **Skipped for**:
    - Same branches as `compile-binaries`

- 📌 **Create tag** (`create-tag`)

  - Creates a Git tag for the release version
  - **Requires**:
    - Push to `main` branch
    - Release commits matrix from [`gha-utils metadata`](https://github.com/kdeldycke/workflows/blob/main/gha_utils/metadata.py)

- 🐍 **Publish to PyPI** (`publish-pypi`)

  - Uploads packages to PyPI with attestations using [`uv publish`](https://github.com/astral-sh/uv)
  - **Requires**:
    - `PYPI_TOKEN` secret
    - Built packages from `build-package` job

- 🐙 **Create release** (`create-release`)

  - Creates a GitHub release with the Python package attached using [`action-gh-release`](https://github.com/softprops/action-gh-release)
  - Binaries are attached independently by each `compile-binaries` matrix entry as they complete
  - **Requires**:
    - Successful `create-tag` job

### 🆕 [`.github/workflows/renovate.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/renovate.yaml)

- 🔄 **Sync bundled config** (`sync-bundled-config`)

  - Keeps the bundled `gha_utils/data/renovate.json5` in sync with the root `renovate.json5`
  - **Only runs in**:
    - The `kdeldycke/workflows` repository

- 🚚 **Migrate to Renovate** (`migrate-to-renovate`)

  - Automatically migrates from Dependabot to Renovate by creating a PR that:
    - Exports `renovate.json5` configuration file (if missing)
    - Removes `.github/dependabot.yaml` or `.github/dependabot.yml` (if present)
  - PR body includes a prerequisites status table showing:
    - What this PR fixes (config file creation, Dependabot removal)
    - What needs manual action (security updates settings, token permissions)
    - Links to relevant settings pages for easy access
  - Uses [`peter-evans/create-pull-request`](https://github.com/peter-evans/create-pull-request) for consistent PR creation
  - **Skipped if**:
    - No changes needed (`renovate.json5` already exists and no Dependabot config is present)

- 🆕 **Renovate** (`renovate`)

  - Validates prerequisites before running (fails if not met):
    - `renovate.json5` configuration exists
    - No Dependabot config file present
    - Dependabot security updates disabled
  - Runs self-hosted [Renovate](https://github.com/renovatebot/renovate) to update dependencies
  - Creates PRs for outdated dependencies with stabilization periods
  - Handles security vulnerabilities via `vulnerabilityAlerts`
  - **Requires**:
    - `WORKFLOW_UPDATE_GITHUB_PAT` secret with Dependabot alerts permission

- ⛓️ **Sync `uv.lock`** (`sync-uv-lock`)

  - Runs `uv lock --upgrade` to update transitive dependencies to their latest allowed versions using [`gha-utils sync-uv-lock`](https://github.com/kdeldycke/workflows/blob/main/gha_utils/renovate.py)
  - Only creates a PR when the lock file contains real dependency changes (timestamp-only noise is detected and skipped)
  - Replaces Renovate's `lockFileMaintenance`, which cannot reliably revert noise-only changes
  - **Requires**:
    - Python package with a `pyproject.toml` file

### 🔬 [`.github/workflows/tests.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/tests.yaml)

- 🔬 **Run tests** (`tests`)

  - Runs the test suite across a matrix of OS (Linux/macOS/Windows × `x86_64`/`arm64`) and Python versions (`3.10`, `3.14`, `3.14t`, `3.15`, `3.15t`)
  - Verifies CLI launchability via `uvx`, `uv run`, and module invocation
  - Runs `pytest` with coverage reporting to Codecov
  - Runs self-tests against the CLI test plan
  - Job names prefixed with **✅** (stable) or **⁉️** (unstable, e.g., unreleased Python versions)

- 🖥️ **Validate architecture** (`validate-arch`)

  - Checks that the detected CPU architecture matches what the runner image advertises
  - Ensures runners are not silently using emulation (e.g., x86_64 on aarch64)
  - **Requires**:
    - Build targets from `project-metadata` job

### 🧬 What is this `project-metadata` job?

Most jobs in this repository depend on a shared parent job called `project-metadata`. It runs first to extract contextual information, reconcile and combine it, and expose it for downstream jobs to consume.

This expands the capabilities of GitHub Actions, since it allows to:

- Share complex data across jobs (like build matrix)
- Remove limitations of conditional jobs
- Allow for runner introspection
- Fix quirks (like missing environment variables, events/commits mismatch, merge commits, etc.)

This job relies on the [`gha-utils metadata` command](https://github.com/kdeldycke/workflows/blob/main/gha_utils/metadata.py) to gather data from multiple sources:

- **Git**: current branch, latest tag, commit messages, changed files
- **GitHub**: event type, actor, PR labels
- **Environment**: OS, architecture
- **`pyproject.toml`**: project name, version, entry points

> [!IMPORTANT]
> This flexibility comes at the cost of:
>
> - Making the whole workflow a bit more computationally intensive
> - Introducing a small delay at the beginning of the run
> - Preventing child jobs to run in parallel before its completion
>
> But is worth it given how [GitHub Actions can be frustrating](https://nesbitt.io/2025/12/06/github-actions-package-manager.html).

## How does it work?

### `uv` everywhere

All Python dependencies and CLIs are installed via [`uv`](https://github.com/astral-sh/uv) for speed and reproducibility.

### Smart job skipping

Jobs are guarded by conditions to skip unnecessary steps: file type detection (only lint Python if `.py` files exist), branch filtering (`prepare-release` skipped for most linting), and bot detection.

### Maintainer-in-the-loop

Workflows never commit directly or act silently. Every proposed change creates a PR; every action needed opens an issue. You review and decide — nothing lands without your approval.

### Configurable with sensible defaults

Workflows accept `inputs` for customization while providing defaults that work out of the box. Downstream projects can further customize behavior via [`[tool.gha-utils]` configuration](#toolgha-utils-configuration) in `pyproject.toml`.

### Idempotent operations

Safe to re-run: tag creation skips if already exists, version bumps have eligibility checks, PRs update existing branches.

### Graceful degradation

Fallback tokens (`secrets.WORKFLOW_UPDATE_GITHUB_PAT || secrets.GITHUB_TOKEN`) and `continue-on-error` for unstable targets. Job names use emoji prefixes for at-a-glance status: **✅** for stable jobs that must pass, **⁉️** for unstable jobs (e.g., experimental Python versions, unreleased platforms) that are expected to fail and won't block the workflow.

### Dogfooding

This repository uses these workflows for itself.

### Dependency strategy

All dependencies are pinned to specific versions for stability, reproducibility, and security.

#### Pinning mechanisms

| Mechanism                   | What it pins                | How it's updated  |
| :-------------------------- | :-------------------------- | :---------------- |
| `uv.lock`                   | Project dependencies        | Renovate PRs      |
| Hard-coded versions in YAML | GitHub Actions, npm, Python | Renovate PRs      |
| `uv --exclude-newer` option | Transitive dependencies     | Time-based window |
| Tagged workflow URLs        | Remote workflow references  | Release process   |
| `--from . gha-utils`        | CLI from local source       | Release freeze    |

#### Hard-coded versions in workflows

GitHub Actions and npm packages are pinned directly in YAML files:

```yaml
  - uses: actions/checkout@v6.0.1        # Pinned action
  - run: npm install eslint@9.39.1       # Pinned npm package
```

Renovate's `github-actions` manager handles action updates, and a [custom regex manager](https://github.com/kdeldycke/workflows/blob/main/renovate.json5) handles npm packages pinned inline in workflow files.

#### Renovate cooldowns

To avoid update fatigue, and [mitigate supply chain attacks](https://blog.yossarian.net/2025/11/21/We-should-all-be-using-dependency-cooldowns), [`renovate.json5`](https://github.com/kdeldycke/workflows/blob/main/renovate.json5) uses stabilization periods (with prime numbers to stagger updates).

This ensures major updates get more scrutiny while patches flow through faster.

#### `uv.lock` and `--exclude-newer`

The `uv.lock` file pins all project dependencies, and Renovate keeps it in sync.

The `--exclude-newer` flag ignores packages released in the last 7 days, providing a buffer against freshly-published broken releases.

#### Tagged workflow URLs

Workflows in this repository are **self-referential**. The [`prepare-release`](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/changelog.yaml) job's freeze commit rewrites workflow URL references from `main` to the release tag, ensuring released versions reference immutable URLs. The unfreeze commit reverts them back to `main` for development.

### Permissions and token

This repository updates itself via GitHub Actions. But updating its own YAML files in `.github/workflows` is forbidden by default, and we need extra permissions.

#### Why `permissions:` isn't enough

Usually, to grant special permissions to some jobs, you use the [`permissions` parameter in workflow](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#permissions) files:

```yaml
on: (…)

jobs:
  my-job:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps: (…)
```

But `contents: write` doesn't allow write access to workflow files in `.github/`. The `actions: write` permission only covers workflow *runs*, not their YAML source files. Even `permissions: write-all` doesn't work.

You will always end up with this error:

```text
! [remote rejected] branch_xxx -> branch_xxx (refusing to allow a GitHub App to create or update workflow `.github/workflows/my_workflow.yaml` without `workflows` permission)

error: failed to push some refs to 'https://github.com/kdeldycke/my-repo'
```

> [!NOTE]
> The **Settings → Actions → General → Workflow permissions** setting on your repository has no effect on this issue. Even with "Read and write permissions" enabled, the default `GITHUB_TOKEN` cannot modify workflow files—that's a hard security boundary enforced by GitHub:
> ![](docs/assets/repo-workflow-permissions.png)

#### What needs the PAT

Modifying workflow files is the primary reason for the PAT, but it serves additional purposes. Events triggered by `GITHUB_TOKEN` [don't start new workflow runs](https://docs.github.com/en/actions/security-guides/automatic-token-authentication#using-the-github_token-in-a-workflow), so operations like tag pushes also need the PAT to trigger downstream workflows. Renovate requires several additional permissions for its full feature set.

Jobs that use `WORKFLOW_UPDATE_GITHUB_PAT`:

| Workflow         | Job                    | Reason                                                                    |
| :--------------- | :--------------------- | :------------------------------------------------------------------------ |
| `autofix.yaml`   | Fix typos              | Create PR touching `.github/workflows/` files                             |
| `autofix.yaml`   | Sync workflows         | Create PR updating workflow caller files                                  |
| `autofix.yaml`   | Sync awesome template  | Checkout and sync including workflow files                                |
| `changelog.yaml` | Prepare release        | Create release PR freezing versions in workflow files                     |
| `release.yaml`   | Create tag             | Push tag that triggers `on.push.tags` workflows                           |
| `release.yaml`   | Publish GitHub release | Create release that triggers downstream workflows                         |
| `renovate.yaml`  | Renovate               | Manage dependency PRs, status checks, dashboard, and vulnerability alerts |

Each token permission maps to specific needs:

| Permission            | Needed for                                                                            |
| :-------------------- | :------------------------------------------------------------------------------------ |
| **Workflows**         | All PR-creating jobs that touch `.github/workflows/` files                            |
| **Contents**          | Tag pushes, release publishing, PR branch creation                                    |
| **Pull requests**     | All PR-creating jobs (sync-workflows, fix-typos, prepare-release, Renovate)           |
| **Commit statuses**   | Renovate `stability-days` status checks                                               |
| **Dependabot alerts** | Renovate vulnerability alert reading                                                  |
| **Issues**            | Renovate [Dependency Dashboard](https://docs.renovatebot.com/key-concepts/dashboard/) |
| **Metadata**          | Required for all fine-grained token API operations                                    |

All jobs fall back to `GITHUB_TOKEN` when the PAT is unavailable (`secrets.WORKFLOW_UPDATE_GITHUB_PAT || secrets.GITHUB_TOKEN`), but operations requiring the `workflows` permission or workflow triggering will silently fail.

#### Solution: Fine-grained Personal Access Token

To bypass these limitations, create a custom access token called `WORKFLOW_UPDATE_GITHUB_PAT`. It replaces the default `secrets.GITHUB_TOKEN` [in steps that need elevated permissions](https://github.com/search?q=repo%3Akdeldycke%2Fworkflows%20WORKFLOW_UPDATE_GITHUB_PAT&type=code).

##### Step 1: Create the token

1. Go to **GitHub → Settings → Developer Settings → Personal Access Tokens → [Fine-grained tokens](https://github.com/settings/personal-access-tokens)**

2. Click **Generate new token**

3. Configure:

   | Field                 | Value                                                                                    |
   | :-------------------- | :--------------------------------------------------------------------------------------- |
   | **Token name**        | `workflow-self-update` (or similar descriptive name)                                     |
   | **Expiration**        | Choose based on your security policy                                                     |
   | **Repository access** | Select **Only select repositories** and choose the repos that need workflow self-updates |

4. Click **Add permissions**:

   | Permission            | Access                  |
   | :-------------------- | :---------------------- |
   | **Commit statuses**   | Read and Write          |
   | **Contents**          | Read and Write          |
   | **Dependabot alerts** | Read-only               |
   | **Issues**            | Read and Write          |
   | **Metadata**          | Read-only *(mandatory)* |
   | **Pull requests**     | Read and Write          |
   | **Workflows**         | Read and Write          |

   > [!IMPORTANT]
   > The **Workflows** permission is the key. This is the *only* place where you can grant it—it's not available via the `permissions:` parameter in YAML files.
   >
   > The **Commit statuses** permission is required by Renovate to set status checks (e.g., `renovate/stability-days`) on commits.
   >
   > The **Dependabot alerts** permission allows Renovate to read vulnerability alerts and create security update PRs, replacing Dependabot security updates.
   >
   > The **Issues** permission is required by Renovate to create and update the [Dependency Dashboard](https://docs.renovatebot.com/key-concepts/dashboard/) issue.

5. Click **Generate token** and copy the `github_pat_XXXX` value

##### Step 2: Add the secret to your repository

1. Go to your repository → **Settings → Security → Secrets and variables → Actions**
2. Click **New repository secret**
3. Set:
   - **Name**: `WORKFLOW_UPDATE_GITHUB_PAT`
   - **Secret**: paste the `github_pat_XXXX` token

##### Step 3: Configure Dependabot settings

Go to your repository → **Settings → Advanced Security → Dependabot** and configure:

| Setting                         | Status      | Reason                                                |
| :------------------------------ | :---------- | :---------------------------------------------------- |
| **Dependabot alerts**           | ✅ Enabled  | Renovate reads these alerts to detect vulnerabilities |
| **Dependabot security updates** | ❌ Disabled | Renovate creates security PRs instead                 |
| **Grouped security updates**    | ❌ Disabled | Not needed when security updates are disabled         |
| **Dependabot version updates**  | ❌ Disabled | Renovate handles all version updates                  |

> [!WARNING]
> Keep **Dependabot alerts** enabled—these are passive notifications that Renovate reads via the API.
> Disable all other Dependabot features since Renovate handles both security and version updates.

##### Step 4: Verify it works

Re-run your workflow. It should now update files in `.github/workflows/` without the error.

> [!TIP]
> **For organizations**: Consider using a [machine user account](https://docs.github.com/en/get-started/learning-about-github/types-of-github-accounts#personal-accounts) or a dedicated service account to own the PAT, rather than tying it to an individual's account.

> [!WARNING]
> **Token expiration**: Fine-grained PATs expire. Set a calendar reminder to rotate the token before expiration, or your workflows will fail silently.

### Concurrency and cancellation

All workflows use a `concurrency` directive to prevent redundant runs and save CI resources. When a new commit is pushed, any in-progress workflow runs for the same branch or PR are automatically cancelled.

Workflows are grouped by:

- **Pull requests**: `{workflow-name}-{pr-number}` — Multiple commits to the same PR cancel previous runs
- **Branch pushes**: `{workflow-name}-{branch-ref}` — Multiple pushes to the same branch cancel previous runs

`release.yaml` uses a stronger protection: release commits get a **unique concurrency group** based on the commit SHA, so they can never be cancelled. This ensures tagging, PyPI publishing, and GitHub release creation complete successfully.

Additionally, [`cancel-runs.yaml`](#githubworkflowscancel-runsyaml-jobs) actively cancels in-progress and queued runs when a PR is closed. This complements passive concurrency groups, which only trigger cancellation when a *new* run enters the same group — closing a PR doesn't produce such an event.

> [!TIP]
> For implementation details on how concurrency groups are computed and why `release.yaml` needs special handling, see [`claude.md` § Concurrency implementation](claude.md#concurrency-implementation).

## Claude Code integration

This repository includes [Claude Code skills](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/skills) that wrap `gha-utils` CLI commands as slash commands. Downstream repositories can install them with:

```shell-session
$ uvx -- gha-utils init skills
```

To keep skills in sync with the latest version:

```shell-session
$ uvx -- gha-utils sync-skills
```

Available skills: `/gha-init`, `/gha-changelog`, `/gha-release`, `/gha-lint`, `/gha-sync`, `/gha-deps`, `/gha-test`, `/gha-metadata`.

## Used in

Check these projects to get real-life examples of usage and inspiration:

- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/awesome-falsehood?label=%E2%AD%90&style=flat-square) [Awesome Falsehood](https://github.com/kdeldycke/awesome-falsehood) - Falsehoods Programmers Believe in.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/awesome-engineering-team-management?label=%E2%AD%90&style=flat-square) [Awesome Engineering Team Management](https://github.com/kdeldycke/awesome-engineering-team-management) - How to transition from software development to engineering management.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/awesome-iam?label=%E2%AD%90&style=flat-square) [Awesome IAM](https://github.com/kdeldycke/awesome-iam) - Identity and Access Management knowledge for cloud platforms.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/awesome-billing?label=%E2%AD%90&style=flat-square) [Awesome Billing](https://github.com/kdeldycke/awesome-billing) - Billing & Payments knowledge for cloud platforms.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/meta-package-manager?label=%E2%AD%90&style=flat-square) [Meta Package Manager](https://github.com/kdeldycke/meta-package-manager) - A unifying CLI for multiple package managers.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/mail-deduplicate?label=%E2%AD%90&style=flat-square) [Mail Deduplicate](https://github.com/kdeldycke/mail-deduplicate) - A CLI to deduplicate similar emails.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/dotfiles?label=%E2%AD%90&style=flat-square) [dotfiles](https://github.com/kdeldycke/dotfiles) - macOS dotfiles for Python developers.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/click-extra?label=%E2%AD%90&style=flat-square) [Click Extra](https://github.com/kdeldycke/click-extra) - Extra colorization and configuration loading for Click.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/workflows?label=%E2%AD%90&style=flat-square) [workflows](https://github.com/kdeldycke/workflows) - Itself. Eat your own dog-food.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/extra-platforms?label=%E2%AD%90&style=flat-square) [Extra Platforms](https://github.com/kdeldycke/extra-platforms) - Detect platforms and group them by family.

Feel free to send a PR to add your project in this list if you are relying on these scripts.

## Development

See [`claude.md`](claude.md) for development commands, code style, testing guidelines, and design principles.
