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

"""GitHub Actions output formatting, annotations, and workflow events.

This module provides utilities for working with GitHub Actions: multiline
output formatting, workflow annotations, event payload loading, and
GitHub-specific constants and enums shared across multiple modules.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from enum import Enum
from functools import lru_cache
from pathlib import Path
from random import randint

if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from backports.strenum import StrEnum  # type: ignore[import-not-found]

TYPE_CHECKING = False
if TYPE_CHECKING:
    from typing import Any, Literal


NULL_SHA = "0" * 40
"""The null SHA used by Git to represent a non-existent commit.

GitHub sends this value as the ``before`` SHA when a tag is created, since there is no
previous commit to compare against.
"""


class WorkflowEvent(StrEnum):
    """Workflow events that cause a workflow to run.

    `List of events
    <https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows>`_.
    """

    branch_protection_rule = "branch_protection_rule"
    check_run = "check_run"
    check_suite = "check_suite"
    create = "create"
    delete = "delete"
    deployment = "deployment"
    deployment_status = "deployment_status"
    discussion = "discussion"
    discussion_comment = "discussion_comment"
    fork = "fork"
    gollum = "gollum"
    issue_comment = "issue_comment"
    issues = "issues"
    label = "label"
    merge_group = "merge_group"
    milestone = "milestone"
    page_build = "page_build"
    project = "project"
    project_card = "project_card"
    project_column = "project_column"
    public = "public"
    pull_request = "pull_request"
    pull_request_comment = "pull_request_comment"
    pull_request_review = "pull_request_review"
    pull_request_review_comment = "pull_request_review_comment"
    pull_request_target = "pull_request_target"
    push = "push"
    registry_package = "registry_package"
    release = "release"
    repository_dispatch = "repository_dispatch"
    schedule = "schedule"
    status = "status"
    watch = "watch"
    workflow_call = "workflow_call"
    workflow_dispatch = "workflow_dispatch"
    workflow_run = "workflow_run"


class AnnotationLevel(Enum):
    """Annotation levels for GitHub Actions workflow commands."""

    ERROR = "error"
    WARNING = "warning"
    NOTICE = "notice"


def generate_delimiter() -> str:
    """Generate a unique delimiter for GitHub Actions multiline output.

    GitHub Actions requires a unique delimiter to encode multiline values in
    ``$GITHUB_OUTPUT``. This function generates a random delimiter that is
    extremely unlikely to appear in the output content.

    The delimiter format is ``GHA_DELIMITER_NNNNNNNNN`` where N is a digit,
    producing a 9-digit random suffix.

    :return: A unique delimiter string.

    .. seealso::
        https://github.com/orgs/community/discussions/26288#discussioncomment-3876281
    """
    return f"GHA_DELIMITER_{randint(10**8, (10**9) - 1)}"


def format_multiline_output(name: str, value: str) -> str:
    """Format a multiline value for GitHub Actions output.

    Produces output in the heredoc format required by ``$GITHUB_OUTPUT``:

    .. code-block:: text

        name<<GHA_DELIMITER_NNNNNNNNN
        value line 1
        value line 2
        GHA_DELIMITER_NNNNNNNNN

    :param name: The output variable name.
    :param value: The multiline value.
    :return: Formatted string for ``$GITHUB_OUTPUT``.
    """
    delimiter = generate_delimiter()
    return f"{name}<<{delimiter}\n{value}\n{delimiter}"


def emit_annotation(
    level: AnnotationLevel | Literal["error", "warning", "notice"],
    message: str,
) -> None:
    """Emit a GitHub Actions workflow annotation.

    Prints a workflow command that creates an annotation visible in the GitHub
    Actions UI and PR checks.

    :param level: The annotation level (error, warning, or notice).
    :param message: The annotation message.

    .. seealso::
        https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/workflow-commands-for-github-actions#setting-an-error-message
    """
    if isinstance(level, str):
        level = AnnotationLevel(level)
    print(f"::{level.value}::{message}")


@lru_cache(maxsize=1)
def get_github_event() -> dict[str, Any]:
    """Load the GitHub event payload from ``GITHUB_EVENT_PATH``.

    :return: The parsed event payload, or empty dict if not available.
    """
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return {}
    event_file = Path(event_path)
    if not event_file.exists():
        logging.warning(f"Event file not found: {event_path}")
        return {}
    return json.loads(event_file.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
