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
is_python_project=true
uv_requirement_params=--requirement pyproject.toml
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
                            'os': 'macos-14',
                            'arch': 'arm64',
                            'bin_name': 'mpm-macos-arm64-build-6f27db4.bin'},
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

from __future__ import annotations

import ast
import json
import logging
import os
import re
import sys
from collections.abc import Iterable
from functools import cached_property
from itertools import product
from pathlib import Path
from random import randint
from re import escape
from typing import Any, Final, Iterator, cast

if sys.version_info >= (3, 11):
    from enum import StrEnum

    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]
    from backports.strenum import StrEnum  # type: ignore[import-not-found]

from bumpversion.config import get_configuration  # type: ignore[import-untyped]
from bumpversion.config.files import find_config_file  # type: ignore[import-untyped]
from bumpversion.show import resolve_name  # type: ignore[import-untyped]
from packaging.specifiers import SpecifierSet
from packaging.version import Version
from pydriller import Commit, Git, Repository  # type: ignore[import-untyped]
from pyproject_metadata import ConfigurationError, StandardMetadata
from wcmatch.glob import (
    BRACE,
    DOTGLOB,
    FOLLOW,
    GLOBSTAR,
    GLOBTILDE,
    NEGATE,
    NODIR,
    iglob,
)

SHORT_SHA_LENGTH = 7
"""Default SHA length hard-coded to ``7``.

.. caution::

    The `default is subject to change <https://stackoverflow.com/a/21015031>`_ and
    depends on the size of the repository.
"""

RESERVED_MATRIX_KEYWORDS = ["include", "exclude"]


WorkflowEvent = StrEnum(
    "WorkflowEvent",
    (
        "branch_protection_rule",
        "check_run",
        "check_suite",
        "create",
        "delete",
        "deployment",
        "deployment_status",
        "discussion",
        "discussion_comment",
        "fork",
        "gollum",
        "issue_comment",
        "issues",
        "label",
        "merge_group",
        "milestone",
        "page_build",
        "project",
        "project_card",
        "project_column",
        "public",
        "pull_request",
        "pull_request_comment",
        "pull_request_review",
        "pull_request_review_comment",
        "pull_request_target",
        "push",
        "registry_package",
        "release",
        "repository_dispatch",
        "schedule",
        "status",
        "watch",
        "workflow_call",
        "workflow_dispatch",
        "workflow_run",
    ),
)
"""Workflow events that cause a workflow to run.

`List of events
<https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows>`_.
"""


Dialects = StrEnum("Dialects", ("github", "plain"))
"""Dialects in which metadata can be formatted to."""


class TargetVersion(StrEnum):
    """List of Python 3 minor versions supported by Black.

    `Mirrors official implementation from black.mode.TargetVersion
    <https://github.com/psf/black/blob/main/src/black/mode.py>`_.
    """

    PY33 = "3.3"
    PY34 = "3.4"
    PY35 = "3.5"
    PY36 = "3.6"
    PY37 = "3.7"
    PY38 = "3.8"
    PY39 = "3.9"
    PY310 = "3.10"
    PY311 = "3.11"
    PY312 = "3.12"
    PY313 = "3.13"


MYPY_VERSION_MIN: Final = (3, 8)
"""Earliest version supported by Mypy's ``--python-version 3.x`` parameter.

`Sourced from Mypy original implementation
<https://github.com/python/mypy/blob/master/mypy/defaults.py>`_.
"""


class Matrix(dict):
    """A matrix to used in a GitHub workflow."""

    def __str__(self) -> str:
        """Render matrix as a JSON string."""
        return json.dumps(self)


