# Workflows

A central place where all my GitHub action worklows are defined.

This relies on the brand new
[reuseable workflows feature](https://docs.github.com/en/actions/learn-github-actions/reusing-workflows)
introduced in
[November 2021](https://github.blog/changelog/2021-11-24-github-actions-reusable-workflows-are-generally-available/).

## Changelog

A [detailed changelog](changelog.md) is available.

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
