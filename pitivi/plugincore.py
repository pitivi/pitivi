# PiTiVi , Non-linear video editor
#
#       pitivi/plugincore.py
#
# Copyright (c) 2007, Luca Della Santina <dellasantina@farm.unipi.it>
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

from zope.interface import Interface, Attribute

"""
PiTiVi plugin system
"""

# Interfaces
class IPlugin(Interface):
    """ Every plugin must implement this interface """

    name = Attribute(""" Name of the plugin """)
    category = Attribute(""" Category of the plugin i.e. Video """)
    description = Attribute(""" Description of the plugin's behaviour """)
    version = Attribute(""" Version of the plugin """)
    authors = Attribute(""" Authors of the plugin, separated by comma """)

    settings = Attribute(""" Plugin settings """)
    enabled = Attribute(""" Retrieve or toggle plugin status """)

    def __call__(self):
        """ Initialize the plugin passing a reference to the plugin manager """

class IConfigurable(Interface):
    """Allow user customization of plugin settings """

    def configure(self):
        """ Display preferences dialog """

class IUpdateSettings(Interface):
    """ Allow importing settings from different versions of the plugin """

    def update_settings(self):
        """ import settings from a different version """

# Exceptions
class PluginError(Exception):
    pass

class InvalidPluginError(PluginError):
    def __init__(self, filename):
        self.filename = filename

class InvalidPluginClassError(InvalidPluginError):
    pass

class IPluginNotImplementedError(InvalidPluginError):
    pass

class DuplicatePluginError(PluginError):
    def __init__(self, old_plugin, new_plugin):
        self.old_plugin = old_plugin
        self.new_plugin = new_plugin

class RemovePluginError(PluginError):
    def __init__(self, filename):
        self.filename = filename
