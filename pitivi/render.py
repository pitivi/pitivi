# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       pitivi/render.py
#
# Copyright (c) 2009, Edward Hervey <bilboed@bilboed.com>
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
Rendering-related utilities and classes
"""

import os
import subprocess
import time

from gi.repository import GES
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk

from gettext import gettext as _

from pitivi import configure

from pitivi.check import missing_soft_deps
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import show_user_manual, path_from_uri
from pitivi.utils.ripple_update_group import RippleUpdateGroup
from pitivi.utils.ui import model, frame_rates, audio_rates,\
    audio_channels, get_combo_value, set_combo_value, beautify_ETA
from pitivi.utils.widgets import GstElementSettingsDialog


class CachedEncoderList(object):

    """
    Registry of avalaible Muxer/Audio encoder/Video Encoder. And
    avalaible combinations of those.

    You can acces directly the

    @aencoders: List of avalaible audio encoders
    @vencoders: List of avalaible video encoders
    @muxers: List of avalaible muxers
    @audio_combination: Dictionary from muxer names to compatible audio encoders ordered by Rank
    @video_combination: Dictionary from muxer names to compatible video encoders ordered by Rank


    It is a singleton.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """
        Override the new method to return the singleton instance if available.
        Otherwise, create one.
        """
        if not cls._instance:
            cls._instance = super(
                CachedEncoderList, cls).__new__(cls, *args, **kwargs)
            Gst.Registry.get().connect(
                "feature-added", cls._instance._registryFeatureAddedCb)
            cls._instance._buildEncoders()
            cls._instance._buildCombinations()
        return cls._instance

    def _buildEncoders(self):
        self.aencoders = []
        self.vencoders = []
        self.muxers = Gst.ElementFactory.list_get_elements(
            Gst.ELEMENT_FACTORY_TYPE_MUXER,
            Gst.Rank.SECONDARY)

        for fact in Gst.ElementFactory.list_get_elements(
                Gst.ELEMENT_FACTORY_TYPE_ENCODER, Gst.Rank.SECONDARY):
            klist = fact.get_klass().split('/')
            if "Video" in klist or "Image" in klist:
                self.vencoders.append(fact)
            elif "Audio" in klist:
                self.aencoders.append(fact)

    def _buildCombinations(self):
        self.audio_combination = {}
        self.video_combination = {}
        useless_muxers = set([])
        for muxer in self.muxers:
            mux = muxer.get_name()
            aencs = self._findCompatibleEncoders(self.aencoders, muxer)
            vencs = self._findCompatibleEncoders(self.vencoders, muxer)
            # only include muxers with audio and video

            if aencs and vencs:
                self.audio_combination[mux] = sorted(
                    aencs, key=lambda x: - x.get_rank())
                self.video_combination[mux] = sorted(
                    vencs, key=lambda x: - x.get_rank())
            else:
                useless_muxers.add(muxer)

        for muxer in useless_muxers:
            self.muxers.remove(muxer)

    def _findCompatibleEncoders(self, encoders, muxer, muxsinkcaps=[]):
        """ returns the list of encoders compatible with the given muxer """
        res = []
        if muxsinkcaps == []:
            muxsinkcaps = [x.get_caps() for x in muxer.get_static_pad_templates()
                           if x.direction == Gst.PadDirection.SINK]
        for encoder in encoders:
            for tpl in encoder.get_static_pad_templates():
                if tpl.direction == Gst.PadDirection.SRC:
                    if self._canSinkCaps(muxer, tpl.get_caps(), muxsinkcaps):
                        res.append(encoder)
                        break
        return res

    def _canSinkCaps(self, muxer, ocaps, muxsinkcaps=[]):
        """ returns True if the given caps intersect with some of the muxer's
        sink pad templates' caps.
        """
        # fast version
        if muxsinkcaps != []:
            for c in muxsinkcaps:
                if not c.intersect(ocaps).is_empty():
                    return True
            return False
        # slower default
        for x in muxer.get_static_pad_templates():
            if x.direction == Gst.PadDirection.SINK:
                if not x.get_caps().intersect(ocaps).is_empty():
                    return True
        return False

    # sinkcaps = (x.get_caps() for x in muxer.get_static_pad_templates() if x.direction == Gst.PadDirection.SINK)
    # for x in sinkcaps:
    #     if not x.intersect(ocaps).is_empty():
    #         return True
    # return False

    def _registryFeatureAddedCb(self, registry, feature):
        # TODO Check what feature has been added and update our lists
        pass


