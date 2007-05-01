# PiTiVi , Non-linear video editor
#
#       ui/filelisterrordialog.py
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
Dialog box listing files which had errors, and the reasons.
"""

import gobject
import gtk
import gst
import pango
from glade import GladeWindow

from gettext import gettext as _

class FileListErrorDialog(GladeWindow):
    """ Dialog box for showing errors in a list of files """
    glade_file = "filelisterrordialog.glade"
    __gsignals__ = {
        'close': (gobject.SIGNAL_RUN_LAST,
                  gobject.TYPE_NONE,
                  ( )),
        'response': (gobject.SIGNAL_RUN_LAST,
                     gobject.TYPE_NONE,
                     (gobject.TYPE_PYOBJECT, ))
        }

    def __init__(self, title, headline):
        GladeWindow.__init__(self)
        self.window.set_modal(False)
        self.widgets["headline"].set_text(headline)
        self.window.set_title(title)
        self.errorvbox = self.widgets["errorvbox"]
#        self.treeview = self.widgets["treeview"]
        self.window.set_geometry_hints(min_width=400)
#         self._setUpTreeView()

#     def _setUpTreeView(self):
#         self.storemodel = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
#         self.treeview.set_model(self.storemodel)

#         txtcell = gtk.CellRendererText()
#         txtcell.set_property("ellipsize", pango.ELLIPSIZE_START)
#         uricol = gtk.TreeViewColumn(_("File"), txtcell, text=0)
#         uricol.set_expand(True)
#         self.treeview.append_column(uricol)

#         txtcell2 = gtk.CellRendererText()
#         txtcell2.set_property("ellipsize", pango.ELLIPSIZE_END)
#         reasoncol = gtk.TreeViewColumn(_("Reason"), txtcell2, text=1)
#         reasoncol.set_expand(True)
#         self.treeview.append_column(reasoncol)

    def addFailedFile(self, uri, reason=_("Unknown reason"), extra=None):
        """Add the given uri to the list of failed files. You can optionnaly
        give a string identifying the reason why the file failed to be
        discovered
        """
        gst.debug("Uri:%s, reason:%s" % (uri, reason))
        exp = self._createFileExpander(uri, reason)
        self.errorvbox.pack_start(exp)
        exp.show_all()
        #self.storemodel.append([str(uri), str(reason)])

    def _createFileExpander(self, uri, reason):
        exp = gtk.Expander(uri)
        label = gtk.Label(reason)
        exp.add(label)
        return exp

    def isVisible(self):
        """ returns True if this dialog is currently shown """
        return self.window.get_property("visible")

    ## Callbacks from glade

    def _closeCb(self, unused_dialog):
        self.emit('close')

    def _responseCb(self, unused_dialog, response):
        self.emit('response', response)
