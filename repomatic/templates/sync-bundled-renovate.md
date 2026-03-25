---
title: Sync bundled `renovate.json5`
footer: false
---

### Description

Regenerates `repomatic/data/renovate.json5` from the root `renovate.json5`, stripping repo-specific settings (`assignees`, self-referencing `customManagers`). This bundled template is what downstream repos receive via `repomatic init renovate`.
