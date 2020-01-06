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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
"""PluginManager for loading Pitivi plugins."""
import os
from enum import IntEnum
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Peas

from pitivi.configure import get_plugins_dir
from pitivi.configure import get_user_plugins_dir
from pitivi.settings import GlobalSettings
from pitivi.utils.loggable import Loggable


GlobalSettings.add_config_section("plugins")
GlobalSettings.add_config_option("ActivePlugins",
                                 section="plugins", key="active-plugins",
                                 default=[])


class API(GObject.GObject):
    """Interface that gives access to all the objects inside Pitivi."""

    def __init__(self, app):
        GObject.GObject.__init__(self)
        self.app = app


class PluginType(IntEnum):
    """Types of plugins we support, depending on their directory location."""

    # pylint: disable=comparison-with-callable,inconsistent-return-statements,no-else-return

    SYSTEM = 1
    USER = 2

    def __str__(self):
        if self.value == PluginType.USER:
            return _("User plugins")
        elif self.value == PluginType.SYSTEM:
            return _("System plugins")

    def get_dir(self):
        """Returns the directory where this type of plugins can be found."""
        if self.value == PluginType.USER:
            return get_user_plugins_dir()
        elif self.value == PluginType.SYSTEM:
            return get_plugins_dir()


class PluginManager(Loggable):
    """Pitivi Plugin Manager to handle a set of plugins.

    Attributes:
        DEFAULT_LOADERS (tuple): Default loaders used by the plugin manager. For
            possible values see
            https://developer.gnome.org/libpeas/stable/PeasEngine.html#peas-engine-enable-loader
    """

    DEFAULT_LOADERS = ("python3", )

    def __init__(self, app):
        Loggable.__init__(self)
        self.app = app
        self.engine = Peas.Engine.get_default()
        # Many plugins need access to the main window. However, by the time a
        # plugin is loaded from settings (as soon Pitivi application starts),
        # the main window doesn't exist yet. So we load plugins from settings
        # after the main window is added.
        self.app.connect("window-added", self.__window_added_cb)

        for loader in self.DEFAULT_LOADERS:
            self.engine.enable_loader(loader)

        self._setup_plugins_dir()
        self._setup_extension_set()

    @property
    def plugins(self):
        """Gets the engine's plugin list."""
        return self.engine.get_plugin_list()

    @classmethod
    def get_plugin_type(cls, plugin_info):
        """Gets the PluginType for the specified Peas.PluginInfo."""
        paths = [plugin_info.get_data_dir(), get_plugins_dir()]
        if os.path.commonprefix(paths) == get_plugins_dir():
            return PluginType.SYSTEM
        return PluginType.USER

    def get_extension(self, module_name):
        """Gets the extension identified by the specified name.

        Args:
            module_name (str): The name of the extension.

        Returns:
            The extension if exists. Otherwise, `None`.
        """
        plugin = self.get_plugin_info(module_name)
        if not plugin:
            return None

        return self.extension_set.get_extension(plugin)

    def get_plugin_info(self, module_name):
        """Gets the plugin info for the specified plugin name.

        Args:
            module_name (str): The name from the .plugin file of the module.

        Returns:
            Peas.PluginInfo: The plugin info if it exists. Otherwise, `None`.
        """
        for plugin in self.plugins:
            if plugin.get_module_name() == module_name:
                return plugin
        return None

    def _load_plugins(self):
        """Loads plugins from settings."""
        plugin_names = self.app.settings.ActivePlugins
        for plugin_name in plugin_names:
            plugin_info = self.engine.get_plugin_info(plugin_name)
            if plugin_info not in self.plugins:
                self.warning("Plugin missing: %s", plugin_name)
                continue
            self.engine.load_plugin(plugin_info)

    def _setup_extension_set(self):
        plugin_iface = API(self.app)
        self.extension_set = Peas.ExtensionSet.new(self.engine,
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
        if os.path.exists(user_plugins_dir):
            self.engine.add_search_path(user_plugins_dir)

    @staticmethod
    def __extension_removed_cb(unused_set, unused_plugin_info, extension):
        extension.deactivate()

    @staticmethod
    def __extension_added_cb(unused_set, unused_plugin_info, extension):
        extension.activate()

    def __window_added_cb(self, unused_app, unused_window):
        """Handles the addition of a window to the application."""
        self._load_plugins()
        self.engine.connect("notify::loaded-plugins", self.__loaded_plugins_cb)
        self.app.disconnect_by_func(self.__window_added_cb)

    def __loaded_plugins_cb(self, engine, unused_pspec):
        """Handles the changing of the loaded plugin list."""
        self.app.settings.ActivePlugins = engine.get_property("loaded-plugins")
