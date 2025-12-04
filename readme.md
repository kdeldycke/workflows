# `gha-utils` CLI + reusable workflows

[![Last release](https://img.shields.io/pypi/v/gha-utils.svg)](https://pypi.org/project/gha-utils/)
[![Python versions](https://img.shields.io/pypi/pyversions/gha-utils.svg)](https://pypi.org/project/gha-utils/)
[![Downloads](https://static.pepy.tech/badge/gha_utils/month)](https://pepy.tech/projects/gha_utils)
[![Unittests status](https://github.com/kdeldycke/workflows/actions/workflows/tests.yaml/badge.svg?branch=main)](https://github.com/kdeldycke/workflows/actions/workflows/tests.yaml?query=branch%3Amain)
[![Coverage status](https://codecov.io/gh/kdeldycke/workflows/branch/main/graph/badge.svg)](https://app.codecov.io/gh/kdeldycke/workflows)

This repository contains:

- a [collection of reusable workflows](#reusable-workflows-collection)
- a standalone [CLI called `gha-utils`](#gha-utils-cli)

It is designed for `uv`-based Python projects, but can be used for other projects as well. Thanks to this project, I am able to **release Python packages multiple times a day with only 2-clicks**.

It takes care of:

- Version bumping
- Changelog management
- Formatting autofix for: Python, Markdown, JSON, typos
- Linting: Python types with `mypy`, YAML, `zsh`, GitHub actions, URLS & redirects, Awesome lists, secrets
- Compiling of Python binaries for Linux / macOS / Windows on `x86_64` & `arm64`
- Building of Python packages and upload to PyPi
- Produce attestations
- Git version tagging and GitHub release creation
- Synchronization of: `uv.lock`, `.gitignore`, `.mailmap` and Mermaid dependency graph
- Auto-locking of inactive closed issues
- Static image optimization
- Sphinx documentation building & deployment, and `autodoc` updates
- Label management, with file-based and content-based rules
- Awesome list template synchronization

Nothing is done behind your back. A PR is created every time a change is proposed, so you can inspect it before merging it.

## `gha-utils` CLI

`gha-utils` stands for *GitHub action workflows utilities*.

### Try it

Thanks to `uv`, you can run it in one command, without installation or venv:

```shell-session
$ uvx -- gha-utils
Usage: gha-utils [OPTIONS] COMMAND [ARGS]...

Options:
  --time / --no-time    Measure and print elapsed execution time.  [default: no-
                        time]
  --color, --ansi / --no-color, --no-ansi
                        Strip out all colors and all ANSI codes from output.
                        [default: color]
  --config CONFIG_PATH  Location of the configuration file. Supports local path
                        with glob patterns or remote URL.  [default:
                        ~/Library/Application Support/gha-
                        utils/*.toml|*.yaml|*.yml|*.json|*.ini]
  --no-config           Ignore all configuration files and only use command line
                        parameters and environment variables.
  --show-params         Show all CLI parameters, their provenance, defaults and
                        value, then exit.
  --table-format [asciidoc|csv|csv-excel|csv-excel-tab|csv-unix|double-grid|double-outline|fancy-grid|fancy-outline|github|grid|heavy-grid|heavy-outline|html|jira|latex|latex-booktabs|latex-longtable|latex-raw|mediawiki|mixed-grid|mixed-outline|moinmoin|orgtbl|outline|pipe|plain|presto|pretty|psql|rounded-grid|rounded-outline|rst|simple|simple-grid|simple-outline|textile|tsv|unsafehtml|vertical|youtrack]
                        Rendering style of tables.  [default: rounded-outline]
  --verbosity LEVEL     Either CRITICAL, ERROR, WARNING, INFO, DEBUG.  [default:
                        WARNING]
  -v, --verbose         Increase the default WARNING verbosity by one level for
                        each additional repetition of the option.  [default: 0]
  --version             Show the version and exit.
  -h, --help            Show this message and exit.

Commands:
  changelog     Maintain a Markdown-formatted changelog
  mailmap-sync  Update Git's .mailmap file with missing contributors
  metadata      Output project metadata
  test-plan     Run a test plan from a file against a binary
```

```shell-session
$ uvx -- gha-utils --version
gha-utils, version 4.24.6
```

That's the best way to get started with `gha-utils` and experiment with it.

### Executables

To ease deployment, standalone executables of `gha-utils`'s latest version are available as direct downloads for several platforms and architectures:

| Platform    | `arm64`                                                                                                                               | `x86_64`                                                                                                                          |
| :---------- | ------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **Linux**   | [Download `gha-utils-linux-arm64.bin`](https://github.com/kdeldycke/workflows/releases/latest/download/gha-utils-linux-arm64.bin)     | [Download `gha-utils-linux-x64.bin`](https://github.com/kdeldycke/workflows/releases/latest/download/gha-utils-linux-x64.bin)     |
| **macOS**   | [Download `gha-utils-macos-arm64.bin`](https://github.com/kdeldycke/workflows/releases/latest/download/gha-utils-macos-arm64.bin)     | [Download `gha-utils-macos-x64.bin`](https://github.com/kdeldycke/workflows/releases/latest/download/gha-utils-macos-x64.bin)     |
| **Windows** | [Download `gha-utils-windows-arm64.exe`](https://github.com/kdeldycke/workflows/releases/latest/download/gha-utils-windows-arm64.exe) | [Download `gha-utils-windows-x64.exe`](https://github.com/kdeldycke/workflows/releases/latest/download/gha-utils-windows-x64.exe) |

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
gha-utils, version 4.18.2
```

## Reusable workflows collection

This repository contains workflows to automate most of the boring tasks in the form of [reusable GitHub actions workflows](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows).

### Guidelines

All workflows:

- Are designed to be reusable in other repositories [via the `uses:` syntax](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows#calling-a-reusable-workflow).
- Uses `uv` to install dependencies and CLIs.
- Have jobs guarded by conditions to skip unnecessary steps when not needed.
- Rely on pinned versions of actions, tools and CLIs, to ensure stability, reproducibility and security.
- Are run and tested in this repository: we eat our own dog-food.

### [`.github/workflows/autofix.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/autofix.yaml)

- **Format Python** (`format-python`)

  - Auto-formats Python code using [`autopep8`](https://github.com/hhatto/autopep8), [`ruff`](https://github.com/astral-sh/ruff), and [`blacken-docs`](https://github.com/adamchainz/blacken-docs)
  - **Requires**:
    - Python files (`**/*.{py,pyi,pyw,pyx,ipynb}`) in the repository, or
    - documentation files (`**/*.{markdown,mdown,mkdn,mdwn,mkd,md,mdtxt,mdtext,rst,tex}`)

- **Sync `uv.lock`** (`sync-uv-lock`)

  - Keeps `uv.lock` file up to date with dependencies using [`uv`](https://github.com/astral-sh/uv)
  - **Requires**:
    - Python package with a `pyproject.toml` file

- **Format Markdown** (`format-markdown`)

  - Auto-formats Markdown files using [`mdformat`](https://github.com/hukkin/mdformat)
  - **Requires**:
    - Markdown files (`**/*.{markdown,mdown,mkdn,mdwn,mkd,md,mdtxt,mdtext}`) in the repository

- **Format JSON** (`format-json`)

  - Auto-formats JSON, JSONC, and JSON5 files using [ESLint](https://github.com/eslint/eslint) with [`@eslint/json`](https://github.com/eslint/json) plugin
  - **Requires**:
    - JSON files (`**/*.{json,jsonc,json5}`, `**/.code-workspace`, `!**/package-lock.json`) in the repository

- **Update .gitignore** (`update-gitignore`)

  - Regenerates `.gitignore` from [gitignore.io](https://github.com/toptal/gitignore.io) templates using [`git-extras`](https://github.com/tj/git-extras)
  - **Requires**:
    - A `.gitignore` file in the repository

### [`.github/workflows/autolock.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/autolock.yaml)

- **Lock inactive threads** (`lock`)

  - Automatically locks closed issues and PRs after 90 days of inactivity using [`lock-threads`](https://github.com/dessant/lock-threads)

### [`.github/workflows/changelog.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/changelog.yaml)

- **Version increments** (`version-increments`)

  - Creates PRs for minor and major version bumps using [`bump-my-version`](https://github.com/callowayproject/bump-my-version)
  - **Requires**:
    - `bump-my-version` configuration in `pyproject.toml`
    - A `changelog.md` file
  - **Skipped for**:
    - Schedule events
    - Release commits (starting with `[changelog] Release v`)

- **Prepare release** (`prepare-release`)

  - Creates a release PR with changelog updates and version tagging using [`bump-my-version`](https://github.com/callowayproject/bump-my-version) and [`gha-utils changelog`](https://github.com/kdeldycke/workflows/blob/main/gha_utils/changelog.py)
  - **Requires**:
    - `bump-my-version` configuration in `pyproject.toml`
    - A `changelog.md` file

### [`.github/workflows/docs.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/docs.yaml)

Some of these jobs requires a `docs` [dependency group](https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-groups) in `pyproject.toml` so they can determine the right Sphinx version to install and its dependencies:

```toml
[dependency-groups]
docs = [
    "furo",
    "myst-parser",
    "sphinx",
    …
]
```

- **Fix typos** (`autofix-typo`)

  - Automatically fixes typos in the codebase using [`typos`](https://github.com/crate-ci/typos)

- **Optimize images** (`optimize-images`)

  - Compresses images in the repository using [`image-actions`](https://github.com/calibreapp/image-actions)
  - **Requires**:
    - Image files (`**/*.{jpeg,jpg,png,webp,avif}`) in the repository

- **Update `.mailmap`** (`update-mailmap`)

  - Keeps `.mailmap` file up to date with contributors using [`gha-utils mailmap-sync`](https://github.com/kdeldycke/workflows/blob/main/gha_utils/mailmap.py)
  - **Requires**:
    - A `.mailmap` file in the repository root

- **Update dependency graph** (`update-deps-graph`)

  - Generates a Mermaid dependency graph of the Python project using [`pipdeptree`](https://github.com/tox-dev/pipdeptree)
  - **Requires**:
    - Python package with a `pyproject.toml` file

- **Update autodoc** (`update-autodoc`)

  - Regenerates Sphinx autodoc files using [`sphinx-apidoc`](https://github.com/sphinx-doc/sphinx)
  - **Requires**:
    - Python package with a `pyproject.toml` file
    - `docs` dependency group
    - Sphinx autodoc enabled (checks for `sphinx.ext.autodoc` in `docs/conf.py`)

- **Deploy Sphinx doc** (`deploy-docs`)

  - Builds Sphinx-based documentation and publishes it to GitHub Pages using [`sphinx`](https://github.com/sphinx-doc/sphinx) and [`gh-pages`](https://github.com/peaceiris/actions-gh-pages)
  - **Requires**:
    - Python package with a `pyproject.toml` file
    - `docs` dependency group
    - Sphinx configuration file at `docs/conf.py`

- **Sync awesome template** (`awesome-template-sync`)

  - Syncs awesome list projects from the [`awesome-template`](https://github.com/kdeldycke/awesome-template) repository using [`actions-template-sync`](https://github.com/AndreasAugustin/actions-template-sync)
  - **Requires**:
    - Repository name starts with `awesome-`
    - Repository is not [`awesome-template`](https://github.com/kdeldycke/awesome-template) itself

### [`.github/workflows/labels.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/labels.yaml)

- **Sync labels** (`sync-labels`)

  - Synchronizes repository labels from a YAML definition file using [`action-manage-label`](https://github.com/julb/action-manage-label)
  - Automatically includes [`labels-awesome.yaml`](https://github.com/kdeldycke/workflows/blob/main/.github/labels-awesome.yaml) for `awesome-*` repositories

- **File-based PR labeller** (`file-labeller`)

  - Automatically labels PRs based on changed file paths using [`labeler`](https://github.com/actions/labeler)
  - **Skipped for**:
    - `prepare-release` branch
    - Bot-created PRs

- **Content-based labeller** (`content-labeller`)

  - Automatically labels issues and PRs based on title and body content using [`issue-labeler`](https://github.com/github/issue-labeler)
  - **Skipped for**:
    - `prepare-release` branch
    - Bot-created PRs

- **Tag sponsors** (`sponsor-labeller`)

  - Adds a `💖 sponsors` label to issues and PRs from sponsors using [`is-sponsor-label-action`](https://github.com/JasonEtco/is-sponsor-label-action)
  - **Skipped for**:
    - `prepare-release` branch
    - Bot-created PRs

### [`.github/workflows/lint.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/lint.yaml)

- **Mypy lint** (`mypy-lint`)

  - Type-checks Python code using [`mypy`](https://github.com/python/mypy)
  - **Requires**:
    - Python files (`**/*.{py,pyi,pyw,pyx,ipynb}`) in the repository
    - `typing` [dependency group](https://docs.astral.sh/uv/concepts/projects/dependencies/#dependency-groups) in `pyproject.toml`
  - **Skipped for**:
    - `prepare-release` branch

- **Lint YAML** (`lint-yaml`)

  - Lints YAML files using [`yamllint`](https://github.com/adrienverge/yamllint)
  - **Requires**:
    - YAML files (`**/*.{yaml,yml}`) in the repository
  - **Skipped for**:
    - `prepare-release` branch
    - Bot-created PRs

- **Lint Zsh** (`lint-zsh`)

  - Syntax-checks Zsh scripts using `zsh --no-exec`
  - **Requires**:
    - Zsh files (`**/*.zsh`) in the repository
  - **Skipped for**:
    - `prepare-release` branch
    - Bot-created PRs

- **Lint GitHub Actions** (`lint-github-action`)

  - Lints workflow files using [`actionlint`](https://github.com/rhysd/actionlint) and [`shellcheck`](https://github.com/koalaman/shellcheck)
  - **Requires**:
    - Workflow files (`.github/workflows/**/*.{yaml,yml}`) in the repository
  - **Skipped for**:
    - `prepare-release` branch
    - Bot-created PRs

- **Broken links** (`broken-links`)

  - Checks for broken links in documentation using [`lychee`](https://github.com/lycheeverse/lychee)
  - Creates/updates issues for broken links found
  - **Requires**:
    - Documentation files (`**/*.{markdown,mdown,mkdn,mdwn,mkd,md,mdtxt,mdtext,rst,tex}`) in the repository
  - **Skipped for**:
    - All PRs (only runs on push to main)
    - `prepare-release` branch
    - Post-release bump commits

- **Lint Awesome list** (`lint-awesome`)

  - Lints awesome lists using [`awesome-lint`](https://github.com/sindresorhus/awesome-lint)
  - **Requires**:
    - Repository name starts with `awesome-`
    - Repository is not [`awesome-template`](https://github.com/kdeldycke/awesome-template) itself
  - **Skipped for**:
    - `prepare-release` branch

- **Check secrets** (`check-secrets`)

  - Scans for leaked secrets using [`gitleaks`](https://github.com/gitleaks/gitleaks)
  - **Skipped for**:
    - `prepare-release` branch
    - Bot-created PRs

### [`.github/workflows/release.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/release.yaml)

[Release Engineering is a full-time job, and full of edge-cases](https://web.archive.org/web/20250126113318/https://blog.axo.dev/2023/02/cargo-dist) that nobody wants to deal with. This workflow automates most of it for Python projects.

- **Build package** (`package-build`)

  - Builds Python wheel and sdist packages using [`uv build`](https://github.com/astral-sh/uv)
  - **Requires**:
    - Python package with a `pyproject.toml` file

- **Compile binaries** (`compile-binaries`)

  - Compiles standalone binaries using [`Nuitka`](https://github.com/Nuitka/Nuitka) for Linux/macOS/Windows on `x64`/`arm64`
  - **Requires**:
    - Python package with [CLI entry points](https://docs.astral.sh/uv/concepts/projects/config/#entry-points) defined in `pyproject.toml`

- **Test binaries** (`test-binaries`)

  - Runs test plans against compiled binaries using [`gha-utils test-plan`](https://github.com/kdeldycke/workflows/blob/main/gha_utils/test_plan.py)
  - **Requires**:
    - Compiled binaries from `compile-binaries` job
    - Test plan file (default: `./tests/cli-test-plan.yaml`)

- **Git tag** (`git-tag`)

  - Creates a Git tag for the release version
  - **Requires**:
    - Push to `main` branch
    - Release commits matrix from [`gha-utils metadata`](https://github.com/kdeldycke/workflows/blob/main/gha_utils/metadata.py)

- **Publish to PyPi** (`pypi-publish`)

  - Uploads packages to PyPi with attestations using [`uv publish`](https://github.com/astral-sh/uv)
  - **Requires**:
    - `PYPI_TOKEN` secret
    - Built packages from `package-build` job

- **GitHub release** (`github-release`)

  - Creates a GitHub release with all artifacts attached using [`action-gh-release`](https://github.com/softprops/action-gh-release)
  - **Requires**:
    - Successful `git-tag` job

### What is this `project-metadata` job?

Most jobs in this repository depend on a shared parent job called `project-metadata`. It runs first to extracts contextual information, reconcile and combine them, and expose them for downstream jobs to consume.

This expand the capabilities of GitHub actions, since it allows to:

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
> But is worth it given how GitHub actions can be frustrating.

## Dependency strategy

All dependencies in this project are pinned to specific versions to ensure stability, reproducibility, and security. This section explains the mechanisms in place.

### Pinning mechanisms

| Mechanism                   | What it pins                  | How it's updated   |
| :-------------------------- | :---------------------------- | :----------------- |
| `requirements/*.txt` files  | Python CLIs used in workflows | Dependabot PRs     |
| `uv.lock`                   | Project dependencies          | `sync-uv-lock` job |
| Hard-coded versions in YAML | GitHub Actions, npm packages  | Dependabot PRs     |
| `uv --exclude-newer` option | Transitive dependencies       | Time-based window  |
| Tagged workflow URLs        | Remote workflow references    | Release process    |

### `requirements/*.txt` files

Each Python CLI used in workflows has its own requirements file (e.g., [`requirements/yamllint.txt`](https://github.com/kdeldycke/workflows/blob/main/requirements/yamllint.txt)). This allows Dependabot to track and update each tool independently.

We use these files instead of inline version strings because **Dependabot cannot parse versions in `run:` blocks**—it only supports `requirements.txt` and `pyproject.toml` files for Python projects ([source](https://github.com/dependabot/dependabot-core/blob/c938bbf7cb4da88053d4379dcab297a3eaa8c0a7/python/lib/dependabot/python/file_fetcher.rb#L24-L44)).

```yaml
# ❌ Dependabot cannot update this:
  - run: uvx -- yamllint==1.37.1

# ✅ So we use requirements/yamllint.txt as an indirection:
  - run: uvx --with-requirements …/requirements/yamllint.txt -- yamllint
```

A root [`requirements.txt`](https://github.com/kdeldycke/workflows/blob/main/requirements.txt) aggregates all files from the `requirements/` folder for bulk installation.

### Hard-coded versions in workflows

GitHub Actions and npm packages are pinned directly in YAML files:

```yaml
  - uses: actions/checkout@v6.0.1        # Pinned action
  - run: npm install eslint@9.39.1       # Pinned npm package
```

Dependabot's `github-actions` ecosystem handles action updates.

> [!WARNING]
> For npm packages, we pin versions inline since they're used sparingly, and then update them manually when needed.

### Dependabot cooldowns

To avoid update fatigue, and [mitigate supply chain attacks](https://blog.yossarian.net/2025/11/21/We-should-all-be-using-dependency-cooldowns), [`.github/dependabot.yaml`](https://github.com/g/blob/main/.github/dependabot.yaml) uses cooldown periods (with prime numbers to stagger updates).

This ensures major updates get more scrutiny while patches flow through faster.

### `uv.lock` and `--exclude-newer`

The `uv.lock` file pins all project dependencies, and the [`sync-uv-lock`](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/autofix.yaml) job keeps it in sync.

The `--exclude-newer` flag ignores packages released in the last 7 days, providing a buffer against freshly-published broken releases.

### Tagged workflow URLs

Workflows in this repository are **self-referential**, and points to themselves via raw GitHub URLs.

During development, these point to `main`:

```yaml
--with-requirements https://raw.githubusercontent.com/kdeldycke/workflows/main/requirements/yamllint.txt
...
```

The [`prepare-release`](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/changelog.yaml) job rewrites these to the release tag before tagging:

```yaml
# Before release commit:
…/workflows/main/requirements/yamllint.txt

# In the tagged release commit:
…/workflows/v4.24.6/requirements/yamllint.txt

# After post-release bump:
…/workflows/main/requirements/yamllint.txt
```

This ensures released versions reference immutable, tagged URLs while `main` remains editable.

## Permissions and token

As [explained above](#tagged-workflow-urls), this repository updates itself via GitHub actions. But updating its own YAML files in `.github/workflows` is forbidden by default, and we need extra permissions.

### Why `permissions:` isn't enough

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
> The **Settings → Actions → General → Workflow permissions** setting on your repository has no effect on this issue, even with "Read and write permissions" enabled:
> ![](docs/assets/repo-workflow-permissions.png)

### Solution: Fine-grained Personal Access Token

To bypass this limitation, create a custom access token called `WORKFLOW_UPDATE_GITHUB_PAT`. It replaces the default `secrets.GITHUB_TOKEN` [in steps that modify workflow files](https://github.com/search?q=repo%3Akdeldycke%2Fworkflows%20WORKFLOW_UPDATE_GITHUB_PAT&type=code).

#### Step 1: Create the token

1. Go to **GitHub → Settings → Developer Settings → Personal Access Tokens → [Fine-grained tokens](https://github.com/settings/personal-access-tokens)**

1. Click **Generate new token**

1. Configure:

   | Field                 | Value                                                                                    |
   | :-------------------- | :--------------------------------------------------------------------------------------- |
   | **Token name**        | `workflow-self-update` (or similar descriptive name)                                     |
   | **Expiration**        | Choose based on your security policy                                                     |
   | **Repository access** | Select **Only select repositories** and choose the repos that need workflow self-updates |

1. Click **Add permissions**:

   | Permission        | Access                  |
   | :---------------- | :---------------------- |
   | **Contents**      | Read and Write          |
   | **Metadata**      | Read-only *(mandatory)* |
   | **Pull requests** | Read and Write          |
   | **Workflows**     | Read and Write          |

   > [!IMPORTANT]
   > The **Workflows** permission is the key. This is the *only* place where you can grant it—it's not available via the `permissions:` parameter in YAML files.

1. Click **Generate token** and copy the `github_pat_XXXX` value

#### Step 2: Add the secret to your repository

1. Go to your repository → **Settings → Security → Secrets and variables → Actions**
1. Click **New repository secret**
1. Set:
   - **Name**: `WORKFLOW_UPDATE_GITHUB_PAT`
   - **Secret**: paste the `github_pat_XXXX` token

#### Step 3: Verify it works

Re-run your workflow. It should now update files in `.github/workflows/` without the error.

> [!TIP]
> **For organizations**: Consider using a [machine user account](https://docs.github.com/en/get-started/learning-about-github/types-of-github-accounts#personal-accounts) or a dedicated service account to own the PAT, rather than tying it to an individual's account.

> [!WARNING]
> **Token expiration**: Fine-grained PATs expire. Set a calendar reminder to rotate the token before expiration, or your workflows will fail silently.

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

## Release process

All steps of the release process and version management are automated in the
[`changelog.yaml`](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/changelog.yaml)
and
[`release.yaml`](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/release.yaml)
workflows.

All there's left to do is to:

- [check the open draft `prepare-release` PR](https://github.com/kdeldycke/workflows/pulls?q=is%3Apr+is%3Aopen+head%3Aprepare-release)
  and its changes,
- click the `Ready for review` button,
- click the `Rebase and merge` button,
- let the workflows tag the release and set back the `main` branch into a
  development state.
