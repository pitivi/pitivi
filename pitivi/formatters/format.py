# PiTiVi , Non-linear video editor
#
#       formatter.format
#
# Copyright (c) 2009, Edward Hervey <bilboed@bilboed.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""
High-level tools for using Formatters
"""

def load_project(location, formatter=None):
    """
    Load the project from the given location.

    If specified, use the given formatter.

    @type location: L{str}
    @param location: The location of the project. Needs to be an
    absolute URI.
    @type formatter: C{Formatter}
    @param formatter: If specified, try loading the project with that
    C{Formatter}. If not specified, will try all available C{Formatter}s.
    @raise FormatterLoadError: If the location couldn't be properly loaded.
    @return: The loaded C{Project}
    """
    pass

def save_project(project, location, formatter=None):
    """
    Save the C{Project} to the given location.

    If specified, use the given formatter.

    @type project: C{Project}
    @param project: The C{Project} to save.
    @type location: L{str}
    @param location: The location to store the project to. Needs to
    be an absolute URI.
    @type formatter: C{Formatter}
    @param formatter: The C{Formatter} to use to store the project if specified.
    If it is not specified, then it will be saved at its original format.
    @raise FormatterStoreError: If the file couldn't be properly stored.
    @return: Whether the file was successfully stored
    @rtype: L{bool}
    """
    pass

def can_handle_location(location):
    """
    Detects whether the project at the given location can be loaded.

    @type location: L{str}
    @param location: The location of the project. Needs to be an
    absolute URI.
    @return: Whether the location contains a valid C{Project}.
    @rtype: L{bool}
    """
    pass
