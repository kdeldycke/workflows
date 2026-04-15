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

| Phase       | Skill                  | Description                                                      |
| :---------- | :--------------------- | :--------------------------------------------------------------- |
| Setup       | `/repomatic-init`      | Bootstrap a repository with reusable workflows                   |
| Setup       | `/repomatic-sync`      | Sync workflow caller files with upstream                         |
| Development | `/brand-assets`        | Create and export project logo/banner SVG assets to PNG variants |
| Development | `/repomatic-deps`      | Dependency graphs, tree analysis, and declaration audit          |
| Development | `/repomatic-topics`    | Optimize GitHub topics for discoverability                       |
| Quality     | `/repomatic-lint`      | Lint workflows and repository metadata                           |
| Quality     | `/repomatic-test`      | Run and write YAML test plans for compiled binaries              |
| Maintenance | `/awesome-triage`      | Triage issues and PRs on awesome-list repos (awesome-list only)  |
| Maintenance | `/file-bug-report`     | Write a bug report for an upstream project                       |
| Maintenance | `/repomatic-audit`     | Audit downstream repo alignment with upstream reference          |
| Maintenance | `/sphinx-docs-sync`    | Compare and sync Sphinx docs across sibling projects             |
| Maintenance | `/translation-sync`    | Detect stale translations and draft updates (awesome-list only)  |
| Release     | `/repomatic-changelog` | Draft, validate, and fix changelog entries                       |
| Release     | `/repomatic-release`   | Pre-checks, release preparation, and post-release steps          |

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
