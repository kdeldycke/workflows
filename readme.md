# `gha-utils` CLI + reusable workflows

[![Last release](https://img.shields.io/pypi/v/gha-utils.svg)](https://pypi.org/project/gha-utils/)
[![Python versions](https://img.shields.io/pypi/pyversions/gha-utils.svg)](https://pypi.org/project/gha-utils/)
[![Downloads](https://static.pepy.tech/badge/gha_utils/month)](https://pepy.tech/projects/gha_utils)
[![Unittests status](https://github.com/kdeldycke/workflows/actions/workflows/tests.yaml/badge.svg?branch=main)](https://github.com/kdeldycke/workflows/actions/workflows/tests.yaml?query=branch%3Amain)
[![Coverage status](https://codecov.io/gh/kdeldycke/workflows/branch/main/graph/badge.svg)](https://app.codecov.io/gh/kdeldycke/workflows)

Thanks to this project, I am able to **release Python packages multiple times a day with only 2-clicks**.

This repository contains a collection of reusable workflows and its companion CLI called `gha-utils` (which stands for *GitHub action workflows utilities*).

It is designed for `uv`-based Python projects (and Awesome List projects as a bonus).

It takes care of:

- Version bumping
- Formatting autofix for: Python, Markdown, JSON, typos
- Linting: Python types with `mypy`, YAML, `zsh`, GitHub actions, links, Awesome lists, secrets
- Compiling of Python binaries for Linux / macOS / Windows on `x86_64` & `arm64`
- Building of Python packages and upload to PyPi
- Git version tagging and GitHub release creation
- Synchronization of: `uv.lock`, `.gitignore`, `.mailmap` and Mermaid dependency graph
- Auto-locking of inactive closed issues
- Static image optimization
- Sphinx documentation building & deployment, and `autodoc` updates
- Label management, with file-based and content-based rules

Nothing is done behind your back. A PR is created every time a change is proposed, so you can inspect it, ala dependabot.

## `gha-utils` CLI

### Ad-hoc execution

Thanks to `uv`, you can install and run `gha-utils` in one command, without polluting your system:

```shell-session
$ uvx gha-utils
Usage: gha-utils [OPTIONS] COMMAND [ARGS]...

Options:
  --time / --no-time        Measure and print elapsed execution time.  [default:
                            no-time]
  --color, --ansi / --no-color, --no-ansi
                            Strip out all colors and all ANSI codes from output.
                            [default: color]
  -C, --config CONFIG_PATH  Location of the configuration file. Supports glob
                            pattern of local path and remote URL.  [default:
                            ~/Library/Application Support/gha-
                            utils/*.{toml,yaml,yml,json,ini,xml}]
  --show-params             Show all CLI parameters, their provenance, defaults
                            and value, then exit.
  --verbosity LEVEL         Either CRITICAL, ERROR, WARNING, INFO, DEBUG.
                            [default: WARNING]
  -v, --verbose             Increase the default WARNING verbosity by one level
                            for each additional repetition of the option.
                            [default: 0]
  --version                 Show the version and exit.
  -h, --help                Show this message and exit.

Commands:
  changelog     Maintain a Markdown-formatted changelog
  mailmap-sync  Update Git's .mailmap file with missing contributors
  metadata      Output project metadata
  test-plan     Run a test plan from a file against a binary
```

```shell-session
$ uvx gha-utils --version
gha-utils, version 4.9.0
```

That's the best way to get started with `gha-utils` and experiment with it.

### Executables

To ease deployment, standalone executables of `gha-utils`'s latest version are available as direct downloads for several platforms and architectures:

| Platform    | `x86_64`                                                                                                                          | `arm64`                                                                                                                               |
| ----------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **Linux**   | [Download `gha-utils-linux-x64.bin`](https://github.com/kdeldycke/workflows/releases/latest/download/gha-utils-linux-x64.bin)     | [Download `gha-utils-linux-arm64.bin`](https://github.com/kdeldycke/workflows/releases/latest/download/gha-utils-linux-arm64.bin)     |
| **macOS**   | [Download `gha-utils-macos-x64.bin`](https://github.com/kdeldycke/workflows/releases/latest/download/gha-utils-macos-x64.bin)     | [Download `gha-utils-macos-arm64.bin`](https://github.com/kdeldycke/workflows/releases/latest/download/gha-utils-macos-arm64.bin)     |
| **Windows** | [Download `gha-utils-windows-x64.exe`](https://github.com/kdeldycke/workflows/releases/latest/download/gha-utils-windows-x64.exe) | [Download `gha-utils-windows-arm64.exe`](https://github.com/kdeldycke/workflows/releases/latest/download/gha-utils-windows-arm64.exe) |

ABI targets:

```shell-session
$ file ./gha-utils-*
./gha-utils-linux-arm64.bin:   ELF 64-bit LSB pie executable, ARM aarch64, version 1 (SYSV), dynamically linked, interpreter /lib/ld-linux-aarch64.so.1, BuildID[sha1]=520bfc6f2bb21f48ad568e46752888236552b26a, for GNU/Linux 3.7.0, stripped
./gha-utils-linux-x64.bin:     ELF 64-bit LSB pie executable, x86-64, version 1 (SYSV), dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, BuildID[sha1]=56ba24bccfa917e6ce9009223e4e83924f616d46, for GNU/Linux 3.2.0, stripped
./gha-utils-macos-arm64.bin:   Mach-O 64-bit executable arm64
./gha-utils-macos-x64.bin:     Mach-O 64-bit executable x86_64
./gha-utils-windows-arm64.exe: PE32+ executable (console) Aarch64, for MS Windows
./gha-utils-windows-x64.exe:   PE32+ executable (console) x86-64, for MS Windows
```

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

- Are designed to be reusable in other repositories via the `uses:` syntax.
- Uses `uv` to install dependencies and CLIs.
- Have jobs guarded by conditions to skip unnecessary steps when not needed.
- Rely on pinned versions of actions, tools and CLIs, to ensure stability, reproducibility and security.
- Are run and tested in this repository: we eat our own dog-food.

### [`.github/workflows/autofix.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/autofix.yaml]

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

### [`.github/workflows/autolock.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/autolock.yaml]

- **Lock inactive threads** (`lock`)

  - Automatically locks closed issues and PRs after 90 days of inactivity using [`lock-threads`](https://github.com/dessant/lock-threads)

### [`.github/workflows/changelog.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/changelog.yaml]

- **Version increments** (`version-increments`)

  - Creates PRs for minor and major version bumps using [`bump-my-version`](https://github.com/callowayproject/bump-my-version)
  - **Requires**:
    - `bump-my-version` configuration in `pyproject.toml`
    - A `changelog.md` file
  - **Skipped for**:
    - Schedule events
    - Release commits (starting with `[changelog] Release v`)

- **Prepare release** (`prepare-release`)

  - Creates a release PR with changelog updates and version tagging using [`bump-my-version`](https://github.com/callowayproject/bump-my-version)
  - **Requires**:
    - `bump-my-version` configuration in `pyproject.toml`
    - A `changelog.md` file

### [`.github/workflows/docs.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/docs.yaml]

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
    - Sphinx autodoc enabled (checks for `sphinx.ext.autodoc` in `docs/conf.py`)

- **Deploy Sphinx doc** (`deploy-docs`)

  - Builds Sphinx-based documentation and publishes it to GitHub Pages using [`sphinx`](https://github.com/sphinx-doc/sphinx) and [`gh-pages`](https://github.com/peaceiris/actions-gh-pages)
  - **Requires**:
    - Python package with a `pyproject.toml` file
    - Sphinx configuration file at `docs/conf.py`
    - All Sphinx dependencies in a `docs` [extra dependency group](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#dependencies-and-requirements):
      ```toml
      [project.optional-dependencies]
      docs = [
          "furo",
          "myst-parser",
          "sphinx",
          ...
      ]
      ```

- **Sync awesome template** (`awesome-template-sync`)

  - Syncs awesome list projects from the [`awesome-template`](https://github.com/kdeldycke/awesome-template) repository using [`actions-template-sync`](https://github.com/AndreasAugustin/actions-template-sync)
  - **Requires**:
    - Repository name starts with `awesome-`
    - Repository is not [`awesome-template`](https://github.com/kdeldycke/awesome-template) itself

### [`.github/workflows/labels.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/labels.yaml]

- **Sync labels** (`labels`)

  - Synchronizes repository labels from a YAML definition file using [`action-manage-label`](https://github.com/julb/action-manage-label)

### [`.github/workflows/labeller-content-based.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/labeller-content-based.yaml]

- **Content-based labeller** (`labeller`)

  - Automatically labels issues and PRs based on title and body content using [`issue-labeler`](https://github.com/github/issue-labeler)
  - **Skipped for**:
    - `prepare-release` branch
    - Bot-created PRs

### [`.github/workflows/labeller-file-based.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/labeller-file-based.yaml]

- **File-based labeller** (`labeller`)

  - Automatically labels PRs based on changed file paths using [`labeler`](https://github.com/actions/labeler)
  - **Skipped for**:
    - `prepare-release` branch
    - Bot-created PRs

### [`.github/workflows/label-sponsors.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/label-sponsors.yaml]

- **Tag sponsors** (`label-sponsors`)

  - Adds a `💖 sponsors` label to issues and PRs from sponsors using [`is-sponsor-label-action`](https://github.com/JasonEtco/is-sponsor-label-action)
  - **Skipped for**:
    - `prepare-release` branch
    - Bot-created PRs

### [`.github/workflows/lint.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/lint.yaml]

- **Mypy lint** (`mypy-lint`)

  - Type-checks Python code using [`mypy`](https://github.com/python/mypy)
  - **Requires**:
    - Python files (`**/*.{py,pyi,pyw,pyx,ipynb}`) in the repository
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

### [`.github/workflows/release.yaml` jobs](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/release.yaml]

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

### Why all these `requirements/*.txt` files?

Let's look for example at the `lint-yaml` job from [`.github/workflows/lint.yaml`](https://github.com/kdeldycke/workflows/blob/72a2e5d5cd6cf4d4c8369a17cee922a43acaa57f/.github/workflows/lint.yaml#L67-L85). Here [we only need to run `yamllint`](https://github.com/kdeldycke/workflows/blob/72a2e5d5cd6cf4d4c8369a17cee922a43acaa57f/.github/workflows/lint.yaml#L85). This CLI is [distributed on PyPi](https://pypi.org/project/yamllint/).

So we could have simply run it with this step:

```yaml
  - run: |
      uvx -- yamllint
```

Instead, we install it by pointing to the [`requirements/yamllint.txt` file](https://github.com/kdeldycke/workflows/blob/main/requirements/yamllint.txt):

```yaml
  - run: |
      uvx --with-requirements https://raw.githubusercontent.com/kdeldycke/workflows/main/requirements/yamllint.txt -- yamllint
```

Why? Because I want the version of `yamllint` to be pinned. By pinning it, I make the workflow stable, predictable and reproducible.

So why use a dedicated requirements file? Why don't we simply add the version? Like this:

```yaml
  - run: |
      uvx -- yamllint==1.37.1
```

That would indeed pin the version. But it requires the maintainer (me) to keep track of new release and update manually the version string. That's a lot of work. And I'm lazy. So this should be automated.

To automate that, the only practical way I found was to rely on dependabot. But dependabot cannot update arbitrary versions in `run:` YAML blocks. It [only supports `requirements.txt` and `pyproject.toml`](https://github.com/dependabot/dependabot-core/blob/c938bbf7cb4da88053d4379dcab297a3eaa8c0a7/python/lib/dependabot/python/file_fetcher.rb#L24-L44) files for Python projects.

So to keep track of new versions of dependencies while keeping them stable, we've hard-coded all Python libraries and CLIs in the `requirements/*.txt` files. All with pinned versions.

And for the case we need to install all dependencies in one go, we have a [`requirements.txt` file at the root](https://github.com/kdeldycke/workflows/blob/main/requirements.txt) that is referencing all files from the `requirements/` subfolder.

> [!NOTE]
> In the future, we might be able to get rid of this workaround by [relying on Renovate](https://github.com/kdeldycke/workflows/issues/1728).

### Permissions and token

This repository updates itself via GitHub actions. It particularly updates its own YAML files in `.github/workflows`. That's forbidden by default. So we need extra permissions.

Usually, to grant special permissions to some jobs, you use the [`permissions` parameter in workflow](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#permissions) files. It looks like this:

```yaml
on: (...)

jobs:

  my-job:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write

    steps: (...)
```

But the `contents: write` permission doesn't allow write access to the workflow files in the `.github` subfolder. There is `actions: write`, but it only covers workflow runs, not their YAML source file. Even a `permissions: write-all` doesn't work. So you cannot use the `permissions` parameter to allow a repository's workflow update its own workflow files.

You will always end up with this kind or errors:

```text
   ! [remote rejected] branch_xxx -> branch_xxx (refusing to allow a GitHub App to create or update workflow `.github/workflows/my_workflow.yaml` without `workflows` permission)

  error: failed to push some refs to 'https://github.com/kdeldycke/my-repo'
```

> [!NOTE]
> That's also why the Settings > Actions > General > Workflow permissions parameter on your repository has no effect on this issue, even with the `Read and write permissions` set:
> ![](docs/assets/repo-workflow-permissions.png)

To bypass the limitation, we rely on a custom access token. By convention, we call it `WORKFLOW_UPDATE_GITHUB_PAT`. It will be used, [in place of the default `secrets.GITHUB_TOKEN`](https://github.com/search?q=repo%3Akdeldycke%2Fworkflows%20WORKFLOW_UPDATE_GITHUB_PAT&type=code), in steps in which we need to change the workflow YAML files.

To create this custom `WORKFLOW_UPDATE_GITHUB_PAT`:

- From your GitHub user, go to `Settings` > `Developer Settings` > `Personal Access Tokens` > `Fine-grained tokens`
- Click on the `Generate new token` button
- Choose a good token name like `workflow-self-update` to make your intention clear
- Choose `Only select repositories` and the list the repositories in needs of updating their workflow YAML files
- In the `Repository permissions` drop-down, sets:
  - `Contents`: `Access: **Read and Write**`
  - `Metadata` (mandatory): `Access: **Read-only**`
  - `Pull Requests`: `Access: **Read and Write**`
  - `Workflows`: `Access: **Read and Write**`
    > [!NOTE]
    > This is the only place where I can have control over the `Workflows` permission, which is not supported by the `permissions:` parameter in YAML files.
- Now save these parameters and copy the `github_pat_XXXX` secret token
- Got to your repo > `Settings` > `Security` > `Secrets and variables` > `Actions` > `Secrets` > `Repository secrets` and click `New repository secrets`
- Name your secret `WORKFLOW_UPDATE_GITHUB_PAT` and copy the `github_pat_XXXX` token in the `Secret` field

Now re-run your actions and they should be able to update the workflow files in `.github` folder without the `refusing to allow a GitHub App to create or update workflow` error.

### Release management

It turns out [Release Engineering is a full-time job, and full of edge-cases](https://web.archive.org/web/20250126113318/https://blog.axo.dev/2023/02/cargo-dist).

Things have improved a lot in the Python ecosystem with `uv`. But there are still a lot of manual steps to do to release.

So I made up this [`release.yaml` workflow](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/release.yaml), which:

1. Extracts project metadata from `pyproject.toml`
1. Generates a build matrix of all commits / os / arch / CLI entry points
1. Builds Python wheels with `uv`
1. Compiles binaries of all CLI with Nuitka
1. Tag the release commit in Git
1. Produces attestations of released artefacts
1. Publish new version to PyPi
1. Publish a GitHub release
1. Attach and rename build artifacts to the GitHub release

## Changelog

A [detailed changelog](changelog.md) is available.

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
- ![GitHub stars](https://img.shields.io/github/stars/themagicalmammal/wikibot?label=%E2%AD%90&style=flat-square) [Wiki bot](https://github.com/themagicalmammal/wikibot) - A bot which provides features from Wikipedia like summary, title searches, location API etc.
- ![GitHub stars](https://img.shields.io/github/stars/themagicalmammal/stock-analyser?label=%E2%AD%90&style=flat-square) [Stock Analysis](https://github.com/themagicalmammal/stock-analyser) - Simple to use interfaces for basic technical analysis of stocks.
- ![GitHub stars](https://img.shields.io/github/stars/themagicalmammal/genetictabler?label=%E2%AD%90&style=flat-square) [GeneticTabler](https://github.com/themagicalmammal/genetictabler) - Time Table Scheduler using Genetic Algorithms.
- ![GitHub stars](https://img.shields.io/github/stars/themagicalmammal/excel-write?label=%E2%AD%90&style=flat-square) [Excel Write](https://github.com/themagicalmammal/excel-write) - Optimised way to write in excel files.

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
