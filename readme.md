# `repomatic`

[![Last release](https://img.shields.io/pypi/v/repomatic.svg)](https://pypi.org/project/repomatic/)
[![Python versions](https://img.shields.io/pypi/pyversions/repomatic.svg)](https://pypi.org/project/repomatic/)
[![Downloads](https://static.pepy.tech/badge/repomatic/month)](https://pepy.tech/projects/repomatic)
[![Unittests status](https://github.com/kdeldycke/repomatic/actions/workflows/tests.yaml/badge.svg?branch=main)](https://github.com/kdeldycke/repomatic/actions/workflows/tests.yaml?query=branch%3Amain)
[![Coverage status](https://codecov.io/gh/kdeldycke/repomatic/branch/main/graph/badge.svg)](https://app.codecov.io/gh/kdeldycke/repomatic)

A Python CLI and `pyproject.toml` configuration that let you **release Python packages multiple times a day with only 2-clicks**. Designed for `uv`-based Python projects, but usable for other projects too. The CLI operates through reusable GitHub Actions workflows as its CI delivery mechanism.

**Maintainer-in-the-loop**: nothing is done behind your back. A PR or issue is created every time a change is proposed or action is needed.

Automates:

- Version bumping
- Changelog management
- Formatting autofix for: Python, Markdown, JSON, Shell, typos
- Linting: Python types with `mypy`, YAML, `zsh`, GitHub Actions, workflow security, URLS & redirects, Awesome lists, secrets
- Compiling of Python binaries for Linux / macOS / Windows on `x86_64` & `arm64`
- Building of Python packages and upload to PyPI
- Produce attestations
- Git version tagging and GitHub release creation
- Synchronization of: `uv.lock`, `.gitignore`, `.mailmap` and Mermaid dependency graph
- Auto-locking of inactive closed issues
- Static image optimization
- Sphinx documentation building & deployment, and `autodoc` updates
- Label management, with file-based and content-based rules
- Awesome list template synchronization

## Quick start

```shell-session
$ cd my-project
$ uvx -- repomatic init
$ git add .
$ git commit -m "Update repomatic files"
$ git push
```

This **works for both new and existing repositories** — managed files (workflows, configs, skills) are always regenerated to the latest version. The only exception is `changelog.md`, which is never overwritten once it exists. The workflows will start running and guide you through any remaining setup via issues and PRs in your repository.

Run `repomatic init --help` to see available components and options.

## Documentation

See the **[full documentation](https://kdeldycke.github.io/repomatic/)** for:

- [Installation methods and executables](https://kdeldycke.github.io/repomatic/install.html)
- [`[tool.repomatic]` configuration reference](https://kdeldycke.github.io/repomatic/configuration.html)
- [CLI parameters](https://kdeldycke.github.io/repomatic/cli-parameters.html)
- [Reusable workflow reference](https://kdeldycke.github.io/repomatic/workflows.html) (all 13 workflows with job descriptions)
- [Security practices and token setup](https://kdeldycke.github.io/repomatic/security.html)
- [Claude Code skills](https://kdeldycke.github.io/repomatic/skills.html)
- [API reference](https://kdeldycke.github.io/repomatic/repomatic.html)

## Used in

Check these projects to get real-life examples of usage and inspiration:

- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/awesome-falsehood?label=%E2%AD%90&style=flat-square) [Awesome Falsehood](https://github.com/kdeldycke/awesome-falsehood) - Falsehoods Programmers Believe in.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/awesome-engineering-team-management?label=%E2%AD%90&style=flat-square) [Awesome Engineering Team Management](https://github.com/kdeldycke/awesome-engineering-team-management) - How to transition from software development to engineering management.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/awesome-iam?label=%E2%AD%90&style=flat-square) [Awesome IAM](https://github.com/kdeldycke/awesome-iam) - Identity and Access Management knowledge for cloud platforms.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/awesome-billing?label=%E2%AD%90&style=flat-square) [Awesome Billing](https://github.com/kdeldycke/awesome-billing) - Billing & Payments knowledge for cloud platforms.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/meta-package-manager?label=%E2%AD%90&style=flat-square) [Meta Package Manager](https://github.com/kdeldycke/meta-package-manager) - A unifying CLI for multiple package managers.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/mail-deduplicate?label=%E2%AD%90&style=flat-square) [Mail Deduplicate](https://github.com/kdeldycke/mail-deduplicate) - A CLI to deduplicate similar emails.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/dotfiles?label=%E2%AD%90&style=flat-square) [dotfiles](https://github.com/kdeldycke/dotfiles) - macOS dotfiles for Python developers.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/click-extra?label=%E2%AD%90&style=flat-square) [Click Extra](https://github.com/kdeldycke/click-extra) - Extra colorization and configuration loading for Click.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/repomatic?label=%E2%AD%90&style=flat-square) [repomatic](https://github.com/kdeldycke/repomatic) - Itself. Eat your own dog-food.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/extra-platforms?label=%E2%AD%90&style=flat-square) [Extra Platforms](https://github.com/kdeldycke/extra-platforms) - Detect platforms and group them by family.

Feel free to send a PR to add your project in this list if you are relying on these scripts.

## Development

See `claude.md` for development commands, code style, testing guidelines, and design principles.
