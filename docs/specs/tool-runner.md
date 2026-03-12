# Spec: `repomatic run` — unified tool runner

## Problem

Repomatic workflows invoke ~15 external tools. Each tool has its own config format, CLI flags, and discovery rules. This creates three pain points:

1. **Scattered config.** Tool settings live in 8+ files (`zizmor.yaml`, `lychee.toml`, `.github/actionlint.yaml`, `biome.json`, inline workflow flags, etc.) instead of one `pyproject.toml`.

2. **No defaults for downstream repos.** Repomatic bundles sensible defaults in `data/` but they are only used during `repomatic init` to seed files. If a downstream repo skips init for a tool, the workflow runs that tool with no config at all — or with hardcoded inline flags that can't be customized.

3. **Tools that reject `pyproject.toml`.** Six tools (lychee, zizmor, taplo, actionlint, biome, shfmt) lack native `pyproject.toml` support. Their maintainers range from "actively discussing" to "explicitly declined." Repomatic can bridge this gap by reading `[tool.X]` and translating to whatever the tool accepts.

## Design

### Core concept: `repomatic run <tool> [-- extra-args...]`

A single CLI command that:

1. **Installs the tool** at the version pinned in the `ToolSpec` registry.
2. **Resolves config** for the tool using a strict precedence chain.
3. **Translates config** into the tool's native format (temp config file or CLI flags).
4. **Invokes the tool** with the resolved config, passing through any extra args.
5. **Cleans up** any temp files on exit.

### Config resolution precedence

For each tool, config is resolved in this order (first match wins, no merging between levels):

1. **Native config file** — if the tool's own config file exists in the repo (e.g., `zizmor.yaml`, `lychee.toml`, `.taplo.toml`), use it as-is. The tool is invoked naked — repomatic adds no flags, no defaults, no overrides. The user owns the config completely.

2. **`[tool.X]` in `pyproject.toml`** — if the user has written a `[tool.X]` section (e.g., `[tool.zizmor]`, `[tool.lychee]`), repomatic translates it to the tool's native format. For tools that accept a config file, this means writing a temp file and passing `--config <tempfile>`. For tools that only accept CLI flags, this means generating the equivalent flags.

3. **Repomatic bundled defaults** — if neither of the above exists, repomatic uses its own bundled default config from `data/`. This provides a zero-config experience for downstream repos.

4. **Bare invocation** — if the tool has no bundled default either (e.g., actionlint, autopep8), invoke it with no config at all.

### What "naked invocation" means

When a native config file exists (precedence level 1), repomatic's role is reduced to:

- Installing the tool at the pinned version.
- Passing through any extra args from `-- extra-args...`.
- Adding CI output format flags (e.g., `--format github`) when `$GITHUB_ACTIONS` is set.

Repomatic does **not** inject additional defaults, merge configs, or override the user's file. This matches the convention established by ruff, uv, and typos: dedicated config file wins, period.

### Translation is generic dict serialization

The key simplification: since `[tool.X]` keys mirror the tool's native config keys 1:1, translation is just **format conversion** — read a Python dict from TOML, serialize it to the target format. No per-tool key mapping needed.

Three generic serializers cover all tools:

- **`dict_to_yaml(data) -> str`** — `yaml.safe_dump(data)`. Covers yamllint, zizmor, actionlint.
- **`dict_to_toml(data) -> str`** — `tomli_w.dumps(data)` (new dependency) or manual TOML generation for the simple subset used by these tools. Covers lychee, taplo, mdformat.
- **`dict_to_json(data) -> str`** — `json.dumps(data, indent=2)`. Covers biome.

Per-tool adapters are only needed for the **CLI-flags** format (shfmt, autopep8, pyproject-fmt), where key-to-flag mapping is inherently tool-specific. These are the minority case and can be deferred to phase 2.

### Bundled defaults stored in native format

Bundled defaults in `data/` are stored in the tool's **native config format** (e.g., `data/yamllint.yaml`, `data/lychee.toml`), not as TOML fragments that need translation. When a bundled default is used (precedence level 3), repomatic passes it directly to the tool via `--config <path>` — no serialization or temp file needed. Translation only happens for the `[tool.X]` path (level 2).

This means the common case (downstream repo, no custom config) is the cheapest code path: just point the tool at the bundled file.

### Temp file management

