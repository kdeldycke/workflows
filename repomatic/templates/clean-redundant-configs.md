---
title: Remove redundant tool config files
footer: false
---

### Description

Removes tool config files (`.yamllint.yaml`, `zizmor.yaml`, etc.) that are identical to the bundled defaults in [repomatic](https://github.com/kdeldycke/repomatic). The tool runner already uses these defaults as a fallback when no native config file exists, so the on-disk copies are redundant.
