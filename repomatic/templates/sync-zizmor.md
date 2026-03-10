---
title: Sync zizmor config
footer: false
---

### Description

Syncs `zizmor.yaml` with the canonical reference from [`kdeldycke/repomatic`](https://github.com/kdeldycke/repomatic/blob/main/repomatic/data/zizmor.yaml). See the [`sync-zizmor` job documentation](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#githubworkflowsautofixyaml-jobs) for details.

### Configuration

```toml
[tool.repomatic]
zizmor.sync = true # Set to false to disable (default: true)
```
