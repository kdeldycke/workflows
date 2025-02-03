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

RESERVED_MATRIX_KEYWORDS = ["include", "exclude"]


class Matrix(dict):
    """A matrix to used in a GitHub workflow."""

    include: set[dict[str:str]]
    exclude: set[dict[str:str]]

    def __init__(self):
        super().__init__()
        self.include = set()
        self.exclude = set()

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {super().__repr__()}; include={self.include!r}; exclude={self.exclude!r}>"

    def __str__(self) -> str:
        """Render matrix as a JSON string."""
        dict_copy = dict(self)
        if self.include:
            dict_copy["include"] = self.include
        if self.exclude:
            dict_copy["exclude"] = self.exclude
        return json.dumps(dict_copy, cls=MatrixEncoder)

    def __setattr__(self, name, value):
        return super().__setattr__(name, value)

    def add_variation(self, variation_id: str, values: Iterable[str]) -> None:
        if variation_id in RESERVED_MATRIX_KEYWORDS:
            raise ValueError(f"{variation_id} cannot be used as a variation ID")
        if not values:
            raise ValueError(f"No variation values provided: {values}")
        if set(map(type, values)) != {str}:
            raise ValueError(f"Only strings are accepted in {values}")
        self.setdefault(variation_id, set()).update(values)


class MatrixEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return sorted(obj)
        return super().default(obj)
