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

from __future__ import annotations

import logging
import os
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from click_extra import (
    Choice,
    Context,
    argument,
    extra_group,
    file_path,
    option,
    pass_context,
    path,
)

from . import __version__
from .changelog import Changelog
from .mailmap import Mailmap
from .metadata import Dialects, Metadata


def is_stdout(filepath):
    return str(filepath) == "-"


@contextmanager
def file_writer(filepath):
    """A context-aware file writer which default to stdout if no path is
    provided."""
    if is_stdout(filepath):
        yield sys.stdout
    else:
        writer = filepath.open("w")
        yield writer
        writer.close()


def get_header(ctx: Context):
    """Generates metadata to be leaved as comments to the top of a file generated by this CLI."""
    return (
        f"# Generated by {ctx.command_path} v{__version__}"
        " - https://github.com/kdeldycke/workflows\n"
        f"# Timestamp: {datetime.now().isoformat()}.\n\n"
    )


@extra_group
def gha_utils():
    pass


@gha_utils.command(short_help="Output project metadata")
@option(
    "--format",
    type=Choice(tuple(item.value for item in Dialects), case_sensitive=False),
    default="github",
    help="Rendering format of the metadata.",
)
@option(
    "--overwrite",
    "--force",
    "--replace",
    is_flag=True,
    default=False,
    help="Allow output target file to be silently wiped out if it already exists.",
)
@argument(
    "output_path",
    type=file_path(writable=True, resolve_path=True, allow_dash=True),
    default="-",
)
@pass_context
def metadata(ctx, format, overwrite, output_path):
    """Dump project metadata to a file.

    By default the metadata produced are displayed directly to the console output.
    So `gha-utils metadata` is the same as a call to `gha-utils metadata -`. To have the results written
    in a file on disk, specify the output file like so: `gha-utils metadata dump.txt`.

    For GitHub you want to output to the standard environment file pointed to by the `$GITHUB_OUTPUT` variable. I.e.:

        $ gha-utils metadata --format github "$GITHUB_OUTPUT"
    """
    if is_stdout(output_path):
        if overwrite:
            logging.warning("Ignore the --overwrite/--force/--replace option.")
        logging.info(f"Print metadata to {sys.stdout.name}")
    else:
        logging.info(f"Dump all metadata to {output_path}")

        if output_path.exists():
            msg = "Target file exist and will be overwritten."
            if overwrite:
                logging.warning(msg)
            else:
                logging.critical(msg)
                ctx.exit(2)

    metadata = Metadata()

    # Output a warning in GitHub runners if metadata are not saved to $GITHUB_OUTPUT.
    if metadata.in_ci_env:
        env_file = os.getenv("GITHUB_OUTPUT")
        if env_file and Path(env_file) != output_path:
            logging.warning(
                "Output path is not the same as $GITHUB_OUTPUT environment variable,"
                " which is generally what we're looking to do in GitHub CI runners for"
                " other jobs to consume the produced metadata."
            )

    dialect = Dialects(format)
    content = metadata.dump(dialect=dialect)

    with file_writer(output_path) as f:
        f.write(f"{get_header(ctx)}{content}")


@gha_utils.command(short_help="Maintain a Markdown-formatted changelog")
@option(
    "--source",
    type=path(exists=True, readable=True, resolve_path=True),
    default="changelog.md",
    help="Changelog source file in Markdown format.",
)
@argument(
    "changelog_path",
    type=file_path(writable=True, resolve_path=True, allow_dash=True),
    default="-",
)
@pass_context
def changelog(ctx, source, changelog_path):
    initial_content = None
    if source:
        logging.info(f"Read initial changelog from {source}")
        initial_content = source.read_text()

    changelog = Changelog(initial_content)
    content = changelog.update()

    if is_stdout(changelog_path):
        logging.info(f"Print updated results to {sys.stdout.name}")
    else:
        logging.info(f"Save updated results to {changelog_path}")

    with file_writer(changelog_path) as f:
        f.write(content)


@gha_utils.command(short_help="Sync Git's .mailmap at project's root")
@option(
    "--source",
    type=path(exists=True, readable=True, resolve_path=True),
    default=".mailmap",
    help=".mailmap source file to be updated with missing contributors.",
)
@argument(
    "updated_mailmap",
    type=file_path(writable=True, resolve_path=True, allow_dash=True),
    default="-",
)
@pass_context
def mailmap(ctx, source, updated_mailmap):
    """Update a ``.mailmap`` file with missing contributors found in Git commit history.

    By default the existing .mailmap is read to be used as initial mapping. To which missing contributors are added.
    Then the results are printed to the console output. So `gha-utils mailmap` is the same as a call to `gha-utils mailmap --source .mailmap -`.

    To have the updated results written
    to a file on disk, specify the output file like so: `gha-utils mailmap .mailmap`.

    The updated results are quite dumb, so it is advised to identify potential duplicate identities,
    then regroup them by hand.
    """
    initial_content = None
    if source:
        logging.info(f"Read initial mapping from {source}")
        initial_content = source.read_text()

    mailmap = Mailmap(initial_content)
    content = mailmap.updated_map()

    if is_stdout(updated_mailmap):
        logging.info(f"Print updated results to {sys.stdout.name}")
    else:
        logging.info(f"Save updated results to {updated_mailmap}")

    with file_writer(updated_mailmap) as f:
        f.write(f"{get_header(ctx)}{content}")
