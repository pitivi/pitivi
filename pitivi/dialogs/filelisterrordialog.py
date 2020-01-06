# -*- coding: utf-8 -*-
# Pitivi video editor
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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
"""Assets discovery errors."""
import os
from gettext import gettext as _
from urllib.parse import unquote

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from pitivi.configure import get_ui_dir
from pitivi.utils.loggable import Loggable


class FileListErrorDialog(GObject.Object, Loggable):
    """Dialog for showing errors blocking importing media files."""

    __gsignals__ = {
        'close': (GObject.SignalFlags.RUN_LAST, None, ()),
        'response': (GObject.SignalFlags.RUN_LAST, None, (object,))}

    def __init__(self, title, headline):
        GObject.Object.__init__(self)
        Loggable.__init__(self)
        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(get_ui_dir(),
                                                "filelisterrordialog.ui"))
        self.builder.connect_signals(self)

        self.window = self.builder.get_object("filelisterrordialog")
        self.window.set_modal(False)
        self.window.set_title(title)

        self.builder.get_object("headline").set_text(headline)
        self.errorvbox = self.builder.get_object("errorvbox")

    def add_failed_file(self, uri, reason=_("Unknown reason"), extra=None):
        """Adds the specified URI to the list of failures.

        Args:
            uri (str): The URI of the asset which cannot be imported.
            reason (Optional[str]): The reason of the file discovery failure.
            extra (Optional[str]): Extra information to display.
        """
        self.debug("Uri: %s, reason: %s, extra: %s", uri, reason, extra)
        exp = self.__create_file_expander(uri, reason, extra)
        self.errorvbox.pack_start(exp, False, False, 0)
        if len(self.errorvbox.get_children()) < 3:
            exp.set_expanded(True)  # Let's save the user some clicks
        exp.show_all()

    @staticmethod
    def __create_file_expander(uri, reason, extra=None):
        if uri:
            if uri.startswith("file://"):
                uri = uri[7:]
            uri = uri.split('/')[-1]
            uri = unquote(uri)
            exp = Gtk.Expander(label=uri)
        else:
            exp = Gtk.Expander(label=reason)

        textbuffer = Gtk.TextBuffer()
        table = textbuffer.get_tag_table()
        boldtag = Gtk.TextTag()
        boldtag.props.weight = Pango.Weight.BOLD
        table.add(boldtag)

        end = textbuffer.get_end_iter()
        textbuffer.insert_with_tags(end, _("Problem:") + " ", boldtag)

        end = textbuffer.get_end_iter()
        textbuffer.insert(end, "%s\n" % reason)

        if extra:
            end = textbuffer.get_end_iter()
            textbuffer.insert_with_tags(
                end, _("Extra information:") + " ", boldtag)

            end = textbuffer.get_end_iter()
            textbuffer.insert(end, "%s\n" % extra)

        textview = Gtk.TextView(buffer=textbuffer)
        textview.set_wrap_mode(Gtk.WrapMode.WORD)

        exp.add(textview)

        return exp

    def is_visible(self):
        """Returns True if the dialog is currently shown."""
        return self.window.get_property("visible")

    def destroy(self):
        """Destroys the dialog."""
        self.window.destroy()

    # Callbacks from glade

    def _close_cb(self, unused_dialog):
        """Emits the `close` signal."""
        self.emit('close')

    def _response_cb(self, unused_dialog, response):
        """Emits the `response` signal."""
        self.emit('response', response)
