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

"""Unified tool runner with managed config resolution.

Provides ``repomatic run <tool>`` — a single entry point that installs an
external tool at a pinned version, resolves its configuration through a strict
4-level precedence chain, translates ``[tool.X]`` sections from
``pyproject.toml`` into the tool's native format, and invokes the tool with
the resolved config.

.. note::
    Config resolution precedence (first match wins, no merging):

    1. **Native config file** — tool's own config file in the repo.
    2. **``[tool.X]`` in ``pyproject.toml``** — translated to native format.
    3. **Bundled default** — from ``repomatic/data/``.
    4. **Bare invocation** — no config at all.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from importlib.resources import as_file, files
from pathlib import Path

import yaml
from extra_platforms import is_github_ci

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]

TYPE_CHECKING = False
if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence
    from typing import Any

    from .metadata import Metadata


@dataclass(frozen=True)
class ToolSpec:
    """Specification for an external tool managed by repomatic."""

    name: str
    """CLI name: ``repomatic run <name>``."""

    version: str
    """Pinned version (e.g., ``'1.38.0'``)."""

    package: str
    """PyPI package name (e.g., ``'yamllint'``). May differ from ``name``."""

    executable: str | None = None
    """Executable name if different from ``name``. ``None`` defaults to ``name``."""

    native_config_files: tuple[str, ...] = ()
    """Config filenames the tool auto-discovers, checked in order.

    Paths relative to repo root (e.g., ``'zizmor.yaml'``,
    ``'.github/actionlint.yaml'``). Empty for tools with no config file.
    """

    config_flag: str | None = None
    """CLI flag to pass a config file path (e.g., ``'--config'``,
    ``'--config-file'``). ``None`` if the tool only reads from fixed paths.
    """

    native_format: str = "yaml"
    """Target format for ``[tool.X]`` translation: ``'yaml'``, ``'toml'``,
    ``'json'``, ``'jsonc'``, ``'cli-flags'``.
    """

    default_config: str | None = None
    """Filename in ``repomatic/data/`` for bundled defaults, stored in
    ``native_format``. ``None`` if no bundled default exists.
    """

    reads_pyproject: bool = False
    """Whether the tool natively reads ``[tool.X]`` from ``pyproject.toml``.

    When ``True``, repomatic skips config resolution entirely — the tool
    handles its own config.
    """

    default_flags: tuple[str, ...] = ()
    """Flags always passed to the tool (e.g., ``('--strict',)``)."""

    ci_flags: tuple[str, ...] = ()
    """Flags added only when ``$GITHUB_ACTIONS`` is set (e.g., output format)."""

    with_packages: tuple[str, ...] = ()
    """Extra packages installed alongside the tool (e.g., mdformat plugins).

    Passed as ``--with <pkg>`` to uvx.
    """

    needs_venv: bool = False
    """If ``True``, use ``uv run`` (project venv) instead of ``uvx`` (isolated).

    Required when the tool imports project code (mypy, pytest).
    """

    computed_params: Callable[[Metadata], list[str]] | None = None
    """Callable that receives a ``Metadata`` instance and returns extra CLI args
    derived from project metadata (e.g., mypy's ``--python-version`` from
    ``requires-python``). ``None`` if no computed params.
    """


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, ToolSpec] = {
    # autopep8 configuration reference:
    # - CLI flags: https://pypi.org/project/autopep8/
    #   No config file support; all options via CLI flags.
    # - Source: https://github.com/hhatto/autopep8
    "autopep8": ToolSpec(
        name="autopep8",
        version="2.3.2",
        package="autopep8",
        default_flags=(
            "--recursive",
            "--in-place",
            "--max-line-length",
            "88",
            "--select",
            "E501",
            "--aggressive",
        ),
    ),
    # mdformat configuration reference:
    # - Config discovery: https://mdformat.readthedocs.io/en/stable/users/configuration_file.html
    #   Searches .mdformat.toml in CWD and parents.
    # - CLI flags: https://mdformat.readthedocs.io/en/stable/users/cli.html
    #   --number for ordered list numbering; --strict-front-matter for YAML
    #   front matter validation.
    # - Source: https://github.com/hukkin/mdformat
    "mdformat": ToolSpec(
        name="mdformat",
        version="1.0.0",
        package="mdformat",
        native_config_files=(".mdformat.toml",),
        native_format="toml",
        default_flags=("--number", "--strict-front-matter"),
        with_packages=(
            "mdformat_admon==2.1.1",
            "mdformat-config==0.2.1",
            "mdformat_deflist==0.1.4",
            "mdformat_footnote==0.1.3",
            "mdformat-front-matters==2.0.0",
            "mdformat-gfm==1.0.0",
            "mdformat_gfm_alerts==2.0.0",
            "mdformat_myst==0.3.0",
            "mdformat-pelican @ git+https://github.com/kdeldycke/mdformat-pelican@fix-mdformat-1.0.0",
            "mdformat_pyproject==0.1.1",
            "mdformat-recover-urls==0.0.2",
            "mdformat-ruff==0.1.3",
            "mdformat-shfmt==0.2.0",
            "mdformat_simple_breaks==0.1.0",
            "mdformat-toc==0.5.0",
            "mdformat-web==0.2.0",
            "ruff==0.15.5",
        ),
    ),
    # mypy configuration reference:
    # - Config discovery: https://mypy.readthedocs.io/en/stable/config_file.html
    #   Reads [tool.mypy] from pyproject.toml natively.
    # - CLI flags: https://mypy.readthedocs.io/en/stable/command_line.html
    #   --python-version for target version; --color-output for colored output.
    # - Source: https://github.com/python/mypy
    "mypy": ToolSpec(
        name="mypy",
        version="1.19.1",
        package="mypy",
        reads_pyproject=True,
        needs_venv=True,
        default_flags=("--color-output",),
        computed_params=lambda m: m.mypy_params or [],
    ),
    # pyproject-fmt configuration reference:
    # - CLI flags: https://pyproject-fmt.readthedocs.io/en/latest/
    #   --expand-tables for table expansion. Returns exit code 1 when file is
    #   reformatted.
    # - Source: https://github.com/tox-dev/pyproject-fmt
    "pyproject-fmt": ToolSpec(
        name="pyproject-fmt",
        version="2.16.2",
        package="pyproject-fmt",
        default_flags=(
            "--expand-tables",
            "project.entry-points,project.optional-dependencies,project.urls,project.scripts",
        ),
    ),
    # yamllint configuration reference:
    # - Config discovery: https://yamllint.readthedocs.io/en/stable/configuration.html
    #   Searches .yamllint, .yamllint.yaml, .yamllint.yml in CWD and parents.
    # - CLI flags: https://yamllint.readthedocs.io/en/stable/quickstart.html
    #   -c / --config-file for explicit config; -f / --format for output format.
    # - Source: https://github.com/adrienverge/yamllint
    "yamllint": ToolSpec(
        name="yamllint",
        version="1.38.0",
        package="yamllint",
        native_config_files=(
            ".yamllint.yaml",
            ".yamllint.yml",
            ".yamllint",
        ),
        config_flag="--config-file",
        native_format="yaml",
        default_config="yamllint.yaml",
        default_flags=("--strict",),
        ci_flags=("--format", "github"),
    ),
    # zizmor configuration reference:
    # - Config discovery: https://docs.zizmor.sh/configuration/
    #   Searches zizmor.yml / zizmor.yaml in input dir, .github/, then parents
    #   up to first .git directory.
    # - CLI flags: https://docs.zizmor.sh/usage/
    #   --config for explicit config; --format for output format; --offline to
    #   disable network requests.
    # - Source: https://github.com/zizmorcore/zizmor
    "zizmor": ToolSpec(
        name="zizmor",
        version="1.23.0",
        package="zizmor",
        native_config_files=("zizmor.yaml",),
        config_flag="--config",
        native_format="yaml",
        default_config="zizmor.yaml",
        default_flags=("--offline",),
        ci_flags=("--format", "github"),
    ),
}


# ---------------------------------------------------------------------------
# Bundled data file access
# ---------------------------------------------------------------------------


@contextmanager
def get_data_file_path(filename: str) -> Iterator[Path]:
    """Yield the filesystem path of a bundled data file.

    Unlike ``init_project.get_data_content()`` which returns string content,
    this yields a ``Path`` suitable for passing to external tools via
    ``--config <path>``. The path is valid only within the context manager.
    """
    data_files = files("repomatic.data")
    with as_file(data_files.joinpath(filename)) as path:
        if not path.exists():
            msg = f"Bundled data file not found: {filename}"
            raise FileNotFoundError(msg)
        yield path


# ---------------------------------------------------------------------------
# Config resolution
# ---------------------------------------------------------------------------


def load_pyproject_tool_section(tool_name: str) -> dict[str, Any]:
    """Load ``[tool.<tool_name>]`` from ``pyproject.toml`` in the current directory.

    :return: The tool's config dict, or empty dict if not found.
    """
    pyproject_path = Path("pyproject.toml")
    if not pyproject_path.exists():
        return {}
    pyproject_data = tomllib.loads(pyproject_path.read_text(encoding="UTF-8"))
    tool_section: dict[str, Any] = pyproject_data.get("tool", {}).get(tool_name, {})
    return tool_section


def resolve_config(
    spec: ToolSpec,
    tool_config: dict[str, Any] | None = None,
) -> tuple[list[str], Path | None]:
    """Resolve config for a tool using the 4-level precedence chain.

    :param spec: Tool specification.
    :param tool_config: Pre-loaded ``[tool.X]`` config dict. If ``None``,
        reads from ``pyproject.toml`` in the current directory.
    :return: Tuple of (extra CLI args for config, temp file path to clean up).
        The temp file path is ``None`` when no temp file was created.
    """
    # Tools that read pyproject.toml natively need no config resolution.
    if spec.reads_pyproject:
        logging.debug("%s reads pyproject.toml natively. Skipping resolution.", spec.name)
        return [], None

    # Level 1: Native config file exists in the repo.
    for config_file in spec.native_config_files:
        if Path(config_file).exists():
            logging.debug("Using native config: %s", config_file)
            return [], None

    # Level 2: [tool.X] in pyproject.toml.
    if tool_config is None:
        tool_config = load_pyproject_tool_section(spec.name)

    if tool_config:
        if spec.native_format == "yaml":
            content = yaml.safe_dump(
                tool_config, default_flow_style=False, sort_keys=False
            )
        else:
            msg = f"Unsupported native format for translation: {spec.native_format}"
            raise ValueError(msg)

        logging.debug(
            "Translated [tool.%s] to %s:\n%s",
            spec.name,
            spec.native_format,
            content,
        )

        # Write to temp file. Caller is responsible for cleanup via the
        # returned path.
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=f".{spec.native_format}",
            prefix=f"repomatic-{spec.name}-",
            delete=False,
        ) as tmp:
            tmp.write(content)
        tmp_path = Path(tmp.name)
        logging.debug("Wrote temp config: %s", tmp_path)

        if spec.config_flag:
            return [spec.config_flag, str(tmp_path)], tmp_path
        return [], tmp_path

    # Level 3: Bundled default from repomatic/data/.
    if spec.default_config and spec.config_flag:
        logging.debug("Using bundled default: %s", spec.default_config)
        # Return a sentinel; the actual path is resolved at invocation time
        # inside the get_data_file_path() context manager.
        return ["__bundled__"], None

    # Level 4: Bare invocation.
    logging.debug("No config found for %s, bare invocation.", spec.name)
    return [], None


# ---------------------------------------------------------------------------
# Tool invocation
# ---------------------------------------------------------------------------


def _build_install_args(spec: ToolSpec) -> list[str]:
    """Build the command prefix for installing and running a tool."""
    package_pin = f"{spec.package}=={spec.version}"
    executable = spec.executable or spec.name

    if spec.needs_venv:
        cmd = [
            "uv",
            "--no-progress",
            "run",
            "--frozen",
            "--with",
            package_pin,
            "--",
            executable,
        ]
    else:
        cmd = ["uvx", "--no-progress"]
        for pkg in spec.with_packages:
            cmd.extend(["--with", pkg])
        cmd.extend(["--from", package_pin, executable])

    return cmd


def run_tool(
    name: str,
    extra_args: Sequence[str] = (),
) -> int:
    """Run an external tool with managed config resolution.

    :param name: Tool name (must be in ``TOOL_REGISTRY``).
    :param extra_args: Extra arguments passed through to the tool.
    :return: The tool's exit code.
    """
    if name not in TOOL_REGISTRY:
        msg = (
            f"Unknown tool: {name!r}. "
            f"Available tools: {', '.join(sorted(TOOL_REGISTRY))}"
        )
        raise ValueError(msg)

    spec = TOOL_REGISTRY[name]
    config_args, tmp_path = resolve_config(spec)

    try:
        cmd = _build_install_args(spec)

        # Default flags (always applied).
        if spec.default_flags:
            cmd.extend(spec.default_flags)

        # CI output format flags.
        if spec.ci_flags and is_github_ci():
            cmd.extend(spec.ci_flags)

        # Computed parameters derived from project metadata.
        if spec.computed_params:
            from .metadata import Metadata

            cmd.extend(spec.computed_params(Metadata()))

        # Config args from resolution.
        if config_args == ["__bundled__"]:
            # Level 3: use bundled default via context manager.
            # Both are guaranteed non-None when __bundled__ is returned.
            assert spec.default_config is not None
            assert spec.config_flag is not None
            with get_data_file_path(spec.default_config) as bundled_path:
                cmd.extend([spec.config_flag, str(bundled_path)])
                cmd.extend(extra_args)
                logging.debug("Running: %s", " ".join(cmd))
                result = subprocess.run(cmd, check=False)
            return result.returncode
        else:
            cmd.extend(config_args)

        cmd.extend(extra_args)
        logging.debug("Running: %s", " ".join(cmd))
        result = subprocess.run(cmd, check=False)
        return result.returncode

    finally:
        if tmp_path is not None:
            logging.debug("Cleaning up temp config: %s", tmp_path)
            tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------


def resolve_config_source(spec: ToolSpec) -> str:
    """Return a human-readable description of the active config source.

    Used by ``repomatic run --list`` to show which precedence level is active
    for each tool in the current repo.
    """
    if spec.reads_pyproject:
        pyproject_path = Path("pyproject.toml")
        if pyproject_path.exists():
            data = tomllib.loads(pyproject_path.read_text(encoding="UTF-8"))
            if data.get("tool", {}).get(spec.name):
                return f"[tool.{spec.name}] in pyproject.toml"
        return "(bare)"

    for config_file in spec.native_config_files:
        if Path(config_file).exists():
            return config_file

    tool_config = load_pyproject_tool_section(spec.name)
    if tool_config:
        return f"[tool.{spec.name}] in pyproject.toml"

    if spec.default_config:
        return "bundled default"

    return "(bare)"
