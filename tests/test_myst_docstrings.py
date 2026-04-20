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
"""Tests for the MyST-to-reST docstring conversion hook."""

from __future__ import annotations

import pytest

from repomatic.myst_docstrings import myst_to_rst


def _convert(text: str) -> str:
    """Helper: run myst_to_rst on a string and return the result."""
    lines = text.split("\n")
    myst_to_rst(lines)
    return "\n".join(lines)


# ---- Cross-references: {role}`target` -> :role:`target` --------------------


@pytest.mark.parametrize(
    ("myst", "expected"),
    [
        ("{func}`foo`", ":func:`foo`"),
        ("{data}`~extra_platforms.MACOS`", ":data:`~extra_platforms.MACOS`"),
        ("{deco}`~pytest.skip_linux`", ":deco:`~pytest.skip_linux`"),
        (
            "{func}`is_a`, {func}`is_b` and {data}`C`",
            ":func:`is_a`, :func:`is_b` and :data:`C`",
        ),
        ("a {class}`frozenset` of items", "a :class:`frozenset` of items"),
    ],
    ids=["simple", "tilde", "custom-role", "multiple", "mid-sentence"],
)
def test_xref_conversion(myst, expected):
    assert _convert(myst) == expected


# ---- Admonitions: :::{directive} -> .. directive:: -------------------------


@pytest.mark.parametrize(
    ("myst", "expected_fragments"),
    [
        (
            ":::{note}\nSome content.\n:::",
            [".. note::", "    Some content."],
        ),
        (
            ":::{hint}\nLine one.\nLine two.\n:::",
            [".. hint::", "    Line one.", "    Line two."],
        ),
        (
            ":::{warning} Be careful\nDon't do this.\n:::",
            [".. warning:: Be careful", "    Don't do this."],
        ),
        (
            ":::{note}\nOuter.\n\n    - Item one.\n    - Item two.\n:::",
            [".. note::", "        - Item one."],
        ),
        (
            ":::{seealso}\nSource: <https://example.com>\n:::",
            [".. seealso::", "    Source: <https://example.com>"],
        ),
    ],
    ids=["note", "multiline", "with-title", "indented-body", "seealso"],
)
def test_admonition_conversion(myst, expected_fragments):
    result = _convert(myst)
    for fragment in expected_fragments:
        assert fragment in result


def test_admonition_preserves_blank_lines():
    result = _convert(":::{note}\nFirst.\n\nSecond.\n:::")
    assert "" in result.split("\n")


# ---- Links: [text](url) -> `text <url>`_ ----------------------------------


@pytest.mark.parametrize(
    ("myst", "expected"),
    [
        (
            "[click here](https://example.com)",
            "`click here <https://example.com>`_",
        ),
        (
            "See [the docs](https://docs.example.com) for details.",
            "See `the docs <https://docs.example.com>`_ for details.",
        ),
        (
            "[Wikipedia](https://en.wikipedia.org/wiki/Foo)",
            "`Wikipedia <https://en.wikipedia.org/wiki/Foo>`_",
        ),
    ],
    ids=["simple", "mid-sentence", "parens-in-url"],
)
def test_link_conversion(myst, expected):
    assert _convert(myst) == expected


def test_image_link_not_converted():
    text = "![logo](https://example.com/logo.png)"
    assert _convert(text) == text


@pytest.mark.parametrize(
    ("myst", "expected"),
    [
        (
            "[`sys.platform`](https://docs.python.org/3)",
            "`sys.platform <https://docs.python.org/3>`_",
        ),
        (
            "the [`/proc`](https://example.com) filesystem",
            "the `/proc <https://example.com>`_ filesystem",
        ),
        (
            "[from `foo` to `bar`](https://example.com)",
            "`from foo to bar <https://example.com>`_",
        ),
    ],
    ids=["code-label", "code-label-mid-sentence", "multiple-code-spans"],
)
def test_link_strips_backticks_from_label(myst, expected):
    """reST has no nested markup, so backticks are stripped from link labels."""
    assert _convert(myst) == expected


# ---- Inline code: `text` -> ``text`` ---------------------------------------


@pytest.mark.parametrize(
    ("myst", "expected"),
    [
        ("`True`", "``True``"),
        ("Returns `True` if detected.", "Returns ``True`` if detected."),
        ("`foo` and `bar`", "``foo`` and ``bar``"),
        ("`platform.machine()`", "``platform.machine()``"),
    ],
    ids=["simple", "in-sentence", "multiple", "dotted-call"],
)
def test_inline_code_conversion(myst, expected):
    assert _convert(myst) == expected


def test_inline_code_preserves_double_backticks():
    """Already-doubled backticks must not be quadrupled."""
    text = "Returns ``True`` if detected."
    assert _convert(text) == text


