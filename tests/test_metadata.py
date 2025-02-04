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
            r"blacken_docs_params=--target-version py310 --target-version py311 "
            r"--target-version py312 --target-version py313\n"
            r"ruff_py_version=py310\n"
            r"mypy_params=--python-version 3\.10\n"
            r"current_version=\n"
            r"released_version=\n"
            r"is_sphinx=false\n"
            r"active_autodoc=false\n"
            r"release_notes=\n"
            r"new_commits_matrix=\n"
            r"release_commits_matrix=\n"
            r'nuitka_matrix=\{"os": \["ubuntu-24\.04", "ubuntu-24\.04-arm", '
            r'"macos-15", "macos-13", "windows-2022"\], '
            r'"entry_point": \["gha-utils"\], '
            r'"commit": \["[a-z0-9]+"\]\}\n'
        ),
        metadata.dump(Dialects.github),
    )


def test_metadata_plain_format():
    metadata = Metadata()

    assert re.fullmatch(
        (
            r"\{"
            r"'new_commits': None, "
            r"'release_commits': None, "
            r"'gitignore_exists': True, "
            r"'python_files': <generator object Metadata\.python_files at 0x[a-z0-9]+>, "
            r"'doc_files': <generator object Metadata\.doc_files at 0x[a-z0-9]+>, "
            r"'is_python_project': True, "
            r"'package_name': 'gha-utils', "
            r"'blacken_docs_params': \("
            r"'--target-version py310', "
            r"'--target-version py311', "
            r"'--target-version py312', "
            r"'--target-version py313'\), "
            r"'ruff_py_version': 'py310', "
            r"'mypy_params': '--python-version 3\.10', "
            r"'current_version': None, "
            r"'released_version': None, "
            r"'is_sphinx': False, "
            r"'active_autodoc': False, "
            r"'release_notes': None, "
            r"'new_commits_matrix': None, "
            r"'release_commits_matrix': None, "
            r"'nuitka_matrix': <Matrix: \{"
            r"'os': \('ubuntu-24\.04', 'ubuntu-24\.04-arm', "
            r"'macos-15', 'macos-13', 'windows-2022'\), "
            r"'entry_point': \('gha-utils',\), "
            r"'commit': \('[a-z0-9]+',\)\}; "
            r"include=\(\); exclude=\(\)>\}"
        ),
        metadata.dump(Dialects.plain),
    )
