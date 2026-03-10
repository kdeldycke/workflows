---
title: Regenerate dependency graph
footer: false
---

### Description

Regenerates the Mermaid dependency graph from the `uv` lockfile. See the [`update-deps-graph` job documentation](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#githubworkflowsautofixyaml-jobs) for details.

### Configuration

Relevant [`[tool.repomatic]`](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#toolrepomatic-configuration) options:

```toml
[tool.repomatic]
dependency-graph.output = "docs/dependency-graph.md"
dependency-graph.all-groups = true
dependency-graph.all-extras = true
dependency-graph.no-groups = []
dependency-graph.no-extras = []
dependency-graph.level = 0
```
