---
name: repokit-init
description: Bootstrap a repository with reusable workflows from kdeldycke/repokit.
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob
argument-hint: '[component ...]'
---

## Context

!`[ -f pyproject.toml ] && echo "pyproject.toml exists" || echo "No pyproject.toml"`
!`ls .github/workflows/ 2>/dev/null || echo "No .github/workflows/ directory"`
!`[ -f repokit/__init__.py ] && echo "CANONICAL_REPO" || echo "DOWNSTREAM"`

## Instructions

You help users bootstrap a repository to use the reusable GitHub Actions workflows from `kdeldycke/repokit`.

### Determine invocation method

- If the context above shows `CANONICAL_REPO`, use `uv run repokit init`.
- Otherwise, use `uvx -- repokit init`.

### Argument handling

- If `$ARGUMENTS` is empty, first analyze the project (check `pyproject.toml`, existing workflows, project language) and recommend which components to initialize. Then ask the user to confirm before running.
- If `$ARGUMENTS` is provided, pass it through: `<cmd> init $ARGUMENTS`.

### After running

- Show the generated files and explain what each workflow does.
- Highlight required next steps: GitHub PAT setup for workflows that need it, GitHub Pages configuration for docs workflows, and any `pyproject.toml` `[tool.repokit]` configuration options.
- If existing workflow files were detected, warn about potential conflicts.