def beautify_factoryname(factory):
    """
    Returns a nice name for the specified Gst.ElementFactory instance.
    This is intended to remove redundant words and shorten the codec names.
    """
    # only replace lowercase versions of "format", "video", "audio"
    # otherwise they might be part of a trademark name
    words_to_remove = ["Muxer", "muxer", "Encoder", "encoder",
                       "format", "video", "audio", "instead",
                       # Incorrect naming for Sorenson Spark:
                       "Flash Video (FLV) /", ]
    words_to_replace = [["version ", "v"], ["Microsoft", "MS"], ]
    name = factory.get_longname()
    for word in words_to_remove:
        name = name.replace(word, "")
    for match, replacement in words_to_replace:
        name = name.replace(match, replacement)
    return " ".join(word for word in name.split())


def extension_for_muxer(muxer):
    """Returns the file extension appropriate for the specified muxer."""
    exts = {
        "asfmux": "asf",
        "avimux": "avi",
        "avmux_3g2": "3g2",
        "avmux_avm2": "avm2",
        "avmux_dvd": "vob",
        "avmux_flv": "flv",
        "avmux_ipod": "mp4",
        "avmux_mpeg": "mpeg",
        "avmux_mpegts": "mpeg",
        "avmux_psp": "mp4",
        "avmux_rm": "rm",
        "avmux_svcd": "mpeg",
        "avmux_swf": "swf",
        "avmux_vcd": "mpeg",
        "avmux_vob": "vob",
        "flvmux": "flv",
        "gppmux": "3gp",
        "matroskamux": "mkv",
        "mj2mux": "mj2",
        "mp4mux": "mp4",
        "mpegpsmux": "mpeg",
        "mpegtsmux": "mpeg",
        "mvemux": "mve",
        "mxfmux": "mxf",
        "oggmux": "ogv",
        "qtmux": "mov",
        "webmmux": "webm"}
    return exts.get(muxer)


def factorylist(factories):
    """Create a Gtk.ListStore() of sorted, beautified factory names.

    @param factories: The factories available for creating the list.
    @type factories: A sequence of Gst.ElementFactory instances.
    """
    columns = (str, object)
    data = [(beautify_factoryname(factory), factory)
            for factory in factories
            if factory.get_rank() > 0]
    data.sort(key=lambda x: x[0])
    return model(columns, data)


# --------------------------------- Public classes -----------------------------#

class RenderingProgressDialog(GObject.Object):

    __gsignals__ = {
        "pause": (GObject.SIGNAL_RUN_LAST, None, ()),
        "cancel": (GObject.SIGNAL_RUN_LAST, None, ()),
    }

    def __init__(self, app, parent):
        GObject.Object.__init__(self)

        self.app = app
        self.main_render_dialog = parent
        self.builder = Gtk.Builder()
        self.builder.add_from_file(
            os.path.join(configure.get_ui_dir(), "renderingprogress.ui"))
        self.builder.connect_signals(self)

        self.window = self.builder.get_object("render-progress")
        self.table1 = self.builder.get_object("table1")
        self.progressbar = self.builder.get_object("progressbar")
        self.play_pause_button = self.builder.get_object("play_pause_button")
        self.play_rendered_file_button = self.builder.get_object(
            "play_rendered_file_button")
        self.close_button = self.builder.get_object("close_button")
        self.cancel_button = self.builder.get_object("cancel_button")
        self._filesize_est_label = self.builder.get_object(
            "estimated_filesize_label")
        self._filesize_est_value_label = self.builder.get_object(
            "estimated_filesize_value_label")
        # Parent the dialog with mainwindow, since renderingdialog is hidden.
        # It allows this dialog to properly minimize together with mainwindow
        self.window.set_transient_for(self.app.gui)

        # UI widgets
        self.window.set_icon_from_file(
            configure.get_pixmap_dir() + "/pitivi-render-16.png")

        # We will only show the close/play buttons when the render is done:
        self.play_rendered_file_button.hide()
        self.close_button.hide()

    def updatePosition(self, fraction):
        self.progressbar.set_fraction(fraction)
        self.window.set_title(
            _("Rendering — %d%% complete") % int(100 * fraction))

    def updateProgressbarETA(self, time_estimation):
        # Translators: this string indicates the estimated time
        # remaining until an action (such as rendering) completes.
        # The "%s" is an already-localized human-readable duration,
        # such as "31 seconds", "1 minute" or "1 hours, 14 minutes".
        # In some languages, "About %s left" can be expressed roughly as
        # "There remains approximatively %s" (to handle gender and plurals).
        self.progressbar.set_text(_("About %s left") % time_estimation)

    def setFilesizeEstimate(self, estimated_filesize=None):
        if not estimated_filesize:
            self._filesize_est_label.hide()
            self._filesize_est_value_label.hide()
        else:
            self._filesize_est_value_label.set_text(estimated_filesize)
            self._filesize_est_label.show()
            self._filesize_est_value_label.show()

    def _deleteEventCb(self, unused_dialog_widget, unused_event):
        """If the user closes the window by pressing Escape, stop rendering"""
        self.emit("cancel")

    def _cancelButtonClickedCb(self, unused_button):
        self.emit("cancel")

    def _pauseButtonClickedCb(self, unused_button):
        self.emit("pause")

    def _closeButtonClickedCb(self, unused_button):
        self.window.destroy()
        if self.main_render_dialog.notification is not None:
            self.main_render_dialog.notification.close()
        self.main_render_dialog.window.show()

    def _playRenderedFileButtonClickedCb(self, unused_button):
        subprocess.Popen(["xdg-open", self.main_render_dialog.outfile])


