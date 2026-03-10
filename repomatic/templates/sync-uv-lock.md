---
title: Sync `uv.lock`
footer: false
---

### Description

Runs `uv lock --upgrade` to update transitive dependencies to their latest allowed versions. Only creates a PR when the lock file contains real dependency changes (timestamp-only noise is detected and skipped). See the [`sync-uv-lock` job documentation](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#githubworkflowsautofixyaml-jobs) for details.

### Configuration

Relevant [`[tool.repomatic]`](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#toolrepomatic-configuration) options:

```toml
[tool.repomatic]
uv-lock.sync = true
```
