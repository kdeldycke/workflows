---
args: [repo_url, repo_slug]
footer: 'false'
---

Set the GitHub Pages deployment source to **GitHub Actions** so the `docs.yaml` workflow can deploy via `actions/deploy-pages`.

The fastest fix is a single `gh` command. Use `POST` to enable Pages for the first time, or `PUT` if Pages is already configured with a different source:

```shell
# Enable Pages (first time):
gh api --method POST repos/$repo_slug/pages -f build_type=workflow

# Or update an existing Pages configuration:
gh api --method PUT repos/$repo_slug/pages -f build_type=workflow
```

Or set it manually at [**Settings → Pages**]($repo_url/settings/pages) → **Build and deployment** → **Source** → select **GitHub Actions**.

If the repository has a leftover `gh-pages` branch from a previous deployment method, delete it after switching:

```shell
gh api --method DELETE repos/$repo_slug/git/refs/heads/gh-pages
```

The `lint-repo` job warns about stale `gh-pages` branches.
