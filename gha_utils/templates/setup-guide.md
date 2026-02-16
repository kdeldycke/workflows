Some workflows need a **fine-grained personal access token** to create PRs that update files in `.github/workflows/`. Without it, those jobs will silently fail.

### Create the token

1. Go to **GitHub → Settings → Developer Settings → Personal Access Tokens → [Fine-grained tokens](https://github.com/settings/personal-access-tokens)**.

2. Click **Generate new token**.

3. Under **Repository access**, select this repository.

4. Add these permissions:

   | Permission          | Access         |
   | :------------------ | :------------- |
   | **Commit statuses** | Read and Write |
   | **Contents**        | Read and Write |
   | **Metadata**        | Read-only      |
   | **Pull requests**   | Read and Write |
   | **Workflows**       | Read and Write |

5. Click **Generate token** and copy it.

### Add the secret

1. Go to **this repo → Settings → Secrets and variables → Actions**.
2. Click **New repository secret**.
3. Name: `WORKFLOW_UPDATE_GITHUB_PAT`
4. Paste the token and click **Add secret**.

This issue will close automatically once the secret is detected.
