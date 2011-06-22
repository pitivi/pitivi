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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

"""
Dialog box listing files which had errors, and the reasons.
"""

import gtk
import os
import pango

from gettext import gettext as _

from urllib import unquote
from pitivi.configure import get_ui_dir
from pitivi.signalinterface import Signallable
from pitivi.log.loggable import Loggable


class FileListErrorDialog(Signallable, Loggable):
    """ Dialog box for showing errors in a list of files """
    __signals__ = {
        'close': None,
        'response': ["something"]
        }

    def __init__(self, title, headline):
        Loggable.__init__(self)
        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(get_ui_dir(),
            "filelisterrordialog.ui"))
        self.builder.connect_signals(self)

        self.window = self.builder.get_object("filelisterrordialog")
        self.window.set_modal(False)
        self.window.set_title(title)

        self.builder.get_object("headline").set_text(headline)
        self.errorvbox = self.builder.get_object("errorvbox")

    def addFailedFile(self, uri, reason=_("Unknown reason"), extra=None):
        """Add the given uri to the list of failed files. You can optionnaly
        give a string identifying the reason why the file failed to be
        discovered
        """
        self.debug("Uri:%s, reason:%s, extra:%s", uri, reason, extra)
        exp = self._createFileExpander(uri, reason, extra)
        self.errorvbox.pack_start(exp, expand=False, fill=False)
        if len(self.errorvbox.get_children()) < 3:
            exp.set_expanded(True)  # Let's save the user some clicks
        exp.show_all()
        #self.storemodel.append([str(uri), str(reason)])

    def _createFileExpander(self, uri, reason, extra=None):
        if uri:
            if uri.startswith("file://"):
                uri = uri[7:]
            uri = uri.split('/')[-1]
            uri = unquote(uri)
            exp = gtk.Expander(uri)
        else:
            exp = gtk.Expander(reason)

        textbuffer = gtk.TextBuffer()
        table = textbuffer.get_tag_table()
        boldtag = gtk.TextTag()
        boldtag.props.weight = pango.WEIGHT_BOLD
        table.add(boldtag)

        end = textbuffer.get_end_iter()
        textbuffer.insert_with_tags(end, _("Problem:") + " ", boldtag)

        end = textbuffer.get_end_iter()
        textbuffer.insert(end, "%s\n" % reason)

        if extra:
            end = textbuffer.get_end_iter()
            textbuffer.insert_with_tags(end, _("Extra information:") + " ", boldtag)

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
