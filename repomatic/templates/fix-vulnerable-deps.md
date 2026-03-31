---
args: [diff_table]
title: Fix vulnerable dependencies
footer: false
---

### Description

Upgrades packages with known security vulnerabilities detected by [`uv audit`](https://docs.astral.sh/uv/reference/cli/#uv-audit) against the [Python Packaging Advisory Database](https://github.com/pypa/advisory-database). Uses [`--exclude-newer-package`](https://docs.astral.sh/uv/reference/settings/#exclude-newer-package) to bypass the [`exclude-newer`](https://docs.astral.sh/uv/reference/settings/#exclude-newer) cooldown for security fixes. See the [`fix-vulnerable-deps` job documentation](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#githubworkflowsautofixyaml-jobs) for details.

$diff_table