When repomatic translates `[tool.X]` to a temp config file (level 2 only), it creates a `NamedTemporaryFile(delete=False)` and cleans it up in a `try/finally` block — ensuring cleanup whether the tool succeeds, fails, or is interrupted. The temp file path is returned from `resolve_config()` alongside the CLI args, and the caller (`run_tool()`) is responsible for cleanup.

No artifacts left on disk. `repomatic --verbosity DEBUG run <tool>` logs the generated config content for debugging.

### Tool installation

`repomatic run` handles tool installation as part of invocation. The `ToolSpec` specifies how:

- **`uvx`** — for PyPI-distributed tools (the common case). Repomatic runs `uvx --no-progress '<package>==<version>' <args>`. No separate install step.
- **`uv-run`** — for tools that need the project's virtual environment (mypy, pytest). Repomatic runs `uv --no-progress run --frozen --with '<package>==<version>' -- <tool> <args>`.
- **`binary`** — for tools distributed as platform binaries (actionlint, biome, typos). Repomatic downloads to a temp directory, verifies SHA-256, and runs the binary. Download URLs and checksums are per-platform fields in `ToolSpec`.

Phase 1 implements `uvx` and `uv-run` only. Binary installs (phase 2) can coexist with the existing curl-based workflow steps in the meantime.

### Tool registry

Simplified `ToolSpec` with fields derived from behavior rather than declared redundantly:

```python
@dataclass(frozen=True)
class ToolSpec:
    """Specification for an external tool managed by repomatic."""

    name: str
    """CLI name: ``repomatic run <name>``."""

    version: str
    """Pinned version (e.g., ``'1.23.0'``)."""

    package: str
    """PyPI package name (e.g., ``'zizmor'``). May differ from ``name``."""

    executable: str | None = None
    """Executable name if different from ``name``. None defaults to ``name``."""

    native_config_files: tuple[str, ...] = ()
    """Config filenames the tool auto-discovers, checked in order. Paths relative to repo root (e.g., ``'zizmor.yaml'``, ``'.github/actionlint.yaml'``). Empty for tools with no config file."""

    config_flag: str | None = None
    """CLI flag to pass a config file path (e.g., ``'--config'``, ``'--config-file'``). None if the tool only reads from fixed paths."""

    native_format: str = "yaml"
    """Target format for ``[tool.X]`` translation: ``'yaml'``, ``'toml'``, ``'json'``, ``'jsonc'``, ``'cli-flags'``."""

    default_config: str | None = None
    """Filename in ``repomatic/data/`` for bundled defaults, stored in ``native_format``. None if no bundled default exists."""

    reads_pyproject: bool = False
    """Whether the tool natively reads ``[tool.X]`` from pyproject.toml. When True, repomatic skips config resolution entirely — the tool handles its own config."""

    default_flags: tuple[str, ...] = ()
    """Flags always passed to the tool (e.g., ``('--strict',)`` for yamllint, ``('--offline',)`` for zizmor). These encode the tool's expected behavior — strict linting, offline determinism — so callers don't have to remember them."""

    ci_flags: tuple[str, ...] = ()
    """Flags added only when ``$GITHUB_ACTIONS`` is set (e.g., ``('--format', 'github')`` for annotation output)."""

    with_packages: tuple[str, ...] = ()
    """Extra packages installed alongside the tool (e.g., mdformat plugins). Passed as ``--with <pkg>`` to uvx."""

    needs_venv: bool = False
    """If True, use ``uv run`` (project venv) instead of ``uvx`` (isolated). Required when the tool imports project code (mypy, pytest)."""

    computed_params: str | None = None
    """Name of a ``Metadata`` property that returns extra CLI args for this tool (e.g., ``'mypy_params'``). None if no computed params."""
```

Notable simplifications vs. the previous draft:

- **No `pyproject_section` / `repomatic_section` split.** Both are just `tool.{name}`. The `reads_pyproject` bool tells repomatic whether to translate or leave it alone.
- **No `install_method` enum.** Derived from `needs_venv` (True → `uv run`, False → `uvx`). Binary installs are a future extension.
- **`computed_params` is a string reference** to a Metadata property, not a callback. Avoids import cycles and keeps ToolSpec serializable.
- **`with_packages`** handles the mdformat plugin problem natively.

### Which tools need translation?

