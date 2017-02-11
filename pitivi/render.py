# -*- coding: utf-8 -*-
# Pitivi video editor
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
"""Rendering-related classes and utilities."""
import os
import time
from gettext import gettext as _

from gi.repository import GES
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk

from pitivi import configure
from pitivi.check import missing_soft_deps
from pitivi.preset import EncodingTargetManager
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import path_from_uri
from pitivi.utils.misc import show_user_manual
from pitivi.utils.ripple_update_group import RippleUpdateGroup
from pitivi.utils.ui import audio_channels
from pitivi.utils.ui import audio_rates
from pitivi.utils.ui import beautify_ETA
from pitivi.utils.ui import frame_rates
from pitivi.utils.ui import get_combo_value
from pitivi.utils.ui import set_combo_value
from pitivi.utils.widgets import GstElementSettingsDialog
from pitivi.utils.widgets import TextWidget


class Encoders(Loggable):
    """Registry of avalaible Muxers, Audio encoders and Video encoders.

    Also keeps the avalaible combinations of those.

    It is a singleton. Use `Encoders()` to access the instance.

    Attributes:
        supported_muxers (List[Gst.ElementFactory]): The supported available
            muxers.
        supported_aencoders (List[Gst.ElementFactory]): The supported available
            audio encoders.
        supported_vencoders (List[Gst.ElementFactory]): The supported available
            video encoders.
        muxers (List[Gst.ElementFactory]): The available muxers.
        aencoders (List[Gst.ElementFactory]): The available audio encoders.
        vencoders (List[Gst.ElementFactory]): The available video encoders.
        compatible_audio_encoders (dict): Maps each muxer name to a list of
            compatible audio encoders ordered by rank.
        compatible_video_encoders (dict): Maps each muxer name to a list of
            compatible video encoders ordered by rank.
        default_muxer (str): The factory name of the default muxer.
        default_audio_encoder (str): The factory name of the default audio
            encoder.
        default_video_encoder (str): The factory name of the default video
            encoder.
    """

    OGG = "oggmux"
    MKV = "matroskamux"
    MP4 = "mp4mux"
    QUICKTIME = "qtmux"
    WEBM = "webmmux"

    AAC = "voaacenc"
    AC3 = "avenc_ac3_fixed"
    OPUS = "opusenc"
    VORBIS = "vorbisenc"

    JPEG = "jpegenc"
    THEORA = "theoraenc"
    VP8 = "vp8enc"
    X264 = "x264enc"

    SUPPORTED_ENCODERS_COMBINATIONS = [
        (OGG, VORBIS, THEORA),
        (OGG, OPUS, THEORA),
        (WEBM, VORBIS, VP8),
        (WEBM, OPUS, VP8),
        (MP4, AAC, X264),
        (MP4, AC3, X264),
        (QUICKTIME, AAC, JPEG),
        (MKV, OPUS, X264),
        (MKV, VORBIS, X264),
        (MKV, OPUS, JPEG),
        (MKV, VORBIS, JPEG)]
    """The combinations of muxers and encoders which are supported.

    Mirror of GES_ENCODING_TARGET_COMBINATIONS from
    https://cgit.freedesktop.org/gstreamer/gst-editing-services/tree/tests/validate/geslaunch.py
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Returns the singleton instance."""
        if not cls._instance:
            cls._instance = super(Encoders, cls).__new__(cls)
            # We have to initialize the instance here, otherwise
            # __init__ is called every time we use Encoders().
            Loggable.__init__(cls._instance)
            cls._instance._load_encoders()
            cls._instance._load_combinations()
        return cls._instance

    def _load_encoders(self):
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

    def _load_combinations(self):
        self.compatible_audio_encoders = {}
        self.compatible_video_encoders = {}
        useless_muxers = set()
        for muxer in self.muxers:
            aencs = self._find_compatible_encoders(self.aencoders, muxer)
            vencs = self._find_compatible_encoders(self.vencoders, muxer)
            if not aencs or not vencs:
                # The muxer is not compatible with no video encoder or
                # with no audio encoder.
                useless_muxers.add(muxer)
                continue

            muxer_name = muxer.get_name()
            self.compatible_audio_encoders[muxer_name] = aencs
            self.compatible_video_encoders[muxer_name] = vencs

        for muxer in useless_muxers:
            self.muxers.remove(muxer)

        self.factories_by_name = dict([(fact.get_name(), fact)
                                       for fact in self.muxers + self.aencoders + self.vencoders])

        good_muxers, good_aencoders, good_vencoders = zip(*self.SUPPORTED_ENCODERS_COMBINATIONS)
        self.supported_muxers = set([muxer
                                     for muxer in self.muxers
                                     if muxer.get_name() in good_muxers])
        self.supported_aencoders = set([encoder
                                        for encoder in self.aencoders
                                        if encoder.get_name() in good_aencoders])
        self.supported_vencoders = set([encoder
                                        for encoder in self.vencoders
                                        if encoder.get_name() in good_vencoders])

        self.default_muxer, \
            self.default_audio_encoder, \
            self.default_video_encoder = self._pick_defaults()

    def _find_compatible_encoders(self, encoders, muxer):
        """Returns the list of encoders compatible with the specified muxer."""
        res = []
        sink_caps = [template.get_caps()
                     for template in muxer.get_static_pad_templates()
                     if template.direction == Gst.PadDirection.SINK]
        for encoder in encoders:
            for template in encoder.get_static_pad_templates():
                if not template.direction == Gst.PadDirection.SRC:
                    continue
                if self._can_muxer_sink_caps(template.get_caps(), sink_caps):
                    res.append(encoder)
                    break
        return sorted(res, key=lambda encoder: - encoder.get_rank())

    def _can_muxer_sink_caps(self, output_caps, sink_caps):
        """Checks whether the specified caps match the muxer's receptors."""
        for caps in sink_caps:
            if not caps.intersect(output_caps).is_empty():
                return True
        return False

    def _pick_defaults(self):
        """Picks the defaults for new projects.

        Returns:
            (str, str, str): The muxer, audio encoder, video encoder.
        """
        for muxer, audio, video in self.SUPPORTED_ENCODERS_COMBINATIONS:
            if muxer not in self.factories_by_name or \
                    audio not in self.factories_by_name or \
                    video not in self.factories_by_name:
                continue
            self.info("Default encoders: %s, %s, %s", muxer, audio, video)
            return muxer, audio, video
        self.warning("No good combination of container and encoders available.")
        return Encoders.OGG, Encoders.VORBIS, Encoders.THEORA

    def is_supported(self, factory):
        """Returns whether the specified factory is supported."""
        if type(factory) is str:
            factory = self.factories_by_name[factory]
        return factory in self.supported_muxers or\
            factory in self.supported_aencoders or\
            factory in self.supported_vencoders


