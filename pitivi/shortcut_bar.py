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
from gi.repository import Gtk

from pitivi.utils.ui import clear_styles

class BarWindow(Gtk.Window):

    def __init__(self, app):
        self.app = app
        Gtk.Window.__init__(self, title="")
        self.set_size_request(1000, 50)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_decorated(False)
        self.add(vbox)

        completion = self.entry_suggestion()

        self.entry = Gtk.SearchEntry()
        clear_styles(self.entry)
        self.entry.set_completion(completion)
        vbox.pack_start(self.entry, True, True, 0)

        self.connect("focus-out-event", self.focus_out_cb)

    def entry_suggestion(self):
        completion = Gtk.EntryCompletion()
        store = Gtk.ListStore(str, str)

        for i in self.app.shortcuts.group_actions:
            for j in self.app.shortcuts.group_actions[i]:
                store.append([j[1], self.app.get_accels_for_action(j[0])[0]])

        renderer = Gtk.CellRendererText()
        completion.pack_end(renderer, True)

        completion.set_model(store)
        completion.add_attribute(renderer, "text", 1)
        completion.set_text_column(0)
        completion.set_inline_completion(True)
        completion.set_inline_selection(True)
        completion.set_match_func(self.any_match_func)

        return completion

    def any_match_func(self, completion, entry, i):
        entry_model = completion.get_model()[i][0].lower()
        return entry.lower() in entry_model

    def focus_out_cb(self, window, unused):
        self.destroy()
        return True
