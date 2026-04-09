---
args: [repo_url, repo_slug]
footer: 'false'
---

Require approval before workflows from fork pull requests run for any first-time contributor. Without this, a drive-by PR from any GitHub account (not just brand-new ones) can execute arbitrary workflow logic on its first contribution.

The fastest fix is a single `gh` command:

```shell
gh api --method PUT repos/$repo_slug/actions/permissions/fork-pr-contributor-approval -f approval_policy=first_time_contributors
```

Or set it manually at [**Settings → Actions → General**]($repo_url/settings/actions) → **Fork pull request workflows from outside collaborators** → **Require approval for first-time contributors**.

> [!NOTE]
> The three policy values, from weakest to strongest:
>
> - `first_time_contributors_new_to_github`: only catches brand-new GitHub accounts (GitHub's default, too weak)
> - `first_time_contributors`: requires approval for any first-time contributor to this repository (recommended minimum)
> - `all_external_contributors`: requires approval for every PR from any outside collaborator (strictest)
