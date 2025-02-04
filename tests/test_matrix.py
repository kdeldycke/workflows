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
    matrix = Matrix()

    assert matrix == dict()

    assert hasattr(matrix, "include")
    assert hasattr(matrix, "exclude")
    assert matrix.include == tuple()
    assert matrix.exclude == tuple()

    matrix.add_variation("foo", ["a", "b", "c"])
    assert matrix == {"foo": ("a", "b", "c")}
    assert not matrix.include
    assert not matrix.exclude

    # Natural deduplication.
    matrix.add_variation("foo", ["a", "a", "d"])
    assert matrix == {"foo": ("a", "b", "c", "d")}
    assert not matrix.include
    assert not matrix.exclude

    assert matrix.matrix() == {"foo": ("a", "b", "c", "d")}

    assert str(matrix) == '{"foo": ["a", "b", "c", "d"]}'
    assert (
        repr(matrix)
        == "<Matrix: {'foo': ('a', 'b', 'c', 'd')}; include=(); exclude=()>"
    )

    with pytest.raises(ValueError):
        matrix.add_variation("variation_1", None)

    with pytest.raises(ValueError):
        matrix.add_variation("variation_1", [])

    with pytest.raises(ValueError):
        matrix.add_variation("variation_1", [None])

    with pytest.raises(ValueError):
        matrix.add_variation("include", ["a", "b", "c"])

    with pytest.raises(ValueError):
        matrix.add_variation("exclude", ["a", "b", "c"])


def test_includes():
    matrix = Matrix()

    matrix.add_variation("foo", ["a", "b", "c"])
    assert matrix.matrix() == {"foo": ("a", "b", "c")}

    # First addition.
    matrix.add_includes({"foo": "a", "bar": "1"})
    assert matrix.matrix() == {
        "foo": ("a", "b", "c"),
        "include": ({"foo": "a", "bar": "1"},),
    }

    # Second addition is cumulative.
    matrix.add_includes({"foo": "b", "bar": "2"})
    assert matrix.matrix() == {
        "foo": ("a", "b", "c"),
        "include": ({"foo": "a", "bar": "1"}, {"foo": "b", "bar": "2"}),
    }

    # Deduplication.
    matrix.add_includes({"foo": "b", "bar": "2"})
    assert matrix.matrix() == {
        "foo": ("a", "b", "c"),
        "include": ({"foo": "a", "bar": "1"}, {"foo": "b", "bar": "2"}),
    }

    # Rendering.
    assert (
        str(matrix) == '{"foo": ["a", "b", "c"], '
        '"include": [{"foo": "a", "bar": "1"}, {"foo": "b", "bar": "2"}]}'
    )
    assert (
        repr(matrix) == "<Matrix: {'foo': ('a', 'b', 'c')}; "
        "include=({'foo': 'a', 'bar': '1'}, {'foo': 'b', 'bar': '2'}); exclude=()>"
    )

    # Multiple insertions.
    matrix.add_includes({"foo": "c", "bar": "3"}, {"foo": "d", "bar": "4"})
    assert matrix.matrix() == {
        "foo": ("a", "b", "c"),
        "include": (
            {"foo": "a", "bar": "1"},
            {"foo": "b", "bar": "2"},
            {"foo": "c", "bar": "3"},
            {"foo": "d", "bar": "4"},
        ),
    }

    # Forbidden values.
    with pytest.raises(ValueError):
        matrix.add_includes({"include": "random"})
    with pytest.raises(ValueError):
        matrix.add_includes({"exclude": "random"})


