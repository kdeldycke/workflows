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

"""Bundled data files for gha-utils.

This package contains label configurations, labeller rules, bumpversion template,
and workflow templates that are copied from ``.github/`` at build time via the
``[tool.uv.build-backend.force-include]`` configuration in ``pyproject.toml``.

The source files live in ``.github/`` for linting and formatting, but are
bundled here at package build time to be accessible via ``importlib.resources``.
"""
