---
description: Monitor CI test workflow, diagnose failures, fix code, commit, and loop until all stable jobs pass. Ignores unstable failures.
user_invocable: true
---

# Babysit CI: monitor and fix tests.yaml

Monitor the `tests.yaml` workflow in a fix-verify loop until all stable matrix variations pass.

## Invocation

This skill involves repeated `gh`, `git`, `uv run pytest`, `git commit`, and `git push` calls. Run with `--dangerously-skip-permissions` to avoid manual approval on each step. Sonnet is recommended: the task is mechanical (fetch logs, match patterns, edit code, commit) and doesn't need deep reasoning:

```shell-session
$ claude --dangerously-skip-permissions --model sonnet /babysit-ci
```

Because this loop runs autonomously without human review, commits must be attributed to Claude with a `Co-Authored-By` trailer. This is the one exception to the global no-AI-attribution rule.

## Timeline

```
LOCAL (free)                              REMOTE (expensive)
─────────────                             ──────────────────

┌───────────────────────┐                 ┌──────────────────────────┐
│  step 3: local tests  │                 │  step 3: CI matrix       │
│  ┌─ pytest ─────────┐ │   parallel      │  [stable] Linux 3.10     │
│  ├─ mypy ───────┐   │ │ ◄──────────►   │  [stable] Linux 3.13     │
│  └─ ruff ──┐    │   │ │                 │  [stable] Windows 3.13   │
│            │    │   │ │                 │  [unstable] Linux 3.15   │
│            ▼    ▼   ▼ │                 │  [stable] macOS 3.13     │
│    local results ready │                 └────────────┬─────────────┘
└───────────┬────────────┘                              │
            │                                           ▼
            │ local                        ┌────────────────────────┐
            │ fail?──yes──►                │  first stable failure? │
            │ no                           └───────────┬────────────┘
            │                                          │
            └──────────────────┬───────────────────────┘
                               ▼
              ┌─────────────────────────────────────┐
              │  step 4: CANCEL remaining CI runs   │
              │  step 4: download ALL failed logs   │
              └────────────────┬────────────────────┘
                               ▼
              ┌─────────────────────────────────────┐
              │  step 5: FIX                        │
              │  combine local + CI failures        │
              │  write fix                          │
              │  re-run pytest + mypy + ruff locally │
              └────────────────┬────────────────────┘
                               ▼
              ┌─────────────────────────────────────┐
              │  step 6: pre-push checks            │
              │  check remote lint.yaml results     │
              │  check format-python autofix PR     │
              │  merge autofix PR if useful, rebase │
              └────────────────┬────────────────────┘
                               ▼
              ┌─────────────────────────────────────┐
              │  step 7: commit + push              │
              └────────────────┬────────────────────┘
                               │
              ┌────────────────▼────────────────────┐
              │  step 8: repeat (back to step 2)    │
              └─────────────────────────────────────┘
```

## Loop

1. **Detect the repo** from the current working directory:

   ```
   gh repo view --json nameWithOwner --jq '.nameWithOwner'
   ```

2. **Get the latest run** for the `main` branch:

   ```
   gh run list --workflow=tests.yaml --branch=main --limit=1
   ```

3. **Run local tests while waiting for CI.** Don't idle while polling. Start the full test suite and linters locally in the background immediately after identifying the run:

   ```
   uv run pytest --no-header -q &
   uv run --group typing repomatic run mypy -- repomatic &
   uv run --group lint ruff check repomatic &
   ```

   In parallel, poll CI every 60 seconds for the first stable failure (or success):

   ```
   gh run view <RUN_ID> --json status,conclusion,jobs \
     --jq '{status, conclusion, failed: [.jobs[] | select(.conclusion == "failure" and (.name | startswith("✅")))] | length}'
   ```

   If local tests fail before CI reports anything, you already have the diagnosis: skip straight to step 5 without waiting.

