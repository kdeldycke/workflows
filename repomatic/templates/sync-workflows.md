---
title: Sync workflow files
footer: false
---

### Description

Syncs [thin-caller workflow files](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#example-usage) from the upstream [`kdeldycke/repomatic`](https://github.com/kdeldycke/repomatic) repository. See the [`sync-workflows` job documentation](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#githubworkflowsautofixyaml-jobs) for details.

### Configuration

```toml
[tool.repomatic]
workflow.sync = true                    # Set to false to disable (default: true)
workflow.sync-exclude = ["debug.yaml"]  # Workflow files to skip
workflow.source-paths = ["src", "lib"]  # Source dirs for paths: filters (default: auto-derived)
```
