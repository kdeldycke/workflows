---
title: Sync `.mailmap`
footer: false
---

### Description

Synchronizes the `.mailmap` file with the project's Git contributors. See the [`sync-mailmap` job documentation](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#githubworkflowsautofixyaml-jobs) for details.

### Configuration

Relevant [`[tool.repomatic]`](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#toolrepomatic-configuration) options:

```toml
[tool.repomatic]
mailmap.sync = true
```
