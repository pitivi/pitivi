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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
"""Rendering-related classes and utilities."""
import os
import posixpath
import time
from enum import IntEnum
from gettext import gettext as _

from gi.repository import GdkPixbuf
from gi.repository import GES
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GstPbutils
from gi.repository import Gtk

from pitivi import configure
from pitivi.check import MISSING_SOFT_DEPS
from pitivi.dialogs.projectsettings import ProjectSettingsDialog
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import cmp
from pitivi.utils.misc import is_pathname_valid
from pitivi.utils.misc import path_from_uri
from pitivi.utils.misc import show_user_manual
from pitivi.utils.ripple_update_group import RippleUpdateGroup
from pitivi.utils.ui import AUDIO_CHANNELS
from pitivi.utils.ui import beautify_eta
from pitivi.utils.ui import create_audio_rates_model
from pitivi.utils.ui import create_frame_rates_model
from pitivi.utils.ui import filter_unsupported_media_files
from pitivi.utils.ui import get_combo_value
from pitivi.utils.ui import set_combo_value
from pitivi.utils.widgets import GstElementSettingsDialog


# The category of GstPbutils.EncodingTarget objects holding
# a GstPbutils.EncodingProfile used as a Pitivi render preset.
PITIVI_ENCODING_TARGET_CATEGORY = "user-defined"


def set_icon_and_title(icon, title, preset_item, icon_size=Gtk.IconSize.DND):
    """Adds icon for the respective preset.

    Args:
        icon (Gtk.Image): The image widget to be updated.
        title (Gtk.Label): The label widget to be updated.
        preset_item (PresetItem): Preset profile related information.
        icon_size (Gtk.IconSize): Size of the icon.
    """
    icon_files = {
        "youtube": "youtube.png"
    }
    icon_names = {
        "dvd": "media-optical-dvd-symbolic"
    }

    if not preset_item:
        display_name = _("Custom")
        icon_name = "applications-multimedia-symbolic"
    else:
        display_name = preset_item.display_name
        icon_name = preset_item.name

    title.props.label = display_name
    title.set_xalign(0)
    title.set_yalign(0)

    icon.props.valign = Gtk.Align.START

    if icon_name in icon_files:
        icon_filename = icon_files[icon_name]
        icon_path = os.path.join(configure.get_pixmap_dir(), "presets", icon_filename)

        res, width, height = Gtk.IconSize.lookup(icon_size)
        assert res

        pic = GdkPixbuf.Pixbuf.new_from_file_at_scale(icon_path, height, width, True)
        icon.set_from_pixbuf(pic)
        return

    icon_name = icon_names.get(icon_name, "applications-multimedia-symbolic")
    icon.set_from_icon_name(icon_name, icon_size)


class PresetItem(GObject.Object):
    """Info about a render preset.

    Attributes:
        name (string): Name of the target containing the profile.
        target (GstPbutils.EncodingTarget): The encoding target containing
            the profile.
        profile (GstPbutils.EncodingContainerProfile): The represented preset.
    """

    def __init__(self, name, target, profile):
        GObject.Object.__init__(self)

        name_dict = {
            "youtube": _("YouTube"),
            "dvd": _("DVD"),
        }

        self.name = name
        self.target = target
        self.profile = profile
        self.display_name = name_dict.get(name, name)

    @staticmethod
    def compare_func(item1, item2, *unused_data):
        user_defined1 = item1.target.get_category() == PITIVI_ENCODING_TARGET_CATEGORY
        user_defined2 = item2.target.get_category() == PITIVI_ENCODING_TARGET_CATEGORY
        if user_defined1 != user_defined2:
            return cmp(user_defined1, user_defined2)

        return cmp(item1.name, item2.name)


