# PiTiVi , Non-linear video editor
#
#       ui/audiofxlist.py
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

import gtk
import pango
from gettext import gettext as _

"""
Audio FX list widgets
"""

class AudioFxList(gtk.VBox):
    """ Widget for listing video effects """

    def __init__(self, instance):
        gtk.VBox.__init__(self)
        self.set_border_width(5)
        self.app = instance

        # model
        self.storemodel = gtk.ListStore(str, str, object)

        self.scrollwin = gtk.ScrolledWindow()
        self.scrollwin.set_policy(gtk.POLICY_NEVER,
                                  gtk.POLICY_AUTOMATIC)
        self.pack_start(self.scrollwin)

        self.iconview = gtk.IconView(self.storemodel)
        self.treeview = gtk.TreeView(self.storemodel)

        namecol = gtk.TreeViewColumn(_("Name"))
        self.treeview.append_column(namecol)
        namecell = gtk.CellRendererText()
        namecol.pack_start(namecell)
        namecol.add_attribute(namecell, "text", 0)

        namecol = gtk.TreeViewColumn(_("Description"))
        self.treeview.append_column(namecol)
        namecell = gtk.CellRendererText()
        namecell.set_property("ellipsize", pango.ELLIPSIZE_END)
        namecol.pack_start(namecell)
        namecol.add_attribute(namecell, "text", 1)

        self.scrollwin.add(self.treeview)

        self._fillUpModel()

    def _fillUpModel(self):
        for factory in self.app.effects.simple_audio:
            self.storemodel.append([factory.get_longname(),
                                    factory.get_description(),
                                    factory])
