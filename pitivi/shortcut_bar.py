# -*- coding: utf-8 -*-
from gi.repository import Gtk
from gi.repository.Gdk import keyval_name

from pitivi.utils.ui import clear_styles

class BarWindow(Gtk.Window):

    def __init__(self, app):
        self.app = app
        Gtk.Window.__init__(self, title="")
        self.set_size_request(1000, 50)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_decorated(False)
        self.add(vbox)

        suggestions = self.entry_suggestion()

        self.entry = Gtk.SearchEntry()
        clear_styles(self.entry)
        self.entry.set_completion(suggestions)
        vbox.pack_start(self.entry, True, True, 0)

        self.connect('key-press-event', self.key_pressed_fun)

    def entry_suggestion(self):
        completion = Gtk.EntryCompletion()
        store = Gtk.ListStore(str)

        for i in self.app.shortcuts.group_actions:
            for j in self.app.shortcuts.group_actions[i]:
                store.append([j[0]])

        completion.set_model(store)
        completion.set_text_column(0)
        completion.set_inline_completion(True)
        completion.set_inline_selection(True)
        completion.set_match_func(self.any_match)

        return completion

    def any_match(self, completion, entry, i):
        entry_model = completion.get_model()[i][0].lower()
        return entry.lower() in entry_model

    def key_pressed_fun(self, widget, event):
        if keyval_name(event.keyval) == 'Escape':
            widget.destroy()
