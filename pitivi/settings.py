# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
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
import configparser
import os

from gi.repository import GLib
from gi.repository import GObject

from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import unicode_error_dialog


def get_bool_env(var):
    value = os.getenv(var)
    if not value:
        return False
    value = value.lower()
    if value == 'False':
        return False
    if value == '0':
        return False
    else:
        return bool(value)


def get_env_by_type(type_, var):
    """Gets an environment variable.

    Args:
        type_ (type): The type of the variable.
        var (str): The name of the environment variable.

    Returns:
        The contents of the environment variable, or None if it doesn't exist.
    """
    if var is None:
        return None
    if type_ == bool:
        return get_bool_env(var)
    value = os.getenv(var)
    if value:
        return type_(os.getenv(var))
    return None


def get_dir(path, autocreate=True):
    if autocreate and not os.path.exists(path):
        os.makedirs(path)
    return path


def xdg_config_home(autocreate=True):
    """Gets the directory for storing the user's Pitivi configuration."""
    default = os.path.join(GLib.get_user_config_dir(), "pitivi")
    path = os.getenv("PITIVI_USER_CONFIG_DIR", default)
    return get_dir(path, autocreate)


def xdg_data_home(autocreate=True):
    """Gets the directory for storing the user's data: presets, plugins, etc."""
    default = os.path.join(GLib.get_user_data_dir(), "pitivi")
    path = os.getenv("PITIVI_USER_DATA_DIR", default)
    return get_dir(path, autocreate)


def xdg_cache_home(autocreate=True):
    """Gets the Pitivi cache directory."""
    default = os.path.join(GLib.get_user_cache_dir(), "pitivi")
    path = os.getenv("PITIVI_USER_CACHE_DIR", default)
    return get_dir(path, autocreate)


class ConfigError(Exception):
    pass


class Notification(object):
    """A descriptor which emits a signal when set."""

    def __init__(self, attrname):
        self.attrname = "_" + attrname
        self.signame = self.signalName(attrname)

    @staticmethod
    def signalName(attrname):
        return attrname + "Changed"

    def __get__(self, instance, unused):
        return getattr(instance, self.attrname)

    def __set__(self, instance, value):
        setattr(instance, self.attrname, value)
        instance.emit(self.signame)


