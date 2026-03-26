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

"""Git operations for GitHub Actions workflows.

This module provides utilities for common Git operations in CI/CD contexts,
with idempotent behavior to allow safe re-runs of failed workflows.

All operations follow a "belt-and-suspenders" approach: combine workflow
timing guarantees (e.g. ``workflow_run`` ensures tags exist) with idempotent
guards (e.g. ``skip_existing`` on tag creation). This ensures correctness
in the face of race conditions, API eventual consistency, and partial failures
that are common in GitHub Actions.

.. warning:: Tag push requires ``REPOMATIC_PAT``

   Tags pushed with the default ``GITHUB_TOKEN`` do not trigger downstream
   ``on.push.tags`` workflows. The custom PAT is required so that tagging
   a release commit actually fires the publish and release creation jobs.
"""

from __future__ import annotations

import logging
import re
import subprocess

from packaging.version import Version
from pydriller import Git  # type: ignore[import-untyped]

SHORT_SHA_LENGTH = 7
"""Default SHA length hard-coded to ``7``.

.. caution::

    The `default is subject to change <https://stackoverflow.com/a/21015031>`_ and
    depends on the size of the repository.
"""

RELEASE_COMMIT_PATTERN = re.compile(
    r"^\[changelog\] Release v(?P<version>[0-9]+\.[0-9]+\.[0-9]+)$"
)
"""Pre-compiled regex for release commit messages.

Matches the full message and captures the version number. Use ``fullmatch``
to validate a commit is a release commit, or ``match``/``search`` with
``.group("version")`` to extract the version string.

A rebase merge preserves the original commit messages, so release commits
match this pattern. A squash merge replaces them with the PR title
(e.g. ``Release `v1.2.3` (#42)``), which does **not** match. This mismatch
is the mechanism by which squash merges are safely skipped: the ``create-tag``
job only processes commits matching this pattern, so no tag, PyPI publish, or
GitHub release is created from a squash merge. The ``detect-squash-merge``
job in ``release.yaml`` detects this and opens an issue to notify the
maintainer.
"""


def get_latest_tag_version() -> Version | None:
    """Returns the latest release version from Git tags.

    Looks for tags matching the pattern ``vX.Y.Z`` and returns the highest version.
    Returns ``None`` if no matching tags are found.
    """
    git = Git(".")
    # Get all tags matching the version pattern.
    tags = git.repo.git.tag("--list", "v[0-9]*.[0-9]*.[0-9]*").splitlines()

    if not tags:
        logging.debug("No version tags found in repository.")
        return None

    # Parse and find the highest version.
    versions = []
    for tag in tags:
        # Strip the 'v' prefix and parse.
        version = Version(tag.lstrip("v"))
        versions.append(version)

    latest = max(versions)
    logging.debug(f"Latest tag version: {latest}")
    return latest


def get_release_version_from_commits(max_count: int = 10) -> Version | None:
    """Extract release version from recent commit messages.

    Searches recent commits for messages matching the pattern
    ``[changelog] Release vX.Y.Z`` and returns the version from the most recent match.

    This provides a fallback when tags haven't been pushed yet due to race conditions
    between workflows. The release commit message contains the version information
    before the tag is created.

    :param max_count: Maximum number of commits to search.
    :return: The version from the most recent release commit, or ``None`` if not found.
    """
    git = Git(".")

    for commit in git.repo.iter_commits("HEAD", max_count=max_count):
        match = RELEASE_COMMIT_PATTERN.fullmatch(commit.message.strip())
        if match:
            version = Version(match.group("version"))
            logging.debug(f"Found release version {version} in commit {commit.hexsha}")
            return version

    logging.debug("No release commit found in recent history.")
    return None


def get_tag_date(tag: str) -> str | None:
    """Get the date of a Git tag in ``YYYY-MM-DD`` format.

    Uses ``creatordate`` which resolves to the tagger date for annotated
    tags and the commit date for lightweight tags.

    :param tag: The tag name to look up.
    :return: Date string in ``YYYY-MM-DD`` format, or ``None`` if the
        tag does not exist.
    """
    result = subprocess.run(
        ["git", "tag", "-l", "--format=%(creatordate:short)", tag],
        capture_output=True,
        text=True,
        check=False,
    )
    date = result.stdout.strip()
    if not date:
        return None
    return date


def get_all_version_tags() -> dict[str, str]:
    """Get all version tags and their dates.

    Runs a single ``git tag`` command to list all tags matching the
    ``vX.Y.Z`` pattern and extracts their dates.

    :return: Dict mapping version strings (without ``v`` prefix) to
        dates in ``YYYY-MM-DD`` format.
    """
    result = subprocess.run(
        [
            "git",
            "tag",
            "-l",
            "v[0-9]*.[0-9]*.[0-9]*",
            "--format=%(refname:short) %(creatordate:short)",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    tags: dict[str, str] = {}
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            tag, date = parts
            if tag.startswith("v"):
                tags[tag[1:]] = date
    return tags


def tag_exists(tag: str) -> bool:
    """Check if a Git tag already exists locally.

    :param tag: The tag name to check.
    :return: True if the tag exists, False otherwise.
    """
    result = subprocess.run(
        ["git", "show-ref", "--tags", tag, "--quiet"],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def create_tag(tag: str, commit: str | None = None) -> None:
    """Create a local Git tag.

    :param tag: The tag name to create.
    :param commit: The commit to tag. Defaults to HEAD.
    :raises subprocess.CalledProcessError: If tag creation fails.
    """
    cmd = ["git", "tag", tag]
    if commit:
        cmd.append(commit)
    logging.debug(f"Creating tag: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def push_tag(tag: str, remote: str = "origin") -> None:
    """Push a Git tag to a remote repository.

    :param tag: The tag name to push.
    :param remote: The remote name. Defaults to "origin".
    :raises subprocess.CalledProcessError: If push fails.
    """
    cmd = ["git", "push", remote, tag]
    logging.debug(f"Pushing tag: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def create_and_push_tag(
    tag: str,
    commit: str | None = None,
    push: bool = True,
    skip_existing: bool = True,
) -> bool:
    """Create and optionally push a Git tag.

    This function is idempotent: if the tag already exists and ``skip_existing``
    is True, it returns False without failing. This allows safe re-runs of
    workflows that were interrupted after tag creation but before other steps.

    :param tag: The tag name to create.
    :param commit: The commit to tag. Defaults to HEAD.
    :param push: Whether to push the tag to the remote. Defaults to True.
    :param skip_existing: If True, skip silently when tag exists.
        If False, raise an error. Defaults to True.
    :return: True if the tag was created, False if it already existed.
    :raises ValueError: If tag exists and skip_existing is False.
    :raises subprocess.CalledProcessError: If Git operations fail.
    """
    if tag_exists(tag):
        if skip_existing:
            logging.info(f"Tag {tag!r} already exists, skipping.")
            return False
        msg = f"Tag {tag!r} already exists."
        raise ValueError(msg)

    create_tag(tag, commit)
    logging.info(f"Created tag {tag!r}")

    if push:
        push_tag(tag)
        logging.info(f"Pushed tag {tag!r} to remote.")

    return True
