# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2012, Paul Lange <palango@gmx.de>
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
import re
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gio
from gi.repository import Gtk

from pitivi.timeline import elements
from pitivi.undo.timeline import CommitTimelineFinalizingAction
from pitivi.utils.loggable import Loggable
from pitivi.utils.timeline import Zoomable
from pitivi.utils.ui import LAYER_HEIGHT
from pitivi.utils.ui import PADDING
from pitivi.utils.ui import SEPARATOR_HEIGHT


class SpacedSeparator(Gtk.EventBox):
    """A Separator with vertical spacing.

    Inherits from EventBox since we want to change background color.
    """

    def __init__(self):
        Gtk.EventBox.__init__(self)

        self.get_style_context().add_class("SpacedSeparator")
        self.props.height_request = SEPARATOR_HEIGHT


class LayerControls(Gtk.EventBox, Loggable):
    """Container with widgets for controlling a layer."""

    __gtype_name__ = 'PitiviLayerControls'

    def __init__(self, ges_layer, app):
        Gtk.EventBox.__init__(self)
        Loggable.__init__(self)

        self.ges_layer = ges_layer
        self.ges_timeline = self.ges_layer.get_timeline()
        self.app = app

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(hbox)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hbox.pack_start(vbox, True, True, 0)

        rightside_separator = Gtk.Separator.new(Gtk.Orientation.VERTICAL)
        hbox.pack_start(rightside_separator, False, False, 0)

        name_row = Gtk.Box()
        name_row.set_orientation(Gtk.Orientation.HORIZONTAL)
        name_row.props.spacing = PADDING
        name_row.props.margin_top = PADDING
        name_row.props.margin_left = PADDING
        name_row.props.margin_right = PADDING
        vbox.pack_start(name_row, False, False, 0)

        self.name_entry = Gtk.Entry()
        self.name_entry.get_style_context().add_class("LayerControlEntry")
        self.name_entry.props.valign = Gtk.Align.CENTER
        self.name_entry.connect("focus-out-event", self.__name_focus_out_cb)
        self.ges_layer.connect("notify-meta", self.__layer_rename_cb)
        self.__updateName()
        name_row.pack_start(self.name_entry, True, True, 0)

        self.menubutton = Gtk.MenuButton.new()
        self.menubutton.props.valign = Gtk.Align.CENTER
        self.menubutton.props.relief = Gtk.ReliefStyle.NONE
        model, action_group = self.__createMenuModel()
        popover = Gtk.Popover.new_from_model(self.menubutton, model)
        popover.insert_action_group("layer", action_group)
        popover.props.position = Gtk.PositionType.LEFT
        self.menubutton.set_popover(popover)
        name_row.pack_start(self.menubutton, False, False, 0)

        space = Gtk.Label()
        space.props.vexpand = True
        vbox.pack_start(space, False, False, 0)

        self.ges_layer.connect("notify::priority", self.__layerPriorityChangedCb)
        self.ges_timeline.connect("layer-added", self.__timelineLayerAddedCb)
        self.ges_timeline.connect("layer-removed", self.__timelineLayerRemovedCb)
        self.__updateActions()

        # When the window property is set, specify the mouse cursor.
        self.connect("notify::window", self.__windowSetCb)

    def __windowSetCb(self, unused_window, unused_pspec):
        self.props.window.set_cursor(Gdk.Cursor.new(Gdk.CursorType.HAND1))

    def __del__(self):
        self.name_entry.disconnect_by_func(self.__name_focus_out_cb)
        self.ges_layer.disconnect_by_func(self.__layer_rename_cb)
        self.ges_layer.disconnect_by_func(self.__layerPriorityChangedCb)
        self.ges_timeline.disconnect_by_func(self.__timelineLayerAddedCb)
        self.ges_timeline.disconnect_by_func(self.__timelineLayerRemovedCb)
        super().__del__()

    def __layer_rename_cb(self, unused_ges_layer, item, value):
        if not item == "video::name":
            return
        self.__updateName()

    def __name_focus_out_cb(self, unused_widget, unused_event):
        current_name = self.ges_layer.ui.getName()
        name = self.name_entry.get_text()
        if name == current_name:
            return

        with self.app.action_log.started("change layer name"):
            self.ges_layer.ui.setName(name)

    def __layerPriorityChangedCb(self, unused_ges_layer, unused_pspec):
        self.__updateActions()
        self.__updateName()

    def __timelineLayerAddedCb(self, unused_timeline, unused_ges_layer):
        self.__updateActions()

    def __timelineLayerRemovedCb(self, unused_timeline, unused_ges_layer):
        self.__updateActions()

    def __updateActions(self):
        priority = self.ges_layer.get_priority()
        first = priority == 0
        self.__move_layer_up_action.props.enabled = not first
        self.__move_layer_top_action.props.enabled = not first
        layers_count = len(self.ges_timeline.get_layers())
        last = priority == layers_count - 1
        self.__move_layer_down_action.props.enabled = not last
        self.__move_layer_bottom_action.props.enabled = not last
        self.delete_layer_action.props.enabled = layers_count > 1

    def __updateName(self):
        self.name_entry.set_text(self.ges_layer.ui.getName())

    def __createMenuModel(self):
        action_group = Gio.SimpleActionGroup()
        menu_model = Gio.Menu()

        self.__move_layer_top_action = Gio.SimpleAction.new("move-layer-to-top", None)
        action = self.__move_layer_top_action
        action.connect("activate", self.__move_layer_cb, -2)
        action_group.add_action(action)
        menu_model.append(_("Move layer to top"), "layer.%s" % action.get_name().replace(" ", "."))

        self.__move_layer_up_action = Gio.SimpleAction.new("move-layer-up", None)
        action = self.__move_layer_up_action
        action.connect("activate", self.__move_layer_cb, -1)
        action_group.add_action(action)
        menu_model.append(_("Move layer up"), "layer.%s" % action.get_name().replace(" ", "."))

        self.__move_layer_down_action = Gio.SimpleAction.new("move-layer-down", None)
        action = self.__move_layer_down_action
        action.connect("activate", self.__move_layer_cb, 1)
        action_group.add_action(action)
        menu_model.append(_("Move layer down"), "layer.%s" % action.get_name().replace(" ", "."))

        self.__move_layer_bottom_action = Gio.SimpleAction.new("move-layer-to-bottom", None)
        action = self.__move_layer_bottom_action
        action.connect("activate", self.__move_layer_cb, 2)
        action_group.add_action(action)
        menu_model.append(_("Move layer to bottom"), "layer.%s" % action.get_name().replace(" ", "."))

        self.delete_layer_action = Gio.SimpleAction.new("delete-layer", None)
        action = self.delete_layer_action
        action.connect("activate", self.__delete_layer_cb)
        action_group.add_action(action)
        menu_model.append(_("Delete layer"), "layer.%s" % action.get_name())

        return menu_model, action_group

    def __delete_layer_cb(self, unused_action, unused_parameter):
        pipeline = self.ges_timeline.get_asset().pipeline
        with self.app.action_log.started("delete layer",
                                         CommitTimelineFinalizingAction(pipeline)):
            self.ges_timeline.remove_layer(self.ges_layer)
            removed_priority = self.ges_layer.props.priority
            for ges_layer in self.ges_timeline.get_layers():
                if ges_layer.props.priority > removed_priority:
                    ges_layer.props.priority -= 1

    def __move_layer_cb(self, unused_simple_action, unused_parameter, step):
        index = self.ges_layer.get_priority()
        if abs(step) == 1:
            index += step
        elif step == -2:
            index = 0
        else:
            index = len(self.ges_timeline.get_layers()) - 1
        self.ges_timeline.ui.moveLayer(self.ges_layer, index)
        self.app.project_manager.current_project.pipeline.commit_timeline()

    def update(self, media_types):
        self.props.height_request = self.ges_layer.ui.props.height_request

        if media_types & GES.TrackType.VIDEO:
            icon = "video-x-generic"
        else:
            icon = "audio-x-generic"
        image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
        self.menubutton.props.image = image

        # TODO: Use media_types to determine which controls to show.


