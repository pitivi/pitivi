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
"""Gtk.Notebook helpers."""
from gi.repository import Gdk
from gi.repository import Gtk

from pitivi.settings import ConfigError
from pitivi.settings import GlobalSettings
from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import SPACING


class BaseTabs(Gtk.Notebook, Loggable):
    """Notebook which can detach its tabs to new windows.

    Persists which of its tabs are detached.

    Attributes:
        app (Pitivi): The app.
    """

    def __init__(self, app):
        Gtk.Notebook.__init__(self)
        Loggable.__init__(self)
        self.set_border_width(SPACING)
        self.set_scrollable(True)
        self.settings = app.settings
        notebook_widget_settings = self.get_settings()
        notebook_widget_settings.props.gtk_dnd_drag_threshold = 1
        self.connect("create-window", self.__create_window_cb)

    def append_page(self, child_name, child, label):
        Gtk.Notebook.append_page(self, child, label)
        self._set_child_properties(child, label)
        label.show()

        self._create_default_config(child_name)
        docked = getattr(self.settings, child_name + "docked")
        if docked is False:
            # Restore a previously undocked state.
            notebook = self._create_window(child)
            original_position = self.page_num(child)
            self.remove_page(original_position)
            # Add the tab to the notebook in our newly created window.
            notebook.append_page(child, Gtk.Label(label=child_name))
        child.show()

    def _set_child_properties(self, child, label):
        self.child_set_property(child, "detachable", True)
        self.child_set_property(child, "tab-expand", False)
        self.child_set_property(child, "tab-fill", True)
        label.props.xalign = 0.0

    def __detached_window_destroyed_cb(self, window, child,
                                       original_position, child_name):
        notebook = window.get_child()
        position = notebook.page_num(child)
        notebook.remove_page(position)
        setattr(self.settings, child_name + "docked", True)
        label = Gtk.Label(label=child_name)
        self.insert_page(child, label, original_position)
        self._set_child_properties(child, label)

    def __create_window_cb(self, unused_notebook, child, unused_x, unused_y):
        """Handles the detachment of a page.

        Args:
            child (Gtk.Widget): The detached page.

        Returns:
            Gtk.Notebook: The notebook the page should be attached to.
        """
        return self._create_window(child)

    def _create_window(self, child):
        """Creates a separate window for the specified child."""
        original_position = self.page_num(child)
        child_name = self.get_tab_label(child).get_text()
        window = Gtk.Window()
        window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        window.set_title(child_name)

        # Get the previous window state settings
        width = getattr(self.settings, child_name + "width")
        height = getattr(self.settings, child_name + "height")
        x = getattr(self.settings, child_name + "x")
        y = getattr(self.settings, child_name + "y")

        # Save the fact that the window is now detached
        setattr(self.settings, child_name + "docked", False)

        window.set_default_size(width, height)
        notebook = Gtk.Notebook()
        notebook.props.show_tabs = False
        window.add(notebook)
        window.show_all()
        window.move(x, y)
        window.connect(
            "configure-event", self.__detached_window_configure_cb,
            child_name)
        window.connect(
            "destroy", self.__detached_window_destroyed_cb, child,
            original_position, child_name)

        return notebook

    def __detached_window_configure_cb(self, window, event, child_name):
        """Saves the position and size of the specified window."""
        # get_position() takes the window manager's decorations into account
        position = window.get_position()
        setattr(self.settings, child_name + "width", event.width)
        setattr(self.settings, child_name + "height", event.height)
        setattr(self.settings, child_name + "x", position[0])
        setattr(self.settings, child_name + "y", position[1])

    def _create_default_config(self, child_name):
        """Creates default settings to save the state of a detachable widget."""
        try:
            GlobalSettings.add_config_section(child_name)
        except ConfigError:
            self.info("Section %s already exists", child_name)
            return

        GlobalSettings.add_config_option(child_name + "docked",
                                         section=child_name,
                                         key="docked",
                                         default=True)
        GlobalSettings.add_config_option(child_name + "width",
                                         section=child_name,
                                         key="width",
                                         default=320)
        GlobalSettings.add_config_option(child_name + "height",
                                         section=child_name,
                                         key="height",
                                         default=400)
        GlobalSettings.add_config_option(child_name + "x",
                                         section=child_name,
                                         key="x",
                                         default=0)
        GlobalSettings.add_config_option(child_name + "y",
                                         section=child_name,
                                         key="y",
                                         default=0)

        self.settings.read_setting_section_from_file(child_name)
