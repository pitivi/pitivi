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
import posixpath
import time
from gettext import gettext as _

from gi.repository import GES
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk

from pitivi import configure
from pitivi.check import MISSING_SOFT_DEPS
from pitivi.preset import EncodingTargetManager
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import path_from_uri
from pitivi.utils.misc import show_user_manual
from pitivi.utils.ripple_update_group import RippleUpdateGroup
from pitivi.utils.ui import AUDIO_CHANNELS
from pitivi.utils.ui import AUDIO_RATES
from pitivi.utils.ui import beautify_eta
from pitivi.utils.ui import FRAME_RATES
from pitivi.utils.ui import get_combo_value
from pitivi.utils.ui import set_combo_value
from pitivi.utils.widgets import GstElementSettingsDialog
from pitivi.utils.widgets import TextWidget


class Encoders(Loggable):
    """Registry of available Muxers, Audio encoders and Video encoders.

    Also keeps the available combinations of those.

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

    if Gst.ElementFactory.find("fdkaacenc"):
        AAC = "fdkaacenc"
    else:
        AAC = "voaacenc"
    AC3 = "avenc_ac3_fixed"
    OPUS = "opusenc"
    VORBIS = "vorbisenc"

    JPEG = "jpegenc"
    THEORA = "theoraenc"
    VP8 = "vp8enc"
    X264 = "x264enc"

    SUPPORTED_ENCODERS_COMBINATIONS = [
        (WEBM, VORBIS, VP8),
        (OGG, VORBIS, THEORA),
        (OGG, OPUS, THEORA),
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
    https://gitlab.freedesktop.org/gstreamer/gst-editing-services/blob/master/tests/validate/geslaunch.py
    """

    _instance = None

    def __new__(cls):
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
        # pylint: disable=attribute-defined-outside-init
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
        # pylint: disable=attribute-defined-outside-init
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

        self.factories_by_name = {fact.get_name(): fact
                                  for fact in self.muxers + self.aencoders + self.vencoders}

        good_muxers, good_aencoders, good_vencoders = zip(*self.SUPPORTED_ENCODERS_COMBINATIONS)
        self.supported_muxers = {muxer
                                 for muxer in self.muxers
                                 if muxer.get_name() in good_muxers}
        self.supported_aencoders = {encoder
                                    for encoder in self.aencoders
                                    if encoder.get_name() in good_aencoders}
        self.supported_vencoders = {encoder
                                    for encoder in self.vencoders
                                    if encoder.get_name() in good_vencoders}

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
        if isinstance(factory, str):
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
        "pause": (GObject.SignalFlags.RUN_LAST, None, ()),
        "cancel": (GObject.SignalFlags.RUN_LAST, None, ()),
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
        self.show_in_file_manager_button = self.builder.get_object(
            "show_in_file_manager_button")
        self.cancel_button = self.builder.get_object("cancel_button")
        self._filesize_est_label = self.builder.get_object(
            "estimated_filesize_label")
        self._filesize_est_value_label = self.builder.get_object(
            "estimated_filesize_value_label")
        # Parent the dialog with mainwindow, since renderingdialog is hidden.
        # It allows this dialog to properly minimize together with mainwindow
        self.window.set_transient_for(self.app.gui)
        self.window.set_icon_name("system-run-symbolic")

        self.play_rendered_file_button.get_style_context().add_class("suggested-action")

        # We will only show the close/play buttons when the render is done:
        self.play_rendered_file_button.hide()
        self.close_button.hide()
        self.show_in_file_manager_button.hide()

    def update_position(self, fraction):
        self.progressbar.set_fraction(fraction)
        self.window.set_title(
            _("Rendering — %d%% complete") % int(100 * fraction))

    def update_progressbar_eta(self, time_estimation):
        # Translators: this string indicates the estimated time
        # remaining until an action (such as rendering) completes.
        # The "%s" is an already-localized human-readable duration,
        # such as "31 seconds", "1 minute" or "1 hours, 14 minutes".
        # In some languages, "About %s left" can be expressed roughly as
        # "There remains approximatively %s" (to handle gender and plurals).
        self.progressbar.set_text(_("About %s left") % time_estimation)

    def set_filesize_estimate(self, estimated_filesize=None):
        if not estimated_filesize:
            self._filesize_est_label.hide()
            self._filesize_est_value_label.hide()
        else:
            self._filesize_est_value_label.set_text(estimated_filesize)
            self._filesize_est_label.show()
            self._filesize_est_value_label.show()

    def _delete_event_cb(self, unused_dialog_widget, unused_event):
        """Stops the rendering."""
        # The user closed the window by pressing Escape.
        self.emit("cancel")

    def _cancel_button_clicked_cb(self, unused_button):
        self.emit("cancel")

    def _pause_button_clicked_cb(self, unused_button):
        self.emit("pause")

    def _close_button_clicked_cb(self, unused_button):
        self.window.destroy()
        if self.main_render_dialog.notification is not None:
            self.main_render_dialog.notification.close()
        self.main_render_dialog.window.show()

    def _play_rendered_file_button_clicked_cb(self, unused_button):
        Gio.AppInfo.launch_default_for_uri(self.main_render_dialog.outfile, None)

    def _show_in_file_manager_button_clicked_cb(self, unused_button):
        directory_uri = posixpath.dirname(self.main_render_dialog.outfile)
        Gio.AppInfo.launch_default_for_uri(directory_uri, None)


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
        self._filesize_estimate_timer = None
        self._time_estimate_timer = None
        self._is_rendering = False
        self._rendering_is_paused = False
        self._last_timestamp_when_pausing = 0
        self.current_position = None
        self._time_started = 0
        self._time_spent_paused = 0  # Avoids the ETA being wrong on resume
        self._is_filename_valid = True

        # Various gstreamer signal connection ID's
        # {object: sigId}
        self._gst_signal_handlers_ids = {}

        self.render_presets = EncodingTargetManager(project)
        self.render_presets.connect('profile-selected', self._encoding_profile_selected_cb)

        # Whether encoders changing are a result of changing the muxer.
        self.muxer_combo_changing = False
        self._create_ui()
        self.progress = None
        self.dialog = None

        # Directory and Filename
        self.filebutton.set_current_folder(self.app.settings.lastExportFolder)
        if not self.project.name:
            self._update_filename(_("Untitled"))
        else:
            self._update_filename(self.project.name)

        # Add a shortcut for the project folder (if saved)
        if self.project.uri:
            shortcut = os.path.dirname(self.project.uri)
            self.filebutton.add_shortcut_folder_uri(shortcut)

        self._setting_encoding_profile = False

        # We store these so that when the user tries various container formats,
        # (AKA muxers) we select these a/v encoders, if they are compatible with
        # the current container format.
        self.preferred_vencoder = self.project.vencoder
        self.preferred_aencoder = self.project.aencoder
        self.__replaced_assets = {}

        self.frame_rate_combo.set_model(FRAME_RATES)
        self.channels_combo.set_model(AUDIO_CHANNELS)
        self.sample_rate_combo.set_model(AUDIO_RATES)
        self.__initialize_muxers_model()
        self._display_settings()
        self._display_render_settings()

        self.window.connect("delete-event", self._delete_event_cb)
        self.project.connect("rendering-settings-changed",
                             self._rendering_settings_changed_cb)

        # Monitor changes

        self.widgets_group = RippleUpdateGroup()
        self.widgets_group.add_vertex(self.frame_rate_combo, signal="changed")
        self.widgets_group.add_vertex(self.channels_combo, signal="changed")
        self.widgets_group.add_vertex(self.sample_rate_combo, signal="changed")
        self.widgets_group.add_vertex(self.muxer_combo, signal="changed")
        self.widgets_group.add_vertex(self.audio_encoder_combo, signal="changed")
        self.widgets_group.add_vertex(self.video_encoder_combo, signal="changed")
        self.widgets_group.add_vertex(self.preset_menubutton,
                                      update_func=self._update_preset_menu_button)

        self.widgets_group.add_edge(self.frame_rate_combo, self.preset_menubutton)
        self.widgets_group.add_edge(self.audio_encoder_combo, self.preset_menubutton)
        self.widgets_group.add_edge(self.video_encoder_combo, self.preset_menubutton)
        self.widgets_group.add_edge(self.muxer_combo, self.preset_menubutton)
        self.widgets_group.add_edge(self.channels_combo, self.preset_menubutton)
        self.widgets_group.add_edge(self.sample_rate_combo, self.preset_menubutton)

    def _encoding_profile_selected_cb(self, unused_target, encoding_profile):
        self._set_encoding_profile(encoding_profile)

    def _set_encoding_profile(self, encoding_profile, recursing=False):
        old_profile = self.project.container_profile

        def rollback():
            if recursing:
                return

            self._set_encoding_profile(old_profile, True)

        def factory(x):
            return Encoders().factories_by_name.get(getattr(self.project, x))

        self.project.set_container_profile(encoding_profile)
        self._setting_encoding_profile = True

        if not set_combo_value(self.muxer_combo, factory('muxer')):
            rollback()
            return

        self.update_available_encoders()
        self._update_valid_audio_restrictions(Gst.ElementFactory.find(self.project.aencoder))
        self._update_valid_video_restrictions(Gst.ElementFactory.find(self.project.vencoder))
        for i, (combo, name, value) in enumerate([
                (self.audio_encoder_combo, "aencoder", factory("aencoder")),
                (self.video_encoder_combo, "vencoder", factory("vencoder")),
                (self.sample_rate_combo, "audiorate", self.project.audiorate),
                (self.channels_combo, "audiochannels", self.project.audiochannels),
                (self.frame_rate_combo, "videorate", self.project.videorate)]):
            if value is None:
                self.error("%d - Got no value for %s (%s)... rolling back",
                           i, name, combo)
                rollback()
                return

            if not set_combo_value(combo, value):
                self.error("%d - Could not set value %s for combo %s... rolling back",
                           i, value, combo)
                rollback()
                return

        self.update_resolution()
        self.project.add_encoding_profile(self.project.container_profile)
        self._update_file_extension()
        self._setting_encoding_profile = False

    def _update_preset_menu_button(self, unused_source, unused_target):
        self.render_presets.update_menu_actions()

    def muxer_setter(self, widget, muxer_name):
        set_combo_value(widget, Encoders().factories_by_name.get(muxer_name))
        self.project.set_encoders(muxer=muxer_name)

        self._update_file_extension()

        # Update muxer-dependent widgets.
        self.update_available_encoders()

    def acodec_setter(self, widget, aencoder_name):
        set_combo_value(widget, Encoders().factories_by_name.get(aencoder_name))
        self.project.aencoder = aencoder_name
        if not self.muxer_combo_changing:
            # The user directly changed the audio encoder combo.
            self.preferred_aencoder = aencoder_name

    def vcodec_setter(self, widget, vencoder_name):
        set_combo_value(widget, Encoders().factories_by_name.get(vencoder_name))
        self.project.set_encoders(vencoder=vencoder_name)
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

    def _create_ui(self):
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
        self.frame_rate_combo.set_model(FRAME_RATES)
        self.scale_spinbutton = builder.get_object("scale_spinbutton")
        self.channels_combo = builder.get_object("channels_combo")
        self.channels_combo.set_model(AUDIO_CHANNELS)
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

        self.__automatically_use_proxies = builder.get_object(
            "automatically_use_proxies")

        self.__always_use_proxies = builder.get_object("always_use_proxies")
        self.__always_use_proxies.props.group = self.__automatically_use_proxies

        self.__never_use_proxies = builder.get_object("never_use_proxies")
        self.__never_use_proxies.props.group = self.__automatically_use_proxies

        self.render_presets.setup_ui(self.presets_combo, self.preset_menubutton)
        self.render_presets.load_all()

        self.window.set_icon_name("system-run-symbolic")
        self.window.set_transient_for(self.app.gui)

        media_types = self.project.ges_timeline.ui.media_types

        self.audio_output_checkbutton.props.active = media_types & GES.TrackType.AUDIO
        self._update_audio_widgets_sensitivity()

        self.video_output_checkbutton.props.active = media_types & GES.TrackType.VIDEO
        self._update_video_widgets_sensitivity()

    def _rendering_settings_changed_cb(self, unused_project, unused_item):
        """Handles Project metadata changes."""
        self.update_resolution()

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

        if data_unsupported:
            # Translators: This item appears in a combobox's popup and
            # contains as children the unsupported (but still available)
            # muxers and encoders.
            unsupported_iter = model.append(None, (_("Unsupported"), None))
            data_unsupported.sort()
            for row in data_unsupported:
                model.append(unsupported_iter, row)

        return model

    def _display_settings(self):
        """Displays the settings also in the ProjectSettingsDialog."""
        # Video settings
        set_combo_value(self.frame_rate_combo, self.project.videorate)
        # Audio settings
        set_combo_value(self.channels_combo, self.project.audiochannels)
        set_combo_value(self.sample_rate_combo, self.project.audiorate)

    def _update_audio_widgets_sensitivity(self):
        active = self.audio_output_checkbutton.get_active()
        self.channels_combo.set_sensitive(active)
        self.sample_rate_combo.set_sensitive(active)
        self.audio_encoder_combo.set_sensitive(active)
        self.audio_settings_button.set_sensitive(active)
        self.project.audio_profile.set_enabled(active)
        self.__update_render_button_sensitivity()

    def _update_video_widgets_sensitivity(self):
        active = self.video_output_checkbutton.get_active()
        self.scale_spinbutton.set_sensitive(active)
        self.frame_rate_combo.set_sensitive(active)
        self.video_encoder_combo.set_sensitive(active)
        self.video_settings_button.set_sensitive(active)
        self.project.video_profile.set_enabled(active)
        self.__update_render_button_sensitivity()

    def _display_render_settings(self):
        """Displays the settings available only in the RenderDialog."""
        # Video settings
        # This will trigger an update of the video resolution label.
        self.scale_spinbutton.set_value(self.project.render_scale)
        # Muxer settings
        # This will trigger an update of the codec comboboxes.
        set_combo_value(self.muxer_combo,
                        Encoders().factories_by_name.get(self.project.muxer))

    def _check_filename(self):
        """Displays a warning if the file path already exists."""
        path = self.filebutton.get_current_folder()
        if not path:
            # This happens when the window is initialized.
            return

        filename = self.fileentry.get_text()

        # Characters that cause pipeline failure.
        blacklist = ["/"]
        invalid_chars = "".join([ch for ch in blacklist if ch in filename])

        warning_icon = "dialog-warning"
        self._is_filename_valid = True
        if not filename:
            tooltip_text = _("A file name is required.")
            self._is_filename_valid = False
        elif os.path.exists(os.path.join(path, filename)):
            tooltip_text = _("This file already exists.\n"
                             "If you don't want to overwrite it, choose a "
                             "different file name or folder.")
        elif invalid_chars:
            tooltip_text = _("Remove invalid characters from the filename: %s") % invalid_chars
            self._is_filename_valid = False
        else:
            warning_icon = None
            tooltip_text = None

        self.fileentry.set_icon_from_icon_name(1, warning_icon)
        self.fileentry.set_icon_tooltip_text(1, tooltip_text)
        self.__update_render_button_sensitivity()

    def _get_filesize_estimate(self):
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

    def _update_filename(self, basename):
        """Updates the filename UI element to show the specified file name."""
        extension = extension_for_muxer(self.project.muxer)
        if extension:
            name = "%s%s%s" % (basename, os.path.extsep, extension)
        else:
            name = basename
        self.fileentry.set_text(name)

    def _update_valid_restriction_values(self, caps, combo, caps_template,
                                         model, combo_value,
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

        for value in sorted(reduced, key=lambda v: float(v[1])):
            reduced_model.append(value)
        combo.set_model(reduced_model)

        set_combo_value(combo, combo_value)
        if get_combo_value(combo) != combo_value:
            combo.set_active(len(reduced_model) - 1)
            self.warning("%s in %s not supported, setting: %s",
                         combo_value, caps_template, get_combo_value(combo))

    def _update_valid_audio_restrictions(self, factory):
        template = [t for t in factory.get_static_pad_templates()
                    if t.direction == Gst.PadDirection.SINK][0]

        caps = template.static_caps.get()
        self._update_valid_restriction_values(caps, self.sample_rate_combo,
                                              "audio/x-raw,rate=(int)%d",
                                              AUDIO_RATES,
                                              self.project.audiorate)

        self._update_valid_restriction_values(caps, self.channels_combo,
                                              "audio/x-raw,channels=(int)%d",
                                              AUDIO_CHANNELS,
                                              self.project.audiochannels)

    def _update_valid_video_restrictions(self, factory):
        def fraction_expander_func(caps_template, value):
            return caps_template % (value.num, value.denom)

        template = [t for t in factory.get_static_pad_templates()
                    if t.direction == Gst.PadDirection.SINK][0]

        caps = template.static_caps.get()
        self._update_valid_restriction_values(
            caps, self.frame_rate_combo,
            "video/x-raw,framerate=(GstFraction)%d/%d", FRAME_RATES,
            self.project.videorate,
            caps_template_expander=fraction_expander_func)

    def update_available_encoders(self):
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

    def _element_settings_dialog(self, factory, media_type):
        """Opens a dialog to edit the properties for the specified factory.

        Args:
            factory (Gst.ElementFactory): The factory for editing.
            media_type (str): String describing the media type ('audio' or 'video')
        """
        # Reconstitute the property name from the media type (vcodecsettings or acodecsettings)
        properties = getattr(self.project, media_type[0] + 'codecsettings')

        self.dialog = GstElementSettingsDialog(factory, properties=properties,
                                               caps=getattr(self.project, media_type + '_profile').get_format(),
                                               parent_window=self.window)
        self.dialog.ok_btn.connect(
            "clicked", self._ok_button_clicked_cb, media_type)

    def __additional_debug_info(self):
        if self.project.vencoder == 'x264enc':
            if self.project.videowidth % 2 or self.project.videoheight % 2:
                return "\n\n%s\n\n" % _("<b>Make sure your rendering size is even, "
                                        "x264enc might not be able to render otherwise.</b>\n\n")

        return ""

    def _show_render_error_dialog(self, error, unused_details):
        primary_message = _("Sorry, something didn’t work right.")
        secondary_message = "".join([
            _("An error occurred while trying to render your project."),
            self.__additional_debug_info(),
            _("You might want to check our troubleshooting guide or file a bug report. "
              "The GStreamer error was:"),
            "\n\n<i>" + str(error) + "</i>"])

        dialog = Gtk.MessageDialog(transient_for=self.window, modal=True,
                                   message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK,
                                   text=primary_message)
        dialog.set_property("secondary-text", secondary_message)
        dialog.set_property("secondary-use-markup", True)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def start_action(self):
        """Starts the render process."""
        self._pipeline.set_state(Gst.State.NULL)
        self._pipeline.set_mode(GES.PipelineFlags.RENDER)
        encodebin = self._pipeline.get_by_name("internal-encodebin")
        self._gst_signal_handlers_ids[encodebin] = encodebin.connect(
            "element-added", self.__element_added_cb)
        for element in encodebin.iterate_recurse():
            self.__set_properties(element)
        self._pipeline.set_state(Gst.State.PLAYING)
        self._is_rendering = True
        self._time_started = time.time()

    def _cancel_render(self, *unused_args):
        self.debug("Aborting render")
        self._shut_down()
        self._destroy_progress_window()

    def _shut_down(self):
        """Shuts down the pipeline and disconnects from its signals."""
        self._is_rendering = False
        self._rendering_is_paused = False
        self._time_spent_paused = 0
        self._pipeline.set_state(Gst.State.NULL)
        self.project.set_rendering(False)
        self._use_proxy_assets()
        self._disconnect_from_gst()
        self._pipeline.set_mode(GES.PipelineFlags.FULL_PREVIEW)
        self._pipeline.set_state(Gst.State.PAUSED)

    def _pause_render(self, unused_progress):
        self._rendering_is_paused = self.progress.play_pause_button.get_active()
        if self._rendering_is_paused:
            self._last_timestamp_when_pausing = time.time()
        else:
            self._time_spent_paused += time.time() - self._last_timestamp_when_pausing
            self.debug(
                "Resuming render after %d seconds in pause", self._time_spent_paused)
        self.project.pipeline.toggle_playback()

    def _destroy_progress_window(self):
        """Handles the completion or the cancellation of the render process."""
        self.progress.window.destroy()
        self.progress = None
        self.window.show()  # Show the rendering dialog again

    def _disconnect_from_gst(self):
        for obj, handler_id in self._gst_signal_handlers_ids.items():
            obj.disconnect(handler_id)
        self._gst_signal_handlers_ids = {}
        try:
            self.project.pipeline.disconnect_by_func(self._update_position_cb)
        except TypeError:
            # The render was successful, so this was already disconnected
            pass

    def destroy(self):
        self.window.destroy()

    def _maybe_play_finished_sound(self):
        """Plays a sound to signal the render operation is done."""
        if "GSound" in MISSING_SOFT_DEPS:
            return
        from gi.repository import GSound
        sound_context = GSound.Context()
        try:
            sound_context.init()
            sound_context.play_simple({GSound.ATTR_EVENT_ID: "complete"})
        except GLib.Error as e:
            self.warning("GSound failed to play: %s", e)

    def _asset_replacement(self, clip):
        if not isinstance(clip, GES.UriClip):
            return None

        asset = clip.get_asset()
        asset_target = asset.get_proxy_target()
        if not asset_target:
            # The asset is not a proxy.
            return None

        # Replace all proxies
        if self.__never_use_proxies.get_active():
            return asset_target

        # Use HQ Proxy (or equivalent) only for unsupported assets
        if self.__automatically_use_proxies.get_active():
            if self.app.proxy_manager.is_asset_format_well_supported(
                    asset_target):
                return asset_target
            else:
                proxy_unsupported = True

        # Use HQ Proxy (or equivalent) whenever available
        if self.__always_use_proxies.get_active() or proxy_unsupported:
            if self.app.proxy_manager.is_hq_proxy(asset):
                return None

            if self.app.proxy_manager.is_scaled_proxy(asset):
                width, height = self.project.get_video_width_and_height(render=True)
                stream = asset.get_info().get_video_streams()[0]
                asset_res = [stream.get_width(), stream.get_height()]

                if asset_res[0] == width and asset_res[1] == height:
                    # Check whether the scaled proxy size matches the render size
                    # exactly. If the size is same, render from the scaled proxy
                    # to avoid double scaling.
                    return None

                hq_proxy = GES.Asset.request(GES.UriClip,
                                             self.app.proxy_manager.get_proxy_uri(asset_target))
                return hq_proxy
        return None

    def __replace_proxies(self):
        for clip in self.project.ges_timeline.ui.clips():
            asset = self._asset_replacement(clip)
            if asset:
                self.__replaced_assets[clip] = clip.get_asset()
                clip.set_asset(asset)

    def _use_proxy_assets(self):
        for clip, asset in self.__replaced_assets.items():
            self.info("Reverting to using proxy asset %s", asset)
            clip.set_asset(asset)

        self.__replaced_assets = {}

    # ------------------- Callbacks ------------------------------------------ #

    # -- UI callbacks
    def _ok_button_clicked_cb(self, unused_button, media_type):
        assert media_type in ("audio", "video")
        setattr(self.project, media_type[0] + 'codecsettings', self.dialog.get_settings())

        caps = self.dialog.get_caps()
        if caps:
            getattr(self.project, media_type + '_profile').set_format(caps)
        self.dialog.window.destroy()

    def _render_button_clicked_cb(self, unused_button):
        """Starts the rendering process."""
        self.__replace_proxies()
        self.outfile = os.path.join(self.filebutton.get_uri(),
                                    self.fileentry.get_text())
        self.progress = RenderingProgressDialog(self.app, self)
        # Hide the rendering settings dialog while rendering
        self.window.hide()

        self.app.gui.editor.timeline_ui.timeline.set_best_zoom_ratio(allow_zoom_in=True)
        self.project.set_rendering(True)
        self._pipeline.set_render_settings(
            self.outfile, self.project.container_profile)
        self.start_action()
        self.progress.window.show()
        self.progress.connect("cancel", self._cancel_render)
        self.progress.connect("pause", self._pause_render)
        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        self._gst_signal_handlers_ids[bus] = bus.connect('message', self._bus_message_cb)
        self.project.pipeline.connect("position", self._update_position_cb)
        # Force writing the config now, or the path will be reset
        # if the user opens the rendering dialog again
        self.app.settings.lastExportFolder = self.filebutton.get_current_folder(
        )
        self.app.settings.store_settings()

    def _close_button_clicked_cb(self, unused_button):
        self.debug("Render dialog's Close button clicked")
        self.project.disconnect_by_func(self._rendering_settings_changed_cb)
        self.destroy()

    def _delete_event_cb(self, unused_window, unused_event):
        self.debug("Render dialog is being deleted")
        self.destroy()

    def _container_context_help_clicked_cb(self, unused_button):
        show_user_manual("codecscontainers")

    def _current_folder_changed_cb(self, *unused_args):
        self._check_filename()

    def _filename_changed_cb(self, *unused_args):
        self._check_filename()

    # Periodic (timer) callbacks
    def _update_time_estimate_cb(self):
        if self._rendering_is_paused:
            # Do nothing until we resume rendering
            return True
        if self._is_rendering:
            if self.current_position:
                timediff = time.time() - self._time_started - self._time_spent_paused
                length = self.project.ges_timeline.props.duration
                estimated_time = timediff * length / self.current_position
                remaining_time = estimated_time - timediff
                estimate = beautify_eta(int(remaining_time * Gst.SECOND))
                if estimate:
                    self.progress.update_progressbar_eta(estimate)
            return True
        else:
            self._time_estimate_timer = None
            self.debug("Stopping the ETA timer")
            return False

    def _update_filesize_estimate_cb(self):
        if self._rendering_is_paused:
            return True  # Do nothing until we resume rendering
        elif self._is_rendering:
            est_filesize = self._get_filesize_estimate()
            if est_filesize:
                self.progress.set_filesize_estimate(est_filesize)
            return True
        else:
            self.debug("Stopping the filesize estimation timer")
            self._filesize_estimate_timer = None
            return False  # Stop the timer

    # GStreamer callbacks
    def _bus_message_cb(self, unused_bus, message):
        if message.type == Gst.MessageType.EOS:  # Render complete
            self.debug("got EOS message, render complete")
            self._shut_down()
            self.progress.progressbar.set_fraction(1.0)
            self.progress.progressbar.set_text(_("Render complete"))
            self.progress.window.set_title(_("Render complete"))
            self.progress.set_filesize_estimate(None)
            if not self.progress.window.is_active():
                notification = _(
                    '"%s" has finished rendering.') % self.fileentry.get_text()
                self.notification = self.app.system.desktop_message(
                    _("Render complete"), notification, "pitivi")
            self._maybe_play_finished_sound()
            self.progress.play_rendered_file_button.show()
            self.progress.close_button.show()
            self.progress.show_in_file_manager_button.show()
            self.progress.cancel_button.hide()
            self.progress.play_pause_button.hide()

        elif message.type == Gst.MessageType.ERROR:
            # Errors in a GStreamer pipeline are fatal. If we encounter one,
            # we should abort and show the error instead of sitting around.
            error, details = message.parse_error()
            self._cancel_render()
            self._show_render_error_dialog(error, details)

        elif message.type == Gst.MessageType.STATE_CHANGED and self.progress:
            if message.src == self._pipeline:
                unused_prev, state, pending = message.parse_state_changed()
                if pending == Gst.State.VOID_PENDING:
                    # State will not change further.
                    if state == Gst.State.PLAYING:
                        self.debug("Inhibiting sleep when rendering")
                        self.app.simple_inhibit(RenderDialog.INHIBIT_REASON,
                                                Gtk.ApplicationInhibitFlags.SUSPEND)
                    else:
                        self.app.simple_uninhibit(RenderDialog.INHIBIT_REASON)

    def _update_position_cb(self, unused_pipeline, position):
        """Updates the progress bar and triggers the update of the file size.

        This one occurs every time the pipeline emits a position changed signal,
        which is *very* often.
        """
        self.current_position = position
        if not self.progress or not position:
            return

        length = self.project.ges_timeline.props.duration
        fraction = float(min(position, length)) / float(length)
        self.progress.update_position(fraction)

        # In order to have enough averaging, only display the ETA after 5s
        timediff = time.time() - self._time_started
        if not self._time_estimate_timer:
            if timediff < 6:
                self.progress.progressbar.set_text(_("Estimating..."))
            else:
                self._time_estimate_timer = GLib.timeout_add_seconds(
                    3, self._update_time_estimate_cb)

        # Filesize is trickier and needs more time to be meaningful.
        if not self._filesize_estimate_timer and (fraction > 0.33 or timediff > 180):
            self._filesize_estimate_timer = GLib.timeout_add_seconds(
                5, self._update_filesize_estimate_cb)

    def __element_added_cb(self, unused_bin, gst_element):
        self.__set_properties(gst_element)

    def __set_properties(self, gst_element):
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
    def _scale_spinbutton_changed_cb(self, unused_button):
        render_scale = self.scale_spinbutton.get_value()
        self.project.render_scale = render_scale
        self.update_resolution()

    def update_resolution(self):
        width, height = self.project.get_video_width_and_height(render=True)
        self.resolution_label.set_text("%d×%d" % (width, height))

    def _project_settings_button_clicked_cb(self, unused_button):
        from pitivi.project import ProjectSettingsDialog
        dialog = ProjectSettingsDialog(self.window, self.project, self.app)
        dialog.window.run()

    def _audio_output_checkbutton_toggled_cb(self, unused_audio):
        self._update_audio_widgets_sensitivity()

    def _video_output_checkbutton_toggled_cb(self, unused_video):
        self._update_video_widgets_sensitivity()

    def __update_render_button_sensitivity(self):
        video_enabled = self.video_output_checkbutton.get_active()
        audio_enabled = self.audio_output_checkbutton.get_active()
        self.render_button.set_sensitive(self._is_filename_valid and
                                         (video_enabled or audio_enabled))

    def _frame_rate_combo_changed_cb(self, combo):
        if self._setting_encoding_profile:
            return
        framerate = get_combo_value(combo)
        self.project.videorate = framerate

    def _video_encoder_combo_changed_cb(self, combo):
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

    def _video_settings_button_clicked_cb(self, unused_button):
        if self._setting_encoding_profile:
            return
        factory = get_combo_value(self.video_encoder_combo)
        self._element_settings_dialog(factory, 'video')

    def _channels_combo_changed_cb(self, combo):
        if self._setting_encoding_profile:
            return
        self.project.audiochannels = get_combo_value(combo)

    def _sample_rate_combo_changed_cb(self, combo):
        if self._setting_encoding_profile:
            return
        self.project.audiorate = get_combo_value(combo)

    def _audio_encoder_changed_combo_cb(self, combo):
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

    def _audio_settings_button_clicked_cb(self, unused_button):
        factory = get_combo_value(self.audio_encoder_combo)
        self._element_settings_dialog(factory, 'audio')

    def _update_file_extension(self):
        # Update the extension of the filename.
        basename = os.path.splitext(self.fileentry.get_text())[0]
        self._update_filename(basename)

    def _muxer_combo_changed_cb(self, combo):
        """Handles the changing of the container format combobox."""
        if self._setting_encoding_profile:
            return
        factory = get_combo_value(combo)
        self.project.muxer = factory.get_name()

        self._update_file_extension()

        # Update muxer-dependent widgets.
        self.update_available_encoders()
