# pylint: disable=missing-docstring
# -*- coding: utf-8 -*-
# Copyright (c) 2017, Fabian Orccon <cfoch.fabian@gmail.com>
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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
import os

from gi.repository import GObject
from gi.repository import Peas

from pitivi.configure import get_plugins_dir
from pitivi.configure import get_user_plugins_dir


class API(GObject.GObject):
    """Interface that gives access to all the objects inside Pitivi."""

    def __init__(self, app):
        GObject.GObject.__init__(self)
        self.app = app


class PluginManager:
    """Pitivi Plugin Manager to handle a set of plugins.

    Attributes:
        DEFAULT_LOADERS (tuple): Default loaders used by the plugin manager. For
            possible values see
            https://developer.gnome.org/libpeas/stable/PeasEngine.html#peas-engine-enable-loader
    """

    DEFAULT_LOADERS = ("python3", )

    def __init__(self, app):
        self.app = app
        self.engine = Peas.Engine.get_default()

        for loader in self.DEFAULT_LOADERS:
            self.engine.enable_loader(loader)

        self._setup_plugins_dir()
        self._setup_extension_set()

    @property
    def plugins(self):
        """Gets the engine's plugin list."""
        return self.engine.get_plugin_list()

    def _setup_extension_set(self):
        plugin_iface = API(self.app)
        self.extension_set =\
            Peas.ExtensionSet.new_with_properties(self.engine,
                                                  Peas.Activatable,
                                                  ["object"],
                                                  [plugin_iface])
        self.extension_set.connect("extension-removed",
                                   self.__extension_removed_cb)
        self.extension_set.connect("extension-added",
                                   self.__extension_added_cb)

    def _setup_plugins_dir(self):
        plugins_dir = get_plugins_dir()
        user_plugins_dir = get_user_plugins_dir()
        if os.path.exists(plugins_dir):
            self.engine.add_search_path(plugins_dir)
        if os.path.exists(plugins_dir):
            self.engine.add_search_path(user_plugins_dir)

    @staticmethod
    def __extension_removed_cb(unused_set, unused_plugin_info, extension):
        extension.deactivate()

    @staticmethod
    def __extension_added_cb(unused_set, unused_plugin_info, extension):
        extension.activate()
