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

"""Extract some metadata from repository and Python projects to be used by GitHub workflows.

The following variables are `printed to the environment file
<https://docs.github.com/en/free-pro-team@latest/actions/reference/workflow-commands-for-github-actions#environment-files>`_:

```text
new_commits=346ce664f055fbd042a25ee0b7e96702394d5e95 6f27db47612aaee06fdf361008744b09a9f5f6c2
release_commits=6f27db47612aaee06fdf361008744b09a9f5f6c2
python_files=".github/update_mailmap.py" ".github/update_changelog.py" ".github/python_metadata.py"
doc_files="changelog.md" "readme.md" "docs/license.md"
is_poetry_project=true
package_name=click-extra
black_params=--target-version py37 --target-version py38
mypy_params=--python-version 3.7
is_sphinx=true
active_autodoc=true
new_commits_matrix={"commit": ["346ce664f055fbd042a25ee0b7e96702394d5e95", "6f27db47612aaee06fdf361008744b09a9f5f6c2"], "include": [{"commit": "346ce664f055fbd042a25ee0b7e96702394d5e95", "short_sha": "346ce66"}, {"commit": "6f27db47612aaee06fdf361008744b09a9f5f6c2", "short_sha": "6f27db4"}]}
release_commits_matrix={"commit": ["6f27db47612aaee06fdf361008744b09a9f5f6c2"], "include": [{"commit": "6f27db47612aaee06fdf361008744b09a9f5f6c2", "short_sha": "6f27db4"}]}
nuitka_matrix={"entry_point": ["mpm"], "os": ["ubuntu-22.04", "macos-12", "windows-2022"], "arch": ["x64"], "include": [{"entry_point": "mpm", "cli_id": "mpm", "module_id": "meta_package_manager.__main__", "callable_id": "main", "module_path": "meta_package_manager/__main__.py"}, {"os": "ubuntu-22.04", "platform_id": "linux", "extension": "bin", "extra_python_params": ""}, {"os": "macos-12", "platform_id": "macos", "extension": "bin", "extra_python_params": ""}, {"os": "windows-2022", "platform_id": "windows", "extension": "exe", "extra_python_params": "-X utf8"}, {"entry_point": "mpm", "os": "ubuntu-22.04", "arch": "x64", "bin_name": "mpm-linux-x64-build-6f27db4.bin"}, {"entry_point": "mpm", "os": "macos-12", "arch": "x64", "bin_name": "mpm-macos-x64-build-6f27db4.bin"}, {"entry_point": "mpm", "os": "windows-2022", "arch": "x64", "bin_name": "mpm-windows-x64-build-6f27db4.exe"}]}
```

Automatic detection of minimal Python version is being discussed upstream for:
- `black` at https://github.com/psf/black/issues/3124
- `mypy` [rejected] at https://github.com/python/mypy/issues/13294
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys
from itertools import product
from pathlib import Path
from textwrap import dedent
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

SHORT_SHA_LENGTH = 7
"""Default SHA lentgth hard-coded to ``7``.

.. caution::

    The `default is subject to change <https://stackoverflow.com/a/21015031>`_ and
    depends on the size of the repository.
