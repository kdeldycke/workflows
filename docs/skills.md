# {octicon}`dependabot` Claude Code skills

This repository includes [Claude Code skills](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/skills) that wrap `repomatic` CLI commands as slash commands. Downstream repositories can install them with:

```shell-session
$ uvx -- repomatic init skills
```

To install a single skill:

```shell-session
$ uvx -- repomatic init skills/repomatic-topics
```

Selectors use the same `component[/file]` syntax as the `exclude` config option in [`[tool.repomatic]`](configuration.md).

To list all available skills with descriptions:

```shell-session
$ uvx -- repomatic list-skills
```

## Available skills

| Phase       | Skill                                                                                                                  | Description                                                      |
| :---------- | :--------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------- |
| Setup       | [`/repomatic-init`](https://github.com/kdeldycke/repomatic/blob/main/.claude/skills/repomatic-init/SKILL.md)           | Bootstrap a repository with reusable workflows                   |
| Setup       | [`/repomatic-sync`](https://github.com/kdeldycke/repomatic/blob/main/.claude/skills/repomatic-sync/SKILL.md)           | Sync workflow caller files with upstream                         |
| Development | [`/brand-assets`](https://github.com/kdeldycke/repomatic/blob/main/.claude/skills/brand-assets/SKILL.md)               | Create and export project logo/banner SVG assets to PNG variants |
| Development | [`/repomatic-deps`](https://github.com/kdeldycke/repomatic/blob/main/.claude/skills/repomatic-deps/SKILL.md)           | Dependency graphs, tree analysis, and declaration audit          |
| Development | [`/repomatic-topics`](https://github.com/kdeldycke/repomatic/blob/main/.claude/skills/repomatic-topics/SKILL.md)       | Optimize GitHub topics for discoverability                       |
| Quality     | [`/repomatic-lint`](https://github.com/kdeldycke/repomatic/blob/main/.claude/skills/repomatic-lint/SKILL.md)           | Lint workflows and repository metadata                           |
| Quality     | [`/repomatic-test`](https://github.com/kdeldycke/repomatic/blob/main/.claude/skills/repomatic-test/SKILL.md)           | Run and write YAML test plans for compiled binaries              |
| Maintenance | [`/awesome-triage`](https://github.com/kdeldycke/repomatic/blob/main/.claude/skills/awesome-triage/SKILL.md)           | Triage issues and PRs on awesome-list repos (awesome-list only)  |
| Maintenance | [`/file-bug-report`](https://github.com/kdeldycke/repomatic/blob/main/.claude/skills/file-bug-report/SKILL.md)         | Write a bug report for an upstream project                       |
| Maintenance | [`/repomatic-audit`](https://github.com/kdeldycke/repomatic/blob/main/.claude/skills/repomatic-audit/SKILL.md)         | Audit downstream repo alignment with upstream reference          |
| Maintenance | [`/sphinx-docs-sync`](https://github.com/kdeldycke/repomatic/blob/main/.claude/skills/sphinx-docs-sync/SKILL.md)       | Compare and sync Sphinx docs across sibling projects             |
| Maintenance | [`/translation-sync`](https://github.com/kdeldycke/repomatic/blob/main/.claude/skills/translation-sync/SKILL.md)       | Detect stale translations and draft updates (awesome-list only)  |
| Release     | [`/repomatic-changelog`](https://github.com/kdeldycke/repomatic/blob/main/.claude/skills/repomatic-changelog/SKILL.md) | Draft, validate, and fix changelog entries                       |
| Release     | [`/repomatic-release`](https://github.com/kdeldycke/repomatic/blob/main/.claude/skills/repomatic-release/SKILL.md)     | Pre-checks, release preparation, and post-release steps          |

## Recommended workflow

The typical lifecycle for maintaining a downstream repository follows this sequence. Each skill suggests next steps after completing, creating a guided flow:

1. `/repomatic-init` — One-time setup: bootstrap workflows, labels, and configs
2. `/repomatic-sync` — Periodic: pull latest upstream workflow changes
3. `/repomatic-lint` — Before merging: validate workflows and metadata
4. `/repomatic-deps` — As needed: visualize the dependency tree
5. `/repomatic-changelog` — Before release: draft and validate changelog entries
6. `/repomatic-release` — Release time: pre-flight checks and release preparation

### Walkthrough: setup to first release

```text
# In Claude Code, bootstrap your repository
/repomatic-init

# After making changes, sync with latest upstream workflows
/repomatic-sync

# Validate everything
/repomatic-lint all

# Add changelog entries for your changes
/repomatic-changelog add

# Validate the changelog
/repomatic-changelog check

# Pre-flight checks before release
/repomatic-release check

# Prepare the release PR
/repomatic-release prep
```
