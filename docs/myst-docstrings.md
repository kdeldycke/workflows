# {octicon}`pencil` MyST docstrings

Python docstrings in this project use [MyST markdown](https://myst-parser.readthedocs.io/en/latest/) instead of reStructuredText. A Sphinx extension ({mod}`repomatic.myst_docstrings`) transparently converts MyST back to reST at build time, so `sphinx.ext.autodoc` works without modification. A companion CLI command ({ref}`repomatic convert-to-myst <repomatic-convert-to-myst>`) handles the one-time source migration.

## Why not `sphinx-autodoc2`?

[`sphinx-autodoc2`](https://github.com/sphinx-extensions2/sphinx-autodoc2) was designed as a full replacement for `sphinx.ext.autodoc` with native MyST support. It parses docstrings as MyST directly, eliminating the need for a conversion step. In practice the project is abandoned: the last release (`v0.5.0`) dates from November 2023, its test suite does not pass against current Sphinx or docutils versions, and it has no compatibility with `sphinx_autodoc_typehints`.

{mod}`repomatic.myst_docstrings` fills the same gap with a lighter approach: it hooks into `sphinx.ext.autodoc`'s existing `autodoc-process-docstring` event and converts MyST constructs to reST before Sphinx processes them. This preserves full compatibility with `sphinx_autodoc_typehints`, `autodoc_default_options`, `autoclass_content`, and every other extension or setting that builds on `sphinx.ext.autodoc`. The conversion is regex-based, idempotent, and handles all inline constructs that are valid inside docstrings (cross-references, inline code, links, fenced directives).

## Setup

### 1. Add the extension

In your Sphinx `conf.py`, add {mod}`repomatic.myst_docstrings` alongside `sphinx.ext.autodoc`:

```python
extensions = [
    "sphinx.ext.autodoc",
    "repomatic.myst_docstrings",
    "sphinx_autodoc_typehints",  # must come after myst_docstrings
    # ... other extensions
]
```

If `sphinx.ext.autodoc` is absent, the `autodoc-process-docstring` event never fires and the extension silently does nothing.

:::{warning}
If you also use `sphinx_autodoc_typehints`, list `repomatic.myst_docstrings` **before** it in the `extensions` list. The extension registers its `autodoc-process-docstring` hook at priority 400 (vs the default 500 used by `sphinx_autodoc_typehints`), so MyST-to-reST conversion always runs first regardless of registration order. Listing it first makes the intent explicit and is enforced at load time: if `sphinx_autodoc_typehints` is already registered when `repomatic.myst_docstrings` loads, the build fails with a clear error.
:::

### 2. Add the dependency

`repomatic` must be importable during the docs build. Add it to your docs dependency group in `pyproject.toml`:

```toml
[dependency-groups]
docs = [
  "repomatic",
  "sphinx>=8",
  # ...
]
```

### 3. Migrate existing docstrings

Run the converter on your source directory:

```shell-session
$ uv run repomatic convert-to-myst
```

The command auto-detects the package directory from `pyproject.toml` entry points. You can also pass an explicit path:

```shell-session
$ uv run repomatic convert-to-myst src/mypackage
```

The conversion is idempotent: re-running it on already-converted files is a no-op.

## Syntax reference

Write docstrings in standard MyST markdown. The extension handles the reST translation at build time.

### Cross-references

Use MyST `` {role}`target` `` syntax instead of reST `` :role:`target` `` syntax:

| MyST (write this)                    | reST (produced at build time)        |
| :----------------------------------- | :----------------------------------- |
| `` {func}`foo` ``                    | `` :func:`foo` ``                    |
| `` {data}`~extra_platforms.MACOS` `` | `` :data:`~extra_platforms.MACOS` `` |
| `` {class}`str` ``                   | `` :class:`str` ``                   |

The `~` prefix for abbreviating to the last component works the same way.

### Admonitions

Both colon fences and backtick fences are supported:

````python
def detect():
    """Detect the current platform.

    ```{note}
    Falls back to generic detection if the specific
    platform check is unavailable.
    ```
    """
````

The colon-fence equivalent (`:::{note}` / `:::`) works identically. All standard Sphinx admonitions work: `note`, `warning`, `caution`, `hint`, `tip`, `seealso`, `danger`, `important`.

Admonitions with titles:

````python
"""
```{warning} Experimental API
This function may change in future releases.
```
"""
````

### Links

Use standard markdown links:

| MyST (write this)                                 | reST (produced at build time)                     |
| :------------------------------------------------ | :------------------------------------------------ |
| `[click here](https://example.com)`               | `` `click here <https://example.com>`_ ``         |
| `` [`sys.platform`](https://docs.python.org/3) `` | `` `sys.platform <https://docs.python.org/3>`_ `` |

Backticks in link labels are stripped automatically because reST does not support nested markup.

### Inline code

Use single backticks. The extension doubles them for reST:

| MyST (write this)          | reST (produced at build time)  |
| :------------------------- | :----------------------------- |
| `` `True` ``               | ``` ``True`` ```               |
| `` `platform.machine()` `` | ``` ``platform.machine()`` ``` |

### Code blocks

Use fenced `code-block` directives (either backtick or colon style):

````python
"""
```{code-block} python
extensions = [
    "sphinx.ext.autodoc",
    "repomatic.myst_docstrings",
]
```
"""
````

Plain triple-backtick fences *without* a directive name (like ```` ``` python ````) are **not** converted. Use ```` ```{code-block} python ```` or `:::{code-block} python` instead.

### Field lists

`:param:`, `:return:`, `:raises:` and other Sphinx field list entries use the same syntax in MyST and reST, so the field list markers themselves need no conversion. The content *inside* field list entries is converted normally: inline code, cross-references, and links all work:

```python
def read(path, config):
    """Read a file and return its contents.

    :param path: Filesystem `path` to process.
    :param config: A {class}`~repomatic.config.Config` instance.
    :return: `True` if the file was read successfully.
    :raises FileNotFoundError: If `path` does not exist.
    """
```

In the example above, single-backtick code spans (`path`, `True`) are doubled for reST, and the `{class}` cross-reference is converted to `:class:`. The field list markers (`:param path:`, `:return:`, `:raises FileNotFoundError:`) pass through unchanged.

## What the converter does

{ref}`repomatic convert-to-myst <repomatic-convert-to-myst>` applies these transformations to Python source files, in order:

1. **Cross-references**: `` :role:`target` `` becomes `` {role}`target` ``
2. **Named links**: `` `text <url>`_ `` becomes `[text](url)`
3. **Inline code**: ``` ``code`` ``` becomes `` `code` ``
4. **`#:` comment blocks**: prefix stripped, directives converted, prefix restored
5. **Directives**: `.. directive::` + indented body becomes `:::{directive}` / `:::`

Content containing `{` inside inline code is left as double backticks to avoid clashing with MyST cross-reference syntax. These pass through the extension unchanged.

## Limitations

The extension handles the constructs listed above. It does **not** convert:

- **Plain triple-backtick code blocks** (```` ``` python ```` without `{code-block}`). Use ```` ```{code-block} python ```` or `:::{code-block} python` instead.
- **Nested fences of the same type** (`::::` / `:::` or ` ` / \`\`\` \`\`\`\`). A single nesting level works because the inner directive (like `.. code-block::`) stays as reST inside the converted outer fence.
- **Complex tables** (`:::{list-table}`, `:::{csv-table}`). These work in module-level docstrings processed by `myst-parser` but are unlikely to appear in function docstrings.
- **`{` inside single backticks**. Content like `` `{version}` `` would be misinterpreted as a cross-reference. The converter intentionally keeps these as double backticks (``` ``{version}`` ```), which the extension passes through to Sphinx as-is.
- **MyST footnotes** (`[^1]` / `[^1]: text`). Footnote syntax is not recognized and passes through as literal text. Footnotes are rare in docstrings but would need reST syntax (``.. [1]``) if required.
- **MyST substitution references** (`{{variable}}`). These are a `myst-parser` feature for `.md` files and are not processed inside docstrings.
- **MyST definition lists**. The `deflist` extension syntax (term on one line, `: definition` on the next) is not converted. Use reST definition lists or restructure as a field list.
- **Heading syntax** (`#`, `##`). Markdown headings inside docstrings are not converted to reST sections. Docstrings should not contain headings.

For constructs the extension does not handle, use reST syntax directly in the docstring body. The extension is idempotent: reST content passes through unchanged.
