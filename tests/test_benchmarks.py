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

"""Performance benchmarks for gha-utils using pytest-codspeed."""

from __future__ import annotations

from pathlib import Path

from pytest_codspeed import BenchmarkFixture

from gha_utils.metadata import Metadata, get_latest_tag_version


def test_metadata_creation(benchmark: BenchmarkFixture) -> None:
    """Benchmark Metadata object creation and initialization."""

    @benchmark
    def bench():
        Metadata()


def test_metadata_json_dump(benchmark: BenchmarkFixture) -> None:
    """Benchmark JSON serialization of metadata."""
    from gha_utils.metadata import Dialect

    metadata = Metadata()

    @benchmark
    def bench():
        metadata.dump(Dialect.json)


def test_metadata_github_dump(benchmark: BenchmarkFixture) -> None:
    """Benchmark GitHub format serialization of metadata."""
    metadata = Metadata()

    @benchmark
    def bench():
        metadata.dump()


def test_get_latest_tag_version_benchmark(benchmark: BenchmarkFixture) -> None:
    """Benchmark retrieving the latest Git tag version."""

    @benchmark
    def bench():
        get_latest_tag_version()


def test_changelog_update(benchmark: BenchmarkFixture) -> None:
    """Benchmark changelog update operations."""
    from gha_utils.changelog import Changelog

    changelog_path = Path(__file__).parent.parent / "changelog.md"
    if not changelog_path.exists():
        return

    initial_content = changelog_path.read_text()

    @benchmark
    def bench():
        changelog = Changelog(initial_content)
        changelog.update()
