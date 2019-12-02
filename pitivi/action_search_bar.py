# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2019, Ayush Mittal <ayush.mittal9398@gmail.com>
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
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import Gtk

from pitivi.utils.ui import clear_styles
from pitivi.utils.ui import gtk_style_context_get_color
from pitivi.utils.ui import PADDING


class ActionSearchBar(Gtk.Window):

    def __init__(self, app):
        Gtk.Window.__init__(self)
        self.app = app

        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        self.set_size_request(600, 50)
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=PADDING)
        self.set_decorated(False)
        self.add(self.vbox)

        self.entry = Gtk.SearchEntry()
        self.results_window = Gtk.ScrolledWindow()
        clear_styles(self.entry)
        self.setup_results_window()
        self.entry.props.placeholder_text = _("Search Action")
        self.vbox.set_focus_chain([self.entry, self.results_window])

        self.connect("key-press-event", self._entry_key_press_event_cb)
        self.entry.connect("changed", self._entry_changed_cb)
        self.results_treeview.connect("row-activated", self._row_activated_cb)

        self.vbox.pack_start(self.entry, True, True, 0)
        self.vbox.pack_start(self.results_window, True, True, 0)

    def setup_results_window(self):
        self.list_model = Gtk.ListStore(str, int, Gdk.ModifierType, Gio.SimpleAction, object)
        self.model_filter = self.list_model.filter_new()
        disable_groups = ["medialibrary"]

        for group in self.app.shortcuts.group_actions:
            if group not in disable_groups:
                for action, title, action_object in self.app.shortcuts.group_actions[group]:
                    accelerator_parsed = Gtk.accelerator_parse(self.app.get_accels_for_action(action)[0])
                    self.list_model.append([title,
                                            accelerator_parsed.accelerator_key,
                                            accelerator_parsed.accelerator_mods,
                                            action_object,
                                            title.lower().split(" ")])

        self.model_filter.set_visible_func(self.filter_func)
        self.results_treeview = Gtk.TreeView.new_with_model(self.model_filter)
        self.results_treeview.props.headers_visible = False

        text_renderer = Gtk.CellRendererText()
        description_column = Gtk.TreeViewColumn("Description", text_renderer, text=0)
        description_column.set_fixed_width(400)
        self.results_treeview.append_column(description_column)

        accel_renderer = Gtk.CellRendererAccel()

        # The default is Gtk.CellRendererAccelMode.GTK, but with that one
        # accelerator "Left" appears as "Invalid" for some reason.
        accel_renderer.props.accel_mode = Gtk.CellRendererAccelMode.OTHER

        style_context = self.results_window.get_style_context()
        color_insensitive = gtk_style_context_get_color(style_context, Gtk.StateFlags.INSENSITIVE)
        accel_renderer.props.foreground_rgba = color_insensitive
        accel_renderer.props.foreground_set = True
        shortcut_column = Gtk.TreeViewColumn("Shortcut", accel_renderer, accel_key=1, accel_mods=2)
        self.results_treeview.append_column(shortcut_column)
        row_iter = self.model_filter.get_iter_first()
        row_path = self.model_filter.get_path(row_iter)
        self.results_treeview.set_cursor(row_path)

        self.results_window.add(self.results_treeview)
        self.results_window.props.min_content_height = 300

    def filter_func(self, model, row, data):
        text = self.entry.get_text()
        if text:
            self.results_window.show()
            all_found = True
            for keyword in text.lower().split(" "):
                found = False
                for term in model[row][4]:
                    if term.startswith(keyword):
                        found = True
                        break
                if not found:
                    all_found = False
            return all_found
        else:
            return True

    def do_focus_out_event(self, event):
        self.destroy()
        return True

    def _row_activated_cb(self, treeview, path, col):
        _, rows = self.results_treeview.get_selection().get_selected_rows()
        row_path = self.model_filter.convert_path_to_child_path(rows[0])
        action_object = self.list_model[row_path][3]
        action_object.activate()
        self.destroy()
        return True

    def _entry_changed_cb(self, *args):
        self.model_filter.refilter()
        row_iter = self.model_filter.get_iter_first()
        row_path = self.model_filter.get_path(row_iter)
        self.results_treeview.set_cursor(row_path)
        return True

    def _entry_key_press_event_cb(self, entry, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
            return True

        if event.keyval == Gdk.KEY_Return:
            self._row_activated_cb(self.results_treeview, None, None)
            return True

        _, rows = self.results_treeview.get_selection().get_selected_rows()
        first_row_iter = self.model_filter.get_iter_first()
        first_row_path = self.model_filter.get_path(first_row_iter)
        if event.keyval == Gdk.KEY_Up and rows[0] == first_row_path:
            self.entry.grab_focus()
            return True

        return False
