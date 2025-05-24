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

from gha_utils.metadata import Dialects, Metadata


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
            r'nuitka_matrix=\{"os": \["ubuntu-24\.04-arm", "ubuntu-24\.04", '
            r'"macos-15", "macos-13", "windows-11-arm", "windows-2025"\], '
            r'"entry_point": \["gha-utils"\], "commit": \["[a-z0-9]+"\], '
            r'"include": \[\{"entry_point": "gha-utils", '
            r'"cli_id": "gha-utils", "module_id": "gha_utils\.__main__", '
            r'"callable_id": "main", '
            r'"module_path": "gha_utils(/|\\\\)__main__\.py"\}, '
            r'\{"commit": "[a-z0-9]+", "short_sha": "[a-z0-9]+", '
            r'"current_version": "[0-9\.]+"\}, \{"os": "ubuntu-24\.04-arm", '
            r'"platform_id": "linux", "arch": "arm64", "extension": "bin"\}, '
            r'\{"os": "ubuntu-24\.04", "platform_id": "linux", '
            r'"arch": "x64", "extension": "bin"\}, \{"os": "macos-15", '
            r'"platform_id": "macos", "arch": "arm64", "extension": "bin"\}, '
            r'\{"os": "macos-13", "platform_id": "macos", "arch": "x64", '
            r'"extension": "bin"\}, \{"os": "windows-11-arm", '
            r'"platform_id": "windows", "arch": "arm64", "extension": "exe"\}, '
            r'\{"os": "windows-2025", '
            r'"platform_id": "windows", "arch": "x64", "extension": "exe"\}, '
            r'\{"os": "ubuntu-24\.04-arm", "entry_point": "gha-utils", '
            r'"commit": "[a-z0-9]+", '
            r'"bin_name": "gha-utils-linux-arm64-build-[a-z0-9]+\.bin"\}, '
            r'\{"os": "ubuntu-24\.04", "entry_point": "gha-utils", '
            r'"commit": "[a-z0-9]+", '
            r'"bin_name": "gha-utils-linux-x64-build-[a-z0-9]+\.bin"\}, '
            r'\{"os": "macos-15", "entry_point": "gha-utils", '
            r'"commit": "[a-z0-9]+", '
            r'"bin_name": "gha-utils-macos-arm64-build-[a-z0-9]+\.bin"\}, '
            r'\{"os": "macos-13", "entry_point": "gha-utils", '
            r'"commit": "[a-z0-9]+", '
            r'"bin_name": "gha-utils-macos-x64-build-[a-z0-9]+\.bin"\}, '
            r'\{"os": "windows-11-arm", "entry_point": "gha-utils", '
            r'"commit": "[a-z0-9]+", '
            r'"bin_name": "gha-utils-windows-arm64-build-[a-z0-9]+\.exe"\}, '
            r'\{"os": "windows-2025", "entry_point": "gha-utils", '
            r'"commit": "[a-z0-9]+", '
            r'"bin_name": "gha-utils-windows-x64-build-[a-z0-9]+\.exe"\}, '
            r'\{"state": "stable"\}, '
            r'\{"state": "unstable", "os": "windows-11-arm"\}\]\}\n'
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
            r"include=\(\{'entry_point': 'gha-utils', 'cli_id': 'gha-utils', "
            r"'module_id': 'gha_utils\.__main__', 'callable_id': 'main', "
            r"'module_path': 'gha_utils(/|\\\\)__main__\.py'\}, "
            r"\{'commit': '[a-z0-9]+', 'short_sha': '[a-z0-9]+', "
            r"'current_version': '[0-9\.]+'\}, \{'os': 'ubuntu-24\.04-arm', "
            r"'platform_id': 'linux', 'arch': 'arm64', 'extension': 'bin'}, "
            r"{'os': 'ubuntu-24\.04', 'platform_id': 'linux', "
            r"'arch': 'x64', 'extension': 'bin'\}, \{'os': 'macos-15', "
            r"'platform_id': 'macos', 'arch': 'arm64', 'extension': 'bin'\}, "
            r"\{'os': 'macos-13', 'platform_id': 'macos', 'arch': 'x64', "
            r"'extension': 'bin'\}, \{'os': 'windows-11-arm', 'platform_id': "
            r"'windows', 'arch': 'arm64', 'extension': 'exe'\}, "
            r"\{'os': 'windows-2025', 'platform_id': "
            r"'windows', 'arch': 'x64', 'extension': 'exe'\}, "
            r"\{'os': 'ubuntu-24\.04-arm', 'entry_point': 'gha-utils', "
            r"'commit': '[a-z0-9]+', "
            r"'bin_name': 'gha-utils-linux-arm64-build-[a-z0-9]+\.bin'\}, "
            r"\{'os': 'ubuntu-24\.04', 'entry_point': 'gha-utils', "
            r"'commit': '[a-z0-9]+', "
            r"'bin_name': 'gha-utils-linux-x64-build-[a-z0-9]+\.bin'\}, "
            r"\{'os': 'macos-15', 'entry_point': 'gha-utils', "
            r"'commit': '[a-z0-9]+', "
            r"'bin_name': 'gha-utils-macos-arm64-build-[a-z0-9]+\.bin'\}, "
            r"\{'os': 'macos-13', 'entry_point': 'gha-utils', "
            r"'commit': '[a-z0-9]+', 'bin_name': "
            r"'gha-utils-macos-x64-build-[a-z0-9]+\.bin'\}, "
            r"\{'os': 'windows-11-arm', 'entry_point': 'gha-utils', "
            r"'commit': '[a-z0-9]+', "
            r"'bin_name': 'gha-utils-windows-arm64-build-[a-z0-9]+\.exe'\}, "
            r"\{'os': 'windows-2025', 'entry_point': 'gha-utils', "
            r"'commit': '[a-z0-9]+', "
            r"'bin_name': 'gha-utils-windows-x64-build-[a-z0-9]+\.exe'\}, "
            r"\{'state': 'stable'\}, "
            r"\{'state': 'unstable', 'os': 'windows-11-arm'\}\); "
            r"exclude=\(\)>\}"
        ),
        metadata.dump(Dialects.plain),
        re.DOTALL,
    )
