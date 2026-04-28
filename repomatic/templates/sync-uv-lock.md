---
args: [diff_table]
title: Sync `uv.lock`
footer: false
---

### Description

Runs `uv lock --upgrade` to update transitive dependencies to their latest allowed versions. See the [`sync-uv-lock` job documentation](https://kdeldycke.github.io/repomatic/workflows.html#github-workflows-autofix-yaml-jobs) for details.

\$diff_table

### Configuration

Relevant [`[tool.repomatic]`](https://kdeldycke.github.io/repomatic/configuration.html) options:

- [`uv-lock.sync`](https://kdeldycke.github.io/repomatic/configuration.html#uv-lock-sync)
