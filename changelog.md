# Changelog

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
