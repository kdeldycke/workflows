---
args: [repo_name, repo_owner, repo_slug]
footer: "false"
---
### Rename the secret

Your repository uses the deprecated `WORKFLOW_UPDATE_GITHUB_PAT` secret. Rename it to `REPOMATIC_PAT`.

GitHub does not allow renaming secrets, so you need a token value to store under the new name. Since secret values are never displayed after saving, either regenerate the existing token or create a new one:

1. Go to **[Fine-grained tokens](https://github.com/settings/personal-access-tokens)**, find the token named `$repo_name-repomatic`, and click **Regenerate token** to get a fresh value. Alternatively, [create a new fine-grained PAT](https://github.com/settings/personal-access-tokens/new?name=$repo_name-repomatic&description=REPOMATIC_PAT+for+$repo_owner/$repo_name&target_name=$repo_owner&contents=write&issues=write&metadata=read&pull_requests=write&statuses=write&vulnerability_alerts=read&workflows=write).
2. Create a new secret named `REPOMATIC_PAT` with the token value:

```shell
gh secret set REPOMATIC_PAT --repo $repo_slug
```

3. Delete the old secret:

```shell
gh secret delete WORKFLOW_UPDATE_GITHUB_PAT --repo $repo_slug
```

This issue will close automatically once `REPOMATIC_PAT` is detected.
