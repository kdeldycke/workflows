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

import json
from typing import Iterable

from boltons.iterutils import unique  # type: ignore[import-untyped]

RESERVED_MATRIX_KEYWORDS = ["include", "exclude"]


class Matrix(dict):
    """A matrix as defined by GitHub actions workflows.

    See: https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/running-variations-of-jobs-in-a-workflow
    """

    # Special directives are tuples to:
    # - make the matrix immutable and prevent users meddling with our internals (unless
    #   using the proper update methods)
    # - keep items ordered by their insertion into the matrix
    include: tuple[dict[str:str], ...] = tuple()
    exclude: tuple[dict[str:str], ...] = tuple()

    def matrix(
        self, ignore_includes: bool = False, ignore_excludes: bool = False
    ) -> dict[str:str]:
        """Returns a copy of the matrix.

        The special ``include`` and ``excludes`` directives will be added by default.
        You can selectively ignore them by passing the corresponding parameters.
        """
        dict_copy = dict(self)
        if not ignore_includes and self.include:
            dict_copy["include"] = self.include
        if not ignore_excludes and self.exclude:
            dict_copy["exclude"] = self.exclude
        return dict_copy

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}: {super().__repr__()}; "
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
        if set(map(type, values)) != {str}:
            raise ValueError(f"Only strings are accepted in {values}")
        # Extend variation with values, and deduplicate them along the way.
        var_values = list(self.get(variation_id, [])) + list(values)
        self[variation_id] = tuple(unique(var_values))

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
        self, ignore_includes: bool = False, ignore_excludes: bool = False
    ) -> dict[str : tuple[str, ...]]:
        """Return all variations encountered in the matrix.

        Extra variations mentioned in the special ``include`` and ``excludes``
        directives will be taken into account by default. You can selectively ignore
        them by passing the corresponding parameters.
        """
        variations = {k: list(v) for k, v in self.items()}

        for ignore, directive_values in (
            (ignore_includes, self.include),
            (ignore_excludes, self.exclude),
        ):
            if not ignore:
                for value in directive_values:
                    for k, v in value.items():
                        variations.setdefault(k, []).append(v)

        return {k: tuple(unique(v)) for k, v in variations.items()}

    def product(
        self, ignore_includes: bool = False, ignore_excludes: bool = False
    ) -> Iterator[dict[str:str]]:
        yield from map(
            dict,
            itertools.product(
                *(
                    tuple((variant_id, value) for value in variant_values)
                    for variant_id, variant_values in self.all_variations(
                        ignore_includes=ignore_includes, ignore_excludes=ignore_excludes
                    ).items()
                )
            ),
        )
