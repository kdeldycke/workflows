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
from string import ascii_lowercase, digits

from extra_platforms import ALL_IDS

from gha_utils.metadata import NUITKA_BUILD_TARGETS, Dialects, Metadata


def test_nuitka_targets():
    for target_id, target_data in NUITKA_BUILD_TARGETS.items():
        assert isinstance(target_id, str)
        assert isinstance(target_data, dict)

        assert set(target_data) == {
            "os",
            "platform_id",
            "arch",
            "extension",
        }, f"Unexpected keys in target data for {target_id}"

        assert isinstance(target_data["os"], str)
        assert isinstance(target_data["platform_id"], str)
        assert isinstance(target_data["arch"], str)
        assert isinstance(target_data["extension"], str)

        assert set(target_data["os"]).issubset(ascii_lowercase + digits + "-.")
        assert target_data["platform_id"] in ALL_IDS
        assert target_data["arch"] in {"arm64", "x64"}
        assert set(target_data["extension"]).issubset(ascii_lowercase)

        assert target_id == target_data["platform_id"] + "-" + target_data["arch"]
        assert set(target_id).issubset(ascii_lowercase + digits + "-")


def test_metadata_github_format():
    metadata = Metadata()

    assert re.fullmatch(
        (
            r"new_commits=\n"
            r"release_commits=\n"
            r"gitignore_exists=true\n"
            r"python_files=[\S ]*\n"
            r"doc_files=[\S ]*\n"
            r"is_python_project=true\n"
            r"package_name=gha-utils\n"
            r"blacken_docs_params=--target-version py311 "
            r"--target-version py312 --target-version py313\n"
            r"mypy_params=--python-version 3\.11\n"
            r"current_version=[0-9\.]+\n"
            r"released_version=\n"
            r"is_sphinx=false\n"
            r"active_autodoc=false\n"
            r"release_notes<<ghadelimiter_[0-9]+\n"
            r"### Changes\n\n"
            r"> \[\!IMPORTANT\]\n"
            r"> This version is not released yet and is under active development.\n\n"
            r".+\n"
            r"ghadelimiter_[0-9]+\n"
            r"new_commits_matrix=\n"
            r"release_commits_matrix=\n"
            #
            r"nuitka_matrix=\{"
            #
            r'"os": \["ubuntu-24\.04-arm", "ubuntu-24\.04", '
            r'"macos-15", "macos-13", "windows-11-arm", "windows-2025"\], '
            #
            r'"entry_point": \["gha-utils"\], '
            #
            r'"commit": \["[a-z0-9]+"\], '
            #
            r'"include": \['
            #
            r'\{"target": "linux-arm64", "os": "ubuntu-24\.04-arm", '
            r'"platform_id": "linux", "arch": "arm64", "extension": "bin"\}, '
            r'\{"target": "linux-x64", "os": "ubuntu-24\.04", '
            r'"platform_id": "linux", "arch": "x64", "extension": "bin"\}, '
            r'\{"target": "macos-arm64", "os": "macos-15", '
            r'"platform_id": "macos", "arch": "arm64", "extension": "bin"\}, '
            r'\{"target": "macos-x64", "os": "macos-13", '
            r'"platform_id": "macos", "arch": "x64", '
            r'"extension": "bin"\}, '
            r'\{"target": "windows-arm64", "os": "windows-11-arm", '
            r'"platform_id": "windows", "arch": "arm64", "extension": "exe"\}, '
            r'\{"target": "windows-x64", "os": "windows-2025", '
            r'"platform_id": "windows", "arch": "x64", "extension": "exe"\}, '
            #
            r'\{"entry_point": "gha-utils", '
            r'"cli_id": "gha-utils", "module_id": "gha_utils\.__main__", '
            r'"callable_id": "main", '
            r'"module_path": "gha_utils(/|\\\\)__main__\.py"\}, '
            #
            r'\{"commit": "[a-z0-9]+", "short_sha": "[a-z0-9]+", '
            r'"current_version": "[0-9\.]+"\}, '
            #
            r'\{"os": "ubuntu-24\.04-arm", "entry_point": "gha-utils", '
            r'"commit": "[a-z0-9]+", '
            r'"bin_name": "gha-utils-linux-arm64-[a-z0-9]+\.bin"\}, '
            r'\{"os": "ubuntu-24\.04", "entry_point": "gha-utils", '
            r'"commit": "[a-z0-9]+", '
            r'"bin_name": "gha-utils-linux-x64-[a-z0-9]+\.bin"\}, '
            r'\{"os": "macos-15", "entry_point": "gha-utils", '
            r'"commit": "[a-z0-9]+", '
            r'"bin_name": "gha-utils-macos-arm64-[a-z0-9]+\.bin"\}, '
            r'\{"os": "macos-13", "entry_point": "gha-utils", '
            r'"commit": "[a-z0-9]+", '
            r'"bin_name": "gha-utils-macos-x64-[a-z0-9]+\.bin"\}, '
            r'\{"os": "windows-11-arm", "entry_point": "gha-utils", '
            r'"commit": "[a-z0-9]+", '
            r'"bin_name": "gha-utils-windows-arm64-[a-z0-9]+\.exe"\}, '
            r'\{"os": "windows-2025", "entry_point": "gha-utils", '
            r'"commit": "[a-z0-9]+", '
            r'"bin_name": "gha-utils-windows-x64-[a-z0-9]+\.exe"\}, '
            r'\{"state": "stable"\}\]\}\n'
        ),
        metadata.dump(Dialects.github),
        re.DOTALL,
    )