def test_excludes():
    matrix = Matrix()

    matrix.add_variation("foo", ["a", "b", "c"])
    assert matrix.matrix() == {"foo": ("a", "b", "c")}

    # First addition.
    matrix.add_excludes({"foo": "a", "bar": "1"})
    assert matrix.matrix() == {
        "foo": ("a", "b", "c"),
        "exclude": ({"foo": "a", "bar": "1"},),
    }

    # Second addition is cumulative.
    matrix.add_excludes({"foo": "b", "bar": "2"})
    assert matrix.matrix() == {
        "foo": ("a", "b", "c"),
        "exclude": ({"foo": "a", "bar": "1"}, {"foo": "b", "bar": "2"}),
    }

    # Deduplication.
    matrix.add_excludes({"foo": "b", "bar": "2"})
    assert matrix.matrix() == {
        "foo": ("a", "b", "c"),
        "exclude": ({"foo": "a", "bar": "1"}, {"foo": "b", "bar": "2"}),
    }

    # Rendering.
    assert (
        str(matrix) == '{"foo": ["a", "b", "c"], '
        '"exclude": [{"foo": "a", "bar": "1"}, {"foo": "b", "bar": "2"}]}'
    )
    assert (
        repr(matrix) == "<Matrix: {'foo': ('a', 'b', 'c')}; "
        "include=(); exclude=({'foo': 'a', 'bar': '1'}, {'foo': 'b', 'bar': '2'})>"
    )

    # Multiple insertions.
    matrix.add_excludes({"foo": "c", "bar": "3"}, {"foo": "d", "bar": "4"})
    assert matrix.matrix() == {
        "foo": ("a", "b", "c"),
        "exclude": (
            {"foo": "a", "bar": "1"},
            {"foo": "b", "bar": "2"},
            {"foo": "c", "bar": "3"},
            {"foo": "d", "bar": "4"},
        ),
    }

    # Forbidden values.
    with pytest.raises(ValueError):
        matrix.add_excludes({"include": "random"})
    with pytest.raises(ValueError):
        matrix.add_excludes({"exclude": "random"})


def test_all_variations():
    matrix = Matrix()

    assert matrix.all_variations() == {}

    matrix.add_variation("foo", ["a", "b", "c"])
    matrix.add_variation("bar", ["1", "2", "3"])

    matrix.add_includes(
        {"foo": "b", "color": "green"},
        {"foo": "d", "color": "orange"},
        {"bar": "1", "shape": "triangle"},
        {"size": "small"},
    )
    matrix.add_excludes(
        {"foo": "b", "shape": "circle"},
        {"bar": "2", "color": "blue"},
        {"bar": "4", "color": "yellow"},
        {"weight": "heavy"},
    )

    assert matrix.matrix() == {
        "foo": ("a", "b", "c"),
        "bar": ("1", "2", "3"),
        "include": (
            {"foo": "b", "color": "green"},
            {"foo": "d", "color": "orange"},
            {"bar": "1", "shape": "triangle"},
            {"size": "small"},
        ),
        "exclude": (
            {"foo": "b", "shape": "circle"},
            {"bar": "2", "color": "blue"},
            {"bar": "4", "color": "yellow"},
            {"weight": "heavy"},
        ),
    }

    assert matrix.matrix(ignore_includes=True) == {
        "foo": ("a", "b", "c"),
        "bar": ("1", "2", "3"),
        "exclude": (
            {"foo": "b", "shape": "circle"},
            {"bar": "2", "color": "blue"},
            {"bar": "4", "color": "yellow"},
            {"weight": "heavy"},
        ),
    }

    assert matrix.matrix(ignore_excludes=True) == {
        "foo": ("a", "b", "c"),
        "bar": ("1", "2", "3"),
        "include": (
            {"foo": "b", "color": "green"},
            {"foo": "d", "color": "orange"},
            {"bar": "1", "shape": "triangle"},
            {"size": "small"},
        ),
    }

    assert matrix.matrix(ignore_includes=True, ignore_excludes=True) == {
        "foo": ("a", "b", "c"),
        "bar": ("1", "2", "3"),
    }

    assert matrix.all_variations() == {
        "foo": ("a", "b", "c"),
        "bar": ("1", "2", "3"),
    }

    assert matrix.all_variations(with_includes=True) == {
        "foo": ("a", "b", "c", "d"),
        "bar": ("1", "2", "3"),
        "color": ("green", "orange"),
        "shape": ("triangle",),
        "size": ("small",),
    }

    assert matrix.all_variations(with_excludes=True) == {
        "foo": ("a", "b", "c"),
        "bar": ("1", "2", "3", "4"),
        "shape": ("circle",),
        "color": ("blue", "yellow"),
        "weight": ("heavy",),
    }

    assert matrix.all_variations(with_excludes=True, with_includes=True) == {
        "foo": ("a", "b", "c", "d"),
        "bar": ("1", "2", "3", "4"),
        "color": ("green", "orange", "blue", "yellow"),
        "shape": ("triangle", "circle"),
        "size": ("small",),
        "weight": ("heavy",),
    }