class Metadata:
    """Metadata class."""

    def __init__(self) -> None:
        """Initialize internal variables."""
        # None indicates the is_python_project variable has not been evaluated yet.
        self._is_python_project: bool | None = None

    pyproject_path = Path() / "pyproject.toml"
    sphinx_conf_path = Path() / "docs" / "conf.py"

    @cached_property
    def in_ci_env(self) -> bool:
        """Returns ``True`` if the code is executed in a GitHub Actions runner.

        Other CI are available at:
        https://github.com/cucumber/ci-environment/blob/main/python/src/ci_environment/CiEnvironments.json
        """
        return bool("GITHUB_RUN_ID" in os.environ)

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
              run: |
                gha-utils --verbosity DEBUG metadata --overwrite "$GITHUB_OUTPUT"

        .. todo::
            Try to remove reliance on GitHub context entirely so we can eliminate the
            JSON/env hack above.
        """
        if "GITHUB_CONTEXT" not in os.environ:
            if self.in_ci_env:
                message = (
                    "Missing GitHub context in environment. "
                    "Did you forget to set GITHUB_CONTEXT?"
                )
                logging.warning(message)
            return {}
        context = json.loads(os.environ["GITHUB_CONTEXT"])
        logging.debug("--- GitHub context ---")
        logging.debug(json.dumps(context, indent=4))
        return context  # type:ignore[no-any-return]

    def git_stash_count(self, git_repo: Git) -> int:
        """Returns the number of stashes."""
        count = int(
            git_repo.repo.git.rev_list(
                "--walk-reflogs", "--ignore-missing", "--count", "refs/stash"
            )
        )
        logging.debug(f"Number of stashes in repository: {count}")
        return count

    def commit_matrix(self, commits: Iterable[Commit] | None) -> Matrix | None:
        """Pre-compute a matrix of commits.

        .. danger::
            This method temporarily modify the state of the repository to compute
            version metadata from the past.

            To prevent any loss of uncommitted data, it stashes and unstash the
            local changes between checkouts.

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

        git = Git(".")
        current_commit = git.repo.head.commit.hexsha

        # Check if we need to get back in time in the Git log and browse past commits.
        if len(commits) == 1:  # type: ignore[arg-type]
            # Is the current commit the one we're looking for?
            past_commit_lookup = bool(
                current_commit != commits[0].hash  # type: ignore[index]
            )
        # If we have multiple commits then yes, we need to look for past commits.
        else:
            past_commit_lookup = True

        # We need to go back in time, but first save the current state of the
        # repository.
        if past_commit_lookup:
            logging.debug(
                "We need to look into the commit history. Inspect the initial state of the repository."
            )

            if not self.in_ci_env:
                raise RuntimeError(
                    "Local repository manipulations only allowed in CI environment"
                )

            # Save the initial commit reference and SHA of the repository. The reference is
            # either the canonical active branch name (i.e. ``main``), or the commit SHA if
            # the current HEAD commit is detached from a branch.
            if git.repo.head.is_detached:
                init_ref = current_commit
            else:
                init_ref = git.repo.active_branch.name
            logging.debug(f"Initial commit reference: {init_ref}")

            # Try to stash local changes and check if we'll need to unstash them later.
            counter_before = self.git_stash_count(git)
            logging.debug("Try to stash local changes before our series of checkouts.")
            git.repo.git.stash()
            counter_after = self.git_stash_count(git)
            logging.debug(
                f"Stash counter changes after 'git stash' command: {counter_before} -> {counter_after}"
            )
            assert counter_after >= counter_before
            need_unstash = bool(counter_after > counter_before)
            logging.debug(f"Need to unstash after checkouts: {need_unstash}")

        else:
            init_ref = None
            need_unstash = False
            logging.debug(
                f"No need to look into the commit history: repository is already checked out at {current_commit}"
            )

        sha_list = []
        include_list = []
        for commit in commits:
            if past_commit_lookup:
                logging.debug(f"Checkout to commit {commit.hash}")
                git.checkout(commit.hash)

            logging.debug(f"Extract project version at commit {commit.hash}")
            current_version = Metadata.get_current_version()

            sha_list.append(commit.hash)
            include_list.append({
                "commit": commit.hash,
                "short_sha": commit.hash[:SHORT_SHA_LENGTH],
                "current_version": current_version,
            })

        # Restore the repository to its initial state.
        if past_commit_lookup:
            logging.debug(f"Restore repository to {init_ref}.")
            git.checkout(init_ref)
            if need_unstash:
                logging.debug("Unstash local changes that were previously saved.")
                git.repo.git.stash("pop")

        return Matrix({
            "commit": sha_list,
            "include": include_list,
        })

    @cached_property
    def event_type(self) -> WorkflowEvent | None:  # type: ignore[valid-type]
        """Returns the type of event that triggered the workflow run.

        .. caution::
            This property is based on a crude heuristics as it only looks at the value
            of the ``GITHUB_BASE_REF`` environment variable. Which is `only set when
            the event that triggers a workflow run is either pull_request or pull_request_target
            <https://docs.github.com/en/actions/learn-github-actions/variables#default-environment-variables>`_.

        .. todo::
            Add detection of all workflow trigger events.
        """
        if not self.in_ci_env:
            logging.warning(
                "Cannot guess event type because we're not in a CI environment."
            )
            return None
        if "GITHUB_BASE_REF" not in os.environ:
            logging.warning(
                "Cannot guess event type because no GITHUB_BASE_REF env var found."
            )
            return None

        if bool(os.environ.get("GITHUB_BASE_REF")):
            return WorkflowEvent.pull_request  # type: ignore[no-any-return]
        return WorkflowEvent.push  # type: ignore[no-any-return]

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

        The default ``GITHUB_SHA`` environment variable is not enough as it only points to
        the last commit. We need to inspect the commit history to find all new ones. New
        commits needs to be fetched differently in ``push`` and ``pull_requests``
        events.

        .. seealso::

            - https://stackoverflow.com/a/67204539
            - https://stackoverflow.com/a/62953566
            - https://stackoverflow.com/a/61861763

        .. todo::
            Refactor so we can get rid of ``self.github_context``. Maybe there's enough metadata lying around in
            the environment variables that we can inspect the git history and find the commit range.
        """
        if not self.github_context or not self.event_type:
            return None
        # Pull request event.
        if self.event_type in (  # type: ignore[unreachable]
            WorkflowEvent.pull_request,
            WorkflowEvent.pull_request_target,
        ):
            base_ref = os.environ["GITHUB_BASE_REF"]
            assert base_ref
            start = f"origin/{base_ref}"
            # We need to checkout the HEAD commit instead of the artificial merge
            # commit introduced by the pull request.
            end = self.github_context["event"]["pull_request"]["head"]["sha"]
        # Push event.
        else:
            start = self.github_context["event"]["before"]
            end = os.environ["GITHUB_SHA"]
            assert end
        logging.debug(f"Commit range: {start} -> {end}")
        return start, end

    @cached_property
    def current_commit(self) -> Commit | None:
        """Returns the current ``Commit`` object."""
        return next(Repository(".", single="HEAD").traverse_commits())

    @cached_property
    def current_commit_matrix(self) -> Matrix | None:
        """Pre-computed matrix with long and short SHA values of the current commit."""
        return self.commit_matrix((self.current_commit,))

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
    def new_commits_matrix(self) -> Matrix | None:
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
    def release_commits_matrix(self) -> Matrix | None:
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
    def glob_files(*patterns: str) -> Iterator[str]:
        """Glob files in patterns, while optionally ignoring some."""
        yield from iglob(
            patterns,
            flags=NODIR | GLOBSTAR | DOTGLOB | GLOBTILDE | BRACE | FOLLOW | NEGATE,
        )

    @cached_property
    def python_files(self) -> Iterator[str]:
        """Returns a list of python files."""
        yield from self.glob_files("**/*.py", "!.venv/**")

    @cached_property
    def requirement_files(self) -> Iterator[str]:
        """Returns a list of requirement files supported by uv."""
        yield from self.glob_files(
            "**/pyproject.toml", "*requirements.txt", "requirements/*.txt"
        )

    @cached_property
    def doc_files(self) -> Iterator[str]:
        """Returns a list of doc files."""
        yield from self.glob_files("**/*.{md,markdown,rst,tex}", "!.venv/**")

    @cached_property
    def uv_requirement_params(self) -> Iterator[str]:
        return (f"--requirement {req}" for req in self.requirement_files)

    @property
    def is_python_project(self):
        """Returns ``True`` if repository is a Python project.

        Presence of a ``pyproject.toml`` file is not enough, as 3rd party tools can use
        that file to store their own configuration.
        """
        return self._is_python_project

    @is_python_project.getter
    def is_python_project(self):
        """Try to read and validate the ``pyproject.toml`` file on access to the
        ``is_python_project`` property.
        """
        if self._is_python_project is None:
            self.pyproject
        return self._is_python_project

    @cached_property
    def pyproject(self) -> StandardMetadata | None:
        """Returns metadata stored in the ``pyproject.toml`` file.

        Also sets the internal ``_is_python_project`` value to ``True`` if the
        ``pyproject.toml`` exists and respects the standards. ``False`` otherwise.
        """
        if self.pyproject_path.exists() and self.pyproject_path.is_file():
            toml = tomllib.loads(self.pyproject_path.read_text(encoding="UTF-8"))
            try:
                metadata = StandardMetadata.from_pyproject(toml)
                self._is_python_project = True
                return metadata
            except ConfigurationError:
                pass

        self._is_python_project = False
        return None

    @cached_property
    def package_name(self) -> str | None:
        """Returns package name as published on PyPi."""
        if self.pyproject and self.pyproject.canonical_name:
            return self.pyproject.canonical_name
        return None

    @cached_property
    def script_entries(self) -> list[tuple[str, str, str]]:
        """Returns a list of tuples containing the script name, its module and callable.

        Results are derived from the script entries of ``pyproject.toml``. So that:

        .. code-block:: toml
            [project.scripts]
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
        if self.pyproject:
            for cli_id, script in self.pyproject.scripts.items():
                module_id, callable_id = script.split(":")
                entries.append((cli_id, module_id, callable_id))
        # Double check we do not have duplicate entries.
        all_cli_ids = [cli_id for cli_id, _, _ in entries]
        assert len(set(all_cli_ids)) == len(all_cli_ids)
        return entries

    @cached_property
    def py_target_versions(self) -> tuple[Version, ...] | None:
        """Generates the list of Python target versions.

        Only takes ``major.minor`` variations into account. Smaller version dimensions
        are ignored, so a package depending on ``3.8.6`` will keep ``3.8`` as a Python
        target.
        """
        if self.pyproject and self.pyproject.requires_python:
            # Dumb down specifiers' lower bounds to their major.minor version.
            spec_list = []
            for spec in self.pyproject.requires_python:
                if spec.operator in (">=", ">"):
                    release = Version(spec.version).release
                    new_spec = f"{spec.operator}{release[0]}.{release[1]}"
                else:
                    new_spec = str(spec)
                spec_list.append(new_spec)
            relaxed_specs = SpecifierSet(",".join(spec_list))
            logging.debug(
                "Relax Python requirements from "
                f"{self.pyproject.requires_python} to {relaxed_specs}."
            )

            # Iterate through Python version support.
            return tuple(
                Version(target)
                for target in tuple(TargetVersion)
                if relaxed_specs.contains(target)
            )
        return None

    @cached_property
    def blacken_docs_params(self) -> tuple[str, ...] | None:
        """Generates ``blacken-docs`` parameters.

        `Blacken-docs reuses Black's --target-version pyXY parameters
        <https://github.com/adamchainz/blacken-docs/blob/cd4e60f/src/blacken_docs/__init__.py#L263-L271>`_,
        and needs to be fed with a subset of these:
        - ``--target-version py33``
        - ``--target-version py34``
        - ``--target-version py35``
        - ``--target-version py36``
        - ``--target-version py37``
        - ``--target-version py38``
        - ``--target-version py39``
        - ``--target-version py310``
        - ``--target-version py311``
        - ``--target-version py312``

        As mentioned in Black usage, you should `include all Python versions that you
        want your code to run under
        <https://github.com/psf/black/issues/751#issuecomment-473066811>`_.
        """
        if self.py_target_versions:
            return tuple(
                f"--target-version py{version.major}{version.minor}"
                for version in self.py_target_versions
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
            version = self.py_target_versions[0]
            return f"py{version.major}{version.minor}"
        return None

    @cached_property
    def mypy_params(self) -> str | None:
        """Generates `mypy` parameters.

        Mypy needs to be fed with this parameter: ``--python-version 3.x``.
        """
        if self.py_target_versions:
            # Compare to Mypy's lowest supported version of Python dialect.
            major, minor = max(
                MYPY_VERSION_MIN,
                min((v.major, v.minor) for v in self.py_target_versions),
            )
            return f"--python-version {major}.{minor}"
        return None

    @staticmethod
    def get_current_version() -> str | None:
        """Returns the current version as managed by bump-my-version.

        Same as calling the CLI:

            .. code-block:: shell-session
                $ bump-my-version show current_version
        """
        conf_file = find_config_file()
        if not conf_file:
            return None
        config = get_configuration(conf_file)
        config_dict = config.model_dump()
        return str(resolve_name(config_dict, "current_version"))

    @cached_property
    def current_version(self) -> str | None:
        """Returns the current version.

        I.e. the version of the most recent commit.
        """
        version = None
        if self.new_commits_matrix:
            details = self.new_commits_matrix.get("include")
            if details:
                version = details[0].get("current_version")
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
                version = details[0].get("current_version")
        return version

    @cached_property
    def is_sphinx(self) -> bool:
        """Returns ``True`` if the Sphinx config file is present."""
        # The Sphinx config file is present, that's enough for us.
        return self.sphinx_conf_path.exists() and self.sphinx_conf_path.is_file()

    @cached_property
    def active_autodoc(self) -> bool:
        """Returns ``True`` if there are active Sphinx extensions."""
        if self.is_sphinx:
            # Look for list of active Sphinx extensions.
            for node in ast.parse(self.sphinx_conf_path.read_bytes()).body:
                if isinstance(node, ast.Assign) and isinstance(
                    node.value,
                    ast.List | ast.Tuple,  # type: ignore[operator]
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

    @cached_property
    def nuitka_matrix(self) -> Matrix | None:
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
            # Run the compilation only the latest supported version of each OS.
            # The exception is macOS, as macos-14 is arm64 and macos-13 is x64, so we
            # need both to target the two architectures.
            "os": [
                "ubuntu-22.04",
                "macos-14",
                "macos-13",
                "windows-2022",
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

        # We'd like to run a build for each new commit bundled in the action trigger.
        # If no new commits are detected, it's because we are not in a GitHub workflow
        # event, so we'll fallback to the current commit and only build for it.
        build_commit_matrix = (
            self.new_commits_matrix
            if self.new_commits_matrix
            else self.current_commit_matrix
        )
        assert build_commit_matrix
        # Extend the matrix with a new dimension: a list of commits.
        matrix["commit"] = build_commit_matrix["commit"]
        matrix["include"].extend(build_commit_matrix["include"])

        # Add platform-specific variables.
        # Arch values are inspired from those specified for self-hosted runners:
        # https://docs.github.com/en/actions/hosting-your-own-runners/about-self-hosted-runners#architectures
        # Arch is not a matrix variant because support is not widely distributed
        # between different OS.
        extra_os_params = [
            {
                "os": "ubuntu-22.04",
                "platform_id": "linux",
                "arch": "x64",
                "extension": "bin",
                "extra_python_params": "",
            },
            {
                "os": "macos-14",
                "platform_id": "macos",
                "arch": "arm64",
                "extension": "bin",
                "extra_python_params": "",
            },
            {
                "os": "macos-13",
                "platform_id": "macos",
                "arch": "x64",
                "extension": "bin",
                "extra_python_params": "",
            },
            {
                "os": "windows-2022",
                "platform_id": "windows",
                "arch": "x64",
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
            extra_name_param["bin_name"] = (
                "{cli_id}-{platform_id}-{arch}-build-{short_sha}.{extension}"
            ).format(**full_variant)
            matrix["include"].append(extra_name_param)

        return Matrix(matrix)

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
            Path("./changelog.md").read_text(encoding="UTF-8"),
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
            pypi_link = (
                "[🐍 Available on PyPi](https://pypi.org/project/"
                + self.package_name
                + "/"
                + version
                + ")."
            )

        # Assemble the release notes.
        return f"{changes}\n\n{pypi_link}".strip()

    @staticmethod
    def format_github_value(value: Any) -> str:
        """Transform Python value to GitHub-friendly, JSON-like, console string.

        Renders:
        - `str` as-is
        - `None` into empty string
        - `bool` into lower-cased string
        - `Matrix` into JSON string
        - `Iterable` of strings into a serialized space-separated string
        - `Iterable` of `Path` into a serialized string whose items are space-separated
          and double-quoted
        """
        # Structured metadata to be rendered as JSON.
        if isinstance(value, Matrix):
            return str(value)

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

    def dump(
        self,
        dialect: Dialects = Dialects.github,  # type: ignore[valid-type]
    ) -> str:
        """Returns all metadata in the specified format.

        Defaults to GitHub dialect.
        """
        metadata: dict[str, Any] = {
            "new_commits": self.new_commits_hash,
            "release_commits": self.release_commits_hash,
            "python_files": self.python_files,
            "doc_files": self.doc_files,
            "is_python_project": self.is_python_project,
            "uv_requirement_params": self.uv_requirement_params,
            "package_name": self.package_name,
            "blacken_docs_params": self.blacken_docs_params,
            "ruff_py_version": self.ruff_py_version,
            "mypy_params": self.mypy_params,
            "current_version": self.current_version,
            "released_version": self.released_version,
            "is_sphinx": self.is_sphinx,
            "active_autodoc": self.active_autodoc,
            "release_notes": self.release_notes,
            "new_commits_matrix": self.new_commits_matrix,
            "release_commits_matrix": self.release_commits_matrix,
            "nuitka_matrix": self.nuitka_matrix,
        }

        logging.debug(f"Raw metadata: {metadata!r}")
        logging.debug(f"Format metadata into {dialect} format.")

        content = ""
        if dialect == Dialects.github:
            for env_name, value in metadata.items():
                env_value = self.format_github_value(value)

                is_multiline = bool(len(env_value.splitlines()) > 1)
                if not is_multiline:
                    content += f"{env_name}={env_value}\n"
                else:
                    # Use a random unique delimiter to encode multiline value:
                    delimiter = f"ghadelimiter_{randint(10**8, (10**9) - 1)}"
                    content += f"{env_name}<<{delimiter}\n{env_value}\n{delimiter}\n"
        else:
            assert dialect == Dialects.PLAIN
            content = repr(metadata)

        logging.debug(f"Formatted metadata:\n{content}")

        return content
