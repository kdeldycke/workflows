---
args: [repo_url]
footer: 'false'
---

Create a [**branch ruleset**]($repo_url/settings/rules/new?target=branch&enforcement=active) to prevent accidental force-pushes or deletions:

1. **Ruleset name**: `main`
2. **Enforcement status**: Active
3. Under **Target branches**, click **Add target** → **Include default branch**
4. Check **Restrict deletions** and **Block force pushes** (both are on by default for new rulesets)
5. Click **Create**

No status checks are required — the above is enough to protect commit history.

> [!NOTE]
> GitHub [prompts repository admins](https://github.com/orgs/community/discussions/23046) to protect their default branch when none is set. This step silences that prompt and guards against irreversible mistakes.
