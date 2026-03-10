---
title: Sync `.mailmap`
footer: false
---

### Description

Synchronizes the `.mailmap` file with the project's Git contributors. See the [`sync-mailmap` job documentation](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#githubworkflowsautofixyaml-jobs) for details.

### Configuration

```toml
[tool.repomatic]
mailmap.sync = true # Set to false to disable (default: true)
```
