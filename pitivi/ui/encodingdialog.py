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
import time
import gobject
import gtk
import gst
from gettext import gettext as _
import pitivi.configure as configure
from pitivi.ui.exportsettingswidget import ExportSettingsDialog
from pitivi.ui.glade import GladeWindow

class EncodingDialog(GladeWindow):
    """ Encoding dialog box """
    glade_file = "encodingdialog.glade"

    def __init__(self, project, instance):
        GladeWindow.__init__(self)
        self.pitivi = instance
        self.project = project
        self.bin = project.getBin()
        self.bus = self.bin.get_bus()
        self.bus.add_signal_watch()
        self.eosid = self.bus.connect("message::eos", self._eosCb)
        self.outfile = None
        self.progressbar = self.widgets["progressbar"]
        self.filebutton = self.widgets["filebutton"]
        self.settingsbutton = self.widgets["settingsbutton"]
        self.cancelbutton = self.widgets["cancelbutton"]
        self.recordbutton = self.widgets["recordbutton"]
        self.recordbutton.set_sensitive(False)
        self.positionhandler = 0
        self.rendering = False
        self.settings = project.getSettings()
        self.timestarted = 0
        self.vinfo = self.widgets["videoinfolabel"]
        self.ainfo = self.widgets["audioinfolabel"]
        self.window.set_icon_from_file(configure.get_pixmap_dir() + "/pitivi-render-16.png")
        self._displaySettings()

    def _displaySettings(self):
        self.vinfo.set_markup(self.settings.getVideoDescription())
        self.ainfo.set_markup(self.settings.getAudioDescription())

    def _fileButtonClickedCb(self, button):

        dialog = gtk.FileChooserDialog(title=_("Choose file to render to"),
                                       parent=self.window,
                                       buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                                gtk.STOCK_OK, gtk.RESPONSE_ACCEPT),
                                       action=gtk.FILE_CHOOSER_ACTION_SAVE)
        if self.outfile:
            dialog.set_current_name(self.outfile)
        res = dialog.run()
        dialog.hide()
        if res == gtk.RESPONSE_ACCEPT:
            self.outfile = dialog.get_uri()
            button.set_label(os.path.basename(self.outfile))
            self.recordbutton.set_sensitive(True)
            self.progressbar.set_text("")
        dialog.destroy()

    def _positionCb(self, unused_playground, unused_smartbin, position):
        timediff = time.time() - self.timestarted
        self.progressbar.set_fraction(float(min(position, self.bin.length)) / float(self.bin.length))
        if timediff > 5.0 and position:
            # only display ETA after 5s in order to have enough averaging and
            # if the position is non-null
            totaltime = (timediff * float(self.bin.length) / float(position)) - timediff
            self.progressbar.set_text(_("Finished in %dm%ds") % (int(totaltime) / 60,
                                                              int(totaltime) % 60))

    def _recordButtonClickedCb(self, unused_button):
        if self.outfile and not self.rendering:
            if self.bin.record(self.outfile, self.settings):
                self.timestarted = time.time()
                self.positionhandler = self.pitivi.playground.connect('position', self._positionCb)
                self.rendering = True
                self.cancelbutton.set_label("gtk-cancel")
                self.progressbar.set_text(_("Rendering"))
                self.recordbutton.set_sensitive(False)
                self.filebutton.set_sensitive(False)
                self.settingsbutton.set_sensitive(False)
            else:
                self.progressbar.set_text(_("Couldn't start rendering"))

    def _settingsButtonClickedCb(self, unused_button):
        dialog = ExportSettingsDialog(self.settings)
        res = dialog.run()
        dialog.hide()
        if res == gtk.RESPONSE_ACCEPT:
            self.settings = dialog.getSettings()
            self._displaySettings()
        dialog.destroy()

    def do_destroy(self):
        gst.debug("cleaning up...")
        self.bus.remove_signal_watch()
        gobject.source_remove(self.eosid)

    def _eosCb(self, unused_bus, unused_message):
        self.rendering = False
        if self.positionhandler:
            self.pitivi.playground.disconnect(self.positionhandler)
            self.positionhandler = 0
        self.progressbar.set_text(_("Rendering Complete"))
        self.progressbar.set_fraction(1.0)
        self.recordbutton.set_sensitive(True)
        self.filebutton.set_sensitive(True)
        self.settingsbutton.set_sensitive(True)
        self.cancelbutton.set_label("gtk-close")

    def _cancelButtonClickedCb(self, unused_button):
        self.bin.stopRecording()
        if self.positionhandler:
            self.pitivi.playground.disconnect(self.positionhandler)
            self.positionhandler = 0
        self.pitivi.playground.pause()
        self.destroy()
