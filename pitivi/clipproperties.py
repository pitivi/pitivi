# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (C) 2010 Thibault Saunier <tsaunier@gnome.org>
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
"""Widgets to control clips properties."""
import os
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import Pango

from pitivi.configure import get_ui_dir
from pitivi.effects import AUDIO_EFFECT
from pitivi.effects import EffectsPropertiesManager
from pitivi.effects import HIDDEN_EFFECTS
from pitivi.effects import VIDEO_EFFECT
from pitivi.undo.timeline import CommitTimelineFinalizingAction
from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import disable_scroll
from pitivi.utils.ui import EFFECT_TARGET_ENTRY
from pitivi.utils.ui import fix_infobar
from pitivi.utils.ui import PADDING
from pitivi.utils.ui import SPACING

(COL_ACTIVATED,
 COL_TYPE,
 COL_BIN_DESCRIPTION_TEXT,
 COL_NAME_TEXT,
 COL_DESC_TEXT,
 COL_TRACK_EFFECT) = list(range(6))


class ClipPropertiesError(Exception):
    pass


class ClipProperties(Gtk.ScrolledWindow, Loggable):
    """Widget for configuring the selected clip.

    Attributes:
        app (Pitivi): The app.
    """

    def __init__(self, app):
        Gtk.ScrolledWindow.__init__(self)
        Loggable.__init__(self)
        self.app = app

        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        viewport = Gtk.Viewport()
        viewport.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        viewport.show()
        self.add(viewport)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.show()
        viewport.add(vbox)

        self.infobar_box = Gtk.Box()
        self.infobar_box.set_orientation(Gtk.Orientation.VERTICAL)
        self.infobar_box.show()
        vbox.pack_start(self.infobar_box, False, False, 0)

        transformation_expander = TransformationProperties(app)
        transformation_expander.set_vexpand(False)
        vbox.pack_start(transformation_expander, False, False, 0)

        self.effect_expander = EffectProperties(app, self)
        self.effect_expander.set_vexpand(False)
        vbox.pack_start(self.effect_expander, False, False, 0)

    def createInfoBar(self, text):
        """Creates an infobar to be displayed at the top."""
        label = Gtk.Label(label=text)
        label.set_line_wrap(True)
        infobar = Gtk.InfoBar()
        fix_infobar(infobar)
        infobar.props.message_type = Gtk.MessageType.OTHER
        infobar.get_content_area().add(label)
        self.infobar_box.pack_start(infobar, False, False, 0)
        return infobar