class GlobalSettings(GObject.Object, Loggable):
    """Pitivi app settings.

    Loads settings from different sources, currently:
    - the local configuration file,
    - environment variables.

    Modules declare which settings they wish to access by calling the
    addConfigOption() class method during initialization.

    Attributes:
        options (dict): The available settings.
        environment (set): The controlled environment variables.
    """

    options = {}
    environment = set()
    defaults = {}

    def __init__(self):
        GObject.Object.__init__(self)
        Loggable.__init__(self)

        self.conf_file_path = os.path.join(xdg_config_home(), "pitivi.conf")
        self._config = configparser.ConfigParser()
        self._readSettingsFromConfigurationFile()
        self._readSettingsFromEnvironmentVariables()

    def _readSettingsFromConfigurationFile(self):
        """Reads the settings from the user configuration file."""
        try:
            self._config.read(self.conf_file_path)
        except UnicodeDecodeError as e:
            self.error("Failed to read %s: %s", self.conf_file_path, e)
            unicode_error_dialog()
            return
        except configparser.ParsingError as e:
            self.error("Failed to parse %s: %s", self.conf_file_path, e)
            return

        for (section, attrname, typ, key, env, value) in self.iterAllOptions():
            if not self._config.has_section(section):
                continue
            if key and self._config.has_option(section, key):
                if typ == int or typ == int:
                    try:
                        value = self._config.getint(section, key)
                    except ValueError:
                        # In previous configurations we incorrectly stored
                        # ints using float values.
                        value = int(self._config.getfloat(section, key))
                elif typ == float:
                    value = self._config.getfloat(section, key)
                elif typ == bool:
                    value = self._config.getboolean(section, key)
                else:
                    value = self._config.get(section, key)
                setattr(self, attrname, value)

    @classmethod
    def readSettingSectionFromFile(self, cls, section):
        """Reads a particular section of the settings file.

        Use this if you dynamically determine settings sections/keys at runtime.
        Otherwise, the settings file would be read only once, at the
        initialization phase of your module, and your config sections would
        never be read, thus values would be reset to defaults on every startup
        because GlobalSettings would think they don't exist.
        """
        if cls._config.has_section(section):
            for option in cls._config.options(section):
                # We don't know the value type in advance, just try them all.
                try:
                    value = cls._config.getfloat(section, option)
                except:
                    try:
                        value = cls._config.getint(section, option)
                    except:
                        try:
                            value = cls._config.getboolean(section, option)
                        except:
                            value = cls._config.get(section, option)

                setattr(cls, section + option, value)

    def _readSettingsFromEnvironmentVariables(self):
        """Reads settings from their registered environment variables."""
        for section, attrname, typ, key, env, value in self.iterAllOptions():
            if not env:
                # This option does not have an environment variable name.
                continue
            var = get_env_by_type(typ, env)
            if var is not None:
                setattr(self, attrname, var)

    def _writeSettingsToConfigurationFile(self):
        for (section, attrname, typ, key, env_var, value) in self.iterAllOptions():
            if not self._config.has_section(section):
                self._config.add_section(section)
            if key:
                if value is not None:
                    self._config.set(section, key, str(value))
                else:
                    self._config.remove_option(section, key)
        try:
            with open(self.conf_file_path, 'w') as file:
                self._config.write(file)
        except (IOError, OSError) as e:
            self.error("Failed to write to %s: %s", self.conf_file_path, e)

    def storeSettings(self):
        """Writes settings to the user's local configuration file.

        Only those settings which were added with a section and a key value are
        stored.
        """
        self._writeSettingsToConfigurationFile()

    def iterAllOptions(self):
        """Iterates over all registered options."""
        for section, options in list(self.options.items()):
            for attrname, (typ, key, environment) in list(options.items()):
                yield section, attrname, typ, key, environment, getattr(self, attrname)

    def isDefault(self, attrname):
        return getattr(self, attrname) == self.defaults[attrname]

    def setDefault(self, attrname):
        """Resets the specified setting to its default value."""
        setattr(self, attrname, self.defaults[attrname])

    @classmethod
    def addConfigOption(cls, attrname, type_=None, section=None, key=None,
                        environment=None, default=None, notify=False,):
        """Adds a configuration option.

        This function should be called during module initialization, before
        the config file is actually read. By default, only options registered
        beforehand will be loaded.

        If you want to add configuration options after initialization,
        use the `readSettingSectionFromFile` method to force reading later on.

        Args:
            attrname (str): The attribute of this class for accessing the option.
            type_ (Optional[type]): The type of the attribute. Unnecessary if a
                `default` value is specified.
            section (Optional[str]): The section of the config file under which
                this option is saved. This section must have been added with
                addConfigSection(). Not necessary if `key` is not given.
            key (Optional[str]): The key under which this option is to be saved.
                By default the option will not be saved.
            notify (Optional[bool]): Whether this attribute should emit
                signals when modified. By default signals are not emitted.
        """
        if section and section not in cls.options:
            raise ConfigError("You must add the section `%s` first" % section)
        if key and not section:
            raise ConfigError("You must specify a section for key `%s`" % key)
        if section and key in cls.options[section]:
            raise ConfigError("Key `%s` is already in use" % key)
        if hasattr(cls, attrname):
            raise ConfigError("Attribute `%s` is already in use" % attrname)
        if environment and environment in cls.environment:
            raise ConfigError("Env var `%s` is already in use" % environment)
        if not type_ and default is None:
            raise ConfigError("Attribute `%s` must have a type or a default" %
                              attrname)
        if not type_:
            type_ = type(default)
        if notify:
            notification = Notification(attrname)
            setattr(cls, attrname, notification)
            setattr(cls, "_" + attrname, default)
            GObject.signal_new(notification.signame,
                               cls,
                               GObject.SIGNAL_RUN_LAST,
                               None,
                               ())
        else:
            setattr(cls, attrname, default)
        if section and key:
            cls.options[section][attrname] = type_, key, environment
        cls.environment.add(environment)
        cls.defaults[attrname] = default

    @classmethod
    def addConfigSection(cls, section):
        """Adds a section to the local config file.

        Args:
            section (str): The section name.

        Raises:
            ConfigError: If the section already exists.
        """
        if section in cls.options:
            raise ConfigError("Duplicate Section \"%s\"." % section)
        cls.options[section] = {}

    @classmethod
    def notifiesConfigOption(cls, attrname):
        """Checks whether a signal is emitted when the setting is changed.

        Args:
            attrname (str): The attribute name used to access the setting.

        Returns:
            bool: True when the setting emits a signal when changed,
                False otherwise.
        """
        signal_name = Notification.signalName(attrname)
        return bool(GObject.signal_lookup(signal_name, cls))
