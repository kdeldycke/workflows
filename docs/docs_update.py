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
"""Dynamic documentation content generation.

Auto-detected and executed by the upstream ``docs.yaml`` reusable workflow
via ``repomatic update-docs``.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import click
from click.testing import CliRunner

from repomatic.config import config_reference

PROJECT_ROOT = Path(__file__).parent.parent.resolve()


def replace_content(
    filepath: Path,
    new_content: str,
    start_tag: str,
    end_tag: str | None = None,
) -> None:
    """Replace in a file the content between start and end tags."""
    filepath = filepath.resolve()
    assert filepath.exists(), f"File {filepath} does not exist."
    assert filepath.is_file(), f"File {filepath} is not a file."

    orig_content = filepath.read_text()

    assert start_tag in orig_content, (
        f"Start tag {start_tag!r} not found in {filepath}."
    )
    pre_content, table_start = orig_content.split(start_tag, 1)

    if end_tag:
        _, post_content = table_start.split(end_tag, 1)
    else:
        end_tag = ""
        post_content = ""

    filepath.write_text(
        f"{pre_content}{start_tag}{new_content}{end_tag}{post_content}",
    )


def _option_anchor(option: str) -> str:
    """Convert a backtick-wrapped option to an anchor ID.

    ``"`awesome-template.sync`"`` becomes ``"conf-awesome-template-sync"``.
    """
    return "conf-" + option.strip("`").replace(".", "-")


def config_deflist() -> str:
    """Render the config reference as a summary table + anchored definition list."""
    rows = config_reference()
    lines: list[str] = []

    # Quick-reference table with deep links to each definition.
    lines.append("| Option | Type | Default |")
    lines.append("| :--- | :--- | :--- |")
    for option, ftype, default, _description in rows:
        anchor = _option_anchor(option)
        bare = option.strip("`")
        lines.append(f"| [`{bare}`](#{anchor}) | {ftype} | {default} |")
    lines.append("")

    # Detailed definitions with anchor targets.
    for option, ftype, default, description in rows:
        anchor = _option_anchor(option)
        lines.append(f"({anchor})=")
        lines.append(option)
        lines.append(f": **Type:** {ftype} | **Default:** {default}")
        lines.append("")
        lines.append(f"  {description}")
        lines.append("")
    return "\n".join(lines)


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from terminal output."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _capture_help(cmd_path: list[str]) -> str:
    """Invoke a CLI command with ``--help`` and return clean output."""
    from repomatic.cli import repomatic

    runner = CliRunner()
    # Suppress color codes.
    old_val = os.environ.get("NO_COLOR")
    os.environ["NO_COLOR"] = "1"
    try:
        result = runner.invoke(repomatic, [*cmd_path, "--help"])
    finally:
        if old_val is None:
            os.environ.pop("NO_COLOR", None)
        else:
            os.environ["NO_COLOR"] = old_val
    return _strip_ansi(result.output).rstrip()


def _command_anchor(cmd_path: list[str]) -> str:
    """Build an anchor ID from a command path.

    ``["cache", "show"]`` becomes ``"cli-cache-show"``.
    """
    return "cli-" + "-".join(cmd_path)


def cli_reference() -> str:
    """Generate CLI reference with a summary table and per-command sections."""
    from repomatic.cli import repomatic

    lines: list[str] = []

    # Collect all commands (top-level + subcommands of groups).
    entries: list[tuple[list[str], click.BaseCommand]] = []
    for name in sorted(repomatic.commands):
        cmd = repomatic.commands[name]
        entries.append(([name], cmd))
        if isinstance(cmd, click.Group):
            for sub_name in sorted(cmd.commands):
                entries.append(([name, sub_name], cmd.commands[sub_name]))

    # Summary table.
    lines.append("| Command | Description |")
    lines.append("| :--- | :--- |")
    for path, cmd in entries:
        anchor = _command_anchor(path)
        label = " ".join(path)
        desc = (cmd.get_short_help_str() or "").rstrip(".")
        lines.append(f"| [`repomatic {label}`](#{anchor}) | {desc} |")
    lines.append("")

    # Main help screen.
    lines.append("## Help screen")
    lines.append("")
    lines.append("```text")
    lines.append(_capture_help([]))
    lines.append("```")
    lines.append("")

    # Per-command sections.
    for path, _cmd in entries:
        anchor = _command_anchor(path)
        label = " ".join(path)
        depth = len(path)
        heading = "#" * (depth + 1)
        lines.append(f"({anchor})=")
        lines.append(f"{heading} `repomatic {label}`")
        lines.append("")
        lines.append("```text")
        lines.append(_capture_help(path))
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def update_configuration() -> None:
    """Update ``configuration.md`` with the config reference list."""
    config_md = PROJECT_ROOT / "docs" / "configuration.md"
    replace_content(
        config_md,
        "\n" + config_deflist(),
        "<!-- config-reference-start -->",
        "<!-- config-reference-end -->",
    )


def update_cli_parameters() -> None:
    """Update ``cli-parameters.md`` with the CLI reference."""
    cli_md = PROJECT_ROOT / "docs" / "cli-parameters.md"
    replace_content(
        cli_md,
        "\n" + cli_reference(),
        "<!-- cli-reference-start -->",
        "<!-- cli-reference-end -->",
    )


if __name__ == "__main__":
    update_configuration()
    update_cli_parameters()
