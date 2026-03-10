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

"""Tests for the ``sync-zizmor`` CLI command."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from repomatic.cli import sync_zizmor
from repomatic.init_project import export_content

MINIMAL_PYPROJECT = "[project]\nname = 'test'\nversion = '0.1.0'\n"


@pytest.mark.parametrize("pre_existing", [True, False])
def test_sync_zizmor_writes_canonical_config(
    tmp_path, monkeypatch, pre_existing
):
    """Sync writes the canonical bundled config whether the file exists or not."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "zizmor.yaml"
    if pre_existing:
        target.write_text("# old content")
    (tmp_path / "pyproject.toml").write_text(MINIMAL_PYPROJECT)

    result = CliRunner().invoke(sync_zizmor)
    assert result.exit_code == 0
    assert target.read_text(encoding="utf-8").rstrip() == export_content(
        "zizmor.yaml"
    ).rstrip()


def test_sync_zizmor_config_toggle_off(tmp_path, monkeypatch):
    """Exit 0 when ``zizmor.sync = false`` in ``[tool.repomatic]``."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "zizmor.yaml"
    target.write_text("# old content")
    (tmp_path / "pyproject.toml").write_text(
        MINIMAL_PYPROJECT + "\n[tool.repomatic]\nzizmor.sync = false\n"
    )

    result = CliRunner().invoke(sync_zizmor)
    assert result.exit_code == 0
    assert target.read_text() == "# old content"
