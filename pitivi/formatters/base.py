# PiTiVi , Non-linear video editor
#
#       formatter.base
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
Base Formatter classes
"""

from pitivi.project import Project

class FormatterError(Exception):
    pass

class FormatterLoadError(FormatterError):
    pass

class FormatterSaveError(FormatterError):
    pass

# FIXME : How do we handle interaction with the UI ??
# Do we blindly load everything and let the UI figure out what's missing from
# the loaded project ?

class Formatter(object):
    """
    Provides convenience methods for storing and loading
    Project files.

    @cvar description: Description of the format.
    @type description: C{str}
    """

    description = "Description of the format"

    def loadProject(self, location):
        """
        Loads the project from the given location.

        @type location: L{str}
        @param location: The location of a file. Needs to be an absolute URI.

        @rtype: C{Project}
        @return: The C{Project}
        @raise FormatterLoadError: If the file couldn't be properly loaded.
        """
        raise FormatterLoadError("No Loading feature")

    def saveProject(self, project, location):
        """
        Saves the given project to the given location.

        @type project: C{Project}
        @param project: The Project to store.
        @type location: L{str}
        @param location: The location where to store the project. Needs to be
        an absolute URI.
        @raise FormatterSaveError: If the file couldn't be properly stored.
        """
        raise FormatterSaveError("No Saving feature")

    def canHandle(self, location):
        """
        Can this Formatter load the project at the given location.

        @type location: L{str}
        @param location: The location. Needs to be an absolute C{URI}.
        @rtype: L{bool}
        @return: True if this Formatter can load the C{Project}.
        """
        raise NotImplementedError

class LoadOnlyFormatter(Formatter):
    def saveProject(self, project, location):
        raise FormatterSaveError("No Saving feature")


class SaveOnlyFormatter(Formatter):
    def saveProject(self, project, location):
        raise FormatterSaveError("No Saving feature")


class DefaultFormatter(Formatter):

    description = "PiTiVi default file format"

    pass
