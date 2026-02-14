---
title: Update `.gitignore`
---
### Description

Regenerates `.gitignore` from [gitignore.io](https://github.com/toptal/gitignore.io) templates. See the [`update-gitignore` job documentation](https://github.com/kdeldycke/workflows?tab=readme-ov-file#githubworkflowsautofixyaml-jobs) for details.

### Configuration

Customize `.gitignore` generation in your `pyproject.toml`:

```toml
[tool.gha-utils]
gitignore-location = "./.gitignore"               # File path (default)
gitignore-extra-categories = ["terraform", "go"]  # Extra gitignore.io categories
gitignore-extra-content = '''
junit.xml

# Claude Code
.claude/
'''
```