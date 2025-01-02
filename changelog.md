# Changelog

## [5.0.0 (unreleased)](https://github.com/kdeldycke/workflows/compare/v4.9.0...main)

> [!IMPORTANT]
> This version is not released yet and is under active development.

- Replace unmaintained `jsonlint` by ESLint.

## [4.9.0 (2024-12-27)](https://github.com/kdeldycke/workflows/compare/v4.8.4...v4.9.0)

- Use `uv` instead of `setup-python` action to install Python. On all platforms but `windows-2019`.
- Remove auto-generated dummy `pyproject.toml` used to hack `setup-python` caching.
- Run all jobs on Python 3.13.
- Move coverage configuration to pytest invocation.
- Do not let `uv sync` operation update the `uv.lock` file.
- Depends on released version of `mdformat_deflist`.

## [4.8.4 (2024-11-22)](https://github.com/kdeldycke/workflows/compare/v4.8.3...v4.8.4)

- Run binaries tests into a shell subprocess.

## [4.8.3 (2024-11-20)](https://github.com/kdeldycke/workflows/compare/v4.8.2...v4.8.3)

- Fix parsing of default timeout.
- Do not force encoding when running CLI in binary test job.

## [4.8.2 (2024-11-20)](https://github.com/kdeldycke/workflows/compare/v4.8.1...v4.8.2)

- Add a `timeout` parameter to release workflow test execution.

## [4.8.1 (2024-11-19)](https://github.com/kdeldycke/workflows/compare/v4.8.0...v4.8.1)

- Fix permissions for tagging in release workflow.

## [4.8.0 (2024-11-19)](https://github.com/kdeldycke/workflows/compare/v4.7.2...v4.8.0)

- Run Nuitka binary builds on Python 3.13.
- Run a series of test calls on the binaries produced by the build job.
- Replace unmaintained `hub` CLI by `gh` in broken links job.

## [4.7.2 (2024-11-10)](https://github.com/kdeldycke/workflows/compare/v4.7.1...v4.7.2)

- Fix installation of `hub` on broken links job.

## [4.7.1 (2024-11-03)](https://github.com/kdeldycke/workflows/compare/v4.7.0...v4.7.1)

- Fix upload to PyPi on release.
- Remove unused `uv_requirement_params` in metadata.

## [4.7.0 (2024-11-03)](https://github.com/kdeldycke/workflows/compare/v4.6.1...v4.7.0)

- Remove `extra_python_params` variant in `nuitka_matrix` metadata.
- Add official support of Python 3.13.
- Drop support for Python 3.9.
- Use `macos-15` instead of `macos-14` to build binaries for `arm64`.
- Use `ubuntu-24.04` instead of `ubuntu-22.04` to built binaries for Linux.
- Run tests on Python 3.14-dev.

## [4.6.1 (2024-09-26)](https://github.com/kdeldycke/workflows/compare/v4.6.0...v4.6.1)

- Use `uv` to publish Python packages.

## [4.6.0 (2024-09-20)](https://github.com/kdeldycke/workflows/compare/v4.5.4...v4.6.0)

- Use `uv` to build Python packages.
- Remove dependency on `build` package.
- Fix coverage report upload.
- Upload test results to coverage.

## [4.5.4 (2024-09-04)](https://github.com/kdeldycke/workflows/compare/v4.5.3...v4.5.4)

- Rerelease to stabilize changelog updates.

## [4.5.3 (2024-09-04)](https://github.com/kdeldycke/workflows/compare/v4.5.2...v4.5.3)

- Fix changelog indention.
- Add changelog unittests.

## [4.5.2 (2024-08-26)](https://github.com/kdeldycke/workflows/compare/v4.5.1...v4.5.2)

- Rerelease to fix admonition in changelog.
- Fix changelog new entry format.

## [4.5.1 (2024-08-25)](https://github.com/kdeldycke/workflows/compare/v4.5.0...v4.5.1)

- Fix over-escaping of `[!IMPORTANT]` admonition in changelog.
- Fix content writing into output files.

## [4.5.0 (2024-08-24)](https://github.com/kdeldycke/workflows/compare/v4.4.5...v4.5.0)

- Replace `mdformat-black` by `mdformat-ruff`.
- Install `mdformat`, `gha-utils`, `yamllint`, `bump-my-version`, `ruff`, `blacken-docs` and `autopep8` as a global tool to not interfere with the project dependencies.
- Fix `mdformat-pelican` compatibility with `mdformat-gfm`.
- Upgrade job runs from `ubuntu-22.04` to `ubuntu-24.04`.
- Mark python 3.13-dev tests as stable.
- Fix empty entry composition.
- Remove local workaround for Nuitka.

## [4.4.5 (2024-08-18)](https://github.com/kdeldycke/workflows/compare/v4.4.4...v4.4.5)

- Bump `gha-utils` CLI.

## [4.4.4 (2024-08-18)](https://github.com/kdeldycke/workflows/compare/v4.4.3...v4.4.4)

- Fix update of changelog without past entries.

## [4.4.3 (2024-08-12)](https://github.com/kdeldycke/workflows/compare/v4.4.2...v4.4.3)

- Release with relaxed dependencies.

## [4.4.2 (2024-08-02)](https://github.com/kdeldycke/workflows/compare/v4.4.1...v4.4.2)

- Add local workaround for Nuitka to fix bad packaging of `license_expression` package at build time.

## [4.4.1 (2024-08-01)](https://github.com/kdeldycke/workflows/compare/v4.4.0...v4.4.1)

- Bump Nuitka and `uv`.

## [4.4.0 (2024-07-27)](https://github.com/kdeldycke/workflows/compare/v4.3.4...v4.4.0)

- Drop support for Python 3.8.
- Rely on released version of `mdformat-pelican`.
- Fix invocation of installed `mdformat` and its plugin.

## [4.3.4 (2024-07-24)](https://github.com/kdeldycke/workflows/compare/v4.3.3...v4.3.4)

- Do not maintain `.mailmap` files on Awesome repositories.

## [4.3.3 (2024-07-24)](https://github.com/kdeldycke/workflows/compare/v4.3.2...v4.3.3)

- Bump `uv` and Nuitka.

## [4.3.2 (2024-07-22)](https://github.com/kdeldycke/workflows/compare/v4.3.1...v4.3.2)

- Always use frozen `uv.lock` file on `uv run` invocation.

## [4.3.1 (2024-07-18)](https://github.com/kdeldycke/workflows/compare/v4.3.0...v4.3.1)

- Do not print progress bars on `uv` calls.

## [4.3.0 (2024-07-17)](https://github.com/kdeldycke/workflows/compare/v4.2.1...v4.3.0)

- Add a new job to keep `uv.lock` updated and in sync.
- Exclude auto-updated `uv.lock` files from PRs produced from `uv run` and `uv tool run` invocations.

## [4.2.1 (2024-07-15)](https://github.com/kdeldycke/workflows/compare/v4.2.0...v4.2.1)

- Fix options in `gha-utils mailmap-sync` calls.
- Use latest `gha-utils` release in workflows.

## [4.2.0 (2024-07-15)](https://github.com/kdeldycke/workflows/compare/v4.1.4...v4.2.0)

