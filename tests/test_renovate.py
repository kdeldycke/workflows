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

"""Tests for Renovate utilities module."""

from __future__ import annotations

import subprocess
from datetime import date, timedelta
from unittest.mock import MagicMock, patch


from gha_utils.renovate import (
    add_exclude_newer_to_file,
    calculate_target_date,
    check_commit_statuses_permission,
    check_dependabot_config_absent,
    check_dependabot_security_disabled,
    has_tool_uv_section,
    parse_exclude_newer_date,
    run_renovate_prereq_checks,
    update_exclude_newer_in_file,
)


class TestParseExcludeNewerDate:
    """Tests for parse_exclude_newer_date function."""

    def test_valid_date(self, tmp_path):
        """Parse valid exclude-newer date."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.uv]\nexclude-newer = "2025-01-15T00:00:00Z"\n')
        result = parse_exclude_newer_date(pyproject)
        assert result == date(2025, 1, 15)

    def test_date_in_pip_section(self, tmp_path):
        """Parse date from tool.uv.pip section."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.uv.pip]\nexclude-newer = "2025-01-20T00:00:00Z"\n')
        result = parse_exclude_newer_date(pyproject)
        assert result == date(2025, 1, 20)

    def test_no_exclude_newer(self, tmp_path):
        """Return None when no exclude-newer field."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.uv]\ndev-dependencies = []\n")
        result = parse_exclude_newer_date(pyproject)
        assert result is None

    def test_file_not_exists(self, tmp_path):
        """Return None when file doesn't exist."""
        pyproject = tmp_path / "pyproject.toml"
        result = parse_exclude_newer_date(pyproject)
        assert result is None

    def test_malformed_date(self, tmp_path):
        """Return None for malformed date."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.uv]\nexclude-newer = "not-a-date"\n')
        result = parse_exclude_newer_date(pyproject)
        assert result is None

    def test_invalid_toml(self, tmp_path):
        """Return None for invalid TOML."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("this is not valid TOML [[[")
        result = parse_exclude_newer_date(pyproject)
        assert result is None


class TestHasToolUvSection:
    """Tests for has_tool_uv_section function."""

    def test_has_section(self, tmp_path):
        """Return True when [tool.uv] exists."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.uv]\ndev-dependencies = []\n")
        assert has_tool_uv_section(pyproject) is True

    def test_no_section(self, tmp_path):
        """Return False when [tool.uv] doesn't exist."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\nname = \"test\"\n")
        assert has_tool_uv_section(pyproject) is False

    def test_file_not_exists(self, tmp_path):
        """Return False when file doesn't exist."""
        pyproject = tmp_path / "pyproject.toml"
        assert has_tool_uv_section(pyproject) is False

    def test_invalid_toml(self, tmp_path):
        """Return False for invalid TOML."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("this is not valid TOML [[[")
        assert has_tool_uv_section(pyproject) is False


class TestAddExcludeNewerToFile:
    """Tests for add_exclude_newer_to_file function."""

    def test_add_to_existing_section(self, tmp_path):
        """Add exclude-newer to existing [tool.uv] section."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.uv]\ndev-dependencies = []\n")
        result = add_exclude_newer_to_file(pyproject, date(2025, 1, 20))
        assert result is True
        content = pyproject.read_text()
        assert 'exclude-newer = "2025-01-20T00:00:00Z"' in content
        assert "dev-dependencies = []" in content

    def test_no_tool_uv_section(self, tmp_path):
        """Return False when no [tool.uv] section."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\nname = \"test\"\n")
        result = add_exclude_newer_to_file(pyproject, date(2025, 1, 20))
        assert result is False

    def test_exclude_newer_already_exists(self, tmp_path):
        """Return False when exclude-newer already exists."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.uv]\nexclude-newer = "2025-01-01T00:00:00Z"\n')
        result = add_exclude_newer_to_file(pyproject, date(2025, 1, 20))
        assert result is False

    def test_file_not_exists(self, tmp_path):
        """Return False when file doesn't exist."""
        pyproject = tmp_path / "pyproject.toml"
        result = add_exclude_newer_to_file(pyproject, date(2025, 1, 20))
        assert result is False

    def test_adds_comment_block(self, tmp_path):
        """Adds explanatory comments with the setting."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.uv]\ndev-dependencies = []\n")
        add_exclude_newer_to_file(pyproject, date(2025, 1, 20))
        content = pyproject.read_text()
        assert "Cooldown period" in content
        assert "auto-updated by the autofix workflow" in content


class TestCalculateTargetDate:
    """Tests for calculate_target_date function."""

    def test_default_7_days(self):
        """Default to 7 days ago."""
        expected = date.today() - timedelta(days=7)
        assert calculate_target_date() == expected

    def test_custom_days(self):
        """Calculate with custom days."""
        expected = date.today() - timedelta(days=14)
        assert calculate_target_date(days_ago=14) == expected


class TestUpdateExcludeNewerInFile:
    """Tests for update_exclude_newer_in_file function."""

    def test_update_date(self, tmp_path):
        """Update exclude-newer date."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.uv]\nexclude-newer = "2025-01-01T00:00:00Z"\n')
        result = update_exclude_newer_in_file(pyproject, date(2025, 1, 20))
        assert result is True
        content = pyproject.read_text()
        assert 'exclude-newer = "2025-01-20T00:00:00Z"' in content

    def test_no_change_needed(self, tmp_path):
        """Return False when date is already correct."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[tool.uv]\nexclude-newer = "2025-01-20T00:00:00Z"\n')
        result = update_exclude_newer_in_file(pyproject, date(2025, 1, 20))
        assert result is False

    def test_file_not_exists(self, tmp_path):
        """Return False when file doesn't exist."""
        pyproject = tmp_path / "pyproject.toml"
        result = update_exclude_newer_in_file(pyproject, date(2025, 1, 20))
        assert result is False

    def test_no_exclude_newer_field(self, tmp_path):
        """Return False when no exclude-newer field."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[tool.uv]\ndev-dependencies = []\n")
        result = update_exclude_newer_in_file(pyproject, date(2025, 1, 20))
        assert result is False

    def test_preserves_formatting(self, tmp_path):
        """Preserve surrounding content and formatting."""
        pyproject = tmp_path / "pyproject.toml"
        original = """\
[project]
name = "my-package"

[tool.uv]
exclude-newer = "2025-01-01T00:00:00Z"
dev-dependencies = []
"""
        pyproject.write_text(original)
        update_exclude_newer_in_file(pyproject, date(2025, 1, 20))
        content = pyproject.read_text()
        assert '[project]\nname = "my-package"' in content
        assert "dev-dependencies = []" in content


class TestCheckDependabotConfigAbsent:
    """Tests for check_dependabot_config_absent function."""

    def test_no_config_file(self, tmp_path, monkeypatch):
        """Pass when no Dependabot config exists."""
        monkeypatch.chdir(tmp_path)
        passed, msg = check_dependabot_config_absent()
        assert passed is True
        assert "disabled" in msg

    def test_yaml_exists(self, tmp_path, monkeypatch):
        """Fail when .github/dependabot.yaml exists."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "dependabot.yaml").touch()
        passed, msg = check_dependabot_config_absent()
        assert passed is False
        assert "dependabot.yaml" in msg

    def test_yml_exists(self, tmp_path, monkeypatch):
        """Fail when .github/dependabot.yml exists."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "dependabot.yml").touch()
        passed, msg = check_dependabot_config_absent()
        assert passed is False
        assert "dependabot.yml" in msg


class TestCheckDependabotSecurityDisabled:
    """Tests for check_dependabot_security_disabled function."""

    def test_disabled(self):
        """Pass when security updates disabled."""
        with patch("gha_utils.renovate.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="disabled\n", returncode=0)
            passed, msg = check_dependabot_security_disabled("owner/repo")
            assert passed is True
            assert "disabled" in msg

    def test_enabled(self):
        """Fail when security updates enabled."""
        with patch("gha_utils.renovate.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="enabled\n", returncode=0)
            passed, msg = check_dependabot_security_disabled("owner/repo")
            assert passed is False
            assert "enabled" in msg.lower()

    def test_api_failure(self):
        """Handle API failure gracefully."""
        with patch("gha_utils.renovate.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "gh")
            passed, msg = check_dependabot_security_disabled("owner/repo")
            # Non-fatal, passes but with warning message.
            assert passed is True


class TestCheckCommitStatusesPermission:
    """Tests for check_commit_statuses_permission function."""

    def test_has_permission(self):
        """Pass when token has permission."""
        with patch("gha_utils.renovate.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            passed, msg = check_commit_statuses_permission("owner/repo", "abc123")
            assert passed is True
            assert "access" in msg

    def test_no_permission(self):
        """Pass with warning when no permission (non-fatal)."""
        with patch("gha_utils.renovate.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "gh")
            passed, msg = check_commit_statuses_permission("owner/repo", "abc123")
            # Non-fatal, passes but with warning.
            assert passed is True
            assert "permission" in msg.lower()


class TestRunRenovatePrereqChecks:
    """Tests for run_renovate_prereq_checks function."""

    def test_all_checks_pass(self, tmp_path, monkeypatch, capsys):
        """Return 0 when all checks pass."""
        monkeypatch.chdir(tmp_path)
        with patch("gha_utils.renovate.check_dependabot_security_disabled") as mock_sec:
            with patch(
                "gha_utils.renovate.check_commit_statuses_permission"
            ) as mock_perm:
                mock_sec.return_value = (True, "Disabled")
                mock_perm.return_value = (True, "Has access")
                exit_code = run_renovate_prereq_checks("owner/repo", "abc123")
                assert exit_code == 0

    def test_dependabot_config_exists(self, tmp_path, monkeypatch, capsys):
        """Return 1 when Dependabot config exists."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "dependabot.yaml").touch()
        with patch("gha_utils.renovate.check_dependabot_security_disabled") as mock_sec:
            with patch(
                "gha_utils.renovate.check_commit_statuses_permission"
            ) as mock_perm:
                mock_sec.return_value = (True, "Disabled")
                mock_perm.return_value = (True, "Has access")
                exit_code = run_renovate_prereq_checks("owner/repo", "abc123")
                assert exit_code == 1
                captured = capsys.readouterr()
                assert "::error::" in captured.out

    def test_security_updates_enabled(self, tmp_path, monkeypatch, capsys):
        """Return 1 when Dependabot security updates are enabled."""
        monkeypatch.chdir(tmp_path)
        with patch("gha_utils.renovate.check_dependabot_security_disabled") as mock_sec:
            with patch(
                "gha_utils.renovate.check_commit_statuses_permission"
            ) as mock_perm:
                mock_sec.return_value = (False, "Security updates enabled")
                mock_perm.return_value = (True, "Has access")
                exit_code = run_renovate_prereq_checks("owner/repo", "abc123")
                assert exit_code == 1
                captured = capsys.readouterr()
                assert "::error::" in captured.out
