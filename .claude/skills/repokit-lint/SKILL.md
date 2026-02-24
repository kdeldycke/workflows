---
name: repokit-lint
description: Lint workflows and repository metadata.
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob
argument-hint: '[workflows|repo|all]'
---

## Context

!`ls .github/workflows/*.yaml 2>/dev/null`
!`[ -f repokit/__init__.py ] && echo "CANONICAL_REPO" || echo "DOWNSTREAM"`

## Instructions

You help users lint their workflows and repository metadata for common issues.

### Determine invocation method

- If the context above shows `CANONICAL_REPO`, use `uv run repokit`.
- Otherwise, use `uvx -- repokit`.

### Argument handling

- `all` (default when `$ARGUMENTS` is empty): Run both workflow and repo linting.
- `workflows`: Run `<cmd> workflow lint` only.
- `repo`: Run `<cmd> lint-repo` only.

### After running

- Explain each issue found: what the problem is, why it matters, and how to fix it.
- Group issues by severity (errors first, then warnings).
- For workflow issues, reference the specific file and line where possible.
