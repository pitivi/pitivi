# PiTiVi , Non-linear video editor
#
#       ui/mainwindow.py
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
Encoding dialog
"""

import os
import gtk
import gst

from gettext import gettext as _

import pitivi.configure as configure
from pitivi.log.loggable import Loggable
from pitivi.ui.glade import GladeWindow
from pitivi.actioner import Renderer

class EncodingDialog(GladeWindow, Renderer):
    """ Encoding dialog box """
    glade_file = "encodingdialog.glade"

    def __init__(self, app, project, pipeline=None):
        Loggable.__init__(self)
        GladeWindow.__init__(self)

        self.app = app

        # UI widgets
        self.window.set_icon_from_file(configure.get_pixmap_dir() + "/pitivi-render-16.png")

        Renderer.__init__(self, project, pipeline)

        self.timestarted = 0
        self._displaySettings()

        self.window.connect("delete-event", self._deleteEventCb)


    def _displaySettings(self):


    def updatePosition(self, fraction, text):
        self.progressbar.set_fraction(fraction)
        self.window.set_title(_("%.0f%% rendered" % (fraction*100)))
        if text is not None:
            self.progressbar.set_text(_("About %s left") % text)

        self.startAction()

    def _settingsButtonClickedCb(self, unused_button):
        dialog = ExportSettingsDialog(self.app, self.settings)
        res = dialog.run()
        dialog.hide()
        if res == gtk.RESPONSE_ACCEPT:
            self.settings = dialog.getSettings()
            self._displaySettings()
        dialog.destroy()

    def updateUIOnEOS(self):

    def _cancelButtonClickedCb(self, unused_button):
        self.debug("Cancelling !")

    def _deleteEventCb(self, window, event):
        self.debug("delete event")