- Rename `gha-utils mailmap` command to `gha-utils mailmap-sync`.
- Add new `--create-if-missing`/`--skip-if-missing` option to `gha-utils mailmap-sync` command.
- Do not create `.mailmap` from scratch in workflows: only update existing ones.
- Normalize, deduplicate and sort identities in `.mailmap` files.
- Keep comments attached to their mapping when re-sorting `.mailmap` files.
- Do not duplicate header metadata on `.mailmap` updates.
- Do not update `.mailmap` files if no changes are detected.
- Add new `boltons` dependency.

## [4.1.4 (2024-07-02)](https://github.com/kdeldycke/workflows/compare/v4.1.3...v4.1.4)

- Bump `gha-utils` CLI.

## [4.1.3 (2024-07-02)](https://github.com/kdeldycke/workflows/compare/v4.1.2...v4.1.3)

- Fix recreation of specifiers.

## [4.1.2 (2024-07-02)](https://github.com/kdeldycke/workflows/compare/v4.1.1...v4.1.2)

- Revert to rely entirely on released `gha-utils` CLI for release workflow.

## [4.1.1 (2024-07-02)](https://github.com/kdeldycke/workflows/compare/v4.1.0...v4.1.1)

- Pre-compute repository initial state before digging into commit log history.
- Redo release as `v4.1.0` has been broken.
- Rely on old `v4.0.2` standalone metadata script temporarily to fix release process.
- Remove failing `--statistics` production on `ruff` invocation.

## [4.1.0 (2024-07-01)](https://github.com/kdeldycke/workflows/compare/v4.0.2...v4.1.0)

- Replace in-place `metadata.py`, `update_changelog.py` and `update_mailmap.py` scripts by `gha-utils` CLI.
- Remove pre-workflow `check-mailmap` job.
- Bump Python minimal requirement to 3.8.6.
- Fix computation of lower bound Python version support if minimal requirement is not contained to `major.minor` specifier.
- Add dependency on `backports.strenum` for `Python < 3.11`.
- Change dependency on `mdformat-pelican` from personal fork to unreleased upstream.
- Remove dependency on `black` and `mypy`.

## [4.0.2 (2024-06-29)](https://github.com/kdeldycke/workflows/compare/v4.0.1...v4.0.2)

- Remove comments in GitHub action's environment variable files.
- Test CLI invocation.

## [4.0.1 (2024-06-29)](https://github.com/kdeldycke/workflows/compare/v4.0.0...v4.0.1)

- Re-release to register PyPi project.

## [4.0.0 (2024-06-29)](https://github.com/kdeldycke/workflows/compare/v3.5.11...v4.0.0)

- Package all utilities in a `gha_utils` CLI.
- Remove support for Poetry-based projects. All Python projects are expected to follow [standard `pyproject.toml` conventions](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/).
- Sort contributors in `.mailmap` files regardless of case sensitivity.
- Force default values of workflow's inputs when triggered from other events (i.e. in non-reusable contexts).
- Run all Python-based commands via `uv run` and `uv tool run`.
- Replace `is_poetry_project` metadata by `is_python_project`.
- Add new `uv_requirement_params` metadata output.
- Remove dependency on `poetry` package.
- Add new dependencies on `build`, `packaging`, `pyproject-metadata` and `click-extra`.

## [3.5.11 (2024-06-22)](https://github.com/kdeldycke/workflows/compare/v3.5.10...v3.5.11)

- Read `pyproject.toml` without relying on Poetry.

## [3.5.10 (2024-06-20)](https://github.com/kdeldycke/workflows/compare/v3.5.9...v3.5.10)

- Replace Myst admonition in changelog by GFM alerts.

## [3.5.9 (2024-06-20)](https://github.com/kdeldycke/workflows/compare/v3.5.8...v3.5.9)

- Restrict removal of changelog warning admonition to `{important}` class on version bump.

## [3.5.8 (2024-06-20)](https://github.com/kdeldycke/workflows/compare/v3.5.7...v3.5.8)

- Fix dependency graph generation by replacing Poetry by `uv`.

## [3.5.7 (2024-06-05)](https://github.com/kdeldycke/workflows/compare/v3.5.6...v3.5.7)

- Use `uv` to install and run tools.
- Fix markdown autofix.

## [3.5.6 (2024-06-05)](https://github.com/kdeldycke/workflows/compare/v3.5.5...v3.5.6)

- Use `uv` to install `mdformat`.

## [3.5.5 (2024-06-05)](https://github.com/kdeldycke/workflows/compare/v3.5.4...v3.5.5)

- Run Nuitka builds on Python 3.12.
- Auto cleanup PRs produced by awesome template sync job.

## [3.5.4 (2024-05-23)](https://github.com/kdeldycke/workflows/compare/v3.5.3...v3.5.4)

- Fix `mypy` run for Poetry projects.

## [3.5.3 (2024-05-23)](https://github.com/kdeldycke/workflows/compare/v3.5.2...v3.5.3)

- Pin `uv` version everywhere to improve stability.
- Fix `mypy` execution and dependency installation.

## [3.5.2 (2024-05-22)](https://github.com/kdeldycke/workflows/compare/v3.5.1...v3.5.2)

- Install all extra dependencies before checking typing with `mypy`.

## [3.5.1 (2024-05-22)](https://github.com/kdeldycke/workflows/compare/v3.5.0...v3.5.1)

- Requires typing dependencies to be set in a `typing` group in `pyproject.toml`.
- Install all extra dependencies on doc generation.

## [3.5.0 (2024-05-22)](https://github.com/kdeldycke/workflows/compare/v3.4.7...v3.5.0)

- Requires Sphinx dependencies to be set in a `docs` group in `pyproject.toml`.
- Let `pipdeptree` resolve the Python executable to use in a virtual environment.
- Do not let Nuitka assume a Python package is bundled with its unittests in a `tests` subfolder.
- Reduce number of `git` calls to produce `.mailmap`. Refs #984.

## [3.4.7 (2024-04-26)](https://github.com/kdeldycke/workflows/compare/v3.4.6...v3.4.7)

- Update dependencies.

## [3.4.6 (2024-04-18)](https://github.com/kdeldycke/workflows/compare/v3.4.5...v3.4.6)

- Dynamically search the Python executable used by Poetry.

## [3.4.5 (2024-04-18)](https://github.com/kdeldycke/workflows/compare/v3.4.4...v3.4.5)

- Support dependency graph generation for both package and non-package Poetry projects.
- Provides venv's Python to `pipdeptree` to bypass non-detection of active venv.

## [3.4.4 (2024-04-17)](https://github.com/kdeldycke/workflows/compare/v3.4.3...v3.4.4)

- Name is optional for non-`package-mode` Poetry projects.

## [3.4.3 (2024-04-14)](https://github.com/kdeldycke/workflows/compare/v3.4.2...v3.4.3)

- Fix incompatibility between `mdformat-gfm` and `mdformat-pelican`.

## [3.4.2 (2024-04-04)](https://github.com/kdeldycke/workflows/compare/v3.4.1...v3.4.2)

- Fix template URL in `awesome-template-sync` job PR body.

## [3.4.1 (2024-03-19)](https://github.com/kdeldycke/workflows/compare/v3.4.0...v3.4.1)

- Fix variable substitution in `awesome-template-sync` job PR body.

## [3.4.0 (2024-03-18)](https://github.com/kdeldycke/workflows/compare/v3.3.6...v3.4.0)

- Support GitHub admonition in Markdown linting.
- Add new dependency on `mdformat_gfm_alerts`.
- Use pre-commit hooks in `awesome-template-sync` job to replace URLs.
- Source remote requirement files from `uv` CLI.