| Tool | `reads_pyproject` | `native_config_files` | `native_format` | `config_flag` |
|---|---|---|---|---|
| mypy | True | `mypy.ini` | — | — |
| ruff | True | `ruff.toml`, `.ruff.toml` | — | — |
| typos | True | `typos.toml`, `.typos.toml` | — | — |
| pytest | True | `pytest.ini` | — | — |
| yamllint | False | `.yamllint.yaml`, `.yamllint.yml` | yaml | `--config-file` |
| zizmor | False | `zizmor.yaml` | yaml | `--config` |
| actionlint | False | `.github/actionlint.yaml` | yaml | `-config-file` |
| lychee | False | `lychee.toml`, `.lycheerc` | toml | `--config` |
| biome | False | `biome.json`, `biome.jsonc` | json | `--config-path` |
| taplo | False | `.taplo.toml`, `taplo.toml` | toml | `--config` |
| shfmt | False | — | cli-flags | — |
| autopep8 | False | — | cli-flags | — |
| pyproject-fmt | False | — | cli-flags | — |
| mdformat | False | `.mdformat.toml` | toml | — |

### Config resolution logic

See `repomatic/tool_runner.py` for the actual implementation. `resolve_config()` returns `(extra_cli_args, temp_file_path)` — the temp file path allows the caller to clean up after invocation. A `["__bundled__"]` sentinel in the args signals that the bundled default should be resolved at invocation time via `get_data_file_path()` context manager (because `importlib.resources.as_file()` needs an active context).

### Bundled defaults lifecycle

Today, `data/*.toml` files are only used during `repomatic init` to seed `pyproject.toml` sections. With `repomatic run`, data files gain a second role: **runtime fallback configs**.

For tools that `reads_pyproject` (ruff, mypy, pytest, typos), the bundled default is still only used by `init`. No change.

For tools that don't read `pyproject.toml`, new bundled defaults in native format are needed:

- `data/yamllint.yaml` — replaces the inline `--config-data` in the workflow.
- `data/actionlint.yaml` — minimal config (may be empty initially).
- `data/lychee.toml` — default lychee config.
- etc.

### Workflow integration

Before (zizmor — 5 lines, conditional init + separate invocation):

```yaml
- name: Generate zizmor config if missing
  if: hashFiles('zizmor.yaml') == ''
  run: uvx --no-progress --from . repomatic init zizmor
- name: Run zizmor
  run: uvx --no-progress 'zizmor==1.23.0' --format github --offline .
```

