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
        "asfmux": "asf",
        "avimux" : "avi",
        "ffmux_3g2": "3g2",
        "ffmux_avm2": "avm2",
        "ffmux_dvd": "vob",
        "ffmux_flv": "flv",
        "ffmux_ipod": "mp4",
        "ffmux_mpeg": "mpeg",
        "ffmux_mpegts": "mpeg",
        "ffmux_psp": "mp4",
        "ffmux_rm": "rm",
        "ffmux_svcd": "mpeg",
        "ffmux_swf": "swf",
        "ffmux_vcd": "mpeg",
        "ffmux_vob": "vob",
        "flvmux": "flv",
        "gppmux": "3gp",
        "matroskamux" : "mkv",
        "mj2mux": "mj2",
        "mp4mux": "mp4",
        "mpegpsmux": "mpeg",
        "mpegtsmux": "mpeg",
        "mvemux": "mve",
        "mxfmux" : "mxf",
        "oggmux" : "ogv",
        "qtmux"  : "mov",
        "webmmux": "webm",
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

class EncodingDialog(GladeWindow, Renderer, Loggable):
    """ Encoding dialog box """
    glade_file = "encodingdialog.glade"

    def __init__(self, app, project, pipeline=None):
        Loggable.__init__(self)
        GladeWindow.__init__(self)

        self.app = app
        self.project = project
        # clone the current project settings
        self.original_settings = self.project.getSettings()
        self.settings = self.original_settings.copy()
        self.project.setSettings(self.settings)

        # UI widgets
        self.window.set_icon_from_file(configure.get_pixmap_dir() + "/pitivi-render-16.png")

        Renderer.__init__(self, project, pipeline)

        ellipsize(self.muxercombobox)
        ellipsize(self.audio_encoder_combo)
        ellipsize(self.video_encoder_combo)

        self.timestarted = 0
        self._displaySettings()

        self.window.connect("delete-event", self._deleteEventCb)
        self.settings.connect("settings-changed", self._settingsChanged)
        self.settings.connect("encoders-changed", self._settingsChanged)

    def _settingsChanged(self, settings):
        self._updateSummary()
        self.updateResolution()

    def _displaySettings(self):
        self.width = self.settings.videowidth
        self.height = self.settings.videoheight

        # Video settings
        self.frame_rate_combo.set_model(frame_rates)
        set_combo_value(self.frame_rate_combo, self.settings.videorate)
        self.scale_spinbutton.set_value(100)
        self.updateResolution()

        # Audio settings
        self.channels_combo.set_model(audio_channels)
        set_combo_value(self.channels_combo, self.settings.audiochannels)

        self.sample_rate_combo.set_model(audio_rates)
        set_combo_value(self.sample_rate_combo, self.settings.audiorate)

        self.sample_depth_combo.set_model(audio_depths)
        set_combo_value(self.sample_depth_combo, self.settings.audiodepth)

        # Muxer
        self.muxercombobox.set_model(factorylist(
            self.settings.muxers))
        # note: this will trigger an update of the codec comboboxes
        set_combo_value(self.muxercombobox,
            gst.element_factory_find(self.settings.muxer))

        # Encoder/Muxer settings

        # File
        self.filebutton.set_current_folder(self.app.settings.lastExportFolder)
        self.updateFilename(self.project.name)

        # Summary
        self._updateSummary()

    def updateFilename(self, name):
        self.fileentry.set_text(name + extension_for_muxer(self.settings.muxer))

    def _muxerComboChangedCb(self, muxer):
        basename = os.path.splitext(self.fileentry.get_text())[0]
        muxer = get_combo_value(muxer).get_name()

        self.settings.setEncoders(muxer=muxer)
        self.updateFilename(basename)

        # update muxer-dependent video widgets
        self.video_encoder_combo.set_model(factorylist(
            self.settings.getVideoEncoders()))
        self.video_encoder_combo.set_active(0)

        # update muxer-dependent audio widgets
        self.audio_encoder_combo.set_model(factorylist(
            self.settings.getAudioEncoders()))
        self.audio_encoder_combo.set_active(0)

    # TODO: selected-only changed

    # TODO: draft quality changed

    def _scaleSpinbuttonChangedCb(self, button):
        width, height = self.updateResolution()
        self.settings.setVideoProperties(width=width, height=height)

    def updateResolution(self):
        scale = self.scale_spinbutton.get_value() / 100
        width = int(self.width * scale)
        height = int(self.height * scale)
        self.resolution_label.set_text("%d x %d" % (width, height))
        return width, height

    def _projectSettingsButtonClickedCb(self, button):
        from pitivi.ui.projectsettings import ProjectSettingsDialog
        self.settings.setVideoProperties(width=self.width, height=self.height)
        d = ProjectSettingsDialog(self.window, self.project)
        d.window.connect("destroy", self._projectSettingsDestroyCb)
        d.show()

    def _projectSettingsDestroyCb(self, dialog):
        self.width = self.settings.videowidth
        self.height = self.settings.videoheight
        width, height = self.updateResolution()
        self.settings.setVideoProperties(width=width, height=height)
        self._displaySettings()

    def _frameRateComboChangedCb(self, combo):
        framerate = get_combo_value(combo)
        self.settings.setVideoProperties(framerate=framerate)

    def _videoEncoderComboChangedCb(self, combo):
        name = get_combo_value(combo).get_name()
        self.settings.setEncoders(vencoder=name)

    def _videoSettingsButtonClickedCb(self, button):
        self._elementSettingsDialog(self.video_encoder_combo,
            'vcodecsettings')

    def _channelsComboChangedCb(self, combo):
        self.settings.setAudioProperties(nbchanns=get_combo_value(combo))

    def _sampleDepthComboChangedCb(self, combo):
        self.settings.setAudioProperties(depth=get_combo_value(combo))

    def _sampleRateComboChangedCb(self, combo):
        self.settings.setAudioProperties(rate=get_combo_value(combo))

    def _audioEncoderChangedComboCb(self, combo):
        name = get_combo_value(combo).get_name()
        self.settings.setEncoders(aencoder=name)

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

    def _renderButtonClickedCb(self, unused_button):
        self.outfile = self.filebutton.get_uri() + "/" + self.fileentry.get_text()
        self.progress = EncodingProgressDialog(self.app, self)
        self.window.hide() # Hide the rendering settings dialog while rendering
        self.progress.show()
        self.startAction()
        self.progress.connect("cancel", self._cancelRender)
        self.progress.connect("pause", self._pauseRender)
        self.pipeline.connect("state-changed", self._stateChanged)

    def _cancelRender(self, progress):
        self.debug("aborting render")
        self.shutdown()

    def _pauseRender(self, progress):
        self.pipeline.togglePlayback()

    def _stateChanged(self, pipeline, state):
        self.progress.setState(state)

    def _settingsButtonClickedCb(self, unused_button):
        dialog = ExportSettingsDialog(self.app, self.settings)
        res = dialog.run()
        dialog.hide()
        if res == gtk.RESPONSE_ACCEPT:
            self.settings = dialog.getSettings()
            self._displaySettings()
        dialog.destroy()

    def updatePosition(self, fraction, text):
        self.progress.updatePosition(fraction, text)

    def updateUIOnEOS(self):
        """
        When a render completes or is cancelled, update the UI
        """
        self.progress.destroy()
        self.window.show()  # Show the encoding dialog again
        self.pipeline.disconnect_by_function(self._stateChanged)

    def _cancelButtonClickedCb(self, unused_button):
        self.debug("Cancelling !")
        self.destroy()

    def _deleteEventCb(self, window, event):
        self.debug("delete event")
        self.destroy()

    def destroy(self):
        self.project.setSettings(self.original_settings)
        GladeWindow.destroy(self)
