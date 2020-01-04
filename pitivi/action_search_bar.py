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
        self.results_window.props.can_focus = False
        clear_styles(self.entry)
        self.setup_results_window()
        self.entry.props.placeholder_text = _("Search Action")

        self.entry.connect("key-press-event", self._entry_key_press_event_cb)
        self.entry.connect("changed", self._entry_changed_cb)
        self.treeview.connect("row-activated", self._treeview_row_activated_cb)

        self.vbox.pack_start(self.entry, True, True, 0)
        self.vbox.pack_start(self.results_window, True, True, 0)

    def setup_results_window(self):
        self.list_model = Gtk.ListStore(str, int, Gdk.ModifierType, Gio.SimpleAction, object, bool, bool)
        self.model_filter = self.list_model.filter_new()
        disable_groups = ["medialibrary"]

        style_context = self.entry.get_style_context()
        color_insensitive = gtk_style_context_get_color(style_context, Gtk.StateFlags.INSENSITIVE)

        for group in self.app.shortcuts.group_actions:
            if group not in disable_groups:
                for action, title, action_object in self.app.shortcuts.group_actions[group]:
                    accels = self.app.get_accels_for_action(action)
                    accel = accels[0] if accels else ""
                    accelerator_parsed = Gtk.accelerator_parse(accel)
                    disabled = not action_object.props.enabled
                    self.list_model.append([title,
                                            accelerator_parsed.accelerator_key,
                                            accelerator_parsed.accelerator_mods,
                                            action_object,
                                            title.lower().split(" "),
                                            disabled,
                                            bool(accels)])

        self.model_filter.set_visible_func(self.filter_func)
        self.treeview = Gtk.TreeView.new_with_model(self.model_filter)
        self.treeview.props.headers_visible = False
        self.treeview.props.enable_search = False
        self.treeview.props.can_focus = False

        text_renderer = Gtk.CellRendererText()
        text_renderer.props.foreground_rgba = color_insensitive
        description_column = Gtk.TreeViewColumn("Description", text_renderer, text=0, foreground_set=5)
        description_column.set_fixed_width(400)
        self.treeview.append_column(description_column)

        accel_renderer = Gtk.CellRendererAccel()
        # The default is Gtk.CellRendererAccelMode.GTK, but with that one
        # accelerator "Left" appears as "Invalid" for some reason.
        accel_renderer.props.accel_mode = Gtk.CellRendererAccelMode.OTHER
        accel_renderer.props.foreground_rgba = color_insensitive
        accel_renderer.props.foreground_set = True
        shortcut_column = Gtk.TreeViewColumn("Shortcut", accel_renderer, accel_key=1, accel_mods=2, visible=6)
        self.treeview.append_column(shortcut_column)

        self.__select_row(self.model_filter.get_iter_first())

        self.results_window.add(self.treeview)
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

    def _treeview_row_activated_cb(self, treeview, path, col):
        self.__activate_selected_action()

    def __activate_selected_action(self):
        model, row_iter = self.treeview.get_selection().get_selected()
        if not row_iter:
            # No row is selected, possibly because there are no rows.
            return

        action_object, = model.get(row_iter, 3)
        action_object.activate()
        self.destroy()

    def _entry_changed_cb(self, entry):
        self.model_filter.refilter()

        # Make sure a row is always selected.
        self.__select_row(self.model_filter.get_iter_first())

    def __select_row(self, row_iter):
        if not row_iter:
            return

        self.treeview.get_selection().select_iter(row_iter)

        row_path = self.model_filter.get_path(row_iter)
        self.treeview.scroll_to_cell(row_path, None, False, 0, 0)

    def _entry_key_press_event_cb(self, entry, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
            return True

        if event.keyval == Gdk.KEY_Return:
            self.__activate_selected_action()
            return True

        if event.keyval == Gdk.KEY_Up:
            selection = self.treeview.get_selection()
            model, row_iter = selection.get_selected()
            if row_iter:
                self.__select_row(model.iter_previous(row_iter))
                return True

        if event.keyval == Gdk.KEY_Down:
            selection = self.treeview.get_selection()
            model, row_iter = selection.get_selected()
            if row_iter:
                self.__select_row(model.iter_next(row_iter))
                return True

        # Let the default handler process this event.
        return False
