---
title: Sync `uv.lock`
---

### Description

Runs `uv lock --upgrade` to update transitive dependencies to their latest allowed versions. Only creates a PR when the lock file contains real dependency changes (timestamp-only noise is detected and skipped). See the [`sync-uv-lock` job documentation](https://github.com/kdeldycke/workflows?tab=readme-ov-file#githubworkflowsautofixyaml-jobs) for details.
