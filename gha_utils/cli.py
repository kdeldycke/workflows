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
from datetime import datetime
from pathlib import Path

from click_extra import (
    Choice,
    Context,
    argument,
    echo,
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


def is_stdout(filepath: Path) -> bool:
    return str(filepath) == "-"


def handle_stdout(filepath: Path) -> Path | None:
    if is_stdout(filepath):
        return None
    return filepath


def generate_header(ctx: Context) -> str:
    """Generate metadata to be left as comments to the top of a file generated by
    this CLI.
    """
    header = (
        f"# Generated by {ctx.command_path} v{__version__}"
        " - https://github.com/kdeldycke/workflows\n"
        f"# Timestamp: {datetime.now().isoformat()}\n"
    )
    logging.debug(f"Generated header:\n{header}")
    return header


def remove_header(content: str) -> str:
    """Return the same content provided, but without the blank lines and header metadata generated by the function above."""
    logging.debug(f"Removing header from:\n{content}")
    lines = []
    still_in_header = True
    for line in content.splitlines():
        if still_in_header:
            # We are still in the header as long as we have blank lines or we have
            # comment lines matching the format produced by the method above.
            if not line.strip() or line.startswith(
                (
                    "# Generated by ",
                    "# Timestamp: ",
                )
            ):
                continue
            else:
                still_in_header = False
        # We are past the header, so keep all the lines: we have nothing left to remove.
        lines.append(line)

    headerless_content = "\n".join(lines)
    logging.debug(f"Result of header removal:\n{headerless_content}")
    return headerless_content


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
    So `gha-utils metadata` is the same as a call to `gha-utils metadata -`. To have
    the results written in a file on disk, specify the output file like so:
    `gha-utils metadata dump.txt`.

    For GitHub you want to output to the standard environment file pointed to by the
    `$GITHUB_OUTPUT` variable. I.e.:

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
    echo(content, file=handle_stdout(output_path))


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
        initial_content = source.read_text(encoding="UTF-8")

    changelog = Changelog(initial_content)
    content = changelog.update()
    if not content:
        logging.warning("Changelog already up to date. Do nothing.")
        ctx.exit()

    if is_stdout(changelog_path):
        logging.info(f"Print updated results to {sys.stdout.name}")
    else:
        logging.info(f"Save updated results to {changelog_path}")
    echo(content, file=handle_stdout(changelog_path))


@gha_utils.command(short_help="Update Git's .mailmap file with missing contributors")
@option(
    "--source",
    type=file_path(readable=True, resolve_path=True),
    default=".mailmap",
    help="Mailmap source file to use as reference for contributors identities that "
    "are already grouped.",
)
@option(
    "--create-if-missing/--skip-if-missing",
    is_flag=True,
    default=True,
    help="Create the destination mailmap file if it is not found. Or skip the update "
    "process entirely if if does not already exists in the first place. This option "
    f"is ignore if the destination is to print the result to {sys.stdout.name}.",
)
@argument(
    "destination_mailmap",
    type=file_path(writable=True, resolve_path=True, allow_dash=True),
    default="-",
)
@pass_context
def mailmap_sync(ctx, source, create_if_missing, destination_mailmap):
    """Update a ``.mailmap`` file with all missing contributors found in Git commit
    history.

    By default the ``.mailmap`` at the root of the repository is read and its content
    is reused as reference, so identities already aliased in there are preserved and
    used as initial mapping. Only missing contributors not found in this initial mapping
    are added.

    The resulting updated mapping is printed to the console output. So a bare call to
    `gha-utils mailmap-sync` is the same as a call to
    `gha-utils mailmap-sync --source .mailmap -`.

    To have the updated mapping written to a file, specify the output file like so:
    `gha-utils mailmap-sync .mailmap`.

    The updated results are sorted. But no attempts are made at regrouping new
    contributors. SO you have to edit entries by hand to regroup them
    """
    mailmap = Mailmap()

    if source.exists():
        logging.info(f"Read initial mapping from {source}")
        content = remove_header(source.read_text(encoding="UTF-8"))
        mailmap.parse(content)
    else:
        logging.debug(f"Mailmap source file {source} does not exists.")

    mailmap.update_from_git()
    new_content = mailmap.render()

    if is_stdout(destination_mailmap):
        logging.info(f"Print updated results to {sys.stdout.name}.")
        logging.debug(
            "Ignore the "
            + ("--create-if-missing" if create_if_missing else "--skip-if-missing")
            + " option."
        )
    else:
        logging.info(f"Save updated results to {destination_mailmap}")
        if not create_if_missing and not destination_mailmap.exists():
            logging.warning(
                f"{destination_mailmap} does not exists, stop the sync process."
            )
            ctx.exit()
        if content == new_content:
            logging.warning("Nothing to update, stop the sync process.")
            ctx.exit()

    echo(generate_header(ctx) + new_content, file=handle_stdout(destination_mailmap))
