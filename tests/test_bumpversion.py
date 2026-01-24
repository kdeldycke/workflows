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
"""Tests for bundled bumpversion configuration."""

from __future__ import annotations

import sys

import pytest

from gha_utils.version_config import get_bumpversion_content

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]


def test_get_bumpversion_content_returns_string() -> None:
    """Verify that get_bumpversion_content returns a non-empty string."""
    content = get_bumpversion_content()
    assert isinstance(content, str)
    assert len(content) > 0


def test_bumpversion_content_is_valid_toml() -> None:
    """Verify that the returned content is valid TOML."""
    content = get_bumpversion_content()
    parsed = tomllib.loads(content)
    assert isinstance(parsed, dict)


def test_bumpversion_content_has_tool_section() -> None:
    """Verify that the configuration has the expected [tool.bumpversion] section."""
    content = get_bumpversion_content()
    parsed = tomllib.loads(content)

    assert "tool" in parsed
    assert "bumpversion" in parsed["tool"]


def test_bumpversion_content_has_required_settings() -> None:
    """Verify that the configuration has the required bumpversion settings."""
    content = get_bumpversion_content()
    parsed = tomllib.loads(content)

    bumpversion = parsed["tool"]["bumpversion"]

    # Check required top-level settings.
    assert "current_version" in bumpversion
    assert "allow_dirty" in bumpversion
    assert "ignore_missing_files" in bumpversion


def test_bumpversion_content_has_files_section() -> None:
    """Verify that the configuration has file patterns defined."""
    content = get_bumpversion_content()
    parsed = tomllib.loads(content)

    bumpversion = parsed["tool"]["bumpversion"]

    # Check that files array exists and has entries.
    assert "files" in bumpversion
    assert isinstance(bumpversion["files"], list)
    assert len(bumpversion["files"]) > 0


@pytest.mark.parametrize(
    "expected_pattern",
    [
        "__init__.py",
        "pyproject.toml",
        "changelog.md",
        "citation.cff",
    ],
)
def test_bumpversion_content_has_expected_file_patterns(expected_pattern: str) -> None:
    """Verify that the configuration includes expected file patterns."""
    content = get_bumpversion_content()
    assert expected_pattern in content
