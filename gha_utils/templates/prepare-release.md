---
args: [version, repo_url]
title: Release `v$version`
---
### Description

This PR is ready to be merged. See the [`prepare-release` job documentation](https://github.com/kdeldycke/workflows?tab=readme-ov-file#githubworkflowschangelogyaml-jobs) for details. The [merge event will trigger](https://github.com/kdeldycke/workflows?tab=readme-ov-file#githubworkflowsreleaseyaml-jobs) the:

1. Creation of a [`v$version` tag on `main`]($repo_url/tree/v$version) branch

1. Build and release of the Python package to [PyPI](https://pypi.org)

1. Compilation of the project's binaries

1. Publication of a [GitHub `v$version` release]($repo_url/releases/tag/v$version) with all artifacts above attached

### How-to release `v$version`

1. **Click `Ready for review`** button below, to get this PR out of `Draft` mode

1. **Click `Rebase and merge`** button below

   > [!CAUTION]
   > Do not `Squash and merge`: [we need the 2 distinct commits](https://github.com/kdeldycke/workflows/blob/main/claude.md#release-pr-freeze-and-unfreeze-commits) in this PR.