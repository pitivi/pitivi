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

from gettext import gettext as _

# FIXME : We need a registry of all available formatters

def load_project(uri, formatter=None, missinguricallback=None):
    """
    Load the project from the given location.

    If specified, use the given formatter.

    @type uri: L{str}
    @param uri: The location of the project. Needs to be an
    absolute URI.
    @type formatter: L{Formatter}
    @param formatter: If specified, try loading the project with that
    L{Formatter}. If not specified, will try all available L{Formatter}s.
    @raise FormatterLoadError: If the location couldn't be properly loaded.
    @param missinguricallback: A callback that will be used if some
    files to load can't be found anymore. The callback shall call the
    formatter's addMapping() method with the moved location.
    @type missinguricallback: C{callable}
    @return: The project. The caller needs to ensure the loading is
    finished before using it. See the 'loaded' property and signal of
    L{Project}.
    @rtype: L{Project}.
    """
    raise NotImplementedError

def save_project(project, uri, formatter=None, overwrite=False):
    """
    Save the L{Project} to the given location.

    If specified, use the given formatter.

    @type project: L{Project}
    @param project: The L{Project} to save.
    @type uri: L{str}
    @param uri: The location to store the project to. Needs to
    be an absolute URI.
    @type formatter: L{Formatter}
    @param formatter: The L{Formatter} to use to store the project if specified.
    If it is not specified, then it will be saved at its original format.
    @param overwrite: Whether to overwrite existing location.
    @type overwrite: C{bool}
    @raise FormatterSaveError: If the file couldn't be properly stored.

    @see: L{Formatter.saveProject}
    """
    if formatter == None:
        if project.format:
            formatter == project.format
        else:
            from pitivi.formatters.etree import ElementTreeFormatter
            formatter = ElementTreeFormatter()
    formatter.saveProject(project, uri, overwrite)

def can_handle_location(uri):
    """
    Detects whether the project at the given location can be loaded.

    @type uri: L{str}
    @param uri: The location of the project. Needs to be an
    absolute URI.
    @return: Whether the location contains a valid L{Project}.
    @rtype: L{bool}
    """

    for klass, name, exts in list_formats():
        if klass.canHandle(uri):
            return True

def list_formats():
    """
    Returns a sequence of available project file formats

    @return: a sequence of 3-tuples (class, name, extensions) representing available
    file formats, where name is a user-readable name, and extensions is a
    sequence of extensions for this format ('.' omitted).
    """
    from pitivi.formatters.etree import ElementTreeFormatter
    from pitivi.formatters.playlist import PlaylistFormatter
    return [
        (ElementTreeFormatter, _("PiTiVi Native (XML)"), ('xptv',)),
        (PlaylistFormatter, _("Playlist format"), ('pls', ))
        ]

def get_formatter_for_uri(uri):
    """
    Returns an Formatter object that can parse the given project file

    @type uri:L{str}
    @param uri: The location of the project file
    @return: an instance of a Formatter, or None
    """
    from pitivi.formatters.etree import ElementTreeFormatter

    for klass, name, exts in list_formats():
        if klass.canHandle(uri):
            return klass()
