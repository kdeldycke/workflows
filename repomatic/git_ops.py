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

.. warning:: Tag push requires ``WORKFLOW_UPDATE_GITHUB_PAT``

   Tags pushed with the default ``GITHUB_TOKEN`` do not trigger downstream
   ``on.push.tags`` workflows. The custom PAT is required so that tagging
   a release commit actually fires the publish and release creation jobs.
"""

from __future__ import annotations

import logging
import subprocess


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
