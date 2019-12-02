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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
from gi.repository import Gio
from gi.repository import Gtk

from pitivi.utils.ui import clear_styles
from pitivi.utils.ui import PADDING

class ActionSearchBar(Gtk.Window):

    def __init__(self, app):
        self.app = app
        Gtk.Window.__init__(self, title="")
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_size_request(1000, 50)
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=PADDING)
        self.set_decorated(False)
        self.add(self.vbox)

        self.entry = Gtk.SearchEntry()
        self.suggestion_window = Gtk.ScrolledWindow()
        clear_styles(self.entry)
        self.entry_suggestion()
        self.vbox.pack_start(self.entry, True, True, 0)
        self.connect("focus-out-event", self.focus_out_event_cb)

    def entry_suggestion(self):
        list_model = Gtk.ListStore(str, str, Gio.SimpleAction)
        self.model_filter = list_model.filter_new()
        self.suggestions = 0

        for i in self.app.shortcuts.group_actions:
            for action, title, action_object in self.app.shortcuts.group_actions[i]:
                accelerator_parsed = Gtk.accelerator_parse(self.app.get_accels_for_action(action)[0])
                accel_name = Gtk.accelerator_get_label(accelerator_parsed.accelerator_key, accelerator_parsed.accelerator_mods)
                list_model.append([title, accel_name, action_object])

        self.model_filter.set_visible_func(self.filter_func)
        self.suggestion_treeview = Gtk.TreeView.new_with_model(self.model_filter)
        self.suggestion_treeview.props.headers_visible = False

        text_renderer = Gtk.CellRendererText()
        description_column = Gtk.TreeViewColumn("Description", text_renderer, text=0)
        description_column.set_fixed_width(500)
        self.suggestion_treeview.append_column(description_column)

        accel_renderer = Gtk.CellRendererText()
        accel_renderer.set_property("foreground", "Gray")
        shortcut_column = Gtk.TreeViewColumn("Shortcut", accel_renderer, text=1)
        self.suggestion_treeview.append_column(shortcut_column)

        self.suggestion_window.add(self.suggestion_treeview)
        self.suggestion_treeview.connect("row-activated", self.row_activated_cb)
        self.suggestion_window.set_property("min-content-height", 300)
        self.vbox.pack_end(self.suggestion_window, True, True, 0)
        self.entry.connect("changed", self.changed_entry_cb)

    def filter_func(self, model, row, data):
        entry = self.entry.get_text()
        if entry != '':
            self.suggestion_window.show()
            action_name = model[row][0].lower()
            if entry.lower() in action_name:
                self.suggestions += 1
                return True
            else:
                return False
        else:
            return True

    def focus_out_event_cb(self, window, unused):
        self.destroy()
        return True

    def row_activated_cb(self, treeview, path, col):
        model, rows = self.suggestion_treeview.get_selection().get_selected_rows()
        row_path = self.model_filter.convert_path_to_child_path(rows[0])
        action_object = model[row_path][2]
        action_object.activate()
        self.destroy()
        return True

    def changed_entry_cb(self, *args):
        self.model_filter.refilter()
        return True