@pytest.mark.parametrize(
    ("myst", "expected"),
    [
        ("{func}`foo` returns `True`", ":func:`foo` returns ``True``"),
        ("a {data}`~X` or `None`", "a :data:`~X` or ``None``"),
        ("`some_var` is a {class}`str`", "``some_var`` is a :class:`str`"),
    ],
    ids=["xref-then-code", "xref-or-code", "code-then-xref"],
)
def test_inline_code_no_cross_contamination_with_xref(myst, expected):
    """Closing backtick of a cross-ref must not pair with inline code."""
    assert _convert(myst) == expected


def test_inline_code_no_match_across_newlines():
    text = "`start\nend`"
    assert _convert(text) == text


# ---- Idempotent pass-through for reST docstrings ---------------------------


@pytest.mark.parametrize(
    "text",
    [
        ":func:`~extra_platforms.is_linux`",
        ".. note::\n    Some content.",
        "`click here <https://example.com>`_",
        "Returns ``True`` if detected.",
        ":param name: The name.\n:returns: A value.",
    ],
    ids=["xref", "admonition", "link", "double-backtick", "field-list"],
)
def test_idempotent_rst_passthrough(text):
    assert _convert(text) == text


def test_idempotent_full_rst_docstring():
    """A complete reST docstring passes through unchanged."""
    text = (
        "Return :data:`True` if current architecture is"
        " :data:`~extra_platforms.ARM`.\n"
        "\n"
        ".. hint::\n"
        "    This is a fallback detection for generic ARM architecture."
        " It will return\n"
        "    ``True`` for any ARM architecture not specifically covered"
        " by the more precise\n"
        "    variants: :func:`~extra_platforms.is_aarch64`,"
        " :func:`~extra_platforms.is_armv5tel`.\n"
    )
    assert _convert(text) == text


# ---- Mixed MyST + reST (generated docstrings) ------------------------------


def test_mixed_myst_attribute_then_rst_metadata():
    """Simulates generate_docstring() output: MyST attribute docstring
    concatenated with reST metadata lines.
    """
    text = (
        "All BSD platforms.\n"
        "\n"
        ":::{note}\n"
        "Includes FreeBSD and macOS.\n"
        ":::\n"
        "\n"
        "- **ID**: ``bsd``\n"
        "- **Detection function**: :func:`~is_bsd`\n"
    )
    result = _convert(text)
    assert ".. note::" in result
    assert "    Includes FreeBSD and macOS." in result
    assert "- **ID**: ``bsd``" in result
    assert "- **Detection function**: :func:`~is_bsd`" in result


# ---- Realistic docstring patterns ------------------------------------------


def test_real_detection_function():
    myst = (
        "Return {data}`True` if current platform is"
        " {data}`~extra_platforms.ANDROID`.\n"
        "\n"
        ":::{seealso}\n"
        "Source:\n"
        "[kivy/utils.py](https://github.com/kivy/kivy/blob/master/kivy/utils.py)\n"
        ":::"
    )
    result = _convert(myst)
    assert ":data:`True`" in result
    assert ":data:`~extra_platforms.ANDROID`" in result
    assert ".. seealso::" in result
    assert (
        "    `kivy/utils.py"
        " <https://github.com/kivy/kivy/blob/master/kivy/utils.py>`_"
    ) in result


def test_real_group_with_wikipedia_link():
    myst = (
        "All BSD platforms.\n"
        "\n"
        ":::{note}\n"
        "Are considered of this family ([according Wikipedia]"
        "(https://en.wikipedia.org/wiki/Template:Unix)):\n"
        "\n"
        "- `386BSD` (`FreeBSD`, `NetBSD`)\n"
        "- `Darwin` (`macOS`, `iOS`)\n"
        ":::"
    )
    result = _convert(myst)
    assert ".. note::" in result
    assert (
        "    Are considered of this family"
        " (`according Wikipedia <https://en.wikipedia.org/wiki/Template:Unix>`_):"
    ) in result
    assert "    - ``386BSD`` (``FreeBSD``, ``NetBSD``)" in result


def test_real_caution_with_code_block():
    myst = (
        "Return {data}`True` if architecture is"
        " {data}`~extra_platforms.AARCH64`.\n"
        "\n"
        ":::{caution}\n"
        "`platform.machine()` returns different values depending on the OS:\n"
        "\n"
        "- Linux: `aarch64`\n"
        "- macOS: `arm64`\n"
        "- Windows: `ARM64`\n"
        ":::"
    )
    result = _convert(myst)
    assert ":data:`True`" in result
    assert ".. caution::" in result
    assert (
        "    ``platform.machine()`` returns different values"
        " depending on the OS:"
    ) in result
    assert "    - Linux: ``aarch64``" in result
