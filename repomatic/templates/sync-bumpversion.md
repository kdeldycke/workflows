---
title: Sync `bump-my-version` config
footer: false
---

### Description

Initializes the `[tool.bumpversion]` configuration in `pyproject.toml` from the [bundled template](https://github.com/kdeldycke/repomatic/blob/main/repomatic/data/bumpversion.toml). See the [`sync-bumpversion` job documentation](https://kdeldycke.github.io/repomatic/workflows.html#github-workflows-autofix-yaml-jobs) for details.

### Configuration

Relevant [`[tool.repomatic]`](https://kdeldycke.github.io/repomatic/configuration.html) options:

- [`bumpversion.sync`](https://kdeldycke.github.io/repomatic/configuration.html#bumpversion-sync)
