---
name: repokit-sync
description: Sync workflow caller files with upstream reusable workflows.
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob
argument-hint: '[args]'
---

## Context

!`ls .github/workflows/*.yaml 2>/dev/null`
!`grep -h 'uses:.*kdeldycke/repokit' .github/workflows/*.yaml 2>/dev/null | head -10`
!`[ -f repokit/__init__.py ] && echo "CANONICAL_REPO" || echo "DOWNSTREAM"`

## Instructions

You help users synchronize their workflow caller files with upstream reusable workflows from `kdeldycke/repokit`.

### Determine invocation method

- If the context above shows `CANONICAL_REPO`, use `uv run repokit`.
- Otherwise, use `uvx -- repokit`.

### Argument handling

- Pass `$ARGUMENTS` through to `<cmd> workflow sync $ARGUMENTS`.
- If `$ARGUMENTS` is empty, run `<cmd> workflow sync` with no extra arguments.

### After running

- Show the diff of changed files.
- Warn about any breaking changes (removed inputs, renamed jobs, changed defaults).
- Suggest running `/repokit-lint workflows` to validate the synced files.
