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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

"""
Render dialog
"""

import os
import gtk
import gst
import pango

from pitivi import configure
from pitivi.settings import ExportSettings
from pitivi.log.loggable import Loggable
from pitivi.ui.encodingprogress import EncodingProgressDialog
from pitivi.ui.gstwidget import GstElementSettingsDialog
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
    """Returns a nice name for the specified gst.ElementFactory instance."""
    # only replace lowercase versions of "format", "video", "audio"
    # otherwise they might be part of a trademark name
    words_to_remove = ["Muxer", "muxer", "Encoder", "encoder",
            "format", "video", "audio", "instead"]
    name = factory.get_longname()
    for word in words_to_remove:
        name = name.replace(word, "")
    return " ".join(word for word in name.split())


def extension_for_muxer(muxer):
    """Returns the file extension appropriate for the specified muxer."""
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
        "webmmux": "webm"}
    return exts.get(muxer)


def factorylist(factories):
    """Create a gtk.ListStore() of sorted, beautified factory names.

    @param factories: The factories available for creating the list. 
    @type factories: A sequence of gst.ElementFactory instances.
    """
    columns = (str, object)
    data = [(beautify_factoryname(factory), factory)
            for factory in factories
            if factory.get_rank() > 0]
    data.sort(key=lambda x: x[0])
    return model(columns, data)


