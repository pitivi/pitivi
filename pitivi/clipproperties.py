# Pitivi video editor
#
#       pitivi/clipproperties.py
#
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

import os

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango
from gi.repository import GES

from gettext import gettext as _

from pitivi.configure import get_ui_dir

from pitivi.dialogs.depsmanager import DepsManager

from pitivi.utils.ui import EFFECT_TARGET_ENTRY
from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import PADDING, SPACING

from pitivi.effects import AUDIO_EFFECT, VIDEO_EFFECT, HIDDEN_EFFECTS, \
    EffectsPropertiesManager


(COL_ACTIVATED,
 COL_TYPE,
 COL_BIN_DESCRIPTION_TEXT,
 COL_NAME_TEXT,
 COL_DESC_TEXT,
 COL_TRACK_EFFECT) = list(range(6))


class ClipPropertiesError(Exception):
    """Base Exception for errors happening in L{ClipProperties}s or L{EffectProperties}s"""
    pass


class ClipProperties(Gtk.Box, Loggable):
    """
    Widget for configuring the selected clip.

    @type app: L{Pitivi}
    """

    def __init__(self, app):
        Gtk.Box.__init__(self)
        Loggable.__init__(self)
        self.app = app
        self.settings = app.settings
        self._project = None

        self.set_orientation(Gtk.Orientation.VERTICAL)

        self.infobar_box = Gtk.Box()
        self.infobar_box.set_orientation(Gtk.Orientation.VERTICAL)
        self.infobar_box.show()
        self.pack_start(self.infobar_box, False, False, 0)

        # Transformation boxed DISABLED
        # self.transformation_expander = TransformationProperties(instance, instance.action_log)
        # self.transformation_expander.set_vexpand(False)
        # vbox.pack_start(self.transformation_expander, False, False, 0)

        effects_properties_manager = EffectsPropertiesManager(app)
        self.effect_expander = EffectProperties(
            app, effects_properties_manager, self)
        self.effect_expander.set_vexpand(False)
        viewport = Gtk.ScrolledWindow()
        viewport.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        viewport.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        viewport.set_visible(True)
        viewport.add(self.effect_expander)
        self.pack_start(viewport, True, True, 0)

    def _setProject(self, project):
        self._project = project
        if project:
            self.effect_expander._connectTimelineSelection(
                self.app.gui.timeline_ui.timeline)
            # Transformation boxed DISABLED
            # if self.transformation_expander:
            #     self.transformation_expander.timeline = self.app.gui.timeline_ui.timeline

    def _getProject(self):
        return self._project

    project = property(_getProject, _setProject)

    def createInfoBar(self, text):
        label = Gtk.Label(label=text)
        label.set_line_wrap(True)
        infobar = Gtk.InfoBar()
        infobar.props.message_type = Gtk.MessageType.OTHER
        infobar.get_content_area().add(label)
        self.infobar_box.pack_start(infobar, False, False, 0)
        return infobar

    def _getTimeline(self):
        return self._timeline

    def _setTimeline(self, timeline):
        self.effect_expander.timeline = timeline
        # Transformation boxed DISABLED
        # self.transformation_expander.timeline = timeline
        self._timeline = timeline

    timeline = property(_getTimeline, _setTimeline)


