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

"""Prepare a release by updating changelog, citation, and workflow files.

This module orchestrates the full release preparation across multiple file
types, delegating changelog operations to :mod:`gha_utils.changelog`. It
handles:

- Changelog freeze via :meth:`Changelog.freeze() <gha_utils.changelog.Changelog.freeze>`.
- Setting the release date in ``citation.cff``.
- Freezing workflow URLs to versioned tags (for `kdeldycke/workflows`).
- Freezing ``gha-utils`` CLI invocations to PyPI versions, unfreezing back to
  local source (``--from . gha-utils``).
"""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone
from functools import cached_property
from pathlib import Path
from urllib.request import Request, urlopen

from .changelog import Changelog

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]


class ReleasePrep:
    """Prepare files for a release by updating dates, URLs, and removing warnings."""

    def __init__(
        self,
        changelog_path: Path | None = None,
        citation_path: Path | None = None,
        workflow_dir: Path | None = None,
        default_branch: str = "main",
    ) -> None:
        self.changelog_path = changelog_path or Path("./changelog.md").resolve()
        self.citation_path = citation_path or Path("./citation.cff").resolve()
        self.workflow_dir = workflow_dir or Path("./.github/workflows").resolve()
        self.default_branch = default_branch
        self.modified_files: list[Path] = []

    @cached_property
    def current_version(self) -> str:
        """Extract current version from bump-my-version config in pyproject.toml."""
        config_file = Path("./pyproject.toml").resolve()
        logging.info(f"Reading version from {config_file}")
        config = tomllib.loads(config_file.read_text(encoding="UTF-8"))
        version: str = config["tool"]["bumpversion"]["current_version"]
        logging.info(f"Current version: {version}")
        return version

    @cached_property
    def release_date(self) -> str:
        """Return today's date in UTC as YYYY-MM-DD."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _update_file(self, path: Path, content: str, original: str) -> bool:
        """Write content to file if it changed. Return True if modified."""
        if content != original:
            path.write_text(content, encoding="UTF-8")
            self.modified_files.append(path)
            logging.info(f"Updated {path}")
            return True
        logging.debug(f"No changes to {path}")
        return False

    def set_citation_release_date(self) -> bool:
        """Update the ``date-released`` field in citation.cff.

        :return: True if the file was modified.
        """
        if not self.citation_path.exists():
            logging.debug(f"Citation file not found: {self.citation_path}")
            return False

        original = self.citation_path.read_text(encoding="UTF-8")
        content = re.sub(
            r"date-released: \d{4}-\d{2}-\d{2}",
            f"date-released: {self.release_date}",
            original,
            count=1,
        )

        return self._update_file(self.citation_path, content, original)

    def freeze_workflow_urls(self) -> int:
        """Replace workflow URLs from default branch to versioned tag.

        This is part of the **freeze** step: it freezes workflow references to
        the release tag so released versions reference immutable URLs.

        Replaces ``/workflows/{default_branch}/`` with ``/workflows/v{version}/``
        and ``/workflows/.github/actions/...@{default_branch}`` with
        ``/workflows/.github/actions/...@v{version}`` in all workflow YAML files.

        :return: Number of files modified.
        """
        if not self.workflow_dir.exists():
            logging.debug(f"Workflow directory not found: {self.workflow_dir}")
            return 0

        count = 0
        # URL pattern: /workflows/main/ -> /workflows/v1.2.3/
        url_search = f"/workflows/{self.default_branch}/"
        url_replace = f"/workflows/v{self.current_version}/"
        # Action reference pattern: /workflows/.github/...@main -> @v1.2.3
        action_search = f"/workflows/.github/actions/pr-metadata@{self.default_branch}"
        action_replace = (
            f"/workflows/.github/actions/pr-metadata@v{self.current_version}"
        )

        for workflow_file in self.workflow_dir.glob("*.yaml"):
            original = workflow_file.read_text(encoding="UTF-8")
            content = original.replace(url_search, url_replace)
            content = content.replace(action_search, action_replace)
            if self._update_file(workflow_file, content, original):
                count += 1

        return count

    @staticmethod
    def _get_latest_pypi_version(package: str) -> str:
        """Fetch the latest published version of a package from PyPI.

        :param package: The PyPI package name.
        :return: The latest version string.
        :raises RuntimeError: If the PyPI API request fails.
        """
        url = f"https://pypi.org/pypi/{package}/json"
        request = Request(url, headers={"Accept": "application/json"})
        logging.info(f"Fetching latest version of {package} from PyPI")
        with urlopen(request) as response:  # noqa: S310
            data = json.loads(response.read())
        version: str = data["info"]["version"]
        logging.info(f"Latest PyPI version of {package}: {version}")
        return version

    def freeze_cli_version(self, version: str) -> int:
        """Replace local source CLI invocations with a frozen PyPI version.

        This is part of the **freeze** step: it freezes ``gha-utils``
        invocations to a specific PyPI version so the released workflow files
        reference a published package. Downstream repos that check out a tagged
        release will install from PyPI rather than expecting a local source
        tree.

        Replaces ``--from . gha-utils`` with ``'gha-utils=={version}'`` in all
        workflow YAML files.

        :param version: The PyPI version to freeze to.
        :return: Number of files modified.
        """
        if not self.workflow_dir.exists():
            logging.debug(f"Workflow directory not found: {self.workflow_dir}")
            return 0

        count = 0
        search = "--from . gha-utils"
        replace = f"'gha-utils=={version}'"

        for workflow_file in self.workflow_dir.glob("*.yaml"):
            original = workflow_file.read_text(encoding="UTF-8")
            content = original.replace(search, replace)
            if self._update_file(workflow_file, content, original):
                count += 1

        return count

    def unfreeze_cli_version(self) -> int:
        """Replace frozen PyPI CLI invocations with local source.

        This is part of the **unfreeze** step: it reverts ``gha-utils``
        invocations back to local source (``--from . gha-utils``) for the next
        development cycle on ``main``.

        Replaces ``'gha-utils==X.Y.Z'`` with ``--from . gha-utils`` in all
        workflow YAML files.

        :return: Number of files modified.
        """
        if not self.workflow_dir.exists():
            logging.debug(f"Workflow directory not found: {self.workflow_dir}")
            return 0

        count = 0
        pattern = re.compile(r"'gha-utils==[\d.]+'")
        replace = "--from . gha-utils"

        for workflow_file in self.workflow_dir.glob("*.yaml"):
            original = workflow_file.read_text(encoding="UTF-8")
            content = pattern.sub(replace, original)
            if self._update_file(workflow_file, content, original):
                count += 1

        return count

    def unfreeze_workflow_urls(self) -> int:
        """Replace workflow URLs from versioned tag back to default branch.

        This is part of the **unfreeze** step: it reverts workflow references back
        to the default branch for the next development cycle.

        Replaces ``/workflows/v{version}/`` with ``/workflows/{default_branch}/``
        and ``/workflows/.github/actions/...@v{version}`` with
        ``/workflows/.github/actions/...@{default_branch}`` in all workflow YAML files.

        :return: Number of files modified.
        """
        if not self.workflow_dir.exists():
            logging.debug(f"Workflow directory not found: {self.workflow_dir}")
            return 0

        count = 0
        # URL pattern: /workflows/v1.2.3/ -> /workflows/main/
        url_search = f"/workflows/v{self.current_version}/"
        url_replace = f"/workflows/{self.default_branch}/"
        # Action reference pattern: @v1.2.3 -> @main
        action_search = (
            f"/workflows/.github/actions/pr-metadata@v{self.current_version}"
        )
        action_replace = f"/workflows/.github/actions/pr-metadata@{self.default_branch}"

        for workflow_file in self.workflow_dir.glob("*.yaml"):
            original = workflow_file.read_text(encoding="UTF-8")
            content = original.replace(url_search, url_replace)
            content = content.replace(action_search, action_replace)
            if self._update_file(workflow_file, content, original):
                count += 1

        return count

    def prepare_release(self, update_workflows: bool = False) -> list[Path]:
        """Run all freeze steps to prepare the release commit.

        :param update_workflows: If True, also freeze workflow URLs to versioned tag
            and freeze CLI invocations to the latest PyPI version.
        :return: List of modified files.
        """
        self.modified_files = []

        if Changelog.freeze_file(
            self.changelog_path,
            version=self.current_version,
            release_date=self.release_date,
            default_branch=self.default_branch,
        ):
            self.modified_files.append(self.changelog_path)

        self.set_citation_release_date()

        if update_workflows:
            self.freeze_workflow_urls()
            pypi_version = self._get_latest_pypi_version("gha-utils")
            self.freeze_cli_version(pypi_version)

        return self.modified_files

    def post_release(self, update_workflows: bool = False) -> list[Path]:
        """Run all unfreeze steps to prepare the post-release commit.

        :param update_workflows: If True, unfreeze workflow URLs back to default
            branch and unfreeze CLI invocations back to local source.
        :return: List of modified files.
        """
        self.modified_files = []

        if update_workflows:
            self.unfreeze_workflow_urls()
            self.unfreeze_cli_version()

        return self.modified_files
