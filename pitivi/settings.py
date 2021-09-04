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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
import configparser
import os

from gi.repository import Gdk
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


def xdg_config_home(*subdirs):
    """Gets the directory for storing the user's Pitivi configuration."""
    default_base = os.path.join(GLib.get_user_config_dir(), "pitivi")
    base = os.getenv("PITIVI_USER_CONFIG_DIR", default_base)
    path = os.path.join(base, *subdirs)
    os.makedirs(path, exist_ok=True)
    return path


def xdg_data_home(*subdirs):
    """Gets the directory for storing the user's data: presets, plugins, etc."""
    default_base = os.path.join(GLib.get_user_data_dir(), "pitivi")
    base = os.getenv("PITIVI_USER_DATA_DIR", default_base)
    path = os.path.join(base, *subdirs)
    os.makedirs(path, exist_ok=True)
    return path


def xdg_cache_home(*subdirs):
    """Gets the Pitivi cache directory."""
    default_base = os.path.join(GLib.get_user_cache_dir(), "pitivi")
    base = os.getenv("PITIVI_USER_CACHE_DIR", default_base)
    path = os.path.join(base, *subdirs)
    os.makedirs(path, exist_ok=True)
    return path


class ConfigError(Exception):
    pass


class Notification:
    """A descriptor which emits a signal when set."""

    def __init__(self, attrname):
        self.attrname = "_" + attrname
        self.signame = self.signal_name(attrname)

    @staticmethod
    def signal_name(attrname):
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
    add_config_option() class method during initialization.

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
        self._read_settings_from_configuration_file()
        self._read_settings_from_environment_variables()

    def reload_attribute_from_file(self, section, attrname):
        """Reads and sets an attribute from the configuration file.

        Pitivi's default behavior is to set attributes from the configuration
        file when starting and to save those attributes back to the file when
        exiting the application. You can use this method when you need to
        read an attribute during runtime (in the middle of the process).
        """
        if section in self.options:
            if attrname in self.options[section]:
                type_, key, _ = self.options[section][attrname]
                try:
                    value = self._read_value(section, key, type_)
                except configparser.NoSectionError:
                    return
                setattr(self, attrname, value)

    def _read_value(self, section, key, type_):
        if type_ == int:
            try:
                value = self._config.getint(section, key)
            except ValueError:
                # In previous configurations we incorrectly stored
                # ints using float values.
                value = int(self._config.getfloat(section, key))
        elif type_ == float:
            value = self._config.getfloat(section, key)
        elif type_ == bool:
            value = self._config.getboolean(section, key)
        elif type_ == list:
            tmp_value = self._config.get(section, key)
            value = [token.strip() for token in tmp_value.split("\n") if token]
        elif type_ == Gdk.RGBA:
            value = self.get_rgba(section, key)
        else:
            value = self._config.get(section, key)
        return value

    def _write_value(self, section, key, value):
        if isinstance(value, list):
            value = "\n" + "\n".join(value)
            self._config.set(section, key, value)
        elif isinstance(value, Gdk.RGBA):
            self.set_rgba(section, key, value)
        else:
            self._config.set(section, key, str(value))

    def _read_settings_from_configuration_file(self):
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

        for (section, attrname, typ, key, unused_env, value) in self.iter_all_options():
            if not self._config.has_section(section):
                continue
            if key and self._config.has_option(section, key):
                value = self._read_value(section, key, typ)
                setattr(self, attrname, value)

    def read_setting_section_from_file(self, section):
        """Reads a particular section of the settings file.

        Use this if you dynamically determine settings sections/keys at runtime.
        Otherwise, the settings file would be read only once, at the
        initialization phase of your module, and your config sections would
        never be read, thus values would be reset to defaults on every startup
        because GlobalSettings would think they don't exist.
        """
        if self._config.has_section(section):
            for option in self._config.options(section):
                # We don't know the value type in advance, just try them all.
                try:
                    value = self._config.getfloat(section, option)
                except ValueError:
                    try:
                        value = self._config.getint(section, option)
                    except ValueError:
                        try:
                            value = self._config.getboolean(section, option)
                        except ValueError:
                            value = self._config.get(section, option)

                setattr(self, section + option, value)

    def _read_settings_from_environment_variables(self):
        """Reads settings from their registered environment variables."""
        for unused_section, attrname, typ, unused_key, env, unused_value in self.iter_all_options():
            if not env:
                # This option does not have an environment variable name.
                continue
            var = get_env_by_type(typ, env)
            if var is not None:
                setattr(self, attrname, var)

    def _write_settings_to_configuration_file(self):
        for section, unused_attrname, unused_typ, key, unused_env_var, value in self.iter_all_options():
            if not self._config.has_section(section):
                self._config.add_section(section)
            if key:
                if value is not None:
                    self._write_value(section, key, value)
                else:
                    self._config.remove_option(section, key)
        try:
            with open(self.conf_file_path, "w", encoding="UTF-8") as file:
                self._config.write(file)
        except (IOError, OSError) as e:
            self.error("Failed to write to %s: %s", self.conf_file_path, e)

    def store_settings(self):
        """Writes settings to the user's local configuration file.

        Only those settings which were added with a section and a key value are
        stored.
        """
        self._write_settings_to_configuration_file()

    def iter_all_options(self):
        """Iterates over all registered options."""
        for section, options in list(self.options.items()):
            for attrname, (typ, key, environment) in list(options.items()):
                yield section, attrname, typ, key, environment, getattr(self, attrname)

    def is_default(self, attrname):
        return getattr(self, attrname) == self.defaults[attrname]

    def set_default(self, attrname):
        """Resets the specified setting to its default value."""
        setattr(self, attrname, self.defaults[attrname])

    def get_rgba(self, section, option):
        """Gets the option value from the configuration file parsed as a RGBA.

        Args:
            section (str): The section.
            option (str): The option that belongs to the `section`.

        Returns:
            Gdk.RGBA: The value for the `option` at the given `section`.
        """
        value = self._config.get(section, option)
        color = Gdk.RGBA()
        if not color.parse(value):
            raise Exception("Value cannot be parsed as Gdk.RGBA: %s" % value)
        return color

    def set_rgba(self, section, option, value):
        """Sets the option value to the configuration file as a RGBA.

        Args:
            section (str): The section.
            option (str): The option that belongs to the `section`.
            value (Gdk.RGBA): The color.
        """
        value = value.to_string()
        self._config.set(section, option, value)

    @classmethod
    def add_config_option(cls, attrname, type_=None, section=None, key=None,
                          environment=None, default=None, notify=False):
        """Adds a configuration option.

        This function should be called during module initialization, before
        the config file is actually read. By default, only options registered
        beforehand will be loaded.

        If you want to add configuration options after initialization,
        use the `read_setting_section_from_file` method to read them from
        the file.

        Args:
            attrname (str): The attribute of this class for accessing the option.
            type_ (Optional[type]): The type of the attribute. Unnecessary if a
                `default` value is specified.
            section (Optional[str]): The section of the config file under which
                this option is saved. This section must have been added with
                add_config_section(). Not necessary if `key` is not given.
            key (Optional[str]): The key under which this option is to be saved.
                By default the option will not be saved.
            environment (Optional[str]): The name of the environment variable
                for overwriting the value of the option.
            default (Optional[object]): The default value of the option.
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
            if notification.signame not in GObject.signal_list_names(cls):
                GObject.signal_new(notification.signame,
                                   cls,
                                   GObject.SignalFlags.RUN_LAST,
                                   None,
                                   ())
        else:
            setattr(cls, attrname, default)
        if section and key:
            cls.options[section][attrname] = type_, key, environment
        cls.environment.add(environment)
        cls.defaults[attrname] = default

    @classmethod
    def add_config_section(cls, section):
        """Adds a section to the local config file.

        Args:
            section (str): The section name.
        """
        if section in cls.options:
            return
        cls.options[section] = {}

    @classmethod
    def notifies_config_option(cls, attrname):
        """Checks whether a signal is emitted when the setting is changed.

        Args:
            attrname (str): The attribute name used to access the setting.

        Returns:
            bool: True when the setting emits a signal when changed,
                False otherwise.
        """
        signal_name = Notification.signal_name(attrname)
        return bool(GObject.signal_lookup(signal_name, cls))
