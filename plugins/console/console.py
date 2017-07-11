# -*- coding: utf-8 -*-
# Pitivi Developer Console
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
"""Python console for inspecting and interacting with Pitivi and the project."""
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import Peas
from utils import Namespace
from widgets import ConsoleWidget

from pitivi.dialogs.prefs import PreferencesDialog
from pitivi.settings import ConfigError


class PitiviNamespace(Namespace):
    """A class to define public objects in the namespace."""

    def __init__(self, app):
        Namespace.__init__(self)
        self._app = app

    @property
    @Namespace.shortcut
    def app(self):
        """Gets the Pitivi instance."""
        return self._app

    @property
    @Namespace.shortcut
    def plugin_manager(self):
        """Gets the Plugin Manager of the Pitivi instance."""
        return self._app.plugin_manager

    @property
    @Namespace.shortcut
    def timeline(self):
        """Gets the GES.Timeline of the current project."""
        return self._app.gui.timeline_ui.timeline.ges_timeline

    @property
    @Namespace.shortcut
    def shortcuts(self):
        """Gets the available methods in the namespace."""
        print(_("These are the available methods or attributes."))
        print()
        for attr in self.get_shortcuts():
            print(" - %s" % attr)
        print()
        print(_("Type \"{help}(<shortcut_command>)\" for more information.")
              .format(help="help"))


