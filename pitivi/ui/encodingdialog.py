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
import gtk
import gst

from gettext import gettext as _

import pitivi.configure as configure
from pitivi.log.loggable import Loggable
from pitivi.ui.exportsettingswidget import ExportSettingsDialog
from pitivi.ui.glade import GladeWindow
from pitivi.action import render_action_for_uri, ViewAction
from pitivi.factories.base import SourceFactory
from pitivi.settings import export_settings_to_render_settings
from pitivi.stream import AudioStream, VideoStream
from pitivi.utils import beautify_length

class EncodingDialog(GladeWindow, Loggable):
    """ Encoding dialog box """
    glade_file = "encodingdialog.glade"

    def __init__(self, app, project, pipeline=None):
        GladeWindow.__init__(self)
        Loggable.__init__(self)

        self.app = app

        # UI widgets
        self.progressbar = self.widgets["progressbar"]
        self.filebutton = self.widgets["filebutton"]
        self.settingsbutton = self.widgets["settingsbutton"]
        self.cancelbutton = self.widgets["cancelbutton"]
        self.recordbutton = self.widgets["recordbutton"]
        self.recordbutton.set_sensitive(False)
        self.vinfo = self.widgets["videoinfolabel"]
        self.ainfo = self.widgets["audioinfolabel"]
        self.window.set_icon_from_file(configure.get_pixmap_dir() + "/pitivi-render-16.png")

        # grab the Pipeline and settings
        self.project = project
        if pipeline != None:
            self.pipeline = pipeline
        else:
            self.pipeline = self.project.pipeline
        self.outfile = None
        self.rendering = False
        self.renderaction = None
        self.settings = project.getSettings()
        self.timestarted = 0
        self._displaySettings()

        self.window.connect("delete-event", self._deleteEventCb)

    def _shutDown(self):
        self.debug("shutting down")
        # Abort recording
        self.removeRecordAction()
        self.destroy()

    def _displaySettings(self):
        self.vinfo.set_markup(self.settings.getVideoDescription())
        self.ainfo.set_markup(self.settings.getAudioDescription())

    def _fileButtonClickedCb(self, button):
        dialog = gtk.FileChooserDialog(title=_("Choose file to render to"),
                                       parent=self.window,
                                       buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                                gtk.STOCK_OK, gtk.RESPONSE_ACCEPT),
                                       action=gtk.FILE_CHOOSER_ACTION_SAVE)
        dialog.set_icon_name("pitivi")
        if self.outfile:
            dialog.set_uri(self.outfile)
            dialog.set_current_name(os.path.basename(self.outfile))
        else:
            dialog.set_current_folder(self.app.settings.lastExportFolder)

        res = dialog.run()
        dialog.hide()
        if res == gtk.RESPONSE_ACCEPT:
            self.outfile = dialog.get_uri()
            button.set_label(os.path.basename(self.outfile))
            self.recordbutton.set_sensitive(True)
            self.progressbar.set_text("")
            self.app.settings.lastExportFolder = dialog.get_current_folder()
        dialog.destroy()

    def _positionCb(self, unused_pipeline, position):
        self.debug("%r %r", unused_pipeline, position)
        timediff = time.time() - self.timestarted
        length = self.project.timeline.duration
        self.progressbar.set_fraction(float(min(position, length)) / float(length))
        if timediff > 5.0 and position:
            # only display ETA after 5s in order to have enough averaging and
            # if the position is non-null
            totaltime = (timediff * float(length) / float(position)) - timediff
            length = beautify_length(int(totaltime * gst.SECOND))
            if length:
                self.progressbar.set_text(_("About %s left") % length)

    def _recordButtonClickedCb(self, unused_button):
        self.debug("Rendering")
        if self.outfile and not self.rendering:
            self.addRecordAction()
            self.pipeline.play()
            self.timestarted = time.time()
            self.rendering = True
            self.cancelbutton.set_label("gtk-cancel")
            self.progressbar.set_text(_("Rendering"))
            self.recordbutton.set_sensitive(False)
            self.filebutton.set_sensitive(False)
            self.settingsbutton.set_sensitive(False)

    def _settingsButtonClickedCb(self, unused_button):
        dialog = ExportSettingsDialog(self.app, self.settings)
        res = dialog.run()
        dialog.hide()
        if res == gtk.RESPONSE_ACCEPT:
            self.settings = dialog.getSettings()
            self._displaySettings()
        dialog.destroy()

    def _eosCb(self, unused_pipeline):
        self.debug("EOS !")
        self.rendering = False
        self.progressbar.set_text(_("Rendering Complete"))
        self.progressbar.set_fraction(1.0)
        self.recordbutton.set_sensitive(False)
        self.filebutton.set_sensitive(True)
        self.settingsbutton.set_sensitive(True)
        self.cancelbutton.set_label("gtk-close")
        self.removeRecordAction()

    def _cancelButtonClickedCb(self, unused_button):
        self.debug("Cancelling !")
        self._shutDown()

    def _deleteEventCb(self, window, event):
        self.debug("delete event")
        self._shutDown()

    def addRecordAction(self):
        self.debug("renderaction %r", self.renderaction)
        if self.renderaction == None:
            self.pipeline.connect('position', self._positionCb)
            self.pipeline.connect('eos', self._eosCb)
            self.debug("Setting pipeline to STOP")
            self.pipeline.stop()
            settings = export_settings_to_render_settings(self.settings)
            sources = [x for x in self.pipeline.factories if isinstance(x, SourceFactory)]
            self.debug("Creating RenderAction")
            self.renderaction = render_action_for_uri(self.outfile, settings, *sources)
            self.debug("setting action on pipeline")
            self.pipeline.addAction(self.renderaction)
            self.debug("Activating render action")
            self.renderaction.activate()
            self.debug("Setting all active ViewAction to sync=False")
            for ac in self.pipeline.actions:
                if isinstance(ac, ViewAction) and ac.isActive():
                    ac.setSync(False)
            self.debug("setting pipeline to PAUSE")
            self.pipeline.pause()
            self.debug("done")

    def removeRecordAction(self):
        self.debug("renderaction %r", self.renderaction)
        if self.renderaction:
            self.pipeline.stop()
            self.renderaction.deactivate()
            self.pipeline.removeAction(self.renderaction)
            self.debug("putting all active ViewActions back to sync=True")
            for ac in self.pipeline.actions:
                if isinstance(ac, ViewAction) and ac.isActive():
                    ac.setSync(True)
            self.pipeline.pause()
            self.pipeline.disconnect_by_function(self._positionCb)
            self.pipeline.disconnect_by_function(self._eosCb)
            self.renderaction = None
