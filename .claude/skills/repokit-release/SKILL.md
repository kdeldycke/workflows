---
name: repokit-release
description: Pre-checks, release preparation, and post-release steps.
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob
argument-hint: '[check|prep|post-release]'
---

## Context

!`grep -m1 'version' pyproject.toml 2>/dev/null`
!`head -5 changelog.md 2>/dev/null`
!`git tag --sort=-v:refname | head -5 2>/dev/null`
!`git status --short 2>/dev/null`
!`[ -f repokit/__init__.py ] && echo "CANONICAL_REPO" || echo "DOWNSTREAM"`

## Instructions

You help users prepare and validate releases. Reference `CLAUDE.md` § Release checklist for completeness criteria.

### Determine invocation method

- If the context above shows `CANONICAL_REPO`, use `uv run repokit`.
- Otherwise, use `uvx -- repokit`.

### Argument handling

- `check` (default when `$ARGUMENTS` is empty): Run pre-flight validation. Check that the working tree is clean, changelog has unreleased entries, version is consistent across files, and lint-changelog passes. Report any blockers.
- `prep`: Run `<cmd> release-prep` and show the resulting diff. Explain the freeze/unfreeze commit structure (see `CLAUDE.md` § Release PR: freeze and unfreeze commits). Remind that the release PR must use "Rebase and merge", never squash.
- `post-release`: Run `<cmd> release-prep --post-release` and show results.

### After running

- Cross-check against `CLAUDE.md` § Release checklist: git tag, GitHub release, binaries, PyPI package, changelog entry.
- Warn about any incomplete items.
- Explain the version formatting rules: bare versions for package references, `v`-prefixed for tag references (see `CLAUDE.md` § Version formatting).
