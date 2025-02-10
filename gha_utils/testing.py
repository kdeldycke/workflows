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

import shlex
import sys
from pathlib import Path
from subprocess import SubprocessError, run
from typing import Generator, Iterable

import yaml

DEFAULT_TEST_PLAN = (
    # Output the version of the CLI.
    ("--version",),
    # Test combination of version and verbosity.
    ("--verbosity", "DEBUG", "--version"),
    # Test help output.
    ("--help",),
)


def parse_test_plan(plan_path: Path) -> Generator[list[str], None, None]:
    plan = yaml.full_load(plan_path.read_text(encoding="UTF-8"))
    if not plan:
        raise ValueError(f"Empty test plan file {plan_path}")
    if not isinstance(plan, list):
        raise ValueError(f"Invalid test plan file {plan_path}")

    for index, test in enumerate(plan):
        if not (
            isinstance(test, dict)
            and len(test) == 1
            and test.keys() == {"cli-parameters"}
            and test["cli-parameters"]
            and isinstance(test["cli-parameters"], str)
        ):
            raise ValueError(
                f"Invalid test plan file {plan_path} at line {index + 1}:\n{test}"
            )

        param_string = test["cli-parameters"].strip()

        if sys.platform == "win32":
            params = param_string.split()
        else:
            params = shlex.split(param_string)

        yield params


def run_cli_test(binary: Path, cli_params: Iterable[str], timeout: int):
    """Run tests."""
    cli = [str(binary), *cli_params]
    try:
        result = run(
            cli,
            capture_output=True,
            shell=True,
            timeout=timeout,
            check=True,
            # XXX Do not force encoding to let CLIs figure out by themselves
            # the contextual encoding to use. This avoid UnicodeDecodeError on
            # output in Window's console which still defaults to legacy
            # encoding (e.g. cp1252, cp932, etc...):
            #
            #   Traceback (most recent call last):
            #     File "C:\...\__main__.py", line 49, in <module>
            #     File "C:\...\__main__.py", line 45, in main
            #     File "C:\...\click\core.py", line 1157, in __call__
            #     File "C:\...\click_extra\commands.py", line 347, in main
            #     File "C:\...\click\core.py", line 1078, in main
            #     File "C:\...\click_extra\commands.py", line 377, in invoke
            #     File "C:\...\click\core.py", line 1688, in invoke
            #     File "C:\...\click_extra\commands.py", line 377, in invoke
            #     File "C:\...\click\core.py", line 1434, in invoke
            #     File "C:\...\click\core.py", line 783, in invoke
            #     File "C:\...\cloup\_context.py", line 47, in new_func
            #     File "C:\...\meta_package_manager\cli.py", line 570, in managers
            #     File "C:\...\meta_package_manager\output.py", line 187, in print_table
            #     File "C:\...\click_extra\tabulate.py", line 97, in render_csv
            #     File "encodings\cp1252.py", line 19, in encode
            #   UnicodeEncodeError: 'charmap' codec can't encode character '\u2713' in position 128:
            #   character maps to <undefined>
            #
            # encoding="utf-8",
            text=True,
        )
    except SubprocessError as ex:
        print(f"\n=== stdout ===\n{ex.stdout}")
        print(f"\n=== stderr ===\n{ex.stderr}")
        raise ex

    print(result.stdout)
