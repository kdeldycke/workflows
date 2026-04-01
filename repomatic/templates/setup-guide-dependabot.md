---
args: [repo_url, repo_slug]
footer: 'false'
---

Enable [vulnerability alerts](https://docs.github.com/en/code-security/dependabot/dependabot-alerts/configuring-dependabot-alerts) ([Renovate reads these via API](https://docs.renovatebot.com/configuration-options/#vulnerabilityalerts)) and [disable automated security fixes](https://docs.github.com/en/code-security/dependabot/dependabot-security-updates/configuring-dependabot-security-updates) ([Renovate handles security PRs](https://docs.renovatebot.com/upgrade-best-practices/#vulnerability-remediation)):

```shell
gh api repos/$repo_slug/vulnerability-alerts --method PUT
gh api repos/$repo_slug/automated-security-fixes --method DELETE
```

Disabling security updates also disables grouped security updates. Dependabot version updates and grouped security updates have no API — if either was manually enabled, disable them at **this repo → [Settings → Advanced Security → Dependabot]($repo_url/settings/security_analysis)**. (If `.github/dependabot.yml` exists, the `renovate.yaml` workflow will remove it automatically.)