class PresetBoxRow(Gtk.ListBoxRow):
    """ListBoxRow displaying a render preset.

    Attributes:
        preset_item (PresetItem): Preset profile related information.
    """

    def __init__(self, preset_item):
        Gtk.ListBoxRow.__init__(self)

        self.preset_item = preset_item
        grid = Gtk.Grid()

        title = Gtk.Label()
        icon = Gtk.Image()
        set_icon_and_title(icon, title, preset_item)

        description = Gtk.Label(preset_item.target.get_description())
        description.set_xalign(0)
        description.set_line_wrap(True)
        description.props.max_width_chars = 30

        grid.attach(title, 1, 0, 1, 1)
        grid.attach(description, 1, 1, 1, 1)
        grid.attach(icon, 0, 0, 1, 2)
        grid.set_row_spacing(6)
        grid.set_column_spacing(10)
        grid.set_row_homogeneous(False)
        grid.props.margin = 6
        self.add(grid)


class PresetsManager(GObject.Object, Loggable):
    """Manager of EncodingProfiles used as render presets.

    The EncodingProfiles are retrieved from the available EncodingTargets.
    An EncodingTarget can contain multiple EncodingProfiles.

    The render presets created by us are stored as EncodingProfiles,
    each in its own EncodingTarget.

    Attributes:
        cur_preset_item (PresetItem): The currently selected PresetItem.
        model (Gio.ListStore): The model to store PresetItems for all the preset-profiles.
        project (Project): The project holding the container_profile to be saved or turned into a new preset.
    """

    __gsignals__ = {
        "profile-updated": (GObject.SignalFlags.RUN_LAST, None, (PresetItem,))
    }

    def __init__(self, project):
        GObject.Object.__init__(self)
        Loggable.__init__(self)

        self.project = project

        # menu button actions
        self.action_new = None
        self.action_remove = None
        self.action_save = None

        self.cur_preset_item = None
        self.model = Gio.ListStore.new(PresetItem)

        self.load_all()

    def load_all(self):
        """Loads profiles from GstEncodingTarget and add them to self.model."""
        for target in GstPbutils.encoding_list_all_targets():
            if target.get_category() != GstPbutils.ENCODING_CATEGORY_FILE_EXTENSION:
                self._add_target(target)

    def preset_menubutton_setup(self, button):
        action_group = Gio.SimpleActionGroup()
        menu_model = Gio.Menu()

        action = Gio.SimpleAction.new("new", None)
        action.connect("activate", self._add_preset_cb)
        action_group.add_action(action)
        menu_model.append(_("New"), "preset.%s" % action.get_name())
        self.action_new = action

        action = Gio.SimpleAction.new("remove", None)
        action.connect("activate", self._remove_preset_cb)
        action_group.add_action(action)
        menu_model.append(_("Remove"), "preset.%s" % action.get_name())
        self.action_remove = action

        action = Gio.SimpleAction.new("save", None)
        action.connect("activate", self._save_preset_cb)
        action_group.add_action(action)
        menu_model.append(_("Save"), "preset.%s" % action.get_name())
        self.action_save = action

        self.action_remove.set_enabled(False)
        self.action_save.set_enabled(False)
        menu = Gtk.Menu.new_from_model(menu_model)
        menu.insert_action_group("preset", action_group)
        button.set_popup(menu)

    def _add_preset_cb(self, unused_action, unused_param):
        preset_name = self.get_new_preset_name()
        self.select_preset(self.create_preset(preset_name))

    def _remove_preset_cb(self, unused_action, unused_param):
        self.action_remove.set_enabled(False)
        self.action_save.set_enabled(False)

        if not self.cur_preset_item:
            return

        # There is only one EncodingProfile in the EncodingTarget.
        preset_path = self.cur_preset_item.target.get_path()
        if preset_path:
            os.remove(preset_path)

        res, pos = self.model.find(self.cur_preset_item)
        assert res, self.cur_preset_item.name
        self.model.remove(pos)

        self.cur_preset_item = None
        self.emit("profile-updated", None)

    def _save_preset_cb(self, unused_action, unused_param):
        name = self.cur_preset_item.target.get_name()

        # Remove the currently selected preset item from the model.
        res, pos = self.model.find(self.cur_preset_item)
        assert res, self.cur_preset_item.name
        self.model.remove(pos)

        # Recreate the preset with the current values.
        self.cur_preset_item = self.create_preset(name)
        self.emit("profile-updated", self.cur_preset_item)

    def _add_target(self, encoding_target):
        """Adds the profiles of the specified encoding_target as render presets.

        Args:
            encoding_target (GstPbutils.EncodingTarget): An encoding target.
        """
        preset_items = []
        for profile in encoding_target.get_profiles():
            # The name can be for example "youtube;yt"
            name = encoding_target.get_name().split(";")[0]
            if len(encoding_target.get_profiles()) != 1 and profile.get_name().lower() != "default":
                name += "_" + profile.get_name()

            # Check the GStreamer elements are available.
            profiles = [profile] + profile.get_profiles()
            if not all(self.project.get_element_factory_name(p)
                       for p in profiles):
                self.warning("unusable preset: %s", name)
                continue

            preset_item = PresetItem(name, encoding_target, profile)
            self.model.insert_sorted(preset_item, PresetItem.compare_func)
            preset_items.append(preset_item)

        return preset_items

    def has_preset(self, name):
        name = name.lower()
        preset_names = (item.name for item in self.model)
        return any(name == preset.lower() for preset in preset_names)

    def create_preset(self, preset_name):
        """Creates a preset, overwriting the preset with the same name if any.

        Args:
            preset_name (str): The name for the new preset created.
            values (dict): The values of the new preset.
        """
        target = GstPbutils.EncodingTarget.new(preset_name, PITIVI_ENCODING_TARGET_CATEGORY,
                                               "",
                                               [self.project.container_profile])
        target.save()
        return self._add_target(target)[0]

    def get_new_preset_name(self):
        """Gets a unique name for a new preset."""
        # Translators: This must contain exclusively low case alphanum and '-'
        name = _("new-profile")
        i = 1
        while self.has_preset(name):
            # Translators: This must contain exclusively low case alphanum and '-'
            name = _("new-profile-%d") % i
            i += 1
        return name

    def select_preset(self, preset_item):
        """Selects a preset.

        Args:
            preset_item (PresetItem): The row representing the preset to be applied.
        """
        self.cur_preset_item = preset_item
        writable = bool(preset_item) and \
            len(preset_item.target.get_profiles()) == 1 and \
            os.access(preset_item.target.get_path(), os.W_OK)

        self.action_remove.set_enabled(writable)
        self.action_save.set_enabled(writable)

    def initial_preset(self):
        """Returns the initial preset to be displayed."""
        has_vcodecsettings = bool(self.project.vcodecsettings)
        if has_vcodecsettings:
            # It's a project with previous render settings, see what matches.
            return self.matching_preset()
        else:
            # It's a new project.
            for item in self.model:
                if item.name == "youtube":
                    return item

            return None

    def matching_preset(self):
        """Returns the first preset matching the project's encoding profile."""
        for item in self.model:
            if self.project.matches_container_profile(item.profile):
                return item
        return None


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
            klist = fact.get_klass().split("/")
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