class EffectProperties(Gtk.Expander, Loggable):
    """
    Widget for viewing and configuring effects

    @type app: C{Pitivi}
    @type effects_properties_manager: C{EffectsPropertiesManager}
    """

    def __init__(self, app, effects_properties_manager, clip_properties):
        Gtk.Expander.__init__(self)
        self.set_expanded(True)
        self.set_label(_("Effects"))
        Loggable.__init__(self)

        # Global variables related to effects
        self.app = app
        self.settings = app.settings

        self.selected_effects = []
        self.clips = []
        self._effect_config_ui = None
        self.effects_properties_manager = effects_properties_manager
        self.clip_properties = clip_properties
        self._config_ui_h_pos = None
        self._timeline = None

        # The toolbar that will go between the list of effects and properties
        self._toolbar = Gtk.Toolbar()
        self._toolbar.get_style_context().add_class(
            Gtk.STYLE_CLASS_INLINE_TOOLBAR)
        self._toolbar.set_icon_size(Gtk.IconSize.SMALL_TOOLBAR)
        removeEffectButton = Gtk.ToolButton()
        removeEffectButton.set_icon_name("list-remove-symbolic")
        removeEffectButton.set_label(_("Remove effect"))
        removeEffectButton.set_is_important(True)
        self._toolbar.insert(removeEffectButton, 0)

        # Treeview to display a list of effects (checkbox, effect type and
        # name)
        self.treeview_scrollwin = Gtk.ScrolledWindow()
        self.treeview_scrollwin.set_policy(Gtk.PolicyType.NEVER,
                                           Gtk.PolicyType.AUTOMATIC)
        self.treeview_scrollwin.set_shadow_type(Gtk.ShadowType.ETCHED_IN)

        # We need to specify Gtk.TreeDragSource because otherwise we are hitting
        # bug https://bugzilla.gnome.org/show_bug.cgi?id=730740.
        class EffectsListStore(Gtk.ListStore, Gtk.TreeDragSource):
            def __init__(self, *args):
                Gtk.ListStore.__init__(self, *args)
                # Simply set the source index on the storemodrel directly
                # to avoid issues with the selection_data API
                # FIXME: Work around https://bugzilla.gnome.org/show_bug.cgi?id=737587
                self.source_index = None

            def do_drag_data_get(self, path, selection_data):
                self.source_index = path.get_indices()[0]

        self.storemodel = EffectsListStore(bool, str, str, str, str, object)
        self.treeview = Gtk.TreeView(model=self.storemodel)
        self.treeview_scrollwin.add(self.treeview)
        self.treeview.set_property("has_tooltip", True)
        self.treeview.set_headers_clickable(False)
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.SINGLE)

        activatedcell = Gtk.CellRendererToggle()
        activatedcell.props.xpad = PADDING
        activatedcell.connect("toggled", self._effectActiveToggleCb)
        activatedcol = self.treeview.insert_column_with_attributes(-1,
                                                                   _("Active"), activatedcell, active=COL_ACTIVATED)

        typecol = Gtk.TreeViewColumn(_("Type"))
        typecol.set_spacing(SPACING)
        typecol.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        typecell = Gtk.CellRendererText()
        typecell.props.xpad = PADDING
        typecell.set_property("ellipsize", Pango.EllipsizeMode.END)
        typecol.pack_start(typecell, True)
        typecol.add_attribute(typecell, "text", COL_TYPE)
        self.treeview.append_column(typecol)

        namecol = Gtk.TreeViewColumn(_("Effect name"))
        namecol.set_spacing(SPACING)
        namecell = Gtk.CellRendererText()
        namecell.props.xpad = PADDING
        namecell.set_property("ellipsize", Pango.EllipsizeMode.END)
        namecol.pack_start(namecell, True)
        namecol.add_attribute(namecell, "text", COL_NAME_TEXT)
        self.treeview.append_column(namecol)

        # Allow the treeview to accept EFFECT_TARGET_ENTRY when drag&dropping.
        self.treeview.enable_model_drag_dest([EFFECT_TARGET_ENTRY],
                                             Gdk.DragAction.COPY)

        # Enable reordering by drag&drop.
        self.treeview.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK,
                                               [EFFECT_TARGET_ENTRY],
                                               Gdk.DragAction.MOVE)

        self.selection = self.treeview.get_selection()

        self._infobar = clip_properties.createInfoBar(
            _("Select a clip on the timeline to configure its associated effects"))

        # Prepare the main container widgets and lay out everything
        self._vcontent = Gtk.VPaned()
        self._table = Gtk.Table(n_rows=3, n_columns=1, homogeneous=False)
        self._table.attach(self.treeview_scrollwin, 0, 1, 0, 1)
        self._table.attach(
            self._toolbar, 0, 1, 2, 3, yoptions=Gtk.AttachOptions.FILL)
        self._vcontent.pack1(self._table, resize=True, shrink=False)
        self.add(self._vcontent)
        self._vcontent.show()
        self._table.show_all()
        self._infobar.show_all()
        self._toolbar.hide()
        self.hide()

        # Connect all the widget signals
        self.selection.connect("changed", self._treeviewSelectionChangedCb)
        self.treeview.connect("drag-motion", self._dragMotionCb)
        self.treeview.connect("drag-leave", self._dragLeaveCb)
        self.treeview.connect("drag-data-received", self._dragDataReceivedCb)
        self.treeview.connect("query-tooltip", self._treeViewQueryTooltipCb)
        self._vcontent.connect("notify", self._vcontentNotifyCb)
        removeEffectButton.connect("clicked", self._removeEffectCb)
        self.app.project_manager.connect(
            "new-project-loaded", self._newProjectLoadedCb)
        self.connect('notify::expanded', self._expandedCb)
        self.connected = False

    def _newProjectLoadedCb(self, app, project, unused_fully_loaded):
        self.clip_properties.project = project
        self.selected_effects = self.timeline.selection.getSelectedEffects()
        self.updateAll()

    def _vcontentNotifyCb(self, paned, gparamspec):
        if gparamspec and gparamspec.name == 'position':
            self._config_ui_h_pos = self._vcontent.get_position()
            self.settings.effectVPanedPosition = self._config_ui_h_pos

    def _getTimeline(self):
        return self._timeline

    def _setTimeline(self, timeline):
        if self.connected:
            self._timeline.selection.disconnect_by_func(
                self._selectionChangedCb)
        self._timeline = timeline
        if timeline:
            self._timeline.selection.connect(
                "selection-changed", self._selectionChangedCb)
        self.connected = bool(timeline)

    timeline = property(_getTimeline, _setTimeline)

    def _selectionChangedCb(self, selection,):
        for clip in self.clips:
            clip.disconnect_by_func(self._trackElementAddedCb)
            clip.disconnect_by_func(self._trackElementRemovedCb)

        self.selected_effects = selection.getSelectedEffects()

        if selection.selected:
            self.clips = list(selection.selected)
            for clip in self.clips:
                clip.connect("child-added", self._trackElementAddedCb)
                clip.connect("child-removed", self._trackElementRemovedCb)
            self.show()
        else:
            self.clips = []
            self.hide()
        self.updateAll()

    def _trackElementAddedCb(self, unused_clip, track_element):
        if isinstance(track_element, GES.BaseEffect):
            selec = self.timeline.selection.getSelectedEffects()
            self.selected_effects = selec
            self.updateAll()

    def _trackElementRemovedCb(self, unused_clip, track_element):
        if isinstance(track_element, GES.BaseEffect):
            selec = self.timeline.selection.getSelectedEffects()
            self.selected_effects = selec
            self.updateAll()

    def _connectTimelineSelection(self, timeline):
        self.timeline = timeline

    def _removeEffectCb(self, toolbutton):
        if not self.selection.get_selected()[1]:
            # Cannot remove nothing,
            return
        effect = self.storemodel.get_value(self.selection.get_selected()[1],
                                           COL_TRACK_EFFECT)
        self._removeEffect(effect)

    def _removeEffect(self, effect):
        self.app.action_log.begin("remove effect")
        self._removeEffectConfigurationWidget()
        self.effects_properties_manager.cleanCache(effect)
        effect.get_parent().remove(effect)
        self.app.project_manager.current_project.timeline.commit()
        self.app.action_log.commit()
        self._updateTreeview()

    def addEffectToClip(self, clip, factory_name, priority=None):
        """Adds the specified effect if it can be applied to the clip."""
        model = self.treeview.get_model()
        media_type = self.app.effects.getFactoryFromName(
            factory_name).media_type
        for track_element in clip.get_children(False):
            track_type = track_element.get_track_type()
            if track_type == GES.TrackType.AUDIO and media_type == AUDIO_EFFECT or \
                    track_type == GES.TrackType.VIDEO and media_type == VIDEO_EFFECT:
                # Actually add the effect
                self.app.action_log.begin("add effect")
                effect = GES.Effect.new(bin_description=factory_name)
                clip.add(effect)
                if priority is not None and priority < len(model):
                    clip.set_top_effect_priority(effect, priority)
                self.app.project_manager.current_project.timeline.commit()
                self.app.action_log.commit()
                self.updateAll()
                break

    def addEffectToCurrentSelection(self, factory_name):
        if not self.clips or len(self.clips) > 1:
            return
        clip = self.clips[0]
        # Checking that this effect can be applied on this track object
        # Which means, it has the corresponding media_type
        self.addEffectToClip(clip, factory_name)

    def _dragMotionCb(self, unused_tree_view, unused_drag_context, unused_x, unused_y, unused_timestamp):
        self.debug(
            "Something is being dragged in the clip properties' effects list")
        self.drag_highlight()

    def _dragLeaveCb(self, unused_tree_view, unused_drag_context, unused_timestamp):
        self.info(
            "The item being dragged has left the clip properties' effects list")
        self.drag_unhighlight()

    def _dragDataReceivedCb(self, treeview, drag_context, x, y, selection_data, unused_info, timestamp):
        if not self.clips or len(self.clips) > 1:
            # Indicate that a drop will not be accepted.
            Gdk.drag_status(drag_context, 0, timestamp)
            return
        clip = self.clips[0]
        model = treeview.get_model()
        if drag_context.get_suggested_action() == Gdk.DragAction.COPY:
            # An effect dragged probably from the effects list.
            factory_name = str(selection_data.get_data(), "UTF-8")
            # Target
            dest_row = treeview.get_dest_row_at_pos(x, y)
            if dest_row:
                drop_path, drop_pos = dest_row
                drop_index = drop_path.get_indices()[0]
                if drop_pos != Gtk.TreeViewDropPosition.BEFORE:
                    drop_index += 1
            else:
                # This should happen when dragging after the last row.
                drop_index = None
            self.addEffectToClip(clip, factory_name, drop_index)
        elif drag_context.get_suggested_action() == Gdk.DragAction.MOVE:
            # An effect dragged from the same treeview to change its position.
            # Source
            source_index = self.storemodel.source_index
            self.storemodel.source_index = None
            # Target
            dest_row = treeview.get_dest_row_at_pos(x, y)
            if dest_row:
                drop_path, drop_pos = dest_row
                drop_index = drop_path.get_indices()[0]
                drop_index = self.calculateEffectPriority(
                    source_index, drop_index, drop_pos)
            else:
                # This should happen when dragging after the last row.
                drop_index = len(model) - 1
                drop_pos = Gtk.TreeViewDropPosition.INTO_OR_BEFORE
            self.moveEffect(clip, source_index, drop_index)
        drag_context.finish(True, False, timestamp)

    def moveEffect(self, clip, source_index, drop_index):
        if source_index == drop_index:
            # Noop.
            return
        # The paths are different.
        effects = clip.get_top_effects()
        effect = effects[source_index]
        self.app.action_log.begin("move effect")
        clip.set_top_effect_priority(effect, drop_index)
        self.app.project_manager.current_project.timeline.commit()
        self.app.action_log.commit()
        self.app.project_manager.current_project.pipeline.flushSeek()
        new_path = Gtk.TreePath.new()
        new_path.append_index(drop_index)
        self.updateAll(path=new_path)

    @staticmethod
    def calculateEffectPriority(source_index, drop_index, drop_pos):
        """
        Return where the effect from source_index will end up
        """
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
        iter = self.storemodel.get_iter(path)
        tck_effect = self.storemodel.get_value(iter, COL_TRACK_EFFECT)
        self.app.action_log.begin("change active state")
        tck_effect.set_active(not tck_effect.is_active())
        cellrenderertoggle.set_active(tck_effect.is_active())
        self._updateTreeview()
        self.app.project_manager.current_project.timeline.commit()
        self.app.action_log.commit()

    def _expandedCb(self, expander, params):
        self.updateAll()

    def _treeViewQueryTooltipCb(self, view, x, y, keyboard_mode, tooltip):
        is_row, x, y, model, path, tree_iter = view.get_tooltip_context(
            x, y, keyboard_mode)
        if not is_row:
            return False

        view.set_tooltip_row(tooltip, path)
        description = self.storemodel.get_value(tree_iter, COL_DESC_TEXT)
        bin_description = self.storemodel.get_value(
            tree_iter, COL_BIN_DESCRIPTION_TEXT)
        tooltip.set_text("%s\n%s" % (bin_description, description))
        return True

    def updateAll(self, path=None):
        if self.get_expanded():
            if len(self.clips) == 1:
                self._setEffectDragable()
                self._updateTreeview()
                if path:
                    self.selection.select_path(path)
            else:
                self._removeEffectConfigurationWidget()
                self.storemodel.clear()
                self._infobar.show()
            self._vcontent.show()
        else:
            self._vcontent.hide()

    def _updateTreeview(self):
        self.storemodel.clear()
        clip = self.clips[0]
        for effect in clip.get_top_effects():
            if effect.props.bin_description in HIDDEN_EFFECTS:
                continue
            asset = self.app.effects.getFactoryFromName(
                effect.props.bin_description)
            to_append = [effect.props.active]
            track_type = effect.get_track_type()
            if track_type == GES.TrackType.AUDIO:
                to_append.append("Audio")
            elif track_type == GES.TrackType.VIDEO:
                to_append.append("Video")
            to_append.append(effect.props.bin_description)
            effect_factory = self.app.effects.getFactoryFromName(
                effect.props.bin_description)
            to_append.append(effect_factory.human_name)
            to_append.append(asset.description)
            to_append.append(effect)
            self.storemodel.append(to_append)

    def _setEffectDragable(self):
        self.show()
        self._infobar.hide()

    def _treeviewSelectionChangedCb(self, treeview):
        if self.selection.count_selected_rows() == 0:
            self._toolbar.hide()
        else:
            self._toolbar.show()

        self._updateEffectConfigUi()

    def _updateEffectConfigUi(self):
        if self._config_ui_h_pos is None:
            self._config_ui_h_pos = self.app.gui.settings.effectVPanedPosition
            if self._config_ui_h_pos is None:
                self._config_ui_h_pos = self.app.gui.settings.mainWindowHeight // 3

        model, tree_iter = self.selection.get_selected()
        if tree_iter:
            effect = model.get_value(tree_iter, COL_TRACK_EFFECT)
            self._showEffectConfigurationWidget(effect)
        else:
            self._removeEffectConfigurationWidget()

    def _removeEffectConfigurationWidget(self):
        if not self._effect_config_ui:
            # Nothing to remove.
            return

        viewport = self._effect_config_ui.get_children()[0]
        element_settings_widget = viewport.get_children()[0]
        element_settings_widget.resetKeyframeToggleButtons()

        self._vcontent.remove(self._effect_config_ui)
        self._effect_config_ui = None

    def _showEffectConfigurationWidget(self, effect):
        self._removeEffectConfigurationWidget()
        self._effect_config_ui = self.effects_properties_manager.getEffectConfigurationUI(
            effect)
        if not self._effect_config_ui:
            return
        self._vcontent.pack2(
            self._effect_config_ui, resize=False, shrink=False)
        self._vcontent.set_position(int(self._config_ui_h_pos))
        self._effect_config_ui.show_all()


