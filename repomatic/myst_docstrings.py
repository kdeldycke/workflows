# Copyright Kevin Deldycke <kevin@deldycke.com> and contributors.
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
"""Convert MyST-flavored docstrings to reST for `sphinx.ext.autodoc`.

Hooks into `autodoc-process-docstring` to transparently convert MyST markdown
syntax in Python docstrings to reStructuredText before Sphinx processes them.
See {doc}`/myst-docstrings` for setup and usage.

The conversion is idempotent: docstrings already in reST pass through
unchanged. This allows incremental migration one module at a time.

Supported conversions:

:::{list-table}
:header-rows: 1

* - Construct
  - MyST input
  - reST output
* - Cross-references
  - ``{role}`target```
  - ``{role}`target```
* - Fenced directives
  - ``:::{note}`` or `` ```{note} ``
  - `.. note::`
* - Markdown links
  - `[text](url)`
  - ```text <url>`_``
:::

Inline code (single backtick) is converted to reST double backticks.
Field lists (``{param}`, `{returns}``) need no conversion.

:::{note}
Register this extension in your Sphinx `conf.py`:

.. code-block:: python

    extensions = [
        "sphinx.ext.autodoc",
        "repomatic.myst_docstrings",
    ]

This requires `repomatic` in your docs dependency group.
:::
"""

from __future__ import annotations

import re

# {role}`target` -> {role}`target`
# Negative lookbehind prevents matching inside double backticks (``{version}``).
_XREF_RE = re.compile(r"(?<!``)\{([\w-]+)\}`([^`]*?)`")

# :::{directive} optional-title        ```{directive} optional-title
# body                          or     body
# :::                                  ```
_COLON_FENCE_RE = re.compile(
    r"^( *):::\{([\w-]+)\}[ ]*([^\n]*)\n(.*?)^\1:::\s*$",
    re.MULTILINE | re.DOTALL,
)
_BACKTICK_FENCE_RE = re.compile(
    r"^( *)```\{([\w-]+)\}[ ]*([^\n]*)\n(.*?)^\1```\s*$",
    re.MULTILINE | re.DOTALL,
)

# [text](url) but not ![alt](url)
_LINK_RE = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")


def _convert_link(match: re.Match) -> str:
    """Convert a markdown link to reST, stripping backticks from the label."""
    label = match.group(1).replace("`", "")
    url = match.group(2)
    return f"`{label} <{url}>`_"


# Single-backtick inline code `text` -> ``text`` (after protected spans are
# placeholdered out).
_INLINE_CODE_RE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")

# Backtick spans that must NOT be treated as inline code.  Matches:
#   {role}`target`   — reST cross-references (from step 1)
#   `text`_          — reST hyperlink references (idempotent pass-through)
_PROTECTED_RE = re.compile(r":[\w-]+:`[^`]*`|`[^`]+`_{1,2}")


def _convert_fence(match: re.Match) -> str:
    """Convert a single colon-fenced directive to reST."""
    indent = match.group(1)
    directive = match.group(2)
    title = match.group(3).strip()
    body = match.group(4)

    header = f"{indent}.. {directive}::"
    if title:
        header += f" {title}"
    header += "\n"

    body_indent = indent + "    "
    converted_lines: list[str] = []
    for line in body.split("\n"):
        if line.strip():
            # Preserve relative indentation within the body.
            stripped = line.lstrip()
            extra_spaces = len(line) - len(stripped) - len(indent)
            converted_lines.append(body_indent + " " * max(0, extra_spaces) + stripped)
        else:
            converted_lines.append("")

    # reST directives need a blank line between the header and the body.
    return header + "\n" + "\n".join(converted_lines) + "\n"


def myst_to_rst(lines: list[str]) -> None:
    """Convert MyST syntax to reST, modifying *lines* in place.

    The conversion is idempotent: reST-only docstrings pass through unchanged
    because none of the patterns match reST syntax.
    """
    text = "\n".join(lines)

    # 1. Cross-references: {role}`target` -> {role}`target`.
    text = _XREF_RE.sub(r":\1:`\2`", text)

    # 2. Fenced directives -> reST directives.
    # Handles both colon fences (:::) and backtick fences (```).
    # Loop handles nesting (rare in docstrings, but correct).
    prev = None
    while prev != text:
        prev = text
        text = _COLON_FENCE_RE.sub(_convert_fence, text)
        text = _BACKTICK_FENCE_RE.sub(_convert_fence, text)

    # 3. Single-backtick inline code -> double-backtick.
    # Protect reST backtick spans (cross-references from step 1, and reST
    # hyperlink references in idempotent pass-through) with placeholders so
    # their backticks are not mistaken for inline code boundaries.
    placeholders: dict[str, str] = {}
    counter = 0

    def _save(m: re.Match) -> str:
        nonlocal counter
        key = f"\x00P{counter}\x00"
        counter += 1
        placeholders[key] = m.group(0)
        return key

    text = _PROTECTED_RE.sub(_save, text)
    text = _INLINE_CODE_RE.sub(r"``\1``", text)
    for key, value in placeholders.items():
        text = text.replace(key, value)

    # 4. Markdown links -> reST links.
    # Runs after inline code so that the reST links it produces (which use
    # single backticks: `text <url>`_) are not doubled by step 3.
    # Backticks in link labels are stripped because reST does not support
    # nested markup (inline code inside hyperlinks).  This lets authors write
    # idiomatic MyST like [`sys.platform`](url) and get a clean reST link.
    text = _LINK_RE.sub(_convert_link, text)

    lines[:] = text.split("\n")


def _on_process_docstring(app, what, name, obj, options, lines):
    """`autodoc-process-docstring` event handler."""
    myst_to_rst(lines)


def setup(app):
    """Sphinx extension entry point."""
    app.connect("autodoc-process-docstring", _on_process_docstring)
    return {"version": "0.1", "parallel_read_safe": True}
