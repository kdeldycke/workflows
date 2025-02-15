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

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from subprocess import SubprocessError, run
from typing import Generator, Sequence

import yaml
from boltons.iterutils import flatten
from boltons.strutils import strip_ansi
from click_extra.testing import args_cleanup, print_cli_run


@dataclass(order=True)
class TestCase:
    cli_parameters: tuple[str, ...] = field(default_factory=tuple)
    """Parameters, arguments and options to pass to the CLI."""

    exit_code: int | None = None
    strip_ansi: bool = False
    output_contains: tuple[str, ...] = field(default_factory=tuple)
    stdout_contains: tuple[str, ...] = field(default_factory=tuple)
    stderr_contains: tuple[str, ...] = field(default_factory=tuple)
    output_regex_matches: tuple[str, ...] = field(default_factory=tuple)
    stdout_regex_matches: tuple[str, ...] = field(default_factory=tuple)
    stderr_regex_matches: tuple[str, ...] = field(default_factory=tuple)
    output_regex_fullmatch: str | None = None
    stdout_regex_fullmatch: str | None = None
    stderr_regex_fullmatch: str | None = None

    def __post_init__(self) -> None:
        """Normalize all fields."""
        for field_id, field_data in asdict(self).items():
            # Validates and normalize exit code.
            if field_id == "exit_code":
                if isinstance(field_data, str):
                    field_data = int(field_data)
                elif field_data is not None and not isinstance(field_data, int):
                    raise ValueError(f"exit_code is not an integer: {field_data}")

            elif field_id == "strip_ansi":
                if not isinstance(field_data, bool):
                    raise ValueError(f"strip_ansi is not a boolean: {field_data}")

            # Validates and normalize regex fullmatch fields.
            elif field_id.endswith("_fullmatch"):
                if field_data:
                    if not isinstance(field_data, str):
                        raise ValueError(f"{field_id} is not a string: {field_data}")
                # Normalize empty strings to None.
                else:
                    field_data = None

            # Validates and normalize tuple of strings.
            else:
                # Wraps single string into a tuple.
                if isinstance(field_data, str):
                    field_data = (field_data,)
                if not isinstance(field_data, Sequence):
                    raise ValueError(
                        f"{field_id} is not a tuple or a list: {field_data}"
                    )
                if not all(isinstance(i, str) for i in field_data):
                    raise ValueError(
                        f"{field_id} contains non-string elements: {field_data}"
                    )
                # Ignore blank value.
                field_data = tuple(i.strip() for i in field_data if i.strip())

            # Validates regexps.
            if field_data and "_regex_" in field_id:
                for regex in flatten((field_data,)):
                    try:
                        re.compile(regex)
                    except re.error as ex:
                        raise ValueError(
                            f"Invalid regex in {field_id}: {regex}"
                        ) from ex

            setattr(self, field_id, field_data)

    def check_cli_test(self, binary: str | Path, timeout: int | None = None):
        """Run a CLI command and check its output against the test case.

        ..todo::
            Add support for environment variables.

        ..todo::
            Add support for ANSI code stripping.

        ..todo::
            Add support for proper mixed stdout/stderr stream as a single,
            intertwined output.
        """
        clean_args = args_cleanup(binary, self.cli_parameters)
        try:
            result = run(
                clean_args,
                capture_output=True,
                timeout=timeout,
                check=True,
                # XXX Do not force encoding to let CLIs figure out by
                # themselves the contextual encoding to use. This avoid
                # UnicodeDecodeError on output in Window's console which still
                # defaults to legacy encoding (e.g. cp1252, cp932, etc...):
                #
                #   Traceback (most recent call last):
                #     File "…\__main__.py", line 49, in <module>
                #     File "…\__main__.py", line 45, in main
                #     File "…\click\core.py", line 1157, in __call__
                #     File "…\click_extra\commands.py", line 347, in main
                #     File "…\click\core.py", line 1078, in main
                #     File "…\click_extra\commands.py", line 377, in invoke
                #     File "…\click\core.py", line 1688, in invoke
                #     File "…\click_extra\commands.py", line 377, in invoke
                #     File "…\click\core.py", line 1434, in invoke
                #     File "…\click\core.py", line 783, in invoke
                #     File "…\cloup\_context.py", line 47, in new_func
                #     File "…\mpm\cli.py", line 570, in managers
                #     File "…\mpm\output.py", line 187, in print_table
                #     File "…\click_extra\tabulate.py", line 97, in render_csv
                #     File "encodings\cp1252.py", line 19, in encode
                #   UnicodeEncodeError: 'charmap' codec can't encode character
                #   '\u2713' in position 128: character maps to <undefined>
                #
                # encoding="utf-8",
                text=True,
            )
        except SubprocessError as ex:
            print(f"\n=== stdout ===\n{ex.stdout}")
            print(f"\n=== stderr ===\n{ex.stderr}")
            raise ex

        print_cli_run(clean_args, result)

        for field_id, field_data in asdict(self).items():
            if field_id == "cli_parameters" or (not field_data and field_data != 0):
                continue

            if field_id == "exit_code":
                if result.returncode != field_data:
                    raise AssertionError(
                        f"CLI exited with code {result.returncode}, expected {
                            field_data
                        }"
                    )

            output = ""
            name = ""
            if field_id.startswith("output_"):
                raise NotImplementedError("Output mixing <stdout>/<stderr>")
                # output = result.output
                # name = "output"
            elif field_id.startswith("stdout_"):
                output = result.stdout
                name = "<stdout>"
            elif field_id.startswith("stderr_"):
                output = result.stderr
                name = "<stderr>"

            if self.strip_ansi:
                output = strip_ansi(output)

            if field_id.endswith("_contains"):
                for sub_string in field_data:
                    if sub_string not in output:
                        raise AssertionError(
                            f"CLI's {name} does not contain {sub_string!r}"
                        )

            elif field_id.endswith("_regex_matches"):
                for regex in field_data:
                    if not re.search(regex, output):
                        raise AssertionError(
                            f"CLI's {name} does not match regex {regex!r}"
                        )

            elif field_id.endswith("_regex_fullmatch"):
                regex = field_data
                if not re.fullmatch(regex, output):
                    raise AssertionError(
                        f"CLI's {name} does not fully match regex {regex!r}"
                    )


DEFAULT_TEST_PLAN = (
    # Output the version of the CLI.
    TestCase(cli_parameters="--version"),
    # Test combination of version and verbosity.
    TestCase(cli_parameters=("--verbosity", "DEBUG", "--version")),
    # Test help output.
    TestCase(cli_parameters="--help"),
)


def parse_test_plan(plan_path: Path) -> Generator[TestCase, None, None]:
    plan = yaml.full_load(plan_path.read_text(encoding="UTF-8"))

    # Validates test plan structure.
    if not plan:
        raise ValueError(f"Empty test plan file {plan_path}")
    if not isinstance(plan, list):
        raise ValueError(f"Test plan is not a list: {plan}")

    directives = frozenset(TestCase.__dataclass_fields__.keys())

    for index, test_case in enumerate(plan):
        # Validates test case structure.
        if not isinstance(test_case, dict):
            raise ValueError(f"Test case #{index + 1} is not a dict: {test_case}")
        if not directives.issuperset(test_case):
            raise ValueError(
                f"Test case #{index + 1} contains invalid directives:"
                f"{set(test_case) - directives}"
            )

        yield TestCase(**test_case)
