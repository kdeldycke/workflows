---
title: Regenerate dependency graph
---

### Description

Regenerates the Mermaid dependency graph from the `uv` lockfile. See the [`update-deps-graph` job documentation](https://github.com/kdeldycke/workflows?tab=readme-ov-file#githubworkflowsautofixyaml-jobs) for details.

### Configuration

Customize dependency graph generation in your `pyproject.toml`:

```toml
[tool.gha-utils]
dependency-graph-output = "docs/dependency-graph.md"  # Output file path
dependency-graph-all-groups = true   # Include all dependency groups (default: true)
dependency-graph-all-extras = true   # Include all optional extras (default: true)
dependency-graph-no-groups = []      # Groups to exclude
dependency-graph-no-extras = []      # Extras to exclude
dependency-graph-level = 0           # Max depth (0 or omit = unlimited)
```