class EncodingDialog(Renderer, Loggable):
    """Render dialog box.

    @ivar preferred_aencoder: The last audio encoder selected by the user.
    @type preferred_aencoder: str
    @ivar preferred_vencoder: The last video encoder selected by the user.
    @type preferred_vencoder: str
    """

    def __init__(self, app, project, pipeline=None):
        Loggable.__init__(self)

        self.app = app

        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(configure.get_ui_dir(),
            "encodingdialog.ui"))
        self._setProperties()
        self.builder.connect_signals(self)

        # UI widgets
        icon = os.path.join(configure.get_pixmap_dir(), "pitivi-render-16.png")
        self.window.set_icon_from_file(icon)

        # FIXME: re-enable this widget when bug #637078 is implemented
        self.selected_only_button.destroy()

        Renderer.__init__(self, project, pipeline)

        # Directory and Filename
        self.filebutton.set_current_folder(self.app.settings.lastExportFolder)
        self.updateFilename(self.project.name)

        # We store these so that when the user tries various container formats,
        # (AKA muxers) we select these a/v encoders, if they are compatible with
        # the current container format.
        self.preferred_vencoder = self.settings.vencoder
        self.preferred_aencoder = self.settings.aencoder

        self._initializeComboboxModels()
        self._displaySettings()
        self._displayRenderSettings()

        self.window.connect("delete-event", self._deleteEventCb)
        self.settings.connect("settings-changed", self._settingsChanged)

    def _setProperties(self):
        self.window = self.builder.get_object("render-dialog")
        self.selected_only_button = self.builder.get_object(
            "selected_only_button")
        self.frame_rate_combo = self.builder.get_object("frame_rate_combo")
        self.scale_spinbutton = self.builder.get_object("scale_spinbutton")
        self.channels_combo = self.builder.get_object("channels_combo")
        self.sample_rate_combo = self.builder.get_object(
                        "sample_rate_combo")
        self.sample_depth_combo = self.builder.get_object(
                        "sample_depth_combo")
        self.muxercombobox = self.builder.get_object("muxercombobox")
        self.audio_encoder_combo = self.builder.get_object(
            "audio_encoder_combo")
        self.video_encoder_combo = self.builder.get_object(
            "video_encoder_combo")
        self.filebutton = self.builder.get_object("filebutton")
        self.fileentry = self.builder.get_object("fileentry")
        self.resolution_label = self.builder.get_object("resolution_label")

    def _settingsChanged(self, settings):
        self.updateResolution()

    def _initializeComboboxModels(self):
        self.frame_rate_combo.set_model(frame_rates)
        self.channels_combo.set_model(audio_channels)
        self.sample_rate_combo.set_model(audio_rates)
        self.sample_depth_combo.set_model(audio_depths)
        self.muxercombobox.set_model(factorylist(ExportSettings.muxers))

    def _displaySettings(self):
        """Display the settings that also change in the ProjectSettingsDialog.
        """
        # Video settings
        set_combo_value(self.frame_rate_combo, self.settings.videorate)
        # Audio settings
        set_combo_value(self.channels_combo, self.settings.audiochannels)
        set_combo_value(self.sample_rate_combo, self.settings.audiorate)
        set_combo_value(self.sample_depth_combo, self.settings.audiodepth)

    def _displayRenderSettings(self):
        """Display the settings which can be changed only in the EncodingDialog.
        """
        # Video settings
        # note: this will trigger an update of the video resolution label
        self.scale_spinbutton.set_value(self.settings.render_scale)
        # Muxer settings
        # note: this will trigger an update of the codec comboboxes
        set_combo_value(self.muxercombobox,
            gst.element_factory_find(self.settings.muxer))

        # File
        self.filebutton.set_current_folder(self.app.settings.lastExportFolder)
        self.updateFilename(self.project.name)


    def updateFilename(self, basename):
        """Updates the filename UI element to show the specified file name."""
        extension = extension_for_muxer(self.settings.muxer)
        if extension:
            name = "%s%s%s" % (basename, os.path.extsep, extension)
        else:
            name = basename
        self.fileentry.set_text(name)

    def _muxerComboChangedCb(self, muxer_combo):
        """Handle the changing of the container format combobox."""
        muxer = get_combo_value(muxer_combo).get_name()
        self.settings.setEncoders(muxer=muxer)

        # Update the extension of the filename.
        basename = os.path.splitext(self.fileentry.get_text())[0]
        self.updateFilename(basename)

        # Update muxer-dependent widgets.
        self.muxer_combo_changing = True
        try:
            self.updateAvailableEncoders()
        finally:
            self.muxer_combo_changing = False

    def updateAvailableEncoders(self):
        """Update the encoder comboboxes to show the available encoders."""
        video_encoders = self.settings.getVideoEncoders()
        video_encoder_model = factorylist(video_encoders)
        self.video_encoder_combo.set_model(video_encoder_model)

        audio_encoders = self.settings.getAudioEncoders()
        audio_encoder_model = factorylist(audio_encoders)
        self.audio_encoder_combo.set_model(audio_encoder_model)

        self._updateEncoderCombo(
                self.video_encoder_combo, self.preferred_vencoder)
        self._updateEncoderCombo(
                self.audio_encoder_combo, self.preferred_aencoder)

    def _updateEncoderCombo(self, encoder_combo, preferred_encoder):
        """Select the specified encoder for the specified encoder combo."""
        if preferred_encoder:
            # A preferrence exists, pick it if it can be found in
            # the current model of the combobox.
            vencoder = gst.element_factory_find(preferred_encoder)
            set_combo_value(encoder_combo, vencoder, default_index=0)
        else:
            # No preferrence exists, pick the first encoder from
            # the current model of the combobox.
            encoder_combo.set_active(0)

    def _scaleSpinbuttonChangedCb(self, button):
        render_scale = self.scale_spinbutton.get_value()
        self.settings.setVideoProperties(render_scale=render_scale)
        self.updateResolution()

    def updateResolution(self):
        width, height = self.settings.getVideoWidthAndHeight(render=True)
        self.resolution_label.set_text("%d x %d" % (width, height))

    def _projectSettingsButtonClickedCb(self, button):
        from pitivi.ui.projectsettings import ProjectSettingsDialog
        dialog = ProjectSettingsDialog(self.window, self.project)
        dialog.window.connect("destroy", self._projectSettingsDestroyCb)
        dialog.window.run()

    def _projectSettingsDestroyCb(self, dialog):
        """Handle the destruction of the ProjectSettingsDialog."""
        self._displaySettings()

    def _frameRateComboChangedCb(self, combo):
        framerate = get_combo_value(combo)
        self.settings.setVideoProperties(framerate=framerate)

    def _videoEncoderComboChangedCb(self, combo):
        vencoder = get_combo_value(combo).get_name()
        self.settings.setEncoders(vencoder=vencoder)
        if not self.muxer_combo_changing:
            # The user directly changed the video encoder combo.
            self.preferred_vencoder = vencoder

    def _videoSettingsButtonClickedCb(self, button):
        self._elementSettingsDialog(self.video_encoder_combo, 'vcodecsettings')

    def _channelsComboChangedCb(self, combo):
        self.settings.setAudioProperties(nbchanns=get_combo_value(combo))

    def _sampleDepthComboChangedCb(self, combo):
        self.settings.setAudioProperties(depth=get_combo_value(combo))

    def _sampleRateComboChangedCb(self, combo):
        self.settings.setAudioProperties(rate=get_combo_value(combo))

    def _audioEncoderChangedComboCb(self, combo):
        aencoder = get_combo_value(combo).get_name()
        self.settings.setEncoders(aencoder=aencoder)
        if not self.muxer_combo_changing:
            # The user directly changed the audio encoder combo.
            self.preferred_aencoder = aencoder

    def _audioSettingsButtonClickedCb(self, button):
        self._elementSettingsDialog(self.audio_encoder_combo, 'acodecsettings')

    def _elementSettingsDialog(self, combo, settings_attr):
        factory = get_combo_value(combo)
        settings = getattr(self.settings, settings_attr)
        dialog = GstElementSettingsDialog(factory, settings)
        dialog.window.set_transient_for(self.window)

        response = dialog.window.run()
        if response == gtk.RESPONSE_OK:
            setattr(self.settings, settings_attr, dialog.getSettings())
        dialog.window.destroy()

    def _renderButtonClickedCb(self, unused_button):
        self.outfile = os.path.join(self.filebutton.get_uri(),
                                    self.fileentry.get_text())
        self.progress = EncodingProgressDialog(self.app, self)
        self.window.hide() # Hide the rendering settings dialog while rendering
        self.progress.window.show()
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

    def updatePosition(self, fraction, text):
        if self.progress:
            self.progress.updatePosition(fraction, text)

    def updateUIOnEOS(self):
        """Handle the ending or the cancellation of the render process."""
        self.progress.window.destroy()
        self.progress = None
        self.window.show()  # Show the encoding dialog again
        self.pipeline.disconnect_by_function(self._stateChanged)

    def _closeButtonClickedCb(self, unused_button):
        self.debug("Render Close button clicked")
        self.destroy()

    def _deleteEventCb(self, window, event):
        self.debug("Render window is being deleted")
        self.destroy()

    def destroy(self):
        # TODO: Do this only when the settings actually changed.
        self.project.setSettings(self.settings)
        self.window.destroy()
