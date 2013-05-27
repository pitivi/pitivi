# -*- coding: utf-8 -*-
# PiTiVi , Non-linear video editor
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
from gi.repository import Gtk
from gi.repository import Gst
from gi.repository import GES
import time

from gettext import gettext as _
from pitivi import configure
from pitivi.utils.signal import Signallable

from pitivi.utils.loggable import Loggable
from pitivi.utils.widgets import GstElementSettingsDialog
from pitivi.utils.ripple_update_group import RippleUpdateGroup
from pitivi.utils.misc import show_user_manual
from pitivi.utils.ui import model, frame_rates, audio_rates, audio_depths, \
    audio_channels, get_combo_value, set_combo_value, beautify_ETA
try:
    import pycanberra
    has_canberra = True
except ImportError:
    has_canberra = False

try:
    from gi.repository import Notify
    has_libnotify = True
except ImportError:
    has_libnotify = False


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
            cls._instance = super(CachedEncoderList, cls).__new__(cls, *args, **kwargs)
            Gst.Registry.get().connect("feature-added", cls._instance._registryFeatureAddedCb)
            cls._instance._buildEncoders()
            cls._instance._buildCombinations()
        return cls._instance

    def _buildEncoders(self):
        self.aencoders = []
        self.vencoders = []
        self.muxers = Gst.ElementFactory.list_get_elements(Gst.ELEMENT_FACTORY_TYPE_MUXER,
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
                self.audio_combination[mux] = sorted(aencs, key=lambda x: - x.get_rank())
                self.video_combination[mux] = sorted(vencs, key=lambda x: - x.get_rank())
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


#--------------------------------- Public classes -----------------------------#
class RenderingProgressDialog(Signallable):
    __signals__ = {
        "pause": [],
        "cancel": [],
    }

    def __init__(self, app, parent):
        self.app = app
        self.main_render_dialog = parent
        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(configure.get_ui_dir(),
            "renderingprogress.ui"))
        self.builder.connect_signals(self)

        self.window = self.builder.get_object("render-progress")
        self.table1 = self.builder.get_object("table1")
        self.progressbar = self.builder.get_object("progressbar")
        self.play_pause_button = self.builder.get_object("play_pause_button")
        self.play_rendered_file_button = self.builder.get_object("play_rendered_file_button")
        self.close_button = self.builder.get_object("close_button")
        self.cancel_button = self.builder.get_object("cancel_button")
        # Parent the dialog with mainwindow, since renderingdialog is hidden.
        # It allows this dialog to properly minimize together with mainwindow
        self.window.set_transient_for(self.app.gui)

        # UI widgets
        self.window.set_icon_from_file(configure.get_pixmap_dir() + "/pitivi-render-16.png")

        # TODO: show this widget for rendering statistics (bug 637079)
        self.table1.hide()

        # We will only show the close/play buttons when the render is done:
        self.play_rendered_file_button.hide()
        self.close_button.hide()

    def updatePosition(self, fraction, estimated):
        self.progressbar.set_fraction(fraction)
        self.window.set_title(_("%d%% Rendered") % int(100 * fraction))
        if estimated:
            # Translators: this string indicates the estimated time
            # remaining until an action (such as rendering) completes.
            # The "%s" is an already-localized human-readable duration,
            # such as "31 seconds", "1 minute" or "1 hours, 14 minutes".
            # In some languages, "About %s left" can be expressed roughly as
            # "There remains approximatively %s" (to handle gender and plurals).
            self.progressbar.set_text(_("About %s left") % estimated)
        else:
            self.progressbar.set_text(_("Estimating..."))

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
        os.system('xdg-open "%s"' % self.main_render_dialog.outfile)