class Layer(Gtk.Layout, Zoomable, Loggable):
    """Container for the clips widgets of a layer."""

    __gtype_name__ = "PitiviLayer"

    def __init__(self, ges_layer, timeline):
        Gtk.Layout.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)

        self.ges_layer = ges_layer
        self.ges_layer.ui = self
        self.timeline = timeline
        self.app = timeline.app

        self._children = []
        self._changed = False

        self.ges_layer.connect("clip-added", self._clipAddedCb)
        self.ges_layer.connect("clip-removed", self._clipRemovedCb)

        # The layer is always the width of the Timeline which contains it.
        self.props.hexpand = True
        self.props.valign = Gtk.Align.START

        self.media_types = GES.TrackType(0)
        for ges_clip in ges_layer.get_clips():
            self._add_clip(ges_clip)
        self.checkMediaTypes()

    def setName(self, name):
        self.ges_layer.set_meta("video::name", name)

    def _nameIfSet(self):
        name = self.ges_layer.get_meta("video::name")
        if not name:
            name = self.ges_layer.get_meta("audio::name")
        return name

    def __nameIfMeaningful(self):
        name = self._nameIfSet()
        if name:
            for pattern in ("video [0-9]+$", "audio [0-9]+$", "Layer [0-9]+$"):
                if re.match(pattern, name):
                    return None
        return name

    def getName(self):
        name = self.__nameIfMeaningful()
        if not name:
            name = _('Layer %d') % self.ges_layer.get_priority()
        return name

    def release(self):
        for ges_clip in self.ges_layer.get_clips():
            self._remove_clip(ges_clip)
        self.ges_layer.disconnect_by_func(self._clipAddedCb)
        self.ges_layer.disconnect_by_func(self._clipRemovedCb)

    def checkMediaTypes(self):
        if self.timeline.editing_context:
            self.info("Not updating media types as"
                      " we are editing the timeline")
            return
        old_media_types = self.media_types
        self.media_types = GES.TrackType(0)
        ges_clips = self.ges_layer.get_clips()
        for ges_clip in ges_clips:
            for child in ges_clip.get_children(False):
                track = child.get_track()
                if not track:
                    continue
                self.media_types |= track.props.track_type
                if self.media_types == GES.TrackType.AUDIO | GES.TrackType.VIDEO:
                    # Cannot find more types than these.
                    break

        if not (self.media_types & GES.TrackType.AUDIO) and not (self.media_types & GES.TrackType.VIDEO):
            # An empty layer only shows the video strip.
            self.media_types = GES.TrackType.VIDEO

        height = 0
        if self.media_types & GES.TrackType.AUDIO:
            height += LAYER_HEIGHT / 2
        if self.media_types & GES.TrackType.VIDEO:
            height += LAYER_HEIGHT / 2

        self.props.height_request = height
        if hasattr(self.ges_layer, "control_ui") and self.ges_layer.control_ui:
            self.ges_layer.control_ui.update(self.media_types)

        if old_media_types != self.media_types:
            self.updatePosition()

    def _childAddedToClipCb(self, ges_clip, child):
        self.checkMediaTypes()

    def _childRemovedFromClipCb(self, ges_clip, child):
        self.checkMediaTypes()

    def _clipAddedCb(self, unused_ges_layer, ges_clip):
        self._add_clip(ges_clip)
        self.checkMediaTypes()

    def _add_clip(self, ges_clip):
        ui_type = elements.GES_TYPE_UI_TYPE.get(ges_clip.__gtype__, None)
        if ui_type is None:
            self.error("Implement UI for type %s?", ges_clip.__gtype__)
            return

        widget = ui_type(self, ges_clip)
        self._children.append(widget)
        self._children.sort(key=lambda clip: clip.z_order)
        self.put(widget, self.nsToPixel(ges_clip.props.start), 0)
        widget.updatePosition()
        self._changed = True
        widget.show_all()

        ges_clip.connect_after("child-added", self._childAddedToClipCb)
        ges_clip.connect_after("child-removed", self._childRemovedFromClipCb)

    def _clipRemovedCb(self, unused_ges_layer, ges_clip):
        self._remove_clip(ges_clip)
        self.checkMediaTypes()

    def _remove_clip(self, ges_clip):
        if not ges_clip.ui:
            return

        ui_type = elements.GES_TYPE_UI_TYPE.get(ges_clip.__gtype__, None)
        if ui_type is None:
            self.error("Implement UI for type %s?", ges_clip.__gtype__)
            return

        self.remove(ges_clip.ui)
        self._children.remove(ges_clip.ui)
        self._changed = True
        ges_clip.ui.release()
        ges_clip.ui = None

        ges_clip.disconnect_by_func(self._childAddedToClipCb)
        ges_clip.disconnect_by_func(self._childRemovedFromClipCb)

        self.timeline.selection.unselect([ges_clip])

    def updatePosition(self):
        for ges_clip in self.ges_layer.get_clips():
            if hasattr(ges_clip, "ui"):
                ges_clip.ui.updatePosition()

    def do_draw(self, cr):
        if self._changed:
            self._children.sort(key=lambda clip: clip.z_order)
            for child in self._children:
                if isinstance(child, elements.TransitionClip):
                    window = child.get_window()
                    window.raise_()
            self._changed = False

        for child in self._children:
            self.propagate_draw(child, cr)
