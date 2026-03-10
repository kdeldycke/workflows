---
title: Sync `.gitignore`
footer: false
---

### Description

Regenerates `.gitignore` from [gitignore.io](https://github.com/toptal/gitignore.io) templates. See the [`sync-gitignore` job documentation](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#githubworkflowsautofixyaml-jobs) for details.

### Configuration

Relevant [`[tool.repomatic]`](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#toolrepomatic-configuration) options:

```toml
[tool.repomatic]
gitignore.sync = true
gitignore.location = "./.gitignore"
gitignore.extra-categories = ["terraform", "go"]
gitignore.extra-content = '''
junit.xml

# Claude Code
.claude/
'''
```
