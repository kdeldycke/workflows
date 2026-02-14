---
title: "[autofix] Format Python"
---
### Description

Auto-formats Python files with [autopep8](https://github.com/hhatto/autopep8) (comment wrapping) and [Ruff](https://docs.astral.sh/ruff/) (linting and formatting). A `[tool.ruff]` section is auto-initialized in `pyproject.toml` if missing. See the [`format-python` job documentation](https://github.com/kdeldycke/workflows?tab=readme-ov-file#githubworkflowsautofixyaml-jobs) for details.