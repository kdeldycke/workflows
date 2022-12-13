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

"""Extract some metadata from Python projects to be used by GitHub workflows.

Outputs the following variables to the environment file (see:
https://docs.github.com/en/free-pro-team@latest/actions/reference/workflow-commands-for-github-actions#environment-files):

```text
python_files=".github/update_mailmap.py" ".github/update_changelog.py" ".github/python_metadata.py"
is_poetry_project=true
package_name=click-extra
nuitka_main_modules=["mail_deduplicate/cli.py", "meta_package_manager/__main__.py"]
black_params=--target-version py37 --target-version py38
mypy_params=--python-version 3.7
pyupgrade_params=--py37-plus
is_sphinx=true
active_autodoc=true
```

Automatic detection of minimal Python version is being discussed upstream for:
- `black` at https://github.com/psf/black/issues/3124
- `mypy` [rejected] at https://github.com/python/mypy/issues/13294
- `pyupgrade` [rejected] at https://github.com/asottile/pyupgrade/issues/688
"""

from __future__ import annotations

import ast
import json
import os
import sys
from pathlib import Path
from typing import Any, Generator, Iterable

if sys.version_info >= (3, 8):
    from functools import cached_property
else:
    cached_property = property


from poetry.core.constraints.version import (  # type: ignore[import]
    Version,
    VersionRange,
    parse_constraint,
)
from poetry.core.pyproject.toml import PyProjectTOML  # type: ignore[import]


class PythonMetadata:
    def __init__(self, debug: bool = False) -> None:
        self.debug = debug

    pyproject_path = Path() / "pyproject.toml"
    sphinx_conf_path = Path() / "docs" / "conf.py"

    @cached_property
    def python_files(self) -> Generator[Path, None, None]:
        # is_file() return False if the path doesn’t exist or is a broken symlink.
        yield from (p for p in Path().glob("**/*.py") if p.is_file())

    @cached_property
    def pyproject(self) -> PyProjectTOML:
        return PyProjectTOML(self.pyproject_path)

    @cached_property
    def is_poetry_project(self) -> bool:
        """Is the project relying on Poetry?"""
        if self.pyproject_path.exists() and self.pyproject_path.is_file():
            return self.pyproject.is_poetry_project()
        return False

    @cached_property
    def package_name(self) -> str | None:
        """Returns package name as published on PyPi."""
        if self.is_poetry_project:
            return self.pyproject.poetry_config["name"]
        return None

    @cached_property
    def script_entries(self) -> Generator[tuple[str, str, str], None, None]:
        """Returns a list of tuples containing the script name, its module and callable.

        .. code-block:: toml
            [tool.poetry.scripts]
            mdedup = "mail_deduplicate.cli:mdedup"
            mpm = "meta_package_manager.__main__:main"

        Yields:

        .. code-block:: python
            (
                ("mdedup", "mail_deduplicate.cli", "mdedup"),
                ("mpm", "meta_package_manager.__main__", "main"),
                ...
            )
        """
        if self.is_poetry_project:
            for cli_id, script in self.pyproject.poetry_config["scripts"].items():
                module_id, callable_id = script.split(":")
                yield cli_id, module_id, callable_id

    @cached_property
    def nuitka_main_modules(self) -> tuple[str]:
        """Returns the path of the modules to be compiled by Nuitka."""
        modules_path = []
        for _, module_id, _ in self.script_entries:
            module_path = Path(f"{module_id.replace('.', '/')}.py")
            assert module_path.exists()
            modules_path.append(module_path)
        return modules_path

    @cached_property
    def project_range(self) -> VersionRange | None:
        """Returns Python version support range."""
        if self.is_poetry_project:
            return parse_constraint(
                self.pyproject.poetry_config["dependencies"]["python"]
            )
        return None

    @cached_property
    def black_params(self) -> Generator[str, None, None]:
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
            black_range = (
                Version.from_parts(major=3, minor=minor) for minor in range(3, 11 + 1)
            )
            for version in black_range:
                if self.project_range.allows(version):
                    yield f"--target-version py{version.text.replace('.', '')}"

    @cached_property
    def mypy_param(self) -> str | None:
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
        pyupgrade_range = (
            Version.from_parts(major=3, minor=minor) for minor in range(6, 11 + 1)
        )
        min_version = Version.from_parts(major=3)
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

    @cached_property
    def is_sphinx(self) -> bool:
        # The Sphinx config file is present, that's enought for us.
        return self.sphinx_conf_path.exists() and self.sphinx_conf_path.is_file()

    @cached_property
    def active_autodoc(self) -> bool:
        if self.is_sphinx:
            # Look for list of active Sphinx extensions.
            for node in ast.parse(self.sphinx_conf_path.read_bytes()).body:
                if isinstance(node, ast.Assign) and isinstance(
                    node.value, (ast.List, ast.Tuple)
                ):
                    extension_found = "extensions" in (t.id for t in node.targets)  # type: ignore
                    if extension_found:
                        elements = (
                            e.value
                            for e in node.value.elts
                            if isinstance(e, ast.Constant)
                        )
                        if "sphinx.ext.autodoc" in elements:
                            return True
        return False

    @staticmethod
    def format_github_value(value: Any, force_json=False) -> str:
        """Transform Python value to GitHub-friendly, JSON-like, console string.

        Renders:
        - `str` as-is
        - `None` into emptry string
        - `bool` into lower-cased string
        - `Iterable` of strings into a serialized space-separated string
        - `Iterable` of `Path` into a serialized string whose items are space-separated and double-quoted
        """
        # Convert non-strings.
        if not isinstance(value, str):

            if value is None:
                value = ""

            elif isinstance(value, bool):
                value = str(value).lower()

            elif isinstance(value, Iterable):
                items = []
                for i in value:
                    # Wraps Path items with double-quotes.
                    if not force_json and isinstance(i, Path):
                        items.append(f'"{i}"')
                    # Cast item to string.
                    else:
                        items.append(str(i))

                # Serialize items with a space if non-json.
                if not force_json:
                    value = " ".join(items)
                else:
                    value = items

        if force_json:
            value = json.dumps(value)

        return value

    @cached_property
    def output_env_file(self) -> Path | None:
        """Returns the `Path` to the environment file pointed to by the `$GITHUB_OUTPUT` environment variable."""
        env_file = os.getenv("GITHUB_OUTPUT")
        if env_file:
            output_path = Path(env_file)
            assert output_path.is_file()
            return output_path

    def save_metadata(self):
        """Write data to the environment file pointed to by the `$GITHUB_OUTPUT` environment variable."""
        metadata = {
            "python_files": (self.python_files, False),
            "is_poetry_project": (self.is_poetry_project, False),
            "package_name": (self.package_name, False),
            "nuitka_main_modules": (self.nuitka_main_modules, True),
            "black_params": (self.black_params, False),
            "mypy_params": (self.mypy_param, False),
            "pyupgrade_params": (self.pyupgrade_param, False),
            "is_sphinx": (self.is_sphinx, False),
            "active_autodoc": (self.active_autodoc, False),
        }

        if self.debug:
            print(f"--- Writing into {self.output_env_file} ---")
        content = ""
        for name, (value, force_json) in metadata.items():
            content += f"{name}={self.format_github_value(value, force_json=force_json)}\n"
        if self.debug:
            print(content)
        self.output_env_file.write_text(content)

        if self.debug:
            print(f"--- Content of {self.output_env_file} ---")
            print(self.output_env_file.read_text())


# Output metadata with GitHub syntax.
metadata = PythonMetadata(debug=True)
metadata.save_metadata()
