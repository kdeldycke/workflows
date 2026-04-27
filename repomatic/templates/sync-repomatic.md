---
title: Sync repomatic-managed files
footer: false
---

### Description

Syncs all [repomatic](https://github.com/kdeldycke/repomatic)-managed files: [thin-caller workflows](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#example-usage), configuration files, and skill definitions. Also removes redundant config files identical to bundled defaults and cleans up excluded or stale files.

### Configuration

Relevant [`[tool.repomatic]`](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#toolrepomatic-configuration) options:

```toml
[tool.repomatic]
exclude = ["labels", "workflows/debug.yaml", "skills/awesome-triage"]
workflow.sync = true
workflow.source-paths = ["src", "lib"]
workflow.extra-paths = ["install.sh"]
workflow.ignore-paths = ["uv.lock"]

[tool.repomatic.workflow.paths]
"tests.yaml" = ["install.sh", "packages.toml", ".github/workflows/tests.yaml"]
```
