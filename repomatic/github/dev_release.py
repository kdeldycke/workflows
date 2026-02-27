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

"""Sync a rolling dev pre-release on GitHub.

Maintains a single pre-release that mirrors the unreleased changelog
section and always carries the latest successful dev binaries and
Python package. The dev tag (e.g. ``v6.1.1.dev0``) is force-updated
to point to the latest ``main`` commit — no tag proliferation.

.. note::
    If GitHub's immutable releases setting is enabled on the repository,
    published pre-releases cannot be deleted or have their assets replaced.
    The delete-then-recreate approach will fail in that case. Callers
    should handle :class:`RuntimeError` from ``run_gh_command`` gracefully.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .gh import run_gh_command
from .release_sync import build_expected_body

TYPE_CHECKING = False
if TYPE_CHECKING:
    pass


def sync_dev_release(
    changelog_path: Path,
    version: str,
    nwo: str,
    dry_run: bool = True,
) -> bool:
    """Create or update the dev pre-release on GitHub.

    Reads the changelog, renders the release body for the given version
    via :func:`build_expected_body`, then deletes any existing dev
    release and creates a new pre-release.

    :param changelog_path: Path to ``changelog.md``.
    :param version: Current version string (e.g. ``6.1.1.dev0``).
    :param nwo: Repository name-with-owner (e.g. ``user/repo``).
    :param dry_run: If ``True``, report without making changes.
    :return: ``True`` if the release was synced (or would be in
        dry-run), ``False`` if the changelog section is empty.
    """
    from ..changelog import Changelog

    content = changelog_path.read_text(encoding="UTF-8")
    changelog = Changelog(content)

    body = build_expected_body(changelog, version)
    if not body:
        logging.warning(
            f"Changelog section for {version} produced an empty body."
        )
        return False

    tag = f"v{version}"

    if dry_run:
        logging.info(f"[dry-run] Would sync dev release {tag}.")
        logging.info(f"[dry-run] Release body:\n{body}")
        return True

    # Delete existing dev release + tag. Silently succeed if none exists.
    delete_dev_release(version, nwo)

    # Create new pre-release targeting main.
    run_gh_command([
        "release",
        "create",
        tag,
        "--prerelease",
        "--target",
        "main",
        "--title",
        version,
        "--notes",
        body,
        "--repo",
        nwo,
    ])
    logging.info(f"Created dev pre-release {tag}.")

    return True


def delete_dev_release(version: str, nwo: str) -> None:
    """Delete the dev pre-release and its tag from GitHub.

    Silently succeeds if no dev release exists. This is used both
    during ``sync-dev-release`` (delete-then-recreate) and during
    real releases (cleanup of the dev pre-release).

    :param version: Dev version string (e.g. ``6.1.1.dev0``).
    :param nwo: Repository name-with-owner (e.g. ``user/repo``).
    """
    tag = f"v{version}"
    try:
        run_gh_command([
            "release",
            "delete",
            tag,
            "--cleanup-tag",
            "--yes",
            "--repo",
            nwo,
        ])
        logging.info(f"Deleted dev release {tag}.")
    except RuntimeError:
        logging.debug(f"No existing dev release {tag} to delete.")
