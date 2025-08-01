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
gitignore_exists=true
python_files=".github/update_mailmap.py" ".github/metadata.py" "setup.py"
doc_files="changelog.md" "readme.md" "docs/license.md"
is_python_project=true
package_name=click-extra
blacken_docs_params=--target-version py37 --target-version py38
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
nuitka_matrix={'os': ['ubuntu-24.04-arm', 'ubuntu-24.04', 'macos-15', 'macos-13', 'windows-11-arm', 'windows-2025'],
               'entry_point': ['mpm'],
               'commit': ['346ce664f055fbd042a25ee0b7e96702e95',
                          '6f27db47612aaee06fdf08744b09a9f5f6c2'],
               'include': [{'target': 'linux-arm64',
                            'os': 'ubuntu-24.04-arm',
                            'platform_id': 'linux',
                            'arch': 'arm64',
                            'extension': 'bin'},
                           {'target': 'linux-x64',
                            'os': 'ubuntu-24.04',
                            'platform_id': 'linux',
                            'arch': 'x64',
                            'extension': 'bin'},
                           {'target': 'macos-arm64',
                            'os': 'macos-15',
                            'platform_id': 'macos',
                            'arch': 'arm64',
                            'extension': 'bin'},
                           {'target': 'macos-x64',
                            'os': 'macos-13',
                            'platform_id': 'macos',
                            'arch': 'x64',
                            'extension': 'bin'},
                           {'target': 'windows-arm64',
                            'os': 'windows-11-arm',
                            'platform_id": 'windows',
                            'arch": 'arm64',
                            'extension": 'exe'},
                           {'target': 'windows-x64',
                            'os': 'windows-2025',
                            'platform_id': 'windows',
                            'arch': 'x64',
                            'extension': 'exe'},
                           {'entry_point': 'mpm',
                            'cli_id': 'mpm',
                            'module_id': 'meta_package_manager.__main__',
                            'callable_id': 'main',
                            'module_path': 'meta_package_manager/__main__.py'},
                           {'commit': '346ce664f055fbd042a25ee0b7e96702e95',
                            'short_sha': '346ce66',
                            'current_version': '2.0.0'},
                           {'commit': '6f27db47612aaee06fdf08744b09a9f5f6c2',
                            'short_sha': '6f27db4',
                            'current_version': '1.9.1'},
                           {'os': 'ubuntu-24.04-arm',
                            'entry_point': 'mpm',
                            'commit': '346ce664f055fbd042a25ee0b7e96702e95',
                            'bin_name': 'mpm-linux-arm64-346ce66.bin'},
                           {'os': 'ubuntu-24.04-arm',
                            'entry_point': 'mpm',
                            'commit': '6f27db47612aaee06fdf08744b09a9f5f6c2',
                            'bin_name': 'mpm-linux-arm64-6f27db4.bin'},
                           {'os': 'ubuntu-24.04',
                            'entry_point': 'mpm',
                            'commit': '346ce664f055fbd042a25ee0b7e96702e95',
                            'bin_name': 'mpm-linux-x64-346ce66.bin'},
                           {'os': 'ubuntu-24.04',
                            'entry_point': 'mpm',
                            'commit': '6f27db47612aaee06fdf08744b09a9f5f6c2',
                            'bin_name': 'mpm-linux-x64-6f27db4.bin'},
                           {'os': 'macos-15',
                            'entry_point': 'mpm',
                            'commit': '346ce664f055fbd042a25ee0b7e96702e95',
                            'bin_name': 'mpm-macos-arm64-346ce66.bin'},
                           {'os': 'macos-15',
                            'entry_point': 'mpm',
                            'commit': '6f27db47612aaee06fdf08744b09a9f5f6c2',
                            'bin_name': 'mpm-macos-arm64-6f27db4.bin'},
                           {'os': 'macos-13',
                            'entry_point': 'mpm',
                            'commit': '346ce664f055fbd042a25ee0b7e96702e95',
                            'bin_name': 'mpm-macos-x64-346ce66.bin'},
                           {'os': 'macos-13',
                            'entry_point': 'mpm',
                            'commit': '6f27db47612aaee06fdf08744b09a9f5f6c2',
                            'bin_name': 'mpm-macos-x64-6f27db4.bin'},
                           {'os': 'windows-11-arm',
                            'entry_point': 'mpm',
                            'commit': '346ce664f055fbd042a25ee0b7e96702e95',
                            'bin_name': 'mpm-windows-arm64-346ce66.bin'},
                           {'os': 'windows-11-arm',
                            'entry_point': 'mpm',
                            'commit': '6f27db47612aaee06fdf08744b09a9f5f6c2',
                            'bin_name': 'mpm-windows-arm64-6f27db4.bin'},
                           {'os': 'windows-2025',
                            'entry_point': 'mpm',
                            'commit': '346ce664f055fbd042a25ee0b7e96702e95',
                            'bin_name': 'mpm-windows-x64-346ce66.exe'},
                           {'os': 'windows-2025',
                            'entry_point': 'mpm',
                            'commit': '6f27db47612aaee06fdf08744b09a9f5f6c2',
                            'bin_name': 'mpm-windows-x64-6f27db4.exe'},
                           {'state': 'stable'}]}
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
import tomllib
from collections.abc import Iterable
from enum import StrEnum
from functools import cached_property
from operator import itemgetter
from pathlib import Path
from random import randint
from re import escape
from typing import Any, Final, Iterator, cast

from bumpversion.config import get_configuration  # type: ignore[import-untyped]
from bumpversion.config.files import find_config_file  # type: ignore[import-untyped]
from bumpversion.show import resolve_name  # type: ignore[import-untyped]
from extra_platforms import is_github_ci
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

from .matrix import Matrix

SHORT_SHA_LENGTH = 7
"""Default SHA length hard-coded to ``7``.

.. caution::

    The `default is subject to change <https://stackoverflow.com/a/21015031>`_ and
    depends on the size of the repository.
"""


NUITKA_BUILD_TARGETS = {
    "linux-arm64": {
        "os": "ubuntu-24.04-arm",
        "platform_id": "linux",
        "arch": "arm64",
        "extension": "bin",
    },
    "linux-x64": {
        "os": "ubuntu-24.04",
        "platform_id": "linux",
        "arch": "x64",
        "extension": "bin",
    },
    "macos-arm64": {
        "os": "macos-15",
        "platform_id": "macos",
        "arch": "arm64",
        "extension": "bin",
    },
    "macos-x64": {
        "os": "macos-13",
        "platform_id": "macos",
        "arch": "x64",
        "extension": "bin",
    },
    "windows-arm64": {
        "os": "windows-11-arm",
        "platform_id": "windows",
        "arch": "arm64",
        "extension": "exe",
    },
    "windows-x64": {
        "os": "windows-2025",
        "platform_id": "windows",
        "arch": "x64",
        "extension": "exe",
    },
}
"""List of GitHub-hosted runners used for Nuitka builds.

The key of the dictionary is the target name, which is used as a short name for
user-friendlyness. As such, it is used to name the compiled binary.

Values are dictionaries with the following keys:

- ``os``: Operating system name, as used in `GitHub-hosted runners
    <https://docs.github.com/en/actions/writing-workflows/choosing-where-your-workflow-runs/choosing-the-runner-for-a-job#standard-github-hosted-runners-for-public-repositories>`_.

    .. hint::
        We choose to run the compilation only on the latest supported version of each
        OS, for each architecture. Note that macOS and Windows do not have the latest
        version available for each architecture.

- ``platform_id``: Platform identifier, as defined by `Extra Platform
  <https://github.com/kdeldycke/extra-platforms>`_.

- ``arch``: Architecture identifier.

    .. note::
        Architecture IDs are `inspired from those specified for self-hosted runners
        <https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/supported-architectures-and-operating-systems-for-self-hosted-runners#supported-processor-architectures>`_

    .. note::
        Maybe we should just adopt `target triple
        <https://mcyoung.xyz/2025/04/14/target-triples/>`_.

- ``extension``: File extension of the compiled binary.
"""


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


class Metadata:
    """Metadata class."""

    def __init__(self, unstable_targets: Iterable[str] | None = None) -> None:
        """Initialize internal variables."""
        self.unstable_targets = set()
        if unstable_targets:
            self.unstable_targets = set(unstable_targets)
            assert self.unstable_targets.issubset(NUITKA_BUILD_TARGETS)

        # None indicates the is_python_project variable has not been evaluated yet.
        self._is_python_project: bool | None = None

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
              run: |
                gha-utils --verbosity DEBUG metadata --overwrite "$GITHUB_OUTPUT"

        .. todo::
            Try to remove reliance on GitHub context entirely so we can eliminate the
            JSON/env hack above.
        """
        if "GITHUB_CONTEXT" not in os.environ:
            if is_github_ci():
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
                "We need to look into the commit history. Inspect the initial state "
                "of the repository."
            )

            if not is_github_ci():
                raise RuntimeError(
                    "Local repository manipulations only allowed in CI environment"
                )

            # Save the initial commit reference and SHA of the repository. The
            # reference is either the canonical active branch name (i.e. ``main``), or
            # the commit SHA if the current HEAD commit is detached from a branch.
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
                "Stash counter changes after 'git stash' command: "
                f"{counter_before} -> {counter_after}"
            )
            assert counter_after >= counter_before
            need_unstash = bool(counter_after > counter_before)
            logging.debug(f"Need to unstash after checkouts: {need_unstash}")

        else:
            init_ref = None
            need_unstash = False
            logging.debug(
                "No need to look into the commit history: repository is already "
                f"checked out at {current_commit}"
            )

        matrix = Matrix()
        for commit in commits:
            if past_commit_lookup:
                logging.debug(f"Checkout to commit {commit.hash}")
                git.checkout(commit.hash)

            commit_metadata = {
                "commit": commit.hash,
                "short_sha": commit.hash[:SHORT_SHA_LENGTH],
            }

            logging.debug(f"Extract project version at commit {commit.hash}")
            current_version = Metadata.get_current_version()
            if current_version:
                commit_metadata["current_version"] = current_version

            matrix.add_variation("commit", [commit.hash])
            matrix.add_includes(commit_metadata)

        # Restore the repository to its initial state.
        if past_commit_lookup:
            logging.debug(f"Restore repository to {init_ref}.")
            git.checkout(init_ref)
            if need_unstash:
                logging.debug("Unstash local changes that were previously saved.")
                git.repo.git.stash("pop")

        return matrix

    @cached_property
    def event_type(self) -> WorkflowEvent | None:
        """Returns the type of event that triggered the workflow run.

        .. caution::
            This property is based on a crude heuristics as it only looks at the value
            of the ``GITHUB_BASE_REF`` environment variable. Which is `only set when
            the event that triggers a workflow run is either pull_request or
            pull_request_target
            <https://docs.github.com/en/actions/learn-github-actions/variables#default-environment-variables>`_.

        .. todo::
            Add detection of all workflow trigger events.
        """
        if not is_github_ci():
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
            return WorkflowEvent.pull_request
        return WorkflowEvent.push

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

        The default ``GITHUB_SHA`` environment variable is not enough as it only points
        to the last commit. We need to inspect the commit history to find all new ones.
        New commits needs to be fetched differently in ``push`` and ``pull_requests``
        events.

        .. seealso::

            - https://stackoverflow.com/a/67204539
            - https://stackoverflow.com/a/62953566
            - https://stackoverflow.com/a/61861763

        .. todo::
            Refactor so we can get rid of ``self.github_context``. Maybe there's enough
            metadata lying around in the environment variables that we can inspect the
            git history and find the commit range.
        """
        if not self.github_context or not self.event_type:
            return None
        # Pull request event.
        if self.event_type in (
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
    def glob_files(*patterns: str) -> Iterator[Path]:
        """Return all file path matching the ``patterns``.

        Patterns are glob patterns supporting ``**`` for recursive search, and ``!``
        for negation.

        All directories are traversed, whether they are hidden (i.e. starting with a
        dot ``.``) or not, including symlinks.

        Returns both hidden and non-hidden files, but no directories.

        All files are normalized to their absolute path, so that duplicates produced by
        symlinks are ignored.

        Files that doesn't exist and broken symlinks are skipped.
        """
        seen = set()
        for file_path in iglob(
            patterns,
            flags=NODIR | GLOBSTAR | DOTGLOB | GLOBTILDE | BRACE | FOLLOW | NEGATE,
        ):
            # Normalize the path to avoid duplicates.
            try:
                normalized_path = Path(file_path).resolve(strict=True)
            # Skip files that do not exist or broken symlinks.
            except OSError:
                logging.warning(
                    f"Skipping non-existing file / broken symlink: {file_path}"
                )
                continue
            if normalized_path in seen:
                logging.debug(f"Skipping duplicate file: {normalized_path}")
                continue
            seen.add(normalized_path)
            yield normalized_path

    @cached_property
    def gitignore_exists(self) -> bool:
        return Path(".gitignore").is_file()

    @cached_property
    def python_files(self) -> Iterator[Path]:
        """Returns a list of python files."""
        yield from self.glob_files("**/*.py", "!.venv/**")

    @cached_property
    def doc_files(self) -> Iterator[Path]:
        """Returns a list of doc files."""
        yield from self.glob_files("**/*.{md,markdown,rst,tex}", "!.venv/**")

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
        """Returns a list of tuples containing the script name, its module and
        callable.

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
        - ``--target-version py313``

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

        Current version is fetched from the ``bump-my-version`` configuration file.

        During a release we get two commits bundled into a single event. The first one
        is the release commit itself freezing the version to the release number. The
        second one is the commit that bumps the version to the next one. In this
        situation, the current version returned is the one from the most recent commit.
        """
        version = None
        if self.new_commits_matrix:
            details = self.new_commits_matrix.include
            if details:
                version = details[0].get("current_version")
        else:
            version = self.get_current_version()
        return version

    @cached_property
    def released_version(self) -> str | None:
        """Returns the version of the release commit."""
        version = None
        if self.release_commits_matrix:
            details = self.release_commits_matrix.include
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
                    node.value, ast.List | ast.Tuple
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
                "os": [
                    "ubuntu-24.04-arm",
                    "ubuntu-24.04",
                    "macos-15",
                    "macos-13",
                    "windows-11-arm",
                    "windows-2025",
                ],
                "entry_point": [
                    "mpm",
                ],
                "commit": [
                    "346ce664f055fbd042a25ee0b7e96702e95",
                    "6f27db47612aaee06fdf08744b09a9f5f6c2",
                ],
                "include": [
                    {
                        "target": "linux-arm64",
                        "os": "ubuntu-24.04-arm",
                        "platform_id": "linux",
                        "arch": "arm64",
                        "extension": "bin",
                    },
                    {
                        "target": "linux-x64",
                        "os": "ubuntu-24.04",
                        "platform_id": "linux",
                        "arch": "x64",
                        "extension": "bin",
                    },
                    {
                        "target": "macos-arm64",
                        "os": "macos-15",
                        "platform_id": "macos",
                        "arch": "arm64",
                        "extension": "bin",
                    },
                    {
                        "target": "macos-x64",
                        "os": "macos-13",
                        "platform_id": "macos",
                        "arch": "x64",
                        "extension": "bin",
                    },
                    {
                        "target": "windows-arm64",
                        "os": "windows-11-arm",
                        "platform_id": "windows",
                        "arch": "arm64",
                        "extension": "exe",
                    },
                    {
                        "target": "windows-x64",
                        "os": "windows-2025",
                        "platform_id": "windows",
                        "arch": "x64",
                        "extension": "exe",
                    },
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
                        "current_version": "2.0.0",
                    },
                    {
                        "commit": "6f27db47612aaee06fdf08744b09a9f5f6c2",
                        "short_sha": "6f27db4",
                        "current_version": "1.9.1",
                    },
                    {
                        "os": "ubuntu-24.04-arm",
                        "entry_point": "mpm",
                        "commit": "346ce664f055fbd042a25ee0b7e96702e95",
                        "bin_name": "mpm-linux-arm64-346ce66.bin",
                    },
                    {
                        "os": "ubuntu-24.04-arm",
                        "entry_point": "mpm",
                        "commit": "6f27db47612aaee06fdf08744b09a9f5f6c2",
                        "bin_name": "mpm-linux-arm64-6f27db4.bin",
                    },
                    {
                        "os": "ubuntu-24.04",
                        "entry_point": "mpm",
                        "commit": "346ce664f055fbd042a25ee0b7e96702e95",
                        "bin_name": "mpm-linux-x64-346ce66.bin",
                    },
                    {
                        "os": "ubuntu-24.04",
                        "entry_point": "mpm",
                        "commit": "6f27db47612aaee06fdf08744b09a9f5f6c2",
                        "bin_name": "mpm-linux-x64-6f27db4.bin",
                    },
                    {
                        "os": "macos-15",
                        "entry_point": "mpm",
                        "commit": "346ce664f055fbd042a25ee0b7e96702e95",
                        "bin_name": "mpm-macos-arm64-346ce66.bin",
                    },
                    {
                        "os": "macos-15",
                        "entry_point": "mpm",
                        "commit": "6f27db47612aaee06fdf08744b09a9f5f6c2",
                        "bin_name": "mpm-macos-arm64-6f27db4.bin",
                    },
                    {
                        "os": "macos-13",
                        "entry_point": "mpm",
                        "commit": "346ce664f055fbd042a25ee0b7e96702e95",
                        "bin_name": "mpm-macos-x64-346ce66.bin",
                    },
                    {
                        "os": "macos-13",
                        "entry_point": "mpm",
                        "commit": "6f27db47612aaee06fdf08744b09a9f5f6c2",
                        "bin_name": "mpm-macos-x64-6f27db4.bin",
                    },
                    {
                        "os": "windows-11-arm",
                        "entry_point": "mpm",
                        "commit": "346ce664f055fbd042a25ee0b7e96702e95",
                        "bin_name": "mpm-windows-arm64-346ce66.bin",
                    },
                    {
                        "os": "windows-11-arm",
                        "entry_point": "mpm",
                        "commit": "6f27db47612aaee06fdf08744b09a9f5f6c2",
                        "bin_name": "mpm-windows-arm64-6f27db4.bin",
                    },
                    {
                        "os": "windows-2025",
                        "entry_point": "mpm",
                        "commit": "346ce664f055fbd042a25ee0b7e96702e95",
                        "bin_name": "mpm-windows-x64-346ce66.exe",
                    },
                    {
                        "os": "windows-2025",
                        "entry_point": "mpm",
                        "commit": "6f27db47612aaee06fdf08744b09a9f5f6c2",
                        "bin_name": "mpm-windows-x64-6f27db4.exe",
                    },
                    {
                        "state": "stable",
                    },
                ],
            }
        """
        # Only produce a matrix if the project is providing CLI entry points.
        if not self.script_entries:
            return None

        matrix = Matrix()

        # Register all runners on which we want to run Nuitka builds.
        matrix.add_variation(
            "os", tuple(map(itemgetter("os"), NUITKA_BUILD_TARGETS.values()))
        )
        # Augment each "os" entry with platform-specific data.
        for target_id, target_data in NUITKA_BUILD_TARGETS.items():
            matrix.add_includes({"target": target_id} | target_data)

        # Augment each entry point with some metadata.
        for cli_id, module_id, callable_id in self.script_entries:
            # CLI ID is supposed to be unique, we'll use that as a key.
            matrix.add_variation("entry_point", [cli_id])
            # Derive CLI module path from its ID.
            # XXX We consider here the module is directly callable, because Nuitka
            # doesn't seems to support the entry-point notation.
            module_path = Path(f"{module_id.replace('.', '/')}.py")
            assert module_path.exists()
            matrix.add_includes({
                "entry_point": cli_id,
                "cli_id": cli_id,
                "module_id": module_id,
                "callable_id": callable_id,
                "module_path": str(module_path),
            })

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
        matrix.add_variation("commit", build_commit_matrix["commit"])
        matrix.add_includes(*build_commit_matrix.include)

        # Augment each variation set of the matrix with a the binary name to be
        # produced by Nuitka. Itererate over all matrix variation sets so we have all
        # metadata necessary to generate a unique name specific to these variations.
        for variations in matrix.solve():
            # We will re-attach back this binary name to the with an include directive,
            # so we need a copy the main variants it corresponds to.
            bin_name_include = {k: variations[k] for k in matrix}
            bin_name_include["bin_name"] = (
                "{cli_id}-{target}-{short_sha}.{extension}"
            ).format(**variations)
            matrix.add_includes(bin_name_include)

        # All jobs are stable by default, unless marked otherwise by specific
        # configuration.
        matrix.add_includes({"state": "stable"})
        for unstable_target in self.unstable_targets:
            matrix.add_includes({
                "state": "unstable",
                "os": NUITKA_BUILD_TARGETS[unstable_target]["os"],
            })

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

    def dump(self, dialect: Dialects = Dialects.github) -> str:
        """Returns all metadata in the specified format.

        Defaults to GitHub dialect.
        """
        metadata: dict[str, Any] = {
            "new_commits": self.new_commits_hash,
            "release_commits": self.release_commits_hash,
            "gitignore_exists": self.gitignore_exists,
            "python_files": self.python_files,
            "doc_files": self.doc_files,
            "is_python_project": self.is_python_project,
            "package_name": self.package_name,
            "blacken_docs_params": self.blacken_docs_params,
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
            assert dialect == Dialects.plain
            content = repr(metadata)

        logging.debug(f"Formatted metadata:\n{content}")

        return content