class Console(GObject.GObject, Peas.Activatable):
    """Plugin which adds a Python console for development purposes."""

    __gtype_name__ = "ConsolePlugin"
    object = GObject.Property(type=GObject.Object)

    MENU_LABEL = _("Developer Console")
    TITLE = _("Pitivi Console")

    DEFAULT_COLOR = Gdk.RGBA(0.51, 0.39, 0.54, 1.0)
    DEFAULT_ERROR_COLOR = Gdk.RGBA(0.96, 0.47, 0.0, 1.0)
    DEFAULT_COMMAND_COLOR = Gdk.RGBA(0.2, 0.39, 0.64, 1.0)
    DEFAULT_NORMAL_COLOR = Gdk.RGBA(0.05, 0.5, 0.66, 1.0)
    DEFAULT_FONT = Pango.FontDescription.from_string("Monospace Regular 12")
    _WELCOME_MESSAGE = _("{name} {version}\n\n"
                         "Type \"{shortcuts}\" to list available methods.\n"
                         "For more information, visit {help_uri}\n\n")

    def __init__(self):
        GObject.GObject.__init__(self)
        self.window = None
        self.terminal = None
        self.menu_item = None
        self.app = None

    def do_activate(self):
        api = self.object
        self.app = api.app
        try:
            self.app.settings.addConfigSection("console")
            self.app.settings.addConfigOption(attrname="consoleColor",
                                              section="console",
                                              key="console-color",
                                              notify=True,
                                              default=Console.DEFAULT_COLOR)
            self.app.settings.addConfigOption(attrname="consoleErrorColor",
                                              section="console",
                                              key="console-error-color",
                                              notify=True,
                                              default=Console.DEFAULT_ERROR_COLOR)
            self.app.settings.addConfigOption(attrname="consoleCommandColor",
                                              section="console",
                                              key="console-command-color",
                                              notify=True,
                                              default=Console.DEFAULT_COMMAND_COLOR)
            self.app.settings.addConfigOption(attrname="consoleNormalColor",
                                              section="console",
                                              key="console-normal-color",
                                              notify=True,
                                              default=Console.DEFAULT_NORMAL_COLOR)
            self.app.settings.addConfigOption(attrname="consoleFont",
                                              section="console",
                                              key="console-font",
                                              notify=True,
                                              default=Console.DEFAULT_FONT.to_string())
        except ConfigError:
            pass

        self.app.settings.reload_attribute_from_file("console", "consoleColor")
        self.app.settings.reload_attribute_from_file("console",
                                                     "consoleErrorColor")
        self.app.settings.reload_attribute_from_file("console",
                                                     "consoleCommandColor")
        self.app.settings.reload_attribute_from_file("console",
                                                     "consoleNormalColor")
        self.app.settings.reload_attribute_from_file("console", "consoleFont")

        PreferencesDialog.add_section("console", _("Console"))
        PreferencesDialog.addColorPreference(attrname="consoleColor",
                                             label=_("Color"),
                                             description=None,
                                             section="console")
        PreferencesDialog.addColorPreference(attrname="consoleErrorColor",
                                             label=_("Error color"),
                                             description=None,
                                             section="console")
        PreferencesDialog.addColorPreference(attrname="consoleCommandColor",
                                             label=_("Command color"),
                                             description=None,
                                             section="console")
        PreferencesDialog.addColorPreference(attrname="consoleNormalColor",
                                             label=_("Normal color"),
                                             description=None,
                                             section="console")
        PreferencesDialog.addFontPreference(attrname="consoleFont",
                                            label=_("Font"),
                                            description=None,
                                            section="console")

        self._setup_dialog()
        self.add_menu_item()
        self.menu_item.show()

    def do_deactivate(self):
        PreferencesDialog.remove_section("console")
        self.window.destroy()
        self.remove_menu_item()
        self.window = None
        self.terminal = None
        self.menu_item = None
        self.app = None

    def add_menu_item(self):
        """Inserts a menu item into the Pitivi menu"""
        menu = self.app.gui.editor.builder.get_object("menu")
        self.menu_item = Gtk.MenuItem.new_with_label(Console.MENU_LABEL)
        self.menu_item.connect("activate", self.__menu_item_activate_cb)
        menu.add(self.menu_item)

    def remove_menu_item(self):
        """Removes a menu item from the Pitivi menu"""
        menu = self.app.gui.editor.builder.get_object("menu")
        menu.remove(self.menu_item)
        self.menu_item = None

    def _setup_dialog(self):
        namespace = PitiviNamespace(self.app)
        self.window = Gtk.Window()
        console_plugin_info = self.app.plugin_manager.get_plugin_info("console")
        welcome_message = Console._WELCOME_MESSAGE.format(
            name=console_plugin_info.get_name(),
            shortcuts=PitiviNamespace.shortcuts.fget.__name__,
            version=console_plugin_info.get_version() or "",
            help_uri=console_plugin_info.get_help_uri())
        self.terminal = ConsoleWidget(namespace, welcome_message)

        self._init_colors()
        self.terminal.set_font(self.app.settings.consoleFont)
        self._connect_settings_signals()

        self.window.set_default_size(600, 400)
        self.window.set_title(Console.TITLE)
        self.window.connect("delete-event", self.__delete_event_cb)
        self.window.add(self.terminal)

    def _init_colors(self):
        """Sets the colors from Pitivi settings."""
        self.terminal.error.set_property("foreground-rgba",
                                         self.app.settings.consoleErrorColor)
        self.terminal.command.set_property("foreground-rgba",
                                           self.app.settings.consoleCommandColor)
        self.terminal.normal.set_property("foreground-rgba",
                                          self.app.settings.consoleNormalColor)
        self.terminal.set_color(self.app.settings.consoleColor)

    def _connect_settings_signals(self):
        """Connects the settings' signals."""
        self.app.settings.connect("consoleColorChanged", self.__color_changed_cb)
        self.app.settings.connect("consoleErrorColorChanged",
                                  self.__error_color_changed_cb)
        self.app.settings.connect("consoleCommandColorChanged",
                                  self.__command_color_changed_cb)
        self.app.settings.connect("consoleNormalColorChanged",
                                  self.__command_normal_changed_cb)
        self.app.settings.connect("consoleFontChanged", self.__font_changed_cb)

    def __color_changed_cb(self, settings):
        if self.terminal is not None:
            self.terminal.set_color(settings.consoleColor)

    def __error_color_changed_cb(self, settings):
        if self.terminal is not None:
            self.terminal.error.set_property("foreground-rgba",
                                             settings.consoleErrorColor)

    def __command_color_changed_cb(self, settings):
        if self.terminal is not None:
            self.terminal.command.set_property("foreground-rgba",
                                               settings.consoleCommandColor)

    def __command_normal_changed_cb(self, settings):
        if self.terminal is not None:
            self.terminal.normal.set_property("foreground-rgba",
                                              settings.consoleNormalColor)

    def __font_changed_cb(self, settings):
        if self.terminal is not None:
            self.terminal.set_font(settings.consoleFont)

    def __menu_item_activate_cb(self, unused_data):
        self.window.show_all()
        self.window.set_keep_above(True)

    def __delete_event_cb(self, unused_widget, unused_data):
        return self.window.hide_on_delete()
