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

"""Tests for readme.md documentation sync with code."""

from __future__ import annotations

import re
from pathlib import Path

from click.testing import CliRunner

from repomatic.cli import repomatic
from repomatic.tool_runner import TOOL_REGISTRY

REPO_ROOT = Path(__file__).parent.parent
README = REPO_ROOT / "readme.md"

# The --config default path includes a platform-specific directory
# (~/Library/Application Support/ on macOS, ~/.config/ on Linux, etc.).
# Different path lengths also cause different line-wrapping in the help output.
# Normalize the entire --config block so the README (written on macOS) matches CI.
_CONFIG_BLOCK_RE = re.compile(
    r"(--config CONFIG_PATH\s+Location of the configuration file\. Supports local\n)"
    r"\s+path with glob patterns or remote URL\.\s+\[default:\n"
    r"\s+~[^\]]+\]",
)
_CONFIG_BLOCK_PLACEHOLDER = (
    r"\1                          [default: <platform-specific>]"
)


def _readme_text() -> str:
    """Read readme.md once and cache for the module."""
    return README.read_text(encoding="UTF-8")


def _normalize_config_path(text: str) -> str:
    """Replace the platform-specific --config default block with a placeholder."""
    return _CONFIG_BLOCK_RE.sub(_CONFIG_BLOCK_PLACEHOLDER, text)


def test_readme_cli_help_matches() -> None:
    """CLI help output in readme.md must match actual ``repomatic --help``."""
    runner = CliRunner()
    result = runner.invoke(repomatic, ["--no-color", "--help"])
    assert result.exit_code == 0
    assert result.output, "No output from `repomatic --help`"
    assert _normalize_config_path(result.output) in _normalize_config_path(
        _readme_text()
    ), (
        "CLI help output in readme.md is out of sync. "
        "Re-run `repomatic --no-color --help` and paste the output."
    )


def test_readme_config_table_matches() -> None:
    """Config table in readme.md must match ``show-config`` output."""
    runner = CliRunner()
    result = runner.invoke(
        repomatic, ["--no-color", "--table-format", "github", "show-config"]
    )
    assert result.exit_code == 0
    assert result.output, "No output from `repomatic show-config`"
    assert result.output in _readme_text(), (
        "Config table in readme.md is out of sync. "
        "Re-run `repomatic --table-format github show-config` and paste the output."
    )


def test_readme_bridge_table_covers_registry() -> None:
    """The bridge table must list every registry tool that supports translation.

    A tool supports ``[tool.X]`` translation when it has a ``config_flag`` and
    does not natively read ``pyproject.toml`` (``reads_pyproject=False``).
    """
    readme = _readme_text()
    match = re.search(
        r"### `\[tool\.X\]` bridge for third-party tools.*?"
        r"\| Tool\s+\|.*?\n\| :-+.*?\n(.*?)\n\n",
        readme,
        re.DOTALL,
    )
    assert match, "Bridge table not found in readme.md"
    documented = set()
    for line in match.group(1).strip().splitlines():
        # Extract tool name from markdown link: | [name](url) |
        m = re.match(r"\|\s*\[([^\]]+)\]", line)
        if m:
            documented.add(m.group(1))

    bridgeable = {
        name
        for name, spec in TOOL_REGISTRY.items()
        if spec.config_flag and not spec.reads_pyproject
    }

    missing = bridgeable - documented
    assert not missing, (
        f"Tools with [tool.X] bridge support missing from readme bridge table: "
        f"{sorted(missing)}. Add them to the '### `[tool.X]` bridge' section."
    )

    extra = documented - bridgeable
    assert not extra, (
        f"Tools listed in readme bridge table but not bridgeable in registry: "
        f"{sorted(extra)}. Remove them or update the registry."
    )


def test_readme_tip_table_covers_registry() -> None:
    """The TIP table must list every registry tool that natively reads pyproject.toml.

    Tools with ``reads_pyproject=True`` in the registry should appear in the
    TIP admonition table. The table may also list non-registry tools (e.g.,
    coverage.py, pytest, uv) that the workflows use and that natively read
    ``[tool.*]`` sections.
    """
    readme = _readme_text()
    match = re.search(
        r"> \[!TIP\].*?"
        r"> \| Tool\s+\|.*?\n> \| :-+.*?\n(.*?)\n>\n",
        readme,
        re.DOTALL,
    )
    assert match, "TIP table not found in readme.md"
    documented = set()
    for line in match.group(1).strip().splitlines():
        # Extract tool name from: > | [name](url) |
        m = re.match(r">\s*\|\s*\[([^\]]+)\]", line)
        if m:
            documented.add(m.group(1))

    native_readers = {
        name for name, spec in TOOL_REGISTRY.items() if spec.reads_pyproject
    }

    # Registry tool names may differ from display names (e.g., "bump-my-version"
    # is displayed as "bump-my-version" in the registry but the table shows it
    # by its PyPI/branded name). Map registry names to the names used in the
    # table.
    display_names = set()
    for name in native_readers:
        spec = TOOL_REGISTRY[name]
        display_names.add(spec.package or spec.name)

    missing = display_names - documented
    assert not missing, (
        f"Tools with reads_pyproject=True missing from readme TIP table: "
        f"{sorted(missing)}. Add them to the '[tool.*] sections' TIP."
    )