class RenderDialog(Loggable):
    """Render dialog box.

    @ivar preferred_aencoder: The last audio encoder selected by the user.
    @type preferred_aencoder: str
    @ivar preferred_vencoder: The last video encoder selected by the user.
    @type preferred_vencoder: str
    """
    INHIBIT_REASON = _("Currently rendering")

    def __init__(self, app, project, pipeline=None):

        from pitivi.preset import RenderPresetManager

        Loggable.__init__(self)

        self.app = app
        self.project = project
        self.system = app.system
        if pipeline is not None:
            self._pipeline = pipeline
        else:
            self._pipeline = self.project.pipeline

        self.outfile = None
        self.notification = None
        self.timestarted = 0

        # Various gstreamer signal connection ID's
        # {object: sigId}
        self._gstSigId = {}

        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(configure.get_ui_dir(),
            "renderingdialog.ui"))
        self._setProperties()
        self.builder.connect_signals(self)

        # UI widgets
        icon = os.path.join(configure.get_pixmap_dir(), "pitivi-render-16.png")
        self.window.set_icon_from_file(icon)

        # Set the shading style in the toolbar below presets
        presets_toolbar = self.builder.get_object("render_presets_toolbar")
        presets_toolbar.get_style_context().add_class("inline-toolbar")

        # FIXME: re-enable this widget when bug #637078 is implemented
        self.selected_only_button.destroy()

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

        self._initializeComboboxModels()
        self._displaySettings()
        self._displayRenderSettings()

        self.window.connect("delete-event", self._deleteEventCb)
        self.project.connect("rendering-settings-changed", self._settingsChanged)

        # Monitor changes

        self.wg = RippleUpdateGroup()
        self.wg.addVertex(self.frame_rate_combo, signal="changed")
        self.wg.addVertex(self.save_render_preset_button, update_func=self._updateRenderSaveButton)
        self.wg.addVertex(self.channels_combo, signal="changed")
        self.wg.addVertex(self.sample_rate_combo, signal="changed")
        self.wg.addVertex(self.sample_depth_combo, signal="changed")
        self.wg.addVertex(self.muxercombobox, signal="changed")
        self.wg.addVertex(self.audio_encoder_combo, signal="changed")
        self.wg.addVertex(self.video_encoder_combo, signal="changed")
        self.render_presets = RenderPresetManager()
        self.render_presets.loadAll()

        self._fillPresetsTreeview(
            self.render_preset_treeview,
            self.render_presets,
            self._updateRenderPresetButtons)

        self.wg.addEdge(self.frame_rate_combo, self.save_render_preset_button)
        self.wg.addEdge(self.audio_encoder_combo, self.save_render_preset_button)
        self.wg.addEdge(self.video_encoder_combo, self.save_render_preset_button)
        self.wg.addEdge(self.muxercombobox, self.save_render_preset_button)
        self.wg.addEdge(self.channels_combo, self.save_render_preset_button)
        self.wg.addEdge(self.sample_rate_combo, self.save_render_preset_button)
        self.wg.addEdge(self.sample_depth_combo, self.save_render_preset_button)

        self._infobarForPresetManager = {self.render_presets: self.render_preset_infobar}

        # Bind widgets to RenderPresetsManager
        self.bindCombo(self.render_presets, "channels", self.channels_combo)
        self.bindCombo(self.render_presets, "sample-rate", self.sample_rate_combo)
        self.bindCombo(self.render_presets, "depth", self.sample_depth_combo)
        self.bindCombo(self.render_presets, "acodec", self.audio_encoder_combo)
        self.bindCombo(self.render_presets, "vcodec", self.video_encoder_combo)
        self.bindCombo(self.render_presets, "container", self.muxercombobox)
        self.bindCombo(self.render_presets, "frame-rate", self.frame_rate_combo)
        self.bindHeight(self.render_presets)
        self.bindWidth(self.render_presets)

        self.createNoPreset(self.render_presets)

    def createNoPreset(self, mgr):
        mgr.prependPreset(_("No preset"), {
            "depth": int(get_combo_value(self.sample_depth_combo)),
            "channels": int(get_combo_value(self.channels_combo)),
            "sample-rate": int(get_combo_value(self.sample_rate_combo)),
            "acodec": get_combo_value(self.audio_encoder_combo).get_name(),
            "vcodec": get_combo_value(self.video_encoder_combo).get_name(),
            "container": get_combo_value(self.muxercombobox).get_name(),
            "frame-rate": Gst.Fraction(
                int(get_combo_value(self.frame_rate_combo).num),
                int(get_combo_value(self.frame_rate_combo).denom)),
            "height": self.project.videoheight,
            "width": self.project.videowidth})

    def bindCombo(self, mgr, name, widget):
        if name == "container":
            mgr.bindWidget(name,
                lambda x: self.muxer_setter(widget, x),
                lambda: get_combo_value(widget).get_name())

        elif name == "acodec":
            mgr.bindWidget(name,
                lambda x: self.acodec_setter(widget, x),
                lambda: get_combo_value(widget).get_name())

        elif name == "vcodec":
            mgr.bindWidget(name,
                lambda x: self.vcodec_setter(widget, x),
                lambda: get_combo_value(widget).get_name())

        elif name == "depth":
            mgr.bindWidget(name,
                lambda x: self.sample_depth_setter(widget, x),
                lambda: get_combo_value(widget))

        elif name == "sample-rate":
            mgr.bindWidget(name,
                lambda x: self.sample_rate_setter(widget, x),
                lambda: get_combo_value(widget))

        elif name == "channels":
            mgr.bindWidget(name,
                lambda x: self.channels_setter(widget, x),
                lambda: get_combo_value(widget))

        elif name == "frame-rate":
            mgr.bindWidget(name,
                lambda x: self.framerate_setter(widget, x),
                lambda: get_combo_value(widget))

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

    def sample_depth_setter(self, widget, value):
        self.project.audiodepth = set_combo_value(widget, value)

    def sample_rate_setter(self, widget, value):
        self.project.audiorate = set_combo_value(widget, value)

    def channels_setter(self, widget, value):
        self.project.audiochannels = set_combo_value(widget, value)

    def framerate_setter(self, widget, value):
        self.project.videorate = set_combo_value(widget, value)

    def bindHeight(self, mgr):
        mgr.bindWidget("height",
                    lambda x: setattr(self.project, "videoheight", x),
                    lambda: 0)

    def bindWidth(self, mgr):
        mgr.bindWidget("width",
                    lambda x: setattr(self.project, "videowidth", x),
                    lambda: 0)

    def _fillPresetsTreeview(self, treeview, mgr, update_buttons_func):
        """Set up the specified treeview to display the specified presets.

        @param treeview: The treeview for displaying the presets.
        @type treeview: TreeView
        @param mgr: The preset manager.
        @type mgr: PresetManager
        @param update_buttons_func: A function which updates the buttons for
        removing and saving a preset, enabling or disabling them accordingly.
        @type update_buttons_func: function
        """
        renderer = Gtk.CellRendererText()
        renderer.props.editable = True
        column = Gtk.TreeViewColumn("Preset", renderer, text=0)
        treeview.append_column(column)
        treeview.props.headers_visible = False
        model = mgr.getModel()
        treeview.set_model(model)
        model.connect("row-inserted", self._newPresetCb, column, renderer, treeview)
        renderer.connect("edited", self._presetNameEditedCb, mgr)
        renderer.connect("editing-started", self._presetNameEditingStartedCb, mgr)
        treeview.get_selection().connect("changed", self._presetChangedCb,
                                        mgr, update_buttons_func)
        treeview.connect("focus-out-event", self._treeviewDefocusedCb, mgr)

    def _newPresetCb(self, model, path, iter_, column, renderer, treeview):
        """Handle the addition of a preset to the model of the preset manager.
        """
        treeview.set_cursor_on_cell(path, column, renderer, start_editing=True)
        treeview.grab_focus()

    def _presetNameEditedCb(self, renderer, path, new_text, mgr):
        """Handle the renaming of a preset."""
        from pitivi.preset import DuplicatePresetNameException

        try:
            mgr.renamePreset(path, new_text)
            self._updateRenderPresetButtons()
        except DuplicatePresetNameException:
            error_markup = _('"%s" already exists.') % new_text
            self._showPresetManagerError(mgr, error_markup)

    def _presetNameEditingStartedCb(self, renderer, editable, path, mgr):
        """Handle the start of a preset renaming."""
        self._hidePresetManagerError(mgr)

    def _treeviewDefocusedCb(self, widget, event, mgr):
        """Handle the treeview loosing the focus."""
        self._hidePresetManagerError(mgr)

    def _showPresetManagerError(self, mgr, error_markup):
        """Show the specified error on the infobar associated with the manager.

        @param mgr: The preset manager for which to show the error.
        @type mgr: PresetManager
        """
        infobar = self._infobarForPresetManager[mgr]
        # The infobar must contain exactly one object in the content area:
        # a label for displaying the error.
        label = infobar.get_content_area().children()[0]
        label.set_markup(error_markup)
        infobar.show()

    def _hidePresetManagerError(self, mgr):
        """Hide the error infobar associated with the manager.

        @param mgr: The preset manager for which to hide the error infobar.
        @type mgr: PresetManager
        """
        infobar = self._infobarForPresetManager[mgr]
        infobar.hide()

    def _updateRenderSaveButton(self, unused_in, button):
        button.set_sensitive(self.render_presets.isSaveButtonSensitive())

    @staticmethod
    def _getUniquePresetName(mgr):
        """Get a unique name for a new preset for the specified PresetManager.
        """
        existing_preset_names = list(mgr.getPresetNames())
        preset_name = _("New preset")
        i = 1
        while preset_name in existing_preset_names:
            preset_name = _("New preset %d") % i
            i += 1
        return preset_name

    def _addRenderPresetButtonClickedCb(self, button):
        preset_name = self._getUniquePresetName(self.render_presets)
        self.render_presets.addPreset(preset_name, {
            "depth": int(get_combo_value(self.sample_depth_combo)),
            "channels": int(get_combo_value(self.channels_combo)),
            "sample-rate": int(get_combo_value(self.sample_rate_combo)),
            "acodec": get_combo_value(self.audio_encoder_combo).get_name(),
            "vcodec": get_combo_value(self.video_encoder_combo).get_name(),
            "container": get_combo_value(self.muxercombobox).get_name(),
            "frame-rate": Gst.Fraction(int(get_combo_value(self.frame_rate_combo).num),
                            int(get_combo_value(self.frame_rate_combo).denom)),
            "height": 0,
            "width": 0})

        self.render_presets.restorePreset(preset_name)
        self._updateRenderPresetButtons()

    def _saveRenderPresetButtonClickedCb(self, button):
        self.render_presets.saveCurrentPreset()
        self.save_render_preset_button.set_sensitive(False)
        self.remove_render_preset_button.set_sensitive(True)

    def _updateRenderPresetButtons(self):
        can_save = self.render_presets.isSaveButtonSensitive()
        self.save_render_preset_button.set_sensitive(can_save)
        can_remove = self.render_presets.isRemoveButtonSensitive()
        self.remove_render_preset_button.set_sensitive(can_remove)

    def _removeRenderPresetButtonClickedCb(self, button):
        selection = self.render_preset_treeview.get_selection()
        model, iter_ = selection.get_selected()
        if iter_:
            self.render_presets.removePreset(model[iter_][0])

    def _presetChangedCb(self, selection, mgr, update_preset_buttons_func):
        """Handle the selection of a preset."""
        model, iter_ = selection.get_selected()
        if iter_:
            self.selected_preset = model[iter_][0]
        else:
            self.selected_preset = None

        mgr.restorePreset(self.selected_preset)
        self._displaySettings()
        update_preset_buttons_func()
        self._hidePresetManagerError(mgr)

    def _setProperties(self):
        self.window = self.builder.get_object("render-dialog")
        self.selected_only_button = self.builder.get_object("selected_only_button")
        self.video_output_checkbutton = self.builder.get_object("video_output_checkbutton")
        self.audio_output_checkbutton = self.builder.get_object("audio_output_checkbutton")
        self.render_button = self.builder.get_object("render_button")
        self.video_settings_button = self.builder.get_object("video_settings_button")
        self.audio_settings_button = self.builder.get_object("audio_settings_button")
        self.frame_rate_combo = self.builder.get_object("frame_rate_combo")
        self.scale_spinbutton = self.builder.get_object("scale_spinbutton")
        self.channels_combo = self.builder.get_object("channels_combo")
        self.sample_rate_combo = self.builder.get_object("sample_rate_combo")
        self.sample_depth_combo = self.builder.get_object("sample_depth_combo")
        self.muxercombobox = self.builder.get_object("muxercombobox")
        self.audio_encoder_combo = self.builder.get_object("audio_encoder_combo")
        self.video_encoder_combo = self.builder.get_object("video_encoder_combo")
        self.filebutton = self.builder.get_object("filebutton")
        self.fileentry = self.builder.get_object("fileentry")
        self.resolution_label = self.builder.get_object("resolution_label")
        self.render_preset_treeview = self.builder.get_object("render_preset_treeview")
        self.save_render_preset_button = self.builder.get_object("save_render_preset_button")
        self.remove_render_preset_button = self.builder.get_object("remove_render_preset_button")
        self.render_preset_infobar = self.builder.get_object("render-preset-infobar")

    def _settingsChanged(self, project, key, value):
        self.updateResolution()

    def _initializeComboboxModels(self):
        # Avoid loop import
        self.frame_rate_combo.set_model(frame_rates)
        self.channels_combo.set_model(audio_channels)
        self.sample_rate_combo.set_model(audio_rates)
        self.sample_depth_combo.set_model(audio_depths)
        self.muxercombobox.set_model(factorylist(CachedEncoderList().muxers))

    def _displaySettings(self):
        """Display the settings that also change in the ProjectSettingsDialog.
        """
        # Video settings
        set_combo_value(self.frame_rate_combo, self.project.videorate)
        # Audio settings
        set_combo_value(self.channels_combo, self.project.audiochannels)
        set_combo_value(self.sample_rate_combo, self.project.audiorate)
        set_combo_value(self.sample_depth_combo, self.project.audiodepth)

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

    def _checkForExistingFile(self, *args):
        """
        Display a warning icon and tooltip if the file path already exists.
        """
        path = self.filebutton.get_current_folder()
        if not path:
            # This happens when the window is initialized.
            return
        warning_icon = Gtk.STOCK_DIALOG_WARNING
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
        self.fileentry.set_icon_from_stock(1, warning_icon)
        self.fileentry.set_icon_tooltip_text(1, tooltip_text)

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
        vencoder_model = factorylist(encoders.video_combination[self.project.muxer])
        self.video_encoder_combo.set_model(vencoder_model)

        aencoder_model = factorylist(encoders.audio_combination[self.project.muxer])
        self.audio_encoder_combo.set_model(aencoder_model)

        self._updateEncoderCombo(self.video_encoder_combo, self.preferred_vencoder)
        self._updateEncoderCombo(self.audio_encoder_combo, self.preferred_aencoder)

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
                                            parent_window=self.window)
        self.dialog.ok_btn.connect("clicked", self._okButtonClickedCb, settings_attr)

    def _showRenderErrorDialog(self, error, details):
        primary_message = _("Sorry, something didn’t work right.")
        secondary_message = _("An error occured while trying to render your "
            "project. You might want to check our troubleshooting guide or "
            "file a bug report. See the details below for some basic "
            "information that may help identify the problem.")

        dialog = Gtk.MessageDialog(self.window, Gtk.DialogFlags.MODAL,
            Gtk.MessageType.ERROR, Gtk.ButtonsType.OK,
            primary_message)
        dialog.set_property("secondary-text", secondary_message)

        expander = Gtk.Expander()
        expander.set_label(_("Details"))
        details_label = Gtk.Label(str(error) + "\n\n" + str(details))
        details_label.set_line_wrap(True)
        details_label.set_selectable(True)
        expander.add(details_label)
        dialog.get_message_area().add(expander)
        dialog.show_all()  # Ensure the expander and its children show up
        dialog.run()
        dialog.destroy()

    def startAction(self):
        """ Start the render process """
        self._pipeline.set_state(Gst.State.NULL)
        self._pipeline.set_mode(GES.PipelineFlags.SMART_RENDER)
        encodebin = self._pipeline.get_by_name("internal-encodebin")
        self._gstSigId[encodebin] = encodebin.connect("element-added", self._elementAddedCb)
        self._pipeline.set_state(Gst.State.PLAYING)

    def _cancelRender(self, *unused_args):
        self.debug("Aborting render")
        self._shutDown()
        self._destroyProgressWindow()

    def _shutDown(self):
        """ The render process has been aborted, shutdown the gstreamer pipeline
        and disconnect from its signals """
        self._pipeline.set_state(Gst.State.NULL)
        self._disconnectFromGst()
        self._pipeline.set_mode(GES.PipelineFlags.FULL_PREVIEW)

    def _pauseRender(self, progress):
        self.app.current.pipeline.togglePlayback()

    def _destroyProgressWindow(self):
        """ Handle the completion or the cancellation of the render process. """
        self.progress.window.destroy()
        self.progress = None
        self.window.show()  # Show the rendering dialog again

    def _disconnectFromGst(self):
        for obj, id in self._gstSigId.iteritems():
            obj.disconnect(id)
        self._gstSigId = {}
        self.app.current.pipeline.disconnect_by_func(self._updatePositionCb)

    def destroy(self):
        self.window.destroy()

    #------------------- Callbacks ------------------------------------------#

    #-- UI callbacks
    def _okButtonClickedCb(self, unused_button, settings_attr):
        setattr(self, settings_attr, self.dialog.getSettings())
        self.dialog.window.destroy()

    def _renderButtonClickedCb(self, unused_button):
        """
        The render button inside the render dialog has been clicked,
        start the rendering process.
        """
        self.outfile = os.path.join(self.filebutton.get_uri(),
                                    self.fileentry.get_text())
        self.progress = RenderingProgressDialog(self.app, self)
        self.window.hide()  # Hide the rendering settings dialog while rendering

        self._pipeline.set_render_settings(self.outfile, self.project.container_profile)
        self.startAction()
        self.progress.window.show()
        self.progress.connect("cancel", self._cancelRender)
        self.progress.connect("pause", self._pauseRender)
        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        self._gstSigId[bus] = bus.connect('message', self._busMessageCb)
        self.app.current.pipeline.connect("position", self._updatePositionCb)
        # Force writing the config now, or the path will be reset
        # if the user opens the rendering dialog again
        self.app.settings.lastExportFolder = self.filebutton.get_current_folder()
        self.app.settings.storeSettings()

    def _closeButtonClickedCb(self, unused_button):
        self.debug("Render dialog's Close button clicked")
        self.destroy()

    def _deleteEventCb(self, window, event):
        self.debug("Render dialog is being deleted")
        self.destroy()

    def _containerContextHelpClickedCb(self, unused_button):
        show_user_manual("codecscontainers")

    #-- GStreamer callbacks
    def _busMessageCb(self, unused_bus, message):
        if message.type == Gst.MessageType.EOS:  # Render complete
            self.debug("got EOS message, render complete")
            self._shutDown()
            self.progress.progressbar.set_text(_("Render complete"))
            self.progress.window.set_title(_("Render complete"))
            if has_libnotify:
                Notify.init("pitivi")
                if not self.progress.window.is_active():
                    self.notification = Notify.Notification.new(_("Render complete"), _('"%s" has finished rendering.' % self.fileentry.get_text()), "pitivi")
                    self.notification.show()
            if has_canberra:
                canberra = pycanberra.Canberra()
                canberra.play(1, pycanberra.CA_PROP_EVENT_ID, "complete-media", None)
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
                        self.debug("Rendering started/resumed, resetting ETA calculation and inhibiting sleep")
                        self.timestarted = time.time()
                        self.system.inhibitSleep(RenderDialog.INHIBIT_REASON)
                    else:
                        self.system.uninhibitSleep(RenderDialog.INHIBIT_REASON)

    def _updatePositionCb(self, pipeline, position):
        if self.progress:
            text = None
            timediff = time.time() - self.timestarted
            length = self.app.current.timeline.props.duration
            fraction = float(min(position, length)) / float(length)
            if timediff > 5.0 and position:
                # only display ETA after 5s in order to have enough averaging and
                # if the position is non-null
                totaltime = (timediff * float(length) / float(position)) - timediff
                text = beautify_ETA(int(totaltime * Gst.SECOND))
            self.progress.updatePosition(fraction, text)

    def _elementAddedCb(self, bin, element):
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

        for propname, value in settings.iteritems():
            element.set_property(propname, value)
            self.debug("Setting %s to %s", propname, value)

    #-- Settings changed callbacks
    def _scaleSpinbuttonChangedCb(self, button):
        render_scale = self.scale_spinbutton.get_value()
        self.project.render_scale = render_scale
        self.updateResolution()

    def updateResolution(self):
        width, height = self.project.getVideoWidthAndHeight(render=True)
        self.resolution_label.set_text(u"%d×%d" % (width, height))

    def _projectSettingsButtonClickedCb(self, button):
        from pitivi.project import ProjectSettingsDialog
        dialog = ProjectSettingsDialog(self.window, self.project)
        dialog.window.run()

    def _audioOutputCheckbuttonToggledCb(self, audio):
        active = self.audio_output_checkbutton.get_active()
        if active:
            self.channels_combo.set_sensitive(True)
            self.sample_rate_combo.set_sensitive(True)
            self.sample_depth_combo.set_sensitive(True)
            self.audio_encoder_combo.set_sensitive(True)
            self.audio_settings_button.set_sensitive(True)
            self.render_button.set_sensitive(True)
        else:
            self.channels_combo.set_sensitive(False)
            self.sample_rate_combo.set_sensitive(False)
            self.sample_depth_combo.set_sensitive(False)
            self.audio_encoder_combo.set_sensitive(False)
            self.audio_settings_button.set_sensitive(False)
            if not self.video_output_checkbutton.get_active():
                self.render_button.set_sensitive(False)

    def _videoOutputCheckbuttonToggledCb(self, video):
        active = self.video_output_checkbutton.get_active()
        if active:
            self.scale_spinbutton.set_sensitive(True)
            self.frame_rate_combo.set_sensitive(True)
            self.video_encoder_combo.set_sensitive(True)
            self.video_settings_button.set_sensitive(True)
            self.render_button.set_sensitive(True)
        else:
            self.scale_spinbutton.set_sensitive(False)
            self.frame_rate_combo.set_sensitive(False)
            self.video_encoder_combo.set_sensitive(False)
            self.video_settings_button.set_sensitive(False)
            if not self.audio_output_checkbutton.get_active():
                self.render_button.set_sensitive(False)

    def _frameRateComboChangedCb(self, combo):
        framerate = get_combo_value(combo)
        self.project.framerate = framerate

    def _videoEncoderComboChangedCb(self, combo):
        vencoder = get_combo_value(combo).get_name()
        self.project.vencoder = vencoder

        if not self.muxer_combo_changing:
            # The user directly changed the video encoder combo.
            self.preferred_vencoder = vencoder

    def _videoSettingsButtonClickedCb(self, button):
        factory = get_combo_value(self.video_encoder_combo)
        self._elementSettingsDialog(factory, 'vcodecsettings')

    def _channelsComboChangedCb(self, combo):
        self.project.audiochannels = get_combo_value(combo)

    def _sampleDepthComboChangedCb(self, combo):
        self.project.audiodepth = get_combo_value(combo)

    def _sampleRateComboChangedCb(self, combo):
        self.project.audiorate = get_combo_value(combo)

    def _audioEncoderChangedComboCb(self, combo):
        aencoder = get_combo_value(combo).get_name()
        self.project.aencoder = aencoder
        if not self.muxer_combo_changing:
            # The user directly changed the audio encoder combo.
            self.preferred_aencoder = aencoder

    def _audioSettingsButtonClickedCb(self, button):
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
