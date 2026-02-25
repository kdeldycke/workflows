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

"""GitHub token validation utilities.

Provides early validation for CLI commands that depend on the ``gh`` CLI
and GitHub API, so users get clear error messages at startup rather than
opaque failures mid-execution.
"""

from __future__ import annotations

import json
import logging
import os
from subprocess import run as _run_process

TYPE_CHECKING = False
if TYPE_CHECKING:
    pass


def validate_gh_token_env() -> None:
    """Check that ``GH_TOKEN`` environment variable is set.

    :raises RuntimeError: If ``GH_TOKEN`` is not set.
    """
    if not os.environ.get("GH_TOKEN"):
        msg = (
            "GH_TOKEN environment variable is not set. "
            "Create a personal access token at "
            "https://github.com/settings/tokens "
            "and set it as GH_TOKEN."
        )
        raise RuntimeError(msg)


def validate_gh_api_access() -> tuple[int, dict[str, str], str]:
    """Smoke-test the GitHub API and return parsed response.

    Calls ``gh api -i --method GET /rate_limit`` and parses the HTTP
    response into status code, headers dict, and body string.

    :return: Tuple of ``(status_code, headers, body)``.
    :raises RuntimeError: If the API returns a 4xx/5xx status.
    """
    proc = _run_process(
        ["gh", "api", "-i", "--method", "GET", "/rate_limit"],
        capture_output=True,
        encoding="UTF-8",
    )
    stdout = proc.stdout or ""

    # Parse the HTTP response: status line, headers, then body after blank
    # line.
    lines = stdout.splitlines()
    status_line = lines[0] if lines else ""
    headers: dict[str, str] = {}
    body_start = len(lines)
    for i, line in enumerate(lines[1:], start=1):
        if not line.strip():
            body_start = i + 1
            break
        if ":" in line:
            key, _, value = line.partition(":")
            headers[key.strip().lower()] = value.strip()
    body = "\n".join(lines[body_start:])

    # Extract HTTP status code.
    status_code = 0
    parts = status_line.split()
    if len(parts) >= 2:
        try:
            status_code = int(parts[1])
        except ValueError:
            pass

    if status_code >= 400:
        message = ""
        try:
            message = json.loads(body).get("message", "")
        except (json.JSONDecodeError, AttributeError):
            pass
        detail = f"GitHub API returned an error ({status_line})."
        if message:
            detail += f" GitHub says: {message}"
        raise RuntimeError(detail)

    return status_code, headers, body


def validate_classic_pat_scope(required_scope: str) -> list[str]:
    """Validate that ``GH_TOKEN`` is a classic PAT with the required scope.

    Checks:

    1. ``GH_TOKEN`` environment variable is set.
    2. GitHub API is reachable (smoke-test GET).
    3. Token is a classic PAT (has ``X-OAuth-Scopes`` header).
    4. Token has the required scope.

    :param required_scope: The OAuth scope to require
        (e.g. ``"notifications"``).
    :return: The full list of scopes on the token.
    :raises RuntimeError: If any check fails.
    """
    validate_gh_token_env()
    _status_code, headers, _body = validate_gh_api_access()

    scopes_header = headers.get("x-oauth-scopes")
    if scopes_header is None:
        msg = (
            "No X-OAuth-Scopes header found."
            " GH_TOKEN must be a classic PAT"
            " (fine-grained PATs are not supported)."
        )
        raise RuntimeError(msg)

    scope_list = [s.strip() for s in scopes_header.split(",") if s.strip()]
    if required_scope not in scope_list:
        msg = (
            f"Token scopes: '{scopes_header}'."
            f" The '{required_scope}' scope is required."
        )
        raise RuntimeError(msg)

    logging.info("Token validated: scopes='%s'.", scopes_header)
    return scope_list
