# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2019 Ayush Mittal <ayush.mittal9398@gmail.com>
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
from pitivi.utils.ui import PADDING

class ActionSearchBar(Gtk.Window):

    def __init__(self, app):
        Gtk.Window.__init__(self)
        self.app = app

        self.set_transient_for(app.gui)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        self.set_size_request(600, 50)
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=PADDING)
        self.set_decorated(False)
        self.add(self.vbox)

        self.entry = Gtk.SearchEntry()
        self.suggestion_window = Gtk.ScrolledWindow()
        clear_styles(self.entry)
        self.create_entry()
        self.vbox.pack_start(self.entry, True, True, 0)
        self.entry.props.placeholder_text = _("Search Action")
        self.entry.connect("key-press-event", self._entry_key_press_event_cb)

    def create_entry(self):
        list_model = Gtk.ListStore(str, int, Gdk.ModifierType, Gio.SimpleAction, object)
        self.model_filter = list_model.filter_new()

        for i in self.app.shortcuts.group_actions:
            for action, title, action_object in self.app.shortcuts.group_actions[i]:
                accelerator_parsed = Gtk.accelerator_parse(self.app.get_accels_for_action(action)[0])
                list_model.append([title,
                                   accelerator_parsed.accelerator_key,
                                   accelerator_parsed.accelerator_mods,
                                   action_object,
                                   title.lower().split(' ')])

        self.model_filter.set_visible_func(self.filter_func)
        self.suggestion_treeview = Gtk.TreeView.new_with_model(self.model_filter)
        self.suggestion_treeview.props.headers_visible = False

        text_renderer = Gtk.CellRendererText()
        description_column = Gtk.TreeViewColumn("Description", text_renderer, text=0)
        description_column.set_fixed_width(400)
        self.suggestion_treeview.append_column(description_column)

        accel_renderer = Gtk.CellRendererAccel()
        accel_renderer.props.accel_mode = Gtk.CellRendererAccelMode.OTHER
        accel_renderer.props.foreground = "Gray"
        shortcut_column = Gtk.TreeViewColumn("Shortcut", accel_renderer, accel_key=1, accel_mods=2)
        self.suggestion_treeview.append_column(shortcut_column)

        self.suggestion_window.add(self.suggestion_treeview)
        self.suggestion_treeview.connect("row-activated", self._row_activated_cb)
        self.suggestion_window.props.min_content_height = 300
        self.vbox.pack_end(self.suggestion_window, True, True, 0)
        self.entry.connect("changed", self._entry_changed_cb)

    def filter_func(self, model, row, data):
        text = self.entry.get_text()
        if text:
            self.suggestion_window.show()
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
        model, rows = self.suggestion_treeview.get_selection().get_selected_rows()
        row_path = self.model_filter.convert_path_to_child_path(rows[0])
        action_object = model[row_path][3]
        action_object.activate()
        self.destroy()
        return True

    def _entry_changed_cb(self, *args):
        self.model_filter.refilter()
        return True

    def _entry_key_press_event_cb(self, entry, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
            return True

        return False
