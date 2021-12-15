# Workflows

A central place where all my GitHub action worklows are defined.

This relies on the brand new [reuseable workflows feature](https://docs.github.com/en/actions/learn-github-actions/reusing-workflows) introduced in [November 2021](https://github.blog/changelog/2021-11-24-github-actions-reusable-workflows-are-generally-available/).

## Changelog

A [detailed changelog](changelog.md) is available.

## Release process

All steps of the release process and version management are automated in the
[`changelog.yaml` workflow](https://github.com/kdeldycke/workflows/blob/main/.github/workflows/changelog.yaml).

All there's left to do is check the open `draft` PRs proposed by the workflow and merge them on a case-by-case basis.