def test_product():
    matrix = Matrix()

    assert tuple(matrix.product()) == tuple()

    matrix.add_variation("foo", ["a", "b"])
    matrix.add_variation("bar", ["1", "2"])

    assert tuple(matrix.product()) == (
        {"foo": "a", "bar": "1"},
        {"foo": "a", "bar": "2"},
        {"foo": "b", "bar": "1"},
        {"foo": "b", "bar": "2"},
    )

    matrix.add_includes(
        {"foo": "b", "baz": "W"},
        {"foo": "c", "baz": "X"},
        {"bar": "1", "qux": "福"},
        {"@": "$"},
    )
    matrix.add_excludes(
        {"foo": "b", "qux": "子"},
        {"bar": "2", "baz": "Y"},
        {"bar": "3", "baz": "Z"},
        {"E": "O"},
    )

    assert tuple(matrix.product()) == (
        {"foo": "a", "bar": "1"},
        {"foo": "a", "bar": "2"},
        {"foo": "b", "bar": "1"},
        {"foo": "b", "bar": "2"},
    )

    assert tuple(matrix.product(with_includes=True)) == (
        {"foo": "a", "bar": "1", "baz": "W", "qux": "福", "@": "$"},
        {"foo": "a", "bar": "1", "baz": "X", "qux": "福", "@": "$"},
        {"foo": "a", "bar": "2", "baz": "W", "qux": "福", "@": "$"},
        {"foo": "a", "bar": "2", "baz": "X", "qux": "福", "@": "$"},
        {"foo": "b", "bar": "1", "baz": "W", "qux": "福", "@": "$"},
        {"foo": "b", "bar": "1", "baz": "X", "qux": "福", "@": "$"},
        {"foo": "b", "bar": "2", "baz": "W", "qux": "福", "@": "$"},
        {"foo": "b", "bar": "2", "baz": "X", "qux": "福", "@": "$"},
        {"foo": "c", "bar": "1", "baz": "W", "qux": "福", "@": "$"},
        {"foo": "c", "bar": "1", "baz": "X", "qux": "福", "@": "$"},
        {"foo": "c", "bar": "2", "baz": "W", "qux": "福", "@": "$"},
        {"foo": "c", "bar": "2", "baz": "X", "qux": "福", "@": "$"},
    )

    assert tuple(matrix.product(with_excludes=True)) == (
        {"foo": "a", "bar": "1", "qux": "子", "baz": "Y", "E": "O"},
        {"foo": "a", "bar": "1", "qux": "子", "baz": "Z", "E": "O"},
        {"foo": "a", "bar": "2", "qux": "子", "baz": "Y", "E": "O"},
        {"foo": "a", "bar": "2", "qux": "子", "baz": "Z", "E": "O"},
        {"foo": "a", "bar": "3", "qux": "子", "baz": "Y", "E": "O"},
        {"foo": "a", "bar": "3", "qux": "子", "baz": "Z", "E": "O"},
        {"foo": "b", "bar": "1", "qux": "子", "baz": "Y", "E": "O"},
        {"foo": "b", "bar": "1", "qux": "子", "baz": "Z", "E": "O"},
        {"foo": "b", "bar": "2", "qux": "子", "baz": "Y", "E": "O"},
        {"foo": "b", "bar": "2", "qux": "子", "baz": "Z", "E": "O"},
        {"foo": "b", "bar": "3", "qux": "子", "baz": "Y", "E": "O"},
        {"foo": "b", "bar": "3", "qux": "子", "baz": "Z", "E": "O"},
    )

    assert tuple(matrix.product(with_includes=True, with_excludes=True)) == (
        {"foo": "a", "bar": "1", "baz": "W", "qux": "福", "@": "$", "E": "O"},
        {"foo": "a", "bar": "1", "baz": "W", "qux": "子", "@": "$", "E": "O"},
        {"foo": "a", "bar": "1", "baz": "X", "qux": "福", "@": "$", "E": "O"},
        {"foo": "a", "bar": "1", "baz": "X", "qux": "子", "@": "$", "E": "O"},
        {"foo": "a", "bar": "1", "baz": "Y", "qux": "福", "@": "$", "E": "O"},
        {"foo": "a", "bar": "1", "baz": "Y", "qux": "子", "@": "$", "E": "O"},
        {"foo": "a", "bar": "1", "baz": "Z", "qux": "福", "@": "$", "E": "O"},
        {"foo": "a", "bar": "1", "baz": "Z", "qux": "子", "@": "$", "E": "O"},
        {"foo": "a", "bar": "2", "baz": "W", "qux": "福", "@": "$", "E": "O"},
        {"foo": "a", "bar": "2", "baz": "W", "qux": "子", "@": "$", "E": "O"},
        {"foo": "a", "bar": "2", "baz": "X", "qux": "福", "@": "$", "E": "O"},
        {"foo": "a", "bar": "2", "baz": "X", "qux": "子", "@": "$", "E": "O"},
        {"foo": "a", "bar": "2", "baz": "Y", "qux": "福", "@": "$", "E": "O"},
        {"foo": "a", "bar": "2", "baz": "Y", "qux": "子", "@": "$", "E": "O"},
        {"foo": "a", "bar": "2", "baz": "Z", "qux": "福", "@": "$", "E": "O"},
        {"foo": "a", "bar": "2", "baz": "Z", "qux": "子", "@": "$", "E": "O"},
        {"foo": "a", "bar": "3", "baz": "W", "qux": "福", "@": "$", "E": "O"},
        {"foo": "a", "bar": "3", "baz": "W", "qux": "子", "@": "$", "E": "O"},
        {"foo": "a", "bar": "3", "baz": "X", "qux": "福", "@": "$", "E": "O"},
        {"foo": "a", "bar": "3", "baz": "X", "qux": "子", "@": "$", "E": "O"},
        {"foo": "a", "bar": "3", "baz": "Y", "qux": "福", "@": "$", "E": "O"},
        {"foo": "a", "bar": "3", "baz": "Y", "qux": "子", "@": "$", "E": "O"},
        {"foo": "a", "bar": "3", "baz": "Z", "qux": "福", "@": "$", "E": "O"},
        {"foo": "a", "bar": "3", "baz": "Z", "qux": "子", "@": "$", "E": "O"},
        {"foo": "b", "bar": "1", "baz": "W", "qux": "福", "@": "$", "E": "O"},
        {"foo": "b", "bar": "1", "baz": "W", "qux": "子", "@": "$", "E": "O"},
        {"foo": "b", "bar": "1", "baz": "X", "qux": "福", "@": "$", "E": "O"},
        {"foo": "b", "bar": "1", "baz": "X", "qux": "子", "@": "$", "E": "O"},
        {"foo": "b", "bar": "1", "baz": "Y", "qux": "福", "@": "$", "E": "O"},
        {"foo": "b", "bar": "1", "baz": "Y", "qux": "子", "@": "$", "E": "O"},
        {"foo": "b", "bar": "1", "baz": "Z", "qux": "福", "@": "$", "E": "O"},
        {"foo": "b", "bar": "1", "baz": "Z", "qux": "子", "@": "$", "E": "O"},
        {"foo": "b", "bar": "2", "baz": "W", "qux": "福", "@": "$", "E": "O"},
        {"foo": "b", "bar": "2", "baz": "W", "qux": "子", "@": "$", "E": "O"},
        {"foo": "b", "bar": "2", "baz": "X", "qux": "福", "@": "$", "E": "O"},
        {"foo": "b", "bar": "2", "baz": "X", "qux": "子", "@": "$", "E": "O"},
        {"foo": "b", "bar": "2", "baz": "Y", "qux": "福", "@": "$", "E": "O"},
        {"foo": "b", "bar": "2", "baz": "Y", "qux": "子", "@": "$", "E": "O"},
        {"foo": "b", "bar": "2", "baz": "Z", "qux": "福", "@": "$", "E": "O"},
        {"foo": "b", "bar": "2", "baz": "Z", "qux": "子", "@": "$", "E": "O"},
        {"foo": "b", "bar": "3", "baz": "W", "qux": "福", "@": "$", "E": "O"},
        {"foo": "b", "bar": "3", "baz": "W", "qux": "子", "@": "$", "E": "O"},
        {"foo": "b", "bar": "3", "baz": "X", "qux": "福", "@": "$", "E": "O"},
        {"foo": "b", "bar": "3", "baz": "X", "qux": "子", "@": "$", "E": "O"},
        {"foo": "b", "bar": "3", "baz": "Y", "qux": "福", "@": "$", "E": "O"},
        {"foo": "b", "bar": "3", "baz": "Y", "qux": "子", "@": "$", "E": "O"},
        {"foo": "b", "bar": "3", "baz": "Z", "qux": "福", "@": "$", "E": "O"},
        {"foo": "b", "bar": "3", "baz": "Z", "qux": "子", "@": "$", "E": "O"},
        {"foo": "c", "bar": "1", "baz": "W", "qux": "福", "@": "$", "E": "O"},
        {"foo": "c", "bar": "1", "baz": "W", "qux": "子", "@": "$", "E": "O"},
        {"foo": "c", "bar": "1", "baz": "X", "qux": "福", "@": "$", "E": "O"},
        {"foo": "c", "bar": "1", "baz": "X", "qux": "子", "@": "$", "E": "O"},
        {"foo": "c", "bar": "1", "baz": "Y", "qux": "福", "@": "$", "E": "O"},
        {"foo": "c", "bar": "1", "baz": "Y", "qux": "子", "@": "$", "E": "O"},
        {"foo": "c", "bar": "1", "baz": "Z", "qux": "福", "@": "$", "E": "O"},
        {"foo": "c", "bar": "1", "baz": "Z", "qux": "子", "@": "$", "E": "O"},
        {"foo": "c", "bar": "2", "baz": "W", "qux": "福", "@": "$", "E": "O"},
        {"foo": "c", "bar": "2", "baz": "W", "qux": "子", "@": "$", "E": "O"},
        {"foo": "c", "bar": "2", "baz": "X", "qux": "福", "@": "$", "E": "O"},
        {"foo": "c", "bar": "2", "baz": "X", "qux": "子", "@": "$", "E": "O"},
        {"foo": "c", "bar": "2", "baz": "Y", "qux": "福", "@": "$", "E": "O"},
        {"foo": "c", "bar": "2", "baz": "Y", "qux": "子", "@": "$", "E": "O"},
        {"foo": "c", "bar": "2", "baz": "Z", "qux": "福", "@": "$", "E": "O"},
        {"foo": "c", "bar": "2", "baz": "Z", "qux": "子", "@": "$", "E": "O"},
        {"foo": "c", "bar": "3", "baz": "W", "qux": "福", "@": "$", "E": "O"},
        {"foo": "c", "bar": "3", "baz": "W", "qux": "子", "@": "$", "E": "O"},
        {"foo": "c", "bar": "3", "baz": "X", "qux": "福", "@": "$", "E": "O"},
        {"foo": "c", "bar": "3", "baz": "X", "qux": "子", "@": "$", "E": "O"},
        {"foo": "c", "bar": "3", "baz": "Y", "qux": "福", "@": "$", "E": "O"},
        {"foo": "c", "bar": "3", "baz": "Y", "qux": "子", "@": "$", "E": "O"},
        {"foo": "c", "bar": "3", "baz": "Z", "qux": "福", "@": "$", "E": "O"},
        {"foo": "c", "bar": "3", "baz": "Z", "qux": "子", "@": "$", "E": "O"},
    )


