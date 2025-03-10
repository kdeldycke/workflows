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
import re
import shlex
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from subprocess import TimeoutExpired, run
from typing import Generator, Sequence

import yaml
from boltons.iterutils import flatten
from boltons.strutils import strip_ansi
from click_extra.testing import args_cleanup, render_cli_run
from extra_platforms import Group, _TNestedReferences, current_os


class SkippedTest(Exception):
    """Raised when a test case should be skipped."""

    pass


@dataclass(order=True)
class CLITestCase:
    cli_parameters: tuple[str, ...] | str = field(default_factory=tuple)
    """Parameters, arguments and options to pass to the CLI."""

    skip_platforms: _TNestedReferences = field(default_factory=tuple)
    only_platforms: _TNestedReferences = field(default_factory=tuple)
    timeout: float | str | None = None
    exit_code: int | str | None = None
    strip_ansi: bool = False
    output_contains: tuple[str, ...] | str = field(default_factory=tuple)
    stdout_contains: tuple[str, ...] | str = field(default_factory=tuple)
    stderr_contains: tuple[str, ...] | str = field(default_factory=tuple)
    output_regex_matches: tuple[re.Pattern | str, ...] | str = field(
        default_factory=tuple
    )
    stdout_regex_matches: tuple[re.Pattern | str, ...] | str = field(
        default_factory=tuple
    )
    stderr_regex_matches: tuple[re.Pattern | str, ...] | str = field(
        default_factory=tuple
    )
    output_regex_fullmatch: re.Pattern | str | None = None
    stdout_regex_fullmatch: re.Pattern | str | None = None
    stderr_regex_fullmatch: re.Pattern | str | None = None

    def __post_init__(self) -> None:
        """Normalize all fields."""
        for field_id, field_data in asdict(self).items():
            # Validates and normalize integer properties.
            if field_id == "exit_code":
                if isinstance(field_data, str):
                    field_data = int(field_data)
                elif field_data is not None and not isinstance(field_data, int):
                    raise ValueError(f"exit_code is not an integer: {field_data}")

            # Validates and normalize float properties.
            elif field_id == "timeout":
                if isinstance(field_data, str):
                    field_data = float(field_data)
                elif field_data is not None and not isinstance(field_data, float):
                    raise ValueError(f"timeout is not a float: {field_data}")
                # Timeout can only be unset or positive.
                if field_data and field_data < 0:
                    raise ValueError(f"timeout is negative: {field_data}")

            # Validates and normalize boolean properties.
            elif field_id == "strip_ansi":
                if not isinstance(field_data, bool):
                    raise ValueError(f"strip_ansi is not a boolean: {field_data}")

            # Validates and normalize tuple of strings.
            else:
                if field_data:
                    # Wraps single string and other types into a tuple.
                    if isinstance(field_data, str) or not isinstance(
                        field_data, Sequence
                    ):
                        # CLI parameters provided as a long string needs to be split so
                        # that each argument is a separate item in the final tuple.
                        if field_id == "cli_parameters":
                            # XXX Maybe we should rely on a library to parse them:
                            # https://github.com/maxpat78/w32lex
                            if sys.platform == "win32":
                                field_data = field_data.split()
                            # For Unix platforms, we have the dedicated shlex module.
                            else:
                                field_data = shlex.split(field_data)
                        else:
                            field_data = (field_data,)

                    for item in field_data:
                        if not isinstance(item, str):
                            raise ValueError(f"Invalid string in {field_id}: {item}")
                    # Ignore blank value.
                    field_data = tuple(i for i in field_data if i.strip())

            # Normalize any mishmash of platform and group IDs into a set of platforms.
            if field_id.endswith("_platforms") and field_data:
                field_data = frozenset(Group._extract_platforms(field_data))

            # Validates fields containing one or more regexes.
            if "_regex_" in field_id and field_data:
                # Compile all regexes.
                valid_regexes = []
                for regex in flatten((field_data,)):
                    try:
                        # Let dots in regex match newlines.
                        valid_regexes.append(re.compile(regex, re.DOTALL))
                    except re.error as ex:
                        raise ValueError(
                            f"Invalid regex in {field_id}: {regex}"
                        ) from ex
                # Normalize single regex to a single element.
                if field_id.endswith("_fullmatch"):
                    if valid_regexes:
                        field_data = valid_regexes.pop()
                    else:
                        field_data = None
                else:
                    field_data = tuple(valid_regexes)

            setattr(self, field_id, field_data)

    def run_cli_test(
        self,
        binary: str | Path,
        additional_skip_platforms: _TNestedReferences | None,
        default_timeout: float | None,
    ):
        """Run a CLI command and check its output against the test case.

        ..todo::
            Add support for environment variables.

        ..todo::
            Add support for proper mixed <stdout>/<stderr> stream as a single,
            intertwined output.
        """
        if self.only_platforms:
            if current_os() not in self.only_platforms:  # type: ignore[operator]
                raise SkippedTest(f"Test case only runs on platform: {current_os()}")

        if current_os() in Group._extract_platforms(
            self.skip_platforms, additional_skip_platforms
        ):
            raise SkippedTest(f"Skipping test case on platform: {current_os()}")

        if self.timeout is None and default_timeout is not None:
            logging.info(f"Set default test case timeout to {default_timeout} seconds")
            self.timeout = default_timeout

        clean_args = args_cleanup(binary, self.cli_parameters)
        try:
            result = run(
                clean_args,
                capture_output=True,
                timeout=self.timeout,  # type: ignore[arg-type]
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
        except TimeoutExpired:
            raise TimeoutError(
                f"CLI timed out after {self.timeout} seconds: {' '.join(clean_args)}"
            )

        for line in render_cli_run(clean_args, result).splitlines():
            logging.info(line)

        for field_id, field_data in asdict(self).items():
            if field_id == "exit_code":
                if field_data is not None:
                    logging.info(f"Test exit code, expecting: {field_data}")
                    if result.returncode != field_data:
                        raise AssertionError(
                            f"CLI exited with code {result.returncode}, "
                            f"expected {field_data}"
                        )
                # The specific exit code matches, let's proceed to the next test.
                continue

            # Ignore non-output fields, and empty test cases.
            elif not (
                field_id.startswith(("output_", "stdout_", "stderr_")) and field_data
            ):
                continue

            # Prepare output and name for comparison.
            output = ""
            name = ""
            if field_id.startswith("output_"):
                raise NotImplementedError("<stdout>/<stderr> output mix")
                # output = result.output
                # name = "output"
            elif field_id.startswith("stdout_"):
                output = result.stdout
                name = "<stdout>"
            elif field_id.startswith("stderr_"):
                output = result.stderr
                name = "<stderr>"

            if self.strip_ansi:
                logging.info(f"Strip ANSI sequences from {name}")
                output = strip_ansi(output)

            if field_id.endswith("_contains"):
                for sub_string in field_data:
                    logging.info(f"Check if {name} contains {sub_string!r}")
                    if sub_string not in output:
                        raise AssertionError(f"{name} does not contain {sub_string!r}")

            elif field_id.endswith("_regex_matches"):
                for regex in field_data:
                    logging.info(f"Check if {name} matches {sub_string!r}")
                    if not regex.search(output):
                        raise AssertionError(f"{name} does not match regex {regex}")

            elif field_id.endswith("_regex_fullmatch"):
                regex = field_data
                if not regex.fullmatch(output):
                    raise AssertionError(f"{name} does not fully match regex {regex}")


DEFAULT_TEST_PLAN: list[CLITestCase] = [
    # Output the version of the CLI.
    CLITestCase(cli_parameters="--version"),
    # Test combination of version and verbosity.
    CLITestCase(cli_parameters=("--verbosity", "DEBUG", "--version")),
    # Test help output.
    CLITestCase(cli_parameters="--help"),
]


def parse_test_plan(plan_string: str | None) -> Generator[CLITestCase, None, None]:
    if not plan_string:
        raise ValueError("Empty test plan")

    plan = yaml.full_load(plan_string)

    # Validates test plan structure.
    if not plan:
        raise ValueError("Empty test plan")
    if not isinstance(plan, list):
        raise ValueError(f"Test plan is not a list: {plan}")

    directives = frozenset(CLITestCase.__dataclass_fields__.keys())

    for index, test_case in enumerate(plan):
        # Validates test case structure.
        if not isinstance(test_case, dict):
            raise ValueError(f"Test case #{index + 1} is not a dict: {test_case}")
        if not directives.issuperset(test_case):
            raise ValueError(
                f"Test case #{index + 1} contains invalid directives:"
                f"{set(test_case) - directives}"
            )

        yield CLITestCase(**test_case)
