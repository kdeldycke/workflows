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

from __future__ import annotations

from pathlib import Path

import pytest

from repomatic.prebake import prebake_version


@pytest.fixture
def init_file(tmp_path: Path):
    """Helper that creates a temporary __init__.py with the given content."""

    def _make(content: str) -> Path:
        p = tmp_path / "__init__.py"
        p.write_text(content, encoding="utf-8")
        return p

    return _make


def test_dev_version_prebaked(init_file):
    """A .dev version gets +hash appended."""
    p = init_file('__version__ = "1.0.0.dev0"\n')
    result = prebake_version(p, git_hash="abc1234")
    assert result == "1.0.0.dev0+abc1234"
    assert '__version__ = "1.0.0.dev0+abc1234"' in p.read_text()


def test_dev_version_single_quotes(init_file):
    """Single-quoted __version__ is also handled."""
    p = init_file("__version__ = '2.0.0.dev5'\n")
    result = prebake_version(p, git_hash="f00baa")
    assert result == "2.0.0.dev5+f00baa"
    assert "__version__ = '2.0.0.dev5+f00baa'" in p.read_text()


def test_already_prebaked_skipped(init_file):
    """A version with existing + is left untouched."""
    p = init_file('__version__ = "1.0.0.dev0+existing"\n')
    result = prebake_version(p, git_hash="abc1234")
    assert result is None
    assert '__version__ = "1.0.0.dev0+existing"' in p.read_text()


def test_release_version_skipped(init_file):
    """A release version (no .dev) is not modified."""
    p = init_file('__version__ = "3.2.1"\n')
    result = prebake_version(p, git_hash="abc1234")
    assert result is None
    assert '__version__ = "3.2.1"' in p.read_text()


def test_no_version_in_file(init_file):
    """A file without __version__ returns None."""
    p = init_file('"""Just a docstring."""\n')
    result = prebake_version(p, git_hash="abc1234")
    assert result is None


def test_no_git_hash_returns_none(init_file):
    """Without a hash and no git, returns None."""
    p = init_file('__version__ = "1.0.0.dev0"\n')
    result = prebake_version(p, git_hash=None)
    # May or may not succeed depending on whether git is available in the
    # test environment.  If running inside a git repo it will succeed; if not,
    # it returns None.  Either outcome is acceptable.
    if result is None:
        assert '__version__ = "1.0.0.dev0"' in p.read_text()
    else:
        assert "+" in result


def test_idempotent(init_file):
    """Running prebake twice does not double-suffix."""
    p = init_file('__version__ = "1.0.0.dev0"\n')
    first = prebake_version(p, git_hash="abc1234")
    assert first == "1.0.0.dev0+abc1234"
    second = prebake_version(p, git_hash="def5678")
    assert second is None
    assert '__version__ = "1.0.0.dev0+abc1234"' in p.read_text()


def test_surrounding_content_preserved(init_file):
    """Content around __version__ is not disturbed."""
    content = (
        '"""My package."""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        '__version__ = "4.0.0.dev0"\n'
        "\n"
        "API_URL = 'https://example.com'\n"
    )
    p = init_file(content)
    prebake_version(p, git_hash="cafe123")
    result = p.read_text()
    assert '__version__ = "4.0.0.dev0+cafe123"' in result
    assert "from __future__ import annotations" in result
    assert "API_URL = 'https://example.com'" in result
