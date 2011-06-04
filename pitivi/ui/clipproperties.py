# PiTiVi , Non-linear video editor
#
#       ui/clipproperties.py
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
import dnd

from gettext import gettext as _

from pitivi.log.loggable import Loggable
from pitivi.timeline.track import TrackEffect
from pitivi.stream import VideoStream

from pitivi.ui.gstwidget import GstElementSettingsWidget
from pitivi.ui.effectsconfiguration import EffectsPropertiesHandling
from pitivi.ui.common import PADDING, SPACING
from pitivi.ui import dynamic

(COL_ACTIVATED,
 COL_TYPE,
 COL_NAME_TEXT,
 COL_DESC_TEXT,
 COL_TRACK_EFFECT) = range(5)

class ClipPropertiesError(Exception):
    """Base Exception for errors happening in L{ClipProperties}s or L{EffectProperties}s"""
    pass

class ClipProperties(gtk.VBox, Loggable):
    """
    Widget for configuring clips properties
    """

    def __init__(self, instance, uiman):
        gtk.VBox.__init__(self)
        Loggable.__init__(self)

        self.app = instance
        self.settings = instance.settings
        self._project = None
        self.info_bar_box = gtk.VBox()

        self.effect_properties_handling = EffectsPropertiesHandling(instance.action_log)
        self.effect_expander = EffectProperties(instance,
                                                self.effect_properties_handling,
                                                self)

        self.pack_start(self.info_bar_box, expand=False, fill=True)
        self.pack_end(self.effect_expander, expand=True, fill=True)

        self.info_bar_box.show()
        self.effect_expander.show()
        self.show()

    def _setProject(self, project):
        self._project = project
        if project:
            self.effect_expander._connectTimelineSelection(self._project.timeline)

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

