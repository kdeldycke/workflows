---
title: Format Python
footer: false
---

### Description

Auto-formats Python files with [autopep8](https://github.com/hhatto/autopep8) (comment wrapping) and [Ruff](https://docs.astral.sh/ruff/) (linting and formatting). When no `[tool.ruff]` section or `ruff.toml` is present, [repomatic's bundled defaults](https://github.com/kdeldycke/repomatic/blob/main/repomatic/data/ruff.toml) are applied at runtime. See the [`format-python` job documentation](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#githubworkflowsautofixyaml-jobs) for details.

> [!TIP]
> Customize formatting and linting rules via [`[tool.ruff]`](https://docs.astral.sh/ruff/configuration/) and [`[tool.autopep8]`](https://github.com/hhatto/autopep8#configuration) in your `pyproject.toml`.
