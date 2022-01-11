# Changelog

## [0.7.19 (unreleased)](https://github.com/kdeldycke/workflows/compare/v0.7.18...main)

```{{important}}
This version is not released yet and is under active development.
```

- Secret token need to be passed explicitely in reused workflow for PyPi
  publishing.

## [0.7.18 (2022-01-11)](https://github.com/kdeldycke/workflows/compare/v0.7.17...v0.7.18)

- Add version in the name of built artefacts.

## [0.7.17 (2022-01-11)](https://github.com/kdeldycke/workflows/compare/v0.7.16...v0.7.17)

- Fix detection of Poetry-based projects.

## [0.7.16 (2022-01-11)](https://github.com/kdeldycke/workflows/compare/v0.7.15...v0.7.16)

- Remove temporary debug steps.
- Do not trigger debugging and linters on `pull_request`: it duplicates the
  `push` event.
- Skip file-based labeller workflow for dependabot triggered PRs.

## [0.7.15 (2022-01-10)](https://github.com/kdeldycke/workflows/compare/v0.7.14...v0.7.15)

- Use PAT token to auto-tag releases.

## [0.7.14 (2022-01-10)](https://github.com/kdeldycke/workflows/compare/v0.7.13...v0.7.14)

- Use `actions/checkout` to fetch last 10 commits of PR during release tagging.
- Use commit message to identify release commit.
- Hard-code fetching of `main` branch on tagging to identify the release
  commit.
- Attach the release commit to the GitHub release.

## [0.7.13 (2022-01-10)](https://github.com/kdeldycke/workflows/compare/v0.7.12...v0.7.13)

- Checkout tag within job to create a new GitHub release instead of relying on
  previous job's SHA identification. The latter being different right after it
  has been merged in `main`.

## [0.7.12 (2022-01-10)](https://github.com/kdeldycke/workflows/compare/v0.7.11...v0.7.12)

- Fix variable name used to attach the tagged commit to new GitHub release.

## [0.7.11 (2022-01-10)](https://github.com/kdeldycke/workflows/compare/v0.7.10...v0.7.11)

- Force attachment of new GitHub release to the tagged commit.

## [0.7.10 (2022-01-10)](https://github.com/kdeldycke/workflows/compare/v0.7.9...v0.7.10)

- Trigger changelog workflow on any other workflow change to make sure
  hard-coded versions in URLs are kept in sync.
- Resort to explicit fetching of past commits to identify the first one of the
  `prepare-release` PR on tagging.
- Use `base_ref` variable instead of hard-coding `main` branch in release
  workflow.

## [0.7.9 (2022-01-10)](https://github.com/kdeldycke/workflows/compare/v0.7.8...v0.7.9)

- Force fetching of past 10 commits to identify `prepare-release` PR's first
  commit.
- Do not fetch the final merge commit silently produced by `actions/checkout`
  for PRs. Get `HEAD` instead.

## [0.7.8 (2022-01-10)](https://github.com/kdeldycke/workflows/compare/v0.7.7...v0.7.8)

- Fix local `prepare-release` branch name to search for first commit of PR.

## [0.7.7 (2022-01-10)](https://github.com/kdeldycke/workflows/compare/v0.7.6...v0.7.7)

- Use `git log` to identify the first commit SHA of the `prepare-release` PR.

## [0.7.6 (2022-01-10)](https://github.com/kdeldycke/workflows/compare/v0.7.5...v0.7.6)

- Merge the post-release version bump job into `prepare-release` branch
  creation workflow, the result being a 2 commits PR.
- Allow for empty release notes during the generation of a new changelog entry.

## [0.7.5 (2022-01-09)](https://github.com/kdeldycke/workflows/compare/v0.7.4...v0.7.5)

- Force `push` and `create` events to match on tags in release workflow.

## [0.7.4 (2022-01-09)](https://github.com/kdeldycke/workflows/compare/v0.7.3...v0.7.4)

- Do not try to fetch build artefacts if the publishing step has been skipped.
- Do not trigger debug workflow on `pull_request` events.

## [0.7.3 (2022-01-09)](https://github.com/kdeldycke/workflows/compare/v0.7.2...v0.7.3)

