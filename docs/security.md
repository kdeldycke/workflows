# {octicon}`shield-lock` Security

## Supply chain security

`repomatic` implements most of the practices described in Astral's [Open Source Security at Astral](https://astral.sh/blog/open-source-security-at-astral) post, baked into a drop-in setup that any maintainer can inherit by pointing their workflows at the reusable callers.

| Astral practice                                                | How `repomatic` covers it                                                                                                                                                                                                                                                                                                                                                         |
| :------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Ban dangerous triggers (`pull_request_target`, `workflow_run`) | The [lint-workflow-security](workflows.md#github-workflows-lint-yaml-jobs) job runs [`zizmor`](https://docs.zizmor.sh) on every push: see [`.github/workflows/lint.yaml`](https://github.com/kdeldycke/repomatic/blob/main/.github/workflows/lint.yaml)                                                                                                                               |
| Minimal workflow permissions                                   | [`check_workflow_permissions`](https://github.com/kdeldycke/repomatic/blob/main/repomatic/lint_repo.py) parses every workflow file and warns when a custom-step workflow omits the top-level `permissions` key                                                                                                                                                                    |
| Pinned actions                                                 | All `uses:` refs pinned to full commit SHAs (with the semver tag preserved as a trailing comment) via Renovate's [`helpers:pinGitHubActionDigestsToSemver`](https://docs.renovatebot.com/presets-helpers/#helperspingithubactiondigeststosemver) preset: see [`renovate.json5`](https://github.com/kdeldycke/repomatic/blob/main/renovate.json5)                                  |
| No force-pushes to `main`                                      | [`check_branch_ruleset_on_default`](https://github.com/kdeldycke/repomatic/blob/main/repomatic/lint_repo.py) verifies an active branch ruleset exists, and the [setup guide](https://github.com/kdeldycke/repomatic/blob/main/repomatic/templates/setup-guide-branch-ruleset.md) walks users through creating one                                                                 |
| Immutable release tags                                         | [`check_immutable_releases`](https://github.com/kdeldycke/repomatic/blob/main/repomatic/lint_repo.py) verifies [GitHub immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases) is enabled, and the release workflow rewrites `@main` refs to `@vX.Y.Z` during freeze: see [tagged workflow URLs](workflows.md#tagged-workflow-urls) |
| Dependency cooldowns                                           | Renovate stabilization windows (`minimumReleaseAge`) and `uv --exclude-newer`, with a per-package escape hatch for CVE fixes: see [`renovate.json5`](https://github.com/kdeldycke/repomatic/blob/main/renovate.json5) and [Renovate cooldowns](workflows.md#renovate-cooldowns)                                                                                                   |
| Trusted Publishing                                             | PyPI uploads via `uv publish` with no long-lived token: see the [`publish-pypi`](workflows.md#github-workflows-release-yaml-jobs) job in [`.github/workflows/release.yaml`](https://github.com/kdeldycke/repomatic/blob/main/.github/workflows/release.yaml)                                                                                                                         |
| Cryptographic attestations                                     | Every binary and wheel is attested to the workflow run that built it via `attest-build-provenance`: see the `Generate build attestations` steps in [`.github/workflows/release.yaml`](https://github.com/kdeldycke/repomatic/blob/main/.github/workflows/release.yaml)                                                                                                            |
| Checksums in installer scripts                                 | The [`update-checksums`](https://github.com/kdeldycke/repomatic/blob/main/repomatic/cli.py) CLI command regenerates SHA-256 checksums on every release, invoked from [`.github/workflows/renovate.yaml`](https://github.com/kdeldycke/repomatic/blob/main/.github/workflows/renovate.yaml) when upstream action versions change                                                   |
| Fork PR approval policy                                        | [`check_fork_pr_approval_policy`](https://github.com/kdeldycke/repomatic/blob/main/repomatic/lint_repo.py) warns when the policy is weaker than `first_time_contributors`, and the [setup guide](https://github.com/kdeldycke/repomatic/blob/main/repomatic/templates/setup-guide-fork-pr-approval.md) ships a pre-filled `gh api` one-liner to fix it                            |

> [!WARNING]
> **Known gap: multi-person release approval.** Astral gates releases behind a dedicated [GitHub deployment environment](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/reviewing-deployments) with required reviewers, so that a single compromised account cannot publish. `repomatic` does not enforce this, but if the repository has multiple maintainers, I recommend adding an `environment: release` key to the `publish-pypi` and `create-release` jobs in a downstream caller workflow and configuring required reviewers on that environment in repo settings.

## Permissions and token

Several workflows need a `REPOMATIC_PAT` secret to create PRs that modify files in `.github/workflows/` and to trigger downstream workflows. Without it, those jobs silently fall back to the default `GITHUB_TOKEN`, which lacks the required permissions.

After your first push, the [`setup-guide` job](workflows.md#github-workflows-autofix-yaml-jobs) automatically opens an issue with [step-by-step instructions](https://github.com/kdeldycke/repomatic/blob/main/repomatic/templates/setup-guide.md) to create and configure the token.

## Concurrency and cancellation

All workflows use a `concurrency` directive to prevent redundant runs and save CI resources. When a new commit is pushed, any in-progress workflow runs for the same branch or PR are automatically cancelled.

Workflows are grouped by:

- **Pull requests**: `{workflow-name}-{pr-number}` — Multiple commits to the same PR cancel previous runs
- **Branch pushes**: `{workflow-name}-{branch-ref}` — Multiple pushes to the same branch cancel previous runs

`release.yaml` uses a stronger protection: release commits get a **unique concurrency group** based on the commit SHA, so they can never be cancelled. This ensures tagging, PyPI publishing, and GitHub release creation complete successfully.

Additionally, [`cancel-runs.yaml`](workflows.md#github-workflows-cancel-runs-yaml-jobs) actively cancels in-progress and queued runs when a PR is closed. This complements passive concurrency groups, which only trigger cancellation when a *new* run enters the same group — closing a PR doesn't produce such an event.

> [!TIP]
> For implementation details on how concurrency groups are computed and why `release.yaml` needs special handling, see [`claude.md` § Concurrency implementation](https://github.com/kdeldycke/repomatic/blob/main/claude.md#concurrency-implementation).
