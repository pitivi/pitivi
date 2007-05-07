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
        self.window.set_geometry_hints(min_width=400, min_height=200)

    def addFailedFile(self, uri, reason=_("Unknown reason"), extra=None):
        """Add the given uri to the list of failed files. You can optionnaly
        give a string identifying the reason why the file failed to be
        discovered
        """
        gst.debug("Uri:%s, reason:%s, extra:%s" % (uri, reason, extra))
        exp = self._createFileExpander(uri, reason, extra)
        self.errorvbox.pack_start(exp)
        exp.show_all()
        #self.storemodel.append([str(uri), str(reason)])

    def _createFileExpander(self, uri, reason, extra=None):
        if uri[:7] == "file://":
            uri = uri[7:]
        exp = gtk.Expander(uri)
        if extra:
            label = gtk.Label("%s\n%s" % (reason, extra))
        else:
            label = gtk.Label(reason)
        label.set_alignment(0.0, 0.5)
        label.set_line_wrap(True)
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