# pylint: disable=too-many-instance-attributes
class EffectProperties(Gtk.Expander, Loggable):
    """Widget for viewing a list of effects and configuring them.

    Attributes:
        app (Pitivi): The app.
    """

    # pylint: disable=too-many-statements
    def __init__(self, app, clip_properties):
        Gtk.Expander.__init__(self)
        self.set_expanded(True)
        self.set_label(_("Effects"))
        Loggable.__init__(self)

        # Global variables related to effects
        self.app = app

        self._project = None
        self._selection = None
        self.selected_effects = []
        self.clips = []
        self._effect_config_ui = None
        self.effects_properties_manager = EffectsPropertiesManager(app)
        self.clip_properties = clip_properties

        # The toolbar that will go between the list of effects and properties
        buttons_box = Gtk.ButtonBox()
        buttons_box.set_halign(Gtk.Align.END)
        buttons_box.set_margin_end(SPACING)
        buttons_box.props.margin_top = SPACING / 2

        remove_effect_button = Gtk.Button()
        remove_icon = Gtk.Image.new_from_icon_name("list-remove-symbolic",
                                                   Gtk.IconSize.BUTTON)
        remove_effect_button.set_image(remove_icon)
        remove_effect_button.set_always_show_image(True)
        remove_effect_button.set_label(_("Remove effect"))
        buttons_box.pack_start(remove_effect_button,
                               expand=False, fill=False, padding=0)

        # We need to specify Gtk.TreeDragSource because otherwise we are hitting
        # bug https://bugzilla.gnome.org/show_bug.cgi?id=730740.
        class EffectsListStore(Gtk.ListStore, Gtk.TreeDragSource):
            """Just a work around!"""
            # pylint: disable=non-parent-init-called
            def __init__(self, *args):
                Gtk.ListStore.__init__(self, *args)
                # Set the source index on the storemodel directly,
                # to avoid issues with the selection_data API.
                # FIXME: Work around
                # https://bugzilla.gnome.org/show_bug.cgi?id=737587
                self.source_index = None

            def do_drag_data_get(self, path, unused_selection_data):
                self.source_index = path.get_indices()[0]

        self.storemodel = EffectsListStore(bool, str, str, str, str, object)
        self.treeview = Gtk.TreeView(model=self.storemodel)
        self.treeview.set_property("has_tooltip", True)
        self.treeview.set_headers_visible(False)
        self.treeview.props.margin_top = SPACING
        self.treeview.props.margin_left = SPACING
        # Without this, the treeview hides the border of its parent.
        # I should file a bug about this.
        self.treeview.props.margin_right = 1

        activated_cell = Gtk.CellRendererToggle()
        activated_cell.props.xalign = 0
        activated_cell.props.xpad = 0
        activated_cell.connect("toggled", self._effectActiveToggleCb)
        self.treeview.insert_column_with_attributes(-1,
                                                    _("Active"), activated_cell,
                                                    active=COL_ACTIVATED)

        type_col = Gtk.TreeViewColumn(_("Type"))
        type_col.set_spacing(SPACING)
        type_col.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        type_cell = Gtk.CellRendererText()
        type_cell.props.xpad = PADDING
        type_col.pack_start(type_cell, expand=True)
        type_col.add_attribute(type_cell, "text", COL_TYPE)
        self.treeview.append_column(type_col)

        name_col = Gtk.TreeViewColumn(_("Effect name"))
        name_col.set_spacing(SPACING)
        name_cell = Gtk.CellRendererText()
        name_cell.props.xpad = PADDING
        name_cell.set_property("ellipsize", Pango.EllipsizeMode.END)
        name_col.pack_start(name_cell, expand=True)
        name_col.add_attribute(name_cell, "text", COL_NAME_TEXT)
        self.treeview.append_column(name_col)

        # Allow the treeview to accept EFFECT_TARGET_ENTRY when drag&dropping.
        self.treeview.enable_model_drag_dest([EFFECT_TARGET_ENTRY],
                                             Gdk.DragAction.COPY)

        # Enable reordering by drag&drop.
        self.treeview.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK,
                                               [EFFECT_TARGET_ENTRY],
                                               Gdk.DragAction.MOVE)

        self.treeview_selection = self.treeview.get_selection()
        self.treeview_selection.set_mode(Gtk.SelectionMode.SINGLE)

        self._infobar = clip_properties.createInfoBar(
            _("Select a clip on the timeline to configure its associated effects"))
        self._infobar.show_all()

        # Prepare the main container widgets and lay out everything
        self._vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._vbox.pack_start(self.treeview, expand=False, fill=False, padding=0)
        self._vbox.pack_start(buttons_box, expand=False, fill=False, padding=0)
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(SPACING)
        separator.set_margin_left(SPACING)
        separator.set_margin_right(SPACING)
        self._vbox.pack_start(separator, expand=False, fill=False, padding=0)
        self._vbox.show_all()
        self.add(self._vbox)
        self.hide()

        effects_actions_group = Gio.SimpleActionGroup()
        self.treeview.insert_action_group("clipproperties-effects", effects_actions_group)
        buttons_box.insert_action_group("clipproperties-effects", effects_actions_group)
        self.app.shortcuts.register_group("clipproperties-effects", _("Clip Effects"))

        self.remove_effect_action = Gio.SimpleAction.new("remove-effect", None)
        self.remove_effect_action.connect("activate", self._removeEffectCb)
        effects_actions_group.add_action(self.remove_effect_action)
        self.app.shortcuts.add("clipproperties-effects.remove-effect", ["Delete"],
                               _("Remove the selected effect"))
        self.remove_effect_action.set_enabled(False)
        remove_effect_button.set_action_name("clipproperties-effects.remove-effect")

        # Connect all the widget signals
        self.treeview_selection.connect("changed", self._treeviewSelectionChangedCb)
        self.treeview.connect("drag-motion", self._dragMotionCb)
        self.treeview.connect("drag-leave", self._dragLeaveCb)
        self.treeview.connect("drag-data-received", self._dragDataReceivedCb)
        self.treeview.connect("query-tooltip", self._treeViewQueryTooltipCb)
        self.app.project_manager.connect_after(
            "new-project-loaded", self._newProjectLoadedCb)
        self.connect('notify::expanded', self._expandedCb)

    def _newProjectLoadedCb(self, unused_app, project):
        if self._selection is not None:
            self._selection.disconnect_by_func(self._selectionChangedCb)
            self._selection = None
        self._project = project
        if project:
            self._selection = project.ges_timeline.ui.selection
            self._selection.connect('selection-changed', self._selectionChangedCb)
            self.selected_effects = self._selection.getSelectedEffects()
        self.__updateAll()

    def _selectionChangedCb(self, selection):
        for clip in self.clips:
            clip.disconnect_by_func(self._trackElementAddedCb)
            clip.disconnect_by_func(self._trackElementRemovedCb)

        self.selected_effects = selection.getSelectedEffects()

        if selection:
            self.clips = list(selection.selected)
            for clip in self.clips:
                clip.connect("child-added", self._trackElementAddedCb)
                clip.connect("child-removed", self._trackElementRemovedCb)
            self.show()
        else:
            self.clips = []
            self.hide()
        self.__updateAll()

    def _trackElementAddedCb(self, unused_clip, track_element):
        if isinstance(track_element, GES.BaseEffect):
            selec = self._selection.getSelectedEffects()
            self.selected_effects = selec
            self.__updateAll()
            for path, row in enumerate(self.storemodel):
                if row[COL_TRACK_EFFECT] == track_element:
                    self.treeview_selection.select_path(path)
                    break

    def _trackElementRemovedCb(self, unused_clip, track_element):
        if isinstance(track_element, GES.BaseEffect):
            selec = self._selection.getSelectedEffects()
            self.selected_effects = selec
            self.__updateAll()

    def _removeEffectCb(self, unused_action, unused_param):
        selected = self.treeview_selection.get_selected()
        if not selected[1]:
            # Cannot remove nothing,
            return
        effect = self.storemodel.get_value(selected[1], COL_TRACK_EFFECT)
        self._removeEffect(effect)

    def _removeEffect(self, effect):
        pipeline = self._project.ges_timeline.get_parent()
        with self.app.action_log.started("remove effect", CommitTimelineFinalizingAction(pipeline)):
            self.__remove_configuration_widget()
            self.effects_properties_manager.cleanCache(effect)
            effect.get_parent().remove(effect)
            pipeline.commit_timeline()
        self._updateTreeview()

    def addEffectToClip(self, clip, factory_name, priority=None):
        """Adds the specified effect if it can be applied to the clip."""

        model = self.treeview.get_model()
        media_type = self.app.effects.getInfo(factory_name).media_type
        for track_element in clip.get_children(False):
            track_type = track_element.get_track_type()
            if track_type == GES.TrackType.AUDIO and media_type == AUDIO_EFFECT or \
                    track_type == GES.TrackType.VIDEO and media_type == VIDEO_EFFECT:
                # Actually add the effect
                pipeline = self._project.ges_timeline.get_parent()
                with self.app.action_log.started("add effect",
                                                 CommitTimelineFinalizingAction(pipeline)):
                    effect = GES.Effect.new(bin_description=factory_name)
                    clip.add(effect)
                    if priority is not None and priority < len(model):
                        clip.set_top_effect_priority(effect, priority)
                pipeline.commit_timeline()
                break

    def addEffectToCurrentSelection(self, factory_name):
        """Adds an effect to the current selection.

        Args:
            factory_name (str): The name of the GstElementFactory for creating
                the effect.
        """
        if not self.clips or len(self.clips) > 1:
            return
        clip = self.clips[0]
        # Checking that this effect can be applied on this track object
        # Which means, it has the corresponding media_type
        self.addEffectToClip(clip, factory_name)

    # pylint: disable=too-many-arguments
    def _dragMotionCb(self, unused_tree_view, unused_drag_context, unused_x, unused_y, unused_timestamp):
        self.debug(
            "Something is being dragged in the clip properties' effects list")
        self.drag_highlight()

    def _dragLeaveCb(self, unused_tree_view, unused_drag_context, unused_timestamp):
        self.info(
            "The item being dragged has left the clip properties' effects list")
        self.drag_unhighlight()

    # pylint: disable=too-many-arguments
    def _dragDataReceivedCb(self, treeview, drag_context, x, y, selection_data, unused_info, timestamp):
        if not self.clips or len(self.clips) > 1:
            # Indicate that a drop will not be accepted.
            Gdk.drag_status(drag_context, 0, timestamp)
            return
        clip = self.clips[0]
        dest_row = treeview.get_dest_row_at_pos(x, y)
        if drag_context.get_suggested_action() == Gdk.DragAction.COPY:
            # An effect dragged probably from the effects list.
            factory_name = str(selection_data.get_data(), "UTF-8")
            drop_index = self.__get_new_effect_index(dest_row)
            self.addEffectToClip(clip, factory_name, drop_index)
        elif drag_context.get_suggested_action() == Gdk.DragAction.MOVE:
            # An effect dragged from the same treeview to change its position.
            # Source
            source_index, drop_index = self.__get_move_indexes(
                dest_row, treeview.get_model())
            self.__move_effect(clip, source_index, drop_index)

        drag_context.finish(True, False, timestamp)

    # pylint: disable=no-self-use
    def __get_new_effect_index(self, dest_row):
        # Target
        if dest_row:
            drop_path, drop_pos = dest_row
            drop_index = drop_path.get_indices()[0]
            if drop_pos != Gtk.TreeViewDropPosition.BEFORE:
                drop_index += 1
        else:
            # This should happen when dragging after the last row.
            drop_index = None

        return drop_index

    def __get_move_indexes(self, dest_row, model):
        source_index = self.storemodel.source_index
        self.storemodel.source_index = None

        # Target
        if dest_row:
            drop_path, drop_pos = dest_row
            drop_index = drop_path.get_indices()[0]
            drop_index = self.calculateEffectPriority(
                source_index, drop_index, drop_pos)
        else:
            # This should happen when dragging after the last row.
            drop_index = len(model) - 1
            drop_pos = Gtk.TreeViewDropPosition.INTO_OR_BEFORE

        return source_index, drop_index

    def __move_effect(self, clip, source_index, drop_index):
        if source_index == drop_index:
            # Noop.
            return
        # The paths are different.
        effects = clip.get_top_effects()
        effect = effects[source_index]
        pipeline = self._project.ges_timeline.get_parent()
        with self.app.action_log.started("move effect",
                                         CommitTimelineFinalizingAction(pipeline)):
            clip.set_top_effect_priority(effect, drop_index)

        pipeline.commit_timeline()
        new_path = Gtk.TreePath.new()
        new_path.append_index(drop_index)
        self.__updateAll(path=new_path)

    @staticmethod
    def calculateEffectPriority(source_index, drop_index, drop_pos):
        """Calculates where the effect from source_index will end up."""
        if drop_pos in (Gtk.TreeViewDropPosition.INTO_OR_BEFORE, Gtk.TreeViewDropPosition.INTO_OR_AFTER):
            return drop_index
        if drop_pos == Gtk.TreeViewDropPosition.BEFORE:
            if source_index < drop_index:
                return drop_index - 1
        elif drop_pos == Gtk.TreeViewDropPosition.AFTER:
            if source_index > drop_index:
                return drop_index + 1
        return drop_index

    def _effectActiveToggleCb(self, cellrenderertoggle, path):
        _iter = self.storemodel.get_iter(path)
        tck_effect = self.storemodel.get_value(_iter, COL_TRACK_EFFECT)
        with self.app.action_log.started("change active state"):
            tck_effect.set_active(not tck_effect.is_active())
            cellrenderertoggle.set_active(tck_effect.is_active())
            self._updateTreeview()
            self._project.ges_timeline.commit()

    def _expandedCb(self, unused_expander, unused_params):
        self.__updateAll()

    def _treeViewQueryTooltipCb(self, view, x, y, keyboard_mode, tooltip):
        is_row, x, y, unused_model, path, tree_iter = view.get_tooltip_context(
            x, y, keyboard_mode)
        if not is_row:
            return False

        view.set_tooltip_row(tooltip, path)
        description = self.storemodel.get_value(tree_iter, COL_DESC_TEXT)
        bin_description = self.storemodel.get_value(
            tree_iter, COL_BIN_DESCRIPTION_TEXT)
        tooltip.set_text("%s\n%s" % (bin_description, description))
        return True

    def __updateAll(self, path=None):
        if len(self.clips) == 1:
            self.show()
            self._infobar.hide()
            self._updateTreeview()
            if path:
                self.treeview_selection.select_path(path)
        else:
            self.hide()
            self.__remove_configuration_widget()
            self.storemodel.clear()
            self._infobar.show()

    def _updateTreeview(self):
        self.storemodel.clear()
        clip = self.clips[0]
        for effect in clip.get_top_effects():
            if effect.props.bin_description in HIDDEN_EFFECTS:
                continue
            effect_info = self.app.effects.getInfo(effect.props.bin_description)
            to_append = [effect.props.active]
            track_type = effect.get_track_type()
            if track_type == GES.TrackType.AUDIO:
                to_append.append("Audio")
            elif track_type == GES.TrackType.VIDEO:
                to_append.append("Video")
            to_append.append(effect.props.bin_description)
            to_append.append(effect_info.human_name)
            to_append.append(effect_info.description)
            to_append.append(effect)
            self.storemodel.append(to_append)
        self._vbox.set_visible(len(self.storemodel) > 0)

    def _treeviewSelectionChangedCb(self, unused_treeview):
        selection_is_emtpy = self.treeview_selection.count_selected_rows() == 0
        self.remove_effect_action.set_enabled(not selection_is_emtpy)

        self._updateEffectConfigUi()

    def _updateEffectConfigUi(self):
        model, tree_iter = self.treeview_selection.get_selected()
        if tree_iter:
            effect = model.get_value(tree_iter, COL_TRACK_EFFECT)
            self._showEffectConfigurationWidget(effect)
        else:
            self.__remove_configuration_widget()

    def __remove_configuration_widget(self):
        if not self._effect_config_ui:
            # Nothing to remove.
            return

        self._effect_config_ui.deactivate_keyframe_toggle_buttons()
        self._vbox.remove(self._effect_config_ui)
        self._effect_config_ui = None

    def _showEffectConfigurationWidget(self, effect):
        self.__remove_configuration_widget()
        self._effect_config_ui = self.effects_properties_manager.getEffectConfigurationUI(
            effect)
        if not self._effect_config_ui:
            return
        self._effect_config_ui.show()
        self._effect_config_ui.show_all()
        self._vbox.add(self._effect_config_ui)


