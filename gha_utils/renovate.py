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

"""Renovate-related utilities for GitHub Actions workflows.

This module provides utilities for managing Renovate prerequisites and
updating the ``exclude-newer`` date in ``pyproject.toml`` files.
"""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from datetime import date, timedelta

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]
from pathlib import Path

from .github import AnnotationLevel, emit_annotation

TYPE_CHECKING = False
if TYPE_CHECKING:
    from datetime import date as DateType


def parse_exclude_newer_date(pyproject_path: Path) -> DateType | None:
    """Parse the exclude-newer date from pyproject.toml.

    :param pyproject_path: Path to the pyproject.toml file.
    :return: The date if found, None otherwise.
    """
    if not pyproject_path.exists():
        logging.debug(f"{pyproject_path} does not exist.")
        return None

    content = pyproject_path.read_text(encoding="utf-8")
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError as e:
        logging.warning(f"Failed to parse TOML: {e}")
        return None

    # Navigate to tool.uv.pip.exclude-newer or tool.uv.exclude-newer.
    tool_uv = data.get("tool", {}).get("uv", {})
    exclude_newer = tool_uv.get("pip", {}).get("exclude-newer") or tool_uv.get(
        "exclude-newer"
    )

    if not exclude_newer:
        logging.debug("No exclude-newer field found.")
        return None

    # Extract just the date part (YYYY-MM-DD) from the ISO timestamp.
    match = re.match(r"(\d{4}-\d{2}-\d{2})", exclude_newer)
    if not match:
        logging.warning(f"Could not parse date from {exclude_newer!r}")
        return None

    return date.fromisoformat(match.group(1))


def calculate_target_date(days_ago: int = 7) -> DateType:
    """Calculate the target date for exclude-newer.

    :param days_ago: Number of days in the past. Defaults to 7.
    :return: The target date.
    """
    return date.today() - timedelta(days=days_ago)


def has_tool_uv_section(pyproject_path: Path) -> bool:
    """Check if pyproject.toml has a [tool.uv] section.

    :param pyproject_path: Path to the pyproject.toml file.
    :return: True if [tool.uv] section exists, False otherwise.
    """
    if not pyproject_path.exists():
        return False

    content = pyproject_path.read_text(encoding="utf-8")
    try:
        data = tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        return False

    return "uv" in data.get("tool", {})


def add_exclude_newer_to_file(pyproject_path: Path, target_date: DateType) -> bool:
    """Add exclude-newer to [tool.uv] section if missing.

    Inserts the exclude-newer setting right after the [tool.uv] header line.
    Only works if [tool.uv] section exists but exclude-newer is not set.

    :param pyproject_path: Path to the pyproject.toml file.
    :param target_date: The date to set.
    :return: True if the file was modified, False otherwise.
    """
    if not pyproject_path.exists():
        logging.info(f"{pyproject_path} does not exist.")
        return False

    content = pyproject_path.read_text(encoding="utf-8")

    # Check if [tool.uv] exists.
    if not re.search(r"^\[tool\.uv\]", content, re.MULTILINE):
        logging.info("No [tool.uv] section found.")
        return False

    # Check if exclude-newer already exists.
    if re.search(r"^exclude-newer\s*=", content, re.MULTILINE):
        logging.debug("exclude-newer already exists.")
        return False

    new_timestamp = f"{target_date.isoformat()}T00:00:00Z"

    # Insert exclude-newer after [tool.uv] line.
    # The setting is added with a comment explaining its purpose.
    exclude_newer_block = (
        "# Cooldown period: 7-day buffer before using newly released packages.\n"
        '# Use a fixed date (not relative like "1 week") to prevent uv.lock '
        "timestamp churn.\n"
        "# This date is auto-updated by the autofix workflow when it becomes stale.\n"
        f'exclude-newer = "{new_timestamp}"\n'
    )

    new_content = re.sub(
        r"^(\[tool\.uv\]\n)",
        rf"\g<1>{exclude_newer_block}",
        content,
        count=1,
        flags=re.MULTILINE,
    )

    if new_content == content:
        logging.warning("Failed to insert exclude-newer.")
        return False

    pyproject_path.write_text(new_content, encoding="utf-8")
    logging.info(f"Added exclude-newer = {new_timestamp}")
    return True


