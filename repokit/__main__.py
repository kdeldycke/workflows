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
"""Allow the module to be run as a CLI. I.e.:

.. code-block:: shell-session

    $ python -m repokit
"""

from __future__ import annotations

from repokit.cli import repokit


def main():
    """Execute the CLI but force its name to not let Click defaults to:

    .. code-block:: shell-session
        $ python -m repokit --version
        python -m repokit, version 4.0.0

    Indirection via this ``main()`` method was `required to reconcile
    <https://github.com/python-poetry/poetry/issues/5981>`_:

        - plain inline package call: ``python -m repokit``,
        - Poetry's script entry point: ``repokit = 'repokit.__main__:main``,
        - Nuitka's main module invocation requirement:
          ``python -m nuitka (...) repokit/__main__.py``

    That way we can deduce all three cases from the entry point.
    """
    repokit(prog_name=repokit.name)


if __name__ == "__main__":
    main()
