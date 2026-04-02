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

## Loop

1. **Detect the repo** from the current working directory:

   ```
   gh repo view --json nameWithOwner --jq '.nameWithOwner'
   ```

2. **Get the latest run** for the `main` branch:

   ```
   gh run list --workflow=tests.yaml --branch=main --limit=1
   ```

3. **Wait for jobs to complete** (or for the first stable failure). Poll every 60 seconds:

   ```
   gh run view <RUN_ID> --json status,conclusion,jobs \
     --jq '{status, conclusion, failed: [.jobs[] | select(.conclusion == "failure" and (.name | startswith("✅")))] | length}'
   ```

4. **On stable failure**, download the failed job's log:

   ```
   gh run view <RUN_ID> --json jobs --jq '.jobs[] | select(.conclusion == "failure" and (.name | startswith("✅"))) | .databaseId' | head -1
   gh api repos/<OWNER>/<REPO>/actions/jobs/<JOB_ID>/logs
   ```

   Analyze the log, focusing on the `FAILED` and `AssertionError` lines in the pytest summary.

5. **Fix the root cause** in the codebase (not the tests, unless the tests are genuinely wrong). Run the affected tests locally first, then the full suite to catch regressions before consuming CI resources:

   ```
   uv run pytest <test_file>::<test_name> -x --no-header -q
   uv run pytest --no-header -q
   ```

6. **Cancel all pending/in-progress runs** for `tests.yaml` across all branches to save CI resources:

   ```
   gh run list --workflow=tests.yaml --status=queued --status=in_progress --json databaseId --jq '.[].databaseId'
   ```

   Cancel each before pushing.

7. **Commit the fix** with a clear message describing what changed and why, then `git push`.

8. **Repeat from step 2** until the run completes with all stable (✅) jobs passing.

### Early exit

Once all fast platforms (Linux, Windows) have completed with zero stable failures and only slow runners (macOS) remain queued or in progress, declare success and stop the loop. macOS runners are resource-constrained and can take a long time to start. If the fixes are platform-independent, waiting for macOS adds no diagnostic value.

## Stable vs. unstable

- **Stable jobs** (✅): must pass. Their names start with `✅`.
- **Unstable jobs** (⁉️): allowed to fail (Python dev versions like 3.15, 3.15t). Ignore their failures.

The workflow uses `continue-on-error` for unstable jobs, so even if they fail, the overall run can still succeed.

## Common failure patterns

### Cross-platform help text wrapping

CLI help text wraps at 80 visible columns. Default values that include OS-specific paths (config dirs, app dirs) span a variable number of lines depending on platform path length. Test fixture regex patterns must use `.*` and `(?:...)*` to handle this variability.

Two specific sub-patterns to watch for:

1. **`[default:` line**: on short-path platforms (Linux), content may start on the same line as `[default:`. Use `\[default:.*\n` (not `\[default:\n`) so `.*` absorbs the content start.

2. **Closing `]` on its own line**: on Windows, wrapping may push `]` to a separate line with only ANSI reset codes before it. Use `.*\]` (not `.+\]`) so `.*` allows zero visible characters before the bracket.

### `re.PatternError` in line-by-line matching

When `re.fullmatch(regex, content)` fails and a fallback line-by-line matcher runs, multi-line regex groups like `(?:...\n)*` get split on `\n` into fragments with unmatched parentheses, triggering `re.PatternError`. If you see this error, the root cause is that the full regex doesn't match: fix the regex, not the error handling.

### ANSI code differences in colored output

Colored help output includes ANSI escape sequences. When matching colored output in tests, the regex must account for escape codes that don't contribute to visible width but alter the string content.

### Windows encoding

Windows CI runners redirect output to files using the system default encoding (cp1252). Workflows typically set `PYTHONIOENCODING=utf8` to work around Click's `UnicodeEncodeError` on non-ASCII output.

### Platform-specific test skips

Some tests are skipped on certain platforms (e.g., `windows-11-arm` has no Python 3.10 ARM64 build). Check the matrix `exclude` section in `tests.yaml` before investigating missing results.
