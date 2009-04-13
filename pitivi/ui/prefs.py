# PiTiVi , Non-linear video editor
#
#       ui/prefs.py
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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""
Dialog box for project settings
"""

import gtk
from gettext import gettext as _

class PreferencesDialog(gtk.Window):

    def __init__(self, instance):
        gtk.Window.__init__(self)
        self.app = instance
        self.settings = instance.settings
        self._createUi()
        self._fillContents()
        self._current = None
        self.set_border_width(12)

    def _createUi(self):
        self.set_title(_("Preferences"))
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)

        # basic layout
        vbox = gtk.VBox()
        vbox.set_spacing(6)
        button_box = gtk.HBox()
        button_box.set_spacing(5)
        button_box.set_homogeneous(False)
        pane = gtk.HPaned()
        vbox.pack_start(pane, True, True)
        vbox.pack_end(button_box, False, False)
        self.add(vbox)

        # left-side list view
        self.model = gtk.ListStore(str, str)
        self.treeview = gtk.TreeView(self.model)
        self.treeview.get_selection().connect("changed",
            self._treeSelectionChangedCb)
        ren = gtk.CellRendererText()
        col = gtk.TreeViewColumn(_("Section"), ren, text=0)
        self.treeview.append_column(col)
        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        scrolled.add(self.treeview)
        pane.pack1(scrolled)

        # preferences content region
        self.contents = gtk.ScrolledWindow()
        self.contents.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        pane.pack2(self.contents)

        # revert, close buttons
        factory_settings = gtk.Button(label=_("Restore Factory Settings"))
        factory_settings.connect("clicked", self._factorySettingsButtonCb)
        factory_settings.set_sensitive(False)
        revert_button = gtk.Button(_("Revert"))
        revert_button.connect("clicked", self._revertButtonCb)
        revert_button.set_sensitive(False)
        accept_button = gtk.Button(stock=gtk.STOCK_CLOSE)
        accept_button.connect("clicked", self._acceptButtonCb)
        button_box.pack_start(factory_settings, False, True)
        button_box.pack_end(accept_button, False, True)
        button_box.pack_end(revert_button, False, True)

    def _fillContents(self):
        self.sections = {}
        for section, options in self.settings.prefs.iteritems():
            self.model.append((_(section), section))
            widgets = gtk.Table()
            vp = gtk.Viewport()
            vp.add(widgets)
            self.sections[section] = vp
            for y, (attrname, (label, description)) in enumerate(options.iteritems()):
                widgets.attach(gtk.Label(_(label)), 0, 1, y, y + 1,
                    xoptions=0, yoptions=0)

    def _treeSelectionChangedCb(self, selection):
        model, iter = selection.get_selected()
        new = self.sections[model[iter][1]]
        if self._current != new:
            if self._current:
                self.contents.remove(self._current)
            self.contents.add(new)
            self._current = new
            new.show_all()

    def _clearHistory(self):
        pass

    def _factorySettingsButtonCb(self, unused_button):
        pass

    def _revertButtonCb(self, unused_button):
        pass

    def _acceptButtonCb(self, unused_button):
        self._clearHistory()
        self.hide()