def test_solve_includes():
    matrix = Matrix()

    matrix.add_variation("fruit", ["apple", "pear"])
    matrix.add_variation("animal", ["cat", "dog"])

    matrix.add_includes(
        {"color": "green"},
        {"color": "pink", "animal": "cat"},
        {"fruit": "apple", "shape": "circle"},
        {"fruit": "banana"},
        {"fruit": "banana", "animal": "cat"},
    )

    assert tuple(matrix.solve()) == (
        {"fruit": "apple", "animal": "cat", "color": "pink", "shape": "circle"},
        {"fruit": "apple", "animal": "dog", "color": "green", "shape": "circle"},
        {"fruit": "pear", "animal": "cat", "color": "pink"},
        {"fruit": "pear", "animal": "dog", "color": "green"},
        {"fruit": "banana"},
        {"fruit": "banana", "animal": "cat"},
    )


def test_solve_expanded_configuration():
    matrix = Matrix()

    matrix.add_variation("os", ["windows-latest", "ubuntu-latest"])
    matrix.add_variation("node", ["14", "16"])

    matrix.add_includes({"os": "windows-latest", "node": "16", "npm": "6"})

    assert tuple(matrix.solve()) == (
        {"os": "windows-latest", "node": "14"},
        {"os": "windows-latest", "node": "16", "npm": "6"},
        {"os": "ubuntu-latest", "node": "14"},
        {"os": "ubuntu-latest", "node": "16"},
    )


