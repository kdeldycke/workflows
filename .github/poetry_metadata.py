# Copyright Kevin Deldycke <kevin@deldycke.com> and contributors.
# All Rights Reserved.
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

"""Extract some Poetry metadata to be used by GitHub workflows.

Prints:
```text
::set-output name=is_poetry_project::true
::set-output name=package_name::click-extra
::set-output name=black_params::--target-version py37 --target-version py38
::set-output name=mypy_params::--python-version 3.7
::set-output name=pyupgrade_params::--py37-plus
```

Automatic detection of minimal Python version is being discussed upstream for:
- `black` at https://github.com/psf/black/issues/3124
- `mypy` [rejected] at https://github.com/python/mypy/issues/13294
- `pyupgrade` [rejected] at https://github.com/asottile/pyupgrade/issues/688
"""

import sys
from pathlib import Path
from typing import Optional

if sys.version_info >= (3, 8):
    from functools import cached_property
else:
    cached_property = property


from poetry.core.pyproject.toml import PyProjectTOML  # type: ignore
from poetry.core.semver import Version, VersionRange, parse_constraint  # type: ignore


class PoetryMetadata:

    toml_path = Path("./pyproject.toml")

    @cached_property
    def pyproject(self) -> PyProjectTOML:
        return PyProjectTOML(self.toml_path)

    @cached_property
    def is_poetry_project(self) -> bool:
        """Is the project relying on Poetry?"""
        if self.toml_path.exists() and self.toml_path.is_file():
            return self.pyproject.is_poetry_project()
        return False

    @cached_property
    def package_name(self) -> Optional[str]:
        """Returns package name as published on PyPi."""
        if self.is_poetry_project:
            return self.pyproject.poetry_config["name"]
        return None

    @cached_property
    def project_range(self) -> Optional[VersionRange]:
        """Returns Python version support range."""
        if self.is_poetry_project:
            return parse_constraint(
                self.pyproject.poetry_config["dependencies"]["python"]
            )
        return None

    @cached_property
    def black_params(self) -> list[str]:
        """Generates `black` parameters.

        Black should be fed with a subset of these parameters:
        - `--target-version py33`
        - `--target-version py34`
        - `--target-version py35`
        - `--target-version py36`
        - `--target-version py37`
        - `--target-version py38`
        - `--target-version py39`
        - `--target-version py310`
        - `--target-version py311`

        `You should include all Python versions that you want your code to run under.`,
        as per: https://github.com/psf/black/issues/751
        """
        if self.project_range:
            black_range = (Version(3, minor) for minor in range(3, 11 + 1))
            for version in black_range:
                if self.project_range.allows(version):
                    yield f"--target-version py{version.text.replace('.', '')}"

    @cached_property
    def mypy_param(self) -> Optional[str]:
        """Generates `mypy` parameter.

        Mypy needs to be fed with this parameter: `--python-version x.y`.
        """
        if self.project_range:
            return f"--python-version {self.project_range.min.major}.{self.project_range.min.minor}"
        return None

    @cached_property
    def pyupgrade_param(self) -> str:
        """Generates `pyupgrade` parameter.

        Pyupgrade needs to be fed with one of these parameters:
        - `--py3-plus`
        - `--py36-plus`
        - `--py37-plus`
        - `--py38-plus`
        - `--py39-plus`
        - `--py310-plus`
        - `--py311-plus`

        Defaults to `--py3-plus`.

        """
        pyupgrade_range = (Version(3, minor) for minor in range(6, 11 + 1))
        min_version = Version(3)
        if self.project_range:
            # XXX Pyupgrade will remove Python < 3.x support in Pyupgrade 3.x. See:
            # https://github.com/asottile/pyupgrade/blob/b91f0527127f59d4b7e22157d8ee1884966025a5/pyupgrade/_main.py#L491-L494
            if self.project_range.min.major < 3:
                min_version = None
            for version in pyupgrade_range:
                if self.project_range.allows(version):
                    min_version = version
                    break
        return f"--py{min_version.text.replace('.', '')}-plus"


metadata = PoetryMetadata()

# Render some types into strings.
is_poetry_project_str = str(metadata.is_poetry_project).lower()
black_params_str = " ".join(metadata.black_params)

# Output metadata with GitHub syntax.
print(f"::set-output name=is_poetry_project::{is_poetry_project_str}")
print(f"::set-output name=package_name::{metadata.package_name}")
print(f"::set-output name=black_params::{black_params_str}")
print(f"::set-output name=mypy_params::{metadata.mypy_param}")
print(f"::set-output name=pyupgrade_params::{metadata.pyupgrade_param}")

# Print summary for debug.
print(f"Is project poetry-based? {is_poetry_project_str}")
print(f"Package name: {metadata.package_name}")
print(f"Black parameters: {black_params_str}")
print(f"Mypy parameters: {metadata.mypy_param}")
print(f"Pyupgrade parameters: {metadata.pyupgrade_param}")