"""


TMatrix = dict[str, list[str] | list[dict[str, str]]]


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

    @staticmethod
    def sha_matrix(commits: Iterable[Commit] | None) -> TMatrix | None:
        """Pre-compute a matrix with long and short SHA values.

        Returns a ready-to-use matrix structure:

        .. code-block:: python
            {
                "commit": [
                    "346ce664f055fbd042a25ee0b7e96702394d5e95",
                    "6f27db47612aaee06fdf361008744b09a9f5f6c2",
                ],
                "include": [
                    {
                        "commit": "346ce664f055fbd042a25ee0b7e96702394d5e95",
                        "short_sha": "346ce66",
                    },
                    {
                        "commit": "6f27db47612aaee06fdf361008744b09a9f5f6c2",
                        "short_sha": "6f27db4",
                    },
                ],
            }
        """
        if not commits:
            return None
        sha_list = [commit.hash for commit in commits]
        return {
            "commit": sha_list,
            "include": [
                {
                    "commit": sha,
                    "short_sha": sha[:SHORT_SHA_LENGTH],
                }
                for sha in sha_list
            ],
        }

    @cached_property
    def commit_range(self) -> tuple[str, str] | None:
        """Range of commits bundled within the triggering event.

        A workflow run is triggered by a singular event, which might encapsulate one or
        more commits. This means the workflow will only run once on the last commit,
        even if multiple new commits where pushed.

        This is anoying when we want to keep a carefully constructed commit history,
        and want to run the workflow on each commit. The typical example is a pull
        request that is merged upstream but we'd like to produce artifacts (builds,
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
    def new_commits_matrix(self) -> TMatrix | None:
        """Pre-computed matrix with long and short SHA values of new commits."""
        return self.sha_matrix(self.new_commits)

    @cached_property
    def new_commits_hash(self) -> tuple[str, ...] | None:
        """List all hashes of new commits."""
        return (
            cast(tuple[str, ...], self.new_commits_matrix["commit"])
            if self.new_commits_matrix
            else None
        )

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
    def release_commits_matrix(self) -> TMatrix | None:
        """Pre-computed matrix with long and short SHA values of release commits."""
        return self.sha_matrix(self.release_commits)

    @cached_property
    def release_commits_hash(self) -> tuple[str, ...] | None:
        """List all hashes of release commits."""
        return (
            cast(tuple[str, ...], self.release_commits_matrix["commit"])
            if self.release_commits_matrix
            else None
        )

    def glob_files(self, *patterns: str) -> Generator[Path, None, None]:
        for pattern in patterns:
            # is_file() return False if the path doesn’t exist or is a broken symlink.
            yield from (p for p in Path().glob(pattern) if p.is_file())

    @cached_property
    def python_files(self) -> Generator[Path, None, None]:
        yield from self.glob_files("**/*.py")

    @cached_property
    def doc_files(self) -> Generator[Path, None, None]:
        yield from self.glob_files("**/*.md", "**/*.markdown", "**/*.rst", "**/*.tex")

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

        Results are derived from the script entries of ``pyproject.toml``. So that:

        .. code-block:: toml
            [tool.poetry.scripts]
            mdedup = "mail_deduplicate.cli:mdedup"
            mpm = "meta_package_manager.__main__:main"

        Yields:

        .. code-block:: python
            (
                ("mdedup", "mail_deduplicate.cli", "mdedup"),
                ("mpm", "meta_package_manager.__main__", "main"),
                ...,
            )
        """
        entries = []
        if self.is_poetry_project:
            for cli_id, script in self.pyproject.poetry_config.get(
                "scripts", {}
            ).items():
                module_id, callable_id = script.split(":")
                entries.append((cli_id, module_id, callable_id))
        # Double check we do not have duplicate entries.
        all_cli_ids = [cli_id for cli_id, _, _ in entries]
        assert len(set(all_cli_ids)) == len(all_cli_ids)
        return entries

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

        `You should include all Python versions that you want your code to run under
        <https://github.com/psf/black/issues/751#issuecomment-473066811>`_.

        .. tip::

            Can also be re-used both for:

            - `blacken-docs CLI <https://github.com/adamchainz/blacken-docs>`_.
            - `ruff CLI <https://github.com/charliermarsh/ruff/issues/2857>`_ (soon I hope).

        .. caution::

            Black supports auto-detection of the Python version targetted by your
            project (see `#3124 <https://github.com/psf/black/issues/3124>`_ and
            `#3219 <https://github.com/psf/black/pull/3219>`_), `since v23.1.0
            <https://github.com/psf/black/releases/tag/23.1.0>`_.

            But `only looks <https://github.com/psf/black/blob/b0d1fba/src/black/files.py#L141-L142>`_
            for the `PEP-621's requires-python marker
            <https://peps.python.org/pep-0621/#requires-python>`_ in the ``pyproject.toml`` file, i.e.:

            .. code-block:: toml
                [project]
                requires-python = ">=3.7,<3.11"

            Which means we still needs to resolves these Black parameters for Poetry-based projects.
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
                    extension_found = "extensions" in (
                        t.id for t in node.targets
                    )  # type: ignore
                    if extension_found:
                        elements = (
                            e.value
                            for e in node.value.elts
                            if isinstance(e, ast.Constant)
                        )
                        if "sphinx.ext.autodoc" in elements:
                            return True
        return False

    @cached_property
    def nuitka_matrix(self) -> TMatrix | None:
        """Pre-compute a matrix for Nuitka compilation workflows.

        Combine the variations of:
        - all new commits
        - all entry points
        - for the 3 main OSes
        - for a set of architectures

        Returns a ready-to-use matrix structure, where each variation is augmented with specific extra parameters
        by the way of matching parameters in the `include` directive.

        .. code-block:: python
            {
                "entry_point": ["mpm"],
                "commit": [
                    "346ce664f055fbd042a25ee0b7e96702394d5e95",
                    "6f27db47612aaee06fdf361008744b09a9f5f6c2",
                ],
                "os": ["ubuntu-22.04", "macos-12", "windows-2022"],
                "arch": ["x64"],
                "include": [
                    {
                        "entry_point": "mpm",
                        "cli_id": "mpm",
                        "module_id": "meta_package_manager.__main__",
                        "callable_id": "main",
                        "module_path": "meta_package_manager/__main__.py",
                    },
                    {
                        "commit": "346ce664f055fbd042a25ee0b7e96702394d5e95",
                        "short_sha": "346ce66",
                    },
                    {
                        "commit": "6f27db47612aaee06fdf361008744b09a9f5f6c2",
                        "short_sha": "6f27db4",
                    },
                    {
                        "os": "ubuntu-22.04",
                        "platform_id": "linux",
                        "extension": "bin",
                        "extra_python_params": "",
                    },
                    {
                        "os": "macos-12",
                        "platform_id": "macos",
                        "extension": "bin",
                        "extra_python_params": "",
                    },
                    {
                        "os": "windows-2022",
                        "platform_id": "windows",
                        "extension": "exe",
                        "extra_python_params": "-X utf8",
                    },
                    {
                        "entry_point": "mpm",
                        "commit": "346ce664f055fbd042a25ee0b7e96702394d5e95",
                        "os": "ubuntu-22.04",
                        "arch": "x64",
                        "bin_name": "mpm-linux-x64-build-346ce66.bin",
                    },
                    {
                        "entry_point": "mpm",
                        "commit": "346ce664f055fbd042a25ee0b7e96702394d5e95",
                        "os": "macos-12",
                        "arch": "x64",
                        "bin_name": "mpm-macos-x64-build-346ce66.bin",
                    },
                    {
                        "entry_point": "mpm",
                        "commit": "346ce664f055fbd042a25ee0b7e96702394d5e95",
                        "os": "windows-2022",
                        "arch": "x64",
                        "bin_name": "mpm-windows-x64-build-346ce66.exe",
                    },
                    {
                        "entry_point": "mpm",
                        "commit": "6f27db47612aaee06fdf361008744b09a9f5f6c2",
                        "os": "ubuntu-22.04",
                        "arch": "x64",
                        "bin_name": "mpm-linux-x64-build-6f27db4.bin",
                    },
                    {
                        "entry_point": "mpm",
                        "commit": "6f27db47612aaee06fdf361008744b09a9f5f6c2",
                        "os": "macos-12",
                        "arch": "x64",
                        "bin_name": "mpm-macos-x64-build-6f27db4.bin",
                    },
                    {
                        "entry_point": "mpm",
                        "commit": "6f27db47612aaee06fdf361008744b09a9f5f6c2",
                        "os": "windows-2022",
                        "arch": "x64",
                        "bin_name": "mpm-windows-x64-build-6f27db4.exe",
                    },
                ],
            }
        """
        RESERVED_MATRIX_KEYWORDS = ["include", "exclude"]

        # Only produce a matrix if the project is providing CLI entry points.
        if not self.script_entries:
            return None

        # In the future, we might support and bridge tha t matrix with the full CPython
        # platform support list. See target triples at:
        # https://peps.python.org/pep-0011/
        # https://snarky.ca/webassembly-and-its-platform-targets/
        matrix: dict[str, list[Any]] = {
            "entry_point": [],
            # Run the compilation on the latest supported version of each OS.
            "os": [
                "ubuntu-22.04",
                "macos-12",
                "windows-2022",
            ],
            # Arch values are aligned to those specified for self-hosted runners:
            # https://docs.github.com/en/actions/hosting-your-own-runners/about-self-hosted-runners#architectures
            "arch": [
                "x64",
                # XXX GitHub-hosted runners only supports x64.
                # "ARM64"
                # "ARM32"
                # XXX GitHub-hosted macOS runners with Apple silicon are planned in the future:
                # https://github.com/github/roadmap/issues/528
                # https://github.com/actions/runner-images/issues/2187
                # https://github.com/actions/runner/issues/805
            ],
            # Extra parameters.
            "include": [],
        }

        # Augment each entry point with some metadata.
        extra_entry_point_params = []
        for cli_id, module_id, callable_id in self.script_entries:
            # CLI ID is supposed to be unique, we'll use that as a key.
            matrix["entry_point"].append(cli_id)
            # Derive CLI module path from its ID.
            # XXX We consider here the module is directly callable, because Nuitka
            # doesn't seems to support the entry-point notation.
            module_path = Path(f"{module_id.replace('.', '/')}.py")
            assert module_path.exists()
            extra_entry_point_params.append(
                {
                    "entry_point": cli_id,
                    "cli_id": cli_id,
                    "module_id": module_id,
                    "callable_id": callable_id,
                    "module_path": str(module_path),
                }
            )
        matrix["include"].extend(extra_entry_point_params)

        # We'd like to run a build for each commit bundled in the action trigger.
        if self.new_commits_matrix:
            matrix["commit"] = self.new_commits_matrix["commit"]
            matrix["include"].extend(self.new_commits_matrix["include"])

        # Add platform-specific variables.
        extra_os_params = [
            {
                "os": "ubuntu-22.04",
                "platform_id": "linux",
                "extension": "bin",
                "extra_python_params": "",
            },
            {
                "os": "macos-12",
                "platform_id": "macos",
                "extension": "bin",
                "extra_python_params": "",
            },
            {
                "os": "windows-2022",
                "platform_id": "windows",
                "extension": "exe",
                # XXX "-X utf8" parameter is a workaround for Windows runners
                # redirecting the output of commands to files. See:
                # https://github.com/databrickslabs/dbx/issues/455#issuecomment-1312770919
                # https://github.com/pallets/click/issues/2121#issuecomment-1312773882
                # https://gist.github.com/NodeJSmith/e7e37f2d3f162456869f015f842bcf15
                # https://github.com/Nuitka/Nuitka/blob/ca1ec9e/nuitka/utils/ReExecute.py#L73-L74
                "extra_python_params": "-X utf8",
            },
        ]
        matrix["include"].extend(extra_os_params)

        # Check no extra parameter in reserved directive do not override themselves.
        all_extra_keys = set().union(
            *(
                extras.keys()
                for reserved_key in RESERVED_MATRIX_KEYWORDS
                if reserved_key in matrix
                for extras in matrix[reserved_key]
            )
        )
        assert all_extra_keys.isdisjoint(RESERVED_MATRIX_KEYWORDS)

        # Produce all variations encoded by the matrix, by skipping the special
        # directives.
        all_variations = tuple(
            tuple((variant_id, value) for value in variant_values)
            for variant_id, variant_values in matrix.items()
            if variant_id not in RESERVED_MATRIX_KEYWORDS
        )

        # Emulate collection and aggregation of the 'include' directive to all
        # variations produced by the matrix.
        for variant in product(*all_variations):
            variant_dict = dict(variant)

            # Check each extra parameters from the 'include' directive and accumulate
            # the matching ones to the variant.
            full_variant = variant_dict.copy()
            for extra_params in matrix["include"]:
                # Check if the variant match the extra parameters.
                dimensions_to_match = set(variant_dict).intersection(extra_params)
                d0 = {key: variant_dict[key] for key in dimensions_to_match}
                d1 = {key: extra_params[key] for key in dimensions_to_match}
                # Extra parameters are matchin the current variant, merge their values.
                if d0 == d1:
                    full_variant.update(extra_params)

            # Add to the 'include' directive a new extra parameter that match the
            # current variant.
            extra_name_param = variant_dict.copy()
            # Generate for Nuitka the binary file name to be used that is unique to
            # this variant.
            extra_name_param["bin_name"] = (
                "{cli_id}-{platform_id}-{arch}-build-{short_sha}.{extension}"
            ).format(**full_variant)
            matrix["include"].append(extra_name_param)

        return matrix

    @cached_property
    def release_notes(self) -> str:
        """Generate notes to be attached to the GitHub release."""
        # Generate a link to the version of the package published on PyPi.
        pypi_link = ""
        if self.package_name and self.tagged_version:
            pypi_link = dedent(
                f"""\
                [🐍 Available on PyPi](https://pypi.org/project/{self.package_name}/{self.tagged_version}).
                """
            )

        # Assemble the release notes.
        notes = dedent(
            f"""\
            {pypi_link}
            """
        )
        return notes

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
            "doc_files": (self.doc_files, False),
            "is_poetry_project": (self.is_poetry_project, False),
            "package_name": (self.package_name, False),
            "black_params": (self.black_params, False),
            "mypy_params": (self.mypy_param, False),
            "is_sphinx": (self.is_sphinx, False),
            "active_autodoc": (self.active_autodoc, False),
        }

        # Structured metadata to be rendered as JSON.
        json_metadata = {
            "new_commits_matrix": self.new_commits_matrix,
            "release_commits_matrix": self.release_commits_matrix,
            "nuitka_matrix": self.nuitka_matrix,
        }
        for name, data_dict in json_metadata.items():
            metadata[name] = (data_dict, True) if data_dict else (None, False)

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
