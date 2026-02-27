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

Provides early validation for CLI commands that depend on the GitHub API,
so users get clear error messages at startup rather than opaque failures
mid-execution.

.. note:: Why ``WORKFLOW_UPDATE_GITHUB_PAT`` is needed

   GitHub's ``GITHUB_TOKEN`` cannot modify workflow files in ``.github/``.
   Neither ``contents: write``, ``actions: write``, nor ``permissions:
   write-all`` grant this ability. The only way to push changes to workflow
   YAML files is via a fine-grained Personal Access Token with the
   **Workflows** permission. Without it, pushes are rejected with::

       ! [remote rejected] branch_xxx -> branch_xxx (refusing to allow a
       GitHub App to create or update workflow
       `.github/workflows/my_workflow.yaml` without `workflows` permission)

   Additionally, events triggered by ``GITHUB_TOKEN`` do not start new
   workflow runs (see `GitHub docs
   <https://docs.github.com/en/actions/security-guides/automatic-token-authentication#using-the-github_token-in-a-workflow>`_),
   so tag pushes also need the PAT to trigger downstream workflows.

   The **Settings → Actions → General → Workflow permissions** setting has
   no effect on this limitation — it's a hard security boundary enforced by
   GitHub regardless of repository-level settings.

   Jobs that use ``WORKFLOW_UPDATE_GITHUB_PAT``:

   - ``autofix.yaml``: fix-typos, sync-workflows, sync-awesome-template
     (PRs touching ``.github/workflows/`` files).
   - ``changelog.yaml``: prepare-release (freezes versions in workflow files).
   - ``release.yaml``: create-tag (push triggers ``on.push.tags``),
     create-release (triggers downstream workflows).
   - ``renovate.yaml``: renovate (dependency PRs, status checks, dashboard,
     vulnerability alerts).

   All jobs fall back to ``GITHUB_TOKEN`` when the PAT is unavailable
   (``secrets.WORKFLOW_UPDATE_GITHUB_PAT || secrets.GITHUB_TOKEN``), but
   operations requiring the ``workflows`` permission or workflow triggering
   will silently fail.

   Token permission mapping:

   - **Workflows** — PRs that touch ``.github/workflows/`` files.
   - **Contents** — Tag pushes, release publishing, PR branch creation.
   - **Pull requests** — All PR-creating jobs.
   - **Commit statuses** — Renovate ``stability-days`` status checks.
   - **Dependabot alerts** — Renovate vulnerability alert reading.
   - **Issues** — Renovate Dependency Dashboard.
   - **Metadata** — Required for all fine-grained token API operations.
"""

from __future__ import annotations

import json
import logging
import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def validate_gh_token_env() -> None:
    """Check that a GitHub token environment variable is set.

    The ``gh`` CLI accepts authentication via ``GH_TOKEN`` (highest
    priority) or ``GITHUB_TOKEN``.  This function checks both, matching
    the CLI's own lookup order.

    :raises RuntimeError: If neither variable is set.
    """
    if not (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")):
        msg = (
            "No GitHub token found. "
            "Set GH_TOKEN or GITHUB_TOKEN to a personal access token. "
            "Create one at https://github.com/settings/tokens"
        )
        raise RuntimeError(msg)


def _get_gh_token() -> str:
    """Return the GitHub token from environment variables.

    Uses the same lookup order as :func:`validate_gh_token_env`: ``GH_TOKEN``
    first, then ``GITHUB_TOKEN``.
    """
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""


def validate_gh_api_access() -> tuple[int, dict[str, str], str]:
    """Smoke-test the GitHub API and return parsed response.

    Calls ``GET https://api.github.com/rate_limit`` with the token from
    environment variables.

    :return: Tuple of ``(status_code, headers, body)``.
    :raises RuntimeError: If the API returns a 4xx/5xx status.
    """
    request = Request("https://api.github.com/rate_limit")
    token = _get_gh_token()
    if token:
        request.add_header("Authorization", f"token {token}")

    try:
        response = urlopen(request)  # noqa: S310
    except HTTPError as exc:
        message = ""
        try:
            message = json.loads(exc.read().decode()).get("message", "")
        except (json.JSONDecodeError, AttributeError):
            pass
        detail = f"GitHub API returned an error ({exc.code})."
        if message:
            detail += f" GitHub says: {message}"
        raise RuntimeError(detail) from exc

    body = response.read().decode()
    headers = {k.lower(): v for k, v in response.headers.items()}
    return response.status, headers, body


def validate_classic_pat_scope(required_scope: str) -> list[str]:
    """Validate that the GitHub token is a classic PAT with the required scope.

    Checks:

    1. A GitHub token environment variable is set.
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
            " The token must be a classic PAT"
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
