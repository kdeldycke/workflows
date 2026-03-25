---
args: [event_name, actor, rerun_row, ref_name, repo_url, sha, sha_short, job, workflow_file, run_id, run_number, run_attempt]
---

<details><summary><code>Workflow metadata</code></summary>

| Field | Value |
| :-- | :-- |
| **Trigger** | `\$event_name` |
| **Actor** | @\$actor |
\$rerun_row| **Ref** | `\$ref_name` |
| **Commit** | [`\$sha_short`](\$repo_url/commit/\$sha) |
| **Job** | [`\$job`](\$repo_url/blob/\$sha/.github/workflows/\$workflow_file) |
| **Workflow** | [`\$workflow_file`](\$repo_url/blob/\$sha/.github/workflows/\$workflow_file) |
| **Run** | [#\$run_number.\$run_attempt](\$repo_url/actions/runs/\$run_id) |

</details>
