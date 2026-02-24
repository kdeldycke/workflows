---
name: repokit-metadata
description: Extract and explain project metadata from Git, GitHub, and pyproject.toml.
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob
argument-hint: '[args]'
---

## Context

!`grep -m1 'name' pyproject.toml 2>/dev/null`
!`[ -f repokit/__init__.py ] && echo "CANONICAL_REPO" || echo "DOWNSTREAM"`

## Instructions

You help users extract and understand their project metadata.

### Determine invocation method

- If the context above shows `CANONICAL_REPO`, use `uv run repokit`.
- Otherwise, use `uvx -- repokit`.

### Argument handling

- Run `<cmd> metadata --format json $ARGUMENTS`.
- If `$ARGUMENTS` is empty, run with no extra arguments.

### After running

- Parse the JSON output and explain each field group (project identity, versioning, Git state, GitHub context).
- Highlight anything notable: version drift between sources, missing fields, unexpected values, bot commits in recent history.
- If running in a GitHub Actions context, explain which outputs are available for use in workflow steps.
