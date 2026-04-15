# {octicon}`gear` Configuration

## `[tool.repomatic]` configuration

Downstream projects can customize workflow behavior by adding a `[tool.repomatic]` section in their `pyproject.toml`:

```toml
[tool.repomatic]
pypi-package-history = ["old-name", "older-name"]

awesome-template.sync = false
bumpversion.sync = false
cache.max-age = 14
dev-release.sync = false
gitignore.sync = false
labels.sync = false
mailmap.sync = false
setup-guide = false
uv-lock.sync = false

dependency-graph.output = "./docs/assets/dependencies.mmd"
dependency-graph.all-groups = true
dependency-graph.all-extras = true
dependency-graph.no-groups = []
dependency-graph.no-extras = []
dependency-graph.level = 0

gitignore.location = "./.gitignore"
gitignore.extra-categories = ["terraform", "go"]
gitignore.extra-content = '''
junit.xml

# Claude Code
.claude/
'''

exclude = ["skills", "workflows/debug.yaml", "zizmor"]

labels.extra-files = ["https://example.com/my-labels.toml"]
labels.extra-file-rules = "docs:\n  - docs/**"
labels.extra-content-rules = "security:\n  - '(CVE|vulnerability)'"

nuitka.enabled = false
nuitka.entry-points = ["mpm"]
nuitka.extra-args = [
  "--include-data-files=my_pkg/data/*.json=my_pkg/data/",
]
nuitka.unstable-targets = ["linux-arm64", "windows-arm64"]

test-plan.file = "./tests/cli-test-plan.yaml"
test-plan.timeout = 120
test-plan.inline = "- args: --version"

workflow.sync = false
workflow.source-paths = ["extra_platforms"]
```

<!-- config-reference-start -->
`awesome-template.sync`
: **Type:** bool | **Default:** `true`

  Whether awesome-template sync is enabled for this project.

`bumpversion.sync`
: **Type:** bool | **Default:** `true`

  Whether bumpversion config sync is enabled for this project.

`cache.dir`
: **Type:** str | **Default:** `""`

  Override the binary cache directory path.

`cache.github-release-ttl`
: **Type:** int | **Default:** `604800`

  Freshness TTL for cached single-release bodies (seconds).

`cache.github-releases-ttl`
: **Type:** int | **Default:** `86400`

  Freshness TTL for cached all-releases responses (seconds).

`cache.max-age`
: **Type:** int | **Default:** `30`

  Auto-purge cached entries older than this many days.

`cache.pypi-ttl`
: **Type:** int | **Default:** `86400`

  Freshness TTL for cached PyPI metadata (seconds).

`changelog.location`
: **Type:** str | **Default:** `"./changelog.md"`

  File path of the changelog, relative to the root of the repository.

`dependency-graph.all-extras`
: **Type:** bool | **Default:** `true`

  Whether to include all optional extras in the graph.

`dependency-graph.all-groups`
: **Type:** bool | **Default:** `true`

  Whether to include all dependency groups in the graph.

`dependency-graph.level`
: **Type:** int | **Default:** *(none)*

  Maximum depth of the dependency graph.

`dependency-graph.no-extras`
: **Type:** list[str] | **Default:** `[]`

  Optional extras to exclude from the graph.

`dependency-graph.no-groups`
: **Type:** list[str] | **Default:** `[]`

  Dependency groups to exclude from the graph.

`dependency-graph.output`
: **Type:** str | **Default:** `"./docs/assets/dependencies.mmd"`

  Path where the dependency graph Mermaid diagram should be written.

`dev-release.sync`
: **Type:** bool | **Default:** `true`

  Whether dev pre-release sync is enabled for this project.

`docs.apidoc-exclude`
: **Type:** list[str] | **Default:** `[]`

  Glob patterns for modules to exclude from `sphinx-apidoc`.

`docs.apidoc-extra-args`
: **Type:** list[str] | **Default:** `[]`

  Extra arguments appended to the `sphinx-apidoc` invocation.

`docs.update-script`
: **Type:** str | **Default:** `"./docs/docs_update.py"`

  Path to a Python script run after `sphinx-apidoc` to generate dynamic content.

`exclude`
: **Type:** list[str] | **Default:** `[]`

  Additional components and files to exclude from repomatic operations.

