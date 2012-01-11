# PiTiVi , Non-linear video editor
#
#       clipproperties.py
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

"""
Class handling the midle pane
"""
import gtk
import pango
import os
import ges

from gettext import gettext as _

from pitivi.check import soft_deps
from pitivi.configure import get_ui_dir

from pitivi.dialogs.depsmanager import DepsManager

from pitivi.utils.playback import Seeker
from pitivi.utils.ui import EFFECT_TUPLE
from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import PADDING, SPACING
from pitivi.utils.widgets import GstElementSettingsWidget

from pitivi.effects import AUDIO_EFFECT, VIDEO_EFFECT, HIDDEN_EFFECTS, \
    EffectsPropertiesManager

(COL_ACTIVATED,
 COL_TYPE,
 COL_NAME_TEXT,
 COL_DESC_TEXT,
 COL_TRACK_EFFECT) = range(5)


class ClipPropertiesError(Exception):
    """Base Exception for errors happening in L{ClipProperties}s or L{EffectProperties}s"""
    pass


def compare_type(track, effect_type):

    if track.props.track_type == ges.TRACK_TYPE_AUDIO and \
            effect_type == AUDIO_EFFECT:
        return True
    elif track.props.track_type == ges.TRACK_TYPE_VIDEO and \
             effect_type == VIDEO_EFFECT:
        return True
    return False


class ClipProperties(gtk.ScrolledWindow, Loggable):
    """
    Widget for configuring clips properties
    """

    def __init__(self, instance, uiman):
        gtk.ScrolledWindow.__init__(self)
        Loggable.__init__(self)

        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.set_shadow_type(gtk.SHADOW_NONE)

        vp = gtk.Viewport()
        vp.set_shadow_type(gtk.SHADOW_NONE)
        self.add(vp)

        self.app = instance
        self.settings = instance.settings
        self._project = None
        self.transformation_expander = None
        self.info_bar_box = gtk.VBox()

        vbox = gtk.VBox()
        vbox.set_homogeneous(False)
        vp.add(vbox)

        self.effect_properties_handling = EffectsPropertiesManager(instance.action_log)

        self.effect_expander = EffectProperties(instance,
                self.effect_properties_handling, self)

        vbox.pack_start(self.info_bar_box, expand=False, fill=True)

        self.transformation_expander = TransformationProperties(
            instance, instance.action_log)
        vbox.pack_start(self.transformation_expander, expand=False, fill=False)
        self.transformation_expander.show()

        vbox.pack_end(self.effect_expander, expand=True, fill=True)
        vbox.set_spacing(SPACING)

        self.info_bar_box.show()
        self.effect_expander.show()
        vbox.show()
        vp.show()
        self.show()

    def _setProject(self, project):
        self._project = project
        if project:
            self.effect_expander._connectTimelineSelection(self._project.timeline)
            if self.transformation_expander:
                self.transformation_expander.timeline = self._project.timeline

    def _getProject(self):
        return self._project

    project = property(_getProject, _setProject)

    def addInfoBar(self, text):
        info_bar = gtk.InfoBar()

        label = gtk.Label()
        label.set_padding(PADDING, PADDING)
        label.set_line_wrap(True)
        label.set_line_wrap_mode(pango.WRAP_WORD)
        label.set_justify(gtk.JUSTIFY_CENTER)
        label.set_text(text)

        info_bar.add(label)
        self.info_bar_box.pack_start(info_bar, expand=False, fill=False)

        return label, info_bar


