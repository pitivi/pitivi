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
from gi.repository import GstController
from gi.repository import Gtk
from gi.repository import Pango

from pitivi.configure import get_ui_dir
from pitivi.effects import EffectsPropertiesManager
from pitivi.effects import HIDDEN_EFFECTS
from pitivi.undo.timeline import CommitTimelineFinalizingAction
from pitivi.utils.custom_effect_widgets import setup_custom_effect_widgets
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import disconnectAllByFunc
from pitivi.utils.pipeline import PipelineError
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
        clip (GES.Clip): The clip being configured.
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
        self.clip = None
        self._effect_config_ui = None
        self.effects_properties_manager = EffectsPropertiesManager(app)
        setup_custom_effect_widgets(self.effects_properties_manager)
        self.clip_properties = clip_properties

        no_effect_label = Gtk.Label(
            _("To apply an effect to the clip, drag it from the Effect Library."))
        no_effect_label.set_line_wrap(True)
        self.no_effect_infobar = Gtk.InfoBar()
        fix_infobar(self.no_effect_infobar)
        self.no_effect_infobar.props.message_type = Gtk.MessageType.OTHER
        self.no_effect_infobar.get_content_area().add(no_effect_label)

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

        # Allow the entire expander to accept EFFECT_TARGET_ENTRY when
        # drag&dropping.
        self.drag_dest_set(Gtk.DestDefaults.DROP, [EFFECT_TARGET_ENTRY],
                           Gdk.DragAction.COPY)

        # Allow also the treeview to accept EFFECT_TARGET_ENTRY when
        # drag&dropping so the effect can be dragged at a specific position.
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
        self._expander_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._vbox.pack_start(self.treeview, expand=False, fill=False, padding=0)
        self._vbox.pack_start(buttons_box, expand=False, fill=False, padding=0)
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_top(SPACING)
        separator.set_margin_left(SPACING)
        separator.set_margin_right(SPACING)
        self._vbox.pack_start(separator, expand=False, fill=False, padding=0)
        self._vbox.show_all()
        self._expander_box.pack_start(self.no_effect_infobar, expand=False, fill=False, padding=0)
        self._expander_box.pack_start(self._vbox, expand=False, fill=False, padding=0)
        self._expander_box.show_all()
        self.add(self._expander_box)
        self.hide()

        effects_actions_group = Gio.SimpleActionGroup()
        self.treeview.insert_action_group("clipproperties-effects", effects_actions_group)
        buttons_box.insert_action_group("clipproperties-effects", effects_actions_group)
        self.app.shortcuts.register_group("clipproperties-effects", _("Clip Effects"), position=60)

        self.remove_effect_action = Gio.SimpleAction.new("remove-effect", None)
        self.remove_effect_action.connect("activate", self._removeEffectCb)
        effects_actions_group.add_action(self.remove_effect_action)
        self.app.shortcuts.add("clipproperties-effects.remove-effect", ["Delete"],
                               _("Remove the selected effect"))
        self.remove_effect_action.set_enabled(False)
        remove_effect_button.set_action_name("clipproperties-effects.remove-effect")

        # Connect all the widget signals
        self.treeview_selection.connect("changed", self._treeviewSelectionChangedCb)
        self.connect("drag-motion", self._drag_motion_cb)
        self.connect("drag-leave", self._drag_leave_cb)
        self.connect("drag-data-received", self._drag_data_received_cb)
        self.treeview.connect("drag-motion", self._drag_motion_cb)
        self.treeview.connect("drag-leave", self._drag_leave_cb)
        self.treeview.connect("drag-data-received", self._drag_data_received_cb)
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
        self.__updateAll()

    def _selectionChangedCb(self, selection):
        if self.clip:
            self.clip.disconnect_by_func(self._trackElementAddedCb)
            self.clip.disconnect_by_func(self._trackElementRemovedCb)
            for track_element in self.clip.get_children(recursive=True):
                if isinstance(track_element, GES.BaseEffect):
                    self._disconnect_from_track_element(track_element)

        clips = list(selection.selected)
        self.clip = clips[0] if len(clips) == 1 else None
        if self.clip:
            self.clip.connect("child-added", self._trackElementAddedCb)
            self.clip.connect("child-removed", self._trackElementRemovedCb)
            for track_element in self.clip.get_children(recursive=True):
                if isinstance(track_element, GES.BaseEffect):
                    self._connect_to_track_element(track_element)
        self.__updateAll()

    def _trackElementAddedCb(self, unused_clip, track_element):
        if isinstance(track_element, GES.BaseEffect):
            self._connect_to_track_element(track_element)
            self.__updateAll()
            for path, row in enumerate(self.storemodel):
                if row[COL_TRACK_EFFECT] == track_element:
                    self.treeview_selection.select_path(path)
                    break

    def _connect_to_track_element(self, track_element):
        track_element.connect("notify::active", self._notify_active_cb)
        track_element.connect("notify::priority", self._notify_priority_cb)

    def _disconnect_from_track_element(self, track_element):
        track_element.disconnect_by_func(self._notify_active_cb)
        track_element.disconnect_by_func(self._notify_priority_cb)

    def _notify_active_cb(self, unused_track_element, unused_param_spec):
        self._updateTreeview()

    def _notify_priority_cb(self, unused_track_element, unused_param_spec):
        self._updateTreeview()

    def _trackElementRemovedCb(self, unused_clip, track_element):
        if isinstance(track_element, GES.BaseEffect):
            self._disconnect_from_track_element(track_element)
            self.__updateAll()

    def _removeEffectCb(self, unused_action, unused_param):
        selected = self.treeview_selection.get_selected()
        if not selected[1]:
            # Cannot remove nothing,
            return
        effect = self.storemodel.get_value(selected[1], COL_TRACK_EFFECT)
        selection_path = self.storemodel.get_path(selected[1])
        # Preserve selection in the tree view.
        next_selection_index = selection_path.get_indices()[0]
        effect_count = self.storemodel.iter_n_children()
        if effect_count - 1 == next_selection_index:
            next_selection_index -= 1
        self._removeEffect(effect)
        if next_selection_index >= 0:
            self.treeview_selection.select_path(next_selection_index)

    def _removeEffect(self, effect):
        pipeline = self._project.pipeline
        with self.app.action_log.started("remove effect",
                                         finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                         toplevel=True):
            self.__remove_configuration_widget()
            self.effects_properties_manager.cleanCache(effect)
            effect.get_parent().remove(effect)

    def _drag_motion_cb(self, unused_widget, unused_drag_context, unused_x, unused_y, unused_timestamp):
        """Highlights some widgets to indicate it can receive drag&drop."""
        self.debug(
            "Something is being dragged in the clip properties' effects list")
        self.no_effect_infobar.drag_highlight()
        # It would be nicer to highlight only the treeview, but
        # it does not seem to have a visible effect.
        self._vbox.drag_highlight()

    def _drag_leave_cb(self, unused_widget, unused_drag_context, unused_timestamp):
        """Unhighlights the widgets which can receive drag&drop."""
        self.debug(
            "The item being dragged has left the clip properties' effects list")
        self.no_effect_infobar.drag_unhighlight()
        self._vbox.drag_unhighlight()

    # pylint: disable=too-many-arguments
    def _drag_data_received_cb(self, widget, drag_context, x, y, selection_data, unused_info, timestamp):
        if not self.clip:
            # Indicate that a drop will not be accepted.
            Gdk.drag_status(drag_context, 0, timestamp)
            return

        dest_row = self.treeview.get_dest_row_at_pos(x, y)
        if drag_context.get_suggested_action() == Gdk.DragAction.COPY:
            # An effect dragged probably from the effects list.
            factory_name = str(selection_data.get_data(), "UTF-8")
            if widget is self.treeview:
                drop_index = self.__get_new_effect_index(dest_row)
            else:
                drop_index = len(self.storemodel)
            self.debug("Effect dragged at position %s", drop_index)
            effect_info = self.app.effects.getInfo(factory_name)
            pipeline = self._project.pipeline
            with self.app.action_log.started("add effect",
                                             finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                             toplevel=True):
                effect = self.clip.ui.add_effect(effect_info)
                if effect:
                    self.clip.set_top_effect_index(effect, drop_index)
        elif drag_context.get_suggested_action() == Gdk.DragAction.MOVE:
            # An effect dragged from the same treeview to change its position.
            # Source
            source_index, drop_index = self.__get_move_indexes(
                dest_row, self.treeview.get_model())
            self.__move_effect(self.clip, source_index, drop_index)

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
                                         finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                         toplevel=True):
            clip.set_top_effect_index(effect, drop_index)

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
        effect = self.storemodel.get_value(_iter, COL_TRACK_EFFECT)
        pipeline = self._project.ges_timeline.get_parent()
        with self.app.action_log.started("change active state",
                                         finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                         toplevel=True):
            effect.props.active = not effect.props.active
        # This is not strictly necessary, but makes sure
        # the UI reflects the current status.
        cellrenderertoggle.set_active(effect.is_active())

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
        if self.clip:
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
        for effect in self.clip.get_top_effects():
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
        has_effects = len(self.storemodel) > 0
        self.no_effect_infobar.set_visible(not has_effects)
        self._vbox.set_visible(has_effects)

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
        self.spin_buttons_handler_ids = {}
        self.set_label(_("Transformation"))
        self.__rotate_effect = None

        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(get_ui_dir(),
                                                "cliptransformation.ui"))
        self.__control_bindings = {}
        # Used to make sure self.__control_bindings_changed doesn't get called
        # when bindings are changed from this class
        self.__own_bindings_change = False
        self.add(self.builder.get_object("transform_box"))
        self._initButtons()
        self.show_all()
        self.hide()

        self.app.project_manager.connect_after(
            "new-project-loaded", self._newProjectLoadedCb)
        self.app.project_manager.connect_after(
            "project-closed", self.__project_closed_cb)

    def _newProjectLoadedCb(self, unused_app, project):
        if self._selection is not None:
            self._selection.disconnect_by_func(self._selectionChangedCb)
            self._selection = None
        if self._project:
            self._project.pipeline.disconnect_by_func(self._position_cb)

        self._project = project
        if project:
            self._selection = project.ges_timeline.ui.selection
            self._selection.connect('selection-changed', self._selectionChangedCb)
            self._project.pipeline.connect("position", self._position_cb)

    def __project_closed_cb(self, unused_project_manager, unused_project):
        self._project = None

    def _initButtons(self):
        clear_button = self.builder.get_object("clear_button")
        clear_button.connect("clicked", self._defaultValuesCb)

        self._activate_keyframes_btn = self.builder.get_object("activate_keyframes_button")
        self._activate_keyframes_btn.connect("toggled", self.__show_keyframes_toggled_cb)

        self._next_keyframe_btn = self.builder.get_object("next_keyframe_button")
        self._next_keyframe_btn.connect("clicked", self.__go_to_keyframe, True)
        self._next_keyframe_btn.set_sensitive(False)

        self._prev_keyframe_btn = self.builder.get_object("prev_keyframe_button")
        self._prev_keyframe_btn.connect("clicked", self.__go_to_keyframe, False)
        self._prev_keyframe_btn.set_sensitive(False)

        self.__setup_spin_button("xpos_spinbtn", "posx")
        self.__setup_spin_button("ypos_spinbtn", "posy")

        self.__setup_spin_button("width_spinbtn", "width")
        self.__setup_spin_button("height_spinbtn", "height")

        self.__setup_spin_button("rotate_spinbtn", "angle")

    def __get_keyframes_timestamps(self):
        keyframes_ts = []
        for prop in ["posx", "posy", "width", "height"]:
            prop_keyframes = self.__control_bindings[prop].props.control_source.get_all()
            keyframes_ts.extend([keyframe.timestamp for keyframe in prop_keyframes])

        return sorted(set(keyframes_ts))

    def __go_to_keyframe(self, unused_button, next_keyframe):
        assert self.__control_bindings
        start = self.source.props.start
        duration = self.source.props.duration
        in_point = self.source.props.in_point
        pipeline = self._project.pipeline
        position = pipeline.getPosition() - start + in_point
        seekval = start

        if in_point <= position <= in_point + duration:
            keyframes_ts = self.__get_keyframes_timestamps()

            for i in range(1, len(keyframes_ts)):
                if keyframes_ts[i - 1] <= position <= keyframes_ts[i]:
                    prev_kf_ts = keyframes_ts[i - 1]
                    kf_ts = keyframes_ts[i]
                    if next_keyframe:
                        if kf_ts == position:
                            try:
                                kf_ts = keyframes_ts[i + 1]
                            except IndexError:
                                pass
                        seekval = kf_ts + start - in_point
                    else:
                        seekval = prev_kf_ts + start - in_point
                    break
        if position > in_point + duration:
            seekval = start + duration
        pipeline.simple_seek(seekval)

    def __show_keyframes_toggled_cb(self, unused_button):
        if self._activate_keyframes_btn.props.active:
            self.__set_control_bindings()
        self.__update_keyframes_ui()

    def __update_keyframes_ui(self):
        if self.__source_uses_keyframes():
            self._activate_keyframes_btn.props.label = "◆"
        else:
            self._activate_keyframes_btn.props.label = "◇"
            self._activate_keyframes_btn.props.active = False

        if not self._activate_keyframes_btn.props.active:
            self._prev_keyframe_btn.set_sensitive(False)
            self._next_keyframe_btn.set_sensitive(False)
            if self.__source_uses_keyframes():
                self._activate_keyframes_btn.set_tooltip_text(_("Show keyframes"))
            else:
                self._activate_keyframes_btn.set_tooltip_text(_("Activate keyframes"))
            self.source.ui_element.showDefaultKeyframes()
        else:
            self._prev_keyframe_btn.set_sensitive(True)
            self._next_keyframe_btn.set_sensitive(True)
            self._activate_keyframes_btn.set_tooltip_text(_("Hide keyframes"))
            self.source.ui_element.showMultipleKeyframes(
                list(self.__control_bindings.values()))

    def __update_control_bindings(self):
        self.__control_bindings = {}
        if self.__source_uses_keyframes():
            self.__set_control_bindings()

    def __source_uses_keyframes(self):
        if self.source is None:
            return False

        for prop in ["posx", "posy", "width", "height"]:
            binding = self.source.get_control_binding(prop)
            if binding is None:
                return False

        return True

    def __remove_control_bindings(self):
        for propname, binding in self.__control_bindings.items():
            control_source = binding.props.control_source
            # control_source.unset_all() can't be used here as it doesn't emit
            # the 'value-removed' signal, so the undo system wouldn't notice
            # the removed keyframes
            keyframes_ts = [keyframe.timestamp for keyframe in control_source.get_all()]
            for ts in keyframes_ts:
                control_source.unset(ts)
            self.__own_bindings_change = True
            self.source.remove_control_binding(propname)
            self.__own_bindings_change = False
        self.__control_bindings = {}

    def __set_control_bindings(self):
        adding_kfs = not self.__source_uses_keyframes()

        if adding_kfs:
            self.app.action_log.begin("Transformation properties keyframes activate",
                                      toplevel=True)

        for prop in ["posx", "posy", "width", "height"]:
            binding = self.source.get_control_binding(prop)

            if not binding:
                control_source = GstController.InterpolationControlSource()
                control_source.props.mode = GstController.InterpolationMode.LINEAR
                self.__own_bindings_change = True
                self.source.set_control_source(control_source, prop, "direct-absolute")
                self.__own_bindings_change = False
                self.__set_default_keyframes_values(control_source, prop)

                binding = self.source.get_control_binding(prop)
            self.__control_bindings[prop] = binding

        if adding_kfs:
            self.app.action_log.commit("Transformation properties keyframes activate")

    def __set_default_keyframes_values(self, control_source, prop):
        res, val = self.source.get_child_property(prop)
        assert res
        control_source.set(self.source.props.in_point, val)
        control_source.set(self.source.props.in_point + self.source.props.duration, val)

    def _defaultValuesCb(self, unused_widget):
        with self.app.action_log.started("Transformation properties reset default",
                                         finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline),
                                         toplevel=True):
            if self.__source_uses_keyframes():
                self.__remove_control_bindings()

            for prop in ["posx", "posy", "width", "height"]:
                self.source.set_child_property(prop, self.source.ui.default_position[prop])

            if self.__rotate_effect:
                self._selected_clip.remove(self.__rotate_effect)
                self.__update_spin_btn("angle")

        self.__update_keyframes_ui()

    def __get_source_property(self, prop):
        if self.__source_uses_keyframes():
            try:
                position = self._project.pipeline.getPosition()
                start = self.source.props.start
                in_point = self.source.props.in_point
                duration = self.source.props.duration

                # If the position is outside of the clip, take the property
                # value at the start/end (whichever is closer) of the clip.
                source_position = max(0, min(position - start, duration - 1)) + in_point
                value = self.__control_bindings[prop].get_value(source_position)
                res = value is not None
                return res, value
            except PipelineError:
                pass
        elif prop == "angle":
            self.__rotate_effect = self._get_rotate_effect()
            if self.__rotate_effect:
                return self.__rotate_effect.get_child_property(prop)
            else:
                return True, 0

        return self.source.get_child_property(prop)

    def _position_cb(self, unused_pipeline, unused_position):
        if not self.__source_uses_keyframes():
            return
        for prop in ["posx", "posy", "width", "height", "angle"]:
            self.__update_spin_btn(prop)
        # Keep the overlay stack in sync with the spin buttons values
        self.app.gui.editor.viewer.overlay_stack.update(self.source)

    def __source_property_changed_cb(self, unused_source, unused_element, param):
        self.__update_spin_btn(param.name)

    def __effect_property_changed_cb(self, unused_source, unused_element, param):
        self.__update_spin_btn(param.name, False)

    def __update_spin_btn(self, prop, source_prop=True):
        if source_prop:
            assert self.source
        else:
            assert self.__rotate_effect

        try:
            spin = self.spin_buttons[prop]
            spin_handler_id = self.spin_buttons_handler_ids[prop]
        except KeyError:
            return

        if prop == "angle":
            self.__rotate_effect = self._get_rotate_effect()
            if self.__rotate_effect:
                res, value = self.__rotate_effect.get_child_property(prop)
            else:
                res, value = True, 0
        else:
            res, value = self.__get_source_property(prop)

        assert res
        if spin.get_value() != value:
            # Make sure self._onValueChangedCb doesn't get called here. If that
            # happens, we might have unintended keyframes added.
            with spin.handler_block(spin_handler_id):
                spin.set_value(value)

    def _control_bindings_changed(self, unused_track_element, unused_binding):
        if self.__own_bindings_change:
            # Do nothing if the change occurred from this class
            return

        self.__update_control_bindings()
        self.__update_keyframes_ui()

    def __set_prop(self, prop, value):
        assert self.source

        if self.__source_uses_keyframes():
            try:
                position = self._project.pipeline.getPosition()
                start = self.source.props.start
                in_point = self.source.props.in_point
                duration = self.source.props.duration
                if position < start or position > start + duration:
                    return
                source_position = position - start + in_point

                with self.app.action_log.started(
                        "Transformation property change",
                        finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline),
                        toplevel=True):
                    self.__control_bindings[prop].props.control_source.set(source_position, value)
            except PipelineError:
                self.warning("Could not get pipeline position")
                return
        else:
            with self.app.action_log.started(
                    "Transformation property change",
                    finalizing_action=CommitTimelineFinalizingAction(self._project.pipeline),
                    toplevel=True):
                if prop == "angle":
                    if not self._get_rotate_effect():
                        self.__rotate_effect = GES.Effect.new("rotate")
                        self._selected_clip.add(self.__rotate_effect)
                        self.__rotate_effect.connect("deep-notify", self.__effect_property_changed_cb)

                    self.__rotate_effect.set_child_property(prop, value)
                else:
                    self.source.set_child_property(prop, value)

    def __setup_spin_button(self, widget_name, property_name):
        """Creates a SpinButton for editing a property value."""
        spinbtn = self.builder.get_object(widget_name)
        handler_id = spinbtn.connect("value-changed", self._onValueChangedCb, property_name)
        disable_scroll(spinbtn)
        self.spin_buttons[property_name] = spinbtn
        self.spin_buttons_handler_ids[property_name] = handler_id

    def _get_rotate_effect(self):
        for effect in self._selected_clip.get_top_effects():
            if effect.props.bin_description == "rotate":
                return effect

    def _onValueChangedCb(self, spinbtn, prop):
        if not self.source:
            return

        value = spinbtn.get_value()
        res, cvalue = self.__get_source_property(prop)
        if not res:
            return

        if value != cvalue:
            self.__set_prop(prop, value)
            self.app.gui.editor.viewer.overlay_stack.update(self.source)

    def __set_source(self, source):
        if self.source:
            try:
                self.source.disconnect_by_func(self.__source_property_changed_cb)
                disconnectAllByFunc(self.source, self._control_bindings_changed)
            except TypeError:
                pass
        self.source = source
        if self.source:
            self.__update_control_bindings()
            for prop in self.spin_buttons:
                self.__update_spin_btn(prop)
            self.__update_keyframes_ui()
            self.source.connect("deep-notify", self.__source_property_changed_cb)
            self.source.connect("control-binding-added", self._control_bindings_changed)
            self.source.connect("control-binding-removed", self._control_bindings_changed)

    def _selectionChangedCb(self, unused_timeline):
        if len(self._selection) == 1:
            clip = list(self._selection)[0]
            source = clip.find_track_element(None, GES.VideoSource)
            if source:
                self._selected_clip = clip
                self.__set_source(source)
                self.app.gui.editor.viewer.overlay_stack.select(source)
                self.show()
                return

        # Deselect
        if self._selected_clip:
            self._selected_clip = None
            self._project.pipeline.commit_timeline()
        self.__set_source(None)
        self.hide()
