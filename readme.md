# Workflows

A central place where all my GitHub action worklows are defined.

This relies on the brand new [reuseable workflows feature](https://docs.github.com/en/actions/learn-github-actions/reusing-workflows) introduced in [November 2021](https://github.blog/changelog/2021-11-24-github-actions-reusable-workflows-are-generally-available/).

## Changelog

A [detailed changelog](changelog.md) is available.

## Release process

Get a clean copy of the project:

``` shell-session
$ git clone https://github.com/kdeldycke/workflows.git
$ cd workflows
$ git checkout main
```

Prepare the release for tagging:

``` shell-session
$ ./.github/prepare_release.sh
```

Double check the changelog is clean and the release version has been hard-coded in reuseable workflows.

Then create a release commit and tag it:

``` shell-session
$ git add ./changelog.md ./.github/workflows/*.yaml
$ git commit -m "Release v${RELEASE_VERSION}"
$ git tag "v${RELEASE_VERSION}"
$ git push
$ git push --tags
$ unset RELEASE_VERSION
```

## Version bump

In the middle of your development, if the upcoming release is no longer bug-fix
only, feel free to bump to the next `minor`:

``` shell-session
$ python -m pip install --requirement ./requirements.txt
$ bumpversion --verbose minor
$ git add ./.bumpversion.cfg ./changelog.md
$ git commit -m "Next release no longer bug-fix only. Bump revision."
$ git push
```

For really big changes, bump the `major`.