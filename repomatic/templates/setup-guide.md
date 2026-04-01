---
args: [repo_url, repo_name, repo_owner, repo_slug, immutable_releases_step, org_tip, missing_permissions_section]
---

\$missing_permissions_section

Some workflows need a **fine-grained personal access token** to create PRs that update files in `.github/workflows/`. Without it, those jobs will silently fail.

### Step 1: Create the token

1. Open the [**pre-filled token form**](https://github.com/settings/personal-access-tokens/new?name=$repo_name-repomatic&description=REPOMATIC_PAT+for+$repo_owner/$repo_name&target_name=$repo_owner&contents=write&issues=write&metadata=read&pull_requests=write&statuses=write&vulnerability_alerts=read&workflows=write) (or go to **GitHub → Settings → Developer Settings → [Fine-grained tokens](https://github.com/settings/personal-access-tokens)** and click **Generate new token**).

2. Review the pre-filled **Token name** (`$repo_name-repomatic`).

3. Under **Repository access**, select **Only select repositories** and pick **\$repo_name**. Do not grant access to other repositories.

4. Verify these permissions (pre-filled by the link above):

   | Permission            | Access                  | Reason                                                                                    |
   | :-------------------- | :---------------------- | :---------------------------------------------------------------------------------------- |
   | **Commit statuses**   | Read and Write          | Renovate `stability-days` status checks                                                   |
   | **Contents**          | Read and Write          | Tag pushes, release publishing, PR branch creation                                        |
   | **Dependabot alerts** | Read-only               | Renovate reads vulnerability alerts to create security PRs                                |
   | **Issues**            | Read and Write          | Renovate [Dependency Dashboard](https://docs.renovatebot.com/key-concepts/dashboard/)     |
   | **Metadata**          | Read-only *(mandatory)* | Required for all fine-grained token API operations                                        |
   | **Pull requests**     | Read and Write          | All PR-creating jobs (sync-repomatic, fix-typos, prepare-release, Renovate)               |
   | **Workflows**         | Read and Write          | Push changes to `.github/workflows/` files — not available via YAML `permissions:` at all |

5. Click **Generate token** and copy it.

> [!TIP]
> **Token expiration**: Fine-grained PATs expire. Set a calendar reminder to rotate the token, or workflows will fail silently.

### Step 2: Add the secret

Run this command and paste the token when prompted:

```shell
gh secret set REPOMATIC_PAT --repo $repo_slug
```

Or add it manually: **this repo → [Settings → Secrets → Actions]($repo_url/settings/secrets/actions)** → **New repository secret** → name it `REPOMATIC_PAT` → paste the token.

### Step 3: Configure Dependabot settings

Enable vulnerability alerts (Renovate reads these via API) and disable automated security fixes (Renovate handles security PRs):

```shell
gh api repos/$repo_slug/vulnerability-alerts --method PUT
gh api repos/$repo_slug/automated-security-fixes --method DELETE
```

Disabling security updates also disables grouped security updates. Dependabot version updates and grouped security updates have no API — if either was manually enabled, disable them at **this repo → [Settings → Advanced Security → Dependabot]($repo_url/settings/security_analysis)**. (If `.github/dependabot.yml` exists, the `renovate.yaml` workflow will remove it automatically.)

\$immutable_releases_step

### Protect the `main` branch

Create a [**branch ruleset**]($repo_url/settings/rules/new?target=branch&enforcement=active) to prevent accidental force-pushes or deletions:

1. **Ruleset name**: `main`
2. **Enforcement status**: Active
3. Under **Target branches**, click **Add target** → **Include default branch**
4. Check **Restrict deletions** and **Block force pushes** (both are on by default for new rulesets)
5. Click **Create**

No status checks are required — the above is enough to protect commit history.

> [!NOTE]
> GitHub shows a banner warning on repositories without branch protection. This step silences it and guards against irreversible mistakes.

### Final step: Verify

Trigger a workflow re-run:

```shell
gh workflow run autofix.yaml --repo $repo_slug
```

Or re-run from the [**Actions tab**]($repo_url/actions/workflows/autofix.yaml). Jobs should now update `.github/workflows/` files without errors.

\$org_tip

This issue will close automatically once the secret is detected. Repository state and configuration are continuously checked and enforced by the [`lint-repo` job]($repo_url/actions/workflows/lint.yaml).
