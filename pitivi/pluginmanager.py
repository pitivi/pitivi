# PiTiVi , Non-linear video editor
#
#       pitivi/pluginmanager.py
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

"""
Plugin Manager
"""

import os
import os.path
import stat
import shutil
import inspect
import imp
try:
    import cPickle as pickle
except:
    import pickle
import pkg_resources
import gtk
import zope.interface.verify

from pitivi.signalinterface import Signallable
import pitivi.plugincore as plugincore

class PluginManager(Signallable):
    """
    Manages plugins in a centralized way.

    Assolves the duties of installing, uninstalling and updating plugins.

    Keeps a repository of categorized plugins, that can be queried by the main
    application (or by plugins themself) in order to find items compatible with
    their extension points.

    Signals
    void plugin-enabled-changed(plugin_names)
        plugin.enabled state is changed
        *plugin_names - list of plugin names whose enabled field changed
    void plugin-installed(plugin_name)
        a new plugin is successfully installed
        *plugin_name - name of the new plugin
    void plugin-uninstalled(plugin_name)
        an existent plugin was uninstalled
        *plugin_name - name of the plugin uninstalled

    """

    __signals__ = {
        "plugin-enabled-changed" : ["plugin_names"],
        "plugin-installed" : ["plugin_name"],
        "plugin-uninstalled" : ["plugin_name"],

        }

    def __init__(self, local_plugin_path, settings_path):
        """
        Initialize a new plugin manager

        @param local_plugin_path: local path where new plugins will be installed
        @param settings_path: path where all plugin settings are stored
        """

        # plugins are collected in a bag (a structure relatng 1->many)
        # {"my_plugin":{"plugin":plugin_object, "filename":"/home/luca/plugins/my_plugin.py"}}
        self.pluginbag = {}

        # Store plugin repositiories in the instance ensuring they are expressed
        # as absolute paths.
        self.local_plugin_path = os.path.abspath(local_plugin_path)
        self.plugin_paths = [ self.local_plugin_path, ]
        self.settings_path = os.path.abspath(settings_path)
        self.collect()

    def _match(self, plugin, name=None, interface=plugincore.IPlugin, category=None, only_enabled=False):
        """
        Check if plugin matches the search criteria

        @param plugin: item to match
        @param name: the exact name of the plugin (case sensitive)
        @param interface: interface the plugin must provide
        @param category: category the plugin must belong
        @param only_enabled: if True search only among enabled plugins

        @return: True if plugin matches all the search criteria, False otherwise
        """

        if name and plugin.name != name:
            return False
        elif interface and not interface.providedBy(plugin):
            return False
        elif category and plugin.category != category:
            return False
        elif only_enabled and not plugin.enabled:
            return False
        else:
            return True

    def _get_settings_filename(self, plugin):
        """
        Compute the settings filename for given plugin, by finding plugin's
        filename and replacing extension with .conf

        @param plugin: plugin from which to retrieve the settings filemane
        @return: full path to the plugin settings filename
        """

        plugin_filename = self.pluginbag[plugin.name]["filename"]

        #Extract plugin base_name
        plugin_basename = os.path.basename(plugin_filename)

        #strip file extension from plugin basename ("myplugin.py" -> "myplugin")
        plugin_basename = plugin_basename[:plugin_basename.rfind(".")]

        #assemble and return the configuration file fullpath
        return os.path.join(self.settings_path, plugin_basename + ".conf")

    def _get_settings(self, plugin):
        """
        Get the plugin settings dictionary from disk

        @param plugin: plugin for which to retrieve settings from disk
        @return: settings dictionary, None if not found
        """

        # load only if the plugin has stored settings
        settings_filename = self._get_settings_filename(plugin)
        if not os.path.exists(settings_filename):
            return None

        # deserialize settings dictionary via pickle
        try:
            settings_file = open(settings_filename, "rb")
            settings = pickle.load(settings_file)
            return settings
        finally:
            settings_file.close()

    def _is_valid_plugin_class(self, plugin_class):
        """
        Check if plugin class correctly implements the IPlugin interface

        @param plugin_class: class to validate
        @return: True if class is a valid plugin, False otherwise
        """

        try:
            # ask zope to validate the class against IPlugin interface
            zope.interface.verify.verifyClass(plugincore.IPlugin, plugin_class)

            # verify required class fields (not covered by zope verifyClass)
            assert hasattr(plugin_class, "name") and plugin_class.name
            assert hasattr(plugin_class, "description")
            assert hasattr(plugin_class, "version")
        except:
            return False

        return True

    def alreadyLoaded(self, plugin):
        """
        Check if the plugin is already loaded

        @param plugin: item to check the loaded status
        @return: True if plugin is among loaded, False otherwise
        """

        if self.pluginbag.has_key(plugin.name):
            return self.pluginbag[plugin.name]["plugin"]

    def loadPluginClass(self, filename, directory):
        """
        Load the plugin class fron a given file.

        @param filename: name of the file containing the plugin.
        @param directory: full path to the directory containing the file

        @return: plugin class if successfully loaded, None otherwise
        """
        plugin_class = None

        if filename.endswith(".py"):
            # file is a python module, inspect it for the plugin class
            module_name = os.path.splitext(filename)[0]
            module_file, fullname, description = imp.find_module(module_name, [directory])

            try:
                try:
                    module = imp.load_module(module_name, module_file, fullname, description)

                    # return all classes in the module as a tuple (name, class)
                    for member_class in inspect.getmembers(module, inspect.isclass):
                        # look for a class named like the module (case insensitive)
                        if member_class[0].lower() == module_name.lower():
                            plugin_class = member_class[1]
                finally:
                    if module_file:
                        module_file.close()
            except Exception, e:
                raise plugincore.InvalidPluginClassError(filename)

        elif filename.endswith(".egg"):
            # file is an egg, ask its entry point for the plugin class
            fullname = os.path.join(directory, filename)

            pkg_resources.working_set.add_entry(fullname)
            dist_generator = pkg_resources.find_distributions(fullname)
            for dist in dist_generator:
                try:
                    plugin_class = dist.load_entry_point("pitivi.plugins", "plugin")
                except Exception, e :
                    raise plugincore.InvalidPluginClassError(filename)

        else:
            # file has an unknown extension
            raise plugincore.InvalidPluginError(filename)

        # check we found the plugin class and ensure it implements IPlugin
        if not self._is_valid_plugin_class(plugin_class):
            raise plugincore.IPluginNotImplementedError(filename)

        return plugin_class

    def collect(self):
        """ Scan plugin paths and load plugins """

        for path in self.plugin_paths:
            if not os.path.isdir(path):
                continue
            for filename in os.listdir(path):
                if not(filename.endswith(".egg") or filename.endswith(".py")):
                    continue
                # try loading the plugin from filename
                plugin_class = self.loadPluginClass(filename, path)
                if plugin_class and not self.alreadyLoaded(plugin_class):
                    # insert the new plugin entry filled only with filename
                    self.pluginbag[plugin_class.name] = {\
                        "plugin": None, "filename": os.path.join(path,filename)}

                    # create an instance of the plugin
                    plugin = plugin_class(manager=self)

                    # complete the registration procdeure if all went well
                    if plugin and plugincore.IPlugin.providedBy(plugin):
                        self.pluginbag[plugin.name]["plugin"] = plugin
                    else:
                        del self.pluginbag[plugin.name]

                # process gtk events while loading plugins
                while gtk.events_pending():
                    gtk.main_iteration()

    def getPlugins(self, name=None, interface=plugincore.IPlugin, category=None, only_enabled=False):
        """
        Return the list of plugins matching the search criteria

        @param name: the exact name of the plugin (case sensitive)
        @param interface: interface the plugin must provide
        @param category: category the plugin must belong
        @param only_enabled: if True search only among enabled plugins

        @return: the list of plugins matching all the search criteria
        """
        return [item["plugin"] for item in self.pluginbag.itervalues() if \
                self._match(item["plugin"], name, interface, category, only_enabled)]

    def enablePlugins(self, name=None, interface=plugincore.IPlugin, category=None):
        """
        Enable plugins matching all the search criteria

        @param name: the exact name of the plugin (case sensitive)
        @param interface: interface the plugin must provide
        @param category: category the plugin must belong
        """
        selection = self.getPlugins(name, interface, category, False)

        for plugin in selection:
            plugin.enabled = True

        self.emit('plugin-enabled-changed', [plugin.name for plugin in selection])

    def disablePlugins(self, name=None, interface=plugincore.IPlugin, category=None):
        """
        Disable plugins matching all the search criteria

        @param name: the exact name of the plugin (case sensitive)
        @param interface: interface the plugin must provide
        @param category: category the plugin must belong
        """

        selection = self.getPlugins(name, interface, category, True)

        for plugin in selection:
            plugin.enabled = False

        self.emit('plugin-enabled-changed', [plugin.name for plugin in selection])

    def install(self, filename, repository_path):
        """
        Install a new plugin from filename into the specified repository

        @param filename: full path to the file containing the new plugin
        @param repository_path: Directory to store the new plugin

        @return: plugin instance if installed, None otherwise
        """

        if not (filename.endswith(".egg") or filename.endswith(".py")):
            print "File must be a .py or a .egg"

        plugin_class = self.loadPluginClass(os.path.basename(filename), \
                                            os.path.dirname(filename))

        if not plugin_class:
            raise plugincore.InvalidPluginError(filename)
        elif self.alreadyLoaded(plugin_class):
            raise plugincore.DuplicatePluginError(self.alreadyLoaded(plugin_class), plugin_class)
        else:
            # place plugin into repository and enroll it among the available
            shutil.copy(filename, repository_path)

            # insert the new plugin filename entry
            new_filename = os.path.join(os.path.abspath(repository_path), \
                                        os.path.basename(filename))
            self.pluginbag[plugin_class.name] = {\
                "plugin": None, "filename": new_filename}

            # create an instance of the plugin
            plugin = plugin_class(manager=self)

            # complete the registration procdeure if all went well
            if plugin and plugincore.IPlugin.providedBy(plugin):
                self.pluginbag[plugin.name]["plugin"] = plugin
                self.emit("plugin-installed", plugin.name)
            else:
                del self.pluginbag[plugin.name]

            return plugin

    def update(self, filename, repository_path):
        """
        Overwrite an existent plugin with the one contained in filename

        @param filename: Path to the .egg or .py file containing the new plugin
        @param repository_path: Directory to store the new plugin

        @return: plugin if installed, None otherwise
        """

        new_plugin_class = self.loadPluginClass(os.path.basename(filename), \
                                                os.path.dirname(filename))
        old_plugin = self.alreadyLoaded(new_plugin_class)
        old_settings = self._get_settings(old_plugin)

        if old_plugin and new_plugin_class:
            # remove the old_plugin and install the new_plugin
            old_enabled = old_plugin.enabled
            self.uninstall(old_plugin)
            new_plugin = self.install(filename, repository_path)

            # ask the new plugin to import settings
            if plugincore.IUpdateSettings.providedBy(new_plugin) and old_settings:
                new_plugin.update_settings(old_settings)

            # enable new_plugin if old_plugin was enabled
            if new_plugin and old_enabled:
                new_plugin.enabled = old_enabled

            return new_plugin

    def uninstall(self, plugin):
        """
        Uninstall a plugin

        @param plugin: plugin to be uninstalled
        """
        item = self.pluginbag[plugin.name]
        settings_filename = self._get_settings_filename(item["plugin"])

        # disable the plugin if running
        item["plugin"].enabled = False

        # phisically remove the plugin and settings files from disk
        try:
            name = plugin.name
            os.remove(item["filename"])
            if os.path.exists(settings_filename) :
                os.remove(settings_filename)
            del self.pluginbag[plugin.name]
            self.emit("plugin-uninstalled", name)
        except:
            raise plugincore.RemovePluginError(item["filename"])


    def canUninstall(self, plugin):
        """
        Check if current user has permission to uninstall plugin
        by ensuring that file owner's user_id is equal to current one.

        @param plugin: plugin to check if removable
        @return: True if user may uninstall the plugin, none otherwise
        """

        item = self.pluginbag[plugin.name]
        return os.stat(item["filename"])[stat.ST_UID] == os.getuid()

    def loadSettings(self, plugin):
        """
        Loads plugin settings dictionary from disk using pickle

        @param plugin: plugin for which you want settings to be loaded
        """

        settings = self._get_settings(plugin)
        if settings:
            plugin.settings = settings

    def saveSettings(self, plugin):
        """
        Store plugin settings dictionary to disk using pickle

        @param plugin: plugin for which you want settings to be saved
        """

        # save only if the plugin has settings
        if not plugin.settings:
            return

        # serialize settings dictionary via pickle
        settings_filename = self._get_settings_filename(plugin)
        try:
            settings_file = open(settings_filename, "wb")
            pickle.dump(plugin.settings, settings_file)
        finally:
            settings_file.close()
