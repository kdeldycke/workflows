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

"""Tests for the ``sync-renovate`` CLI command."""

from __future__ import annotations

from click.testing import CliRunner

from gha_utils.cli import sync_renovate
from gha_utils.init_project import export_content


def test_sync_renovate_writes_canonical_config(tmp_path, monkeypatch):
    """Sync overwrites the target with the canonical bundled config."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "renovate.json5"
    target.write_text('{ "old": true }')
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'test'\nversion = '0.1.0'\n")

    runner = CliRunner()
    result = runner.invoke(sync_renovate, ["--output", str(target)])
    assert result.exit_code == 0
    expected = export_content("renovate.json5").rstrip()
    assert target.read_text(encoding="utf-8").rstrip() == expected


def test_sync_renovate_skips_when_missing(tmp_path, monkeypatch):
    """Exit 0 when ``renovate.json5`` does not exist."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "renovate.json5"
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'test'\nversion = '0.1.0'\n")

    runner = CliRunner()
    result = runner.invoke(sync_renovate, ["--output", str(target)])
    assert result.exit_code == 0
    assert not target.exists()


def test_sync_renovate_config_toggle_off(tmp_path, monkeypatch):
    """Exit 0 when ``renovate-sync = false`` in ``[tool.gha-utils]``."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "renovate.json5"
    target.write_text('{ "old": true }')
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        "[project]\nname = 'test'\nversion = '0.1.0'\n\n"
        "[tool.gha-utils]\nrenovate-sync = false\n"
    )

    runner = CliRunner()
    result = runner.invoke(sync_renovate, ["--output", str(target)])
    assert result.exit_code == 0
    # File should remain unchanged.
    assert target.read_text() == '{ "old": true }'


def test_sync_renovate_overwrites_existing(tmp_path, monkeypatch):
    """Existing stale content is fully replaced."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "renovate.json5"
    target.write_text('{ "lockFileMaintenance": { "enabled": true } }')
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'test'\nversion = '0.1.0'\n")

    runner = CliRunner()
    result = runner.invoke(sync_renovate, ["--output", str(target)])
    assert result.exit_code == 0
    expected = export_content("renovate.json5").rstrip()
    assert target.read_text(encoding="utf-8").rstrip() == expected
    # The stale key should be gone.
    assert "lockFileMaintenance" not in target.read_text(encoding="utf-8")
