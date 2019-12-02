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
from gi.repository import Gdk
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
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=PADDING)
        self.set_decorated(False)
        self.add(vbox)

        self.completion = self.entry_suggestion()

        self.entry = Gtk.SearchEntry()
        clear_styles(self.entry)
        self.entry.set_completion(self.completion)
        vbox.pack_start(self.entry, True, True, 0)

        self.connect("focus-out-event", self.focus_out_event_cb)
        self.completion.connect("match-selected", self.match_selected_cb)

    def entry_suggestion(self):
        completion = Gtk.EntryCompletion()
        store = Gtk.ListStore(str, int, Gdk.ModifierType, Gio.SimpleAction)

        for i in self.app.shortcuts.group_actions:
            for action, title, action_object in self.app.shortcuts.group_actions[i]:
                accelerator_parsed = Gtk.accelerator_parse(self.app.get_accels_for_action(action)[0])
                first_col = action+" (<span color='gray'>"+title+"</span>)"
                store.append([first_col, accelerator_parsed.accelerator_key, accelerator_parsed.accelerator_mods, action_object])

        accel_renderer = Gtk.CellRendererAccel()
        text_renderer = Gtk.CellRendererText()
        completion.pack_start(text_renderer, True)
        completion.pack_end(accel_renderer, True)

        completion.set_model(store)
        completion.add_attribute(text_renderer, "markup", 0)
        completion.add_attribute(accel_renderer, "accel_key", 1)
        completion.add_attribute(accel_renderer, "accel_mods", 2)
        accel_renderer.set_property("foreground", "Gray")
        completion.set_match_func(self.any_match_func)

        return completion

    def any_match_func(self, completion, entry, i):
        if entry != '':
            action_name = completion.get_model()[i][0].lower()
            return entry.lower() in action_name
        else:
            return ''

    def focus_out_event_cb(self, window, unused):
        self.destroy()
        return True

    def match_selected_cb(self, completion, model, iter_num):
        action_object = model[iter_num][3]
        action_object.activate()
        return True
