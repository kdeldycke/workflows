---
args: [repo_url, repo_slug]
footer: 'false'
---

Set the GitHub Pages deployment source to **GitHub Actions** so the `docs.yaml` workflow can deploy via `actions/deploy-pages`.

The fastest fix is a single `gh` command:

```shell
gh api --method PUT repos/$repo_slug/pages -f build_type=workflow
```

Or set it manually at [**Settings → Pages**]($repo_url/settings/pages) → **Build and deployment** → **Source** → select **GitHub Actions**.

> [!NOTE]
> The previous deployment method used a `gh-pages` branch. After switching to GitHub Actions, the `gh-pages` branch can be safely deleted.
