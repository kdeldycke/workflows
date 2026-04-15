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

from pathlib import Path

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


def config_deflist() -> str:
    """Render the config reference as a MyST definition list."""
    lines = []
    for option, ftype, default, description in config_reference():
        lines.append(option)
        lines.append(f": **Type:** {ftype} | **Default:** {default}")
        lines.append("")
        lines.append(f"  {description}")
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


if __name__ == "__main__":
    update_configuration()