def test_metadata_plain_format():
    metadata = Metadata()

    assert re.fullmatch(
        (
            r"\{"
            r"'new_commits': None, "
            r"'release_commits': None, "
            r"'gitignore_exists': True, "
            r"'python_files': <generator object Metadata\.python_files at \S+>, "
            r"'doc_files': <generator object Metadata\.doc_files at \S+>, "
            r"'is_python_project': True, "
            r"'package_name': 'gha-utils', "
            r"'blacken_docs_params': \("
            r"'--target-version py311', "
            r"'--target-version py312', "
            r"'--target-version py313'\), "
            r"'mypy_params': '--python-version 3\.11', "
            r"'current_version': '[0-9\.]+', "
            r"'released_version': None, "
            r"'is_sphinx': False, "
            r"'active_autodoc': False, "
            r"'release_notes': '### Changes\\n\\n"
            r"> \[\!IMPORTANT\]\\n"
            r"> This version is not released yet and is under active development.\\n\\n"
            r".+', "
            r"'new_commits_matrix': None, "
            r"'release_commits_matrix': None, "
            r"'nuitka_matrix': <Matrix: \{"
            r"'os': \('ubuntu-24\.04-arm', 'ubuntu-24\.04', "
            r"'macos-15', 'macos-13', 'windows-11-arm', 'windows-2025'\), "
            r"'entry_point': \('gha-utils',\), "
            r"'commit': \('[a-z0-9]+',\)\}; "
            #
            r"include=\(\{'target': 'linux-arm64', 'os': 'ubuntu-24\.04-arm', "
            r"'platform_id': 'linux', 'arch': 'arm64', 'extension': 'bin'\}, "
            r"\{'target': 'linux-x64', 'os': 'ubuntu-24\.04', 'platform_id': 'linux', "
            r"'arch': 'x64', 'extension': 'bin'\}, \{'target': 'macos-arm64', 'os': 'macos-15', "
            r"'platform_id': 'macos', 'arch': 'arm64', 'extension': 'bin'\}, "
            r"\{'target': 'macos-x64', 'os': 'macos-13', 'platform_id': 'macos', 'arch': 'x64', "
            r"'extension': 'bin'\}, \{'target': 'windows-arm64', 'os': 'windows-11-arm', 'platform_id': "
            r"'windows', 'arch': 'arm64', 'extension': 'exe'\}, "
            r"\{'target': 'windows-x64', 'os': 'windows-2025', 'platform_id': "
            r"'windows', 'arch': 'x64', 'extension': 'exe'\}, "
            #
            r"\{'entry_point': 'gha-utils', 'cli_id': 'gha-utils', "
            r"'module_id': 'gha_utils\.__main__', 'callable_id': 'main', "
            r"'module_path': 'gha_utils(/|\\\\)__main__\.py'\}, "
            #
            r"\{'commit': '[a-z0-9]+', 'short_sha': '[a-z0-9]+', "
            r"'current_version': '[0-9\.]+'\}, "
            #
            r"\{'os': 'ubuntu-24\.04-arm', 'entry_point': 'gha-utils', "
            r"'commit': '[a-z0-9]+', "
            r"'bin_name': 'gha-utils-linux-arm64-[a-z0-9]+\.bin'\}, "
            r"\{'os': 'ubuntu-24\.04', 'entry_point': 'gha-utils', "
            r"'commit': '[a-z0-9]+', "
            r"'bin_name': 'gha-utils-linux-x64-[a-z0-9]+\.bin'\}, "
            r"\{'os': 'macos-15', 'entry_point': 'gha-utils', "
            r"'commit': '[a-z0-9]+', "
            r"'bin_name': 'gha-utils-macos-arm64-[a-z0-9]+\.bin'\}, "
            r"\{'os': 'macos-13', 'entry_point': 'gha-utils', "
            r"'commit': '[a-z0-9]+', 'bin_name': "
            r"'gha-utils-macos-x64-[a-z0-9]+\.bin'\}, "
            r"\{'os': 'windows-11-arm', 'entry_point': 'gha-utils', "
            r"'commit': '[a-z0-9]+', "
            r"'bin_name': 'gha-utils-windows-arm64-[a-z0-9]+\.exe'\}, "
            r"\{'os': 'windows-2025', 'entry_point': 'gha-utils', "
            r"'commit': '[a-z0-9]+', "
            r"'bin_name': 'gha-utils-windows-x64-[a-z0-9]+\.exe'\}, "
            r"\{'state': 'stable'\}\); "
            r"exclude=\(\)>\}"
        ),
        metadata.dump(Dialects.plain),
        re.DOTALL,
    )
