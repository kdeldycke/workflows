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

import pytest

from gha_utils.matrix import Matrix


def test_matrix():
    m = Matrix()

    assert m == dict()

    assert hasattr(m, "include")
    assert hasattr(m, "exclude")
    assert m.include == set()
    assert m.exclude == set()

    m.add_variation("foo", ["a", "b", "c"])
    assert m == {"foo": {"a", "b", "c"}}
    assert not m.include
    assert not m.exclude

    m.add_variation("foo", ["a", "a", "d"])
    assert m == {"foo": {"a", "b", "c", "d"}}
    assert not m.include
    assert not m.exclude

    with pytest.raises(ValueError):
        m.add_variation("variation_1", None)

    with pytest.raises(ValueError):
        m.add_variation("variation_1", [])

    with pytest.raises(ValueError):
        m.add_variation("variation_1", [None])

    with pytest.raises(ValueError):
        m.add_variation("include", ["a", "b", "c"])

    with pytest.raises(ValueError):
        m.add_variation("exclude", ["a", "b", "c"])

    assert str(m) == '{"foo": ["a", "b", "c", "d"]}'
