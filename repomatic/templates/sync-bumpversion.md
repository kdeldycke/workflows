---
title: Sync `bump-my-version` config
footer: false
---

### Description

Initializes the `[tool.bumpversion]` configuration in `pyproject.toml` from the bundled template. See the [`sync-bumpversion` job documentation](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#githubworkflowsautofixyaml-jobs) for details.

### Configuration

```toml
[tool.repomatic]
bumpversion.sync = true # Set to false to disable (default: true)
```
