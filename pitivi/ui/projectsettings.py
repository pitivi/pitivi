# PiTiVi , Non-linear video editor
#
#       ui/projectsettings.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
# Copyright (c) 2010, Brandon Lewis <brandon.lewis@collabora.co.uk>
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
Dialog box for project settings
"""

import gtk
import gst
import os

from datetime import datetime

from pitivi.configure import get_ui_dir
from gettext import gettext as _
from pitivi.ui.dynamic import FractionWidget
from pitivi.ui.ripple_update_group import RippleUpdateGroup
from pitivi.ui.common import\
    model,\
    frame_rates,\
    audio_rates,\
    audio_depths,\
    audio_channels,\
    get_combo_value,\
    set_combo_value

from pitivi.ui.preset import AudioPresetManager, DuplicatePresetNameException,\
    VideoPresetManager

# FIXME: are we sure the following tables correct?

pixel_aspect_ratios = model((str, object), (
    (_("Square"), gst.Fraction(1, 1)),
    (_("480p"), gst.Fraction(10, 11)),
    (_("480i"), gst.Fraction(8, 9)),
    (_("480p Wide"), gst.Fraction(40, 33)),
    (_("480i Wide"), gst.Fraction(32, 27)),
    (_("576p"), gst.Fraction(12, 11)),
    (_("576i"), gst.Fraction(16, 15)),
    (_("576p Wide"), gst.Fraction(16, 11)),
    (_("576i Wide"), gst.Fraction(64, 45)),
))

display_aspect_ratios = model((str, object), (
    (_("Standard (4:3)"), gst.Fraction(4, 3)),
    (_("DV (15:11)"), gst.Fraction(15, 11)),
    (_("DV Widescreen (16:9)"), gst.Fraction(16, 9)),
    (_("Cinema (1.37)"), gst.Fraction(11, 8)),
    (_("Cinema (1.66)"), gst.Fraction(166, 100)),
    (_("Cinema (1.85)"), gst.Fraction(185, 100)),
    (_("Anamorphic (2.35)"), gst.Fraction(235, 100)),
    (_("Anamorphic (2.39)"), gst.Fraction(239, 100)),
    (_("Anamorphic (2.4)"), gst.Fraction(24, 10)),
))


class ProjectSettingsDialog():

    def __init__(self, parent, project):
        self.project = project
        self.settings = project.getSettings()

        self.builder = gtk.Builder()
        self.builder.add_from_file(os.path.join(get_ui_dir(),
            "projectsettings.ui"))
        self._setProperties()
        self.builder.connect_signals(self)

        # add custom display aspect ratio widget
        self.dar_fraction_widget = FractionWidget()
        self.video_properties_table.attach(self.dar_fraction_widget,
            0, 1, 6, 7, xoptions=gtk.EXPAND | gtk.FILL, yoptions=0)
        self.dar_fraction_widget.show()

        # add custom pixel aspect ratio widget
        self.par_fraction_widget = FractionWidget()
        self.video_properties_table.attach(self.par_fraction_widget,
            1, 2, 6, 7, xoptions=gtk.EXPAND | gtk.FILL, yoptions=0)
        self.par_fraction_widget.show()

        # add custom framerate widget
        self.frame_rate_fraction_widget = FractionWidget()
        self.video_properties_table.attach(self.frame_rate_fraction_widget,
            1, 2, 2, 3, xoptions=gtk.EXPAND | gtk.FILL, yoptions=0)
        self.frame_rate_fraction_widget.show()

        # populate coboboxes with appropriate data
        self.frame_rate_combo.set_model(frame_rates)
        self.dar_combo.set_model(display_aspect_ratios)
        self.par_combo.set_model(pixel_aspect_ratios)

        self.channels_combo.set_model(audio_channels)
        self.sample_rate_combo.set_model(audio_rates)
        self.sample_depth_combo.set_model(audio_depths)

        # behavior
        self.wg = RippleUpdateGroup()
        self.wg.addVertex(self.frame_rate_combo,
                signal="changed",
                update_func=self._updateCombo,
                update_func_args=(self.frame_rate_fraction_widget,))
        self.wg.addVertex(self.frame_rate_fraction_widget,
                signal="value-changed",
                update_func=self._updateFraction,
                update_func_args=(self.frame_rate_combo,))
        self.wg.addVertex(self.dar_combo, signal="changed")
        self.wg.addVertex(self.dar_fraction_widget, signal="value-changed")
        self.wg.addVertex(self.par_combo, signal="changed")
        self.wg.addVertex(self.par_fraction_widget, signal="value-changed")
        self.wg.addVertex(self.width_spinbutton, signal="value-changed")
        self.wg.addVertex(self.height_spinbutton, signal="value-changed")
        self.wg.addVertex(self.save_audio_preset_button,
                 update_func=self._updateAudioSaveButton)
        self.wg.addVertex(self.save_video_preset_button,
                 update_func=self._updateVideoSaveButton)
        self.wg.addVertex(self.channels_combo, signal="changed")
        self.wg.addVertex(self.sample_rate_combo, signal="changed")
        self.wg.addVertex(self.sample_depth_combo, signal="changed")

        # constrain width and height IFF constrain_sar_button is active
        self.wg.addEdge(self.width_spinbutton, self.height_spinbutton,
            predicate=self.constrained, edge_func=self.updateHeight)
        self.wg.addEdge(self.height_spinbutton, self.width_spinbutton,
            predicate=self.constrained, edge_func=self.updateWidth)

        # keep framereate text field and combo in sync
        self.wg.addBiEdge(self.frame_rate_combo,
           self.frame_rate_fraction_widget)

        # keep dar text field and combo in sync
        self.wg.addEdge(self.dar_combo, self.dar_fraction_widget,
            edge_func=self.updateDarFromCombo)
        self.wg.addEdge(self.dar_fraction_widget, self.dar_combo,
            edge_func=self.updateDarFromFractionWidget)

        # keep par text field and combo in sync
        self.wg.addEdge(self.par_combo, self.par_fraction_widget,
            edge_func=self.updateParFromCombo)
        self.wg.addEdge(self.par_fraction_widget, self.par_combo,
            edge_func=self.updateParFromFractionWidget)

        # constrain DAR and PAR values. because the combo boxes are already
        # linked, we only have to link the fraction widgets together.
        self.wg.addEdge(self.par_fraction_widget, self.dar_fraction_widget,
            edge_func=self.updateDarFromPar)
        self.wg.addEdge(self.dar_fraction_widget, self.par_fraction_widget,
            edge_func=self.updateParFromDar)

        # update PAR when width/height change and the DAR checkbutton is
        # selected
        self.wg.addEdge(self.width_spinbutton, self.par_fraction_widget,
            predicate=self.darSelected, edge_func=self.updateParFromDar)
        self.wg.addEdge(self.height_spinbutton, self.par_fraction_widget,
            predicate=self.darSelected, edge_func=self.updateParFromDar)

        # update DAR when width/height change and the PAR checkbutton is
        # selected
        self.wg.addEdge(self.width_spinbutton, self.dar_fraction_widget,
            predicate=self.parSelected, edge_func=self.updateDarFromPar)
        self.wg.addEdge(self.height_spinbutton, self.dar_fraction_widget,
            predicate=self.parSelected, edge_func=self.updateDarFromPar)

        # presets
        self.audio_presets = AudioPresetManager()
        self.audio_presets.loadAll()
        self.video_presets = VideoPresetManager()
        self.video_presets.loadAll()

        self._fillPresetsTreeview(
                self.audio_preset_treeview, self.audio_presets,
                self._updateAudioPresetButtons)
        self._fillPresetsTreeview(
                self.video_preset_treeview, self.video_presets,
                self._updateVideoPresetButtons)

        # A map which tells which infobar should be used when displaying
        # an error for a preset manager.
        self._infobarForPresetManager = {
                self.audio_presets: self.audio_preset_infobar,
                self.video_presets: self.video_preset_infobar}

        # Bind the widgets in the Video tab to the Video Presets Manager.
        self.bindSpinbutton(self.video_presets, "width", self.width_spinbutton)
        self.bindSpinbutton(self.video_presets, "height",
            self.height_spinbutton)
        self.bindFractionWidget(self.video_presets, "frame-rate",
            self.frame_rate_fraction_widget)
        self.bindPar(self.video_presets)

        # Bind the widgets in the Audio tab to the Audio Presets Manager.
        self.bindCombo(self.audio_presets, "channels",
            self.channels_combo)
        self.bindCombo(self.audio_presets, "sample-rate",
            self.sample_rate_combo)
        self.bindCombo(self.audio_presets, "depth",
            self.sample_depth_combo)

        self.wg.addEdge(self.par_fraction_widget,
            self.save_video_preset_button)
        self.wg.addEdge(self.frame_rate_fraction_widget,
            self.save_video_preset_button)
        self.wg.addEdge(self.width_spinbutton,
            self.save_video_preset_button)
        self.wg.addEdge(self.height_spinbutton,
            self.save_video_preset_button)

        self.wg.addEdge(self.channels_combo,
            self.save_audio_preset_button)
        self.wg.addEdge(self.sample_rate_combo,
            self.save_audio_preset_button)
        self.wg.addEdge(self.sample_depth_combo,
            self.save_audio_preset_button)

        self.updateUI()

        self.createAudioNoPreset(self.audio_presets)
        self.createVideoNoPreset(self.video_presets)

    def bindPar(self, mgr):

        def updatePar(value):
            # activate par so we can set the value
            self.select_par_radiobutton.props.active = True
            self.par_fraction_widget.setWidgetValue(value)

        mgr.bindWidget("par", updatePar,
            self.par_fraction_widget.getWidgetValue)

    def bindFractionWidget(self, mgr, name, widget):
        mgr.bindWidget(name, widget.setWidgetValue,
            widget.getWidgetValue)

    def bindCombo(self, mgr, name, widget):
        mgr.bindWidget(name,
            lambda x: set_combo_value(widget, x),
            lambda: get_combo_value(widget))

    def bindSpinbutton(self, mgr, name, widget):
        mgr.bindWidget(name,
            lambda x: widget.set_value(float(x)),
            lambda: int(widget.get_value()))

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
        renderer.connect("editing-started", self._presetNameEditingStartedCb,
            mgr)
        treeview.get_selection().connect("changed", self._presetChangedCb,
            mgr, update_buttons_func)
        treeview.connect("focus-out-event", self._treeviewDefocusedCb, mgr)

    def createAudioNoPreset(self, mgr):
        mgr.prependPreset(_("No preset"), {
            "depth": int(get_combo_value(self.sample_depth_combo)),
            "channels": int(get_combo_value(self.channels_combo)),
            "sample-rate": int(get_combo_value(self.sample_rate_combo))})

    def createVideoNoPreset(self, mgr):
        mgr.prependPreset(_("No preset"), {
            "par": gst.Fraction(int(get_combo_value(self.par_combo).num),
                                    int(get_combo_value(self.par_combo).denom)),
            "frame-rate": gst.Fraction(int(get_combo_value(self.frame_rate_combo).num),
                            int(get_combo_value(self.frame_rate_combo).denom)),
            "height": int(self.height_spinbutton.get_value()),
            "width": int(self.width_spinbutton.get_value())})

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

    def _presetNameEditingStartedCb(self, renderer, editable, path, mgr):
        """Handle the start of a preset renaming."""
        self._hidePresetManagerError(mgr)

    def _presetChangedCb(self, selection, mgr, update_preset_buttons_func):
        """Handle the selection of a preset."""
        model, iter_ = selection.get_selected()
        if iter_:
            preset = model[iter_][0]
        else:
            preset = None
        mgr.restorePreset(preset)
        update_preset_buttons_func()
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

    def constrained(self):
        return self.constrain_sar_button.props.active

    def _updateFraction(self, unused, fraction, combo):
        fraction.setWidgetValue(get_combo_value(combo))

    def _updateCombo(self, unused, combo, fraction):
        set_combo_value(combo, fraction.getWidgetValue())

    def getSAR(self):
        width = int(self.width_spinbutton.get_value())
        height = int(self.height_spinbutton.get_value())
        return gst.Fraction(width, height)

    def _setProperties(self):
        self.window = self.builder.get_object("project-settings-dialog")
        self.video_properties_table = self.builder.get_object(
            "video_properties_table")
        self.video_properties_table = self.builder.get_object(
            "video_properties_table")
        self.frame_rate_combo = self.builder.get_object("frame_rate_combo")
        self.dar_combo = self.builder.get_object("dar_combo")
        self.par_combo = self.builder.get_object("par_combo")
        self.channels_combo = self.builder.get_object("channels_combo")
        self.sample_rate_combo = self.builder.get_object("sample_rate_combo")
        self.sample_depth_combo = self.builder.get_object("sample_depth_combo")
        self.year_spinbutton = self.builder.get_object("year_spinbutton")
        self.author_entry = self.builder.get_object("author_entry")
        self.width_spinbutton = self.builder.get_object("width_spinbutton")
        self.height_spinbutton = self.builder.get_object("height_spinbutton")
        self.save_audio_preset_button = self.builder.get_object(
            "save_audio_preset_button")
        self.save_video_preset_button = self.builder.get_object(
            "save_video_preset_button")
        self.audio_preset_treeview = self.builder.get_object(
            "audio_preset_treeview")
        self.video_preset_treeview = self.builder.get_object(
            "video_preset_treeview")
        self.select_par_radiobutton = self.builder.get_object(
            "select_par_radiobutton")
        self.remove_audio_preset_button = self.builder.get_object(
            "remove_audio_preset_button")
        self.remove_video_preset_button = self.builder.get_object(
            "remove_video_preset_button")
        self.constrain_sar_button = self.builder.get_object(
            "constrain_sar_button")
        self.select_dar_radiobutton = self.builder.get_object(
            "select_dar_radiobutton")
        self.video_preset_infobar = self.builder.get_object(
            "video-preset-infobar")
        self.audio_preset_infobar = self.builder.get_object(
            "audio-preset-infobar")
        self.title_entry = self.builder.get_object("title_entry")
        self.author_entry = self.builder.get_object("author_entry")
        self.year_spinbutton = self.builder.get_object("year_spinbutton")

    def _constrainSarButtonToggledCb(self, button):
        if button.props.active:
            self.sar = self.getSAR()

    def _selectDarRadiobuttonToggledCb(self, button):
        state = button.props.active
        self.dar_fraction_widget.set_sensitive(state)
        self.dar_combo.set_sensitive(state)
        self.par_fraction_widget.set_sensitive(not state)
        self.par_combo.set_sensitive(not state)

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

    def _addAudioPresetButtonClickedCb(self, button):
        preset_name = self._getUniquePresetName(self.audio_presets)
        self.audio_presets.addPreset(preset_name, {
            "channels": get_combo_value(self.channels_combo),
            "sample-rate": get_combo_value(self.sample_rate_combo),
            "depth": get_combo_value(self.sample_depth_combo)
        })
        self.audio_presets.restorePreset(preset_name)
        self._updateAudioPresetButtons()

    def _removeAudioPresetButtonClickedCb(self, button):
        selection = self.audio_preset_treeview.get_selection()
        model, iter_ = selection.get_selected()
        if iter_:
            self.audio_presets.removePreset(model[iter_][0])

    def _saveAudioPresetButtonClickedCb(self, button):
        self.audio_presets.savePreset()
        self.save_audio_preset_button.set_sensitive(False)

    def _addVideoPresetButtonClickedCb(self, button):
        preset_name = self._getUniquePresetName(self.video_presets)
        self.video_presets.addPreset(preset_name, {
            "width": int(self.width_spinbutton.get_value()),
            "height": int(self.height_spinbutton.get_value()),
            "frame-rate": self.frame_rate_fraction_widget.getWidgetValue(),
            "par": self.par_fraction_widget.getWidgetValue(),
        })
        self.video_presets.restorePreset(preset_name)
        self._updateVideoPresetButtons()

    def _removeVideoPresetButtonClickedCb(self, button):
        selection = self.video_preset_treeview.get_selection()
        model, iter_ = selection.get_selected()
        if iter_:
            self.video_presets.removePreset(model[iter_][0])

    def _saveVideoPresetButtonClickedCb(self, button):
        self.video_presets.savePreset()
        self.save_video_preset_button.set_sensitive(False)

    def _updateAudioPresetButtons(self):
        preset_changed = self.audio_presets.isCurrentPresetChanged()
        self.save_audio_preset_button.set_sensitive(preset_changed)
        preset_selected = bool(self.audio_presets.cur_preset)
        self.remove_audio_preset_button.set_sensitive(preset_selected)

    def _updateVideoPresetButtons(self):
        preset_changed = self.video_presets.isCurrentPresetChanged()
        self.save_video_preset_button.set_sensitive(preset_changed)
        preset_selected = bool(self.video_presets.cur_preset)
        self.remove_video_preset_button.set_sensitive(preset_selected)

    def _updateAudioSaveButton(self, unused_in, button):
        button.set_sensitive(self.audio_presets.isCurrentPresetChanged())

    def _updateVideoSaveButton(self, unused_in, button):
        button.set_sensitive(self.video_presets.isCurrentPresetChanged())

    def darSelected(self):
        return self.select_dar_radiobutton.props.active

    def parSelected(self):
        return not self.darSelected()

    def updateWidth(self):
        height = int(self.height_spinbutton.get_value())
        self.width_spinbutton.set_value(height * self.sar)

    def updateHeight(self):
        width = int(self.width_spinbutton.get_value())
        self.height_spinbutton.set_value(width * (1 / self.sar))

    def updateDarFromPar(self):
        par = self.par_fraction_widget.getWidgetValue()
        sar = self.getSAR()
        self.dar_fraction_widget.setWidgetValue(sar * par)

    def updateParFromDar(self):
        dar = self.dar_fraction_widget.getWidgetValue()
        sar = self.getSAR()
        self.par_fraction_widget.setWidgetValue(dar * (1 / sar))

    def updateDarFromCombo(self):
        self.dar_fraction_widget.setWidgetValue(get_combo_value(
            self.dar_combo))

    def updateDarFromFractionWidget(self):
        set_combo_value(self.dar_combo,
            self.dar_fraction_widget.getWidgetValue())

    def updateParFromCombo(self):
        self.par_fraction_widget.setWidgetValue(get_combo_value(
            self.par_combo))

    def updateParFromFractionWidget(self):
        set_combo_value(self.par_combo,
            self.par_fraction_widget.getWidgetValue())

    def updateUI(self):

        self.width_spinbutton.set_value(self.settings.videowidth)
        self.height_spinbutton.set_value(self.settings.videoheight)

        # video
        self.frame_rate_fraction_widget.setWidgetValue(self.settings.videorate)
        self.par_fraction_widget.setWidgetValue(self.settings.videopar)

        # audio
        set_combo_value(self.channels_combo, self.settings.audiochannels)
        set_combo_value(self.sample_rate_combo, self.settings.audiorate)
        set_combo_value(self.sample_depth_combo, self.settings.audiodepth)

        self._selectDarRadiobuttonToggledCb(self.select_dar_radiobutton)

        # metadata
        self.title_entry.set_text(self.project.name)
        self.author_entry.set_text(self.project.author)
        if self.project.year:
            year = int(self.project.year)
        else:
            year = datetime.now().year
        self.year_spinbutton.get_adjustment().set_value(year)

    def updateMetadata(self):
        self.project.name = self.title_entry.get_text()
        self.project.author = self.author_entry.get_text()
        self.project.year = str(self.year_spinbutton.get_value_as_int())

    def updateSettings(self):
        width = int(self.width_spinbutton.get_value())
        height = int(self.height_spinbutton.get_value())
        par = self.par_fraction_widget.getWidgetValue()
        frame_rate = self.frame_rate_fraction_widget.getWidgetValue()

        channels = get_combo_value(self.channels_combo)
        sample_rate = get_combo_value(self.sample_rate_combo)
        sample_depth = get_combo_value(self.sample_depth_combo)

        self.settings.setVideoProperties(width, height, frame_rate, par)
        self.settings.setAudioProperties(channels, sample_rate, sample_depth)

        self.project.setSettings(self.settings)

    def _responseCb(self, unused_widget, response):
        if response == gtk.RESPONSE_OK:
            self.updateSettings()
            self.updateMetadata()
        self.window.destroy()