- Always execute the last `github-release` job in the release workflow, even if
  the project is not Poetry-based.
- Catch `create` events so tagging triggers a post-release version bump job.

## [0.7.2 (2022-01-09)](https://github.com/kdeldycke/workflows/compare/v0.7.1...v0.7.2)

- Untie `git-tag` and `post-release-version-bump` events. Trigger the later on
  Git tagging.
- Move the detection logic of the `prepare-release` PR merge event to a
  dedicated job.

## [0.7.1 (2022-01-09)](https://github.com/kdeldycke/workflows/compare/v0.7.0...v0.7.1)

- Fix detection of `prepare-release` PR merge event.

## [0.7.0 (2022-01-09)](https://github.com/kdeldycke/workflows/compare/v0.6.3...v0.7.0)

- Detect Poetry-based project, then auto-build and publish packages on PyPi on
  release.
- Always test builds on each commit.
- Add build artefacts to GitHub releases.

## [0.6.3 (2022-01-09)](https://github.com/kdeldycke/workflows/compare/v0.6.2...v0.6.3)

- Skip labelling on `prepare-release` branch.
- Skip version increment updates on release commits.
- Tighten up changelog job's trigger conditions.

## [0.6.2 (2022-01-09)](https://github.com/kdeldycke/workflows/compare/v0.6.1...v0.6.2)

- Fix generation of file-based labelling rules.

## [0.6.1 (2022-01-08)](https://github.com/kdeldycke/workflows/compare/v0.6.0...v0.6.1)

- Fix extension of default labelling rules.

## [0.6.0 (2022-01-08)](https://github.com/kdeldycke/workflows/compare/v0.5.5...v0.6.0)

- Add a reuseable workflow to automatically label issues and PRs depending on
  changed files.
- Allow extra labelling rules to be specified via custom input.
- Let sponsor labelling workflow to be reused.

## [0.5.5 (2022-01-07)](https://github.com/kdeldycke/workflows/compare/v0.5.4...v0.5.5)

- Replace custom version of `julb/action-manage-label` by upstream.

## [0.5.4 (2022-01-05)](https://github.com/kdeldycke/workflows/compare/v0.5.3...v0.5.4)

- Checkout repository before syncing labels so local extra definitions can be
  used.

## [0.5.3 (2022-01-05)](https://github.com/kdeldycke/workflows/compare/v0.5.2...v0.5.3)

- Fix download of remote file in label workflow.

## [0.5.2 (2022-01-05)](https://github.com/kdeldycke/workflows/compare/v0.5.1...v0.5.2)

- Use my own fork of `julb/action-manage-label` while we wait for upstream fix.
- Rename label workflow's `label-files` input variable to `extra-label-files`.

## [0.5.1 (2022-01-05)](https://github.com/kdeldycke/workflows/compare/v0.5.0...v0.5.1)

- Disable sponsor auto-tagging while we wait for upstream fix.

## [0.5.0 (2022-01-05)](https://github.com/kdeldycke/workflows/compare/v0.4.8...v0.5.0)

- Add a reuseable workflow to maintain GitHub labels.
- Add a set of default emoji-based labels.
- Add dedicated `changelog`, `sponsor` and `dependencies` labels.
- Update `CI/CD` label icon.
- Auto-tag issues and PRs opened by sponsors.
- Allow for sourcing of additional labels when reusing workflow.

## [0.4.8 (2022-01-04)](https://github.com/kdeldycke/workflows/compare/v0.4.7...v0.4.8)

- Use more recent `calibreapp/image-actions` action.
- Remove unused custom variable for reuseable GitHub release job.

## [0.4.7 (2022-01-04)](https://github.com/kdeldycke/workflows/compare/v0.4.6...v0.4.7)

- Fix use of GitHub token for workflow auto-updates on release.
- Allow typo autofix job to propose changes in workflow files.

## [0.4.6 (2022-01-04)](https://github.com/kdeldycke/workflows/compare/v0.4.5...v0.4.6)

- Let GitHub release produced on tagging to be customized with user's content
  and uploaded files.
- Expose tagged version from reuseable `release` workflow.

