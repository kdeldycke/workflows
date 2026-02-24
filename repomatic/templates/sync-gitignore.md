---
title: Sync `.gitignore`
---

### Description

Regenerates `.gitignore` from [gitignore.io](https://github.com/toptal/gitignore.io) templates. See the [`sync-gitignore` job documentation](https://github.com/kdeldycke/repomatic?tab=readme-ov-file#githubworkflowsautofixyaml-jobs) for details.

### Configuration

Customize `.gitignore` generation in your `pyproject.toml`:

```toml
[tool.repomatic]
gitignore-location = "./.gitignore" # File path (default)
gitignore-extra-categories = ["terraform", "go"] # Extra gitignore.io categories
gitignore-extra-content = '''
junit.xml

# Claude Code
.claude/
'''
```