class Quality(IntEnum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2


class QualityAdapter(Loggable):
    """Adapter between a quality value and the properties of an Encoder."""

    def __init__(self, props_values, prop_name=None):
        super().__init__()

        self.props_values = props_values

        if not prop_name:
            assert len(props_values) == 1
            prop_name = list(props_values.keys())[0]
        self.prop_name = prop_name

    def calculate_quality(self, vcodecsettings):
        if self.prop_name in vcodecsettings:
            encoder_property_value = vcodecsettings[self.prop_name]
            values = self.props_values[self.prop_name]
            for quality in (Quality.HIGH, Quality.MEDIUM, Quality.LOW):
                if (values[0] < values[-1] and encoder_property_value >= values[quality]) or \
                        (values[0] > values[-1] and encoder_property_value <= values[quality]):
                    break

            self.debug("Got existing value for prop %s=%s -> quality=%s", self.prop_name, encoder_property_value, quality)
        else:
            quality = Quality.LOW
            self.debug("Cannot calculate quality from missing prop %s", self.prop_name)

        return quality

    def update_project_vcodecsettings(self, project, quality):
        for prop_name, values in self.props_values.items():
            if callable(values):
                value = values(project)
            else:
                value = values[quality]
            project.vcodecsettings[prop_name] = value


quality_adapters = {
    Encoders.X264: QualityAdapter(
        {
            # quantizer accepts values between 0..50, default is 21.
            # Values inspired by https://slhck.info/video/2017/03/01/rate-control.html
            "quantizer": (25, 21, 18),
            # Encoding pass/type: Constant Quality
            # https://gstreamer.freedesktop.org/documentation/x264/index.html?gi-language=python#GstX264EncPass
            "pass": lambda unused_project: 5,
        },
        prop_name="quantizer"),
    Encoders.VP8: QualityAdapter(
        {
            # cq-level accepts values between 0..63, default is 10.
            "cq-level": (31, 47, 63),
            # Rate control mode: Constant Quality Mode (CQ) mode
            # https://gstreamer.freedesktop.org/documentation/vpx/GstVPXEnc.html?gi-language=python#GstVPXEnc:end-usage
            "end-usage": lambda unused_project: 2,
        },
        prop_name="cq-level"),
    Encoders.THEORA: QualityAdapter({
        # Setting the quality property will produce a variable bitrate (VBR) stream.
        # quality accepts values between 0..63, default is 48.
        "quality": (31, 48, 63)}),
    Encoders.JPEG: QualityAdapter({
        # quality accepts values between 0..100, default is 85.
        "quality": (70, 85, 100)}),
}


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

        self.presets_manager = PresetsManager(project)

        # Whether encoders changing are a result of changing the muxer.
        self.muxer_combo_changing = False
        self.progress = None
        self.dialog = None
        self.preset_listbox = None
        self._create_ui()

        # Directory and Filename
        if not self.project.name:
            self._update_filename(_("Untitled"))
        else:
            self._update_filename(self.project.name)

        self._setting_encoding_profile = False

        # We store these so that when the user tries various container formats,
        # (AKA muxers) we select these a/v encoders, if they are compatible with
        # the current container format.
        self.preferred_vencoder = self.project.vencoder
        self.preferred_aencoder = self.project.aencoder
        self.__replaced_assets = {}

        self._display_render_settings()

        self.window.connect("delete-event", self._delete_event_cb)
        self.project.connect("video-size-changed", self._project_video_size_changed_cb)

        self.presets_manager.connect("profile-updated", self._presets_manager_profile_updated_cb)

        preset_item: PresetItem = self.presets_manager.initial_preset()
        if preset_item:
            if self.apply_preset(preset_item):
                self.apply_vcodecsettings_quality(Quality.MEDIUM)
                self.presets_manager.select_preset(preset_item)

        set_icon_and_title(self.preset_icon, self.preset_label, self.presets_manager.cur_preset_item)
        self._update_quality_scale()

        # Monitor changes to keep the preset_selection_menubutton updated.
        self.widgets_group = RippleUpdateGroup()
        self.widgets_group.add_vertex(self.preset_selection_menubutton,
                                      update_func=self._update_preset_selection_menubutton_func)

        self.widgets_group.add_vertex(self.muxer_combo, signal="changed")
        self.widgets_group.add_vertex(self.video_encoder_combo, signal="changed")
        self.widgets_group.add_vertex(self.frame_rate_combo, signal="changed")
        self.widgets_group.add_vertex(self.audio_encoder_combo, signal="changed")
        self.widgets_group.add_vertex(self.channels_combo, signal="changed")
        self.widgets_group.add_vertex(self.sample_rate_combo, signal="changed")

        self.widgets_group.add_edge(self.muxer_combo, self.preset_selection_menubutton)
        self.widgets_group.add_edge(self.video_encoder_combo, self.preset_selection_menubutton)
        self.widgets_group.add_edge(self.frame_rate_combo, self.preset_selection_menubutton)
        self.widgets_group.add_edge(self.audio_encoder_combo, self.preset_selection_menubutton)
        self.widgets_group.add_edge(self.channels_combo, self.preset_selection_menubutton)
        self.widgets_group.add_edge(self.sample_rate_combo, self.preset_selection_menubutton)

    def _presets_manager_profile_updated_cb(self, presets_manager, preset_item):
        """Handles the saving or removing of a render preset."""
        set_icon_and_title(self.preset_icon, self.preset_label, preset_item)

    def _set_encoding_profile(self, encoding_profile):
        """Sets the encoding profile of the project.

        Args:
            encoding_profile(GstPbutils.EncodingContainerProfile): The profile to set.

        Returns:
            bool: Whether the operation succeeded.
        """
        self.project.set_container_profile(encoding_profile)
        self._setting_encoding_profile = True
        try:
            muxer = Encoders().factories_by_name.get(self.project.muxer)
            if not set_combo_value(self.muxer_combo, muxer):
                self.error("Failed to set muxer_combo to %s", muxer)
                return False

            self.update_available_encoders()
            self._update_valid_audio_restrictions(Gst.ElementFactory.find(self.project.aencoder))
            self._update_valid_video_restrictions(Gst.ElementFactory.find(self.project.vencoder))
            aencoder = Encoders().factories_by_name.get(self.project.aencoder)
            vencoder = Encoders().factories_by_name.get(self.project.vencoder)
            for i, (combo, name, value) in enumerate([
                    (self.audio_encoder_combo, "aencoder", aencoder),
                    (self.video_encoder_combo, "vencoder", vencoder),
                    (self.sample_rate_combo, "audiorate", self.project.audiorate),
                    (self.channels_combo, "audiochannels", self.project.audiochannels),
                    (self.frame_rate_combo, "videorate", self.project.videorate)]):
                if value is None:
                    self.error("%d - Got no value for %s (%s)... rolling back",
                               i, name, combo)
                    return False

                if not set_combo_value(combo, value):
                    self.error("%d - Could not set value %s for combo %s... rolling back",
                               i, value, combo)
                    return False

            self.update_resolution()
            self.project.add_encoding_profile(self.project.container_profile)
            self._update_file_extension()
        finally:
            self._setting_encoding_profile = False

        return True

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
        self.frame_rate_combo.set_model(create_frame_rates_model())
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
        self.preset_selection_menubutton = builder.get_object("preset_selection_menubutton")
        self.preset_label = builder.get_object("preset_label")
        self.preset_icon = builder.get_object("preset_icon")
        self.preset_menubutton = builder.get_object("preset_menubutton")
        self.preset_popover = builder.get_object("preset_popover")
        self.quality_box = builder.get_object("quality_box")
        self.quality_scale = builder.get_object("quality_scale")
        self.quality_adjustment = self.quality_scale.props.adjustment

        self.quality_adjustment_handler_id = self.quality_adjustment.connect("value-changed", self._quality_adjustment_value_changed_cb)

        # round_digits is set to -1 in gtk_scale_set_draw_value.
        # Set it to 0 since we don't care about intermediary values.
        self.quality_scale.props.round_digits = 0

        lower = self.quality_adjustment.props.lower
        upper = self.quality_adjustment.props.upper
        self.quality_scale.add_mark(lower + (upper - lower) / 2, Gtk.PositionType.BOTTOM, _("medium"))
        self.quality_scale.add_mark(upper, Gtk.PositionType.BOTTOM, _("high"))

        self.__automatically_use_proxies = builder.get_object(
            "automatically_use_proxies")

        set_icon_and_title(self.preset_icon, self.preset_label, None)
        self.preset_selection_menubutton.connect("clicked", self._preset_selection_menubutton_clicked_cb)

        self.__always_use_proxies = builder.get_object("always_use_proxies")
        self.__always_use_proxies.props.group = self.__automatically_use_proxies

        self.__never_use_proxies = builder.get_object("never_use_proxies")
        self.__never_use_proxies.props.group = self.__automatically_use_proxies

        self.presets_manager.preset_menubutton_setup(self.preset_menubutton)

        self.window.set_icon_name("system-run-symbolic")
        self.window.set_transient_for(self.app.gui)

        media_types = self.project.ges_timeline.ui.media_types

        self.audio_output_checkbutton.props.active = media_types & GES.TrackType.AUDIO
        self._update_audio_widgets_sensitivity()

        self.video_output_checkbutton.props.active = media_types & GES.TrackType.VIDEO
        self._update_video_widgets_sensitivity()

        self.listbox_setup()

    def listbox_setup(self):
        self.preset_listbox = Gtk.ListBox()
        self.preset_listbox.set_selection_mode(Gtk.SelectionMode.NONE)

        self.preset_listbox.bind_model(self.presets_manager.model, self._create_preset_row_func)

        self.preset_listbox.connect("row-activated", self._preset_listbox_row_activated_cb)
        self.preset_popover.add(self.preset_listbox)

    def _create_preset_row_func(self, preset_item):
        return PresetBoxRow(preset_item)

    def _preset_listbox_row_activated_cb(self, listbox, row):
        if self.apply_preset(row.preset_item):
            quality = Quality.MEDIUM
            if self.quality_scale.get_sensitive():
                quality = self.quality_adjustment.props.value

            self.apply_vcodecsettings_quality(quality)
            self._update_quality_scale()

            self.preset_popover.hide()

    def apply_preset(self, preset_item: PresetItem):
        old_profile = self.project.container_profile
        profile = preset_item.profile.copy()
        if not self._set_encoding_profile(profile):
            self.error("failed to apply the encoding profile, reverting to previous one")
            self._set_encoding_profile(old_profile)
            return False

        self.presets_manager.select_preset(preset_item)
        set_icon_and_title(self.preset_icon, self.preset_label, preset_item)

        return True

    def _preset_selection_menubutton_clicked_cb(self, button):
        self.preset_popover.show_all()

    def _project_video_size_changed_cb(self, project):
        """Handles Project metadata changes."""
        self.update_resolution()

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
        """Applies the project settings to the UI."""
        # Video settings
        fr_datum = (self.project.videorate.num, self.project.videorate.denom)
        model = create_frame_rates_model(fr_datum)
        self.frame_rate_combo.set_model(model)
        set_combo_value(self.frame_rate_combo, self.project.videorate)

        # Audio settings
        res = set_combo_value(self.channels_combo, self.project.audiochannels)
        assert res, self.project.audiochannels
        res = set_combo_value(self.sample_rate_combo, self.project.audiorate)
        assert res, self.project.audiorate

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
        """Applies the project render settings to the UI."""
        # Video settings
        # This will trigger an update of the video resolution label.
        self.scale_spinbutton.set_value(self.project.render_scale)

        # Muxer settings
        model = self.create_combobox_model(Encoders().muxers)
        self.muxer_combo.set_model(model)
        # This will trigger an update of the codec comboboxes.
        muxer = Encoders().factories_by_name.get(self.project.muxer)
        if muxer:
            if not set_combo_value(self.muxer_combo, muxer):
                # The project's muxer is not available on this system.
                # Pick the first one available.
                first = self.muxer_combo.props.model.get_iter_first()
                set_combo_value(self.muxer_combo, first)

    def _check_filename(self):
        """Displays a warning if the file path already exists."""
        filepath = self.fileentry.get_text()
        if not filepath:
            tooltip_text = _("A file name is required.")
            self._is_filename_valid = False
        else:
            filepath = os.path.realpath(filepath)
            if os.path.isdir(filepath):
                tooltip_text = _("A file name is required.")
                self._is_filename_valid = False
            elif os.path.exists(filepath):
                tooltip_text = _("This file already exists.\n"
                                 "If you don't want to overwrite it, choose a "
                                 "different file name or folder.")
                self._is_filename_valid = True
            elif not is_pathname_valid(filepath):
                tooltip_text = _("Invalid file path")
                self._is_filename_valid = False
            else:
                tooltip_text = None
                self._is_filename_valid = True

        warning_icon = "dialog-warning-symbolic" if tooltip_text else None
        self.fileentry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, warning_icon)
        self.fileentry.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, tooltip_text)
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
        estimated_size = current_filesize * length / self.current_position
        # Now let's make it human-readable (instead of octets).
        # If it's in the giga range (10⁹) instead of mega (10⁶), use 2 decimals
        gigabytes = estimated_size / (10 ** 9)
        if gigabytes >= 1:
            return _("%.2f GB") % gigabytes

        megabytes = int(estimated_size / (10 ** 6))
        if megabytes == 0:
            return None
        elif megabytes > 30:
            megabytes = int(round(megabytes, -1))  # -1 means round to 10
        return _("%d MB") % megabytes

    def _update_filename(self, basename):
        """Updates the filename UI element to show the specified file name."""
        extension = extension_for_muxer(self.project.muxer)
        if extension:
            name = "%s%s%s" % (basename, os.path.extsep, extension)
        else:
            name = basename

        self.fileentry.set_text(os.path.join(self.app.settings.lastExportFolder, name))

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
            caps_raw = caps_template_expander(caps_template, value)
            ecaps = Gst.Caps(caps_raw)
            if caps.intersect(ecaps).is_empty():
                self.warning(
                    "Ignoring value because not supported by the encoder: %s",
                    caps_raw)
            else:
                reduced.append((name, value))

        for value in sorted(reduced, key=lambda v: float(v[1])):
            reduced_model.append(value)
        combo.set_model(reduced_model)

        if not set_combo_value(combo, combo_value):
            combo.set_active(len(reduced_model) - 1)
            self.warning("%s in %s not supported, setting: %s",
                         combo_value, caps_template, get_combo_value(combo))

    def _update_valid_audio_restrictions(self, factory):
        template = [t for t in factory.get_static_pad_templates()
                    if t.direction == Gst.PadDirection.SINK][0]

        caps = template.static_caps.get()
        model = create_audio_rates_model(self.project.audiorate)
        self._update_valid_restriction_values(caps, self.sample_rate_combo,
                                              "audio/x-raw,rate=(int)%d",
                                              model,
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

        fr_datum = (self.project.videorate.num, self.project.videorate.denom)
        model = create_frame_rates_model(fr_datum)
        self._update_valid_restriction_values(
            caps, self.frame_rate_combo,
            "video/x-raw,framerate=(GstFraction)%d/%d", model,
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
            encoder = Encoders().factories_by_name.get(preferred_encoder)
            if set_combo_value(encoder_combo, encoder):
                # The preference was found in the combo's model
                # and has been activated.
                return

        # Pick the first encoder from the combobox's model.
        first = encoder_combo.props.model.get_iter_first()
        if not first:
            # Model is empty. Should not happen.
            self.warning("Model is empty")
            return

        if encoder_combo.props.model.iter_has_child(first):
            # There are no supported encoders and the first element is
            # the Unsupported group. Activate its first child.
            first = encoder_combo.props.model.iter_nth_child(first, 0)

        encoder_combo.set_active_iter(first)

    def _element_settings_dialog(self, factory, media_type):
        """Opens a dialog to edit the properties for the specified factory.

        Args:
            factory (Gst.ElementFactory): The factory for editing.
            media_type (str): String describing the media type ("audio" or "video")
        """
        # Reconstitute the property name from the media type (vcodecsettings or acodecsettings)
        properties = getattr(self.project, media_type[0] + "codecsettings")

        self.dialog = GstElementSettingsDialog(factory, properties=properties,
                                               caps=getattr(self.project, media_type + "_profile").get_format(),
                                               parent_window=self.window)
        self.dialog.ok_btn.connect(
            "clicked", self._ok_button_clicked_cb, media_type)

    def __additional_debug_info(self):
        if self.project.vencoder == "x264enc":
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

    def __unset_effect_preview_props(self):
        for clip in self.project.ges_timeline.ui.clips():
            for effect in clip.get_top_effects():
                effect_name = effect.get_property("bin-description")
                if effect_name == "frei0r-filter-3-point-color-balance":
                    effect.set_child_property("split-preview", False)

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
            if self.app.proxy_manager.is_asset_format_well_supported(asset_target):
                return asset_target

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

    def _ok_button_clicked_cb(self, unused_button, media_type):
        assert media_type in ("audio", "video")
        setattr(self.project, media_type[0] + "codecsettings", self.dialog.get_settings())

        caps = self.dialog.get_caps()
        if caps:
            getattr(self.project, media_type + "_profile").set_format(caps)
        self.dialog.window.destroy()

    def _select_file_clicked_cb(self, unused_button):
        chooser = Gtk.FileChooserNative.new(
            _("Select file path to render"),
            self.window,
            Gtk.FileChooserAction.SAVE,
            None, None)

        file_filter = Gtk.FileFilter()
        file_filter.set_name(_("Supported file formats"))
        file_filter.add_custom(Gtk.FileFilterFlags.URI | Gtk.FileFilterFlags.MIME_TYPE,
                               filter_unsupported_media_files)
        chooser.add_filter(file_filter)
        chooser.set_current_folder(self.app.settings.lastExportFolder)
        # Add a shortcut for the project folder (if saved)
        if self.project.uri:
            shortcut = os.path.dirname(self.project.uri)
            chooser.add_shortcut_folder_uri(shortcut)

        response = chooser.run()
        if response == Gtk.ResponseType.DELETE_EVENT:
            # This happens because Gtk.FileChooserNative is confused because we
            # added a filter but since it's ignored it complains there is none.
            # Try again without the filter.
            chooser.remove_filter(file_filter)
            response = chooser.run()

        if response == Gtk.ResponseType.ACCEPT:
            self.app.settings.lastExportFolder = chooser.get_current_folder()
            self.fileentry.set_text(os.path.join(chooser.get_filename()))

    def _render_button_clicked_cb(self, unused_button):
        """Starts the rendering process."""
        self.__replace_proxies()
        self.__unset_effect_preview_props()
        filename = os.path.realpath(self.fileentry.get_text())
        self.outfile = Gst.filename_to_uri(filename)
        self.app.settings.lastExportFolder = os.path.dirname(filename)
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
        self._gst_signal_handlers_ids[bus] = bus.connect("message", self._bus_message_cb)
        self.project.pipeline.connect("position", self._update_position_cb)
        # Force writing the config now, or the path will be reset
        # if the user opens the rendering dialog again
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

    def _fileentry_changed_cb(self, unused_entry):
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
        dialog = ProjectSettingsDialog(self.window, self.project, self.app)
        dialog.window.run()
        self._display_settings()

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
        self._update_quality_scale()

    def _video_settings_button_clicked_cb(self, unused_button):
        if self._setting_encoding_profile:
            return

        factory = get_combo_value(self.video_encoder_combo)
        self._element_settings_dialog(factory, "video")

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
        self._element_settings_dialog(factory, "audio")

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

    def _update_preset_selection_menubutton_func(self, source_widget, target_widget):
        if self._setting_encoding_profile:
            return

        preset_item = self.presets_manager.matching_preset()
        self.presets_manager.select_preset(preset_item)

    def _update_quality_scale(self):
        encoder = get_combo_value(self.video_encoder_combo)
        adapter = quality_adapters.get(encoder.get_name())

        self.quality_scale.set_sensitive(bool(adapter))

        if adapter:
            quality = adapter.calculate_quality(self.project.vcodecsettings)
        else:
            quality = self.quality_adjustment.props.lower
        self.quality_adjustment.handler_block(self.quality_adjustment_handler_id)
        try:
            self.quality_adjustment.props.value = quality
        finally:
            self.quality_adjustment.handler_unblock(self.quality_adjustment_handler_id)

    def _quality_adjustment_value_changed_cb(self, adjustment):
        self.apply_vcodecsettings_quality(self.quality_adjustment.props.value)

    def apply_vcodecsettings_quality(self, quality):
        encoder = get_combo_value(self.video_encoder_combo)
        adapter = quality_adapters.get(encoder.get_name())
        if not adapter:
            # The current video encoder is not yet supported.
            return

        adapter.update_project_vcodecsettings(self.project, round(quality))
