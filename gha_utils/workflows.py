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

"""Access bundled workflow templates.

This module provides access to reusable GitHub Actions workflow templates that
are bundled with the package. The source files live in ``.github/workflows/``
for linting and formatting, but are copied into the package at build time.

Available workflows:

- ``autofix.yaml`` - Auto-formatting and dependency syncing
- ``autolock.yaml`` - Auto-locking inactive issues
- ``changelog.yaml`` - Version bumping and release preparation
- ``debug.yaml`` - Debugging and context dumping
- ``docs.yaml`` - Documentation building and deployment
- ``labels.yaml`` - Label management and PR auto-labeling
- ``lint.yaml`` - Linting and type checking
- ``release.yaml`` - Package building, binary compilation, and publishing
- ``renovate.yaml`` - Dependency update management
- ``tests.yaml`` - Test execution
"""

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 9):
    from importlib.resources import as_file, files
else:
    from importlib_resources import as_file, files  # type: ignore[import-not-found]


# All available workflow templates.
WORKFLOW_FILES = (
    "autofix.yaml",
    "autolock.yaml",
    "changelog.yaml",
    "debug.yaml",
    "docs.yaml",
    "labels.yaml",
    "lint.yaml",
    "release.yaml",
    "renovate.yaml",
    "tests.yaml",
)


def _get_workflow_path(filename: str) -> Path:
    """Get the path to a bundled workflow file.

    During development (editable install), falls back to reading from
    ``.github/workflows/``.

    :param filename: Name of the workflow file to retrieve.
    :return: Path to the file.
    :raises FileNotFoundError: If the file doesn't exist.
    """
    if filename not in WORKFLOW_FILES:
        msg = f"Unknown workflow: {filename}. Available: {', '.join(WORKFLOW_FILES)}"
        raise FileNotFoundError(msg)

    # Try to get from package data first (installed package).
    try:
        data_files = files("gha_utils.data.workflows")
        with as_file(data_files.joinpath(filename)) as path:
            if path.exists():
                return path
    except (ModuleNotFoundError, TypeError):
        pass

    # Fall back to .github/workflows/ directory (development/editable install).
    current = Path(__file__).resolve().parent
    for _ in range(5):  # Limit search depth.
        candidate = current / ".github" / "workflows" / filename
        if candidate.exists():
            return candidate
        current = current.parent

    msg = f"Workflow file not found: {filename}"
    raise FileNotFoundError(msg)


def list_workflows() -> tuple[str, ...]:
    """List all available workflow templates.

    :return: Tuple of workflow filenames.
    """
    return WORKFLOW_FILES


def get_workflow_content(filename: str) -> str:
    """Get the content of a workflow template.

    :param filename: Name of the workflow file (e.g., "release.yaml").
    :return: Content of the workflow file as a string.
    :raises FileNotFoundError: If the workflow doesn't exist.
    """
    return _get_workflow_path(filename).read_text(encoding="UTF-8")
