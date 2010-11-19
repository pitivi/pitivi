# PiTiVi , Non-linear video editor
#
#       ui/mainwindow.py
#
# Copyright (c) 2010, Brandon Lewis <brandon.lewis@collabora.co.uk>
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
Encoding dialog
"""

import gtk
import gst
from pitivi.ui.glade import GladeWindow
import pitivi.configure as configure
from gettext import gettext as _
import gobject
from pitivi.signalinterface import Signallable

class EncodingProgressDialog(GladeWindow, Signallable):

    glade_file = "encodingprogress.glade"

    __signals__ = {
        "pause": [],
        "cancel": [],
    }

    def __init__(self, app, parent):
        GladeWindow.__init__(self)

        self.app = app
        self.window.set_transient_for(parent.window)

        # UI widgets
        self.window.set_icon_from_file(configure.get_pixmap_dir() + "/pitivi-render-16.png")

    def updatePosition(self, fraction, estimated):
        self.progressbar.set_fraction(fraction)

        text = _("%d%% Rendered") % int(100 * fraction)
        if estimated:
            text += _(", about %s left") % estimated

        self.progressbar.set_text(text)

    def setState(self, state):
        if state == gst.STATE_PLAYING:
            self.play_pause_button.props.label = gtk.STOCK_MEDIA_PAUSE
        else:
            self.play_pause_button.props.label = 'pitivi-render'

    def _cancelButtonClickedCb(self, unused_button):
        self.emit("cancel")

    def _pauseButtonClickedCb(self, unused_button):
        self.emit("pause")