## [3.3.6 (2024-03-04)](https://github.com/kdeldycke/workflows/compare/v3.3.5...v3.3.6)

- Fix `awesome-template-sync` job.

## [3.3.5 (2024-03-03)](https://github.com/kdeldycke/workflows/compare/v3.3.4...v3.3.5)

- Set `ignore_missing_files` option globally in `pyproject.toml`.
- Remove temporary hack to make `uv` use system Python in workflows.

## [3.3.4 (2024-03-01)](https://github.com/kdeldycke/workflows/compare/v3.3.3...v3.3.4)

- Add some debug messages.

## [3.3.3 (2024-03-01)](https://github.com/kdeldycke/workflows/compare/v3.3.2...v3.3.3)

- Fix updating of existing PR from `awesome-template-sync`.

## [3.3.2 (2024-03-01)](https://github.com/kdeldycke/workflows/compare/v3.3.1...v3.3.2)

- Fix fetching of newly created PR in `awesome-template-sync`.

## [3.3.1 (2024-03-01)](https://github.com/kdeldycke/workflows/compare/v3.3.0...v3.3.1)

- Update repository URLs in `awesome-template-sync` job before re committing the PR.

## [3.3.0 (2024-02-26)](https://github.com/kdeldycke/workflows/compare/v3.2.4...v3.3.0)

- Start collecting `bump-my-version` rules from different projects.
- Move all `*-requirements.txt` files to `requirements` subfolder.
- Remove generation of Pip's `--requirement` parameters in metadata script.
- Reuse `requirements.txt` root file to install dependencies in `mypy-lint` job.
- Add emoji label to awesome template sync PR.

## [3.2.4 (2024-02-24)](https://github.com/kdeldycke/workflows/compare/v3.2.3...v3.2.4)

- Remove labels in `awesome-template-sync` job while we wait for upstream fix.

## [3.2.3 (2024-02-24)](https://github.com/kdeldycke/workflows/compare/v3.2.2...v3.2.3)

- Try to hack `actions-template-sync` labels, again.

## [3.2.2 (2024-02-24)](https://github.com/kdeldycke/workflows/compare/v3.2.1...v3.2.2)

- Try to hack `actions-template-sync` labels.

## [3.2.1 (2024-02-24)](https://github.com/kdeldycke/workflows/compare/v3.2.0...v3.2.1)

- Add label to awesome template sync PR.

## [3.2.0 (2024-02-24)](https://github.com/kdeldycke/workflows/compare/v3.1.0...v3.2.0)

- Add a job to sync awesome repository project from the `awesome-template` repository.

## [3.1.0 (2024-02-18)](https://github.com/kdeldycke/workflows/compare/v3.0.0...v3.1.0)

- Produce `arm64` binaries with Nuitka by using `macos-14` runners.

## [3.0.0 (2024-02-17)](https://github.com/kdeldycke/workflows/compare/v2.26.6...v3.0.0)

- Start replacing `pip` invocations by `uv`.
- Split Python dependencies into several `*requirements.txt` files.
- Let metadata script generates Pip's `--requirement` parameters.
- Add new dependency on `wcmatch` and `uv`.
- Ignore all files from local `.venv/` subfolder.
- Tie Pip cache to `**/pyproject.toml` and `**/*requirements.txt` files.
- Lint and format Jupyter notebooks with ruff.
- Update default ruff config file to new `0.2.x` series.
- Remove installation of unused `bump-my-version` in Git tagging job.
- Document setup and rationale of custom PAT and `*requirements.txt` files.

## [2.26.6 (2024-01-31)](https://github.com/kdeldycke/workflows/compare/v2.26.5...v2.26.6)

- Remove temporary `pyproject.toml` dummy file after ruff invocation not to let it fail due to missing reference.

## [2.26.5 (2024-01-31)](https://github.com/kdeldycke/workflows/compare/v2.26.4...v2.26.5)

- Generate dummy `pyproject.toml` instead of `requirements.txt` everywhere to bypass `setup-python` cache limits for non-Python repositories. Remove the temporary `pyproject.toml` dummy after the fact.

## [2.26.4 (2024-01-30)](https://github.com/kdeldycke/workflows/compare/v2.26.3...v2.26.4)

- Generate a dummy `pyproject.toml` instead of `requirements.txt` to make our ruff local conf work.

## [2.26.3 (2024-01-30)](https://github.com/kdeldycke/workflows/compare/v2.26.2...v2.26.3)

- Fix Python job on non-Python repositories.

## [2.26.2 (2024-01-30)](https://github.com/kdeldycke/workflows/compare/v2.26.1...v2.26.2)

- Fix absence of version in non-Python repositories.

## [2.26.1 (2024-01-30)](https://github.com/kdeldycke/workflows/compare/v2.26.0...v2.26.1)

- Add workaround to allow caching on non-Python repositories.
- Remove hard-coded commit version for `mdformat-gfm`.

## [2.26.0 (2024-01-17)](https://github.com/kdeldycke/workflows/compare/v2.25.0...v2.26.0)

- Replace unmaintained `misspell-fixer` by `typos` to autofix typos. Closes #650.

## [2.25.0 (2024-01-17)](https://github.com/kdeldycke/workflows/compare/v2.24.3...v2.25.0)

- Add a content-based labeller job for issues and PRs.

## [2.24.3 (2024-01-16)](https://github.com/kdeldycke/workflows/compare/v2.24.2...v2.24.3)

- Use `macos-13` instead of `macos-12` for Nuitka builds.

## [2.24.2 (2024-01-06)](https://github.com/kdeldycke/workflows/compare/v2.24.1...v2.24.2)

- Use `bump-my-version` to remove admonition in changelog.

## [2.24.1 (2024-01-06)](https://github.com/kdeldycke/workflows/compare/v2.24.0...v2.24.1)

- Expose current and released version in metadata script.
- Fix fetching of changelog entry for release notes.

## [2.24.0 (2024-01-06)](https://github.com/kdeldycke/workflows/compare/v2.23.0...v2.24.0)

- Add latest changelog entries in GitHub release notes.

## [2.23.0 (2024-01-05)](https://github.com/kdeldycke/workflows/compare/v2.22.0...v2.23.0)

- Produce GitHub release notes dynamically.
- Augment all commits matrix with current version from `bump-my-version`.
- Use new artifact features and scripts.

## [2.22.0 (2024-01-05)](https://github.com/kdeldycke/workflows/compare/v2.21.0...v2.22.0)

- Update default file-based labelling rules for new configuration format.
- Run `autopep8` before `ruff`.

## [2.21.0 (2024-01-04)](https://github.com/kdeldycke/workflows/compare/v2.20.9...v2.21.0)

- Use `ruff` instead of `docformatter` to format docstrings inside Python files.
- Remove dependency on `docformatter`.
- Only run `ruff` once for autofix and linting. Removes `lint-python` job.
- Auto-generate local configuration for `ruff` instead of passing parameters.
- Split generation of Python target version from CLI parameters.
- Rename `black_params` metadata variable to `blacken_docs_params`.
- Remove `ruff_params` metadata variable.

## [2.20.9 (2023-11-13)](https://github.com/kdeldycke/workflows/compare/v2.20.8...v2.20.9)

- Do not cache dependency-less mailmap update workflow step.

## [2.20.8 (2023-11-12)](https://github.com/kdeldycke/workflows/compare/v2.20.7...v2.20.8)

- Cache Python setups.

## [2.20.7 (2023-11-09)](https://github.com/kdeldycke/workflows/compare/v2.20.6...v2.20.7)

