---
title: Sync `bump-my-version` config
footer: false
---

### Description

Initializes the `[tool.bumpversion]` configuration in `pyproject.toml` from the [bundled template](https://github.com/kdeldycke/repomatic/blob/main/repomatic/data/bumpversion.toml). See the [`sync-bumpversion` job documentation](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#githubworkflowsautofixyaml-jobs) for details.

### Configuration

Relevant [`[tool.repomatic]`](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#toolrepomatic-configuration) options:

```toml
[tool.repomatic]
bumpversion.sync = true
```
