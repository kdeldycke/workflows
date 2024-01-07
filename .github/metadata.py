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

"""Extract metadata from repository and Python projects to be used by GitHub workflows.

The following variables are `printed to the environment file
<https://docs.github.com/en/free-pro-team@latest/actions/reference/workflow-commands-for-github-actions#environment-files>`_:

```text
new_commits=346ce664f055fbd042a25ee0b7e96702e95 6f27db47612aaee06fdf08744b09a9f5f6c2
release_commits=6f27db47612aaee06fdf08744b09a9f5f6c2
python_files=".github/update_mailmap.py" ".github/metadata.py" "setup.py"
doc_files="changelog.md" "readme.md" "docs/license.md"
is_poetry_project=true
package_name=click-extra
blacken_docs_params=--target-version py37 --target-version py38
ruff_py_version=py37
mypy_params=--python-version 3.7
current_version=2.0.1
released_version=2.0.0
is_sphinx=true
active_autodoc=true
release_notes=[🐍 Available on PyPi](https://pypi.org/project/click-extra/2.21.3).
new_commits_matrix={'commit': ['346ce664f055fbd042a25ee0b7e96702e95',
                               '6f27db47612aaee06fdf08744b09a9f5f6c2'],
                    'include': [{'commit': '346ce664f055fbd042a25ee0b7e96702e95',
                                 'short_sha': '346ce66',
                                 'current_version': '2.0.1'},
                                {'commit': '6f27db47612aaee06fdf08744b09a9f5f6c2',
                                 'short_sha': '6f27db4',
                                 'current_version': '2.0.0'}]}
release_commits_matrix={'commit': ['6f27db47612aaee06fdf08744b09a9f5f6c2'],
                        'include': [{'commit': '6f27db47612aaee06fdf08744b09a9f5f6c2',
                                     'short_sha': '6f27db4',
                                     'current_version': '2.0.0'}]}
nuitka_matrix={'entry_point': ['mpm'],
               'os': ['ubuntu-22.04', 'macos-13', 'windows-2022'],
               'arch': ['x64'],
               'include': [{'entry_point': 'mpm',
                            'cli_id': 'mpm',
                            'module_id': 'meta_package_manager.__main__',
                            'callable_id': 'main',
                            'module_path': 'meta_package_manager/__main__.py'},
                           {'os': 'ubuntu-22.04',
                            'platform_id': 'linux',
                            'extension': 'bin',
                            'extra_python_params': ''},
                           {'os': 'macos-13',
                            'platform_id': 'macos',
                            'extension': 'bin',
                            'extra_python_params': ''},
                           {'os': 'windows-2022',
                            'platform_id': 'windows',
                            'extension': 'exe',
                            'extra_python_params': '-X utf8'},
                           {'entry_point': 'mpm',
                            'os': 'ubuntu-22.04',
                            'arch': 'x64',
                            'bin_name': 'mpm-linux-x64-build-6f27db4.bin'},
                           {'entry_point': 'mpm',
                            'os': 'macos-13',
                            'arch': 'x64',
                            'bin_name': 'mpm-macos-x64-build-6f27db4.bin'},
                           {'entry_point': 'mpm',
                            'os': 'windows-2022',
                            'arch': 'x64',
                            'bin_name': 'mpm-windows-x64-build-6f27db4.exe'}]}
```

.. warning::

    The ``new_commits_matrix``, ``release_commits_matrix`` and ``nuitka_matrix``
    variables in the block above are pretty-printed for readability. They are not
    actually formatted this way in the environment file, but inlined.
"""

# pylint: disable=fixme,no-name-in-module,too-many-public-methods

from __future__ import annotations

import ast
import json
import os
import re
import sys
from collections.abc import Generator, Iterable
from functools import cached_property
from itertools import product
from pathlib import Path
from random import randint
from re import escape
from textwrap import dedent
from typing import Any, cast

from black.mode import TargetVersion
from bumpversion.config import get_configuration  # type: ignore[import-untyped]
from bumpversion.config.files import find_config_file  # type: ignore[import-untyped]
from bumpversion.show import resolve_name  # type: ignore[import-untyped]
from mypy.defaults import PYTHON3_VERSION_MIN
from poetry.core.constraints.version import Version, VersionConstraint, parse_constraint
from poetry.core.pyproject.toml import PyProjectTOML
from pydriller import Commit, Git, Repository  # type: ignore[import]