## [0.4.5 (2022-01-03)](https://github.com/kdeldycke/workflows/compare/v0.4.4...v0.4.5)

- Fix use of the right token for reused `changelog` and `release` workflows.
- Restrict comparison URL steps to source workflow.

## [0.4.4 (2022-01-03)](https://github.com/kdeldycke/workflows/compare/v0.4.3...v0.4.4)

- Do not rely on `bumpversion` for comparison URL update on release tagging.

## [0.4.3 (2022-01-03)](https://github.com/kdeldycke/workflows/compare/v0.4.2...v0.4.3)

- Only match first occurrence of triple-backticks delimited block text in
  `changelog.md` in `prepare-release` job. Also matches empty line within the
  block.
- Make GitHub changelog URL update more forgiving.

## [0.4.2 (2022-01-03)](https://github.com/kdeldycke/workflows/compare/v0.4.1...v0.4.2)

- Skip steps in workflows which are specific to the source repository.
- Aligns all PR content.

## [0.4.1 (2022-01-03)](https://github.com/kdeldycke/workflows/compare/v0.4.0...v0.4.1)

- Allow changelog and release workflows to be reuseable.

## [0.4.0 (2021-12-31)](https://github.com/kdeldycke/workflows/compare/v0.3.5...v0.4.0)

- Factorize version increment jobs.

## [0.3.5 (2021-12-31)](https://github.com/kdeldycke/workflows/compare/v0.3.4...v0.3.5)

- Provide tag version for GitHub release creation.

## [0.3.4 (2021-12-31)](https://github.com/kdeldycke/workflows/compare/v0.3.3...v0.3.4)

- Chain `post-release-version-bump` job with automatic git tagging.
- Auto-commit `post-release-version-bump` results.
- Create a GitHub release on tagging.

## [0.3.3 (2021-12-30)](https://github.com/kdeldycke/workflows/compare/v0.3.2...v0.3.3)

- Bump YAML linting max line length to 120.
- Auto-tag release after the `prepare-release` PR is merged back into `main`.

## [0.3.2 (2021-12-30)](https://github.com/kdeldycke/workflows/compare/v0.3.1...v0.3.2)

- Refresh every day the date in `prepare-release` job.
- Skip linting on `prepare-release` job as it does not points to tagged URLs
  yet.
- Reduce changelog PRs refresh rate based on changed files.
- Rely on `create-pull-request` action default to set authorship.
- Fix `autofix` workflow reuseability.

## [0.3.1 (2021-12-23)](https://github.com/kdeldycke/workflows/compare/v0.3.0...v0.3.1)

- Hard-code tagged version for executed Python script.
- Activate debugging workflow on all branches and PRs.
- Allows debug workflow to be reused.

## [0.3.0 (2021-12-16)](https://github.com/kdeldycke/workflows/compare/v0.2.0...v0.3.0)

- Add a reuseable workflow to fix typos.
- Add a reuseable workflow to optimize images.
- Add a reuseable workflow to auto-format Python files with isort and Black.
- Add a reuseable workflow to auto-format Markdown files with mdformat.
- Add a reuseable workflow to auto-format JSON files with jsonlint.
- Add a reuseable workflow to auto-update .gitignore file.
- Add a reuseable workflow to auto-update .mailmap file.
- Force retargetting of workflow dependencies to `main` branch on post-release
  version bump.

## [0.2.0 (2021-12-15)](https://github.com/kdeldycke/workflows/compare/v0.1.0...v0.2.0)

- Add autolock reuseable workflow for closed issues and PRs.
- Automate changelog and version management.
- Add workflow to create ready-to-use PRs to prepare a release, post-release
  version bump and minor & major version increments.
- Add a debug workflow to print action context and environment variables.
- Set Pylint failure threshold at 80%.

## [0.1.0 (2021-12-12)](https://github.com/kdeldycke/workflows/compare/v0.0.1...v0.1.0)

- Install project with Poetry before calling Pylint if `pyproject.toml`
  presence is detected.
- Hard-code tagged version in requirement URL for reuseable workflows.
- Document the release process.

## [0.0.1 (2021-12-11)](https://github.com/kdeldycke/workflows/compare/5cbdbb...v0.0.1)

- Initial public release.
