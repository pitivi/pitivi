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
        settings = self.get_settings()
        settings.props.gtk_dnd_drag_threshold = 1

    def append_page(self, child, label):
        Gtk.Notebook.append_page(self, child, label)
        self._set_child_properties(child, label)
        child.show()
        label.show()

        try:
            docked = getattr(self.settings, child_name + "Docked")
        except AttributeError:
            # Create the default config ONLY if keys don't already exist
            self._createDefaultConfig(child_name)

    def _set_child_properties(self, child, label):
        self.child_set_property(child, "detachable", True)
        self.child_set_property(child, "tab-expand", False)
        self.child_set_property(child, "tab-fill", True)
        label.props.xalign = 0.0

    def _detachedWindowDestroyCb(self, window, page, orig_pos, label):
        # We assume there's only one notebook and one tab per utility window
        notebook = window.get_children()[0]
        notebook.remove_page(0)
        self.insert_page(page, label, orig_pos)
        self._set_child_properties(page, label)

    def _createWindowCb(self, unused_notebook, page, x, y):
        # unused_notebook here is the same as "self"
        original_position = self.page_num(page)
        label = self.get_tab_label(page)
        window = Gtk.Window()
        window.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        window.set_title(label.get_text())
        window.set_default_size(600, 400)
        window.connect("destroy", self._detachedWindowDestroyCb,
                    page, original_position, label)
        notebook = Gtk.Notebook()
        notebook.props.show_tabs = False
        window.add(notebook)
        window.show_all()
        window.move(x, y)
        return notebook

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
