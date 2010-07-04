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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.

import gtk
import pango
import dnd

from gettext import gettext as _

from pitivi.log.loggable import Loggable
from pitivi.effects import AUDIO_EFFECT, VIDEO_EFFECT
from pitivi.receiver import receiver, handler
from pitivi.timeline.track import TrackEffect
from pitivi.stream import AudioStream, VideoStream

from pitivi.ui.effectsconfiguration import EffectUIFactory

(COL_ACTIVATED,
 COL_TYPE,
 COL_NAME_TEXT,
 COL_DESC_TEXT,
 COL_TRACK_EFFECT) = range(5)

class ClipProperties(gtk.VBox, Loggable):
    """
    Widget for configuring clips properties
    """

    def __init__(self, instance, uiman):
        gtk.VBox.__init__(self)
        Loggable.__init__(self)

        self.app = instance
        self.settings = instance.settings
        self.project = None

        self.effectExpander = EffectProperties(instance)
        self.pack_start(self.effectExpander, expand=True, fill=True)

        self.effectExpander.show()

    def _setProject(self):
        if self.project:
            self.effectExpander.connectTimelineSelection(self.project.timeline)

    project = receiver(_setProject)

class EffectProperties(gtk.Expander):
    """
    Widget for viewing and configuring effects
    """

    def __init__(self, instance):
        gtk.Expander.__init__(self, "Effects")
        self.set_expanded(True)

        self.selected_effects = []
        self.timeline_object = None
        self.app = instance
        self.effectsHandler = self.app.effects
        self.effectUIFactory = EffectUIFactory()
        self.effect_config_ui = None

        self.VContent = gtk.VBox()
        self.add(self.VContent)

        self.table = gtk.Table(2, 1, False)
        self.VContent.pack_start(self.table, expand=False, fill=True)

        self.toolbar1 = gtk.Toolbar()
        self.removeEffectBt = gtk.ToolButton("gtk-delete")
        self.removeEffectBt.set_label("Remove effect")
        self.removeEffectBt.set_use_underline(True)
        self.removeEffectBt.set_is_important(True)
        self.toolbar1.insert(self.removeEffectBt, 0)
        self.table.attach(self.toolbar1, 0, 1, 0, 1)

        #self.toolbar2 = gtk.Toolbar()
        ##self.toolbar2.set_style(gtk.TOOLBAR_BOTH_HORIZ)
        #self.removeKeyframeBt = gtk.ToolButton("gtk-remove")
        #self.removeKeyframeBt.set_label("Remove keyframe")
        #self.removeKeyframeBt.set_use_underline(True)
        #self.removeKeyframeBt.set_is_important(True)
        #self.toolbar2.insert(self.removeKeyframeBt, 0)
        #self.table.attach(self.toolbar2, 1, 2, 0, 1)

        self.storemodel = gtk.ListStore(bool, str, str, str, object)

        #Treeview
        self.treeview_scrollwin = gtk.ScrolledWindow()
        self.treeview_scrollwin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.treeview_scrollwin.set_shadow_type(gtk.SHADOW_ETCHED_IN)

        # TreeView
        # Displays name, description
        self.treeview = gtk.TreeView(self.storemodel)
        self.treeview_scrollwin.add(self.treeview)
        self.treeview.set_property("rules_hint", True)
        self.treeview.set_property("has_tooltip", True)
        tsel = self.treeview.get_selection()
        tsel.set_mode(gtk.SELECTION_SINGLE)

        activatedcol = gtk.TreeViewColumn(_("Activated"))
        activatedcol.set_sort_column_id(COL_TYPE)
        self.treeview.append_column(activatedcol)
        activatedcol.set_spacing(5)
        activatedcol.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        activatedcol.set_min_width(15)
        activatedcell = gtk.CellRendererToggle()
        activatedcell.props.xpad = 6
        activatedcol.pack_start(activatedcell)

        activatedcell.connect("toggled",  self.effectActiveToggleCb)

        desccol = gtk.TreeViewColumn(_("Type"))
        desccol.set_sort_column_id(COL_TYPE)
        self.treeview.append_column(desccol)
        desccol.set_spacing(5)
        desccol.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        desccol.set_min_width(50)
        desccell = gtk.CellRendererText()
        desccell.props.xpad = 6
        desccell.set_property("ellipsize", pango.ELLIPSIZE_END)
        desccol.pack_start(desccell)
        desccol.add_attribute(desccell, "text", COL_TYPE)

        namecol = gtk.TreeViewColumn(_("Effect name"))
        namecol.set_sort_column_id(COL_NAME_TEXT)
        self.treeview.append_column(namecol)
        namecol.set_spacing(5)
        namecell = gtk.CellRendererText()
        namecell.props.xpad = 6
        namecell.set_property("ellipsize", pango.ELLIPSIZE_END)
        namecol.pack_start(namecell)
        namecol.add_attribute(namecell, "text", COL_NAME_TEXT)

        #Explain how to configure effects
        self.explain_box = gtk.EventBox()
        self.explain_box.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('white'))

        self.explain_label = gtk.Label()
        self.explain_label.set_padding(10, 10)
        self.explain_label.set_line_wrap(True)
        self.explain_label.set_line_wrap_mode(pango.WRAP_WORD)
        self.explain_label.set_justify(gtk.JUSTIFY_CENTER)
        self.explain_label.set_markup(
            _("<span size='large'>You must select a clip on the timeline "
              "to configure its associated effects</span>"))
        self.explain_box.add(self.explain_label)

        self.treeview.drag_dest_set(gtk.DEST_DEFAULT_MOTION,
            [dnd.EFFECT_TUPLE],
            gtk.gdk.ACTION_COPY)

        self.removeEffectBt.connect("clicked", self._removeEffectClicked)

        self.treeview.connect("drag-data-received", self._dragDataReceivedCb)
        self.treeview.connect("drag-leave", self._dragLeaveCb)
        self.treeview.connect("drag-drop", self._dragDropCb)
        self.treeview.connect("drag-motion", self._dragMotionCb)
        self.treeview.connect("query-tooltip", self._treeViewQueryTooltipCb)
        self.treeview.connect("button-press-event", self._treeViewButtonPressEventCb)

        self.connect('notify::expanded', self.expandedcb)

        self.table.attach(self.treeview_scrollwin, 0, 1, 1, 2)
        self.VContent.pack_start(self.explain_box, expand=True, fill=True)

        self._showExplainLabel()
        self.VContent.show()

    timeline = receiver()

    @handler(timeline, "selection-changed")
    def selectionChangedCb(self, timeline):
        self.selected_effects = timeline.selection.getSelectedTrackEffects()
        if timeline.selection.selected:
            self.timeline_object = list(timeline.selection.selected)[0]
        else:
            self.timeline_object = None
        self._updateAll()

    timeline_object = receiver()

    @handler(timeline_object, "track-object-added")
    def  trackAddedCb(self, unused_timeline_object, track_object):
        if isinstance (track_object, TrackEffect):
            self.selected_effects = self.timeline.selection.getSelectedTrackEffects()
            self._updateAll()

    @handler(timeline_object, "track-object-removed")
    def  trackAddedCb(self, unused_timeline_object, track_object):
        if isinstance (track_object, TrackEffect):
            self.selected_effects = self.timeline.selection.getSelectedTrackEffects()
            self._updateAll()

    def connectTimelineSelection(self, timeline):
        self.timeline = timeline

    def _removeEffectClicked(self, toolbutton):
        selection = self.treeview.get_selection().get_selected()
        if not selection[1]:
            return
        else:
            effect = self.storemodel.get_value(selection[1], COL_TRACK_EFFECT)
            self.timeline_object.removeTrackObject(effect)

    def _dragDataReceivedCb(self, unused, context, x, y, timestamp):
        # I am waiting for effects to work again before implementing DND here
        print "Receive"

    def _dragDropCb(self, unused, context, x, y, timestamp):
        print "Drop"

    def _dragLeaveCb(self, unused_layout, unused_context, unused_tstamp):
        self.drag_unhighlight()

    def _dragMotionCb(self, unused, context, x, y, timestamp):
        self.drag_highlight()

    def _timelineWatcherCb(self, timeline):
        print timeline.selection

    def effectActiveToggleCb(self, cellrenderertoggle, path):
        cellrenderertoggle.set_active(not cellrenderertoggle.get_active())

    def expandedcb(self, expander, params):
        self._updateAll()

    def _treeViewQueryTooltipCb(self, treeview, x, y, keyboard_mode, tooltip):
        context = treeview.get_tooltip_context(x, y, keyboard_mode)

        if context is None:
            return False

        treeview.set_tooltip_row (tooltip, context[1][0])
        tooltip.set_text(self.storemodel.get_value(context[2], COL_DESC_TEXT))

        return True

    def _updateAll(self):
        if self.get_expanded():
            if self.timeline_object:
                self.table.show_all()
                if not self.selected_effects:
                    self.toolbar1.hide()
                self.explain_box.hide()
                self._updateTreeview()
            else:
                self._showExplainLabel()
            self.VContent.show()
            self._updateEffectConfigUi()
        else:
            self.VContent.hide()

    def _updateTreeview(self):
        self.storemodel.clear()
        for track_effect in self.selected_effects:
            to_append = [True] #TODO Implement that
            if isinstance(track_effect.factory.getInputStreams()[0], VideoStream):
                to_append.append("Video")
            else:
                to_append.append("Audio")

            to_append.append(track_effect.factory.getHumanName())
            to_append.append(track_effect.factory.getDescription())
            to_append.append(track_effect)

            self.storemodel.append(to_append)

    def _showExplainLabel(self):
        self.table.hide()
        self.explain_box.show()
        self.explain_label.show()

    def _treeViewButtonPressEventCb(self, treeview, event):
        self._updateEffectConfigUi()

    def _updateEffectConfigUi(self):
        selection = self.treeview.get_selection().get_selected()
        if selection[1]:
            effect = self.storemodel.get_value(selection[1], COL_TRACK_EFFECT)
            #TODO figure out the name of the element better
            for element in effect.gnl_object.recurse():
                if effect.factory.name in element.get_name():
                    break

            if self.effect_config_ui:
                self.effect_config_ui.hide()

            self.effect_config_ui = self.effectUIFactory.getEffectConfigurationUI(element)
            if self.effect_config_ui:
                self.VContent.pack_start(self.effect_config_ui, expand=False, fill=True)
                self.effect_config_ui.show_all()
        else:
            if self.effect_config_ui:
                self.effect_config_ui.hide()
                self.effect_config_ui = None
