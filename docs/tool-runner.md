# {octicon}`tools` Tool runner

`repomatic run` is a unified entry point for running external linters, formatters, and security scanners. It installs each tool at a pinned version, resolves configuration through a strict precedence chain, and invokes the tool: no manual setup, no dotfile sprawl.

## Quick start

Run a tool against your project:

```shell-session
$ repomatic run yamllint -- .
```

The `--` separates repomatic's own options from the arguments forwarded to the tool. Everything after `--` is passed through verbatim.

List all managed tools and their resolved config source:

```shell-session
$ repomatic run --list
```

## Available tools

| Tool | Version | Type | Config discovery |
| :--- | :------ | :--- | :--------------- |
| [actionlint](https://github.com/rhysd/actionlint) | `1.7.12` | Binary | `.github/actionlint.yaml` |
| [autopep8](https://github.com/hhatto/autopep8) | `2.3.2` | PyPI | CLI flags only |
| [biome](https://biomejs.dev) | `2.4.5` | Binary | `biome.json`, `biome.jsonc` |
| [bump-my-version](https://github.com/callowayproject/bump-my-version) | `1.2.7` | PyPI | `[tool.bumpversion]` in `pyproject.toml` |
| [gitleaks](https://github.com/gitleaks/gitleaks) | `8.30.1` | Binary | `.gitleaks.toml`, `.github/gitleaks.toml` |
| [labelmaker](https://github.com/jwodder/labelmaker) | `0.6.4` | Binary | CLI flags only |
| [lychee](https://lychee.cli.rs) | `0.23.0` | Binary | `lychee.toml` |
| [mdformat](https://github.com/hukkin/mdformat) | `1.0.0` | PyPI | `.mdformat.toml`, `[tool.mdformat]` in `pyproject.toml` |
| [mypy](https://github.com/python/mypy) | `1.19.1` | PyPI (venv) | `[tool.mypy]` in `pyproject.toml` |
| [pyproject-fmt](https://github.com/tox-dev/pyproject-fmt) | `2.16.2` | PyPI | `[tool.pyproject-fmt]` in `pyproject.toml` |
| [ruff](https://github.com/astral-sh/ruff) | `0.15.5` | PyPI | `ruff.toml`, `.ruff.toml`, `[tool.ruff]` in `pyproject.toml` |
| [shfmt](https://github.com/mvdan/sh) | `3.13.1` | Binary | `.editorconfig` |
| [typos](https://github.com/crate-ci/typos) | `1.44.0` | Binary | `[tool.typos]` in `pyproject.toml` |
| [yamllint](https://github.com/adrienverge/yamllint) | `1.38.0` | PyPI | `.yamllint.yaml`, `.yamllint.yml`, `.yamllint` |
| [zizmor](https://docs.zizmor.sh) | `1.23.0` | PyPI | `zizmor.yaml` |

Tools marked "Binary" are downloaded as platform-specific executables from GitHub Releases. "PyPI" tools are installed via `uvx`. "PyPI (venv)" tools run inside the project virtualenv via `uv run` because they need to import project code.

## Config resolution

When `repomatic run <tool>` is invoked, configuration is resolved through a 4-level precedence chain. The first match wins: no merging across levels.

### Level 1: native config file

If the tool's own config file exists in the repo (like `ruff.toml` or `.yamllint.yaml`), repomatic defers to it entirely. Your repo stays in control.

```shell-session
$ ls ruff.toml
ruff.toml
$ repomatic run ruff -- check .
# Uses ruff.toml directly — repomatic does nothing special.
```

### Level 2: `[tool.X]` in `pyproject.toml`

If no native config file is found but your `pyproject.toml` has a `[tool.<name>]` section, repomatic uses it. For tools that read `pyproject.toml` natively (ruff, mypy, bump-my-version, etc.), this just works. For tools that don't, repomatic translates the section into the tool's native format and passes it via a temporary config file.

```toml
# pyproject.toml
[tool.yamllint.rules.line-length]
max = 120

[tool.yamllint.rules.truthy]
check-keys = false
```

```shell-session
$ repomatic run yamllint -- .
# Translates [tool.yamllint] to YAML, passes via --config-file.
```

The following tools support this `[tool.X]` translation:

| Tool | `[tool.X]` section | Translated to |
| :--- | :------------------ | :------------ |
| [actionlint](https://github.com/rhysd/actionlint) | `[tool.actionlint]` | YAML |
| [biome](https://biomejs.dev) | `[tool.biome]` | JSON |
| [gitleaks](https://github.com/gitleaks/gitleaks) | `[tool.gitleaks]` | TOML |
| [lychee](https://lychee.cli.rs) | `[tool.lychee]` | TOML |
| [yamllint](https://yamllint.readthedocs.io) | `[tool.yamllint]` | YAML |
| [zizmor](https://docs.zizmor.sh) | `[tool.zizmor]` | YAML |

> [!TIP]
> The workflows also invoke tools that read their own `[tool.*]` sections from your `pyproject.toml`. You can customize their behavior in your project without forking or patching the workflows:
>
> | Tool | Section | Customizes |
> | :--- | :------ | :--------- |
> | [bump-my-version](https://callowayproject.github.io/bump-my-version/) | `[tool.bumpversion]` | Version bump patterns and files |
> | [coverage.py](https://coverage.readthedocs.io/en/latest/config.html) | `[tool.coverage.*]` | Code coverage reporting |
> | [mdformat](https://mdformat.readthedocs.io/en/stable/users/configuration_file.html) | `[tool.mdformat]` | Markdown formatting options (via [`mdformat-pyproject`](https://github.com/csala/mdformat-pyproject)) |
> | [mypy](https://mypy.readthedocs.io/en/stable/config_file.html) | `[tool.mypy]` | Static type checking |
> | [pyproject-fmt](https://pyproject-fmt.readthedocs.io/en/latest/) | `[tool.pyproject-fmt]` | `pyproject.toml` formatting (column width, indent, table style) |
> | [pytest](https://docs.pytest.org/en/stable/reference/customize.html) | `[tool.pytest]` | Test runner options |
> | [ruff](https://docs.astral.sh/ruff/configuration/) | `[tool.ruff]` | Linting and formatting rules |
> | [typos](https://github.com/crate-ci/typos) | `[tool.typos]` | Spell-checking exceptions |
> | [uv](https://docs.astral.sh/uv/reference/settings/) | `[tool.uv]` | Package resolution and build config |
>
> See [click-extra's inventory of `pyproject.toml`-aware tools](https://kdeldycke.github.io/click-extra/config.html#pyproject-toml) for a broader list.

### Level 3: bundled default

If the repo has no config at all, repomatic falls back to its own bundled defaults (stored in `repomatic/data/`). These provide sensible baseline rules so that tools produce useful results even without any project-specific configuration.

Tools with bundled defaults: mdformat, ruff, yamllint, zizmor.

### Level 4: bare invocation

If none of the above applies (no config file, no `[tool.X]`, no bundled default), the tool runs with its own built-in defaults. Tools like autopep8 and pyproject-fmt work this way: all behavior is controlled through CLI flags.

### Checking the active config source

To see which precedence level is active for each tool in your repo:

```shell-session
$ repomatic run --list
```

The "Config source" column shows whether the tool is using a native config file (level 1), `[tool.X]` (level 2), a bundled default (level 3), or bare invocation (level 4).

## Tutorial: adding yamllint to your project

This walkthrough covers a common scenario: running yamllint on a project that has no YAML linting configured.

### Step 1: run with defaults

With no config file and no `[tool.yamllint]` section in `pyproject.toml`, repomatic uses its bundled default:

```shell-session
$ repomatic run yamllint -- .
```

The bundled config enforces strict YAML rules. If that produces too many warnings, customize it.

### Step 2: customize via `pyproject.toml`

Instead of creating a `.yamllint.yaml` file, add a section to your `pyproject.toml`:

```toml
[tool.yamllint.rules.line-length]
max = 120

[tool.yamllint.rules.truthy]
check-keys = false
```

Now `repomatic run yamllint -- .` translates this to YAML, passes it via `--config-file`, and cleans up the temporary file afterward.

### Step 3: graduate to a native config file

If your yamllint config grows complex, create a `.yamllint.yaml` directly. Once that file exists, repomatic defers to it (level 1 takes precedence) and the `[tool.yamllint]` section in `pyproject.toml` is ignored.

### Cleaning up redundant configs

If you previously ran `repomatic init` and have a native config file that is identical to the bundled default, `repomatic init --clean-redundant-configs` removes it:

```shell-session
$ repomatic init --clean-redundant-configs
```

## Overriding tool versions

To test a newer version of a tool before the registry is updated:

```shell-session
$ repomatic run shfmt --version 3.14.0 --skip-checksum -- .
```

`--skip-checksum` is required because the registry only stores checksums for the pinned version. For binary tools, `--checksum` lets you provide the correct SHA-256 for the new version instead of skipping verification entirely:

```shell-session
$ repomatic run shfmt --version 3.14.0 --checksum abc123... -- .
```

## Binary caching

`repomatic run` downloads platform-specific binaries (actionlint, biome, gitleaks, labelmaker, lychee, etc.) from GitHub Releases. To avoid re-downloading on every invocation, binaries are cached under a platform-appropriate user cache directory:

| Platform | Default cache path |
| :------- | :----------------- |
| Linux | `$XDG_CACHE_HOME/repomatic` or `~/.cache/repomatic` |
| macOS | `~/Library/Caches/repomatic` |
| Windows | `%LOCALAPPDATA%\repomatic\Cache` |

Cached binaries are re-verified against their registry SHA-256 checksum on every use. Entries older than 30 days are auto-purged.

Both settings are configurable via [`[tool.repomatic]`](configuration.md) (see `cache.dir` and `cache.max-age`) or environment variables. The env var takes precedence over the config.

| Environment variable | Config key | Default | Description |
| :------------------- | :--------- | :------ | :---------- |
| `REPOMATIC_CACHE_DIR` | `cache.dir` | *(platform-specific)* | Override the cache directory path. |
| `REPOMATIC_CACHE_MAX_AGE` | `cache.max-age` | `30` | Auto-purge entries older than this many days. `0` disables. |

Cache management commands:

```shell-session
$ repomatic cache show
$ repomatic cache clean
$ repomatic cache clean --tool ruff --max-age 7
$ repomatic cache path
```

Use `--no-cache` on `repomatic run` to bypass the cache entirely.

## Passing extra arguments

Everything after `--` is forwarded to the tool:

```shell-session
$ repomatic run ruff -- check --fix .
$ repomatic run zizmor -- --offline .github/workflows/
$ repomatic run biome -- format --write src/
```

For tools with subcommands (ruff, biome, gitleaks), the subcommand goes after `--` as the first argument.
