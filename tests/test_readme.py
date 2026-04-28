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

"""Tests for documentation sync with code."""

from __future__ import annotations

import re
from pathlib import Path

from click.testing import CliRunner

from repomatic.cli import repomatic
from repomatic.tool_runner import TOOL_REGISTRY, NativeFormat

REPO_ROOT = Path(__file__).parent.parent
CLI_MD = REPO_ROOT / "docs" / "cli.md"
CONFIGURATION_MD = REPO_ROOT / "docs" / "configuration.md"
TOOL_RUNNER_MD = REPO_ROOT / "docs" / "tool-runner.md"


def _parse_tool_runner_table() -> dict[str, str]:
    """Parse the combined tool table in docs/tool-runner.md.

    Returns a dict mapping display name to support column content,
    for rows that list either 'repomatic bridge' or 'Native' support.
    """
    tool_runner_text = TOOL_RUNNER_MD.read_text(encoding="UTF-8")
    result = {}
    for line in tool_runner_text.splitlines():
        if not line.startswith("| "):
            continue
        cols = [c.strip() for c in line.split("|")]
        if len(cols) < 5:
            continue
        tool_col = cols[1]
        support_col = cols[4]
        if "repomatic bridge" not in support_col and "Native" not in support_col:
            continue
        m = re.match(r"\[([^\]]+)\]", tool_col)
        if m:
            result[m.group(1)] = support_col
    return result


def test_docs_cli_reference_covers_all_commands() -> None:
    """Every command must have a ``{click:run}`` directive in docs/cli.md.

    Help text is rendered live by ``click_extra.sphinx`` at build time, so we
    only check that each command path has a directive block invoking it.
    """
    cli_text = CLI_MD.read_text(encoding="UTF-8")
    paths: list[list[str]] = [["--help"]]
    for name, cmd in repomatic.commands.items():
        paths.append([name, "--help"])
        if hasattr(cmd, "commands"):
            paths.extend([name, sub, "--help"] for sub in cmd.commands)
    for path in paths:
        args_repr = ", ".join(repr(a) for a in path)
        invocation = f"invoke(repomatic, args=[{args_repr}])"
        assert invocation in cli_text, (
            f"Missing {{click:run}} block for `{path}` in docs/cli.md. "
            "Re-run: repomatic update-docs"
        )


def test_docs_config_table_matches() -> None:
    """All show-config options must be documented in docs/configuration.md."""
    runner = CliRunner()
    result = runner.invoke(
        repomatic, ["--no-color", "--table-format", "github", "show-config"]
    )
    assert result.exit_code == 0
    assert result.output, "No output from `repomatic show-config`"
    config_text = CONFIGURATION_MD.read_text(encoding="UTF-8")
    # Extract option names from lines like: | `option-name` | type | default |
    option_re = re.compile(r"^\|\s*`([^`]+)`\s*\|", re.MULTILINE)
    options = {m.group(1) for m in option_re.finditer(result.output)}
    assert options, "No options found in show-config output"
    missing = {opt for opt in options if f"`{opt}`" not in config_text}
    assert not missing, (
        f"Options from show-config missing from docs/configuration.md: "
        f"{sorted(missing)}. Re-run: repomatic update-docs"
    )


def test_docs_bridge_table_covers_registry() -> None:
    """The tool-runner.md table must list every registry tool that supports translation.

    A tool supports ``[tool.X]`` translation when it does not natively read
    ``pyproject.toml`` (``reads_pyproject=False``) and can receive a translated
    config via either a ``config_flag`` or ``native_config_files`` in a
    non-editorconfig format (editorconfig files are shared across tools and
    not suitable as single-tool bridge targets).
    """
    tool_table = _parse_tool_runner_table()
    documented = {
        name for name, support in tool_table.items() if "repomatic bridge" in support
    }

    bridgeable = {
        name
        for name, spec in TOOL_REGISTRY.items()
        if not spec.reads_pyproject
        and (
            spec.config_flag
            or (
                spec.native_config_files
                and spec.native_format is not NativeFormat.EDITORCONFIG
            )
        )
    }

    missing = bridgeable - documented
    assert not missing, (
        f"Tools with [tool.X] bridge support missing from tool-runner.md table: "
        f"{sorted(missing)}. Add them to the tool table in docs/tool-runner.md."
    )

    extra = documented - bridgeable
    assert not extra, (
        f"Tools listed in tool-runner.md bridge rows but not bridgeable in registry: "
        f"{sorted(extra)}. Remove them or update the registry."
    )


def test_docs_tip_table_covers_registry() -> None:
    """The tool-runner.md table must list every registry tool that natively reads pyproject.toml.

    Tools with ``reads_pyproject=True`` in the registry should appear in the
    tool table with 'Native' support. The table may also list non-registry tools
    (like coverage.py, pytest, uv) that the workflows use and that natively
    read ``[tool.*]`` sections.
    """
    tool_table = _parse_tool_runner_table()
    documented = {name for name, support in tool_table.items() if "Native" in support}

    native_readers = {
        name for name, spec in TOOL_REGISTRY.items() if spec.reads_pyproject
    }

    # Registry tool names may differ from display names (e.g., "bump-my-version"
    # is the package name while the registry key is also "bump-my-version"). Map
    # registry names to the display names used in the table.
    display_names = {
        TOOL_REGISTRY[name].package or TOOL_REGISTRY[name].name
        for name in native_readers
    }

    missing = display_names - documented
    assert not missing, (
        f"Tools with reads_pyproject=True missing from tool-runner.md table: "
        f"{sorted(missing)}. Add them to the tool table in docs/tool-runner.md."
    )
