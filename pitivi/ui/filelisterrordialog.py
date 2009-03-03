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

import gtk
import pango

from gettext import gettext as _

from pitivi.ui.glade import GladeWindow
from pitivi.signalinterface import Signallable
from pitivi.log.loggable import Loggable

class FileListErrorDialog(GladeWindow, Signallable, Loggable):
    """ Dialog box for showing errors in a list of files """
    glade_file = "filelisterrordialog.glade"
    __signals__ = {
        'close': None,
        'response': ["something"]
        }

    def __init__(self, title, headline):
        GladeWindow.__init__(self)
        Loggable.__init__(self)
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
        self.debug("Uri:%s, reason:%s, extra:%s", uri, reason, extra)
        exp = self._createFileExpander(uri, reason, extra)
        self.errorvbox.pack_start(exp)
        exp.show_all()
        #self.storemodel.append([str(uri), str(reason)])

    def _createFileExpander(self, uri, reason, extra=None):
        if uri[:7] == "file://":
            uri = uri[7:]
        exp = gtk.Expander(uri.split('/')[-1])

        textbuffer = gtk.TextBuffer()
        table = textbuffer.get_tag_table()
        boldtag = gtk.TextTag()
        boldtag.props.weight = pango.WEIGHT_BOLD
        table.add(boldtag)

        # <b>URI :</b> % uri
        end = textbuffer.get_end_iter()
        textbuffer.insert_with_tags(end, _("URI:"), boldtag)

        end = textbuffer.get_end_iter()
        textbuffer.insert(end, "%s\n" % uri)

        end = textbuffer.get_end_iter()
        textbuffer.insert_with_tags(end, _("Problem:"), boldtag)

        end = textbuffer.get_end_iter()
        textbuffer.insert(end, "%s\n" % reason)

        if extra:
            end = textbuffer.get_end_iter()
            textbuffer.insert_with_tags(end, _("Extra information:"), boldtag)

            end = textbuffer.get_end_iter()
            textbuffer.insert(end, "%s\n" % extra)

        textview = gtk.TextView(textbuffer)
        textview.set_wrap_mode(gtk.WRAP_WORD)

        exp.add(textview)

        return exp

    def isVisible(self):
        """ returns True if this dialog is currently shown """
        return self.window.get_property("visible")

    ## Callbacks from glade

    def _closeCb(self, unused_dialog):
        self.emit('close')

    def _responseCb(self, unused_dialog, response):
        self.emit('response', response)