class TransformationProperties(Gtk.Expander, Loggable):
    """Widget for configuring the placement and size of the clip."""

    __signals__ = {
        'selection-changed': []}

    def __init__(self, app):
        Gtk.Expander.__init__(self)
        Loggable.__init__(self)
        self.app = app
        self._project = None
        self._selection = None
        self.source = None
        self._selected_clip = None
        self.spin_buttons = {}
        self.default_values = {}
        self.set_label(_("Transformation"))

        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(get_ui_dir(),
                                                "cliptransformation.ui"))

        self.add(self.builder.get_object("transform_box"))
        self.show_all()
        self._initButtons()
        self.hide()

        self.app.project_manager.connect_after(
            "new-project-loaded", self._newProjectLoadedCb)

    def _newProjectLoadedCb(self, unused_app, project):
        if self._selection is not None:
            self._selection.disconnect_by_func(self._selectionChangedCb)
            self._selection = None
        self._project = project
        if project:
            self._selection = project.ges_timeline.ui.selection
            self._selection.connect('selection-changed', self._selectionChangedCb)

    def _initButtons(self):
        clear_button = self.builder.get_object("clear_button")
        clear_button.connect("clicked", self._defaultValuesCb)

        self.__setupSpinButton("xpos_spinbtn", "posx")
        self.__setupSpinButton("ypos_spinbtn", "posy")

        self.__setupSpinButton("width_spinbtn", "width")
        self.__setupSpinButton("height_spinbtn", "height")

    def _defaultValuesCb(self, unused_widget):
        for name, spinbtn in list(self.spin_buttons.items()):
            spinbtn.set_value(self.default_values[name])

    def __sourcePropertyChangedCb(self, unused_source, unused_element, param):
        try:
            spin = self.spin_buttons[param.name]
        except KeyError:
            return

        res, value = self.source.get_child_property(param.name)
        assert res
        if spin.get_value() != value:
            spin.set_value(value)

    def _updateSpinButtons(self):
        for name, spinbtn in list(self.spin_buttons.items()):
            res, value = self.source.get_child_property(name)
            assert res
            if name == "width":
                self.default_values[name] = self._project.videowidth
            elif name == "height":
                self.default_values[name] = self._project.videoheight
            else:
                self.default_values[name] = 0
            spinbtn.set_value(value)

    def __setupSpinButton(self, widget_name, property_name):
        """Creates a SpinButton for editing a property value."""
        spinbtn = self.builder.get_object(widget_name)
        spinbtn.connect("output", self._onValueChangedCb, property_name)
        disable_scroll(spinbtn)
        self.spin_buttons[property_name] = spinbtn

    def _onValueChangedCb(self, spinbtn, prop):
        if not self.source:
            return

        value = spinbtn.get_value()

        res, cvalue = self.source.get_child_property(prop)
        assert res
        if value != cvalue:
            with self.app.action_log.started("Transformation property change"):
                self.source.set_child_property(prop, value)
            self._project.pipeline.commit_timeline()
            self.app.gui.viewer.overlay_stack.update(self.source)

    def __setSource(self, source):
        if self.source:
            try:
                self.source.disconnect_by_func(self.__sourcePropertyChangedCb)
            except TypeError:
                pass
        self.source = source
        if self.source:
            self._updateSpinButtons()
            self.source.connect("deep-notify", self.__sourcePropertyChangedCb)

    def _selectionChangedCb(self, unused_timeline):
        if len(self._selection) == 1:
            clip = list(self._selection)[0]
            source = clip.find_track_element(None, GES.VideoSource)
            if source:
                self._selected_clip = clip
                self.__setSource(source)
                self.app.gui.viewer.overlay_stack.select(source)
                self.show()
                return

        # Deselect
        if self._selected_clip:
            self._selected_clip = None
            self._project.pipeline.flushSeek()
        self.__setSource(None)
        self.hide()
