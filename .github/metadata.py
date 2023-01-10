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

"""Extract some metadata from repository and Python projects to be used by GitHub workflows.

The following variables are `printed to the environment file
<https://docs.github.com/en/free-pro-team@latest/actions/reference/workflow-commands-for-github-actions#environment-files>`_:

```text
new_commits=346ce664f055fbd042a25ee0b7e96702394d5e95 6f27db47612aaee06fdf361008744b09a9f5f6c2
release_commits=6f27db47612aaee06fdf361008744b09a9f5f6c2
python_files=".github/update_mailmap.py" ".github/update_changelog.py" ".github/python_metadata.py"
is_poetry_project=true
package_name=click-extra
black_params=--target-version py37 --target-version py38
mypy_params=--python-version 3.7
pyupgrade_params=--py37-plus
is_sphinx=true
active_autodoc=true
new_commits_matrix={"commit": ["346ce664f055fbd042a25ee0b7e96702394d5e95", "6f27db47612aaee06fdf361008744b09a9f5f6c2"]}
release_commits_matrix={"commit": ["6f27db47612aaee06fdf361008744b09a9f5f6c2"]}
nuitka_entry_points={"entry_point": ["mail_deduplicate/cli.py", "meta_package_manager/__main__.py"]}
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
import re
import sys
from pathlib import Path
from typing import Any, Generator, Iterable, cast

if sys.version_info >= (3, 8):
    from functools import cached_property
else:
    # Don't bother caching on older Python versions.
    cached_property = property

import black
from mypy.defaults import PYTHON3_VERSION_MIN
from poetry.core.constraints.version import Version, VersionConstraint, parse_constraint
from poetry.core.pyproject.toml import PyProjectTOML
from pydriller import Commit, Repository  # type: ignore[import]


class Metadata:
    def __init__(self, debug: bool = False) -> None:
        self.debug = debug

    pyproject_path = Path() / "pyproject.toml"
    sphinx_conf_path = Path() / "docs" / "conf.py"

    @cached_property
    def github_context(self) -> dict[str, Any]:
        """Load GitHub context from the environment.

        Expect ``GITHUB_CONTEXT`` to be set as part of the environment. I.e., adds the
        following as part of your job step calling this script:

        .. code-block:: yaml

            - name: Project metadata
              id: project-metadata
              env:
                GITHUB_CONTEXT: ${{ toJSON(github) }}
              run: >
                python -c "$(curl -fsSL
                https://raw.githubusercontent.com/kdeldycke/workflows/main/.github/metadata.py)"
        """
        if "GITHUB_CONTEXT" not in os.environ:
            message = (
                "⚠️  Missing GitHub context in environment. "
                "Did you forget to set GITHUB_CONTEXT?"
            )
            if self.debug:
                print(message, file=sys.stderr)
                return {}
            else:
                raise RuntimeError(message)
        context = json.loads(os.environ["GITHUB_CONTEXT"])
        if self.debug:
            print("--- GitHub context ---")
            print(json.dumps(context, indent=4))
        return context

    @cached_property
    def commit_range(self) -> tuple[str, str] | None:
        """Range of commits bundled within the triggering event.

        A workflow run is triggered by a singular event, which might encapsulate one or
        more commits. This means the workflow will only run once on the last commit,
        even if multiple new commits where pushed.

        This is anoying when we want to keep a carefully constructed commit history,
        and want to run the workflow on each commit. The typical example is a pull
        request that is merged upstream but we'd like to produce artefacts (builds,
        packages, etc.) for each individual commit.

        The default ``GITHUB_SHA`` environment variable is useless as it only points to
        the last commit. We need to inspect the commit history to find all new one. New
        commits needs to be fetched differently in ``push`` and ``pull_requests``
        events.

        .. seealso::

            - https://stackoverflow.com/a/67204539
            - https://stackoverflow.com/a/62953566
            - https://stackoverflow.com/a/61861763
        """
        if not self.github_context:
            return None
        # Pull request event.
        if self.github_context["base_ref"]:
            start = f"origin/{self.github_context['base_ref']}"
            # We need to checkout the HEAD commit instead of the artificial merge
            # commit introduced by the pull request.
            end = self.github_context["event"]["pull_request"]["head"]["sha"]
        # Push event.
        else:
            start = self.github_context["event"]["before"]
            end = self.github_context["sha"]
        print("--- Commit range ---")
        print(f"Range start: {start}")
        print(f"Range end: {end}")
        return start, end

    @cached_property
    def new_commits(self) -> tuple[Commit, ...] | None:
        """Returns list of ``Commit`` objects bundled within the triggering event."""
        if not self.commit_range:
            return None
        start, end = self.commit_range
        # Remove the last commit, as the commit range is inclusive.
        return tuple(
            Repository(
                ".", from_commit=start, to_commit=end, order="reverse"
            ).traverse_commits()
        )[:-1]

    @cached_property
    def new_commits_hash(self) -> tuple[str, ...] | None:
        """List all commit hashes bundled within the triggering event."""
        if not self.new_commits:
            return None
        return tuple(commit.hash for commit in self.new_commits)

    @cached_property
    def release_commits(self) -> tuple[Commit, ...] | None:
        """Returns list of ``Commit`` objects to be tagged within the triggering event.

        We cannot identify a release commit based the presence of a ``vX.Y.Z`` tag
        alone. That's because it is not present in the ``prepare-release`` pull request
        produced by the ``changelog.yaml`` workflow. The tag is produced later on by
        the ``release.yaml`` workflow, when the pull request is merged to ``main``.

        Our best second option is to identify a release based on the full commit
        message, based on the template used in the ``changelog.yaml`` workflow.
        """
        if not self.new_commits:
            return None
        return tuple(
            commit
            for commit in self.new_commits
            if re.fullmatch(
                r"^\[changelog\] Release v[0-9]+\.[0-9]+\.[0-9]+$", commit.msg
            )
        )

    @cached_property
    def release_commits_hash(self) -> tuple[str, ...] | None:
        """List all release commit hashes bundled within the triggering event."""
        if not self.release_commits:
            return None
        return tuple(commit.hash for commit in self.release_commits)

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
            return cast(str, self.pyproject.poetry_config["name"])
        return None

    @cached_property
    def script_entries(self) -> list[tuple[str, str, str]]:
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
        entries = []
        if self.is_poetry_project:
            for cli_id, script in self.pyproject.poetry_config.get(
                "scripts", {}
            ).items():
                module_id, callable_id = script.split(":")
                entries.append((cli_id, module_id, callable_id))
        return entries

    @cached_property
    def nuitka_entry_points(self) -> list[str]:
        """Returns the path of the modules to be compiled by Nuitka, each prefixed with their CLI ID."""
        modules_path = []
        for cli_id, module_id, _ in self.script_entries:
            module_path = Path(f"{module_id.replace('.', '/')}.py")
            assert module_path.exists()
            # Serialize CLI ID and main module path.
            modules_path.append(f"{cli_id}:{module_path}")
        return modules_path

    @cached_property
    def project_range(self) -> VersionConstraint | None:
        """Returns Python version support range."""
        constraint = None
        if self.is_poetry_project:
            constraint = parse_constraint(
                self.pyproject.poetry_config["dependencies"]["python"]
            )
        if constraint and not constraint.is_empty():
            return constraint
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
            minor_range = sorted(v.value for v in black.TargetVersion)
            black_range = (
                Version.from_parts(major=3, minor=minor) for minor in minor_range
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
            if self.project_range.is_simple():
                major = self.project_range.major  # type: ignore[attr-defined]
                minor = self.project_range.minor  # type: ignore[attr-defined]
            else:
                major = self.project_range.min.major  # type: ignore[attr-defined]
                minor = self.project_range.min.minor  # type: ignore[attr-defined]
            # Mypy's lowest supported version of Python dialect.
            major = max(major, PYTHON3_VERSION_MIN[0])
            minor = max(minor, PYTHON3_VERSION_MIN[1])
            return f"--python-version {major}.{minor}"
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
    def format_github_value(value: Any, render_json=False) -> str:
        """Transform Python value to GitHub-friendly, JSON-like, console string.

        Renders:
        - `str` as-is
        - `None` into emptry string
        - `bool` into lower-cased string
        - `Iterable` of strings into a serialized space-separated string
        - `Iterable` of `Path` into a serialized string whose items are space-separated and double-quoted
        """
        if render_json:
            return json.dumps(value)

        # Convert non-strings.
        if not isinstance(value, str):

            if value is None:
                value = ""

            elif isinstance(value, bool):
                value = str(value).lower()

            elif isinstance(value, dict):
                raise NotImplementedError

            elif isinstance(value, Iterable):
                # Cast all items to string, wrapping Path items with double-quotes.
                items = ((f'"{i}"' if isinstance(i, Path) else str(i)) for i in value)
                value = " ".join(items)

        return cast(str, value)

    @cached_property
    def output_env_file(self) -> Path | None:
        """Returns the `Path` to the environment file pointed to by the `$GITHUB_OUTPUT` environment variable."""
        output_path = None
        env_file = os.getenv("GITHUB_OUTPUT")
        if env_file:
            output_path = Path(env_file)
            assert output_path.is_file()
        return output_path

    def save_metadata(self):
        """Write data to the environment file pointed to by the `$GITHUB_OUTPUT` environment variable."""
        # Plain metadata.
        metadata = {
            "new_commits": (self.new_commits_hash, False),
            "release_commits": (self.release_commits_hash, False),
            "python_files": (self.python_files, False),
            "is_poetry_project": (self.is_poetry_project, False),
            "package_name": (self.package_name, False),
            "black_params": (self.black_params, False),
            "mypy_params": (self.mypy_param, False),
            "pyupgrade_params": (self.pyupgrade_param, False),
            "is_sphinx": (self.is_sphinx, False),
            "active_autodoc": (self.active_autodoc, False),
        }

        # Structured metadata to be rendered as JSON.
        json_metadata = {
            "new_commits_matrix": ("commit", self.new_commits_hash),
            "release_commits_matrix": ("commit", self.release_commits_hash),
            "nuitka_entry_points": ("entry_point", self.nuitka_entry_points),
        }

        for name, (key, value) in json_metadata.items():
            metadata[name] = ({key: value}, True) if value else (None, False)

        if self.debug:
            print(f"--- Writing into {self.output_env_file} ---")
        content = ""
        for name, (value, render_json) in metadata.items():
            content += (
                f"{name}={self.format_github_value(value, render_json=render_json)}\n"
            )
        if self.debug:
            print(content)
        if not self.output_env_file:
            raise FileNotFoundError(
                "No output file specified by $GITHUB_OUTPUT environment variable."
            )
        self.output_env_file.write_text(content)

        if self.debug:
            print(f"--- Content of {self.output_env_file} ---")
            print(self.output_env_file.read_text())


# Output metadata with GitHub syntax.
metadata = Metadata(debug=True)
metadata.save_metadata()