def update_exclude_newer_in_file(pyproject_path: Path, target_date: DateType) -> bool:
    """Update the exclude-newer date in pyproject.toml.

    Uses regex replacement to preserve formatting and comments.

    :param pyproject_path: Path to the pyproject.toml file.
    :param target_date: The new date to set.
    :return: True if the file was modified, False otherwise.
    """
    if not pyproject_path.exists():
        logging.info(f"{pyproject_path} does not exist.")
        return False

    content = pyproject_path.read_text(encoding="utf-8")
    new_timestamp = f"{target_date.isoformat()}T00:00:00Z"

    # Replace the exclude-newer value.
    new_content, count = re.subn(
        r'(exclude-newer\s*=\s*")[^"]*(")',
        rf"\g<1>{new_timestamp}\g<2>",
        content,
    )

    if count == 0:
        logging.info("No exclude-newer field found to update.")
        return False

    if new_content == content:
        logging.info("exclude-newer date is already up to date.")
        return False

    pyproject_path.write_text(new_content, encoding="utf-8")
    logging.info(f"Updated exclude-newer to {new_timestamp}")
    return True


def check_dependabot_config_absent() -> tuple[bool, str]:
    """Check that no Dependabot version updates config file exists.

    Renovate handles dependency updates, so Dependabot should be disabled.

    :return: Tuple of (passed, message).
    """
    for filename in (".github/dependabot.yaml", ".github/dependabot.yml"):
        if Path(filename).exists():
            msg = (
                f"Dependabot config found at {filename}. "
                "Remove it and migrate to Renovate: "
                "run `gha-utils bundled export renovate.json5` to get a starter config, "
                "then use the reusable renovate.yaml workflow."
            )
            return False, msg

    return True, "Dependabot version updates: disabled (no config file)"


def check_dependabot_security_disabled(repo: str) -> tuple[bool, str]:
    """Check that Dependabot security updates are disabled.

    Renovate creates security PRs instead.

    :param repo: Repository in 'owner/repo' format.
    :return: Tuple of (passed, message).
    """
    try:
        result = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repo}",
                "--jq",
                ".security_and_analysis.dependabot_security_updates.status "
                '// "disabled"',
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        status = result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.warning(f"Failed to check Dependabot security status: {e}")
        return True, "Could not verify Dependabot security updates status."

    if status == "enabled":
        msg = (
            "Dependabot security updates are enabled. Disable them in "
            "Settings > Advanced Security > Dependabot > Dependabot security updates."
        )
        return False, msg

    return True, "Dependabot security updates: disabled (Renovate handles security PRs)"


def check_commit_statuses_permission(repo: str, sha: str) -> tuple[bool, str]:
    """Check that the token has commit statuses permission.

    Required for Renovate to set stability-days status checks.

    :param repo: Repository in 'owner/repo' format.
    :param sha: Commit SHA to check.
    :return: Tuple of (passed, message). This check never fails fatally.
    """
    try:
        subprocess.run(
            ["gh", "api", f"repos/{repo}/commits/{sha}/statuses", "--silent"],
            capture_output=True,
            check=True,
        )
        return True, "Commit statuses: token has access"
    except subprocess.CalledProcessError:
        msg = (
            "Cannot verify commit statuses permission. "
            "Ensure the token has 'Commit statuses: Read and Write' permission."
        )
        return True, msg  # Non-fatal.


def run_renovate_prereq_checks(repo: str, sha: str) -> int:
    """Run all Renovate prerequisite checks.

    Emits GitHub Actions annotations for each check result.

    :param repo: Repository in 'owner/repo' format.
    :param sha: Commit SHA for permission checks.
    :return: Exit code (0 for success, 1 for fatal errors).
    """
    fatal_error = False

    # Check 1: Dependabot config file.
    passed, msg = check_dependabot_config_absent()
    if passed:
        print(f"✓ {msg}")
    else:
        emit_annotation(AnnotationLevel.ERROR, msg)
        fatal_error = True

    # Check 2: Dependabot security updates.
    passed, msg = check_dependabot_security_disabled(repo)
    if passed:
        print(f"✓ {msg}")
    else:
        emit_annotation(AnnotationLevel.ERROR, msg)
        fatal_error = True

    # Check 3: Commit statuses permission (non-fatal).
    passed, msg = check_commit_statuses_permission(repo, sha)
    if passed:
        print(f"✓ {msg}")
    else:
        emit_annotation(AnnotationLevel.WARNING, msg)

    return 1 if fatal_error else 0
