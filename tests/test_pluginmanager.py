# -*- coding: utf-8 -*-
# Pitivi video editor
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
"""Tests for the pluginmanager module."""
import os
import tempfile
from unittest import mock

from gi.repository import GObject

from pitivi.pluginmanager import PluginManager
from pitivi.settings import GlobalSettings
from tests import common


class TestPluginManager(common.TestCase):
    """Tests for the PluginManager class."""

    def test_load_plugins_from_settings(self):
        """Checks if the plugin manager loads plugins from GlobalSettings."""
        class App(GObject.Object):
            """A representation of the Pitivi Application for test purposes."""

            __gsignals__ = {
                "window-added": (GObject.SignalFlags.RUN_LAST, None, (object, ))
            }

            def __init__(self):
                GObject.Object.__init__(self)
                self.settings = GlobalSettings()

        with mock.patch("pitivi.pluginmanager.get_plugins_dir") as get_plugins_dir,\
                mock.patch("pitivi.pluginmanager.get_user_plugins_dir") as get_user_plugins_dir,\
                tempfile.TemporaryDirectory() as temp_dir:

            plugin_content = ("[Plugin]\n"
                              "Module=pluginA\n"
                              "Name=PluginA\n"
                              "Loader=Python3")

            py_content = ("from gi.repository import GObject\n"
                          "class PluginA(GObject.GObject):\n"
                          "    def __init__(self):\n"
                          "        GObject.Object.__init__(self)")

            with open(os.path.join(temp_dir, "pluginA.plugin"), "w", encoding="UTF-8") as plugin_file:
                plugin_file.write(plugin_content)
            with open(os.path.join(temp_dir, "pluginA.py"), "w", encoding="UTF-8") as py_file:
                py_file.write(py_content)

            get_plugins_dir.return_value = temp_dir
            get_user_plugins_dir.return_value = temp_dir

            app = App()
            app.settings.ActivePlugins = ["pluginA"]

            plugin_manager = PluginManager(app)
            app.emit("window-added", None)

            loaded_plugins = plugin_manager.engine.get_loaded_plugins()
            self.assertCountEqual(loaded_plugins, app.settings.ActivePlugins)
