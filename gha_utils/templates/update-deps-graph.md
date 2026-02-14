---
title: "[autofix] Regenerate dependency graph"
---
### Description

Regenerates the Mermaid dependency graph from the `uv` lockfile. See the [`update-deps-graph` job documentation](https://github.com/kdeldycke/workflows?tab=readme-ov-file#githubworkflowsautofixyaml-jobs) for details.

### Configuration

Customize dependency graph generation in your `pyproject.toml`:

```toml
[tool.gha-utils]
dependency-graph-output = "docs/dependency-graph.md"  # Output file path
```