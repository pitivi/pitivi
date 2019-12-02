# -*- coding: utf-8 -*-
# Pitivi Developer Console
# Copyright (c) 2017-2018, Fabian Orccon <cfoch.fabian@gmail.com>
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
"""Python console for inspecting and interacting with Pitivi and the project."""
import sys
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango
from gi.repository import Peas

from pitivi.dialogs.prefs import PreferencesDialog
from plugins.console.utils import Namespace
from plugins.console.widgets import ConsoleWidget


class PitiviNamespace(Namespace):
    """Easy to shape Python namespace."""

    def __init__(self, app):
        Namespace.__init__(self)
        self._app = app

    @property
    @Namespace.shortcut
    def app(self):
        """The Pitivi instance."""
        return self._app

    @property
    @Namespace.shortcut
    def plugin_manager(self):
        """The Plugin Manager instance."""
        return self._app.plugin_manager

    @property
    @Namespace.shortcut
    def project(self):
        """The current project."""
        return self._app.project_manager.current_project

    @property
    @Namespace.shortcut
    def timeline(self):
        """The GES.Timeline of the current project."""
        return self._app.gui.editor.timeline_ui.timeline.ges_timeline


class Console(GObject.GObject, Peas.Activatable):
    """Plugin which adds a Python console for development purposes."""

    __gtype_name__ = "ConsolePlugin"
    object = GObject.Property(type=GObject.Object)

    DEFAULT_COLOR = Gdk.RGBA(1.0, 1.0, 1.0, 1.0)
    DEFAULT_STDERR_COLOR = Gdk.RGBA(0.96, 0.47, 0.0, 1.0)
    DEFAULT_STDOUT_COLOR = Gdk.RGBA(1.0, 1.0, 1.0, 1.0)
    DEFAULT_FONT = Pango.FontDescription.from_string("Monospace Regular 12")

    def __init__(self):
        GObject.GObject.__init__(self)
        self.window = None
        self.terminal = None
        self.menu_item = None
        self.app = None

        # Set prompt.
        sys.ps1 = ">>> "
        sys.ps2 = "... "

    def do_activate(self):
        api = self.object
        self.app = api.app
        self.app.settings.add_config_section("console")

        self.app.settings.add_config_option(attrname="consoleColor",
                                            section="console",
                                            key="console-color",
                                            notify=True,
                                            default=Console.DEFAULT_COLOR)

        self.app.settings.add_config_option(attrname="consoleErrorColor",
                                            section="console",
                                            key="console-error-color",
                                            notify=True,
                                            default=Console.DEFAULT_STDERR_COLOR)

        self.app.settings.add_config_option(attrname="consoleOutputColor",
                                            section="console",
                                            key="console-output-color",
                                            notify=True,
                                            default=Console.DEFAULT_STDOUT_COLOR)

        self.app.settings.add_config_option(attrname="consoleFont",
                                            section="console",
                                            key="console-font",
                                            notify=True,
                                            default=Console.DEFAULT_FONT.to_string())

        self.app.settings.reload_attribute_from_file("console", "consoleColor")
        self.app.settings.reload_attribute_from_file("console",
                                                     "consoleErrorColor")
        self.app.settings.reload_attribute_from_file("console",
                                                     "consoleOutputColor")
        self.app.settings.reload_attribute_from_file("console", "consoleFont")

        PreferencesDialog.add_section("console", _("Console"))
        PreferencesDialog.add_color_preference(attrname="consoleColor",
                                               label=_("Color"),
                                               description=None,
                                               section="console")
        PreferencesDialog.add_color_preference(attrname="consoleErrorColor",
                                               # Translators: The color of the content from stderr.
                                               label=_("Standard error color"),
                                               description=None,
                                               section="console")
        PreferencesDialog.add_color_preference(attrname="consoleOutputColor",
                                               # Translators: The color of the content from stdout.
                                               label=_("Standard output color"),
                                               description=None,
                                               section="console")
        PreferencesDialog.add_font_preference(attrname="consoleFont",
                                              label=_("Font"),
                                              description=None,
                                              section="console")

        open_action = Gio.SimpleAction.new("open_console", None)
        open_action.connect("activate", self.__menu_item_activate_cb)
        self.app.add_action(open_action)
        self.app.shortcuts.add("app.open_console", ["<Primary>d"], open_action, _("Developer Console"))

        self._setup_dialog()
        self.add_menu_item()
        self.menu_item.show()

    def do_deactivate(self):
        PreferencesDialog.remove_section("console")
        self.window.destroy()
        self.remove_menu_item()
        self.window = None
        self.terminal = None
        self.app = None

    def add_menu_item(self):
        """Inserts a menu item into the Pitivi menu."""
        menu = self.app.gui.editor.builder.get_object("menu_box")
        self.menu_item = Gtk.ModelButton.new()
        self.menu_item.props.text = _("Developer Console")
        self.menu_item.set_action_name("app.open_console")

        menu.add(self.menu_item)

    def remove_menu_item(self):
        """Removes a menu item from the Pitivi menu."""
        self.app.remove_action("open_console")
        menu = self.app.gui.editor.builder.get_object("menu_box")
        menu.remove(self.menu_item)
        self.menu_item = None

    def _setup_dialog(self):
        namespace = PitiviNamespace(self.app)
        self.window = Gtk.Window()
        welcome_message = "".join(self._create_welcome_message(namespace))
        self.terminal = ConsoleWidget(namespace, welcome_message)
        self.terminal.connect("eof", self.__eof_cb)

        self._init_colors()
        self.terminal.set_font(self.app.settings.consoleFont)
        self._connect_settings_signals()

        self.window.set_default_size(600, 400)
        self.window.set_title(_("Pitivi Console"))
        self.window.connect("delete-event", self.__delete_event_cb)
        self.window.add(self.terminal)

    def _create_welcome_message(self, namespace):
        console_plugin_info = self.app.plugin_manager.get_plugin_info("console")
        name = console_plugin_info.get_name()
        version = console_plugin_info.get_version() or ""
        yield "%s %s\n\n" % (name, version)
        yield console_plugin_info.get_help_uri()
        yield "\n\n"
        yield _("You can use the following shortcuts:")
        yield "\n"
        for shortcut in namespace.get_shortcuts():
            yield " - %s\n" % shortcut
        yield "\n"
        yield _("Type \"{help}(<command>)\" for more information.").format(help="help")
        yield "\n\n"

    def _init_colors(self):
        """Sets the colors from Pitivi settings."""
        self.terminal.set_stderr_color(self.app.settings.consoleErrorColor)
        self.terminal.set_stdout_color(self.app.settings.consoleOutputColor)
        self.terminal.set_color(self.app.settings.consoleColor)

    def _connect_settings_signals(self):
        """Connects the settings' signals."""
        self.app.settings.connect("consoleColorChanged", self.__color_changed_cb)
        self.app.settings.connect("consoleErrorColorChanged",
                                  self.__error_color_changed_cb)
        self.app.settings.connect("consoleOutputColorChanged",
                                  self.__output_color_changed_cb)
        self.app.settings.connect("consoleFontChanged", self.__font_changed_cb)

    def __color_changed_cb(self, settings):
        if self.terminal:
            self.terminal.set_color(settings.consoleColor)

    def __error_color_changed_cb(self, settings):
        if self.terminal:
            self.terminal.set_stderr_color(settings.consoleErrorColor)

    def __output_color_changed_cb(self, settings):
        if self.terminal:
            self.terminal.set_stdout_color(settings.consoleOutputColor)

    def __font_changed_cb(self, settings):
        if self.terminal:
            self.terminal.set_font(settings.consoleFont)

    def __menu_item_activate_cb(self, unused_data, unused_param):
        self.window.show_all()
        self.window.set_keep_above(True)

    def __eof_cb(self, unused_widget):
        self.window.hide()
        return True

    def __delete_event_cb(self, unused_widget, unused_data):
        return self.window.hide_on_delete()
