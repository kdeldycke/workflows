---
title: Sync workflow files
footer: false
---

### Description

Syncs [thin-caller workflow files](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#example-usage) from the upstream [`kdeldycke/repomatic`](https://github.com/kdeldycke/repomatic) repository. See the [`sync-workflows` job documentation](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#githubworkflowsautofixyaml-jobs) for details.

### Configuration

Relevant [`[tool.repomatic]`](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#toolrepomatic-configuration) options:

```toml
[tool.repomatic]
exclude = ["workflows/debug.yaml"]
workflow.sync = true
workflow.source-paths = ["src", "lib"]
```