class EffectProperties(gtk.HBox):
    """
    Widget for viewing and configuring effects
    """
    # Note: This should be inherited from gtk.Expander when we get other things
    # to put in ClipProperties, that is why this is done this way

    def __init__(self, instance, effect_properties_handling, clip_properties):
        gtk.HBox.__init__(self)
        #self.set_expanded(True)

        self.selected_effects = []
        self.timeline_objects = []
        self._factory = None
        self.app = instance
        self.effectsHandler = self.app.effects
        self._effect_config_ui = None
        self.pipeline = None
        self.effect_props_handling = effect_properties_handling
        self.clip_properties = clip_properties
        self._info_bar =  None
        self._config_ui_h_pos = None
        self._timeline = None

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
                                                        active = COL_ACTIVATED)
        activatedcell.connect("toggled",  self._effectActiveToggleCb)

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
            [dnd.EFFECT_TUPLE],
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

        #self.connect('notify::expanded', self._expandedCb)

        self._table.attach(self.treeview_scrollwin, 0, 1, 2, 3)

        self._vcontent.pack1(self._table, resize=True, shrink=False)
        self._showInfoBar()
        self._vcontent.show()

    def _newProjectLoadedCb(self, app, project):
        self.clip_properties.project = project
        self.selected_effects = self.timeline.selection.getSelectedTrackEffects()
        self._updateAll()

    def _vcontentNotifyCb(self, paned, gparamspec):
        if gparamspec.name == 'position':
            self._config_ui_h_pos = self._vcontent.get_position()
            self.app.settings.effectVPanedPosition = self._config_ui_h_pos

    def _getTimeline(self):
        return self._timeline

    def _setTimeline(self, timeline):
        self._timeline = timeline
        if timeline:
            self.timeline.connect('selection-changed', self._selectionChangedCb)

    timeline = property(_getTimeline, _setTimeline)

    def _selectionChangedCb(self, timeline):
        for timeline_object in self.timeline_objects:
            timeline_object.disconnect_by_func(self._trackObjectAddedCb)
            timeline_object.disconnect_by_func(self._trackRemovedRemovedCb)

        self.selected_effects = timeline.selection.getSelectedTrackEffects()

        if timeline.selection.selected:
            self.timeline_objects = list(timeline.selection.selected)
            for timeline_object in self.timeline_objects:
                timeline_object.connect("track-object-added", self._trackObjectAddedCb)
                timeline_object.connect("track-object-removed", self._trackRemovedRemovedCb)
        else:
            self.timeline_objects = []
        self._updateAll()

    def  _trackObjectAddedCb(self, unused_timeline_object, track_object):
        if isinstance(track_object, TrackEffect):
            selec = self.timeline.selection.getSelectedTrackEffects()
            self.selected_effects = selec
            self._updateAll()

    def  _trackRemovedRemovedCb(self, unused_timeline_object, track_object):
        if isinstance(track_object, TrackEffect):
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
        effect.timeline_object.removeTrackObject(effect)
        effect.track.removeTrackObject(effect)
        self.app.action_log.commit()

    def _cleanCache(self, effect):
        element = effect.getElement()
        config_ui = self.effect_props_handling.cleanCache(element)

    def addEffectToCurrentSelection(self, factory_name):
        if self.timeline_objects:
            factory = self.app.effects.getFactoryFromName(factory_name)
            self.app.action_log.begin("add effect")
            self.timeline.addEffectFactoryOnObject(factory,
                                                   self.timeline_objects)
            self.app.action_log.commit()

    def _dragDataReceivedCb(self, unused_layout, context, unused_x, unused_y,
        selection, unused_targetType, unused_timestamp):
        self._factory = self.app.effects.getFactoryFromName(selection.data)

    def _dragDropCb(self, unused, context, unused_x, unused_y, unused_timestamp):
        if self._factory:
            self.app.action_log.begin("add effect")
            self.timeline.addEffectFactoryOnObject(self._factory,
                                                   self.timeline_objects)
            self.app.action_log.commit()
        self._factory = None

    def _dragLeaveCb(self, unused_layout, unused_context, unused_tstamp):
        self.factory = None
        self.drag_unhighlight()

    def _dragMotionCb(self, unused, context, x, y, timestamp):
        atom = gtk.gdk.atom_intern(dnd.EFFECT_TUPLE[0])
        if not self._factory:
            self.drag_get_data(context, atom, timestamp)
        self.drag_highlight()

    def _effectActiveToggleCb(self, cellrenderertoggle, path):
        iter = self.storemodel.get_iter(path)
        track_effect = self.storemodel.get_value(iter, COL_TRACK_EFFECT)
        self.app.action_log.begin("change active state")
        track_effect.active = not track_effect.active
        self.app.action_log.commit()

    #def _expandedCb(self, expander, params):
    #    self._updateAll()

    def _treeViewQueryTooltipCb(self, treeview, x, y, keyboard_mode, tooltip):
        context = treeview.get_tooltip_context(x, y, keyboard_mode)

        if context is None:
            return False

        treeview.set_tooltip_row(tooltip, context[1][0])
        tooltip.set_text(self.storemodel.get_value(context[2], COL_DESC_TEXT))

        return True

    def _updateAll(self):
        #if self.get_expanded():
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
        #else:
        #    self._vcontent.hide()

    def _activeChangedCb(self, unusedObj, unusedActive):
        self._updateTreeview()

    def _updateTreeview(self):
        self.storemodel.clear()
        for track_effect in self.selected_effects:
            to_append = [track_effect.gnl_object.get_property("active")]
            track_effect.gnl_object.connect("notify::active",
                                            self._activeChangedCb)
            if isinstance(track_effect.factory.getInputStreams()[0],
                          VideoStream):
                to_append.append("Video")
            else:
                to_append.append("Audio")

            to_append.append(track_effect.factory.getHumanName())
            to_append.append(track_effect.factory.getDescription())
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

        self.treeview.set_sensitive(False)
        self._table.show_all()

    def _setEffectDragable(self):
        self.treeview.set_sensitive(True)
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
            self._config_ui_h_pos =\
                        self.app.gui.settings.effectVPanedPosition
            if self._config_ui_h_pos is None:
                self._config_ui_h_pos=\
                        self.app.gui.settings.mainWindowHeight // 3
        if self.selection.get_selected()[1]:
            track_effect = self.storemodel.get_value(self.selection.get_selected()[1],
                                               COL_TRACK_EFFECT)

            for widget in self._vcontent.get_children():
                if type(widget) in [gtk.ScrolledWindow, GstElementSettingsWidget]:
                    self._vcontent.remove(widget)

            element = track_effect.getElement()
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
