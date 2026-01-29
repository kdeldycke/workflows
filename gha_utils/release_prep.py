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

This module consolidates all release preparation logic that was previously
scattered across multiple bump-my-version ``replace`` commands in the workflow.
It handles:

- Setting the release date in changelog and citation files.
- Updating GitHub comparison URLs from ``main`` to the release tag.
- Removing the "unreleased" warning from the changelog.
- Hard-coding version numbers in workflow URLs (for kdeldycke/workflows).
"""

from __future__ import annotations

import logging
import re
import sys
from datetime import datetime, timezone
from functools import cached_property
from pathlib import Path

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

    def set_changelog_release_date(self) -> bool:
        """Replace `` (unreleased)`` with the release date in changelog.

        :return: True if the file was modified.
        """
        if not self.changelog_path.exists():
            logging.warning(f"Changelog not found: {self.changelog_path}")
            return False

        original = self.changelog_path.read_text(encoding="UTF-8")
        # Only replace the first occurrence (the current release section).
        content = original.replace(" (unreleased)", f" ({self.release_date})", 1)

        return self._update_file(self.changelog_path, content, original)

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

    def update_changelog_comparison_url(self) -> bool:
        """Update the GitHub comparison URL from ``...main`` to ``...v{version}``.

        :return: True if the file was modified.
        """
        if not self.changelog_path.exists():
            logging.warning(f"Changelog not found: {self.changelog_path}")
            return False

        original = self.changelog_path.read_text(encoding="UTF-8")
        # Only replace the first occurrence (the current release section).
        content = original.replace(
            f"...{self.default_branch})",
            f"...v{self.current_version})",
            1,
        )

        return self._update_file(self.changelog_path, content, original)

    def remove_changelog_warning(self) -> bool:
        """Remove the first ``[!IMPORTANT]`` GFM alert from changelog.

        :return: True if the file was modified.
        """
        if not self.changelog_path.exists():
            logging.warning(f"Changelog not found: {self.changelog_path}")
            return False

        original = self.changelog_path.read_text(encoding="UTF-8")
        # Match the first multi-line important GFM alert block.
        # The pattern matches:
        #   > [!IMPORTANT]
        #   > ...any content...
        #   <blank line>
        content = re.sub(
            r"^> \[!IMPORTANT\].+?\n\n",
            "",
            original,
            count=1,
            flags=re.MULTILINE | re.DOTALL,
        )

        return self._update_file(self.changelog_path, content, original)

    def hardcode_workflow_version(self) -> int:
        """Replace workflow URLs from default branch to versioned tag.

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

    def retarget_workflow_branch(self) -> int:
        """Replace workflow URLs from versioned tag back to default branch.

        Replaces ``/workflows/v{version}/`` with ``/workflows/{default_branch}/``
        and ``/workflows/.github/actions/...@v{version}`` with
        ``/workflows/.github/actions/...@{default_branch}`` in all workflow YAML files.
        This is used after the release commit to prepare for the next development cycle.

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
        """Run all release preparation steps.

        :param update_workflows: If True, also update workflow URLs to versioned tag.
        :return: List of modified files.
        """
        self.modified_files = []

        self.set_changelog_release_date()
        self.set_citation_release_date()
        self.update_changelog_comparison_url()
        self.remove_changelog_warning()

        if update_workflows:
            self.hardcode_workflow_version()

        return self.modified_files

    def post_release(self, update_workflows: bool = False) -> list[Path]:
        """Run post-release steps to retarget workflow URLs.

        :param update_workflows: If True, retarget workflow URLs to default branch.
        :return: List of modified files.
        """
        self.modified_files = []

        if update_workflows:
            self.retarget_workflow_branch()

        return self.modified_files
