# {octicon}`command-palette` CLI

> [!TIP]
> Each `[tool.repomatic]` config option maps to CLI behavior. See the [configuration reference](configuration.md) for project-level defaults.

<!-- cli-reference-start -->

| Command                                                                     | Description                                             |
| :-------------------------------------------------------------------------- | :------------------------------------------------------ |
| [`repomatic broken-links`](#repomatic-broken-links)                         | Manage broken links issue lifecycle                     |
| [`repomatic cache`](#repomatic-cache)                                       | Manage the download cache                               |
| [`repomatic cache clean`](#repomatic-cache-clean)                           | Remove cached entries                                   |
| [`repomatic cache help`](#repomatic-cache-help)                             | Show help for a command                                 |
| [`repomatic cache path`](#repomatic-cache-path)                             | Print the cache directory path                          |
| [`repomatic cache show`](#repomatic-cache-show)                             | List cached entries                                     |
| [`repomatic changelog`](#repomatic-changelog)                               | Maintain a Markdown-formatted changelog                 |
| [`repomatic check-renovate`](#repomatic-check-renovate)                     | Check Renovate migration prerequisites                  |
| [`repomatic clean-unmodified-configs`](#repomatic-clean-unmodified-configs) | Remove config files that match bundled defaults         |
| [`repomatic convert-to-myst`](#repomatic-convert-to-myst)                   | Convert reST docstrings to MyST in Python files         |
| [`repomatic fix-vulnerable-deps`](#repomatic-fix-vulnerable-deps)           | Upgrade packages with known vulnerabilities             |
| [`repomatic format-images`](#repomatic-format-images)                       | Format images with lossless optimization                |
| [`repomatic git-tag`](#repomatic-git-tag)                                   | Create and push a Git tag                               |
| [`repomatic help`](#repomatic-help)                                         | Show help for a command                                 |
| [`repomatic init`](#repomatic-init)                                         | Bootstrap a repository to use reusable workflows        |
| [`repomatic lint-changelog`](#repomatic-lint-changelog)                     | Check changelog dates against release dates             |
| [`repomatic lint-repo`](#repomatic-lint-repo)                               | Run repository consistency checks                       |
| [`repomatic list-skills`](#repomatic-list-skills)                           | List available Claude Code skills                       |
| [`repomatic metadata`](#repomatic-metadata)                                 | Output project metadata                                 |
| [`repomatic pr-body`](#repomatic-pr-body)                                   | Generate PR body with workflow metadata                 |
| [`repomatic release-prep`](#repomatic-release-prep)                         | Prepare files for a release                             |
| [`repomatic run`](#repomatic-run)                                           | Run an external tool with managed config                |
| [`repomatic scan-virustotal`](#repomatic-scan-virustotal)                   | Upload release binaries to VirusTotal                   |
| [`repomatic setup-guide`](#repomatic-setup-guide)                           | Manage setup guide issue lifecycle                      |
| [`repomatic show-config`](#repomatic-show-config)                           | Print [tool.repomatic] configuration reference          |
| [`repomatic sponsor-label`](#repomatic-sponsor-label)                       | Label issues/PRs from GitHub sponsors                   |
| [`repomatic sync-bumpversion`](#repomatic-sync-bumpversion)                 | Sync bumpversion config from bundled template           |
| [`repomatic sync-dev-release`](#repomatic-sync-dev-release)                 | Sync rolling dev pre-release on GitHub                  |
| [`repomatic sync-github-releases`](#repomatic-sync-github-releases)         | Sync GitHub release notes from changelog                |
| [`repomatic sync-gitignore`](#repomatic-sync-gitignore)                     | Sync .gitignore from gitignore.io templates             |
| [`repomatic sync-labels`](#repomatic-sync-labels)                           | Sync repository labels via labelmaker                   |
| [`repomatic sync-mailmap`](#repomatic-sync-mailmap)                         | Sync Git's .mailmap file with missing contributors      |
| [`repomatic sync-uv-lock`](#repomatic-sync-uv-lock)                         | Re-lock dependencies and prune stale cooldown overrides |
| [`repomatic test-plan`](#repomatic-test-plan)                               | Run a test plan from a file against a binary            |
| [`repomatic unsubscribe-threads`](#repomatic-unsubscribe-threads)           | Unsubscribe from closed, inactive notification threads  |
| [`repomatic update-checksums`](#repomatic-update-checksums)                 | Update SHA-256 checksums for binary downloads           |
| [`repomatic update-deps-graph`](#repomatic-update-deps-graph)               | Generate dependency graph from uv lockfile              |
| [`repomatic update-docs`](#repomatic-update-docs)                           | Regenerate Sphinx API docs and run update script        |
| [`repomatic verify-binary`](#repomatic-verify-binary)                       | Verify binary architecture using exiftool               |
| [`repomatic version-check`](#repomatic-version-check)                       | Check if a version bump is allowed                      |
| [`repomatic workflow`](#repomatic-workflow)                                 | Lint downstream workflow caller files                   |
| [`repomatic workflow help`](#repomatic-workflow-help)                       | Show help for a command                                 |
| [`repomatic workflow lint`](#repomatic-workflow-lint)                       | Lint workflow files for common issues                   |

## Help screen

```text
Usage: repomatic [OPTIONS] COMMAND [ARGS]...

Options:
  --time / --no-time      Measure and print elapsed execution time.  [default:
                          no-time]
  --color, --ansi / --no-color, --no-ansi
                          Strip out all colors and all ANSI codes from output.
                          [default: color]
  --config CONFIG_PATH    Location of the configuration file. Supports local
                          path with glob patterns or remote URL.  [default: ~/.c
                          onfig/repomatic/{*.toml,*.yaml,*.yml,*.json,*.ini,pypr
                          oject.toml}]
  --no-config             Ignore all configuration files and only use command
                          line parameters and environment variables.
  --validate-config FILE  Validate the configuration file and exit.
  --show-params           Show all CLI parameters, their provenance, defaults
                          and value, then exit.
  --table-format [aligned|asciidoc|colon-grid|csv|csv-excel|csv-excel-tab|csv-unix|double-grid|double-outline|fancy-grid|fancy-outline|github|grid|heavy-grid|heavy-outline|hjson|html|jira|json|json5|jsonc|latex|latex-booktabs|latex-longtable|latex-raw|mediawiki|mixed-grid|mixed-outline|moinmoin|orgtbl|outline|pipe|plain|presto|pretty|psql|rounded-grid|rounded-outline|rst|simple|simple-grid|simple-outline|textile|toml|tsv|unsafehtml|vertical|xml|yaml|youtrack]
                          Rendering style of tables.  [default: rounded-outline]
  --verbosity LEVEL       Either CRITICAL, ERROR, WARNING, INFO, DEBUG.
                          [default: WARNING]
  -v, --verbose           Increase the default WARNING verbosity by one level
                          for each additional repetition of the option.
                          [default: 0]
  --version               Show the version and exit.
  -h, --help              Show this message and exit.

Project setup:
  init                      Bootstrap a repository to use reusable workflows
  metadata                  Output project metadata
  show-config               Print [tool.repomatic] configuration reference
  workflow                  Lint downstream workflow caller files
  update-deps-graph         Generate dependency graph from uv lockfile
  update-docs               Regenerate Sphinx API docs and run update script
  convert-to-myst           Convert reST docstrings to MyST in Python files
  list-skills               List available Claude Code skills
  update-checksums          Update SHA-256 checksums for binary downloads
  format-images             Format images with lossless optimization

Release & versioning:
  changelog                 Maintain a Markdown-formatted changelog
  release-prep              Prepare files for a release
  version-check             Check if a version bump is allowed
  git-tag                   Create and push a Git tag
  scan-virustotal           Upload release binaries to VirusTotal

Sync:
  sync-gitignore            Sync .gitignore from gitignore.io templates
  sync-github-releases      Sync GitHub release notes from changelog
  sync-dev-release          Sync rolling dev pre-release on GitHub
  sync-mailmap              Sync Git's .mailmap file with missing contributors
  fix-vulnerable-deps       Upgrade packages with known vulnerabilities
  sync-uv-lock              Re-lock dependencies and prune stale cooldown
                            overrides
  sync-bumpversion          Sync bumpversion config from bundled template
  clean-unmodified-configs  Remove config files that match bundled defaults
  sync-labels               Sync repository labels via labelmaker

Linting & checks:
  test-plan                 Run a test plan from a file against a binary
  verify-binary             Verify binary architecture using exiftool
  check-renovate            Check Renovate migration prerequisites
  lint-repo                 Run repository consistency checks
  lint-changelog            Check changelog dates against release dates
  run                       Run an external tool with managed config
  cache                     Manage the download cache

GitHub issues & PRs:
  sponsor-label             Label issues/PRs from GitHub sponsors
  broken-links              Manage broken links issue lifecycle
  setup-guide               Manage setup guide issue lifecycle
  unsubscribe-threads       Unsubscribe from closed, inactive notification
                            threads
  pr-body                   Generate PR body with workflow metadata

Other commands:
  help                      Show help for a command.
```

## `repomatic broken-links`

```text
Usage: repomatic broken-links [OPTIONS]

  Manage the broken links issue lifecycle.

  Combines Lychee and Sphinx linkcheck results into a single "Broken links"
  issue. Creates, updates, or closes the issue based on results.

  Requires the gh CLI to be installed and authenticated.

  In GitHub Actions, most options are auto-detected:
  - --repo-name defaults to $GITHUB_REPOSITORY name component.
  - --body-file defaults to ./lychee/out.md when --lychee-exit-code is set.
  - --output-json defaults to ./docs/linkcheck/output.json if it exists.
  - --source-url is composed from $GITHUB_SERVER_URL, $GITHUB_REPOSITORY,
    and $GITHUB_SHA when --output-json is set.

  Examples:
      # In GitHub Actions (auto-detection)
      repomatic broken-links --lychee-exit-code 2

      # Explicit options
      repomatic broken-links \
          --lychee-exit-code 2 \
          --body-file ./lychee/out.md \
          --repo-name "my-repo"

Options:
  --lychee-exit-code INTEGER  Exit code from lychee (0=no broken links, 2=broken
                              links found).
  --body-file FILE            Path to the issue body file (lychee output).
  --output-json FILE          Path to Sphinx linkcheck output.json file.
  --source-url TEXT           Base URL for linking filenames and line numbers in
                              the Sphinx report. Example:
                              https://github.com/owner/repo/blob/<sha>/docs
  --repo-name TEXT            Repository name (for label selection). Defaults to
                              $GITHUB_REPOSITORY name component.
  -h, --help                  Show this message and exit.
```

## `repomatic cache`

```text
Usage: repomatic cache [OPTIONS] COMMAND [ARGS]...

  Manage the local download cache.

  Binary tools and HTTP API responses are cached to avoid redundant downloads.
  This group provides subcommands to inspect, clean, and locate the cache.

Options:
  -h, --help  Show this message and exit.

Commands:
  clean  Remove cached entries
  help   Show help for a command.
  path   Print the cache directory path
  show   List cached entries
```

### `repomatic cache clean`

```text
Usage: repomatic cache clean [OPTIONS]

  Remove cached binaries and HTTP responses.

  Without options, removes everything. Use --tool to target a specific binary
  tool, --namespace for a specific HTTP namespace, or --max-age for entries
  older than a threshold.

  Examples:
      repomatic cache clean
      repomatic cache clean --tool ruff
      repomatic cache clean --namespace pypi
      repomatic cache clean --max-age 7

Options:
  --tool TEXT        Only remove binary entries for this tool.
  --namespace TEXT   Only remove HTTP entries in this namespace (e.g., pypi,
                     github-releases).
  --max-age INTEGER  Only remove entries older than this many days.
  -h, --help         Show this message and exit.
```

### `repomatic cache help`

```text
Usage: repomatic cache help [OPTIONS]
                            [COMMAND_PATH]...

  Show help for a command.

Options:
  --search TEXT  Search all subcommands for matching options or descriptions.
  -h, --help     Show this message and exit.
```

### `repomatic cache path`

```text
Usage: repomatic cache path [OPTIONS]

  Print the absolute path to the cache directory.

  Useful for CI integration with actions/cache or similar tools.

Options:
  -h, --help  Show this message and exit.
```

### `repomatic cache show`

```text
Usage: repomatic cache show [OPTIONS]

  List all cached binaries and HTTP responses.

Options:
  --sort-by [type|name|detail|size|age]
              Sort table by this column. Repeat to set priority.  [default:
              name]
  -h, --help  Show this message and exit.
```

## `repomatic changelog`

```text
Usage: repomatic changelog [OPTIONS] [CHANGELOG_PATH]

  Stamp the changelog with the current version's release header.

Options:
  --source FILE  Changelog source file. Defaults to the configured
                 changelog.location.
  -h, --help     Show this message and exit.
```

## `repomatic check-renovate`

```text
Usage: repomatic check-renovate [OPTIONS]

  Check prerequisites for Renovate migration.

  Validates that:

  - renovate.json5 configuration exists
  - No Dependabot version updates config exists (.github/dependabot.yaml)
  - Dependabot security updates are disabled
  - Token has required PAT permissions (commit statuses, contents, issues,
    pull requests, vulnerability alerts, workflows)

  Use --format=github to output results for $GITHUB_OUTPUT, allowing workflows
  to use the values in conditional steps.

  Examples:
      # Human-readable output (default)
      repomatic check-renovate

      # JSON output for parsing
      repomatic check-renovate --format=json

      # GitHub Actions output format
      repomatic check-renovate --format=github --output "$GITHUB_OUTPUT"

      # Manual invocation
      repomatic check-renovate --repo owner/repo --sha abc123

Options:
  --repo TEXT                  Repository in 'owner/repo' format. Defaults to
                               $GITHUB_REPOSITORY.
  --sha TEXT                   Commit SHA for permission checks. Defaults to
                               $GITHUB_SHA.
  --format [github|json|text]  Output format: text (human-readable), json
                               (structured), or github (for $GITHUB_OUTPUT).
                               [default: text]
  -o, --output FILE            Output file path. Defaults to stdout.  [default:
                               -]
  -h, --help                   Show this message and exit.
```

## `repomatic clean-unmodified-configs`

```text
Usage: repomatic clean-unmodified-configs [OPTIONS]

  Remove config files identical to their bundled defaults.

  Scans both tool configs (yamllint, zizmor, etc.) and init-managed configs
  (labels, renovate) and deletes any file whose content matches the bundled
  default after whitespace normalization.

  Designed for standalone use. The sync-repomatic autofix job uses repomatic
  init --delete-unmodified instead.

Options:
  -h, --help  Show this message and exit.
```

## `repomatic convert-to-myst`

```text
Usage: repomatic convert-to-myst [OPTIONS] [DIRECTORY]

  Convert reST docstrings to MyST markdown in Python source files.

  Transforms reST markup in docstrings and `#:` comment blocks to MyST. The
  companion Sphinx extension `repomatic.myst_docstrings` converts the MyST back
  to reST at build time, so `sphinx.ext.autodoc` still works.

  If DIRECTORY is not specified, auto-detects the source package directory from
  the project's script entry points in `pyproject.toml`.

  Safe to re-run: already-converted MyST syntax does not match the reST
  patterns, so the conversion is idempotent.

Options:
  -h, --help  Show this message and exit.
```

## `repomatic fix-vulnerable-deps`

```text
Usage: repomatic fix-vulnerable-deps [OPTIONS]

  Detect and upgrade packages with known security vulnerabilities.

  Queries every advisory database enabled in
  [tool.repomatic] vulnerable-deps.sources (default: uv-audit and
  github-advisories), unions and deduplicates the results, then upgrades
  each fixable package with uv lock --upgrade-package and:
    - bypasses the exclude-newer cooldown for security fixes
    - persists exclude-newer-package entries in pyproject.toml
    - prints a markdown report of vulnerabilities and version changes

  Examples:
      # Scan and fix vulnerabilities (uses GITHUB_REPOSITORY when set)
      repomatic fix-vulnerable-deps

      # Force a specific repository for the GHSA query
      repomatic fix-vulnerable-deps --repo owner/name

      # CI: write markdown report as a GitHub Actions step output
      repomatic fix-vulnerable-deps \
          --output "$GITHUB_OUTPUT" --output-format github-actions

Options:
  --lockfile FILE  Path to the uv.lock file.  [default: uv.lock]
  --repo TEXT      Repository in OWNER/NAME format. Required to query the GitHub
                   Advisory Database. Defaults to GITHUB_REPOSITORY when set.
                   [default: (dynamic)]
  --output FILE    Write a markdown report (vulnerabilities + updates) to this
                   file.
  --output-format [markdown|github-actions]
                   Format for --output. github-actions produces format for PR
                   template consumption in workflows.  [default: markdown]
  -h, --help       Show this message and exit.
```

## `repomatic format-images`

```text
Usage: repomatic format-images [OPTIONS]

  Format images by losslessly optimizing them with external CLI tools.

  Discovers PNG and JPEG files and compresses them losslessly in-place using
  oxipng and jpegoptim. Produces a markdown summary table showing before/after
  sizes and savings.

  Only lossless optimizers are used so that results are idempotent: running the
  command twice produces no further changes.

  Required tools (install via apt):
      sudo apt-get install oxipng jpegoptim

  Examples:
      # Format images and print summary
      repomatic format-images

      # CI: write as a GitHub Actions step output
      repomatic format-images \
          --output "$GITHUB_OUTPUT" --output-format github-actions

      # Use a 10% minimum savings threshold
      repomatic format-images --min-savings 10

Options:
  --min-savings FLOAT RANGE  Minimum percentage savings to keep an optimized
                             file.  [default: 5; 0<=x<=100]
  --min-savings-bytes INTEGER RANGE
                             Minimum absolute byte savings to keep an optimized
                             file.  [default: 1024; x>=0]
  --output FILE              Output file path. Defaults to stdout.  [default: -]
  --output-format [markdown|github-actions]
                             Format for --output. github-actions produces format
                             for PR template consumption in workflows.
                             [default: markdown]
  -h, --help                 Show this message and exit.
```

## `repomatic git-tag`

```text
Usage: repomatic git-tag [OPTIONS]

  Create and optionally push a Git tag.

  This command is idempotent: if the tag already exists and --skip-existing is
  used, it exits successfully without making changes. This allows safe re-runs
  of workflows interrupted after tag creation.

  Examples:
      # Create and push a tag
      repomatic git-tag --tag v1.2.3

      # Tag a specific commit
      repomatic git-tag --tag v1.2.3 --commit abc123def

      # Create tag without pushing
      repomatic git-tag --tag v1.2.3 --no-push

      # Fail if tag exists
      repomatic git-tag --tag v1.2.3 --error-existing

      # Output result for GitHub Actions
      repomatic git-tag --tag v1.2.3 --output "$GITHUB_OUTPUT"

Options:
  --tag TEXT          Tag name to create (e.g., v1.2.3).  [required]
  --commit TEXT       Commit to tag. Defaults to HEAD.
  --push / --no-push  Push the tag to remote after creation.  [default: push]
  --skip-existing / --error-existing
                      Skip silently if tag exists, or fail with an error.
                      [default: skip-existing]
  -o, --output FILE   Output file for created=true/false (e.g., $GITHUB_OUTPUT).
  -h, --help          Show this message and exit.
```

## `repomatic help`

```text
Usage: repomatic help [OPTIONS] [COMMAND_PATH]...

  Show help for a command.

Options:
  --search TEXT  Search all subcommands for matching options or descriptions.
  -h, --help     Show this message and exit.
```

## `repomatic init`

```text
Usage: repomatic init [OPTIONS]
                      [[COMPONENT[/FILE]]]...

  Bootstrap a repository to use reusable workflows from kdeldycke/repomatic.

  With no arguments, generates thin-caller workflow files, exports configuration
  files (Renovate, labels, labeller rules), and creates a minimal changelog.
  Specify COMPONENTS to initialize only selected parts.

  Scope restrictions (awesome-only, non-awesome) and [tool.repomatic] exclude
  entries only apply during bare init (no arguments). Explicitly naming a
  component bypasses scope, allowing workflows to materialize out-of-scope
  configs at runtime.

  Selectors use the same syntax as the exclude config in [tool.repomatic]: bare
  names select an entire component, qualified component/file entries select a
  single file.

  Components:
      labels              Label config files (labels.toml + labeller rules)
      codecov             Codecov PR comment config (.github/codecov.yaml)
      renovate            Renovate config (renovate.json5)
      agents              Claude Code agent definitions (.claude/agents/)
      skills              Claude Code skill definitions (.claude/skills/)
      workflows           Thin-caller workflow files
      awesome-template    Boilerplate for awesome-* repositories
      changelog           Minimal changelog.md
      lychee              Lychee link checker configuration
      ruff                Ruff linter/formatter configuration
      pytest              Pytest test configuration
      mypy                Mypy type checking configuration
      mdformat            mdformat Markdown formatter configuration
      bumpversion         bump-my-version configuration
      typos               Typos spell checker configuration

  File-level selectors (labels, codecov, renovate, agents, skills, workflows):
      workflows/autofix.yaml    A single workflow
      skills/repomatic-topics   A single skill
      labels/labels.toml        A single label config file

  Examples:
      # Full bootstrap (workflows + labels + renovate + changelog)
      repomatic init

      # Pin to a specific version
      repomatic init --version v5.9.1

      # Install a single skill
      repomatic init skills/repomatic-topics

      # One workflow + all labels
      repomatic init workflows/autofix.yaml labels

      # Only merge ruff config into pyproject.toml
      repomatic init ruff

      # Multiple components
      repomatic init ruff bumpversion

Options:
  --version TEXT          Version pin for upstream workflows (e.g., v5.10.0).
                          Defaults to the latest release derived from the
                          package version.
  --repo TEXT             Upstream repository containing reusable workflows.
                          [default: kdeldycke/repomatic]
  --output-dir DIRECTORY  Root directory of the target repository.  [default: .]
  --delete-excluded       Delete files that are excluded by config but still on
                          disk.
  --delete-unmodified     Delete config files identical to bundled defaults.
  -h, --help              Show this message and exit.
```

## `repomatic lint-changelog`

```text
Usage: repomatic lint-changelog [OPTIONS]

  Verify that changelog release dates match canonical release dates.

  Uses PyPI upload dates as the canonical reference when the project is
  published to PyPI. Falls back to git tag dates for non-PyPI projects.

  PyPI timestamps are immutable and reflect the actual publication date, making
  them more reliable than git tags which can be recreated.

  Also detects orphaned versions: versions that exist as git tags, GitHub
  releases, or PyPI packages but have no corresponding changelog entry. Orphans
  cause a non-zero exit code.

  Reads pypi-package-history from [tool.repomatic] to fetch releases published
  under former package names (for renamed projects).

  Output symbols:
      ✓  Dates match
      ⚠  Version not found on reference source (warning, non-fatal)
      ✗  Date mismatch (error, fatal)

  With --fix, the command also:
      - Corrects mismatched dates to match the canonical source.
      - Adds a PyPI link admonition under each released version.
      - Adds a CAUTION admonition for yanked releases.
      - Adds a WARNING admonition for versions not on PyPI.
      - Inserts placeholder sections for orphaned versions.

  Examples:
      # Check the default changelog.md (auto-detects PyPI package)
      repomatic lint-changelog

      # Fix dates and add admonitions
      repomatic lint-changelog --fix

      # Explicit package name
      repomatic lint-changelog --package repomatic

Options:
  --changelog FILE  Path to the changelog file. Defaults to the configured
                    changelog.location.
  --package TEXT    PyPI package name for date lookups. Auto-detected from
                    pyproject.toml.
  --fix             Fix date mismatches and add PyPI admonitions to the
                    changelog.
  -h, --help        Show this message and exit.
```

## `repomatic lint-repo`

```text
Usage: repomatic lint-repo [OPTIONS]

  Run consistency checks on repository metadata.

  Reads package_name, is_sphinx, and project_description from pyproject.toml in
  the current directory.

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
    - Fork PR workflow approval policy strict enough (warning).
    - VIRUSTOTAL_API_KEY secret missing when Nuitka is active (warning).

  When a PAT is detected, additional capability checks are run:
    - Contents permission (error).
    - Issues permission (error).
    - Pull requests permission (error).
    - Dependabot alerts permission and alerts enabled (error).
    - Workflows permission (error).
    - Commit statuses permission (error, requires --sha).

  Examples:
      # In GitHub Actions (reads pyproject.toml automatically)
      repomatic lint-repo --repo-name my-package

      # Local run (derives repo from $GITHUB_REPOSITORY or --repo)
      repomatic lint-repo --repo owner/repo

      # With PAT capability checks
      repomatic lint-repo --has-pat --sha abc123

Options:
  --repo-name TEXT          Repository name. Defaults to $GITHUB_REPOSITORY name
                            component.
  --repo TEXT               Repository in 'owner/repo' format. Defaults to
                            $GITHUB_REPOSITORY.
  --has-pat / --no-has-pat  Whether REPOMATIC_PAT is configured. Enables PAT
                            capability checks. Auto-detected from the
                            REPOMATIC_PAT environment variable when omitted.
  --has-virustotal-key      Whether VIRUSTOTAL_API_KEY is configured.
  --sha TEXT                Commit SHA for permission checks. Defaults to
                            $GITHUB_SHA.
  -h, --help                Show this message and exit.
```

## `repomatic list-skills`

```text
Usage: repomatic list-skills [OPTIONS]

  List all bundled Claude Code skills grouped by lifecycle phase.

  Reads skill definitions from the bundled data files and displays them in a
  table grouped by phase: Setup, Development, Quality, and Release.

Options:
  -h, --help  Show this message and exit.
```

## `repomatic metadata`

```text
Usage: repomatic metadata [OPTIONS] [KEYS]...

  Dump project metadata to a file.

  Prints all metadata keys to stdout by default. Use --output to write to a
  file. Pass key names as arguments to filter output.

  Examples:
      repomatic metadata current_version is_python_project
      repomatic metadata --list-keys
      repomatic metadata --format github-json --output "$GITHUB_OUTPUT" \
          current_version is_python_project

Options:
  --format [github|github-json|json]
                               Rendering format of the metadata.  [default:
                               github]
  --overwrite, --force, --replace / --no-overwrite, --no-force, --no-replace
                               Overwrite output file if it already exists.
                               [default: overwrite]
  -o, --output FILE            Output file path. Defaults to stdout.  [default:
                               -]
  --list-keys                  List all available metadata keys with
                               descriptions and exit.
  --sort-by [key|description]  Sort table by this column. Repeat to set
                               priority.  [default: key]
  -h, --help                   Show this message and exit.
```

## `repomatic pr-body`

```text
Usage: repomatic pr-body [OPTIONS]

  Generate a PR body with a collapsible workflow metadata block.

  Reads GITHUB_* environment variables to produce a <details> block containing a
  metadata table (trigger, actor, ref, commit, job, workflow, run).

  The prefix can be set via --template (built-in templates) or --prefix
  (arbitrary content, also via GHA_PR_BODY_PREFIX env var). If both are given,
  --prefix is prepended before the rendered template content.

  Examples:
      # Preview metadata block locally
      repomatic pr-body

      # CI: write as GitHub Actions step outputs
      repomatic pr-body --output "$GITHUB_OUTPUT" \
          --output-format github-actions

      # Use a built-in template
      repomatic pr-body --template bump-version \
          --version 1.2.0 --part minor

      # With a prefix via environment variable
      GHA_PR_BODY_PREFIX="Fix formatting" repomatic pr-body

Options:
  --prefix TEXT   Content to prepend before the metadata details block. Can also
                  be set via the GHA_PR_BODY_PREFIX environment variable.
                  [default: ""]
  --template [available-admonition|broken-links-issue|bump-version|detect-squash-merge|development-warning|fix-changelog|fix-typos|fix-vulnerable-deps|format-images|format-json|format-markdown|format-pyproject|format-python|format-shell|generated-footer|github-releases|immutable-releases|pr-metadata|prepare-release|refresh-tip|release-notes|release-sync-report|renovate-migration|setup-guide|setup-guide-branch-ruleset|setup-guide-dependabot|setup-guide-fork-pr-approval|setup-guide-pages-source|setup-guide-token|setup-guide-verify|setup-guide-virustotal|sync-bumpversion|sync-gitignore|sync-mailmap|sync-repomatic|sync-uv-lock|unavailable-admonition|unsubscribe-phase1|unsubscribe-phase2|update-deps-graph|update-docs|yanked-admonition]
                  Use a built-in prefix template instead of --prefix.
  --version TEXT  Version string passed to the template (e.g. 1.2.0).
  --part TEXT     Version part passed to bump-version template (e.g. minor,
                  major).
  --pr-ref TEXT   PR reference passed to detect-squash-merge template (e.g.
                  #2316).
  --output FILE   Output file path. Defaults to stdout.  [default: -]
  --output-format [markdown|github-actions]
                  Format for --output. 'github-actions' wraps body, title, and
                  commit_message as step output variables.  [default: markdown]
  -h, --help      Show this message and exit.
```

## `repomatic release-prep`

```text
Usage: repomatic release-prep [OPTIONS]

  Prepare files for a release or post-release version bump.

  This command consolidates all release preparation steps:

  - Set release date in changelog (replaces "(unreleased)" with today's date).
  - Set release date in citation.cff.
  - Update changelog comparison URL from "...main" to "...v{version}".
  - Remove the "[!WARNING]" development warning block from changelog.
  - Optionally update workflow URLs to use versioned tag.

  When running in GitHub Actions, --update-workflows is auto-detected:
  it defaults to True when $GITHUB_REPOSITORY matches the canonical
  workflows repository (kdeldycke/repomatic).

  For post-release (after the release commit), use --post-release to retarget
  workflow URLs back to the default branch.

  Examples:
      # Prepare release (changelog + citation)
      repomatic release-prep
      # Post-release: retarget workflows to main branch
      repomatic release-prep --post-release

Options:
  --changelog FILE          Path to the changelog file. Defaults to the
                            configured changelog.location.
  --citation FILE           Path to the citation file.  [default: citation.cff]
  --workflow-dir DIRECTORY  Path to the GitHub workflows directory.  [default:
                            .github/workflows]
  --default-branch TEXT     Name of the default branch for workflow URL updates.
                            [default: main]
  --update-workflows / --no-update-workflows
                            Update workflow URLs to use versioned tag instead of
                            default branch. Defaults to True when
                            $GITHUB_REPOSITORY is the canonical workflows repo.
  --post-release            Run post-release steps (retarget workflow URLs to
                            default branch).
  -h, --help                Show this message and exit.
```

## `repomatic run`

```text
Usage: repomatic run [OPTIONS] [TOOL_NAME]
                     [EXTRA_ARGS]...

  Run an external tool with managed configuration.

  Installs the tool at a pinned version, resolves config through a 4-level
  precedence chain (native config file, [tool.X] in pyproject.toml, bundled
  default, bare invocation), and invokes the tool.

  Binary tools are cached locally to avoid re-downloading on repeated runs. Use
  --no-cache to force a fresh download. See repomatic cache for cache
  management.

  Pass extra arguments to the tool after --:
      repomatic run yamllint -- --strict .
      repomatic run zizmor -- --offline .

  Override the pinned version:
      repomatic run shfmt --version 3.14.0 --skip-checksum -- .

  List all managed tools and their resolved config source:
      repomatic run --list

Options:
  --list           List all managed tools.
  --version TEXT   Override the pinned version of the tool.
  --checksum TEXT  Override the SHA-256 checksum for the current platform.
  --skip-checksum  Skip SHA-256 verification of binary downloads.
  --no-cache       Bypass the binary cache (download fresh every time).
  --sort-by [tool|version|config-source]
                   Sort table by this column. Repeat to set priority.  [default:
                   tool]
  -h, --help       Show this message and exit.
```

## `repomatic scan-virustotal`

```text
Usage: repomatic scan-virustotal [OPTIONS]

  Upload release binaries to VirusTotal and update the release body.

  Scans all .bin and .exe files in the given directory, uploads them to
  VirusTotal, and optionally appends analysis links to the GitHub release body.

  With --poll, polls the VirusTotal API for detection statistics after uploading
  (or standalone without --binaries-dir to enrich an existing table).

  Examples:
      repomatic scan-virustotal --tag v1.2.3 --binaries-dir ./binaries

      repomatic scan-virustotal --tag v1.2.3 --repo owner/repo --poll

Options:
  --tag TEXT                    Release tag to scan (e.g., v1.2.3).  [required]
  --repo TEXT                   Repository in owner/repo format.
  --api-key TEXT                VirusTotal API key.  [required]
  --binaries-dir DIRECTORY      Directory containing binary files to upload.
  --rate-limit INTEGER RANGE    Maximum VirusTotal API requests per minute.
                                [default: 4; 1<=x<=60]
  --update-release / --no-update-release
                                Append scan links to the GitHub release body.
                                [default: update-release]
  --poll / --no-poll            Poll for detection statistics after uploading.
                                [default: no-poll]
  --poll-timeout INTEGER RANGE  Maximum seconds to wait for analysis completion
                                when polling.  [default: 600; 60<=x<=3600]
  -h, --help                    Show this message and exit.
```

## `repomatic setup-guide`

```text
Usage: repomatic setup-guide [OPTIONS]

  Manage the setup guide issue lifecycle.

  Each setup step is shown as a collapsible section with a status indicator:
  incomplete steps are expanded with a warning emoji, completed steps are
  collapsed with a checkmark.

  PAT availability is auto-detected from the REPOMATIC_PAT environment variable
  when --has-pat/--no-has-pat is not specified.

  When a PAT is detected and --repo is provided, the command runs granular PAT
  permission checks and repository settings checks. The issue closes only when
  all verifiable steps pass.

  Requires the gh CLI to be installed and authenticated.

  Examples:
      # No secret: create or reopen the setup issue
      repomatic setup-guide

      # Secret configured: close the issue if all checks pass
      repomatic setup-guide --has-pat

Options:
  --has-pat / --no-has-pat  Whether REPOMATIC_PAT is configured. Auto-detected
                            from the REPOMATIC_PAT environment variable when
                            omitted.
  --has-virustotal-key      Whether VIRUSTOTAL_API_KEY is configured.
  --repo TEXT               Repository in 'owner/repo' format. Defaults to
                            $GITHUB_REPOSITORY.
  --sha TEXT                Commit SHA for permission checks. Defaults to
                            $GITHUB_SHA.
  -h, --help                Show this message and exit.
```

## `repomatic show-config`

```text
Usage: repomatic show-config [OPTIONS]

  Print the [tool.repomatic] configuration reference table.

  Renders a table of all available options, their types, defaults, and
  descriptions — generated from the Config dataclass docstrings. Respects the
  global --table-format and --sort-by options.

Options:
  --sort-by [option|type|default|description]
              Sort table by this column. Repeat to set priority.  [default:
              option]
  -h, --help  Show this message and exit.
```

## `repomatic sponsor-label`

```text
Usage: repomatic sponsor-label [OPTIONS]

  Add a label to issues or PRs from GitHub sponsors.

  Checks if the author of an issue or PR is a sponsor of the repository owner.
  If they are, adds the specified label.

  This command requires the gh CLI to be installed and authenticated.

  When run in GitHub Actions, all parameters are auto-detected from environment
  variables ($GITHUB_REPOSITORY_OWNER, $GITHUB_REPOSITORY) and the event payload
  ($GITHUB_EVENT_PATH). You can override any auto-detected value by passing it
  explicitly.

  Examples:
      # In GitHub Actions (all defaults auto-detected)
      repomatic sponsor-label

      # Override specific values
      repomatic sponsor-label --label "sponsor"

      # Manual invocation with all values
      repomatic sponsor-label --owner kdeldycke --author some-user \
          --repo kdeldycke/repomatic --number 123 --issue

Options:
  --owner TEXT            GitHub username or organization to check sponsorship
                          for. Defaults to $GITHUB_REPOSITORY_OWNER.
  --author TEXT           GitHub username of the issue/PR author to check.
                          Defaults to author from $GITHUB_EVENT_PATH.
  --repo TEXT             Repository in 'owner/repo' format. Defaults to
                          $GITHUB_REPOSITORY.
  --number INTEGER RANGE  Issue or PR number. Defaults to number from
                          $GITHUB_EVENT_PATH.  [x>=1]
  --label TEXT            Label to add if author is a sponsor.  [default: 💖
                          sponsors]
  --pr / --issue          Specify issue or pull request. Auto-detected from
                          $GITHUB_EVENT_PATH.
  -h, --help              Show this message and exit.
```

## `repomatic sync-bumpversion`

```text
Usage: repomatic sync-bumpversion [OPTIONS]

  Sync [tool.bumpversion] config in pyproject.toml from the bundled template.

  Overwrites the [tool.bumpversion] section with the canonical template bundled
  in repomatic. Designed for the sync-bumpversion autofix job. The repomatic
  init bumpversion command remains available for interactive bootstrapping.

Options:
  -h, --help  Show this message and exit.
```

## `repomatic sync-dev-release`

```text
Usage: repomatic sync-dev-release [OPTIONS]

  Sync a rolling dev pre-release on GitHub.

  Maintains a single pre-release that mirrors the unreleased changelog section.
  The dev tag is force-updated to point to the latest main commit.

  In --delete mode, removes the dev pre-release without recreating it. This is
  used during real releases to clean up.

  Examples:
      # Dry run to preview what would be synced
      repomatic sync-dev-release --dry-run

      # Create or update the dev pre-release
      repomatic sync-dev-release --live

      # Create or update with asset upload
      repomatic sync-dev-release --live --upload-assets release_assets/

      # Delete the dev pre-release (e.g. during a real release)
      repomatic sync-dev-release --live --delete

Options:
  --dry-run / --live         Report what would be done without making changes.
                             [default: dry-run]
  --delete / --no-delete     Delete-only mode: remove the dev pre-release
                             without recreating.  [default: no-delete]
  --upload-assets DIRECTORY  Directory containing assets (binaries, packages) to
                             upload.
  -h, --help                 Show this message and exit.
```

## `repomatic sync-github-releases`

```text
Usage: repomatic sync-github-releases [OPTIONS]

  Sync GitHub release notes from changelog.md.

  Compares each GitHub release body against the corresponding changelog.md
  section and updates any that have drifted.

  Examples:
      # Dry run to preview what would be updated
      repomatic sync-github-releases --dry-run

      # Update drifted release notes
      repomatic sync-github-releases --live

Options:
  --dry-run / --live  Report what would be done without making changes.
                      [default: dry-run]
  -h, --help          Show this message and exit.
```

## `repomatic sync-gitignore`

```text
Usage: repomatic sync-gitignore [OPTIONS]

  Sync a .gitignore file from gitignore.io templates.

  Fetches templates for a base set of categories plus any extras from
  [tool.repomatic] config, then appends gitignore-extra-content. Writes to the
  path specified by gitignore-location (default ./.gitignore).

  Examples:
      # Generate .gitignore using config from pyproject.toml
      repomatic sync-gitignore

      # Write to custom location
      repomatic sync-gitignore --output ./custom/.gitignore

      # Preview on stdout
      repomatic sync-gitignore --output -

Options:
  --output FILE  Output path. Defaults to gitignore-location from
                 [tool.repomatic] config.
  -h, --help     Show this message and exit.
```

## `repomatic sync-labels`

```text
Usage: repomatic sync-labels [OPTIONS]

  Sync repository labels from bundled definitions using labelmaker.

  Exports label definitions via repomatic init labels, then applies them to the
  repository using labelmaker. Applies the default profile to all repositories,
  plus the awesome profile for awesome-* repos.

  Requires GITHUB_TOKEN in the environment. Downloads labelmaker automatically
  via the tool registry.

Options:
  --repo TEXT  GitHub repository (owner/name). Auto-detected if omitted.
  -h, --help   Show this message and exit.
```

## `repomatic sync-mailmap`

```text
Usage: repomatic sync-mailmap [OPTIONS]
                              [DESTINATION_MAILMAP]

  Update .mailmap with missing contributors from Git history.

  Reads the existing .mailmap as a reference for grouped identities, then
  appends any contributors not already covered. Results are sorted but not
  regrouped: manual editing may be needed.

  The destination defaults to the source file (in-place update). Pass - to print
  to stdout instead.

Options:
  --source FILE  Mailmap source file to use as reference for contributors
                 identities that are already grouped.  [default: .mailmap]
  --create-if-missing / --skip-if-missing
                 If not found, either create the missing destination mailmap
                 file, or skip the update process entirely. This option is
                 ignored if the destination is to print the result to <stdout>.
                 [default: create-if-missing]
  -h, --help     Show this message and exit.
```

## `repomatic sync-uv-lock`

```text
Usage: repomatic sync-uv-lock [OPTIONS]

  Upgrade all dependencies and clean up stale cooldown overrides.

  Wraps uv lock --upgrade and:
    - prunes stale exclude-newer-package entries from pyproject.toml
      whose locked version has aged past the exclude-newer cutoff
    - reverts uv.lock when the only diff is timestamp noise
    - prints a table of updated packages with upload dates
    - optionally fetches release notes from GitHub (markdown)

  The table respects the global --table-format option (github, json,
  csv, etc.). Release notes are always rendered as markdown.

  Examples:
      # Upgrade and show changes
      repomatic sync-uv-lock

      # With release notes
      repomatic sync-uv-lock --release-notes

      # Machine-readable formats
      repomatic --table-format github sync-uv-lock
      repomatic --table-format json sync-uv-lock

      # CI: write markdown report as a GitHub Actions step output
      repomatic sync-uv-lock --no-table --release-notes \
          --output "$GITHUB_OUTPUT" --output-format github-actions

Options:
  --lockfile FILE       Path to the uv.lock file.  [default: uv.lock]
  --table / --no-table  Print a summary table of updated packages.  [default:
                        table]
  --release-notes / --no-release-notes
                        Fetch release notes from GitHub (markdown, appended
                        after the table).  [default: no-release-notes]
  --output FILE         Write a markdown report (table + release notes) to this
                        file.
  --output-format [markdown|github-actions]
                        Format for --output. github-actions produces format for
                        PR template consumption in workflows.  [default:
                        markdown]
  -h, --help            Show this message and exit.
```

## `repomatic test-plan`

```text
Usage: repomatic test-plan [OPTIONS]

  Run CLI test cases against a binary or command.

  Loads test plans from files (--plan-file), environment variables (--plan-
  envvar), [tool.repomatic] config, or a built-in default. Each test invokes the
  command with the specified arguments and validates the output against expected
  patterns.

Options:
  --command, --binary COMMAND    Path to the binary file to test, or a command
                                 line to be executed.  [required]
  -F, --plan-file FILE_PATH      Path to a test plan file in YAML. This option
                                 can be repeated to run multiple test plans in
                                 sequence. If not provided, a default test plan
                                 will be executed.
  -E, --plan-envvar ENVVAR_NAME  Name of an environment variable containing a
                                 test plan in YAML. This option can be repeated
                                 to collect multiple test plans.
  -t, --select-test INTEGER      Only run the tests matching the provided test
                                 case numbers. This option can be repeated to
                                 run multiple test cases. If not provided, all
                                 test cases will be run.  [x>=1]
  -s, --skip-platform [aarch64|aix|alacritty|all_agents|all_architectures|all_arm|all_ci|all_mips|all_platforms|all_shells|all_sparc|all_terminals|all_traits|all_windows|alpine|altlinux|amzn|android|apple_terminal|arch|arch_32_bit|arch_64_bit|arm|armv5tel|armv6l|armv7l|armv8l|ash|azure_pipelines|bamboo|bash|big_endian|bourne_shells|bsd|bsd_without_macos|buildkite|buildroot|c_shells|cachyos|centos|circle_ci|cirrus_ci|claude_code|cline|cloudlinux|cmd|codebuild|contour|csh|cursor|cygwin|dash|debian|dragonfly_bsd|exherbo|fedora|fish|foot|freebsd|generic_linux|gentoo|ghostty|github_ci|gitlab_ci|gnome_terminal|gnu_screen|gpu_terminals|guix|haiku|heroku_ci|hurd|hyper|i386|i586|i686|ibm_mainframe|ibm_powerkvm|illumos|iterm2|kali|kitty|konsole|ksh|kvmibm|linux|linux_layers|linux_like|linuxmint|little_endian|loongarch|loongarch64|macos|mageia|mandriva|manjaro|midnightbsd|mips|mips64|mips64el|mipsel|multiplexers|native_terminals|netbsd|nobara|nushell|openbsd|opensuse|openwrt|oracle|other_posix|other_shells|parallels|pidora|powerpc|powershell|ppc|ppc64|ppc64le|raspbian|rhel|rio|riscv|riscv32|riscv64|rocky|s390x|scientific|slackware|sles|solaris|sparc|sparc64|sunos|system_v|tabby|tcsh|teamcity|tilix|tmux|travis_ci|tumbleweed|tuxedo|ubuntu|ultramarine|unix|unix_layers|unix_without_macos|void|vscode_terminal|wasm32|wasm64|web_terminals|webassembly|wezterm|windows|windows_shells|windows_terminal|wsl1|wsl2|x86|x86_64|xenserver|xonsh|xterm|zellij|zsh]
                                 Skip tests for the specified platforms. This
                                 option can be repeated to skip multiple
                                 platforms.
  -x, --exit-on-error            Exit instantly on first failed test.
  -T, --timeout SECONDS          Set the default timeout for each CLI call, if
                                 not specified in the test plan.  [x>=0]
  --show-trace-on-error / --hide-trace-on-error
                                 Show execution trace of failed tests.
                                 [default: show-trace-on-error]
  --stats / --no-stats           Print per-manager package statistics.
                                 [default: stats]
  -h, --help                     Show this message and exit.
```

## `repomatic unsubscribe-threads`

```text
Usage: repomatic unsubscribe-threads [OPTIONS]

  Unsubscribe from closed, inactive GitHub notification threads.

  Processes notifications in two phases:

  Phase 1 — REST notification threads:
    Fetches Issue/PullRequest notification threads, inspects each for
    closed + stale status, and unsubscribes via DELETE + PATCH.

  Phase 2 — GraphQL threadless subscriptions:
    Searches for closed issues/PRs the user is involved in and
    unsubscribes via the updateSubscription mutation.

  Examples:
      # Dry run to preview what would be unsubscribed
      repomatic unsubscribe-threads --dry-run

      # Unsubscribe from threads inactive for 6+ months
      repomatic unsubscribe-threads --months 6

      # Process at most 50 threads per phase
      repomatic unsubscribe-threads --batch-size 50

Options:
  --months INTEGER RANGE      Inactivity threshold in months. Threads updated
                              more recently are kept.  [default: 3; x>=1]
  --batch-size INTEGER RANGE  Maximum number of threads/items to process per
                              phase.  [default: 200; x>=1]
  --dry-run / --live          Report what would be done without making changes.
                              [default: dry-run]
  -h, --help                  Show this message and exit.
```

## `repomatic update-checksums`

```text
Usage: repomatic update-checksums [OPTIONS]
                                  [WORKFLOW_FILE]

  Update SHA-256 checksums for direct binary downloads.

  By default, scans a workflow YAML file for GitHub release download URLs paired
  with sha256sum --check verification lines. Downloads each binary, computes the
  SHA-256, and replaces stale hashes in-place.

  With --registry, updates checksums in the repomatic run tool registry for all
  binary-distributed tools.

  Designed for Renovate postUpgradeTasks: after a version bump changes a
  download URL, this command downloads the new binary and updates the hash.

  Examples:
      # Update checksums in a single workflow file
      repomatic update-checksums .github/workflows/docs.yaml

      # Update checksums in the tool runner registry
      repomatic update-checksums --registry

Options:
  --registry  Update checksums in the tool runner registry instead of a workflow
              file.
  -h, --help  Show this message and exit.
```

## `repomatic update-deps-graph`

```text
Usage: repomatic update-deps-graph [OPTIONS]

  Generate a Mermaid dependency graph from the project's uv lockfile.

  Parses the CycloneDX SBOM export from uv and renders it as a Mermaid flowchart
  for documentation. Version specifiers from uv.lock are shown as edge labels.

  Examples:
      # Generate Mermaid graph
      repomatic update-deps-graph

      # Include test dependencies
      repomatic update-deps-graph --group test

      # Include all groups and extras
      repomatic update-deps-graph --all-groups --all-extras

      # Include all groups except typing
      repomatic update-deps-graph --all-groups --no-group typing

      # Include all extras except one
      repomatic update-deps-graph --all-extras --no-extra json5

      # Show only test group dependencies (no main deps)
      repomatic update-deps-graph --only-group test

      # Show only a specific extra's dependencies
      repomatic update-deps-graph --only-extra xml

      # Focus on a specific package
      repomatic update-deps-graph --package click-extra

      # Limit graph depth to 2 levels
      repomatic update-deps-graph --level 2

      # Save to file
      repomatic update-deps-graph --output docs/dependency-graph.md

Group filtering:
  -g, --group TEXT   Include dependencies from the specified group (e.g., test,
                     typing). Can be repeated.
  --all-groups       Include all dependency groups from pyproject.toml.
  --no-group TEXT    Exclude the specified group. Takes precedence over --all-
                     groups and --group. Can be repeated.
  --only-group TEXT  Only include dependencies from the specified group,
                     excluding main dependencies. Can be repeated.

Extra filtering:
  -e, --extra TEXT   Include dependencies from the specified extra (e.g., xml,
                     json5). Can be repeated.
  --all-extras       Include all optional extras from pyproject.toml.
  --no-extra TEXT    Exclude the specified extra, if --all-extras is supplied.
                     Can be repeated.
  --only-extra TEXT  Only include dependencies from the specified extra,
                     excluding main dependencies. Can be repeated.

Other options:
  -p, --package TEXT         Focus on a specific package's dependency tree.
  --frozen / --no-frozen     Use --frozen to skip lock file updates.  [default:
                             frozen]
  -l, --level INTEGER RANGE  Maximum depth of the dependency graph. 1 = primary
                             deps only, 2 = primary + their deps, etc.  [x>=1]
  -o, --output FILE          Output file path. Defaults to [tool.repomatic]
                             config or stdout.
  -h, --help                 Show this message and exit.
```

## `repomatic update-docs`

```text
Usage: repomatic update-docs [OPTIONS]

  Regenerate Sphinx autodoc stubs and run the project's update script.

  Orchestrates three phases:

  1. Run `sphinx-apidoc` to generate RST stubs for all modules. 2. If MyST-
  Parser is detected, convert the RST stubs to MyST markdown    with ``{eval-
  rst}`` blocks. 3. Run the project-specific `docs/docs_update.py` script (if
  present)    to generate dynamic content.

  Configuration is read from `[tool.repomatic]` in `pyproject.toml`.

Options:
  -h, --help  Show this message and exit.
```

## `repomatic verify-binary`

```text
Usage: repomatic verify-binary [OPTIONS]

  Verify that a compiled binary matches the expected architecture.

  Uses exiftool to inspect the binary and validates that its architecture
  matches what is expected for the specified target platform.

  Requires exiftool to be installed and available in PATH.

  Examples:
      # Verify a Linux ARM64 binary
      repomatic verify-binary --target linux-arm64 --binary ./mpm-linux-arm64.bin

      # Verify a Windows x64 binary
      repomatic verify-binary --target windows-x64 --binary ./mpm-windows-x64.exe

Options:
  --target [linux-arm64|linux-x64|macos-arm64|macos-x64|windows-arm64|windows-x64]
                 Target platform.  [required]
  --binary FILE  Path to the binary file to verify.  [required]
  -h, --help     Show this message and exit.
```

## `repomatic version-check`

```text
Usage: repomatic version-check [OPTIONS]

  Check if a version bump is allowed for the specified part.

  Compares the current version from pyproject.toml against the latest Git tag to
  detect if a bump has already been applied but not released. Prints "true" if
  allowed, "false" otherwise.

  Examples:
      repomatic version-check --part minor
      repomatic version-check --part major

Options:
  --part [minor|major]  The version part to check for bump eligibility.
                        [required]
  -h, --help            Show this message and exit.
```

## `repomatic workflow`

```text
Usage: repomatic workflow [OPTIONS] COMMAND [ARGS]...

  Lint downstream workflow caller files.

  Check thin caller workflows that delegate to the canonical reusable workflows
  in kdeldycke/repomatic. Use repomatic init workflows to generate or sync
  workflow files.

Options:
  -h, --help  Show this message and exit.

Commands:
  help  Show help for a command.
  lint  Lint workflow files for common issues
```

### `repomatic workflow help`

```text
Usage: repomatic workflow help [OPTIONS]
                               [COMMAND_PATH]...

  Show help for a command.

Options:
  --search TEXT  Search all subcommands for matching options or descriptions.
  -h, --help     Show this message and exit.
```

### `repomatic workflow lint`

```text
Usage: repomatic workflow lint [OPTIONS]

  Lint workflow files for common issues.

  Checks all YAML files in the workflow directory for:

  - Missing workflow_dispatch trigger.
  - Thin callers using @main instead of a version tag.
  - Thin callers with mismatched triggers vs canonical workflows.
  - Thin callers missing secrets: inherit when required.

  Examples:
      # Lint workflows in default location
      repomatic workflow lint

      # Lint with fatal mode (exit 1 on issues)
      repomatic workflow lint --fatal

      # Lint a custom directory
      repomatic workflow lint --workflow-dir ./my-workflows

Options:
  --workflow-dir DIRECTORY  Directory containing workflow YAML files.  [default:
                            .github/workflows]
  --repo TEXT               Upstream repository to match thin callers against.
                            [default: kdeldycke/repomatic]
  --fatal / --warning       Exit with code 1 if issues are found (default:
                            warning only).  [default: warning]
  -h, --help                Show this message and exit.
```

<!-- cli-reference-end -->
