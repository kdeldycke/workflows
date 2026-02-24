---
args: [version]
title: Release `v$version`
---

### Description

This PR is ready to be merged. See the [`prepare-release` job documentation](https://github.com/kdeldycke/repokit?tab=readme-ov-file#githubworkflowschangelogyaml-jobs) for details. The [merge event will trigger](https://github.com/kdeldycke/repokit?tab=readme-ov-file#githubworkflowsreleaseyaml-jobs) the:

1. Creation of a `v$version` tag on `main` branch

2. Build and release of the Python package to [PyPI](https://pypi.org)

3. Compilation of the project's binaries

4. Publication of a GitHub `v$version` release with all artifacts above attached

### How-to release `v$version`

1. **Click `Ready for review`** button below, to get this PR out of `Draft` mode

2. **Click `Rebase and merge`** button below

> [!CAUTION]
> Do not `Squash and merge`: [we need the 2 distinct commits](https://github.com/kdeldycke/repokit/blob/main/claude.md#release-pr-freeze-and-unfreeze-commits) in this PR.
