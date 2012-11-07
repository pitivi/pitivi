# PiTiVi , Non-linear video editor
#
#       tabsmanager.py
#
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

from gi.repository import Gtk
from gi.repository import Gdk
from pitivi.utils.ui import SPACING
from pitivi.settings import GlobalSettings


class BaseTabs(Gtk.Notebook):
    def __init__(self, app):
        Gtk.Notebook.__init__(self)
        self.set_border_width(SPACING)
        self.set_scrollable(True)
        self.connect("create-window", self._createWindowCb)
        self.settings = app.settings  # To save/restore states of detached tabs
        notebook_widget_settings = self.get_settings()
        notebook_widget_settings.props.gtk_dnd_drag_threshold = 1

    def append_page(self, child, label):
        child_name = label.get_text()
        Gtk.Notebook.append_page(self, child, label)
        self._set_child_properties(child, label)
        child.show()
        label.show()

        self._createDefaultConfig(child_name)
        docked = getattr(self.settings, child_name + "Docked")
        if not docked:
            self.createWindow(child)

    def _set_child_properties(self, child, label):
        self.child_set_property(child, "detachable", True)
        self.child_set_property(child, "tab-expand", False)
        self.child_set_property(child, "tab-fill", True)
        label.props.xalign = 0.0

    def _detachedComponentWindowDestroyCb(self, window, child,
            original_position, child_name):
        notebook = window.get_child()
        position = notebook.page_num(child)
        notebook.remove_page(position)
        setattr(self.settings, child_name + "Docked", True)
        label = Gtk.Label(child_name)
        self.insert_page(child, label, original_position)
        self._set_child_properties(child, label)

    def _createWindowCb(self, from_notebook, child, unused_x, unused_y):
        """
        Callback that occurs when tearing off a tab to create a new window
        """
        # from_notebook == BaseTabs instance == self. It is a group of tabs.
        # child is the widget inside the notebook's tab's content area.
        # The return statement here is important to provide the notebook widget
        # that gtk should insert into the window at the end:
        return self.createWindow(child)

    def createWindow(self, child):
        """
        Create a window out of the tab. This can be called by _createWindowCb
        or manually (to restore a previously undocked state)
        """
        original_position = self.page_num(child)
        child_name = self.get_tab_label(child).get_text()
        window = Gtk.Window()
        window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        window.set_title(child_name)

        # Get the previous window state settings
        width = getattr(self.settings, child_name + "Width")
        height = getattr(self.settings, child_name + "Height")
        x = getattr(self.settings, child_name + "X")
        y = getattr(self.settings, child_name + "Y")

        # Save the fact that the window is now detached
        setattr(self.settings, child_name + "Docked", False)

        window.set_default_size(width, height)
        notebook = Gtk.Notebook()
        notebook.props.show_tabs = False
        window.add(notebook)
        window.show_all()
        window.move(x, y)
        window.connect("configure-event", self._detachedComponentWindowConfiguredCb, child_name)
        window.connect("destroy", self._detachedComponentWindowDestroyCb, child,
                        original_position, child_name)
        return notebook

    def _detachedComponentWindowConfiguredCb(self, window, event, child_name):
        """
        When the user configures the detached window
        (changes its size, position, etc.), save the settings.

        The config key's name depends on the name (label) of the tab widget.
        """
        setattr(self.settings, child_name + "Width", event.width)
        setattr(self.settings, child_name + "Height", event.height)
        setattr(self.settings, child_name + "X", event.x)
        setattr(self.settings, child_name + "Y", event.y)

    def _createDefaultConfig(self, child_name):
        """
        If they do not exist already, create default settings
        to save the state of a detachable widget.
        """
        GlobalSettings.addConfigSection("tabs - " + child_name)
        GlobalSettings.addConfigOption(child_name + "Docked",
            section="tabs - " + child_name,
            key="docked",
            default=True)
        GlobalSettings.addConfigOption(child_name + "Width",
            section="tabs - " + child_name,
            key="width",
            default=320)
        GlobalSettings.addConfigOption(child_name + "Height",
            section="tabs - " + child_name,
            key="height",
            default=400)
        GlobalSettings.addConfigOption(child_name + "X",
            section="tabs - " + child_name,
            key="x-pos",
            default=0)
        GlobalSettings.addConfigOption(child_name + "Y",
            section="tabs - " + child_name,
            key="y-pos",
            default=0)

        GlobalSettings.readSettingSectionFromFile(self.settings, "tabs - " + child_name, child_name + "Docked", bool, "docked")
        GlobalSettings.readSettingSectionFromFile(self.settings, "tabs - " + child_name, child_name + "Width", int, "width")
        GlobalSettings.readSettingSectionFromFile(self.settings, "tabs - " + child_name, child_name + "Height", int, "height")
        GlobalSettings.readSettingSectionFromFile(self.settings, "tabs - " + child_name, child_name + "X", int, "x-pos")
        GlobalSettings.readSettingSectionFromFile(self.settings, "tabs - " + child_name, child_name + "Y", int, "y-pos")