After (1 line — `--offline` is a `default_flags` so it's automatic):

```yaml
- name: Run zizmor
  run: uvx --no-progress --from . repomatic run zizmor -- .
```

Before (yamllint — inline config baked into YAML):

```yaml
- name: Run yamllint
  run: >
    uvx --no-progress 'yamllint==1.38.0'
    --strict --format github
    --config-data "{rules: {line-length: {max: 120}}}" .
```

After (`--strict` is a `default_flags` so it's automatic):

```yaml
- name: Run yamllint
  run: uvx --no-progress --from . repomatic run yamllint -- .
```

Before (actionlint — 15+ lines for install + checksums + matcher + run):

```yaml
- name: Install actionlint and shellcheck
  run: |
    curl -fsSL --output /tmp/actionlint.tar.gz \
      "https://github.com/rhysd/actionlint/.../actionlint_1.7.11_linux_amd64.tar.gz"
    echo "900919a8...  /tmp/actionlint.tar.gz" | sha256sum --check
    tar xzf /tmp/actionlint.tar.gz -C /usr/local/bin actionlint
    sudo apt update && sudo apt install --yes shellcheck
- name: Setup problem matcher
  run: |
    curl -fsSL --output ./.github/actionlint-matcher.json \
      https://raw.githubusercontent.com/.../actionlint-matcher.json
    echo "::add-matcher::.github/actionlint-matcher.json"
- name: Run actionlint
  run: >
    actionlint -color
    -ignore 'property "workflow_update_github_pat" is not defined in .+'
```

After (phase 2 with binary support):

```yaml
- name: Install shellcheck
  run: sudo apt install --yes shellcheck
- name: Run actionlint
  run: >
    uvx --no-progress --from . repomatic run actionlint
    -- -ignore 'property "workflow_update_github_pat" is not defined in .+'
```

System dependencies (shellcheck) remain as separate workflow steps — repomatic manages tool binaries, not OS packages.

### `repomatic run --list`

```
$ repomatic run --list
Tool           Version   Config source
─────────────  ────────  ─────────────────────────
actionlint     1.7.11    (bare)
biome          2.4.5     (bare)
lychee         0.23.0    lychee.toml
mypy           1.19.1    [tool.mypy] in pyproject.toml
ruff           0.15.5    [tool.ruff] in pyproject.toml
yamllint       1.38.0    bundled default
zizmor         1.23.0    [tool.zizmor] in pyproject.toml
```

Shows the resolved config source for each tool in the current repo. Useful for debugging which precedence level is active.

### Version pinning

Tool versions move from workflow YAML to the `ToolSpec` registry. Benefits:

- Single source of truth, testable and auditable.
- Renovate updates via `customManagers` regex on Python string literals.
- Downstream repos get bumps automatically when upgrading repomatic.

### Computed parameters

The existing `mypy_params` metadata property computes `--python-version X.Y` from `requires-python`. This is a **computed parameter** — derived from project metadata, orthogonal to config resolution.

`ToolSpec.computed_params` references a `Metadata` property by name. When present, `repomatic run` instantiates `Metadata`, reads the property, and appends the result to the tool's CLI args. This avoids import cycles (ToolSpec doesn't import Metadata) and keeps the registry declarative.

Other tools may gain computed parameters over time (e.g., ruff's `target-version` from `requires-python`).

### Pass-through args

`repomatic run <tool> -- <extra-args>` passes everything after `--` directly to the tool. The `--` separator is mandatory to avoid ambiguity with repomatic's own flags.

### Exit codes

`repomatic run` forwards the tool's exit code unchanged via `sys.exit()`. This is critical for lint jobs where non-zero means "findings detected."

### `[tool.X]` namespace and forward compatibility

Config lives directly under `[tool.X]` (e.g., `[tool.zizmor]`). If a tool later adds native `pyproject.toml` support, the section stays in place — just flip `reads_pyproject = True` in the `ToolSpec` and repomatic stops translating.

### Interaction with `exclude`

`exclude` controls `init` and `sync` only. `repomatic run <tool>` runs regardless. Users can exclude a tool from init (they manage config manually) while still using `repomatic run` for version pinning and CI flags.

## Non-goals

- **Config merging.** No merging between precedence levels. First match wins.

- **Inventing new config schemas.** `[tool.X]` mirrors the tool's native keys 1:1. Repomatic translates format, not semantics.

- **OS package management.** System dependencies (shellcheck, shfmt via apt) stay as separate workflow steps.

## Dependency impact

- **PyYAML** — already a runtime dependency. Used for YAML serialization.
- **`tomli-w`** — new runtime dependency for TOML serialization (writing `[tool.X]` → temp `.toml` files for lychee, taplo, mdformat). Lightweight, maintained by the same team as `tomli`. Alternative: manual TOML generation for the simple flat-dict subset, avoiding the dependency.
- **`json`** — stdlib, no new dependency.

## Phased rollout

### Phase 1: Framework + YAML tools

**Implemented.** See `repomatic/tool_runner.py`, CLI command in `cli.py`, tests in `tests/test_tool_runner.py`.

- `ToolSpec` dataclass and registry with yamllint, zizmor entries.
- `repomatic run` CLI command with `--list` and pass-through args via `--`.
- Config resolution (4-level precedence) with `resolve_config()`.
- Temp file cleanup in `try/finally` with debug logging.
- YAML serialization (`yaml.safe_dump`).
- `uvx` and `uv-run` installation via `_build_install_args()`.
- Bundled default: `data/yamllint.yaml`.
- `yamllint` init component (user-owned, excluded by default).
- Workflow migration: yamllint and zizmor steps in `lint.yaml` use `repomatic run`.
- `resolve_config_source()` for `--list` diagnostics.

### Phase 2: Remaining formats + binary installs

- TOML serialization (lychee, taplo, mdformat).
- JSON serialization (biome).
- CLI-flags adapters (shfmt, autopep8, pyproject-fmt) — these are the only per-tool code, kept minimal.
- Binary download + SHA-256 verification for actionlint, biome, typos.
- ToolSpec entries for all remaining tools.
- Bundled defaults for newly supported tools.

### Phase 3: Full workflow migration

- Migrate all tool invocations in all workflows to `repomatic run`.
- Remove version strings, install steps, and inline configs from workflow YAML.
- Update Renovate `customManagers` to target the Python registry.

### Phase 4: Computed parameters generalization

- Wire `computed_params` into `repomatic run`.
- Add computed params for ruff (`target-version`), others as needed.
- Deprecate `mypy_params` metadata property.
