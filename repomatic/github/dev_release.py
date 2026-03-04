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

Maintains a single **draft** pre-release that mirrors the unreleased
changelog section and always carries the latest successful dev binaries
and Python package. The dev tag (e.g. ``v6.1.1.dev0``) is force-updated
to point to the latest ``main`` commit — no tag proliferation.

When the current version's dev release already exists, it is **edited**
(not deleted and recreated) so that previously uploaded assets — especially
compiled binaries — survive pushes that skip binary compilation (e.g.
documentation-only changes). The workflow's upload step uses ``--clobber``
to replace assets when new builds are available. Stale dev releases from
previous versions are always deleted.

.. note::
    Dev releases are created as **drafts** so they remain mutable even
    when GitHub's immutable releases setting is enabled. Immutability
    only blocks **asset uploads** on published releases — deletion still
    works. But because the workflow needs to upload binaries *after*
    creation, the release must stay as a draft throughout its lifetime
    to allow asset uploads. See ``CLAUDE.md`` § Immutable releases.
"""

from __future__ import annotations

import json
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
    via :func:`build_expected_body`, then either edits the existing dev
    release or creates a new one. Stale dev releases from previous
    versions are always cleaned up.

    Existing releases are edited (not deleted and recreated) to preserve
    assets like compiled binaries from previous successful builds. The
    workflow's upload step uses ``--clobber`` to replace assets when new
    ones are available.

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
        logging.warning(f"Changelog section for {version} produced an empty body.")
        return False

    tag = f"v{version}"

    if dry_run:
        logging.info(f"[dry-run] Would sync dev release {tag}.")
        logging.info(f"[dry-run] Release body:\n{body}")
        return True

    # Delete stale dev releases from previous versions, preserving the current one.
    cleanup_dev_releases(nwo, keep_tag=tag)

    # Try to edit the existing release first. This preserves assets (binaries)
    # from previous successful builds when the current push skips compilation.
    if _edit_dev_release(tag, version, body, nwo):
        logging.info(f"Updated existing dev draft pre-release {tag}.")
    else:
        # No existing release to edit; create a new draft pre-release targeting
        # main. Draft stays mutable so the workflow can upload binaries and
        # packages after creation, and so immutable releases don't block asset
        # uploads or future deletions.
        run_gh_command([
            "release",
            "create",
            tag,
            "--draft",
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
        logging.info(f"Created dev draft pre-release {tag}.")

    return True


def cleanup_dev_releases(nwo: str, *, keep_tag: str | None = None) -> None:
    """Delete stale dev pre-releases from GitHub.

    Lists all releases and deletes any whose tag ends with ``.dev0``,
    except ``keep_tag`` which is preserved so its assets (e.g. compiled
    binaries) survive. This handles stale dev releases left behind after
    version bumps. Silently succeeds if no dev releases exist or if
    individual deletions fail.

    :param nwo: Repository name-with-owner (e.g. ``user/repo``).
    :param keep_tag: Tag to preserve (e.g. ``v6.2.0.dev0``). If ``None``,
        all dev releases are deleted.
    """
    try:
        output = run_gh_command([
            "release",
            "list",
            "--json",
            "tagName",
            "--repo",
            nwo,
        ])
    except RuntimeError:
        logging.debug("Could not list releases.")
        return

    releases = json.loads(output)
    for release in releases:
        tag = release["tagName"]
        if tag.endswith(".dev0") and tag != keep_tag:
            delete_release_by_tag(tag, nwo)


def _edit_dev_release(tag: str, version: str, body: str, nwo: str) -> bool:
    """Edit an existing dev release's metadata.

    Updates the title and body of an existing release without touching its
    assets. Returns ``False`` if the release does not exist.

    :param tag: Git tag name (e.g. ``v6.1.1.dev0``).
    :param version: Version string for the title (e.g. ``6.1.1.dev0``).
    :param body: Release body text.
    :param nwo: Repository name-with-owner (e.g. ``user/repo``).
    :return: ``True`` if the release was edited, ``False`` if it doesn't exist.
    """
    try:
        run_gh_command([
            "release",
            "edit",
            tag,
            "--title",
            version,
            "--notes",
            body,
            "--repo",
            nwo,
        ])
        return True
    except RuntimeError:
        return False


def delete_dev_release(version: str, nwo: str) -> None:
    """Delete the dev pre-release and its tag from GitHub.

    Silently succeeds if no dev release exists. This is used during
    real releases to clean up the dev pre-release for the version
    being released.

    :param version: Dev version string (e.g. ``6.1.1.dev0``).
    :param nwo: Repository name-with-owner (e.g. ``user/repo``).
    """
    delete_release_by_tag(f"v{version}", nwo)


def delete_release_by_tag(tag: str, nwo: str) -> None:
    """Delete a release and its tag from GitHub.

    Silently succeeds if the release does not exist or cannot be deleted.

    :param tag: Git tag name (e.g. ``v6.1.1.dev0``).
    :param nwo: Repository name-with-owner (e.g. ``user/repo``).
    """
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
        logging.debug(f"Could not delete release {tag}.")