4. **On stable failure**, immediately cancel remaining runs to free runners:

   ```
   gh run list --workflow=tests.yaml --status=queued --status=in_progress --json databaseId,displayTitle
   ```

   **Never cancel** a run whose `displayTitle` starts with `[changelog] Release`. This mirrors the `cancel-in-progress` condition in the `tests.yaml` concurrency group (`!startsWith(github.event.head_commit.message, '[changelog] Release')`), which protects release runs from being cancelled. Cancel everything else.

   Then download logs from **all** stable jobs that failed (logs are retained after cancellation):

   ```
   gh run view <RUN_ID> --json jobs --jq '[.jobs[] | select(.conclusion == "failure" and (.name | startswith("✅")))] | .[].databaseId'
   ```

   Fetch each failed job's log (`gh api repos/<OWNER>/<REPO>/actions/jobs/<JOB_ID>/logs`). Different matrix entries often surface different issues (e.g., a Windows encoding error alongside a Linux assertion failure): fixing them all in one batch avoids burning another full CI round.

   Analyze all collected logs, focusing on `FAILED` and `AssertionError` lines in the pytest summaries.

5. **Fix the root cause** using the combined picture from CI logs and local results (step 3). Fix the codebase, not the tests, unless the tests are genuinely wrong. If both mypy and ruff have failures, address them together. Fixing them independently risks an oscillation loop (see [§ mypy/ruff fix oscillation](#mypy-ruff-fix-oscillation)).

   After applying fixes, re-run the full local validation to confirm:

   ```
   uv run pytest --no-header -q
   uv run --group typing repomatic run mypy -- repomatic
   uv run --group lint ruff check repomatic
   ```

6. **Check lint and autofix status before pushing.** Gather the remote picture (these calls are fast, no waiting):

   ```
   gh run list --workflow=lint.yaml --branch=main --limit=1
   gh run list --workflow=autofix.yaml --branch=main --limit=1
   gh pr list --head=format-python --state=open --json number,title,url
   ```

   - If the `lint.yaml` run shows mypy or ruff failures you haven't addressed locally, fix them now.
   - If a `format-python` autofix PR exists, review its diff: it contains ruff's own autofixes for the same commit. If it resolves issues you're seeing, merge it first (`gh pr merge --squash`), pull, and rebase your fix before pushing.

7. **Commit the fix** with a clear message describing what changed and why, then `git push`.

8. **Repeat from step 2** until the test run completes with all stable (✅) jobs passing and the lint run has no mypy/ruff failures.

### Early exit

Once all fast platforms (Linux, Windows) have completed with zero stable failures and only slow runners (macOS) remain queued or in progress, declare success and stop the loop. macOS runners are resource-constrained and can take a long time to start. If the fixes are platform-independent, waiting for macOS adds no diagnostic value.

## Stable vs. unstable

- **Stable jobs** (✅): must pass. Their names start with `✅`.
- **Unstable jobs** (⁉️): allowed to fail (Python dev versions like 3.15, 3.15t). Ignore their failures.

The workflow uses `continue-on-error` for unstable jobs, so even if they fail, the overall run can still succeed.

## Common failure patterns

### mypy/ruff fix oscillation

mypy and ruff can enter a fix loop where each tool's fix breaks the other. Common triggers:

- **Unused import**: ruff removes an import (`F401`), mypy then complains about a missing name. Adding the import back triggers ruff again.
- **Type annotation style**: mypy requires an explicit annotation, ruff considers it redundant or wants a different form.
- **`noqa` vs `type: ignore`**: adding `# noqa` silences ruff but mypy still fails; adding `# type: ignore` silences mypy but ruff flags the unused directive.

When you detect this pattern (the same lines toggling between fixes across iterations), stop and apply a combined resolution: typically a `# type: ignore[code]` with a matching `# noqa: XXXX` on the same line, or a restructuring that satisfies both tools at once. Do not keep iterating.

### Platform-specific test skips

Some tests are skipped on certain platforms (e.g., `windows-11-arm` has no Python 3.10 ARM64 build). Check the matrix `exclude` section in `tests.yaml` before investigating missing results.
