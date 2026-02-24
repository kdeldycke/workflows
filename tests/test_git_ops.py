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

"""Tests for Git operations module."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from repokit.git_ops import (
    create_and_push_tag,
    create_tag,
    push_tag,
    tag_exists,
)


def test_tag_exists_true():
    """Return True when tag exists."""
    with patch("repokit.git_ops.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert tag_exists("v1.0.0") is True
        mock_run.assert_called_once_with(
            ["git", "show-ref", "--tags", "v1.0.0", "--quiet"],
            capture_output=True,
        )


def test_tag_exists_false():
    """Return False when tag does not exist."""
    with patch("repokit.git_ops.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        assert tag_exists("v1.0.0") is False


def test_create_tag_head():
    """Create tag at HEAD."""
    with patch("repokit.git_ops.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        create_tag("v1.0.0")
        mock_run.assert_called_once_with(
            ["git", "tag", "v1.0.0"],
            check=True,
            capture_output=True,
            text=True,
        )


def test_create_tag_at_commit():
    """Create tag at specific commit."""
    with patch("repokit.git_ops.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        create_tag("v1.0.0", "abc123")
        mock_run.assert_called_once_with(
            ["git", "tag", "v1.0.0", "abc123"],
            check=True,
            capture_output=True,
            text=True,
        )


def test_create_tag_failure():
    """Raise exception on git failure."""
    with patch("repokit.git_ops.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        with pytest.raises(subprocess.CalledProcessError):
            create_tag("v1.0.0")


def test_push_tag_default_remote():
    """Push tag to default origin remote."""
    with patch("repokit.git_ops.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        push_tag("v1.0.0")
        mock_run.assert_called_once_with(
            ["git", "push", "origin", "v1.0.0"],
            check=True,
            capture_output=True,
            text=True,
        )


def test_push_tag_custom_remote():
    """Push tag to custom remote."""
    with patch("repokit.git_ops.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        push_tag("v1.0.0", remote="upstream")
        mock_run.assert_called_once_with(
            ["git", "push", "upstream", "v1.0.0"],
            check=True,
            capture_output=True,
            text=True,
        )


def test_push_tag_failure():
    """Raise exception on push failure."""
    with patch("repokit.git_ops.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        with pytest.raises(subprocess.CalledProcessError):
            push_tag("v1.0.0")


def test_create_new_tag():
    """Create and push new tag."""
    with patch("repokit.git_ops.tag_exists", return_value=False):
        with patch("repokit.git_ops.create_tag") as mock_create:
            with patch("repokit.git_ops.push_tag") as mock_push:
                result = create_and_push_tag("v1.0.0")
                assert result is True
                mock_create.assert_called_once_with("v1.0.0", None)
                mock_push.assert_called_once_with("v1.0.0")


def test_create_and_push_tag_at_commit():
    """Create and push tag at specific commit."""
    with patch("repokit.git_ops.tag_exists", return_value=False):
        with patch("repokit.git_ops.create_tag") as mock_create:
            with patch("repokit.git_ops.push_tag"):
                result = create_and_push_tag("v1.0.0", commit="abc123")
                assert result is True
                mock_create.assert_called_once_with("v1.0.0", "abc123")


def test_skip_existing_tag():
    """Skip when tag exists and skip_existing is True."""
    with patch("repokit.git_ops.tag_exists", return_value=True):
        with patch("repokit.git_ops.create_tag") as mock_create:
            with patch("repokit.git_ops.push_tag") as mock_push:
                result = create_and_push_tag("v1.0.0", skip_existing=True)
                assert result is False
                mock_create.assert_not_called()
                mock_push.assert_not_called()


def test_error_existing_tag():
    """Raise ValueError when tag exists and skip_existing is False."""
    with patch("repokit.git_ops.tag_exists", return_value=True):
        with pytest.raises(ValueError, match="already exists"):
            create_and_push_tag("v1.0.0", skip_existing=False)


def test_create_without_push():
    """Create tag without pushing."""
    with patch("repokit.git_ops.tag_exists", return_value=False):
        with patch("repokit.git_ops.create_tag") as mock_create:
            with patch("repokit.git_ops.push_tag") as mock_push:
                result = create_and_push_tag("v1.0.0", push=False)
                assert result is True
                mock_create.assert_called_once()
                mock_push.assert_not_called()