class EffectProperties(gtk.Expander, gtk.HBox):
    """
    Widget for viewing and configuring effects
    """
    # Note: This should be inherited from gtk.Expander when we get other things
    # to put in ClipProperties, that is why this is done this way

    def __init__(self, instance, effect_properties_handling, clip_properties):
        gtk.Expander.__init__(self)
        gtk.HBox.__init__(self)
        #self.set_expanded(True)

        self.selected_effects = []
        self.timeline_objects = []
        self._factory = None
        self.app = instance
        self.settings = instance.settings
        self.effectsHandler = self.app.effects
        self._effect_config_ui = None
        self.pipeline = None
        self.effect_props_handling = effect_properties_handling
        self.clip_properties = clip_properties
        self._info_bar = None
        self._config_ui_h_pos = None
        self._timeline = None
        # We use the seeker to flush the pipeline when needed
        self._seeker = Seeker(80)

        self._vcontent = gtk.VPaned()
        self.add(self._vcontent)

        self._table = gtk.Table(3, 1, False)

        self._toolbar = gtk.Toolbar()
        self._removeEffectBt = gtk.ToolButton("gtk-delete")
        self._removeEffectBt.set_label(_("Remove effect"))
        self._removeEffectBt.set_use_underline(True)
        self._removeEffectBt.set_is_important(True)
        self._removeEffectBt.set_sensitive(False)
        self._toolbar.insert(self._removeEffectBt, 0)
        self._table.attach(self._toolbar, 0, 1, 0, 1, yoptions=gtk.FILL)

        self.storemodel = gtk.ListStore(bool, str, str, str, object)

        #Treeview
        self.treeview_scrollwin = gtk.ScrolledWindow()
        self.treeview_scrollwin.set_policy(gtk.POLICY_NEVER,
                                           gtk.POLICY_AUTOMATIC)
        self.treeview_scrollwin.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        # TreeView
        # Displays name, description
        self.treeview = gtk.TreeView(self.storemodel)
        self.treeview_scrollwin.add(self.treeview)
        self.treeview.set_property("rules_hint", True)
        self.treeview.set_property("has_tooltip", True)
        tsel = self.treeview.get_selection()
        tsel.set_mode(gtk.SELECTION_SINGLE)

        activatedcell = gtk.CellRendererToggle()
        activatedcell.props.xpad = PADDING
        activatedcol = self.treeview.insert_column_with_attributes(-1,
                                                        _("Activated"),
                                                        activatedcell,
                                                        active=COL_ACTIVATED)
        activatedcell.connect("toggled", self._effectActiveToggleCb)

        typecol = gtk.TreeViewColumn(_("Type"))
        typecol.set_sort_column_id(COL_TYPE)
        self.treeview.append_column(typecol)
        typecol.set_spacing(SPACING)
        typecol.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        typecol.set_min_width(50)
        typecell = gtk.CellRendererText()
        typecell.props.xpad = PADDING
        typecell.set_property("ellipsize", pango.ELLIPSIZE_END)
        typecol.pack_start(typecell)
        typecol.add_attribute(typecell, "text", COL_TYPE)

        namecol = gtk.TreeViewColumn(_("Effect name"))
        namecol.set_sort_column_id(COL_NAME_TEXT)
        self.treeview.append_column(namecol)
        namecol.set_spacing(SPACING)
        namecell = gtk.CellRendererText()
        namecell.props.xpad = PADDING
        namecell.set_property("ellipsize", pango.ELLIPSIZE_END)
        namecol.pack_start(namecell)
        namecol.add_attribute(namecell, "text", COL_NAME_TEXT)

        self.treeview.drag_dest_set(gtk.DEST_DEFAULT_MOTION,
            [EFFECT_TUPLE],
            gtk.gdk.ACTION_COPY)

        self.selection = self.treeview.get_selection()

        self.selection.connect("changed", self._treeviewSelectionChangedCb)
        self._removeEffectBt.connect("clicked", self._removeEffectClicked)

        self.connect("drag-data-received", self._dragDataReceivedCb)
        self.treeview.connect("drag-leave", self._dragLeaveCb)
        self.treeview.connect("drag-drop", self._dragDropCb)
        self.treeview.connect("drag-motion", self._dragMotionCb)
        self.treeview.connect("query-tooltip", self._treeViewQueryTooltipCb)
        self._vcontent.connect("notify", self._vcontentNotifyCb)
        self.treeview.set_headers_clickable(False)
        self.app.connect("new-project-loaded",
            self._newProjectLoadedCb)

        self._table.attach(self.treeview_scrollwin, 0, 1, 2, 3)

        self._vcontent.pack1(self._table, resize=True, shrink=False)
        self._showInfoBar()
        self._vcontent.show()
        self.set_expanded(True)
        self.set_label(_("Effects"))
        self.connect('notify::expanded', self._expandedCb)
        self.connected = False

    def _newProjectLoadedCb(self, app, project):
        self.clip_properties.project = project
        self.selected_effects = self.timeline.selection.getSelectedTrackEffects()
        self._updateAll()

    def _vcontentNotifyCb(self, paned, gparamspec):
        if gparamspec.name == 'position':
            self._config_ui_h_pos = self._vcontent.get_position()
            self.settings.effectVPanedPosition = self._config_ui_h_pos

    def _getTimeline(self):
        return self._timeline

    def _setTimeline(self, timeline):
        self._timeline = timeline
        self._timeline.selection.connect("selection-changed", self._selectionChangedCb)
        self.connected = True

    timeline = property(_getTimeline, _setTimeline)

    def _selectionChangedCb(self, selection,):
        for timeline_object in self.timeline_objects:
            timeline_object.disconnect_by_func(self._trackObjectAddedCb)
            timeline_object.disconnect_by_func(self._trackRemovedRemovedCb)

        self.selected_effects = selection.getSelectedTrackEffects()

        if selection.selected:
            self.timeline_objects = list(selection.selected)
            for timeline_object in self.timeline_objects:
                timeline_object.connect("track-object-added", self._trackObjectAddedCb)
                timeline_object.connect("track-object-removed", self._trackRemovedRemovedCb)
            self.set_sensitive(True)
        else:
            self.timeline_objects = []
            self.set_sensitive(False)
        self._updateAll()

    def  _trackObjectAddedCb(self, unused_timeline_object, track_object):
        if isinstance(track_object, ges.TrackEffect):
            selec = self.timeline.selection.getSelectedTrackEffects()
            self.selected_effects = selec
            self._updateAll()

    def  _trackRemovedRemovedCb(self, unused_timeline_object, track_object):
        if isinstance(track_object, ges.TrackEffect):
            selec = self.timeline.selection.getSelectedTrackEffects()
            self.selected_effects = selec
            self._updateAll()

    def _connectTimelineSelection(self, timeline):
        self.timeline = timeline

    def _removeEffectClicked(self, toolbutton):
        if not self.selection.get_selected()[1]:
            return
        else:
            effect = self.storemodel.get_value(self.selection.get_selected()[1],
                                               COL_TRACK_EFFECT)
            self._removeEffect(effect)

    def _removeEffect(self, effect):
        self.app.action_log.begin("remove effect")
        self._cleanCache(effect)
        effect.get_track().remove_object(effect)
        effect.get_timeline_object().release_track_object(effect)
        self._updateTreeview()
        self.app.action_log.commit()

    def _cleanCache(self, effect):
        config_ui = self.effect_props_handling.cleanCache(effect)

    def addEffectToCurrentSelection(self, bin_desc):
        if self.timeline_objects:
            media_type = self.app.effects.getFactoryFromName(bin_desc).media_type

            # Trying to apply effect only on the first object of the selection
            tlobj = self.timeline_objects[0]

            # Checking that this effect can be applied on this track object
            # Which means, it has the corresponding media_type
            for tckobj in tlobj.get_track_objects():
                track = tckobj.get_track()
                if track.props.track_type == ges.TRACK_TYPE_AUDIO and \
                        media_type == AUDIO_EFFECT or \
                        track.props.track_type == ges.TRACK_TYPE_VIDEO and \
                        media_type == VIDEO_EFFECT:
                    #Actually add the effect
                    self.app.action_log.begin("add effect")
                    effect = ges.TrackParseLaunchEffect(bin_desc)
                    tlobj.add_track_object(effect)
                    track.add_object(effect)
                    self._updateAll()
                    self.app.action_log.commit()
                    self._seeker.flush()

                    break

    def _dragDataReceivedCb(self, unused_layout, context, unused_x, unused_y,
            selection, unused_targetType, unused_timestamp):
        self._factory = self.app.effects.getFactoryFromName(selection.data)

    def _dragDropCb(self, unused, context, unused_x, unused_y,
             unused_timestamp):
        if self._factory:
            self.addEffectToCurrentSelection(self._factory.effectname)
        self._factory = None

    def _dragLeaveCb(self, unused_layout, unused_context, unused_tstamp):
        self.factory = None
        self.drag_unhighlight()

    def _dragMotionCb(self, unused, context, x, y, timestamp):
        atom = gtk.gdk.atom_intern(EFFECT_TUPLE[0])
        if not self._factory:
            self.drag_get_data(context, atom, timestamp)
        self.drag_highlight()

    def _effectActiveToggleCb(self, cellrenderertoggle, path):
        iter = self.storemodel.get_iter(path)
        tck_effect = self.storemodel.get_value(iter, COL_TRACK_EFFECT)
        self.app.action_log.begin("change active state")
        tck_effect.set_active(not tck_effect.is_active())
        cellrenderertoggle.set_active(tck_effect.is_active())
        self._updateTreeview()
        self.app.action_log.commit()

    def _expandedCb(self, expander, params):
        self._updateAll()

    def _treeViewQueryTooltipCb(self, treeview, x, y, keyboard_mode, tooltip):
        context = treeview.get_tooltip_context(x, y, keyboard_mode)

        if context is None:
            return False

        treeview.set_tooltip_row(tooltip, context[1][0])

        return True

    def _updateAll(self):
        if self.get_expanded():
            self._removeEffectBt.set_sensitive(False)
            if len(self.timeline_objects) == 1:
                self._setEffectDragable()
                self._updateTreeview()
                self._updateEffectConfigUi()
            else:
                self._hideEffectConfig()
                self.storemodel.clear()
                self._showInfoBar()
            self._vcontent.show()
        else:
            self._vcontent.hide()

    def _updateTreeview(self):
        self.storemodel.clear()

        obj = self.timeline_objects[0]
        for track_effect in obj.get_top_effects():
            if not track_effect.props.bin_description in HIDDEN_EFFECTS:
                material = self.app.effects.getFactoryFromName(
                        track_effect.props.bin_description)
                to_append = [track_effect.props.active]
                track = track_effect.get_track()
                if track.props.track_type == ges.TRACK_TYPE_AUDIO:
                    to_append.append("Audio")
                elif track.props.track_type == ges.TRACK_TYPE_VIDEO:
                    to_append.append("Video")

                to_append.append(track_effect.props.bin_description)
                to_append.append(material.description)
                to_append.append(track_effect)

                self.storemodel.append(to_append)

    def _showInfoBar(self):
        if self._info_bar is None:
            self.txtlabel, self._info_bar = self.clip_properties.addInfoBar(
                                _("Select a clip on the timeline "
                                  "to configure its associated effects"))
        self._info_bar.hide_all()
        self.txtlabel.show()
        self._info_bar.show()

        self.set_sensitive(False)
        self._table.show_all()

    def _setEffectDragable(self):
        self.set_sensitive(True)
        self._table.show_all()
        self._info_bar.hide_all()

    def _treeviewSelectionChangedCb(self, treeview):
        if self.selection.count_selected_rows() == 0 and self.timeline_objects:
            self.app.gui.setActionsSensitive(['DeleteObj'], True)
            self._removeEffectBt.set_sensitive(False)
        else:
            self.app.gui.setActionsSensitive(['DeleteObj'], False)
            self._removeEffectBt.set_sensitive(True)

        self._updateEffectConfigUi()

    def _updateEffectConfigUi(self):
        if self._config_ui_h_pos is None:
            self._config_ui_h_pos = self.app.gui.settings.effectVPanedPosition
            if self._config_ui_h_pos is None:
                self._config_ui_h_pos = self.app.gui.settings.mainWindowHeight // 3

        if self.selection.get_selected()[1]:
            track_effect = self.storemodel.get_value(self.selection.get_selected()[1],
                                               COL_TRACK_EFFECT)

            for widget in self._vcontent.get_children():
                if type(widget) in [gtk.ScrolledWindow, GstElementSettingsWidget]:
                    self._vcontent.remove(widget)

            element = track_effect
            ui = self.effect_props_handling.getEffectConfigurationUI(element)

            self._effect_config_ui = ui
            if self._effect_config_ui:
                self._vcontent.pack2(self._effect_config_ui,
                                         resize=False,
                                         shrink=False)
                self._vcontent.set_position(int(self._config_ui_h_pos))
                self._effect_config_ui.show_all()
            self.selected_on_treeview = track_effect
        else:
            self._hideEffectConfig()

    def _hideEffectConfig(self):
        if self._effect_config_ui:
            self._effect_config_ui.hide()
            self._effect_config_ui = None


