# -*- coding: utf-8 -*-
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
from gettext import gettext as _

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

from pitivi.ui.preset import RenderPresetManager

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
    @ivar settings: The settings used for rendering.
    @type settings: ExportSettings
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

        # The Render dialog and the Project Settings dialog have some
        # common settings, for example the audio sample rate.
        # When these common settings are changed in the Render dialog,
        # we don't want them to be saved, so we create a copy of the project's
        # settings to be used by the Render dialog for rendering.
        render_settings = project.getSettings().copy()
        # Note: render_settings will end up as self.settings.
        Renderer.__init__(self, project,
                pipeline=pipeline, settings=render_settings)

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

        self.render_presets = RenderPresetManager()
        self.render_presets.load()

        self._fillPresetsTreeview(
                self.render_preset_treeview, self.render_presets,
                self._updateRenderPresetButtons)

        # Bind widgets to RenderPresetsManager
        self.bindCombo(self.render_presets, "channels",
            self.channels_combo)
        self.bindCombo(self.render_presets, "sample-rate",
            self.sample_rate_combo)
        self.bindCombo(self.render_presets, "depth",
            self.sample_depth_combo)
        self.bindCombo(self.render_presets, "acodec",
            self.audio_encoder_combo)
        self.bindCombo(self.render_presets, "vcodec",
            self.video_encoder_combo)
        self.bindCombo(self.render_presets, "container",
            self.muxercombobox)
        self.bindCombo(self.render_presets, "frame-rate",
            self.frame_rate_combo)
        self.bindHeight(self.render_presets)
        self.bindWidth(self.render_presets)

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
        set_combo_value(widget, gst.element_factory_find(value))
        self.settings.setEncoders(muxer=value)

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
        set_combo_value(widget, gst.element_factory_find(value))
        self.settings.setEncoders(aencoder=value)
        if not self.muxer_combo_changing:
            # The user directly changed the audio encoder combo.
            self.preferred_aencoder = value

    def vcodec_setter(self, widget, value):
        set_combo_value(widget, gst.element_factory_find(value))
        self.settings.setEncoders(vencoder=value)
        if not self.muxer_combo_changing:
            # The user directly changed the video encoder combo.
            self.preferred_vencoder = value

    def sample_depth_setter(self, widget, value):
        set_combo_value(widget, value)
        self.settings.setAudioProperties(depth=value)

    def sample_rate_setter(self, widget, value):
        set_combo_value(widget, value)
        self.settings.setAudioProperties(rate=value)

    def channels_setter(self, widget, value):
        set_combo_value(widget, value)
        self.settings.setAudioProperties(nbchanns=value)

    def framerate_setter(self, widget, value):
        set_combo_value(widget, value)
        self.settings.setVideoProperties(framerate=value)

    def bindHeight(self, mgr):
        mgr.bindWidget("height",
                       lambda x: self.settings.setVideoProperties(height=x),
                       lambda: self.getDimension("height"))

    def bindWidth(self, mgr):
        mgr.bindWidget("width",
                       lambda x: self.settings.setVideoProperties(width=x),
                       lambda: self.getDimension("width"))

    def getDimension(self, dimension):
        value = self.settings.getVideoWidthAndHeight()
        if dimension == "height":
            return value[1]
        elif dimension == "width":
            return value[0]

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
        renderer = gtk.CellRendererText()
        renderer.props.editable = True
        column = gtk.TreeViewColumn("Preset", renderer, text=0)
        treeview.append_column(column)
        treeview.props.headers_visible = False
        model = mgr.getModel()
        treeview.set_model(model)
        model.connect("row-inserted", self._newPresetCb,
            column, renderer, treeview)
        renderer.connect("edited", self._presetNameEditedCb, mgr)
        treeview.get_selection().connect("changed", self._presetChangedCb,
            mgr, update_buttons_func)

    def _newPresetCb(self, model, path, iter_, column, renderer, treeview):
        """Handle the addition of a preset to the model of the preset manager.
        """
        treeview.set_cursor_on_cell(path, column, renderer, start_editing=True)
        treeview.grab_focus()

    def _presetNameEditedCb(self, renderer, path, new_text, mgr):
        """Handle the renaming of a preset."""
        try:
            mgr.renamePreset(path, new_text)
        except DuplicatePresetNameException:
            error_markup = _('"%s" already exists.') % new_text
            self._showPresetManagerError(mgr, error_markup)

    @staticmethod
    def _getUniquePresetName(mgr):
        """Get a unique name for a new preset for the specified PresetManager.
        """
        existing_preset_names = list(mgr.getPresetNames())
        preset_name = _("New Preset")
        i = 1
        while preset_name in existing_preset_names:
            preset_name = _("New Preset %d") % i
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
            "frame-rate": gst.Fraction(int(get_combo_value(self.frame_rate_combo).num),
                                        int(get_combo_value(self.frame_rate_combo).denom)),
            "height": self.getDimension("height"),
            "width": self.getDimension("width")
        })
        self.render_presets.restorePreset(preset_name)
        self._updateRenderPresetButtons()

    def _saveRenderPresetButtonClickedCb(self, button):
        self.render_presets.savePreset()
        self.save_render_preset_button.set_sensitive(False)

    def _copyRenderPresets(self, cur_preset):
        #  Copies current settings to presets

        self.render_presets.savePreset()
        self.render_presets.save()

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
        self.render_preset_treeview = self.builder.get_object(
                                        "render_preset_treeview")
        self.save_render_preset_button = self.builder.get_object(
                                        "save_render_preset_button")
        self.remove_render_preset_button = self.builder.get_object(
                                        "remove_render_preset_button")

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

    def _checkForExistingFile(self, *args):
        """
        Display a warning icon and tooltip if the file path already exists.
        """
        path = self.filebutton.get_current_folder()
        if not path:
            # This happens when the window is initialized.
            return
        warning_icon = gtk.STOCK_DIALOG_WARNING
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
        self.resolution_label.set_text(u"%d×%d" % (width, height))

    def _projectSettingsButtonClickedCb(self, button):
        from pitivi.ui.projectsettings import ProjectSettingsDialog
        dialog = ProjectSettingsDialog(self.window, self.project)
        dialog.window.connect("destroy", self._projectSettingsDestroyCb)
        dialog.window.run()

    def _projectSettingsDestroyCb(self, dialog):
        """Handle the destruction of the ProjectSettingsDialog."""
        settings = self.project.getSettings()
        self.settings.setVideoProperties(width=settings.videowidth,
                                         height=settings.videoheight,
                                         framerate=settings.videorate)
        self.settings.setAudioProperties(nbchanns=settings.audiochannels,
                                         rate=settings.audiorate,
                                         depth=settings.audiodepth)
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
        factory = get_combo_value(self.video_encoder_combo)
        self._elementSettingsDialog(factory, 'vcodecsettings')

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
        factory = get_combo_value(self.audio_encoder_combo)
        self._elementSettingsDialog(factory, 'acodecsettings')

    def _elementSettingsDialog(self, factory, settings_attr):
        """Open a dialog to edit the properties for the specified factory.

        @param factory: An element factory whose properties the user will edit.
        @type factory: gst.ElementFactory
        @param settings_attr: The ExportSettings attribute holding
        the properties.
        @type settings_attr: str
        """
        properties = getattr(self.settings, settings_attr)
        self.dialog = GstElementSettingsDialog(factory, properties=properties)
        self.dialog.window.set_transient_for(self.window)
        self.dialog.ok_btn.connect("clicked", self._okButtonClickedCb, settings_attr)
        self.dialog.window.run()

    def _okButtonClickedCb(self, unused_button, settings_attr):
        setattr(self.settings, settings_attr, self.dialog.getSettings())
        self.dialog.window.destroy()

    def _renderButtonClickedCb(self, unused_button):
        self.outfile = os.path.join(self.filebutton.get_uri(),
                                    self.fileentry.get_text())
        self.progress = EncodingProgressDialog(self.app, self)
        self.window.hide()  # Hide the rendering settings dialog while rendering
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

    def _updateProjectSettings(self):
        """Updates the settings of the project if the render settings changed.
        """
        settings = self.project.getSettings()
        if (settings.muxer == self.settings.muxer
            and settings.aencoder == self.settings.aencoder
            and settings.vencoder == self.settings.vencoder
            and settings.containersettings == self.settings.containersettings
            and settings.acodecsettings == self.settings.acodecsettings
            and settings.vcodecsettings == self.settings.vcodecsettings
            and settings.render_scale == self.settings.render_scale):
            # No setting which can be changed in the Render dialog
            # and which we want to save have been changed.
            return
        settings.setEncoders(muxer=self.settings.muxer,
                             aencoder=self.settings.aencoder,
                             vencoder=self.settings.vencoder)
        settings.containersettings = self.settings.containersettings
        settings.acodecsettings = self.settings.acodecsettings
        settings.vcodecsettings = self.settings.vcodecsettings
        settings.setVideoProperties(render_scale=self.settings.render_scale)
        # Signal that the project settings have been changed.
        self.project.setSettings(settings)

    def destroy(self):
        self._updateProjectSettings()
        self.window.destroy()