class RenderDialog(Loggable):

    """Render dialog box.

    @type app: L{pitivi.application.Pitivi}
    @ivar preferred_aencoder: The last audio encoder selected by the user.
    @type preferred_aencoder: str
    @ivar preferred_vencoder: The last video encoder selected by the user.
    @type preferred_vencoder: str
    @type project: L{pitivi.project.Project}
    """
    INHIBIT_REASON = _("Currently rendering")

    _factory_formats = {}

    def __init__(self, app, project):

        from pitivi.preset import RenderPresetManager

        Loggable.__init__(self)

        self.app = app
        self.project = project
        self.system = app.system
        self._pipeline = self.project.pipeline

        self.outfile = None
        self.notification = None

        # Variables to keep track of progress indication timers:
        self._filesizeEstimateTimer = self._timeEstimateTimer = None
        self._is_rendering = False
        self._rendering_is_paused = False
        self.current_position = None
        self._time_started = 0
        self._time_spent_paused = 0  # Avoids the ETA being wrong on resume

        # Various gstreamer signal connection ID's
        # {object: sigId}
        self._gstSigId = {}

        self.render_presets = RenderPresetManager()
        self.render_presets.loadAll()

        self._createUi()

        # Directory and Filename
        self.filebutton.set_current_folder(self.app.settings.lastExportFolder)
        if not self.project.name:
            self.updateFilename(_("Untitled"))
        else:
            self.updateFilename(self.project.name)

        # We store these so that when the user tries various container formats,
        # (AKA muxers) we select these a/v encoders, if they are compatible with
        # the current container format.
        self.preferred_vencoder = self.project.vencoder
        self.preferred_aencoder = self.project.aencoder
        self.__unproxiedClips = {}

        self._initializeComboboxModels()
        self._displaySettings()
        self._displayRenderSettings()

        self.window.connect("delete-event", self._deleteEventCb)
        self.project.connect(
            "rendering-settings-changed", self._settingsChanged)

        # Monitor changes

        self.wg = RippleUpdateGroup()
        self.wg.addVertex(self.frame_rate_combo, signal="changed")
        self.wg.addVertex(self.channels_combo, signal="changed")
        self.wg.addVertex(self.sample_rate_combo, signal="changed")
        self.wg.addVertex(self.muxercombobox, signal="changed")
        self.wg.addVertex(self.audio_encoder_combo, signal="changed")
        self.wg.addVertex(self.video_encoder_combo, signal="changed")
        self.wg.addVertex(self.preset_menubutton,
                          update_func=self._updatePresetMenuButton)

        self.wg.addEdge(self.frame_rate_combo, self.preset_menubutton)
        self.wg.addEdge(self.audio_encoder_combo, self.preset_menubutton)
        self.wg.addEdge(self.video_encoder_combo, self.preset_menubutton)
        self.wg.addEdge(self.muxercombobox, self.preset_menubutton)
        self.wg.addEdge(self.channels_combo, self.preset_menubutton)
        self.wg.addEdge(self.sample_rate_combo, self.preset_menubutton)

        # Bind widgets to RenderPresetsManager
        self.render_presets.bindWidget(
            "container",
            lambda x: self.muxer_setter(self.muxercombobox, x),
            lambda: get_combo_value(self.muxercombobox).get_name())
        self.render_presets.bindWidget(
            "acodec",
            lambda x: self.acodec_setter(self.audio_encoder_combo, x),
            lambda: get_combo_value(self.audio_encoder_combo).get_name())
        self.render_presets.bindWidget(
            "vcodec",
            lambda x: self.vcodec_setter(self.video_encoder_combo, x),
            lambda: get_combo_value(self.video_encoder_combo).get_name())
        self.render_presets.bindWidget(
            "sample-rate",
            lambda x: self.sample_rate_setter(self.sample_rate_combo, x),
            lambda: get_combo_value(self.sample_rate_combo))
        self.render_presets.bindWidget(
            "channels",
            lambda x: self.channels_setter(self.channels_combo, x),
            lambda: get_combo_value(self.channels_combo))
        self.render_presets.bindWidget(
            "frame-rate",
            lambda x: self.framerate_setter(self.frame_rate_combo, x),
            lambda: get_combo_value(self.frame_rate_combo))
        self.render_presets.bindWidget(
            "height",
            lambda x: setattr(self.project, "videoheight", x),
            lambda: 0)
        self.render_presets.bindWidget(
            "width",
            lambda x: setattr(self.project, "videowidth", x),
            lambda: 0)

    def _updatePresetMenuButton(self, unused_source, unused_target):
        self.render_presets.updateMenuActions()

    def muxer_setter(self, widget, value):
        set_combo_value(widget, Gst.ElementFactory.find(value))
        self.project.setEncoders(muxer=value)

        # Update the extension of the filename.
        basename = os.path.splitext(self.fileentry.get_text())[0]
        self.updateFilename(basename)

        # Update muxer-dependent widgets.
        self.muxer_combo_changing = True
        try:
            self.updateAvailableEncoders()
        finally:
            self.muxer_combo_changing = False

    def acodec_setter(self, widget, value):
        set_combo_value(widget, Gst.ElementFactory.find(value))
        self.project.aencoder = value
        if not self.muxer_combo_changing:
            # The user directly changed the audio encoder combo.
            self.preferred_aencoder = value

    def vcodec_setter(self, widget, value):
        set_combo_value(widget, Gst.ElementFactory.find(value))
        self.project.setEncoders(vencoder=value)
        if not self.muxer_combo_changing:
            # The user directly changed the video encoder combo.
            self.preferred_vencoder = value

    def sample_rate_setter(self, widget, value):
        set_combo_value(widget, value)
        self.project.audiorate = value

    def channels_setter(self, widget, value):
        set_combo_value(widget, value)
        self.project.audiochannels = value

    def framerate_setter(self, widget, value):
        set_combo_value(widget, value)
        self.project.videorate = value

    def _createUi(self):
        builder = Gtk.Builder()
        builder.add_from_file(
            os.path.join(configure.get_ui_dir(), "renderingdialog.ui"))
        builder.connect_signals(self)

        self.window = builder.get_object("render-dialog")
        self.video_output_checkbutton = builder.get_object(
            "video_output_checkbutton")
        self.audio_output_checkbutton = builder.get_object(
            "audio_output_checkbutton")
        self.render_button = builder.get_object("render_button")
        self.video_settings_button = builder.get_object(
            "video_settings_button")
        self.audio_settings_button = builder.get_object(
            "audio_settings_button")
        self.frame_rate_combo = builder.get_object("frame_rate_combo")
        self.scale_spinbutton = builder.get_object("scale_spinbutton")
        self.channels_combo = builder.get_object("channels_combo")
        self.sample_rate_combo = builder.get_object("sample_rate_combo")
        self.muxercombobox = builder.get_object("muxercombobox")
        self.audio_encoder_combo = builder.get_object("audio_encoder_combo")
        self.video_encoder_combo = builder.get_object("video_encoder_combo")
        self.filebutton = builder.get_object("filebutton")
        self.fileentry = builder.get_object("fileentry")
        self.resolution_label = builder.get_object("resolution_label")
        self.presets_combo = builder.get_object("presets_combo")
        self.preset_menubutton = builder.get_object("preset_menubutton")

        self.video_output_checkbutton.props.active = self.project.video_profile.is_enabled()
        self.audio_output_checkbutton.props.active = self.project.audio_profile.is_enabled()

        self.__automatically_use_proxies = builder.get_object(
            "automatically_use_proxies")

        self.__always_use_proxies = builder.get_object("always_use_proxies")
        self.__always_use_proxies.props.group = self.__automatically_use_proxies

        self.__never_use_proxies = builder.get_object("never_use_proxies")
        self.__never_use_proxies.props.group = self.__automatically_use_proxies

        self.render_presets.setupUi(self.presets_combo, self.preset_menubutton)

        icon = os.path.join(configure.get_pixmap_dir(), "pitivi-render-16.png")
        self.window.set_icon_from_file(icon)
        self.window.set_transient_for(self.app.gui)

    def _settingsChanged(self, unused_project, unused_key, unused_value):
        self.updateResolution()

    def _initializeComboboxModels(self):
        # Avoid loop import
        self.frame_rate_combo.set_model(frame_rates)
        self.channels_combo.set_model(audio_channels)
        self.sample_rate_combo.set_model(audio_rates)
        self.muxercombobox.set_model(factorylist(CachedEncoderList().muxers))

    def _displaySettings(self):
        """Display the settings that also change in the ProjectSettingsDialog.
        """
        # Video settings
        set_combo_value(self.frame_rate_combo, self.project.videorate)
        # Audio settings
        set_combo_value(self.channels_combo, self.project.audiochannels)
        set_combo_value(self.sample_rate_combo, self.project.audiorate)

    def _displayRenderSettings(self):
        """Display the settings which can be changed only in the RenderDialog.
        """
        # Video settings
        # note: this will trigger an update of the video resolution label
        self.scale_spinbutton.set_value(self.project.render_scale)
        # Muxer settings
        # note: this will trigger an update of the codec comboboxes
        set_combo_value(self.muxercombobox,
                        Gst.ElementFactory.find(self.project.muxer))

    def _checkForExistingFile(self, *unused_args):
        """
        Display a warning icon and tooltip if the file path already exists.
        """
        path = self.filebutton.get_current_folder()
        if not path:
            # This happens when the window is initialized.
            return
        warning_icon = "dialog-warning"
        filename = self.fileentry.get_text()
        if not filename:
            tooltip_text = _("A file name is required.")
        elif filename and os.path.exists(os.path.join(path, filename)):
            tooltip_text = _("This file already exists.\n"
                             "If you don't want to overwrite it, choose a "
                             "different file name or folder.")
        else:
            warning_icon = None
            tooltip_text = None
        self.fileentry.set_icon_from_icon_name(1, warning_icon)
        self.fileentry.set_icon_tooltip_text(1, tooltip_text)

    def _getFilesizeEstimate(self):
        """
        Using the current render output's filesize and position in the timeline,
        return a human-readable (ex: "14 MB") estimate of the final filesize.

        Estimates in megabytes (over 30 MB) are rounded to the nearest 10 MB
        to smooth out small variations. You'd be surprised how imprecision can
        improve perceived accuracy.
        """
        if not self.current_position or self.current_position == 0:
            return None

        current_filesize = os.stat(path_from_uri(self.outfile)).st_size
        length = self.app.project_manager.current_project.timeline.props.duration
        estimated_size = float(
            current_filesize * float(length) / self.current_position)
        # Now let's make it human-readable (instead of octets).
        # If it's in the giga range (10⁹) instead of mega (10⁶), use 2 decimals
        if estimated_size > 10e8:
            gigabytes = estimated_size / (10 ** 9)
            return _("%.2f GB" % gigabytes)
        else:
            megabytes = int(estimated_size / (10 ** 6))
            if megabytes > 30:
                megabytes = int(round(megabytes, -1))  # -1 means round to 10
            return _("%d MB" % megabytes)

    def updateFilename(self, basename):
        """Updates the filename UI element to show the specified file name."""
        extension = extension_for_muxer(self.project.muxer)
        if extension:
            name = "%s%s%s" % (basename, os.path.extsep, extension)
        else:
            name = basename
        self.fileentry.set_text(name)

    def updateAvailableEncoders(self):
        """Update the encoder comboboxes to show the available encoders."""
        encoders = CachedEncoderList()
        vencoder_model = factorylist(
            encoders.video_combination[self.project.muxer])
        self.video_encoder_combo.set_model(vencoder_model)

        aencoder_model = factorylist(
            encoders.audio_combination[self.project.muxer])
        self.audio_encoder_combo.set_model(aencoder_model)

        self._updateEncoderCombo(
            self.video_encoder_combo, self.preferred_vencoder)
        self._updateEncoderCombo(
            self.audio_encoder_combo, self.preferred_aencoder)

    def _updateEncoderCombo(self, encoder_combo, preferred_encoder):
        """Select the specified encoder for the specified encoder combo."""
        if preferred_encoder:
            # A preference exists, pick it if it can be found in
            # the current model of the combobox.
            vencoder = Gst.ElementFactory.find(preferred_encoder)
            set_combo_value(encoder_combo, vencoder, default_index=0)
        else:
            # No preference exists, pick the first encoder from
            # the current model of the combobox.
            encoder_combo.set_active(0)

    def _elementSettingsDialog(self, factory, settings_attr):
        """Open a dialog to edit the properties for the specified factory.

        @param factory: An element factory whose properties the user will edit.
        @type factory: Gst.ElementFactory
        @param settings_attr: The MultimediaSettings attribute holding
        the properties.
        @type settings_attr: str
        """
        properties = getattr(self.project, settings_attr)
        self.dialog = GstElementSettingsDialog(factory, properties=properties,
                                               parent_window=self.window, isControllable=False)
        self.dialog.ok_btn.connect(
            "clicked", self._okButtonClickedCb, settings_attr)

    def _showRenderErrorDialog(self, error, unused_details):
        primary_message = _("Sorry, something didn’t work right.")
        secondary_message = _("An error occurred while trying to render your "
                              "project. You might want to check our "
                              "troubleshooting guide or file a bug report. "
                              "The GStreamer error was:") + "\n\n<i>" + str(error) + "</i>"

        dialog = Gtk.MessageDialog(transient_for=self.window, modal=True,
                                   message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK,
                                   text=primary_message)
        dialog.set_property("secondary-text", secondary_message)
        dialog.set_property("secondary-use-markup", True)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def startAction(self):
        """ Start the render process """
        self._pipeline.set_state(Gst.State.NULL)
        # FIXME: https://github.com/pitivi/gst-editing-services/issues/23
        self._pipeline.set_mode(GES.PipelineFlags.RENDER)
        encodebin = self._pipeline.get_by_name("internal-encodebin")
        self._gstSigId[encodebin] = encodebin.connect(
            "element-added", self._elementAddedCb)
        for element in encodebin.iterate_recurse():
            self._elementAddedCb(encodebin, element)
        self._pipeline.set_state(Gst.State.PLAYING)
        self._is_rendering = True
        self._time_started = time.time()

    def _cancelRender(self, *unused_args):
        self.debug("Aborting render")
        self._shutDown()
        self._destroyProgressWindow()

    def _shutDown(self):
        """Shutdown the gstreamer pipeline and disconnect from its signals."""
        self._is_rendering = False
        self._rendering_is_paused = False
        self._time_spent_paused = 0
        self._pipeline.set_state(Gst.State.NULL)
        self.__useProxyAssets()
        self._disconnectFromGst()
        self._pipeline.set_mode(GES.PipelineFlags.FULL_PREVIEW)
        self._pipeline.set_state(Gst.State.PAUSED)
        self.project.set_rendering(False)

    def _pauseRender(self, unused_progress):
        self._rendering_is_paused = self.progress.play_pause_button.get_active(
        )
        if self._rendering_is_paused:
            self._last_timestamp_when_pausing = time.time()
        else:
            self._time_spent_paused += time.time(
            ) - self._last_timestamp_when_pausing
            self.debug(
                "Resuming render after %d seconds in pause", self._time_spent_paused)
        self.app.project_manager.current_project.pipeline.togglePlayback()

    def _destroyProgressWindow(self):
        """ Handle the completion or the cancellation of the render process. """
        self.progress.window.destroy()
        self.progress = None
        self.window.show()  # Show the rendering dialog again

    def _disconnectFromGst(self):
        for obj, id in self._gstSigId.items():
            obj.disconnect(id)
        self._gstSigId = {}
        try:
            self.app.project_manager.current_project.pipeline.disconnect_by_func(
                self._updatePositionCb)
        except TypeError:
            # The render was successful, so this was already disconnected
            pass

    def destroy(self):
        self.window.destroy()

    @staticmethod
    def _maybePlayFinishedSound():
        if "pycanberra" in missing_soft_deps:
            return
        import pycanberra
        canberra = pycanberra.Canberra()
        canberra.play(1, pycanberra.CA_PROP_EVENT_ID, "complete-media", None)

    def __maybeUseSourceAsset(self):
        if self.__always_use_proxies.get_active():
            self.debug("Rendering from proxies, not replacing assets")
            return

        for layer in self.app.gui.timeline_ui.bTimeline.get_layers():
            for clip in layer.get_clips():
                if not isinstance(clip, GES.UriClip):
                    continue

                asset = clip.get_asset()
                asset_target = asset.get_proxy_target()
                if not asset_target:
                    continue

                if self.__automatically_use_proxies.get_active():
                    if self.app.proxy_manager.isAssetFormatWellSupported(
                            asset_target):
                        self.info("Asset %s format well supported, "
                                  "rendering from real asset.",
                                  asset_target.props.id)
                    else:
                        self.info("Asset %s format not well supported, "
                                  "rendering from proxy.",
                                  asset_target.props.id)
                        continue

                if not asset_target.get_error():
                    clip.set_asset(asset_target)
                    self.error("Using %s as an asset (instead of %s)",
                               asset_target.get_id(),
                               asset.get_id())
                    self.__unproxiedClips[clip] = asset

    def __useProxyAssets(self):
        for clip, asset in self.__unproxiedClips.items():
            clip.set_asset(asset)

        self.__unproxiedClips = {}

    # ------------------- Callbacks ------------------------------------------ #

    # -- UI callbacks
    def _okButtonClickedCb(self, unused_button, settings_attr):
        setattr(self.project, settings_attr, self.dialog.getSettings())
        self.dialog.window.destroy()

    def _renderButtonClickedCb(self, unused_button):
        """
        The render button inside the render dialog has been clicked,
        start the rendering process.
        """
        self.__maybeUseSourceAsset()
        self.outfile = os.path.join(self.filebutton.get_uri(),
                                    self.fileentry.get_text())
        self.progress = RenderingProgressDialog(self.app, self)
        # Hide the rendering settings dialog while rendering
        self.window.hide()

        encoder_string = self.project.vencoder
        try:
            fmt = self._factory_formats[encoder_string]
            self.project.video_profile.get_restriction()[0]["format"] = fmt
        except KeyError:
            # Now find a format to set on the restriction caps.
            # The reason is we can't send different formats on the encoders.
            factory = Gst.ElementFactory.find(self.project.vencoder)
            for struct in factory.get_static_pad_templates():
                if struct.direction == Gst.PadDirection.SINK:
                    caps = Gst.Caps.from_string(struct.get_caps().to_string())
                    fixed = caps.fixate()
                    fmt = fixed.get_structure(0).get_value("format")
                    self.project.setVideoRestriction("format", fmt)
                    self._factory_formats[encoder_string] = fmt
                    break

        self.app.gui.timeline_ui.zoomFit()
        self.project.set_rendering(True)
        self._pipeline.set_render_settings(
            self.outfile, self.project.container_profile)
        self.startAction()
        self.progress.window.show()
        self.progress.connect("cancel", self._cancelRender)
        self.progress.connect("pause", self._pauseRender)
        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        self._gstSigId[bus] = bus.connect('message', self._busMessageCb)
        self.app.project_manager.current_project.pipeline.connect(
            "position", self._updatePositionCb)
        # Force writing the config now, or the path will be reset
        # if the user opens the rendering dialog again
        self.app.settings.lastExportFolder = self.filebutton.get_current_folder(
        )
        self.app.settings.storeSettings()

    def _closeButtonClickedCb(self, unused_button):
        self.debug("Render dialog's Close button clicked")
        self.destroy()

    def _deleteEventCb(self, unused_window, unused_event):
        self.debug("Render dialog is being deleted")
        self.destroy()

    def _containerContextHelpClickedCb(self, unused_button):
        show_user_manual("codecscontainers")

    # Periodic (timer) callbacks
    def _updateTimeEstimateCb(self):
        if self._rendering_is_paused:
            return True  # Do nothing until we resume rendering
        elif self._is_rendering:
            timediff = time.time() - \
                self._time_started - self._time_spent_paused
            length = self.app.project_manager.current_project.timeline.props.duration
            totaltime = (timediff * float(length) /
                         float(self.current_position)) - timediff
            time_estimate = beautify_ETA(int(totaltime * Gst.SECOND))
            if time_estimate:
                self.progress.updateProgressbarETA(time_estimate)
            return True
        else:
            self._timeEstimateTimer = None
            self.debug("Stopping the ETA timer")
            return False  # Stop the timer

    def _updateFilesizeEstimateCb(self):
        if self._rendering_is_paused:
            return True  # Do nothing until we resume rendering
        elif self._is_rendering:
            est_filesize = self._getFilesizeEstimate()
            if est_filesize:
                self.progress.setFilesizeEstimate(est_filesize)
            return True
        else:
            self.debug("Stopping the filesize estimation timer")
            self._filesizeEstimateTimer = None
            return False  # Stop the timer

    # GStreamer callbacks
    def _busMessageCb(self, unused_bus, message):
        if message.type == Gst.MessageType.EOS:  # Render complete
            self.debug("got EOS message, render complete")
            self._shutDown()
            self.progress.progressbar.set_fraction(1.0)
            self.progress.progressbar.set_text(_("Render complete"))
            self.progress.window.set_title(_("Render complete"))
            self.progress.setFilesizeEstimate(None)
            if not self.progress.window.is_active():
                notification = _(
                    '"%s" has finished rendering.' % self.fileentry.get_text())
                self.notification = self.app.system.desktopMessage(
                    _("Render complete"), notification, "pitivi")
            self._maybePlayFinishedSound()
            self.progress.play_rendered_file_button.show()
            self.progress.close_button.show()
            self.progress.cancel_button.hide()
            self.progress.play_pause_button.hide()

        elif message.type == Gst.MessageType.ERROR:
            # Errors in a GStreamer pipeline are fatal. If we encounter one,
            # we should abort and show the error instead of sitting around.
            error, details = message.parse_error()
            self._cancelRender()
            self._showRenderErrorDialog(error, details)

        elif message.type == Gst.MessageType.STATE_CHANGED and self.progress:
            prev, state, pending = message.parse_state_changed()
            if message.src == self._pipeline:
                state_really_changed = pending == Gst.State.VOID_PENDING
                if state_really_changed:
                    if state == Gst.State.PLAYING:
                        self.debug(
                            "Rendering started/resumed, inhibiting sleep")
                        self.system.inhibitSleep(RenderDialog.INHIBIT_REASON)
                    else:
                        self.system.uninhibitSleep(RenderDialog.INHIBIT_REASON)

    def _updatePositionCb(self, unused_pipeline, position):
        """
        Unlike other progression indicator callbacks, this one occurs every time
        the pipeline emits a position changed signal, which is *very* often.
        This should only be used for a smooth progressbar/percentage, not text.
        """
        self.current_position = position
        if not self.progress or not position:
            return

        length = self.app.project_manager.current_project.timeline.props.duration
        fraction = float(min(position, length)) / float(length)
        self.progress.updatePosition(fraction)

        # In order to have enough averaging, only display the ETA after 5s
        timediff = time.time() - self._time_started
        if not self._timeEstimateTimer:
            if timediff < 6:
                self.progress.progressbar.set_text(_("Estimating..."))
            else:
                self._timeEstimateTimer = GLib.timeout_add_seconds(
                    3, self._updateTimeEstimateCb)

        # Filesize is trickier and needs more time to be meaningful:
        if not self._filesizeEstimateTimer and (fraction > 0.33 or timediff > 180):
            self._filesizeEstimateTimer = GLib.timeout_add_seconds(
                5, self._updateFilesizeEstimateCb)

    def _elementAddedCb(self, unused_bin, element):
        """
        Setting properties on Gst.Element-s has they are added to the
        Gst.Encodebin
        """
        factory = element.get_factory()
        settings = {}
        if factory == get_combo_value(self.video_encoder_combo):
            settings = self.project.vcodecsettings
        elif factory == get_combo_value(self.audio_encoder_combo):
            settings = self.project.acodecsettings

        for propname, value in settings.items():
            element.set_property(propname, value)
            self.debug("Setting %s to %s", propname, value)

    # Settings changed callbacks
    def _scaleSpinbuttonChangedCb(self, unused_button):
        render_scale = self.scale_spinbutton.get_value()
        self.project.render_scale = render_scale
        self.updateResolution()

    def updateResolution(self):
        width, height = self.project.getVideoWidthAndHeight(True)
        self.resolution_label.set_text("%d×%d" % (width, height))

    def _projectSettingsButtonClickedCb(self, unused_button):
        from pitivi.project import ProjectSettingsDialog
        dialog = ProjectSettingsDialog(self.window, self.project)
        dialog.window.run()

    def _audioOutputCheckbuttonToggledCb(self, unused_audio):
        active = self.audio_output_checkbutton.get_active()
        self.channels_combo.set_sensitive(active)
        self.sample_rate_combo.set_sensitive(active)
        self.audio_encoder_combo.set_sensitive(active)
        self.audio_settings_button.set_sensitive(active)
        self.project.audio_profile.set_enabled(active)
        self.__updateRenderButtonSensitivity()

    def _videoOutputCheckbuttonToggledCb(self, unused_video):
        active = self.video_output_checkbutton.get_active()
        self.scale_spinbutton.set_sensitive(active)
        self.frame_rate_combo.set_sensitive(active)
        self.video_encoder_combo.set_sensitive(active)
        self.video_settings_button.set_sensitive(active)
        self.project.video_profile.set_enabled(active)
        self.__updateRenderButtonSensitivity()

    def __updateRenderButtonSensitivity(self):
        video_enabled = self.video_output_checkbutton.get_active()
        audio_enabled = self.audio_output_checkbutton.get_active()
        self.render_button.set_sensitive(video_enabled or audio_enabled)

    def _frameRateComboChangedCb(self, combo):
        framerate = get_combo_value(combo)
        self.project.framerate = framerate

    def _videoEncoderComboChangedCb(self, combo):
        vencoder = get_combo_value(combo).get_name()
        self.project.vencoder = vencoder

        if not self.muxer_combo_changing:
            # The user directly changed the video encoder combo.
            self.preferred_vencoder = vencoder

    def _videoSettingsButtonClickedCb(self, unused_button):
        factory = get_combo_value(self.video_encoder_combo)
        self._elementSettingsDialog(factory, 'vcodecsettings')

    def _channelsComboChangedCb(self, combo):
        self.project.audiochannels = get_combo_value(combo)

    def _sampleRateComboChangedCb(self, combo):
        self.project.audiorate = get_combo_value(combo)

    def _audioEncoderChangedComboCb(self, combo):
        aencoder = get_combo_value(combo).get_name()
        self.project.aencoder = aencoder
        if not self.muxer_combo_changing:
            # The user directly changed the audio encoder combo.
            self.preferred_aencoder = aencoder

    def _audioSettingsButtonClickedCb(self, unused_button):
        factory = get_combo_value(self.audio_encoder_combo)
        self._elementSettingsDialog(factory, 'acodecsettings')

    def _muxerComboChangedCb(self, muxer_combo):
        """Handle the changing of the container format combobox."""
        self.project.muxer = get_combo_value(muxer_combo).get_name()

        # Update the extension of the filename.
        basename = os.path.splitext(self.fileentry.get_text())[0]
        self.updateFilename(basename)

        # Update muxer-dependent widgets.
        self.muxer_combo_changing = True
        try:
            self.updateAvailableEncoders()
        finally:
            self.muxer_combo_changing = False