class TransformationProperties(gtk.Expander):
    """
    Widget for viewing and configuring speed
    """
    __signals__ = {
        'selection-changed': []}

    def __init__(self, app, action_log):
        gtk.Expander.__init__(self)
        self.action_log = action_log
        self.app = app
        self._timeline = None
        self._current_tl_obj = None
        self.spin_buttons = {}
        self.default_values = {}
        self.set_label(_("Transformation"))
        self.set_sensitive(False)
        self._seeker = Seeker(80)

        if not "Frei0r" in soft_deps:
            self.builder = gtk.Builder()
            self.builder.add_from_file(os.path.join(get_ui_dir(),
                        "cliptransformation.ui"))

            self.add(self.builder.get_object("transform_box"))
            self.show_all()
            self._initButtons()
        self.connect('notify::expanded', self._expandedCb)

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
        if not "Frei0r" in soft_deps:
            if self._current_tl_obj:
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
        for name, spinbtn in self.spin_buttons.items():
            spinbtn.set_value(self.default_values[name])
        self.connectSpinButtonsToFlush()
        self.track_effect.gnl_object.props.active = False

    def disconnectSpinButtonsFromFlush(self):
        for spinbtn in self.spin_buttons.values():
            spinbtn.disconnect_by_func(self._flushPipeLineCb)

    def connectSpinButtonsToFlush(self):
        for spinbtn in self.spin_buttons.values():
            spinbtn.connect("output", self._flushPipeLineCb)

    def _updateSpinButtons(self):
        for name, spinbtn in self.spin_buttons.items():
            spinbtn.set_value(self.effect.get_property(name))

    def _getAndConnectToEffect(self, widget_name, property_name):
        spinbtn = self.builder.get_object(widget_name)
        spinbtn.connect("output",
                        self._onValueChangedCb, property_name)
        self.spin_buttons[property_name] = spinbtn
        self.default_values[property_name] = spinbtn.get_value()

    def _onValueChangedCb(self, spinbtn, prop):
        value = spinbtn.get_value()

        if value != self.default_values[prop] and not self.track_effect.get_gnlobject().props.active:
            self.track_effect.get_gnlobject().props.active = True

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
        self._seeker.flush()

    def _findEffect(self, name):
        for track_effect in self._current_tl_obj.get_track_objects():
            if isinstance(track_effect, ges.TrackParseLaunchEffect):
                if name in track_effect.get_property("bin-description"):
                        self.track_effect = track_effect
                        return track_effect.get_element()

    def _findOrCreateEffect(self, name):
        effect = self._findEffect(name)
        if not effect:
            effect = ges.TrackParseLaunchEffect(name)
            self._current_tl_obj.add_track_object(effect)
            tracks = self.app.projectManager.current.timeline.get_tracks()
            for track in tracks:
                if track.get_caps().to_string() == "video/x-raw-yuv; video/x-raw-rgb":
                    track.add_object(effect)
            effect = self._findEffect(name)
            # disable the effect on default
            a = self.track_effect.get_gnlobject()
            self.effect = list(list(a.elements())[0].elements())[1]
            self.track_effect.get_gnlobject().props.active = False
        self.app.gui.viewer.internal.set_transformation_properties(self)
        effect.freeze_notify()
        return self.effect

    def _selectionChangedCb(self, timeline):
        if self.timeline and len(self.timeline.selection.selected) > 0:
            for tl_obj in self.timeline.selection.selected:
                pass

            if tl_obj != self._current_tl_obj:
                self._current_tl_obj = tl_obj
                self.effect = None

            self.set_sensitive(True)
            if self.get_expanded():
                self.effect = self._findOrCreateEffect("frei0r-filter-scale0tilt")
                self._updateSpinButtons()
        else:
            if self._current_tl_obj:
                self._current_tl_obj = None
                self.zoom_scale.set_value(1.0)
                self._seeker.flush()
            self.effect = None
            self.set_sensitive(False)
        self._updateBoxVisibility()

    def _updateBoxVisibility(self):
        if self.get_expanded() and self._current_tl_obj:
            self.app.gui.viewer.internal.show_box()
        else:
            self.app.gui.viewer.internal.hide_box()

    def _getTimeline(self):
        return self._timeline

    def _setTimeline(self, timeline):
        self._timeline = timeline
        if timeline:
            self._timeline.selection.connect('selection-changed', self._selectionChangedCb)

    timeline = property(_getTimeline, _setTimeline)
