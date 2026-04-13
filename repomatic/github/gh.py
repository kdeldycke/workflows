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

"""Generic wrapper for the ``gh`` CLI.

.. note::

    Token resolution is centralized here so that workflow YAML only needs to
    pass ``REPOMATIC_PAT`` as an env var.  :func:`run_gh_command` prefers
    ``REPOMATIC_PAT`` over ``GH_TOKEN`` over ``GITHUB_TOKEN`` (the default
    Actions token).  When the primary token returns 401 Bad Credentials
    (expired or revoked PAT), it retries with ``GITHUB_TOKEN`` automatically.
"""

from __future__ import annotations

import logging
import os
from subprocess import run


def run_gh_command(args: list[str]) -> str:
    """Run a ``gh`` CLI command and return stdout.

    Token priority: ``REPOMATIC_PAT`` > ``GH_TOKEN`` > ``GITHUB_TOKEN``.
    The ``gh`` CLI does not recognize ``REPOMATIC_PAT``, so when set it is
    injected as ``GH_TOKEN``.  On 401 Bad Credentials the command is retried
    with ``GITHUB_TOKEN`` if available and different, letting CI jobs degrade
    gracefully to the standard Actions token instead of failing outright on a
    stale PAT.

    :param args: Command arguments to pass to ``gh``.
    :return: The stdout output from the command.
    :raises RuntimeError: If the command fails (after fallback, if attempted).
    """
    cmd = ["gh", *args]
    logging.debug(f"Running: {' '.join(cmd)}")

    # Prefer REPOMATIC_PAT when set.  The gh CLI does not recognize this env
    # var, so inject it as GH_TOKEN.
    pat = os.environ.get("REPOMATIC_PAT")
    env = {**os.environ, "GH_TOKEN": pat} if pat else None
    process = run(cmd, capture_output=True, encoding="UTF-8", check=False, env=env)

    if process.returncode:
        stderr = process.stderr
        # On 401 Bad Credentials (typically from an expired or revoked PAT),
        # fall back to GITHUB_TOKEN if available and different.
        fallback = os.environ.get("GITHUB_TOKEN")
        primary = pat or os.environ.get("GH_TOKEN")
        if (
            "Bad credentials" in stderr
            and fallback
            and fallback != primary
        ):
            logging.warning(
                "Primary token returned 401 Bad Credentials, "
                "retrying with GITHUB_TOKEN.",
            )
            retry = run(
                cmd,
                capture_output=True,
                encoding="UTF-8",
                check=False,
                env={**os.environ, "GH_TOKEN": fallback},
            )
            if not retry.returncode:
                return retry.stdout
            logging.warning("GITHUB_TOKEN fallback also failed.")

        logging.debug(f"gh command failed: {stderr}")
        raise RuntimeError(stderr)

    return process.stdout
