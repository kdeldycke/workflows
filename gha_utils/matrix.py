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

import itertools
import json
import logging
from typing import Iterable, Iterator

from boltons.dictutils import FrozenDict  # type: ignore[import-untyped]
from boltons.iterutils import unique  # type: ignore[import-untyped]

RESERVED_MATRIX_KEYWORDS = ["include", "exclude"]


class Matrix(FrozenDict):
    """A matrix as defined by GitHub's actions workflows.

    See GitHub official documentation on `how-to implement variations of jobs in a
    workflow
    <https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/running-variations-of-jobs-in-a-workflow>`_.

    This Matrix behave like a ``dict`` and works everywhere a ``dict`` would. Only that
    it is immutable and based on :class:`FrozenDict`. If you want to populate the matrix
    you have to use the following methods:

    - :meth:`add_variation`
    - :meth:`add_includes`
    - :meth:`add_excludes`

    The implementation respects the order in which items were inserted. This provides a
    natural and visual sorting that should ease the inspection and debugging of large
    matrix.
    """

    # Tuples are used to keep track of the insertion order and force immutability.
    include: tuple[dict[str:str], ...] = tuple()
    exclude: tuple[dict[str:str], ...] = tuple()

    def matrix(
        self, ignore_includes: bool = False, ignore_excludes: bool = False
    ) -> dict[str:str]:
        """Returns a copy of the matrix.

        The special ``include`` and ``excludes`` directives will be added by default.
        You can selectively ignore them by passing the corresponding boolean parameters.
        """
        dict_copy = dict(self)
        if not ignore_includes and self.include:
            dict_copy["include"] = self.include
        if not ignore_excludes and self.exclude:
            dict_copy["exclude"] = self.exclude
        return dict_copy

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}: {super(FrozenDict, self).__repr__()}; "
            f"include={self.include}; exclude={self.exclude}>"
        )

    def __str__(self) -> str:
        """Render matrix as a JSON string."""
        return json.dumps(self.matrix())

    @staticmethod
    def _check_ids(*var_ids: str) -> None:
        for var_id in var_ids:
            if var_id in RESERVED_MATRIX_KEYWORDS:
                raise ValueError(f"{var_id} cannot be used as a variation ID")

    def add_variation(self, variation_id: str, values: Iterable[str]) -> None:
        self._check_ids(variation_id)
        if not values:
            raise ValueError(f"No variation values provided: {values}")
        if any(type(v) is not str for v in values):
            raise ValueError(f"Only strings are accepted in {values}")
        # Extend variation with values, and deduplicate them along the way.
        var_values = list(self.get(variation_id, [])) + list(values)
        super(FrozenDict, self).__setitem__(variation_id, tuple(unique(var_values)))

    def _add_and_dedup_dicts(
        self, *new_dicts: dict[str:str]
    ) -> tuple[dict[str:str], ...]:
        self._check_ids(*(k for d in new_dicts for k in d))
        return tuple(
            dict(items) for items in unique((tuple(d.items()) for d in new_dicts))
        )

    def add_includes(self, *new_includes: dict[str:str]) -> None:
        """Add one or more ``include`` special directives to the matrix."""
        self.include = self._add_and_dedup_dicts(*self.include, *new_includes)

    def add_excludes(self, *new_excludes: dict[str:str]) -> None:
        """Add one or more ``exclude`` special directives to the matrix."""
        self.exclude = self._add_and_dedup_dicts(*self.exclude, *new_excludes)

    def all_variations(
        self, with_includes: bool = False, with_excludes: bool = False
    ) -> dict[str : tuple[str, ...]]:
        """Returns all variations encountered in the matrix.

        Extra variations mentioned in the special ``include`` and ``excludes``
        directives will be ignored by default. You can selectively have them expand the
        inventory of variations by passing the corresponding boolean parameters to the
        method.
        """
        variations = {k: list(v) for k, v in self.items()}

        for expand, directives in (
            (with_includes, self.include),
            (with_excludes, self.exclude),
        ):
            if not expand:
                continue
            for value in directives:
                for k, v in value.items():
                    variations.setdefault(k, []).append(v)

        return {k: tuple(unique(v)) for k, v in variations.items()}

    def product(
        self, with_includes: bool = False, with_excludes: bool = False
    ) -> Iterator[dict[str:str]]:
        """Only returns the combinations of the base matrix by default.

        You can optionnally add any variation referenced in the ``include`` and ``exclude`` special directives.

        Respects the order of variations and their values.
        """
        variations = self.all_variations(
            with_includes=with_includes, with_excludes=with_excludes
        )
        if not variations:
            return
        yield from map(
            dict,
            itertools.product(
                *(
                    tuple((variant_id, variation) for variation in variant_values)
                    for variant_id, variant_values in variations.items()
                )
            ),
        )

    def solve(self) -> Iterator[dict[str:str]]:
        """Returns all combinations of matrix variations while applying ``include`` and ``exclude`` constraints.

        .. caution::
            All ``include`` combinations are processed after ``exclude``. This allows
            you to use ``include`` to add back combinations that were previously excluded.
        """
        counter = 0

        # inclusion_filters = {set(d.items()) for d in self.include}
        exclusion_filters = {frozenset(d.items()) for d in self.exclude}


        var2 = self.all_variations()

        # Search for include directives not applicables to any of base matrix's variations, and put them on the side.
        applicable_includes = []
        unapplicable_includes = []

        if not var2:
            unapplicable_includes = self.include

        else:
            for include in self.include:
                matching_keys = set(include).intersection(var2)

                if not matching_keys or all(
                    include[k] in var2[k] for k in matching_keys
                ):
                    applicable_includes.append(include)
                else:
                    unapplicable_includes.append(include)

        # Include and exclude directives only applies to variations of the base matrix.
        for base_variations in self.product():
            # Skip sets matching exclusion criterions.
            if any(f.issubset(base_variations.items()) for f in exclusion_filters):
                continue

            updated_variations = base_variations.copy()
            for include in applicable_includes:
                # No variant IDs match any of the base variation, so we can update the variation with it.
                if set(include).isdisjoint(base_variations):
                    if set(include).isdisjoint(updated_variations):
                        updated_variations.update(include)
                    continue

                if all(
                    base_variations[k] == include[k]
                    for k in set(include).intersection(base_variations)
                ):
                    updated_variations.update(include)

            yield updated_variations

            counter += 1
            if counter == 256:
                logging.warning("GitHub workflow matrix limits of 256 jobs reached")

        yield from unapplicable_includes
