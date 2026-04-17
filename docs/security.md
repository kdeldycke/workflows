# {octicon}`shield-lock` Security

## Supply chain security

`repomatic` implements most of the practices described in Astral's [Open Source Security at Astral](https://astral.sh/blog/open-source-security-at-astral) post, baked into a drop-in setup that any maintainer can inherit by pointing their workflows at the reusable callers.

| Astral practice                                                | How `repomatic` covers it                                                                                                                                                                                                                                                                                                                                                                   |
| :------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Ban dangerous triggers (`pull_request_target`, `workflow_run`) | The [lint-workflow-security](workflows.md#github-workflows-lint-yaml-jobs) job runs [`zizmor`](https://docs.zizmor.sh) on every push: see [`.github/workflows/lint.yaml`](https://github.com/kdeldycke/repomatic/blob/main/.github/workflows/lint.yaml)                                                                                                                                     |
| Minimal workflow permissions                                   | [`check_workflow_permissions`](https://github.com/kdeldycke/repomatic/blob/main/repomatic/lint_repo.py) parses every workflow file and warns when a custom-step workflow omits the top-level `permissions` key                                                                                                                                                                              |
| Pinned actions                                                 | All `uses:` refs pinned to full commit SHAs (with the semver tag preserved as a trailing comment) via Renovate's [`helpers:pinGitHubActionDigestsToSemver`](https://docs.renovatebot.com/presets-helpers/#helperspingithubactiondigeststosemver) preset: see [`renovate.json5`](https://github.com/kdeldycke/repomatic/blob/main/renovate.json5)                                            |
| No force-pushes to `main`                                      | [`check_branch_ruleset_on_default`](https://github.com/kdeldycke/repomatic/blob/main/repomatic/lint_repo.py) verifies an active branch ruleset exists, and the [setup guide](https://github.com/kdeldycke/repomatic/blob/main/repomatic/templates/setup-guide-branch-ruleset.md) walks users through creating one                                                                           |
| Immutable release tags                                         | [`check_immutable_releases`](https://github.com/kdeldycke/repomatic/blob/main/repomatic/lint_repo.py) verifies [GitHub immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases) is enabled, and the release workflow rewrites `@main` refs to `@vX.Y.Z` during freeze: see [tagged workflow URLs](workflows.md#tagged-workflow-urls) |
| Dependency cooldowns                                           | Renovate stabilization windows (`minimumReleaseAge`) and `uv --exclude-newer`, with a per-package escape hatch for CVE fixes: see [`renovate.json5`](https://github.com/kdeldycke/repomatic/blob/main/renovate.json5) and [Renovate cooldowns](workflows.md#renovate-cooldowns)                                                                                                             |
| Trusted Publishing                                             | PyPI uploads via `uv publish` with no long-lived token: see the [`publish-pypi`](workflows.md#github-workflows-release-yaml-jobs) job in [`.github/workflows/release.yaml`](https://github.com/kdeldycke/repomatic/blob/main/.github/workflows/release.yaml)                                                                                                                                |
| Cryptographic attestations                                     | Every binary and wheel is attested to the workflow run that built it via `attest-build-provenance`: see the `Generate build attestations` steps in [`.github/workflows/release.yaml`](https://github.com/kdeldycke/repomatic/blob/main/.github/workflows/release.yaml)                                                                                                                      |
| Checksums in installer scripts                                 | The [`update-checksums`](https://github.com/kdeldycke/repomatic/blob/main/repomatic/cli.py) CLI command regenerates SHA-256 checksums on every release, invoked from [`.github/workflows/renovate.yaml`](https://github.com/kdeldycke/repomatic/blob/main/.github/workflows/renovate.yaml) when upstream action versions change                                                             |
| Fork PR approval policy                                        | [`check_fork_pr_approval_policy`](https://github.com/kdeldycke/repomatic/blob/main/repomatic/lint_repo.py) warns when the policy is weaker than `first_time_contributors`, and the [setup guide](https://github.com/kdeldycke/repomatic/blob/main/repomatic/templates/setup-guide-fork-pr-approval.md) ships a pre-filled `gh api` one-liner to fix it                                      |

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
> For implementation details on how concurrency groups are computed and why `release.yaml` needs special handling, see the [`repomatic.github.actions`](repomatic.github.html#module-repomatic.github.actions) module docstring.

## AV false-positive submissions

Compiled Python binaries (built with [Nuitka](https://nuitka.net/) `--onefile`) are frequently flagged as malicious by heuristic AV engines. The onefile packaging technique (self-extracting archive with embedded Python runtime) triggers generic "packed/suspicious" signatures. This is a known issue across the Nuitka ecosystem.

The [`scan-virustotal`](workflows.md#github-workflows-release-yaml-jobs) job in `release.yaml` uploads all compiled binaries to [VirusTotal](https://www.virustotal.com/) on every release. This seeds AV vendor databases to reduce false positive rates for downstream distributors (Chocolatey, Scoop, etc.).

When a release is flagged, the `/av-false-positive` [skill](skills.md) generates per-vendor submission files with pre-written text and form field mappings. The vendor details below document the process for manual reference.

### Vendor portals

| Vendor      | Engines covered                                                                     | Portal                                                                                                | Format                                                                             | Turnaround             |
| :---------- | :---------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------- | :--------------------- |
| Microsoft   | `Microsoft`                                                                         | [WDSI file submission](https://www.microsoft.com/en-us/wdsi/filesubmission?persona=SoftwareDeveloper) | One file per form, 1900 char limit on additional info                              | Fastest                |
| BitDefender | `BitDefender`, `ALYac`, `Arcabit`, `Emsisoft`, `GData`, `MicroWorld-eScan`, `VIPRE` | [bitdefender.com/submit](https://www.bitdefender.com/submit/)                                         | One file per form, screenshot mandatory                                            | Fast                   |
| ESET        | `ESET-NOD32`                                                                        | Email to `samples@eset.com`                                                                           | Single email, password-protected ZIP (`infected`), ~24 MB limit                    | Reliable               |
| Symantec    | `Symantec`                                                                          | [symsubmit.symantec.com](https://symsubmit.symantec.com/false_positive)                               | Hash submission only (no `.exe`/`.bin` upload), one hash per form, 5000 char limit | 3-7 business days      |
| Avast/AVG   | `Avast`, `AVG`                                                                      | [avast.com/submit-a-sample](https://www.avast.com/submit-a-sample)                                    | One file per form, shared engine                                                   | Medium                 |
| Sophos      | `Sophos`                                                                            | [sophos.com filesubmission](https://support.sophos.com/support/s/filesubmission)                      | One file per form, 25 MB max per submission                                        | Up to 15 business days |

### Submission priority

Submit in this order to maximize impact:

1. **Microsoft**: most influential engine. ML detections (`Sabsik`, `Wacatac`) have the broadest downstream effect.
2. **BitDefender**: powers ~6 downstream vendor engines. Highest detection-removal-per-submission ratio.
3. **ESET**: email-based channel with no portal dependency. The most reliable submission path.
4. **Symantec**: ML detections (`ML.Attribute.*`) may take longer to process.
5. **Avast/AVG**: shared engine, so one submission covers both.
6. **Sophos**: PUA detections require justification of the software's legitimate purpose.

### Submission content

Every false-positive submission should include:

- The binary's VirusTotal report link.
- VirusTotal links for the clean `.whl` and `.tar.gz` source distributions (as comparison evidence).
- The GitHub release link and direct download URL for the binary.
- Project homepage and PyPI URL.
- License from `pyproject.toml`.
- Reference to any prior false-positive issue in the repository.

All submission text should mention that the binary is compiled with Nuitka `--onefile` from an open-source project.

### Known portal issues

- **Microsoft**: CORS errors or stuck progress modals during upload (auth session expiring). Workaround: sign out, clear cookies for `microsoft.com`, sign back in, submit immediately.
- **BitDefender**: form sometimes returns "Your request could not be registered!" with no details. Retry later.
- **Avast**: form sometimes returns "An internal error occurred while sending the form." Retry later.