- Run Nuitka builds on Python 3.11 while we wait for 3.12 support upstream.

## [2.20.6 (2023-11-05)](https://github.com/kdeldycke/workflows/compare/v2.20.5...v2.20.6)

- Remove hard-coded permissions for release action.

## [2.20.5 (2023-11-05)](https://github.com/kdeldycke/workflows/compare/v2.20.4...v2.20.5)

- Increase scope of hard-coded permissions for release action.
- Use custom token for GitHub release creation.

## [2.20.4 (2023-11-05)](https://github.com/kdeldycke/workflows/compare/v2.20.3...v2.20.4)

- Increase token permissions to full write.

## [2.20.3 (2023-11-05)](https://github.com/kdeldycke/workflows/compare/v2.20.2...v2.20.3)

- Test release action.

## [2.20.2 (2023-11-05)](https://github.com/kdeldycke/workflows/compare/v2.20.1...v2.20.2)

- Increase scope of hard-coded token contents permission.

## [2.20.1 (2023-11-05)](https://github.com/kdeldycke/workflows/compare/v2.20.0...v2.20.1)

- Hard-code token contents permission for creation of GitHub release.

## [2.20.0 (2023-11-05)](https://github.com/kdeldycke/workflows/compare/v2.19.1...v2.20.0)

- Upgrade to `bump-my-version` `0.12.x` series.
- Upgrade to Poetry `1.7.x` series.

## [2.19.1 (2023-10-26)](https://github.com/kdeldycke/workflows/compare/v2.19.0...v2.19.1)

- Activates `ruff` preview and unsafe rules.
- Run actions on Python 3.12.

## [2.19.0 (2023-09-15)](https://github.com/kdeldycke/workflows/compare/v2.18.0...v2.19.0)

- Replace `black` with `ruff`'s autoformatter.
- Rely even more on `bump-my-version` for string replacement.

## [2.18.0 (2023-09-06)](https://github.com/kdeldycke/workflows/compare/v2.17.8...v2.18.0)

- Upgrade to `bump-my-version` `0.10.x` series.
- Remove the step updating the release date of `citation.cff` in `changelog` job. This can be done with `bump-my-version` now.
- Trigger changelog updates on `requirements.txt` changes.

## [2.17.8 (2023-07-16)](https://github.com/kdeldycke/workflows/compare/v2.17.7...v2.17.8)

- Upgrade to `bump-my-version` `0.8.0`.

## [2.17.7 (2023-07-12)](https://github.com/kdeldycke/workflows/compare/v2.17.6...v2.17.7)

- Replace some Perl oneliners with `bump-my-version` invocation.

## [2.17.6 (2023-07-06)](https://github.com/kdeldycke/workflows/compare/v2.17.5...v2.17.6)

- Fix retrieval of tagged version in release workflow.

## [2.17.5 (2023-07-01)](https://github.com/kdeldycke/workflows/compare/v2.17.4...v2.17.5)

- Use bump-my-version `v0.6.0` to fetch current version.

## [2.17.4 (2023-06-22)](https://github.com/kdeldycke/workflows/compare/v2.17.3...v2.17.4)

- Use patched version of `mdformat-web` to fix formatting of HTML code in code blocks.

## [2.17.3 (2023-06-14)](https://github.com/kdeldycke/workflows/compare/v2.17.2...v2.17.3)

- Reactive maximum concurrency in `lychee`, but ignore checks on `twitter.com` and `ycombinator.com`.

## [2.17.2 (2023-06-12)](https://github.com/kdeldycke/workflows/compare/v2.17.1...v2.17.2)

- Limit `lychee` max concurrency and sacrifice performances, to prevent false positives.
- Do not triggers docs workflow on tagging. There is not enough metadata on these events to complete the workflow.
- Skip broken links check on release merge: the tag is created asynchronously which produce false positive reports.

## [2.17.1 (2023-06-12)](https://github.com/kdeldycke/workflows/compare/v2.17.0...v2.17.1)

- Fix parsing of `lychee` exit code.

## [2.17.0 (2023-06-12)](https://github.com/kdeldycke/workflows/compare/v2.16.2...v2.17.0)