SHORT_SHA_LENGTH = 7
"""Default SHA length hard-coded to ``7``.

.. caution::

    The `default is subject to change <https://stackoverflow.com/a/21015031>`_ and
    depends on the size of the repository.
"""

RESERVED_MATRIX_KEYWORDS = ["include", "exclude"]

TMatrix = dict[str, list[str] | list[dict[str, str]]]
"""Defines the structure of a matrix to be used in a GitHub workflow."""


class Metadata:
    """Metadata class."""

    def __init__(self, debug: bool = False) -> None:
        """Initialize instance."""
        self.debug = debug

    pyproject_path = Path() / "pyproject.toml"
    sphinx_conf_path = Path() / "docs" / "conf.py"

    @cached_property
    def github_context(self) -> Any:
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
            raise RuntimeError(message)
        context = json.loads(os.environ["GITHUB_CONTEXT"])
        if self.debug:
            print("--- GitHub context ---")
            print(json.dumps(context, indent=4))
        return context

    @staticmethod
    def commit_matrix(commits: Iterable[Commit] | None) -> TMatrix | None:
        """Pre-compute a matrix of commits.

        The list of commits is augmented with long and short SHA values, as well as
        current version. Most recent commit is first, oldest is last.

        Returns a ready-to-use matrix structure:

        .. code-block:: python
            {
                "commit": [
                    "346ce664f055fbd042a25ee0b7e96702e95",
                    "6f27db47612aaee06fdf08744b09a9f5f6c2",
                ],
                "include": [
                    {
                        "commit": "346ce664f055fbd042a25ee0b7e96702e95",
                        "short_sha": "346ce66",
                        "current_version": "2.0.1",
                    },
                    {
                        "commit": "6f27db47612aaee06fdf08744b09a9f5f6c2",
                        "short_sha": "6f27db4",
                        "current_version": "2.0.0",
                    },
                ],
            }
        """
        if not commits:
            return None

        # Save a reference to the current commit.
        git = Git(".")
        head_sha = git.get_head().hash

        sha_list = []
        include_list = []
        for commit in commits:
            sha = commit.hash

            # Checkout the commit so we can read the version associated with it.
            current_version = None
            git.checkout(sha)
            current_version = Metadata.get_current_version()

            sha_list.append(sha)
            include_list.append({
                "commit": sha,
                "short_sha": sha[:SHORT_SHA_LENGTH],
                "current_version": current_version,
            })

        # Restore the repository to the initial commit.
        git.checkout(head_sha)

        return {
            "commit": sha_list,
            "include": include_list,
        }

    @cached_property
    def commit_range(self) -> tuple[str, str] | None:
        """Range of commits bundled within the triggering event.

        A workflow run is triggered by a singular event, which might encapsulate one or
        more commits. This means the workflow will only run once on the last commit,
        even if multiple new commits where pushed.

        This is annoying when we want to keep a carefully constructed commit history,
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
                ".",
                from_commit=start,
                to_commit=end,
                order="reverse",
            ).traverse_commits(),
        )[:-1]

    @cached_property
    def new_commits_matrix(self) -> TMatrix | None:
        """Pre-computed matrix with long and short SHA values of new commits."""
        return self.commit_matrix(self.new_commits)

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
                r"^\[changelog\] Release v[0-9]+\.[0-9]+\.[0-9]+$",
                commit.msg,
            )
        )

    @cached_property
    def release_commits_matrix(self) -> TMatrix | None:
        """Pre-computed matrix with long and short SHA values of release commits."""
        return self.commit_matrix(self.release_commits)

    @cached_property
    def release_commits_hash(self) -> tuple[str, ...] | None:
        """List all hashes of release commits."""
        return (
            cast(tuple[str, ...], self.release_commits_matrix["commit"])
            if self.release_commits_matrix
            else None
        )

    @staticmethod
    def glob_files(*patterns: str) -> Generator[Path, None, None]:
        """Glob files in patterns."""
        for pattern in patterns:
            # is_file() return False if the path doesn't exist or is a broken symlink.
            yield from (p for p in Path().glob(pattern) if p.is_file())

    @cached_property
    def python_files(self) -> Generator[Path, None, None]:
        """Returns list of python files."""
        yield from self.glob_files("**/*.py")

    @cached_property
    def doc_files(self) -> Generator[Path, None, None]:
        """Returns list of doc files."""
        yield from self.glob_files("**/*.md", "**/*.markdown", "**/*.rst", "**/*.tex")

    @cached_property
    def pyproject(self) -> PyProjectTOML:
        """Returns PyProjectTOML object."""
        return PyProjectTOML(self.pyproject_path)

    @cached_property
    def is_poetry_project(self) -> bool:
        """Returns true if project relies on Poetry."""
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

        Will yields the following list:

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
                "scripts",
                {},
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
                self.pyproject.poetry_config["dependencies"]["python"],
            )
        if constraint and not constraint.is_empty():
            return constraint
        # TODO: Should we default to current running Python ?
        return None

    @cached_property
    def py_target_versions(self) -> tuple[str, ...] | None:
        """Generates the list of Python target versions.

        This is based on Black's support matrix.
        """
        if self.project_range:
            minor_range = sorted(v.value for v in TargetVersion)
            black_range = (
                Version.from_parts(major=3, minor=minor) for minor in minor_range
            )
            return tuple(
                f"py{version.text.replace('.', '')}"
                for version in black_range
                if self.project_range.allows(version)
            )
        return None

    @cached_property
    def blacken_docs_params(self) -> tuple[str, ...] | None:
        """Generates `blacken-docs` parameters.

        `Blacken-docs reuses Black's --target-version pyXY parameters
        <https://github.com/adamchainz/blacken-docs/blob/cd4e60f/src/blacken_docs/__init__.py#L263-L271>`_,
        and needs to be fed with a subset of these:
        - `--target-version py33`
        - `--target-version py34`
        - `--target-version py35`
        - `--target-version py36`
        - `--target-version py37`
        - `--target-version py38`
        - `--target-version py39`
        - `--target-version py310`
        - `--target-version py311`
        - `--target-version py312`

        As mentionned in Black usage, you should `include all Python versions that you
        want your code to run under
        <https://github.com/psf/black/issues/751#issuecomment-473066811>`_.
        """
        if self.py_target_versions:
            return tuple(
                f"--target-version {py_target}" for py_target in self.py_target_versions
            )
        return None

    @cached_property
    def ruff_py_version(self) -> str | None:
        """Returns the oldest Python version targeted.

        .. caution::

            Unlike ``blacken-docs``, `ruff doesn't support multiple
            --target-version values
            <https://github.com/astral-sh/ruff/issues/2857#issuecomment-1428100515>`_,
            and `only supports the minimum Python version
            <https://github.com/astral-sh/ruff/issues/2519>`_.
        """
        if self.py_target_versions:
            return self.py_target_versions[0]
        return None

    @cached_property
    def mypy_params(self) -> str | None:
        """Generates `mypy` parameters.

        Mypy needs to be fed with this parameter: ``--python-version x.y``.
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

    @staticmethod
    def get_current_version() -> str:
        """Returns the current version as managed by bump-my-version.

        Same as calling the CLI:

            .. code-block:: shell-session
                $ bump-my-version show current_version
        """
        config = get_configuration(find_config_file())
        config_dict = config.model_dump()
        return resolve_name(config_dict, "current_version")

    @cached_property
    def current_version(self) -> str | None:
        """Returns the current version.

        I.e. the version of the most recent commit.
        """
        version = None
        if self.new_commits_matrix:
            details = self.new_commits_matrix.get("include")
            if details:
                version = details[0].get("current_version")  # type: ignore[union-attr]
        return version

    @cached_property
    def released_version(self) -> str | None:
        """Returns the version of the release commit."""
        version = None
        if self.release_commits_matrix:
            details = self.release_commits_matrix.get("include")
            if details:
                # This script is only designed for at most 1 release in the list of new
                # commits.
                assert len(details) == 1
                version = details[0].get("current_version")  # type: ignore[union-attr]
        return version

    @cached_property
    def is_sphinx(self) -> bool:
        """Returns true if the Sphinx config file is present."""
        # The Sphinx config file is present, that's enough for us.
        return self.sphinx_conf_path.exists() and self.sphinx_conf_path.is_file()

    @cached_property
    def active_autodoc(self) -> bool:
        """Returns true if there are active Sphinx extensions."""
        if self.is_sphinx:
            # Look for list of active Sphinx extensions.
            for node in ast.parse(self.sphinx_conf_path.read_bytes()).body:
                if isinstance(node, ast.Assign) and isinstance(
                    node.value,
                    ast.List | ast.Tuple,
                ):
                    extension_found = "extensions" in (
                        t.id  # type: ignore[attr-defined]
                        for t in node.targets
                    )
                    if extension_found:
                        elements = (
                            e.value
                            for e in node.value.elts
                            if isinstance(e, ast.Constant)
                        )
                        if "sphinx.ext.autodoc" in elements:
                            return True
        return False

    # pylint: disable=too-many-locals
    @cached_property
    def nuitka_matrix(self) -> TMatrix | None:
        """Pre-compute a matrix for Nuitka compilation workflows.

        Combine the variations of:
        - all new commits
        - all entry points
        - for the 3 main OSes
        - for a set of architectures

        Returns a ready-to-use matrix structure, where each variation is augmented with
        specific extra parameters by the way of matching parameters in the `include`
        directive.

        .. code-block:: python
            {
                "entry_point": ["mpm"],
                "commit": [
                    "346ce664f055fbd042a25ee0b7e96702e95",
                    "6f27db47612aaee06fdf08744b09a9f5f6c2",
                ],
                "os": ["ubuntu-22.04", "macos-13", "windows-2022"],
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
                        "commit": "346ce664f055fbd042a25ee0b7e96702e95",
                        "short_sha": "346ce66",
                    },
                    {
                        "commit": "6f27db47612aaee06fdf08744b09a9f5f6c2",
                        "short_sha": "6f27db4",
                    },
                    {
                        "os": "ubuntu-22.04",
                        "platform_id": "linux",
                        "extension": "bin",
                        "extra_python_params": "",
                    },
                    {
                        "os": "macos-13",
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
                        "commit": "346ce664f055fbd042a25ee0b7e96702e95",
                        "os": "ubuntu-22.04",
                        "arch": "x64",
                        "bin_name": "mpm-linux-x64-build-346ce66.bin",
                    },
                    {
                        "entry_point": "mpm",
                        "commit": "346ce664f055fbd042a25ee0b7e96702e95",
                        "os": "macos-13",
                        "arch": "x64",
                        "bin_name": "mpm-macos-x64-build-346ce66.bin",
                    },
                    {
                        "entry_point": "mpm",
                        "commit": "346ce664f055fbd042a25ee0b7e96702e95",
                        "os": "windows-2022",
                        "arch": "x64",
                        "bin_name": "mpm-windows-x64-build-346ce66.exe",
                    },
                    {
                        "entry_point": "mpm",
                        "commit": "6f27db47612aaee06fdf08744b09a9f5f6c2",
                        "os": "ubuntu-22.04",
                        "arch": "x64",
                        "bin_name": "mpm-linux-x64-build-6f27db4.bin",
                    },
                    {
                        "entry_point": "mpm",
                        "commit": "6f27db47612aaee06fdf08744b09a9f5f6c2",
                        "os": "macos-13",
                        "arch": "x64",
                        "bin_name": "mpm-macos-x64-build-6f27db4.bin",
                    },
                    {
                        "entry_point": "mpm",
                        "commit": "6f27db47612aaee06fdf08744b09a9f5f6c2",
                        "os": "windows-2022",
                        "arch": "x64",
                        "bin_name": "mpm-windows-x64-build-6f27db4.exe",
                    },
                ],
            }
        """
        # Only produce a matrix if the project is providing CLI entry points.
        if not self.script_entries:
            return None

        # In the future, we might support and bridge that matrix with the full CPython
        # platform support list. See target triples at:
        # https://peps.python.org/pep-0011/
        # https://snarky.ca/webassembly-and-its-platform-targets/
        matrix: dict[str, list[Any]] = {
            "entry_point": [],
            # Run the compilation on the latest supported version of each OS.
            "os": [
                "ubuntu-22.04",
                "macos-13",
                "windows-2022",
            ],
            # Arch values are aligned to those specified for self-hosted runners:
            # https://docs.github.com/en/actions/hosting-your-own-runners/about-self-hosted-runners#architectures
            "arch": [
                "x64",
                # XXX GitHub-hosted runners only supports x64.
                # "ARM64"
                # "ARM32"
                # XXX GitHub-hosted macOS runners with Apple silicon are planned in the
                # future:
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
                },
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
                "os": "macos-13",
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
            ),
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
                # Extra parameters are matching the current variant, merge their values.
                if d0 == d1:
                    full_variant.update(extra_params)

            # Add to the 'include' directive a new extra parameter that match the
            # current variant.
            extra_name_param = variant_dict.copy()
            # Generate for Nuitka the binary file name to be used that is unique to
            # this variant.
            # pylint: disable=consider-using-f-string
            extra_name_param["bin_name"] = (
                "{cli_id}-{platform_id}-{arch}-build-{short_sha}.{extension}"
            ).format(**full_variant)
            matrix["include"].append(extra_name_param)

        return matrix

    @cached_property
    def release_notes(self) -> str | None:
        """Generate notes to be attached to the GitHub release."""
        # Produce the release notes of the release version or the current one.
        version = self.released_version
        if not version:
            version = self.current_version
        if not version:
            return None

        # Extract the changelog entry corresponding to the release version, and located
        # between the first two `##` second-level markdown titles.
        changes = ""
        match = re.search(
            rf"^##(?P<title>.+{escape(version)} .+?)\n(?P<changes>.*?)\n##",
            Path("./changelog.md").read_text(),
            flags=re.MULTILINE | re.DOTALL,
        )
        if match:
            changes = match.groupdict().get("changes", "").strip()
            # Add a title.
            if changes:
                changes = "### Changes\n\n" + changes

        # Generate a link to the version of the package published on PyPi.
        pypi_link = ""
        if self.package_name:
            pypi_link = dedent(
                f"""\
                [🐍 Available on
                PyPi](https://pypi.org/project/{self.package_name}/{version}).
                """
            )

        # Assemble the release notes.
        return f"{changes}\n\n{pypi_link}".strip()

    @staticmethod
    def format_github_value(value: Any, render_json: bool = False) -> str:
        """Transform Python value to GitHub-friendly, JSON-like, console string.

        Renders:
        - `str` as-is
        - `None` into empty string
        - `bool` into lower-cased string
        - `Iterable` of strings into a serialized space-separated string
        - `Iterable` of `Path` into a serialized string whose items are space-separated
          and double-quoted
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
        """Returns environment file `Path` pointed to by `$GITHUB_OUTPUT`."""
        output_path = None
        env_file = os.getenv("GITHUB_OUTPUT")
        if env_file:
            output_path = Path(env_file)
            assert output_path.is_file()
        return output_path

    def save_metadata(self) -> None:
        """Write data to the environment file pointed to by `$GITHUB_OUTPUT`."""
        # Plain metadata.
        metadata: dict[str, Any] = {
            "new_commits": (self.new_commits_hash, False),
            "release_commits": (self.release_commits_hash, False),
            "python_files": (self.python_files, False),
            "doc_files": (self.doc_files, False),
            "is_poetry_project": (self.is_poetry_project, False),
            "package_name": (self.package_name, False),
            "blacken_docs_params": (self.blacken_docs_params, False),
            "ruff_py_version": (self.ruff_py_version, False),
            "mypy_params": (self.mypy_params, False),
            "current_version": (self.current_version, False),
            "released_version": (self.released_version, False),
            "is_sphinx": (self.is_sphinx, False),
            "active_autodoc": (self.active_autodoc, False),
            "release_notes": (self.release_notes, False),
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
        for env_name, (value, render_json) in metadata.items():
            env_value = self.format_github_value(value, render_json=render_json)

            is_multiline = bool(len(env_value.splitlines()) > 1)
            if not is_multiline:
                content += f"{env_name}={env_value}\n"
            else:
                # Use a random unique delimiter to encode multiline value:
                delimiter = f"ghadelimiter_{randint(10**8, (10**9) - 1)}"
                content += f"{env_name}<<{delimiter}\n{env_value}\n{delimiter}\n"

        if self.debug:
            print(content)
        if not self.output_env_file:
            msg = "No output file specified by $GITHUB_OUTPUT environment variable."
            raise FileNotFoundError(
                msg,
            )
        self.output_env_file.write_text(content, encoding="utf-8")

        if self.debug:
            print(f"--- Content of {self.output_env_file} ---")
            print(self.output_env_file.read_text(encoding="utf-8"))


# Output metadata with GitHub syntax.
Metadata(debug=True).save_metadata()
