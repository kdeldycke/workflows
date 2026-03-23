---
footer: "false"
args: [repo_name, repo_owner, repo_slug]
---
### Rename the secret

Your repository uses the deprecated `WORKFLOW_UPDATE_GITHUB_PAT` secret. Rename it to `REPOMATIC_PAT`.

GitHub does not allow renaming secrets, so create a new one with the same token value and delete the old one:

1. Go to **[Settings → Secrets → Actions](https://github.com/$repo_slug/settings/secrets/actions)**.
2. Click `WORKFLOW_UPDATE_GITHUB_PAT` → **Update** → copy the token (or [create a new one](https://github.com/settings/personal-access-tokens/new?name=$repo_name-repomatic&description=REPOMATIC_PAT+for+$repo_owner/$repo_name&target_name=$repo_owner&contents=write&issues=write&metadata=read&pull_requests=write&statuses=write&vulnerability_alerts=read&workflows=write) if you no longer have the value).
3. Create a new secret named `REPOMATIC_PAT` with the token value:

```shell
gh secret set REPOMATIC_PAT --repo $repo_slug
```

4. Delete the old secret:

```shell
gh secret delete WORKFLOW_UPDATE_GITHUB_PAT --repo $repo_slug
```

This issue will close automatically once `REPOMATIC_PAT` is detected.