class TransformationProperties(Gtk.Expander):
    """
    Widget for viewing and configuring speed
    """

    __signals__ = {
        'selection-changed': []}

    def __init__(self, app, action_log):
        Gtk.Expander.__init__(self)
        self.action_log = action_log
        self.app = app
        self._timeline = None
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
        self.connect('notify::expanded', self._expandedCb)
        self.hide()

    def _initButtons(self):
        self.zoom_scale = self.builder.get_object("zoom_scale")
        self.zoom_scale.connect("value-changed", self._zoomViewerCb)
        clear_button = self.builder.get_object("clear_button")
        clear_button.connect("clicked", self._defaultValuesCb)

        self._getAndConnectToEffect("xpos_spinbtn", "tilt_x")
        self._getAndConnectToEffect("ypos_spinbtn", "tilt_y")

        self._getAndConnectToEffect("width_spinbtn", "scale_x")
        self._getAndConnectToEffect("height_spinbtn", "scale_y")

        self._getAndConnectToEffect("crop_left_spinbtn", "clip_left")
        self._getAndConnectToEffect("crop_right_spinbtn", "clip_right")
        self._getAndConnectToEffect("crop_top_spinbtn", "clip_top")
        self._getAndConnectToEffect("crop_bottom_spinbtn", "clip_bottom")
        self.connectSpinButtonsToFlush()

    def _zoomViewerCb(self, scale):
        self.app.gui.viewer.setZoom(scale.get_value())

    def _expandedCb(self, expander, params):
        if self._selected_clip:
            self.effect = self._findOrCreateEffect("frei0r-filter-scale0tilt")
            self._updateSpinButtons()
            self.set_expanded(self.get_expanded())
            self._updateBoxVisibility()
            self.zoom_scale.set_value(1.0)
        else:
            if self.get_expanded():
                DepsManager(self.app)
            self.set_expanded(False)

    def _defaultValuesCb(self, widget):
        self.disconnectSpinButtonsFromFlush()
        for name, spinbtn in list(self.spin_buttons.items()):
            spinbtn.set_value(self.default_values[name])
        self.connectSpinButtonsToFlush()
        # FIXME Why are we looking at the gnl object directly?
        self.effect.gnl_object.props.active = False

    def disconnectSpinButtonsFromFlush(self):
        for spinbtn in list(self.spin_buttons.values()):
            spinbtn.disconnect_by_func(self._flushPipeLineCb)

    def connectSpinButtonsToFlush(self):
        for spinbtn in list(self.spin_buttons.values()):
            spinbtn.connect("output", self._flushPipeLineCb)

    def _updateSpinButtons(self):
        for name, spinbtn in list(self.spin_buttons.items()):
            spinbtn.set_value(self.effect.get_property(name))

    def _getAndConnectToEffect(self, widget_name, property_name):
        """
        Create a spinbutton widget and connect its signals to change property
        values. While focused, disable the timeline actions' sensitivity.
        """
        spinbtn = self.builder.get_object(widget_name)
        spinbtn.connect("output", self._onValueChangedCb, property_name)
        self.spin_buttons[property_name] = spinbtn
        self.default_values[property_name] = spinbtn.get_value()

    def _onValueChangedCb(self, spinbtn, prop):
        value = spinbtn.get_value()

        # FIXME Why are we looking at the gnl object directly?
        if value != self.default_values[prop] and not self.effect.get_gnlobject().props.active:
            self.effect.get_gnlobject().props.active = True

        if value != self.effect.get_property(prop):
            self.action_log.begin("Transformation property change")
            self.effect.set_property(prop, value)
            self.action_log.commit()
        box = self.app.gui.viewer.internal.box

        # update box when values are changed in the spin boxes,
        # so no point is selected
        if box and box.clicked_point == 0:
            box.update_from_effect(self.effect)

    def _flushPipeLineCb(self, widget):
        self.app.project_manager.current_project.pipeline.flushSeek()

    def _findEffect(self, name):
        for effect in self._selected_clip.get_children(False):
            if isinstance(effect, GES.BaseEffect):
                if name in effect.get_property("bin-description"):
                    self.effect = effect
                    return effect.get_element()

    def _findOrCreateEffect(self, name):
        effect = self._findEffect(name)
        if not effect:
            effect = GES.Effect.new(bin_description=name)
            self._selected_clip.add(effect)
            tracks = self.app.project_manager.current_project.timeline.get_tracks(
            )
            effect = self._findEffect(name)
            # disable the effect on default
            a = self.effect.get_gnlobject()
            self.effect = list(list(a.elements())[0].elements())[1]
            self.effect.get_gnlobject().props.active = False
        self.app.gui.viewer.internal.set_transformation_properties(self)
        effect.freeze_notify()
        return self.effect

    def _selectionChangedCb(self, timeline):
        if self.timeline and len(self.timeline.selection.selected) > 0:
            # choose last selected clip
            # TODO: hide effects properties when multiple clips are selected
            for clip in self.timeline.selection.selected:
                pass

            if clip != self._selected_clip:
                self._selected_clip = clip
                self.effect = None

            self.show()
            if self.get_expanded():
                self.effect = self._findOrCreateEffect(
                    "frei0r-filter-scale0tilt")
                self._updateSpinButtons()
        else:
            # Deselect
            if self._selected_clip:
                self._selected_clip = None
                self.zoom_scale.set_value(1.0)
                self.app.project_manager.current_project.pipeline.flushSeek()
            self.effect = None
            self.hide()
        self._updateBoxVisibility()

    def _updateBoxVisibility(self):
        if self.get_expanded() and self._selected_clip:
            self.app.gui.viewer.internal.show_box()
        else:
            self.app.gui.viewer.internal.hide_box()

    def _getTimeline(self):
        return self._timeline

    def _setTimeline(self, timeline):
        self._timeline = timeline
        if timeline:
            self._timeline.selection.connect(
                'selection-changed', self._selectionChangedCb)

    timeline = property(_getTimeline, _setTimeline)
