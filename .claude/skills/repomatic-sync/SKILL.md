---
name: repomatic-sync
description: Sync workflow caller files with upstream reusable workflows, then analyze what the mechanical sync cannot cover.
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob
argument-hint: '[args]'
---

## Context

!`ls .github/workflows/*.yaml 2>/dev/null`
!`grep -h 'uses:.*kdeldycke/repomatic' .github/workflows/*.yaml 2>/dev/null | head -10`
!`grep -A5 '\[tool.repomatic\]' pyproject.toml 2>/dev/null || echo "No [tool.repomatic] section"`
!`[ -f repomatic/__init__.py ] && echo "CANONICAL_REPO" || echo "DOWNSTREAM"`

## Instructions

You help users synchronize their workflow caller files with upstream reusable workflows from `kdeldycke/repomatic`.

### Mechanical layer

The `autofix.yaml` workflow's `sync-workflows` job already runs `repomatic workflow sync` automatically on every push to `main`. This skill is useful when you want to run the sync **interactively** (e.g., before pushing, or to preview changes).

### Determine invocation method

- If the context above shows `CANONICAL_REPO`, use `uv run repomatic`.
- Otherwise, use `uvx -- repomatic`.

### Argument handling

- Pass `$ARGUMENTS` through to `<cmd> workflow sync $ARGUMENTS`.
- If `$ARGUMENTS` is empty, run `<cmd> workflow sync` with no extra arguments.

### After running — analytical layer

The mechanical sync only covers thin-caller workflows and header-only workflow headers. After running, provide the analysis that the CLI cannot:

1. Show the diff of changed files.
2. Warn about any breaking changes (removed inputs, renamed jobs, changed defaults).
3. **Check header-only workflow job content** (e.g., `tests.yaml`) for stale action versions, missing workarounds, or outdated patterns compared to the upstream reference. The sync tool does not touch this content.
4. Report any files excluded via `workflow-sync-exclude` in `[tool.repomatic]`.

### Next steps

Suggest the user run:

- `/repomatic-audit workflows` for a deeper analysis of header-only workflow drift.
- `/repomatic-lint workflows` to validate the synced workflow files.
