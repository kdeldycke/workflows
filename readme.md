# Workflows

Maintaining project takes time. This repository contains workflows to automate most of the boring tasks.

These workflows are mostly used for Poetry-based Python CLI and their documentation, but not only. They're all [reuseable GitHub actions workflows](https://docs.github.com/en/actions/learn-github-actions/reusing-workflows).

Reasons for a centralized workflow repository:

- reusability of course: no need to update dozens of repository where 95% of workflows are the same
- centralize all dependencies pertaining to automation: think of the point-release of an action that triggers dependabot upgrade to all your repositories depending on it

## Release management

It turns out [Release Engineering is a full-time job, and full of edge-cases](https://blog.axo.dev/2023/02/cargo-dist).

Rust has [`cargo-dist`](https://github.com/axodotdev/cargo-dist). Go has... ? But there is no equivalent for Python.

So I made up a [`release.yaml` workflow](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/release.yaml), which:

1. Extracts project metadata from `pyproject.toml`
1. Generates a build matrix of all commits / os / arch / CLI entry points
1. Build Python wheel with Twine
1. Compile binaries of all CLI with Nuitka
1. Tag the release commit in Git
1. Publish new version to PyPi
1. Publish a GitHub release
1. Attach and rename build artifacts to it

## Changelog

A [detailed changelog](changelog.md) is available.

## Used in

Check these projects to get real-life examples of usage and inspiration:

- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/awesome-falsehood?label=%E2%AD%90&style=flat-square) [Awesome Falsehood](https://github.com/kdeldycke/awesome-falsehood#readme) - Falsehoods Programmers Believe in.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/awesome-engineering-team-management?label=%E2%AD%90&style=flat-square) [Awesome Engineering Team Management](https://github.com/kdeldycke/awesome-engineering-team-management#readme) - How to transition from software development to engineering management.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/awesome-iam?label=%E2%AD%90&style=flat-square) [Awesome IAM](https://github.com/kdeldycke/awesome-iam#readme) - Identity and Access Management knowledge for cloud platforms.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/awesome-billing?label=%E2%AD%90&style=flat-square) [Awesome Billing](https://github.com/kdeldycke/awesome-billing#readme) - Billing & Payments knowledge for cloud platforms.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/meta-package-manager?label=%E2%AD%90&style=flat-square) [Meta Package Manager](https://github.com/kdeldycke/meta-package-manager#readme) - A unifying CLI for multiple package managers.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/mail-deduplicate?label=%E2%AD%90&style=flat-square) [Mail Deduplicate](https://github.com/kdeldycke/mail-deduplicate#readme) - A CLI to deduplicate similar emails.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/dotfiles?label=%E2%AD%90&style=flat-square) [dotfiles](https://github.com/kdeldycke/dotfiles#readme) - macOS dotfiles for Python developers.
- ![GitHub stars](https://img.shields.io/github/stars/themagicalmammal/wikibot?label=%E2%AD%90&style=flat-square) [Wiki bot](https://github.com/themagicalmammal/wikibot#readme) - A bot which provides features from Wikipedia like summary, title searches, location API etc.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/click-extra?label=%E2%AD%90&style=flat-square) [Click Extra](https://github.com/kdeldycke/click-extra#readme) - Extra colorization and configuration loading for Click.
- ![GitHub stars](https://img.shields.io/github/stars/kdeldycke/workflows?label=%E2%AD%90&style=flat-square) [workflows](https://github.com/kdeldycke/workflows#readme) - Itself. Eat your own dog-food.
- ![GitHub stars](https://img.shields.io/github/stars/themagicalmammal/stock-analyser?label=%E2%AD%90&style=flat-square) [Stock Analysis](https://github.com/themagicalmammal/stock-analyser#readme) - Simple to use interfaces for basic technical analysis of stocks.
- ![GitHub stars](https://img.shields.io/github/stars/themagicalmammal/genetictabler?label=%E2%AD%90&style=flat-square) [GeneticTabler](https://github.com/themagicalmammal/genetictabler#readme) - Time Table Scheduler using Genetic Algorithms.
- ![GitHub stars](https://img.shields.io/github/stars/themagicalmammal/excel-write?label=%E2%AD%90&style=flat-square) [Excel Write](https://github.com/themagicalmammal/excel-write#readme) - Optimised way to write in excel files.

Feel free to send a PR to add your project in this list if you are relying on these scripts.

## Release process

All steps of the release process and version management are automated in the
[`changelog.yaml`](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/changelog.yaml)
and
[`release.yaml`](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/release.yaml)
workflows.

All there's left to do is to:

- [check the open draft `prepare-release` PR](https://github.com/kdeldycke/workflows/pulls?q=is%3Apr+is%3Aopen+head%3Aprepare-release)
  and its changes,
- click the `Ready for review` button,
- click the `Rebase and merge` button,
- let the workflows tag the release and set back the `main` branch into a
  development state.
