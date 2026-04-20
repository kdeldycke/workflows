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

"""Utilities for reading and interpreting `pyproject.toml` metadata.

Provides standalone functions for extracting project name and source paths
from `pyproject.toml`. These functions have no dependency on the
{class}`~repomatic.metadata.Metadata` singleton and can be used independently.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from packaging.utils import canonicalize_name

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Any

    from .config import Config


def derive_source_paths(
    pyproject_data: dict[str, Any] | None = None,
) -> list[str]:
    """Derive source code directory name from `[project.name]`.

    Converts the project name to its importable form by replacing hyphens with
    underscores — the universal Python convention that all build backends
    (setuptools, hatchling, flit, uv) follow by default. For example,
    `name = "extra-platforms"` yields `["extra_platforms"]`.

    :param pyproject_data: Pre-parsed `pyproject.toml` dict. If `None`,
        reads from the current working directory.
    :return: Single-element list with the source directory name, or an empty
        list if no project name is defined.
    """
    if pyproject_data is None:
        pyproject_path = Path() / "pyproject.toml"
        if not (pyproject_path.exists() and pyproject_path.is_file()):
            return []
        pyproject_data = tomllib.loads(pyproject_path.read_text(encoding="UTF-8"))

    name = pyproject_data.get("project", {}).get("name")
    if not name:
        return []
    # PEP 503 normalization (lowercases, collapses [-_.] to hyphens), then
    # convert to the Python import form (underscores).
    return [canonicalize_name(name).replace("-", "_")]


def resolve_source_paths(
    config: Config,
    pyproject_data: dict[str, Any] | None = None,
) -> list[str] | None:
    """Resolve workflow source paths from config or auto-derivation.

    :param config: Loaded `Config` instance from `[tool.repomatic]`.
    :param pyproject_data: Pre-parsed `pyproject.toml` dict for derivation.
    :return: List of source directory names, or `None` when no source paths
        can be determined (paths should be stripped entirely).
    """
    configured = config.workflow.source_paths
    if configured is not None:
        return configured if configured else None
    derived = derive_source_paths(pyproject_data)
    return derived if derived else None


def get_project_name(
    pyproject_data: dict[str, Any] | None = None,
) -> str | None:
    """Read the project name from `pyproject.toml`.

    :param pyproject_data: Pre-parsed dict. If `None`, reads from CWD.
    """
    if pyproject_data is None:
        pyproject_path = Path() / "pyproject.toml"
        if not (pyproject_path.exists() and pyproject_path.is_file()):
            return None
        pyproject_data = tomllib.loads(pyproject_path.read_text(encoding="UTF-8"))
    name: str | None = pyproject_data.get("project", {}).get("name")
    if name:
        logging.debug(f"Project name from pyproject.toml: {name}")
    return name
