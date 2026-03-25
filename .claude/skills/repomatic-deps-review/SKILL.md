---
name: repomatic-deps-review
description: Review pyproject.toml dependency declarations for version policy, comments, ordering, and best practices.
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob, Agent
argument-hint: '[all|runtime|dev|policy]'
---

## Context

!`cat pyproject.toml 2>/dev/null | head -5 || echo "No pyproject.toml found"`
!`grep -c '".*>=\|".*~=\|".*<\|".*==' pyproject.toml 2>/dev/null || echo "0"`
!`[ -f repomatic/__init__.py ] && echo "CANONICAL_REPO" || echo "DOWNSTREAM"`

## Instructions

You review `pyproject.toml` dependency declarations against the version policy established across all `kdeldycke/*` repositories. This is purely analytical work with no mechanical equivalent in CI.

### Scope selection

- `all` (default when `$ARGUMENTS` is empty): Run all checks below.
- `runtime`: Review `[project].dependencies` only.
- `dev`: Review `[dependency-groups]` and `[project.optional-dependencies]` only.
- `policy`: Print the policy summary without auditing.

### Version specifier policy

These conventions are derived from the `pyproject.toml` files across all `kdeldycke/*` repositories.

#### Runtime dependencies (`[project].dependencies`)

1. **Use `>=` (not `~=` or `==`).** Relaxed lower bounds give packagers freedom to release security hotfixes without waiting for an upstream bump. Upper bounds are forbidden per <https://iscinumpy.dev/post/bound-version-constraints/>.
2. **Every version bound needs a comment tying the floor to a concrete code dependency.** The comment goes on the line above the dependency and states which feature, method, or API from that version the project actually uses. Prefer referencing the call site or module that depends on it:
   ```toml
   # wcmatch 10.0 changed globbing semantics; our sync_gitignore() relies on
   # the new symlink-aware matching behavior.
   "wcmatch>=10",
   ```
   A good floor comment answers: "if someone installed an older version, what would break and where?" If you cannot point to a concrete usage, the floor may be unnecessarily high.
3. **Python version support is not a valid reason to bump a floor.** The dependency resolver already picks the right version via `requires-python` metadata. If `boltons>=20` works and boltons 25 merely adds Python 3.13 support, keep `>=20` — the resolver handles it. **Exception:** when a dependency *drops* a Python version your project still supports (or your project drops one, aligning minimum `requires-python`), that alignment is a valid floor bump reason. The comment should state the version range alignment, not the Python support:
   ```toml
   # boltons 25.0.0 dropped Python 3.9, matching our requires-python >= 3.10.
   "boltons>=25",
   ```
4. **Use conditional markers for Python-version-gated deps.** Example: `"tomli>=2.3; python_version<'3.11'"`.
5. **Alphabetical order** within the list.

#### Development dependencies (`[dependency-groups]`)

6. **Prefer `[dependency-groups]`** (uv standard) over `[project.optional-dependencies]` for test, typing, and docs groups.
7. **`>=` is preferred for dev deps too**, but `~=` is acceptable when stricter pinning reduces CI randomness. If a package also appears in runtime deps, the dev entry must use the same specifier style.
8. **Standard group names:** `test`, `typing`, `docs` (lowercase, alphabetical).
9. **Type stubs** go in the `typing` group with stub-specific versions: `"types-boltons>=25.0.0.20250822"`.
10. **Alphabetical order** within each group.

#### General rules

11. **No upper bounds** (`<`, `<=`, `!=`, `~=` that implies an upper bound). The only exception is conditional markers like `python_version<'3.11'`.
12. **Extras syntax** is fine: `"coverage[toml]>=7.11"`.
13. **One dependency per line** for readable diffs.

### Audit procedure

Read the full `pyproject.toml`. For each dependency entry, check:

| Check | What to flag |
|---|---|
| Specifier style | `~=`, `==`, or upper bounds on runtime deps |
| Missing comment | No comment above the entry explaining the version floor |
| Weak comment | Comment cites Python version support instead of a concrete code dependency. Flag unless it documents a `requires-python` alignment or a Python version drop |
| Stale comment | Comment references a reason that no longer applies (e.g., the cited method was replaced, or the Python version was dropped from the support matrix) |
| Ordering | Dependencies not in alphabetical order |
| Group placement | Type stubs outside `typing` group, test deps outside `test` group |
| Section style | `[project.optional-dependencies]` used where `[dependency-groups]` would be appropriate |
| Bare dependency | No version specifier at all (e.g., `"requests"`) |
| Conditional markers | Missing Python version marker for backport packages |

### Cross-repo reference

When the context shows `DOWNSTREAM`, also compare the dependency list against the canonical `repomatic` `pyproject.toml` (fetch with `gh api repos/kdeldycke/repomatic/contents/pyproject.toml --jq '.content' | base64 -d`) to identify:

- Shared dependencies where the downstream floor is lower than upstream (may be missing a needed bump).
- Shared dev dependencies where upstream has moved to a newer group structure.

### Output format

Produce:

1. **Policy compliance summary**: A table with one row per dependency: name, specifier, has comment (yes/no), issues found.
2. **Grouped findings** by severity:
   - **Errors**: Wrong specifier style, missing version, upper bounds.
   - **Warnings**: Missing or stale comments, ordering issues.
   - **Info**: Suggestions for tighter floors based on cross-repo data.
3. **Suggested fixes**: For each error/warning, show the current line and the recommended replacement.

### Next steps

Suggest the user run:

- `/repomatic-deps` to visualize the resolved dependency graph.
- `/repomatic-lint` to check repository metadata for other issues.
- `/repomatic-audit` for a comprehensive alignment check beyond dependencies.
