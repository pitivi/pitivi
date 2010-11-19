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
from pitivi.ui.encodingprogress import EncodingProgressDialog
from pitivi.ui.gstwidget import GstElementSettingsDialog
from pitivi.ui.glade import GladeWindow
from pitivi.actioner import Renderer
from pitivi.ui.common import\
    model,\
    frame_rates,\
    audio_rates,\
    audio_depths,\
    audio_channels,\
    get_combo_value,\
    set_combo_value

def beautify_factoryname(factory):
    # only replace lowercase versions of "format", "video", "audio"
    # otherwise they might be part of a trademark name
    words = ["Muxer", "muxer", "Encoder", "encoder",
            "format", "video", "audio", "instead"]
    name = factory.get_longname()
    for word in words:
        name = name.replace(word, "")
    parts = name.split(" ")
    ret = " ".join(p.strip() for p in parts).strip()

    return ret

def filter_recommended(muxers):
    return [m for m in muxers if m.get_rank() > 0]

def extension_for_muxer(muxer):
    exts = {
        "oggmux" : "ogm",
        "avimux" : "avi",
        "qtmux"  : "mov",
        "mxfmux" : "mxf",
        "matroskamux" : "mkv",
    }

    if muxer in exts:
        return os.path.extsep + exts[muxer]
    return ""

def factorylist(factories):
    """ Given a sequence of factories, returns a gtk.ListStore() 
    of sorted, beautified factory names """

    return model((str, object),
        sorted(((beautify_factoryname(f), f) for f in
            filter_recommended(factories)),
                key = lambda x: x[0]))

import pango

def ellipsize(combo):
    cell_view = combo.get_children()[0]
    cell_renderer = cell_view.get_cell_renderers()[0]
    cell_renderer.props.ellipsize = pango.ELLIPSIZE_END

class EncodingDialog(GladeWindow, Renderer):
    """ Encoding dialog box """
    glade_file = "encodingdialog.glade"

    def __init__(self, app, project, pipeline=None):
        Loggable.__init__(self)
        GladeWindow.__init__(self)

        self.app = app
        self.settings = project.getSettings()

        # UI widgets
        self.window.set_icon_from_file(configure.get_pixmap_dir() + "/pitivi-render-16.png")

        Renderer.__init__(self, project, pipeline)

        ellipsize(self.muxercombobox)
        ellipsize(self.audio_encoder_combo)
        ellipsize(self.video_encoder_combo)

        self.timestarted = 0
        self.containersettings = {}
        self._displaySettings()

        self.window.connect("delete-event", self._deleteEventCb)
        self.settings.connect("settings-changed", self._settingsChanged)
        self.settings.connect("encoders-changed", self._settingsChanged)

    def _settingsChanged(self, settings):
        self._updateSummary()

    def _displaySettings(self):

        # Video settings
        self.frame_rate_combo.set_model(frame_rates)

        # Audio settings
        self.channels_combo.set_model(audio_channels)

        self.sample_rate_combo.set_model(audio_rates)

        self.sample_depth_combo.set_model(audio_depths)
        # Muxer
        self.muxercombobox.set_model(factorylist(
            self.settings.muxers))

        # Encoder/Muxer settings
        self.containersettings = self.settings.containersettings


        # Summary
        self._updateSummary()

    def updateFilename(self, name):
        self.fileentry.set_text(name + extension_for_muxer(self.settings.muxer))

    def updatePosition(self, fraction, text):
        self.progressbar.set_fraction(fraction)
        self.window.set_title(_("%.0f%% rendered" % (fraction*100)))
        if text is not None:
            self.progressbar.set_text(_("About %s left") % text)

    def _muxerComboChangedCb(self, muxer):
        basename = os.path.splitext(self.fileentry.get_text())[0]
        muxer = get_combo_value(muxer).get_name()

        self.settings.setEncoders(muxer=muxer)
        self.updateFilename(basename)


    def _videoSettingsButtonClickedCb(self, button):
        self._elementSettingsDialog(self.video_encoder_combo,
            'vcodecsettings')

    def _updateSummary(self):
        text = self.settings.getVideoDescription() + "\n\n" +\
            self.settings.getAudioDescription()
        self.summary_label.props.label = text

    def _audioSettingsButtonClickedCb(self, button):
        self._elementSettingsDialog(self.audio_encoder_combo,
            'acodecsettings')

    def _elementSettingsDialog(self, combo, settings_attr):
        factory = get_combo_value(combo)
        settings = getattr(self.settings, settings_attr)
        dialog = GstElementSettingsDialog(factory, settings)

        response = dialog.run()
        if response == gtk.RESPONSE_OK:
            setattr(self.settings, settings_attr, dialog.getSettings())
        dialog.destroy()

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