- Check and report links with `lychee`. Closes [`#563`](https://github.com/kdeldycke/workflows/issues/563).

## [2.16.2 (2023-06-11)](https://github.com/kdeldycke/workflows/compare/v2.16.1...v2.16.2)

- Use `mdformat_simple_breaks` plugin to format long `<hr>` rules.
- Format bash code blocks in Markdown via `mdformat-shfmt`.
- Install `shfmt` before calling `mdformat`.
- Add dependencies on `mdformat_deflist` and `mdformat_pelican`.

## [2.16.1 (2023-06-10)](https://github.com/kdeldycke/workflows/compare/v2.16.0...v2.16.1)

- Replace long `____(....)____` `<hr>` rule produced by `mdformat` with canonical `---` form. Refs [`executablebooks/mdformat#328`](https://github.com/executablebooks/mdformat/issues/328#issuecomment-1585775337).
- Apply Markdown fixes for awesome lists to localized versions.

## [2.16.0 (2023-06-08)](https://github.com/kdeldycke/workflows/compare/v2.15.2...v2.16.0)

- Replace `bump2version` with `bump-my-version`. Closes [`#162`](https://github.com/kdeldycke/workflows/issues/162).
- Move version bumping configuration from `.bumpversion.cfg` to `pyproject.toml`.
- Cap `mdformat_admon == 1.0.1` to prevent `mdit-py-plugins >= 0.4.0` conflict.

## [2.15.2 (2023-06-04)](https://github.com/kdeldycke/workflows/compare/v2.15.1...v2.15.2)

- Upgrade Nuitka builds to Python 3.11.
- Remove `--no-ansi` option on Poetry calls.

## [2.15.1 (2023-05-22)](https://github.com/kdeldycke/workflows/compare/v2.15.0...v2.15.1)

- Force colorized output of Mypy, as in CI it defaults to no color.
- Only activates all `ruff` rules for autofix, not linting.
- Ignore `D400` rule in `ruff` to allow for docstrings first line finishing with a punctuation other than a period.

## [2.15.0 (2023-05-06)](https://github.com/kdeldycke/workflows/compare/v2.14.1...v2.15.0)

- Fix hard-coding of tagged external asset's URLs on release and version bump.
- Forces `ruff` to check and autofix against all rules.

## [2.14.1 (2023-05-04)](https://github.com/kdeldycke/workflows/compare/v2.14.0...v2.14.1)

- Reverts publishing via trusted channel: it doesn't work with reusable workflows. See #528.

## [2.14.0 (2023-05-04)](https://github.com/kdeldycke/workflows/compare/v2.13.5...v2.14.0)

- Publish packages to PyPi with OIDC workflow for trusted publishing.

## [2.13.5 (2023-05-02)](https://github.com/kdeldycke/workflows/compare/v2.13.4...v2.13.5)

- Update `docformatter`, `ruff` and `nuitka`.

## [2.13.4 (2023-04-23)](https://github.com/kdeldycke/workflows/compare/v2.13.3...v2.13.4)

- Use `docformatter 1.6.2`.

## [2.13.3 (2023-04-22)](https://github.com/kdeldycke/workflows/compare/v2.13.2...v2.13.3)

- Use `docformatter 1.6.1`.

## [2.13.2 (2023-04-07)](https://github.com/kdeldycke/workflows/compare/v2.13.1...v2.13.2)

- Various dependency updates.

## [2.13.1 (2023-04-04)](https://github.com/kdeldycke/workflows/compare/v2.13.0...v2.13.1)

- Use final version of `docformatter 1.6.0`.

## [2.13.0 (2023-03-29)](https://github.com/kdeldycke/workflows/compare/v2.12.4...v2.13.0)

- Update default destination folder of dependency graph from `images` to `assets`.

## [2.12.4 (2023-03-29)](https://github.com/kdeldycke/workflows/compare/v2.12.3...v2.12.4)

- Skip running `autopep8` if no Python files found.
- Only install main dependencies to generate dependency graph.

## [2.12.3 (2023-03-27)](https://github.com/kdeldycke/workflows/compare/v2.12.2...v2.12.3)

- Try out `docformatter 1.6.0-rc7`.

## [2.12.2 (2023-03-07)](https://github.com/kdeldycke/workflows/compare/v2.12.1...v2.12.2)

- Try out `docformatter 1.6.0-rc6`.

## [2.12.1 (2023-03-05)](https://github.com/kdeldycke/workflows/compare/v2.12.0...v2.12.1)

- Tweak extra content layout.

## [2.12.0 (2023-03-05)](https://github.com/kdeldycke/workflows/compare/v2.11.1...v2.12.0)

- Add new `gitignore-extra-content` parameter to `update-gitignore` job to append extra content to `.gitignore`.

## [2.11.1 (2023-03-05)](https://github.com/kdeldycke/workflows/compare/v2.11.0...v2.11.1)

- Fix Mermaid graph rendering colliding with reserved words.

## [2.11.0 (2023-03-03)](https://github.com/kdeldycke/workflows/compare/v2.10.0...v2.11.0)

- Add `certificates`, `gpg` and `ssh` artefacts to the list of default files in `.gitignore`.
- Fix production of dependency graph in Mermaid format.

## [2.10.0 (2023-02-25)](https://github.com/kdeldycke/workflows/compare/v2.9.0...v2.10.0)

- Lint Github actions workflows with `actionlint`.

## [2.9.0 (2023-02-18)](https://github.com/kdeldycke/workflows/compare/v2.8.3...v2.9.0)

- Renders dependency graph in Mermaid Markdown instead of Graphviz's dot.
- Removes `dependency-graph-format` input variable to `docs.yaml` workflow.

## [2.8.3 (2023-02-17)](https://github.com/kdeldycke/workflows/compare/v2.8.2...v2.8.3)

- Test unreleased `docformatter 1.6.0-rc5` to fix link wrapping.
- Create missing parent folders of dependency graph.

## [2.8.2 (2023-02-16)](https://github.com/kdeldycke/workflows/compare/v2.8.1...v2.8.2)

- Fix subtle bug in `.gitignore` production due to collapsing multiline command block starting with `>` because of variable interpolation.
- Tweak PR titles.

## [2.8.1 (2023-02-16)](https://github.com/kdeldycke/workflows/compare/v2.8.0...v2.8.1)

- Test unreleased `docformatter 1.6.0-rc4` to fix admonition wrapping.

## [2.8.0 (2023-02-14)](https://github.com/kdeldycke/workflows/compare/v2.7.6...v2.8.0)

- Replace `isort`, `pyupgrade`, `pylint`, `pycln` and `pydocstyle` with `ruff`.
- Run `autopep8` before `black` to that longline edge-cases get wrapped first.
- Provides `autopep8` with explicit list of Python files to force it to handle dot-prefixed subdirectories.

## [2.7.6 (2023-02-13)](https://github.com/kdeldycke/workflows/compare/v2.7.5...v2.7.6)

- Test-drive unreleased `docformatter 1.6.0-rc3` to fix URL wrapping and admonition edge-cases.

## [2.7.5 (2023-02-12)](https://github.com/kdeldycke/workflows/compare/v2.7.4...v2.7.5)

- Fix collection of artifact files from their folder.

## [2.7.4 (2023-02-12)](https://github.com/kdeldycke/workflows/compare/v2.7.3...v2.7.4)

- Update artifact name to add `-poetry-` suffix for those to be published on PyPi.
- Fix collection of artifact files from their folder.

## [2.7.3 (2023-02-12)](https://github.com/kdeldycke/workflows/compare/v2.7.2...v2.7.3)

- Fix attachment of artifacts to GitHub release on tagging.

## [2.7.2 (2023-02-12)](https://github.com/kdeldycke/workflows/compare/v2.7.1...v2.7.2)

- Remove broken print debug statement.

## [2.7.1 (2023-02-12)](https://github.com/kdeldycke/workflows/compare/v2.7.0...v2.7.1)

- Fix attachment of artifacts to GitHub release on tagging.

## [2.7.0 (2023-02-11)](https://github.com/kdeldycke/workflows/compare/v2.6.2...v2.7.0)

- Add new dependency on `mdformat_footnote` to properly wrap long footnotes when autofixing Markdown.
- Add new dependency on `mdformat_admon` to future-proof upcoming admonition support.
- Add new dependency on `mdformat_pyproject` so that each project reusing the `autofix.yaml` workflow can setup local configuration for `mdformat` via its `pyproject.toml` file.

## [2.6.2 (2023-02-11)](https://github.com/kdeldycke/workflows/compare/v2.6.1...v2.6.2)

- Do not try to attach non-existing artifacts to GitHub release.

## [2.6.1 (2023-02-11)](https://github.com/kdeldycke/workflows/compare/v2.6.0...v2.6.1)

- Fix attachment of artifacts to GitHub release.

## [2.6.0 (2023-02-10)](https://github.com/kdeldycke/workflows/compare/v2.5.1...v2.6.0)

- Rename artifacts attached to each GitHub release to remove the build ID (i.e. the `-build-6f27db4` suffix). That way we can have stable download URLs pointing to the latest release in the form of: `https://github.com/<user_id>/<project_id>/releases/latest/download/<entry_point>-<platform>-<arch>.{bin,exe}`.
- Normalize binary file names produced by Nuitka with `-` (dash) separators.

## [2.5.1 (2023-02-09)](https://github.com/kdeldycke/workflows/compare/v2.5.0...v2.5.1)

- Remove Pip cache, which breaks with our reusable workflows architecture.

## [2.5.0 (2023-02-09)](https://github.com/kdeldycke/workflows/compare/v2.4.3...v2.5.0)

- Cache dependencies installed by Pip.

## [2.4.3 (2023-01-31)](https://github.com/kdeldycke/workflows/compare/v2.4.2...v2.4.3)

- Bump Nuitka to `1.4.1`.

## [2.4.2 (2023-01-27)](https://github.com/kdeldycke/workflows/compare/v2.4.1...v2.4.2)

- Export full Nuitka build matrix from release workflow.

## [2.4.1 (2023-01-27)](https://github.com/kdeldycke/workflows/compare/v2.4.0...v2.4.1)

- Reuse and align commit metadata.
- Fix module path provided to Nuitka.

## [2.4.0 (2023-01-27)](https://github.com/kdeldycke/workflows/compare/v2.3.7...v2.4.0)

- Pre-compute the whole Nuitka build matrix.
- Pre-compute matrix variations with long and short SHA values in commit lists.

## [2.3.7 (2023-01-25)](https://github.com/kdeldycke/workflows/compare/v2.3.6...v2.3.7)

- Change the order of Python auto-formatting pipeline to `pycln` > `isort` > `black` > `blacken-docs` > `autopep8` > `docformatter`.
- Target unreleased `docformatter 1.6.0-rc2` to fix admonition formatting.
- Ignore failing of `docformatter` as `1.6.x` series returns non-zero exit code if files needs to be reformatted.

## [2.3.6 (2023-01-24)](https://github.com/kdeldycke/workflows/compare/v2.3.5...v2.3.6)

- Reverts to skipping the full `1.5.x` series and `1.6.0rc1` of `docformatter` which struggle on long URLs and admonitions.

## [2.3.5 (2023-01-24)](https://github.com/kdeldycke/workflows/compare/v2.3.4...v2.3.5)

- Empty release.

## [2.3.4 (2023-01-24)](https://github.com/kdeldycke/workflows/compare/v2.3.3...v2.3.4)

- Target unreleased `docformatter 1.6.0.rc1` to fix long URL rewrapping. Closes [`#397`](https://github.com/kdeldycke/workflows/issues/397).
- Remove thoroughly all unused imports.

## [2.3.3 (2023-01-21)](https://github.com/kdeldycke/workflows/compare/v2.3.2...v2.3.3)

- Update dependencies.

## [2.3.2 (2023-01-16)](https://github.com/kdeldycke/workflows/compare/v2.3.1...v2.3.2)

- Force refresh of `apt` before installing anything.

## [2.3.1 (2023-01-13)](https://github.com/kdeldycke/workflows/compare/v2.3.0...v2.3.1)

- Force refresh of `apt` before installing `graphviz`.

## [2.3.0 (2023-01-10)](https://github.com/kdeldycke/workflows/compare/v2.2.3...v2.3.0)

- Format python code blocks in documentation files with `blacken-docs`.
- Let metadata script locate Markdown, reStructuredText and Tex files under the `doc_files` field.
- Add new dependency on `blacken-docs`.
- Allow metadata script to be run on non-GitHub environment.

## [2.2.3 (2023-01-09)](https://github.com/kdeldycke/workflows/compare/v2.2.2...v2.2.3)

- Re-parse dependency graph to stabilize its output, customize its style and make it deterministic.
- Unpin dependency on `yamllint` and depends on latest version.

## [2.2.2 (2023-01-09)](https://github.com/kdeldycke/workflows/compare/v2.2.1...v2.2.2)

- Fix default dependency graph extension.

## [2.2.1 (2023-01-09)](https://github.com/kdeldycke/workflows/compare/v2.2.0...v2.2.1)

- Fix inplace customization of dependency graph.

## [2.2.0 (2023-01-09)](https://github.com/kdeldycke/workflows/compare/v2.1.1...v2.2.0)

- Change the default dependency graph format from `PNG` to `dot` file.
- Add a `dependency-graph-format` parameter to the documentation workflow.
- Customize the style of dependency graph when Graphviz code is produced.
- Install Graphviz when we produce the documentation so we can use `sphinx.ext.graphviz` plugin.
- Add list of projects relying on these scripts.

## [2.1.1 (2022-12-30)](https://github.com/kdeldycke/workflows/compare/v2.1.0...v2.1.1)

- Fix fetching of commit matrix.

## [2.1.0 (2022-12-30)](https://github.com/kdeldycke/workflows/compare/v2.0.6...v2.1.0)

- Rewrite new and release commit detection code from YAML to Python.
- Add dependency on `PyDriller`.
- Trigger debug traces on `pull_request` events.

## [2.0.6 (2022-12-29)](https://github.com/kdeldycke/workflows/compare/v2.0.5...v2.0.6)

- Fix export of binary name from build workflow.

## [2.0.5 (2022-12-29)](https://github.com/kdeldycke/workflows/compare/v2.0.4...v2.0.5)

- Export binary name from build workflow.

## [2.0.4 (2022-12-27)](https://github.com/kdeldycke/workflows/compare/v2.0.3...v2.0.4)

- Fix skipping of Nuitka compiling step for projects without entry points.
- Skip the whole `1.5.x` series of `docformatter` which struggles with long URLs.

## [2.0.3 (2022-12-26)](https://github.com/kdeldycke/workflows/compare/v2.0.2...v2.0.3)

- Fix fetching of absent entry points in project metadata.

## [2.0.2 (2022-12-19)](https://github.com/kdeldycke/workflows/compare/v2.0.1...v2.0.2)

- Fix uploading of artifacts to GitHub release on tagging.

## [2.0.1 (2022-12-19)](https://github.com/kdeldycke/workflows/compare/v2.0.0...v2.0.1)

- Use short SHA commit in build artifacts.
- Fix uploading of Nuitka binaries to GitHub release on tagging.

## [2.0.0 (2022-12-17)](https://github.com/kdeldycke/workflows/compare/v1.10.0...v2.0.0)

- Add Nuitka-based compiling of Poetry's script entry-points into standalone binaries for Linux, macOS and Windows.
- Upload binaries to GitHub releases on tagging.
- Extract Poetry script entry-points in Python metadata script.
- Produce Nuitka-specific main module path from script entry-points.
- Allow rendering of data structure in JSON for inter-job outputs.
- Print Python metadata output before writing to env for debugging.
- Add dependency on `nuitka`, `ordered-set` and `zstandard`.

## [1.10.0 (2022-12-02)](https://github.com/kdeldycke/workflows/compare/v1.9.2...v1.10.0)

- Run all Python-based workflows on 3.11.

## [1.9.2 (2022-11-14)](https://github.com/kdeldycke/workflows/compare/v1.9.1...v1.9.2)

- Fix production of multiline commit list in build and release workflow.

## [1.9.1 (2022-11-12)](https://github.com/kdeldycke/workflows/compare/v1.9.0...v1.9.1)

- Fix tagging.

## [1.9.0 (2022-11-12)](https://github.com/kdeldycke/workflows/compare/v1.8.9...v1.9.0)

- Remove use of deprecated `::set-output` directives and replace them by environment files.

## [1.8.9 (2022-11-09)](https://github.com/kdeldycke/workflows/compare/v1.8.8...v1.8.9)

- Install project with Poetry before generating a dependency graph.

## [1.8.8 (2022-11-09)](https://github.com/kdeldycke/workflows/compare/v1.8.7...v1.8.8)

- Update all dependencies.

## [1.8.7 (2022-09-26)](https://github.com/kdeldycke/workflows/compare/v1.8.6...v1.8.7)

- Allow the use of project's own Mypy in Poetry virtual environment to benefits from typeshed dependencies.

## [1.8.6 (2022-09-23)](https://github.com/kdeldycke/workflows/compare/v1.8.5...v1.8.6)

- Do not let `sphinx-apidoc` CLI produce ToC file.

## [1.8.5 (2022-09-19)](https://github.com/kdeldycke/workflows/compare/v1.8.4...v1.8.5)

- Print raw `pipdeptree` output for debug.

## [1.8.4 (2022-09-19)](https://github.com/kdeldycke/workflows/compare/v1.8.3...v1.8.4)

- Fix installation of `graphviz` dependency in Poetry venv.

## [1.8.3 (2022-09-19)](https://github.com/kdeldycke/workflows/compare/v1.8.2...v1.8.3)

- Run `pipdeptree` in Poetry venv to produce dependency graph.

## [1.8.2 (2022-09-18)](https://github.com/kdeldycke/workflows/compare/v1.8.1...v1.8.2)

- Fix workflow continuation on successful `pyupgrade` run.
- Fix quoting of CLI parameters fed to `black`.

## [1.8.1 (2022-09-18)](https://github.com/kdeldycke/workflows/compare/v1.8.0...v1.8.1)

- Fix version setup in Python metadata script.

## [1.8.0 (2022-09-08)](https://github.com/kdeldycke/workflows/compare/v1.7.5...v1.8.0)

- Upgrade to `poetry` 1.2.0.
- Allow dependency graph to be continuously updated. Closes [`#176`](https://github.com/kdeldycke/workflows/issues/176).
- In Python project metadata fetcher, double-quote file list's items to allow use of path with spaces in workflows.
- Ignore broken symlinks pointing to non-existing files in Python metadata fetcher.
- Fix default `pyupgrade` option produced by new Poetry.

## [1.7.5 (2022-08-25)](https://github.com/kdeldycke/workflows/compare/v1.7.4...v1.7.5)

- Use stable release of `calibreapp/image-actions`.

## [1.7.4 (2022-08-06)](https://github.com/kdeldycke/workflows/compare/v1.7.3...v1.7.4)

- Fix `mypy` parameters passing.
- Upgrade job runs from `ubuntu-20.04` to `ubuntu-22.04`.

## [1.7.3 (2022-08-06)](https://github.com/kdeldycke/workflows/compare/v1.7.2...v1.7.3)

- Fix `mypy` parameters passing.

## [1.7.2 (2022-08-06)](https://github.com/kdeldycke/workflows/compare/v1.7.1...v1.7.2)

- Skip Python-specific jobs early if no Python files found in repository.
- Allow execution of `pyupgrade` on non-Poetry-based projects.
- Default `pyupgrade` parameter to `--py3-plus`.
- Use auto-generated parameter for `mypy`'s minimal Python version.
- Merge all Poetry and Sphinx metadata fetching into a Python script, as we cannot have reusable workflows use reusable workflows. Closes #160.

## [1.7.1 (2022-08-05)](https://github.com/kdeldycke/workflows/compare/v1.7.0...v1.7.1)

- Add direct dependency on `poetry`.

## [1.7.0 (2022-08-05)](https://github.com/kdeldycke/workflows/compare/v1.6.2...v1.7.0)

- Auto-generate the set of python minimal version parameters for `mypy`, `black` and `pyupgrade`. Addresses [`python/mypy#13294`](https://github.com/python/mypy/issues/13294), [`psf/black#3124`](https://github.com/psf/black/issues/3124) and [`asottile/pyupgrade#688`](https://github.com/asottile/pyupgrade/issues/688).

## [1.6.2 (2022-07-31)](https://github.com/kdeldycke/workflows/compare/v1.6.1...v1.6.2)

- Remove upper limit of `pyupgrade` automatic `--py3XX-plus` option generation.
- Allow `gitleaks` to use GitHub token to scan PRs.

## [1.6.1 (2022-07-05)](https://github.com/kdeldycke/workflows/compare/v1.6.0...v1.6.1)

- Keep the release date of `citation.cff` up-to-date in `changelog` job.

## [1.6.0 (2022-07-01)](https://github.com/kdeldycke/workflows/compare/v1.5.1...v1.6.0)

- Check for typing. Add dependency on `mypy`.

## [1.5.1 (2022-06-25)](https://github.com/kdeldycke/workflows/compare/v1.5.0...v1.5.1)

- Revert workflow concurrency logic.

## [1.5.0 (2022-06-23)](https://github.com/kdeldycke/workflows/compare/v1.4.2...v1.5.0)

- Auto-remove unused imports in Python code. Add dependency on `pycln`.
- Freeze Python version used to run all code to the `3.10` series.

## [1.4.2 (2022-05-22)](https://github.com/kdeldycke/workflows/compare/v1.4.1...v1.4.2)

- Group workflow jobs so new commits cancels in-progress execution triggered by previous commits.
- Reduce minimal Pylint success score to `7.0/10`.

## [1.4.1 (2022-04-16)](https://github.com/kdeldycke/workflows/compare/v1.4.0...v1.4.1)

- Fix admonition rendering in changelog template.

## [1.4.0 (2022-04-16)](https://github.com/kdeldycke/workflows/compare/v1.3.1...v1.4.0)

- Use `autopep8` to wrap Python comments at 88 characters length.

## [1.3.1 (2022-04-16)](https://github.com/kdeldycke/workflows/compare/v1.3.0...v1.3.1)

- Bump `actions/checkout` action to fix run in containers jobs.

## [1.3.0 (2022-04-13)](https://github.com/kdeldycke/workflows/compare/v1.2.1...v1.3.0)

- Auto-format docstrings in Python files. Add dependency on `docformatter`.
- Auto-format `JS`, `CSS`, `HTML` and `XML` code blocks in Markdown files. Add
  dependency on `mdformat-web`.
- Lint Python docstrings. Add dependency on `pydocstyle`.
- Use `isort` profile to aligns with `black`. Removes `.isort.cfg`.
- Tweak `🙏 help wanted` label description.

## [1.2.1 (2022-04-12)](https://github.com/kdeldycke/workflows/compare/v1.2.0...v1.2.1)

- Fix Sphinx auto-detection by relying on static syntax analyzer instead of
  trying to import the executable configuration.

## [1.2.0 (2022-04-11)](https://github.com/kdeldycke/workflows/compare/v1.1.0...v1.2.0)

- Detect Sphinx's `autodoc` extension to create a PR updating documentation.
- Auto deploy Sphinx documentation on GitHub pages if detected.
- Update `ℹ️ help wanted` label to `🙏 help wanted`.
- Triggers `docs` workflow on tagging to fix dependency graph generation.
- Allows `release` workflow to be re-launched on tagging error.

## [1.1.0 (2022-03-30)](https://github.com/kdeldycke/workflows/compare/v1.0.1...v1.1.0)

- Dynamically add `⚖️ curation`, `🆕 new link` and `🩹 fix link` labels on
  awesome list projects.

## [1.0.1 (2022-03-30)](https://github.com/kdeldycke/workflows/compare/v1.0.0...v1.0.1)

- Remove the title of the section containing the TOC in awesome lists to fix
  the linter.

## [1.0.0 (2022-03-30)](https://github.com/kdeldycke/workflows/compare/v0.9.1...v1.0.0)

- Lint awesome list repositories.
- Update `👷 CI/CD` label to `🤖 ci`.
- Update `📗 documentation` label to` 📚 documentation`.
- Update `🔄 duplicate` label to `🧑‍🤝‍🧑 duplicate`.
- Update `🆕 feature request` label to `🎁 feature request`.
- Update `❓ question` label to `❔ question`.
- Let Pylint discover Python files and modules to lint.
- Do not generate a `.gitignore` or `.mailmap` if none exist. Only update it.
- Do not run the daily `prepare-release` job to reduce the number of
  notifications. Add instructions on PR on how to refresh it.
- Auto-update TOC in Markdown. Add dependency on `mdformat-toc`.
- Remove forbidden TOC entries in Markdown for awesome lists.
- Remove wrapping of Markdown files to 79 characters.
- Use the `tomllib` from the standard library starting with Python 3.11.

## [0.9.1 (2022-03-09)](https://github.com/kdeldycke/workflows/compare/v0.9.0...v0.9.1)

- Fix search of Python files in `lint-python` workflow.

## [0.9.0 (2022-03-09)](https://github.com/kdeldycke/workflows/compare/v0.8.6...v0.9.0)

- Add Zsh script linter.
- Search for leaked tokens and credentials in code.
- Add new `💣 security` label.
- Adjust `🐛 bug` label color.
- Add new `gitignore-location` and `gitignore-extra-categories` parameters to
  `update-gitignore` workflow.
- Fix usage of default values of reused workflows which are called naked. In
  which case they're not fed with the default from input's definition.

## [0.8.6 (2022-03-04)](https://github.com/kdeldycke/workflows/compare/v0.8.5...v0.8.6)

- Reactivate sponsor auto-tagging workflow now that it has been fixed upstream.

## [0.8.5 (2022-03-02)](https://github.com/kdeldycke/workflows/compare/v0.8.4...v0.8.5)

- Update dependencies.

## [0.8.4 (2022-02-21)](https://github.com/kdeldycke/workflows/compare/v0.8.3...v0.8.4)

- Replace hard-coded PyPi package link in GitHub release text with dynamic
  value from Poetry configuration.

## [0.8.3 (2022-02-13)](https://github.com/kdeldycke/workflows/compare/v0.8.2...v0.8.3)

- Allow the location of the dependency graph image to be set with the
  `dependency-graph-output` parameter for reused workflow.

## [0.8.2 (2022-02-13)](https://github.com/kdeldycke/workflows/compare/v0.8.1...v0.8.2)

- Fix generation of `pyupgrade` Python version parameter.

## [0.8.1 (2022-02-13)](https://github.com/kdeldycke/workflows/compare/v0.8.0...v0.8.1)

- Fix installation of `tomli` dependency for dependency graph generation.
- Fix installation of Poetry in Python modernization workflow.

## [0.8.0 (2022-02-13)](https://github.com/kdeldycke/workflows/compare/v0.7.25...v0.8.0)

- Add new workflow proposing PRs to modernize Python code for Poetry-based
  projects.
- Add new workflow to produce dependency graph of Poetry-based project.
- Auto-detect minimal Python version targeted by Poetry projects.
- Add dependency on `pipdeptree`, `pyupgrade` and `tomli`.

## [0.7.25 (2022-01-16)](https://github.com/kdeldycke/workflows/compare/v0.7.24...v0.7.25)

- Fix fetching of new commits in PRs.

## [0.7.24 (2022-01-15)](https://github.com/kdeldycke/workflows/compare/v0.7.23...v0.7.24)

- Fix upload of build artifacts in GitHub release.

## [0.7.23 (2022-01-15)](https://github.com/kdeldycke/workflows/compare/v0.7.22...v0.7.23)

- Fix use of token for Git tagging.

## [0.7.22 (2022-01-15)](https://github.com/kdeldycke/workflows/compare/v0.7.21...v0.7.22)

- Generate list of all new and release commits in the first job of the release
  workflow.

## [0.7.21 (2022-01-13)](https://github.com/kdeldycke/workflows/compare/v0.7.20...v0.7.21)

- Fix regex matching the release commit.

## [0.7.20 (2022-01-13)](https://github.com/kdeldycke/workflows/compare/v0.7.19...v0.7.20)

- Refactor release workflow to rely on a new matrix-based multi-commit
  detection strategy.
- Trigger tagging by monitoring `main` branch commit messages instead of
  `prepare-release` PR merge event.
- Upload build artifacts for each commit.
- Fix addition of PyPi link in GitHub release content.

## [0.7.19 (2022-01-11)](https://github.com/kdeldycke/workflows/compare/v0.7.18...v0.7.19)

- Secret token need to be passed explicitly in reused workflow for PyPi
  publishing.

## [0.7.18 (2022-01-11)](https://github.com/kdeldycke/workflows/compare/v0.7.17...v0.7.18)

- Add version in the name of built artifacts.

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

- Do not try to fetch build artifacts if the publishing step has been skipped.
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
- Add build artifacts to GitHub releases.

## [0.6.3 (2022-01-09)](https://github.com/kdeldycke/workflows/compare/v0.6.2...v0.6.3)

- Skip labelling on `prepare-release` branch.
- Skip version increment updates on release commits.
- Tighten up changelog job's trigger conditions.

## [0.6.2 (2022-01-09)](https://github.com/kdeldycke/workflows/compare/v0.6.1...v0.6.2)

- Fix generation of file-based labelling rules.

## [0.6.1 (2022-01-08)](https://github.com/kdeldycke/workflows/compare/v0.6.0...v0.6.1)

- Fix extension of default labelling rules.

## [0.6.0 (2022-01-08)](https://github.com/kdeldycke/workflows/compare/v0.5.5...v0.6.0)

- Add a reusable workflow to automatically label issues and PRs depending on
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

- Add a reusable workflow to maintain GitHub labels.
- Add a set of default emoji-based labels.
- Add dedicated `changelog`, `sponsor` and `dependencies` labels.
- Update `CI/CD` label icon.
- Auto-tag issues and PRs opened by sponsors.
- Allow for sourcing of additional labels when reusing workflow.

## [0.4.8 (2022-01-04)](https://github.com/kdeldycke/workflows/compare/v0.4.7...v0.4.8)

- Use more recent `calibreapp/image-actions` action.
- Remove unused custom variable for reusable GitHub release job.

## [0.4.7 (2022-01-04)](https://github.com/kdeldycke/workflows/compare/v0.4.6...v0.4.7)

- Fix use of GitHub token for workflow auto-updates on release.
- Allow typo autofix job to propose changes in workflow files.

## [0.4.6 (2022-01-04)](https://github.com/kdeldycke/workflows/compare/v0.4.5...v0.4.6)

- Let GitHub release produced on tagging to be customized with user's content
  and uploaded files.
- Expose tagged version from reusable `release` workflow.

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

- Allow changelog and release workflows to be reusable.

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
- Fix `autofix` workflow reusability.

## [0.3.1 (2021-12-23)](https://github.com/kdeldycke/workflows/compare/v0.3.0...v0.3.1)

- Hard-code tagged version for executed Python script.
- Activate debugging workflow on all branches and PRs.
- Allows debug workflow to be reused.

## [0.3.0 (2021-12-16)](https://github.com/kdeldycke/workflows/compare/v0.2.0...v0.3.0)

- Add a reusable workflow to fix typos.
- Add a reusable workflow to optimize images.
- Add a reusable workflow to auto-format Python files with isort and Black.
- Add a reusable workflow to auto-format Markdown files with mdformat.
- Add a reusable workflow to auto-format JSON files with `jsonlint`.
- Add a reusable workflow to auto-update .gitignore file.
- Add a reusable workflow to auto-update .mailmap file.
- Force retargeting of workflow dependencies to `main` branch on post-release
  version bump.

## [0.2.0 (2021-12-15)](https://github.com/kdeldycke/workflows/compare/v0.1.0...v0.2.0)

- Add autolock reusable workflow for closed issues and PRs.
- Automate changelog and version management.
- Add workflow to create ready-to-use PRs to prepare a release, post-release
  version bump and minor & major version increments.
- Add a debug workflow to print action context and environment variables.
- Set Pylint failure threshold at 80%.

## [0.1.0 (2021-12-12)](https://github.com/kdeldycke/workflows/compare/v0.0.1...v0.1.0)

- Install project with Poetry before calling Pylint if `pyproject.toml`
  presence is detected.
- Hard-code tagged version in requirement URL for reusable workflows.
- Document the release process.

## [0.0.1 (2021-12-11)](https://github.com/kdeldycke/workflows/compare/5cbdbb...v0.0.1)

- Initial public release.
