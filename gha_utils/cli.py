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

from click_extra import extra_group

from .changelog import Changelog
from .mailmap import Mailmap
from .metadata import Metadata


@extra_group
def gha_utils():
    pass


@gha_utils.command(short_help="Produce metadata")
def metadata():
    # Output metadata with GitHub syntax.
    Metadata().write_metadata()


@gha_utils.command(short_help="Update changelog")
def changelog():
    Changelog().update()


@gha_utils.command(short_help="Update .mailmap")
def mailmap():
    Mailmap().update()
