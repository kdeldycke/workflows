---
name: gha-changelog
description: Draft, validate, and fix changelog entries.
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob, Edit, Write
argument-hint: '[add|check|fix]'
---

## Context

!`head -40 changelog.md 2>/dev/null || echo "No changelog.md found"`
!`git log --oneline -10 2>/dev/null`
!`[ -f gha_utils/__init__.py ] && echo "CANONICAL_REPO" || echo "DOWNSTREAM"`

## Instructions

You help users manage their `changelog.md` file. Follow `CLAUDE.md` § Changelog and readme updates for style rules.

### Determine invocation method

- If the context above shows `CANONICAL_REPO`, use `uv run gha-utils`.
- Otherwise, use `uvx -- gha-utils`.

### Argument handling

- `add` (default when `$ARGUMENTS` is empty): Review recent git commits and draft changelog entries. Place entries under the current unreleased section. Describe **what** changed, not **why**. Keep entries concise and actionable.
- `check`: Run `<cmd> lint-changelog` and report results. Explain each issue found.
- `fix`: Run `<cmd> lint-changelog --fix` and show what was changed.

### Style rules

- Entries describe **what** changed (new features, bug fixes, behavior changes), not **why**.
- Justifications belong in documentation or code comments, not the changelog.
- Follow the version formatting rules from `CLAUDE.md` § Version formatting: bare versions in changelog headings (`` `1.2.3` ``), no `v` prefix.