`gitignore.extra-categories`
: **Type:** list[str] | **Default:** `[]`

  Additional gitignore template categories to fetch from gitignore.io.

`gitignore.extra-content`
: **Type:** str | **Default:** *(see example)*

  Additional content to append at the end of the generated `.gitignore` file.

`gitignore.location`
: **Type:** str | **Default:** `"./.gitignore"`

  File path of the `.gitignore` to update, relative to the root of the repository.

`gitignore.sync`
: **Type:** bool | **Default:** `true`

  Whether `.gitignore` sync is enabled for this project.

`include`
: **Type:** list[str] | **Default:** `[]`

  Components and files to force-include, overriding default exclusions.

`labels.extra-content-rules`
: **Type:** str | **Default:** `""`

  Additional YAML rules appended to the content-based labeller configuration.

`labels.extra-file-rules`
: **Type:** str | **Default:** `""`

  Additional YAML rules appended to the file-based labeller configuration.

`labels.extra-files`
: **Type:** list[str] | **Default:** `[]`

  URLs of additional label definition files (JSON, JSON5, TOML, or YAML).

`labels.sync`
: **Type:** bool | **Default:** `true`

  Whether label sync is enabled for this project.

`mailmap.sync`
: **Type:** bool | **Default:** `true`

  Whether `.mailmap` sync is enabled for this project.

`notification.unsubscribe`
: **Type:** bool | **Default:** `false`

  Whether the unsubscribe-threads workflow is enabled.

`nuitka.enabled`
: **Type:** bool | **Default:** `true`

  Whether Nuitka binary compilation is enabled for this project.

`nuitka.entry-points`
: **Type:** list[str] | **Default:** `[]`

  Which `[project.scripts]` entry points produce Nuitka binaries.

`nuitka.extra-args`
: **Type:** list[str] | **Default:** `[]`

  Extra Nuitka CLI arguments for binary compilation.

`nuitka.unstable-targets`
: **Type:** list[str] | **Default:** `[]`

  Nuitka build targets allowed to fail without blocking the release.

`pypi-package-history`
: **Type:** list[str] | **Default:** `[]`

  Former PyPI package names for projects that were renamed.

`setup-guide`
: **Type:** bool | **Default:** `true`

  Whether the setup guide issue is enabled for this project.

`skills.location`
: **Type:** str | **Default:** `"./.claude/skills/"`

  Directory prefix for Claude Code skill files, relative to the repository root.

`test-matrix.exclude`
: **Type:** list\[dict[str, str]\] | **Default:** `[]`

  Extra exclude rules applied to both full and PR test matrices.

`test-matrix.include`
: **Type:** list\[dict[str, str]\] | **Default:** `[]`

  Extra include directives applied to both full and PR test matrices.

`test-matrix.remove`
: **Type:** dict\[str, list[str]\] | **Default:** {}

  Per-axis value removals applied to both full and PR test matrices.

`test-matrix.replace`
: **Type:** dict\[str, dict[str, str]\] | **Default:** {}

  Per-axis value replacements applied to both full and PR test matrices.

`test-matrix.variations`
: **Type:** dict\[str, list[str]\] | **Default:** {}

  Extra matrix dimension values added to the full test matrix only.

`test-plan.file`
: **Type:** str | **Default:** `"./tests/cli-test-plan.yaml"`

  Path to the YAML test plan file for binary testing.

`test-plan.inline`
: **Type:** str | **Default:** *(none)*

  Inline YAML test plan for binaries.

`test-plan.timeout`
: **Type:** int | **Default:** *(none)*

  Timeout in seconds for each binary test.

`uv-lock.sync`
: **Type:** bool | **Default:** `true`

  Whether `uv.lock` sync is enabled for this project.

`workflow.source-paths`
: **Type:** list[str] | **Default:** *(none)*

  Source code directory names for workflow trigger `paths:` filters.

`workflow.sync`
: **Type:** bool | **Default:** `true`

  Whether workflow sync is enabled for this project.
<!-- config-reference-end -->

## `[tool.X]` bridge and tool runner

`repomatic run` also bridges the gap for tools that can't read `pyproject.toml` natively: write your config in `[tool.<name>]` and repomatic translates it to the tool's native format at invocation time. See the [tool runner](tool-runner.md) page for the full list of supported tools, config resolution precedence, binary caching, and a tutorial.