def test_solve_extended_configuration():
    matrix = Matrix()

    matrix.add_variation("os", ["macos-latest", "windows-latest"])
    matrix.add_variation("version", ["12", "14", "16"])

    matrix.add_includes({"os": "windows-latest", "version": "17"})

    assert tuple(matrix.solve()) == (
        {"os": "macos-latest", "version": "12"},
        {"os": "macos-latest", "version": "14"},
        {"os": "macos-latest", "version": "16"},
        {"os": "windows-latest", "version": "12"},
        {"os": "windows-latest", "version": "14"},
        {"os": "windows-latest", "version": "16"},
        {"os": "windows-latest", "version": "17"},
    )


def test_solve_empty_matrix():
    matrix = Matrix()

    matrix.add_includes(
        {"site": "production", "datacenter": "site-a"},
        {"site": "staging", "datacenter": "site-b"},
    )

    assert tuple(matrix.solve()) == (
        {"site": "production", "datacenter": "site-a"},
        {"site": "staging", "datacenter": "site-b"},
    )


def test_solve_excludes():
    matrix = Matrix()

    matrix.add_variation("os", ["macos-latest", "windows-latest"])
    matrix.add_variation("version", ["12", "14", "16"])
    matrix.add_variation("environment", ["staging", "production"])

    matrix.add_excludes(
        {"os": "macos-latest", "version": "12", "environment": "production"},
        {"os": "windows-latest", "version": "16"},
    )

    assert tuple(matrix.solve()) == (
        {"os": "macos-latest", "version": "12", "environment": "staging"},
        # {"os": "macos-latest", "version": "12", "environment": "production"},
        {"os": "macos-latest", "version": "14", "environment": "staging"},
        {"os": "macos-latest", "version": "14", "environment": "production"},
        {"os": "macos-latest", "version": "16", "environment": "staging"},
        {"os": "macos-latest", "version": "16", "environment": "production"},
        {"os": "windows-latest", "version": "12", "environment": "staging"},
        {"os": "windows-latest", "version": "12", "environment": "production"},
        {"os": "windows-latest", "version": "14", "environment": "staging"},
        {"os": "windows-latest", "version": "14", "environment": "production"},
        # {"os": "windows-latest", "version": "16", "environment": "staging"},
        # {"os": "windows-latest", "version": "16", "environment": "production"},
    )