def beautify_factory_name(factory):
    """Returns a nice name for the specified Gst.ElementFactory instance.

    Intended for removing redundant words and shorten the codec names.

    Args:
        factory (Gst.ElementFactory): The factory which needs to be displayed.

    Returns:
        str: Cleaned up name.
    """
    # Only replace lowercase versions of "format", "video", "audio"
    # otherwise they might be part of a trademark name.
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


def extension_for_muxer(muxer_name):
    """Returns the file extension appropriate for the specified muxer.

    Args:
        muxer_name (str): The name of the muxer factory.
    """
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
    return exts.get(muxer_name)


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
        """Stops the rendering."""
        # The user closed the window by pressing Escape.
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
        uri = Gst.filename_to_uri(self.main_render_dialog.outfile)
        Gio.AppInfo.launch_default_for_uri(uri, None)


class RenderDialog(Loggable):
    """Render dialog box.

    Args:
        app (Pitivi): The app.
        project (Project): The project to be rendered.

    Attributes:
        preferred_aencoder (str): The last audio encoder selected by the user.
        preferred_vencoder (str): The last video encoder selected by the user.
    """
    INHIBIT_REASON = _("Currently rendering")

    _factory_formats = {}

    def __init__(self, app, project):
        Loggable.__init__(self)

        self.app = app
        self.project = project
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

        self.render_presets = EncodingTargetManager(project)
        self.render_presets.connect('profile-selected', self._encoding_profile_selected_cb)

        # Whether encoders changing are a result of changing the muxer.
        self.muxer_combo_changing = False
        self._createUi()

        # Directory and Filename
        self.filebutton.set_current_folder(self.app.settings.lastExportFolder)
        if not self.project.name:
            self.updateFilename(_("Untitled"))
        else:
            self.updateFilename(self.project.name)

        self._setting_encoding_profile = False

        # We store these so that when the user tries various container formats,
        # (AKA muxers) we select these a/v encoders, if they are compatible with
        # the current container format.
        self.preferred_vencoder = self.project.vencoder
        self.preferred_aencoder = self.project.aencoder
        self.__unproxiedClips = {}

        self.frame_rate_combo.set_model(frame_rates)
        self.channels_combo.set_model(audio_channels)
        self.sample_rate_combo.set_model(audio_rates)
        self.__initialize_muxers_model()
        self._displaySettings()
        self._displayRenderSettings()

        self.window.connect("delete-event", self._deleteEventCb)
        self.project.connect(
            "rendering-settings-changed", self._settings_changed_cb)

        # Monitor changes

        self.wg = RippleUpdateGroup()
        self.wg.addVertex(self.frame_rate_combo, signal="changed")
        self.wg.addVertex(self.channels_combo, signal="changed")
        self.wg.addVertex(self.sample_rate_combo, signal="changed")
        self.wg.addVertex(self.muxer_combo, signal="changed")
        self.wg.addVertex(self.audio_encoder_combo, signal="changed")
        self.wg.addVertex(self.video_encoder_combo, signal="changed")
        self.wg.addVertex(self.preset_menubutton,
                          update_func=self._updatePresetMenuButton)

        self.wg.addEdge(self.frame_rate_combo, self.preset_menubutton)
        self.wg.addEdge(self.audio_encoder_combo, self.preset_menubutton)
        self.wg.addEdge(self.video_encoder_combo, self.preset_menubutton)
        self.wg.addEdge(self.muxer_combo, self.preset_menubutton)
        self.wg.addEdge(self.channels_combo, self.preset_menubutton)
        self.wg.addEdge(self.sample_rate_combo, self.preset_menubutton)

    def _encoding_profile_selected_cb(self, unused_target, encoding_profile):
        self._set_encoding_profile(encoding_profile)

    def _set_encoding_profile(self, encoding_profile, recursing=False):
        old_profile = self.project.container_profile

        def rollback(self):
            if recursing:
                return

            self._set_encoding_profile(old_profile, True)

        def factory(x):
            return Encoders().factories_by_name.get(getattr(self.project, x))

        self.project.set_container_profile(encoding_profile)
        self._setting_encoding_profile = True

        if not set_combo_value(self.muxer_combo, factory('muxer')):
            return rollback()

        self.updateAvailableEncoders()
        for i, (combo, value) in enumerate([
                (self.audio_encoder_combo, factory('aencoder')),
                (self.video_encoder_combo, factory('vencoder')),
                (self.sample_rate_combo, self.project.audiorate),
                (self.channels_combo, self.project.audiochannels),
                (self.frame_rate_combo, self.project.videorate)]):
            if value is None:
                self.error("%d - Got no value for combo %s... rolling back",
                           i, combo)
                return rollback(self)

            if not set_combo_value(combo, value):
                self.error("%d - Could not set value %s for combo %s... rolling back",
                           i, value, combo)
                return rollback(self)

        self.updateResolution()
        self._setting_encoding_profile = False

    def _updatePresetMenuButton(self, unused_source, unused_target):
        self.render_presets.updateMenuActions()

    def muxer_setter(self, widget, muxer_name):
        set_combo_value(widget, Encoders().factories_by_name.get(muxer_name))
        self.project.setEncoders(muxer=muxer_name)

        # Update the extension of the filename.
        basename = os.path.splitext(self.fileentry.get_text())[0]
        self.updateFilename(basename)

        # Update muxer-dependent widgets.
        self.updateAvailableEncoders()

    def acodec_setter(self, widget, aencoder_name):
        set_combo_value(widget, Encoders().factories_by_name.get(aencoder_name))
        self.project.aencoder = aencoder_name
        if not self.muxer_combo_changing:
            # The user directly changed the audio encoder combo.
            self.preferred_aencoder = aencoder_name

    def vcodec_setter(self, widget, vencoder_name):
        set_combo_value(widget, Encoders().factories_by_name.get(vencoder_name))
        self.project.setEncoders(vencoder=vencoder_name)
        if not self.muxer_combo_changing:
            # The user directly changed the video encoder combo.
            self.preferred_vencoder = vencoder_name

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
        self.frame_rate_combo.set_model(frame_rates)
        self.scale_spinbutton = builder.get_object("scale_spinbutton")
        self.channels_combo = builder.get_object("channels_combo")
        self.channels_combo.set_model(audio_channels)
        self.sample_rate_combo = builder.get_object("sample_rate_combo")
        self.muxer_combo = builder.get_object("muxercombobox")
        self.audio_encoder_combo = builder.get_object("audio_encoder_combo")
        self.video_encoder_combo = builder.get_object("video_encoder_combo")
        self.filebutton = builder.get_object("filebutton")
        self.fileentry = builder.get_object("fileentry")
        self.resolution_label = builder.get_object("resolution_label")
        self.preset_menubutton = builder.get_object("preset_menubutton")

        text_widget = TextWidget(matches=r'^[a-z][a-z-0-9-]+$', combobox=True)
        self.presets_combo = text_widget.combo
        preset_table = builder.get_object("preset_table")
        preset_table.attach(text_widget, 1, 0, 1, 1)
        text_widget.show()

        self.video_output_checkbutton.props.active = self.project.video_profile.is_enabled()
        self.audio_output_checkbutton.props.active = self.project.audio_profile.is_enabled()

        self.__automatically_use_proxies = builder.get_object(
            "automatically_use_proxies")

        self.__always_use_proxies = builder.get_object("always_use_proxies")
        self.__always_use_proxies.props.group = self.__automatically_use_proxies

        self.__never_use_proxies = builder.get_object("never_use_proxies")
        self.__never_use_proxies.props.group = self.__automatically_use_proxies

        self.render_presets.setupUi(self.presets_combo, self.preset_menubutton)
        self.render_presets.loadAll()

        icon = os.path.join(configure.get_pixmap_dir(), "pitivi-render-16.png")
        self.window.set_icon_from_file(icon)
        self.window.set_transient_for(self.app.gui)

    def _settings_changed_cb(self, unused_project, key, value):
        self.updateResolution()

    def __initialize_muxers_model(self):
        # By default show only supported muxers and encoders.
        model = self.create_combobox_model(Encoders().muxers)
        self.muxer_combo.set_model(model)

    def create_combobox_model(self, factories):
        """Creates a model for a combobox showing factories.

        Args:
            combobox (Gtk.ComboBox): The combobox to setup.
            factories (List[Gst.ElementFactory]): The factories to display.

        Returns:
            Gtk.ListStore: The model with (display name, factory, unsupported).
        """
        model = Gtk.TreeStore(str, object)
        data_supported = []
        data_unsupported = []
        for factory in factories:
            supported = Encoders().is_supported(factory)
            row = (beautify_factory_name(factory), factory)
            if supported:
                data_supported.append(row)
            else:
                data_unsupported.append(row)

        data_supported.sort()
        for row in data_supported:
            model.append(None, row)

        # Translators: This item appears in a combobox's popup and
        # contains as children the unsupported (but still available)
        # muxers and encoders.
        unsupported_iter = model.append(None, (_("Unsupported"), None))
        data_unsupported.sort()
        for row in data_unsupported:
            model.append(unsupported_iter, row)

        return model

    def _displaySettings(self):
        """Displays the settings also in the ProjectSettingsDialog."""
        # Video settings
        set_combo_value(self.frame_rate_combo, self.project.videorate)
        # Audio settings
        set_combo_value(self.channels_combo, self.project.audiochannels)
        set_combo_value(self.sample_rate_combo, self.project.audiorate)

    def _displayRenderSettings(self):
        """Displays the settings available only in the RenderDialog."""
        # Video settings
        # This will trigger an update of the video resolution label.
        self.scale_spinbutton.set_value(self.project.render_scale)
        # Muxer settings
        # This will trigger an update of the codec comboboxes.
        set_combo_value(self.muxer_combo,
                        Encoders().factories_by_name.get(self.project.muxer))

    def _checkForExistingFile(self, *unused_args):
        """Displays a warning if the file path already exists."""
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
        """Estimates the final file size.

        Estimates in megabytes (over 30 MB) are rounded to the nearest 10 MB
        to smooth out small variations. You'd be surprised how imprecision can
        improve perceived accuracy.

        Returns:
            str: A human-readable (ex: "14 MB") estimate for the file size.
        """
        if not self.current_position:
            return None

        current_filesize = os.stat(path_from_uri(self.outfile)).st_size
        length = self.project.ges_timeline.props.duration
        estimated_size = float(
            current_filesize * float(length) / self.current_position)
        # Now let's make it human-readable (instead of octets).
        # If it's in the giga range (10⁹) instead of mega (10⁶), use 2 decimals
        if estimated_size > 10e8:
            gigabytes = estimated_size / (10 ** 9)
            return _("%.2f GB") % gigabytes
        else:
            megabytes = int(estimated_size / (10 ** 6))
            if megabytes > 30:
                megabytes = int(round(megabytes, -1))  # -1 means round to 10
            return _("%d MB") % megabytes

    def updateFilename(self, basename):
        """Updates the filename UI element to show the specified file name."""
        extension = extension_for_muxer(self.project.muxer)
        if extension:
            name = "%s%s%s" % (basename, os.path.extsep, extension)
        else:
            name = basename
        self.fileentry.set_text(name)

    def _update_valid_restriction_values(self, caps, combo, caps_template,
                               model, value,
                               caps_template_expander=None):
        def caps_template_expander_func(caps_template, value):
            return caps_template % value

        if not caps_template_expander:
            caps_template_expander = caps_template_expander_func

        model_headers = [model.get_column_type(i) for i in range(model.get_n_columns())]
        reduced_model = Gtk.ListStore(*model_headers)
        reduced = []
        for name, value in dict(model).items():
            ecaps = Gst.Caps(caps_template_expander(caps_template, value))
            if not caps.intersect(ecaps).is_empty():
                reduced.append((name, value))

        for v in sorted(reduced, key=lambda v: float(v[1])):
            reduced_model.append(v)
        combo.set_model(reduced_model)

        set_combo_value(combo, value)
        if get_combo_value(combo) != value:
            combo.set_active(len(reduced_model) - 1)
            self.warning("%s in %s not supported, setting: %s",
                value, caps_template, get_combo_value(combo))

    def _update_valid_audio_restrictions(self, factory):
        template = [t for t in factory.get_static_pad_templates()
                    if t.direction == Gst.PadDirection.SINK][0]

        caps = template.static_caps.get()
        self._update_valid_restriction_values(caps, self.sample_rate_combo,
                                              "audio/x-raw,rate=(int)%d",
                                              audio_rates,
                                              self.project.audiorate)

        self._update_valid_restriction_values(caps, self.channels_combo,
                                              "audio/x-raw,channels=(int)%d",
                                              audio_channels,
                                              self.project.audiochannels)

    def _update_valid_video_restrictions(self, factory):
        def fraction_expander_func(caps_template, value):
            return caps_template % (value.num, value.denom)

        template = [t for t in factory.get_static_pad_templates()
                    if t.direction == Gst.PadDirection.SINK][0]

        caps = template.static_caps.get()
        self._update_valid_restriction_values(
            caps, self.frame_rate_combo,
            "video/x-raw,framerate=(GstFraction)%d/%d", frame_rates,
            self.project.videorate,
            caps_template_expander=fraction_expander_func)

    def updateAvailableEncoders(self):
        """Updates the encoder comboboxes to show the available encoders."""
        self.muxer_combo_changing = True
        try:
            model = self.create_combobox_model(
                Encoders().compatible_video_encoders[self.project.muxer])
            self.video_encoder_combo.set_model(model)
            self._update_encoder_combo(self.video_encoder_combo,
                                       self.preferred_vencoder)

            model = self.create_combobox_model(
                Encoders().compatible_audio_encoders[self.project.muxer])
            self.audio_encoder_combo.set_model(model)
            self._update_encoder_combo(self.audio_encoder_combo,
                                       self.preferred_aencoder)
        finally:
            self.muxer_combo_changing = False

    def _update_encoder_combo(self, encoder_combo, preferred_encoder):
        """Selects the specified encoder for the specified encoder combo."""
        if preferred_encoder:
            # A preference exists, pick it if it can be found in
            # the current model of the combobox.
            encoder = Encoders().factories_by_name.get(preferred_encoder)
            set_combo_value(encoder_combo, encoder)
        if not preferred_encoder or not get_combo_value(encoder_combo):
            # No preference exists or it is not available,
            # pick the first encoder from the combobox's model.
            first = encoder_combo.props.model.get_iter_first()
            if not first:
                # Model is empty. Should not happen.
                self.warning("Model is empty")
                return
            if not encoder_combo.props.model.iter_has_child(first):
                # The first item is a supported factory.
                encoder_combo.set_active_iter(first)
            else:
                # The first element is the Unsupported group.
                second = encoder_combo.props.model.iter_nth_child(first, 0)
                encoder_combo.set_active_iter(second)

    def _elementSettingsDialog(self, factory, settings_attr):
        """Opens a dialog to edit the properties for the specified factory.

        Args:
            factory (Gst.ElementFactory): The factory for editing.
            settings_attr (str): The Project attribute holding the properties.
        """
        properties = getattr(self.project, settings_attr)
        self.dialog = GstElementSettingsDialog(factory, properties=properties,
                                               parent_window=self.window)
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
        """Starts the render process."""
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
        """Shuts down the pipeline and disconnects from its signals."""
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
        self.project.pipeline.togglePlayback()

    def _destroyProgressWindow(self):
        """Handles the completion or the cancellation of the render process."""
        self.progress.window.destroy()
        self.progress = None
        self.window.show()  # Show the rendering dialog again

    def _disconnectFromGst(self):
        for obj, id in self._gstSigId.items():
            obj.disconnect(id)
        self._gstSigId = {}
        try:
            self.project.pipeline.disconnect_by_func(self._updatePositionCb)
        except TypeError:
            # The render was successful, so this was already disconnected
            pass

    def destroy(self):
        self.window.destroy()

    def _maybe_play_finished_sound(self):
        """Plays a sound to signal the render operation is done."""
        if "GSound" in missing_soft_deps:
            return
        from gi.repository import GSound
        sound_context = GSound.Context()
        try:
            sound_context.init()
            sound_context.play_simple({GSound.ATTR_EVENT_ID: "complete"})
        except GLib.Error as e:
            self.warning("GSound failed to play: %s", e)

    def __maybeUseSourceAsset(self):
        if self.__always_use_proxies.get_active():
            self.debug("Rendering from proxies, not replacing assets")
            return

        for layer in self.app.gui.timeline_ui.ges_timeline.get_layers():
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
        """Starts the rendering process."""
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
            factory = Encoders().factories_by_name.get(self.project.vencoder)
            for struct in factory.get_static_pad_templates():
                if struct.direction == Gst.PadDirection.SINK:
                    caps = Gst.Caps.from_string(struct.get_caps().to_string())
                    fixed = caps.fixate()
                    fmt = fixed.get_structure(0).get_value("format")
                    self.project.setVideoRestriction("format", fmt)
                    self._factory_formats[encoder_string] = fmt
                    break

        self.app.gui.timeline_ui.timeline.set_best_zoom_ratio(allow_zoom_in=True)
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
        self.project.pipeline.connect("position", self._updatePositionCb)
        # Force writing the config now, or the path will be reset
        # if the user opens the rendering dialog again
        self.app.settings.lastExportFolder = self.filebutton.get_current_folder(
        )
        self.app.settings.storeSettings()

    def _closeButtonClickedCb(self, unused_button):
        self.debug("Render dialog's Close button clicked")
        self.project.disconnect_by_func(self._settings_changed_cb)
        self.destroy()

    def _deleteEventCb(self, unused_window, unused_event):
        self.debug("Render dialog is being deleted")
        self.destroy()

    def _containerContextHelpClickedCb(self, unused_button):
        show_user_manual("codecscontainers")

    # Periodic (timer) callbacks
    def _updateTimeEstimateCb(self):
        if self._rendering_is_paused:
            # Do nothing until we resume rendering
            return True
        if self._is_rendering:
            if self.current_position:
                timediff = time.time() - self._time_started - self._time_spent_paused
                length = self.project.ges_timeline.props.duration
                estimated_time = timediff * length / self.current_position
                remaining_time = estimated_time - timediff
                estimate = beautify_ETA(int(remaining_time * Gst.SECOND))
                if estimate:
                    self.progress.updateProgressbarETA(estimate)
            return True
        else:
            self._timeEstimateTimer = None
            self.debug("Stopping the ETA timer")
            return False

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
                    '"%s" has finished rendering.') % self.fileentry.get_text()
                self.notification = self.app.system.desktopMessage(
                    _("Render complete"), notification, "pitivi")
            self._maybe_play_finished_sound()
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
            if message.src == self._pipeline:
                prev, state, pending = message.parse_state_changed()
                if pending == Gst.State.VOID_PENDING:
                    # State will not change further.
                    if state == Gst.State.PLAYING:
                        self.debug("Inhibiting sleep when rendering")
                        self.app.simple_inhibit(RenderDialog.INHIBIT_REASON,
                                                Gtk.ApplicationInhibitFlags.SUSPEND)
                    else:
                        self.app.simple_uninhibit(RenderDialog.INHIBIT_REASON)

    def _updatePositionCb(self, unused_pipeline, position):
        """Updates the progress bar and triggers the update of the file size.

        This one occurs every time the pipeline emits a position changed signal,
        which is *very* often.
        """
        self.current_position = position
        if not self.progress or not position:
            return

        length = self.project.ges_timeline.props.duration
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

        # Filesize is trickier and needs more time to be meaningful.
        if not self._filesizeEstimateTimer and (fraction > 0.33 or timediff > 180):
            self._filesizeEstimateTimer = GLib.timeout_add_seconds(
                5, self._updateFilesizeEstimateCb)

    def _elementAddedCb(self, unused_bin, gst_element):
        """Sets properties on the specified Gst.Element."""
        factory = gst_element.get_factory()
        settings = {}
        if factory == get_combo_value(self.video_encoder_combo):
            settings = self.project.vcodecsettings
        elif factory == get_combo_value(self.audio_encoder_combo):
            settings = self.project.acodecsettings

        for propname, value in settings.items():
            gst_element.set_property(propname, value)
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
        dialog = ProjectSettingsDialog(self.window, self.project, self.app)
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
        if self._setting_encoding_profile:
            return
        framerate = get_combo_value(combo)
        self.project.videorate = framerate

    def _videoEncoderComboChangedCb(self, combo):
        if self._setting_encoding_profile:
            return
        factory = get_combo_value(combo)
        name = factory.get_name()
        self.project.vencoder = name
        if not self.muxer_combo_changing:
            # The user directly changed the video encoder combo.
            self.debug("User chose a video encoder: %s", name)
            self.preferred_vencoder = name
        self._update_valid_video_restrictions(factory)

    def _videoSettingsButtonClickedCb(self, unused_button):
        if self._setting_encoding_profile:
            return
        factory = get_combo_value(self.video_encoder_combo)
        self._elementSettingsDialog(factory, 'vcodecsettings')

    def _channelsComboChangedCb(self, combo):
        if self._setting_encoding_profile:
            return
        self.project.audiochannels = get_combo_value(combo)

    def _sampleRateComboChangedCb(self, combo):
        if self._setting_encoding_profile:
            return
        self.project.audiorate = get_combo_value(combo)

    def _audioEncoderChangedComboCb(self, combo):
        if self._setting_encoding_profile:
            return
        factory = get_combo_value(combo)
        name = factory.get_name()
        self.project.aencoder = name
        if not self.muxer_combo_changing:
            # The user directly changed the audio encoder combo.
            self.debug("User chose an audio encoder: %s", name)
            self.preferred_aencoder = name
        self._update_valid_audio_restrictions(factory)

    def _audioSettingsButtonClickedCb(self, unused_button):
        factory = get_combo_value(self.audio_encoder_combo)
        self._elementSettingsDialog(factory, 'acodecsettings')

    def _muxerComboChangedCb(self, combo):
        """Handles the changing of the container format combobox."""
        if self._setting_encoding_profile:
            return
        factory = get_combo_value(combo)
        self.project.muxer = factory.get_name()

        # Update the extension of the filename.
        basename = os.path.splitext(self.fileentry.get_text())[0]
        self.updateFilename(basename)

        # Update muxer-dependent widgets.
        self.updateAvailableEncoders()
