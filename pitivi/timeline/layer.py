# -- coding: utf-8 --
# Pitivi video editor
#
#       pitivi/timeline/layer.py
#
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

from gi.repository import Gdk
from gi.repository import Gtk
from gi.repository import GES
from gi.repository import Gio
from gi.repository import GObject

from gettext import gettext as _

from pitivi.timeline import elements
from pitivi.utils.loggable import Loggable
from pitivi.utils import ui
from pitivi.utils import timeline as timelineUtils


class TwoStateButton(Gtk.Button):
    """
    Button with two states and according labels/images
    """

    __gsignals__ = {
        "changed-state": (GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_PYOBJECT,),)
    }

    def __init__(self, state1="", state2=""):
        Gtk.Button.__init__(self)
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.connect("clicked", self._clickedCb)

        self.set_states(state1, state2)
        self._state = True

        self.set_label(self.states[self._state])

    def set_states(self, state1, state2):
        self.states = {True: state1, False: state2}

    def _clickedCb(self, unused_widget):
        self._state = not self._state

        self.set_label(self.states[self._state])
        self.emit("changed-state", self._state)


class SpacedSeparator(Gtk.EventBox):
    """
    A Separator with vertical spacing

    Inherits from EventBox since we want to change background color
    """

    def __init__(self, position):
        Gtk.EventBox.__init__(self)

        self.box = Gtk.Box()
        self.box.set_orientation(Gtk.Orientation.VERTICAL)
        self.add(self.box)
        self.__position = position

        self.get_style_context().add_class("SpacedSeparator")
        self.box.get_style_context().add_class("SpacedSeparator")
        self._update()

    def do_state_flags_changed(self, old_flags):
        self._update()
        Gtk.EventBox.do_state_flags_changed(self, old_flags)

    def _update(self):
        HIGLIGHTED_PADDING = 3
        total_height = ui.PADDING + HIGLIGHTED_PADDING
        if not self.get_state_flags() & Gtk.StateFlags.PRELIGHT:
            self.props.height_request = 1
            self.props.margin_bottom = (total_height - 1) / 2
            self.props.margin_top = (total_height - 1) / 2
        else:
            self.props.height_request = ui.PADDING
            if self.__position == Gtk.PositionType.TOP:
                self.props.margin_bottom = HIGLIGHTED_PADDING
                self.props.margin_top = 0
            else:
                self.props.margin_bottom = 0
                self.props.margin_top = HIGLIGHTED_PADDING


class LayerControls(Gtk.EventBox, Loggable):

    __gtype_name__ = 'PitiviLayerControls'

    def __init__(self, bLayer, app):
        Gtk.EventBox.__init__(self)
        Loggable.__init__(self)

        self.bLayer = bLayer
        self.bTimeline = self.bLayer.get_timeline()
        self.app = app

        self.props.width_request = ui.CONTROL_WIDTH
        # Half the height because we display only the video strip when empty.
        self.props.height_request = ui.LAYER_HEIGHT / 2 + ui.PADDING * 3
        self.props.hexpand = True
        self.props.valign = Gtk.Align.FILL

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(hbox)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hbox.pack_start(vbox, True, True, 0)

        self.sep = Gtk.Separator.new(Gtk.Orientation.VERTICAL)
        self.sep.props.margin_top = ui.PADDING / 2
        self.sep.props.margin_bottom = ui.PADDING / 2
        hbox.pack_start(self.sep, False, False, 0)

        self.before_sep = SpacedSeparator(Gtk.PositionType.TOP)
        self.before_sep.props.width_request = self.props.width_request - 1
        self.before_sep.props.vexpand = False
        vbox.pack_start(self.before_sep, False, False, 0)

        name_row = Gtk.Box()
        name_row.set_orientation(Gtk.Orientation.HORIZONTAL)
        name_row.props.spacing = ui.PADDING
        name_row.props.margin_left = ui.PADDING
        name_row.props.margin_right = ui.PADDING
        vbox.pack_start(name_row, False, False, 0)

        self.name_entry = Gtk.Entry()
        self.name_entry.get_style_context().add_class("LayerControlEntry")
        self.name_entry.props.valign = Gtk.Align.CENTER
        self.name_entry.connect("focus-out-event", self.__nameChangedCb)
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

        self.after_sep = SpacedSeparator(Gtk.PositionType.BOTTOM)
        self.after_sep.props.width_request = self.props.width_request - 1
        self.after_sep.props.vexpand = False
        vbox.pack_start(self.after_sep, False, False, 0)

        self.bLayer.connect("notify::priority", self.__layerPriorityChangedCb)
        self.bTimeline.connect("layer-added", self.__timelineLayerAddedCb)
        self.bTimeline.connect("layer-removed", self.__timelineLayerRemovedCb)
        self.__updateActions()

        # When the window property is set, specify the mouse cursor.
        self.connect("notify::window", self.__windowSetCb)

    def __windowSetCb(self, unused_window, unused_pspec):
        self.props.window.set_cursor(Gdk.Cursor.new(Gdk.CursorType.HAND1))

    def __del__(self):
        self.name_entry.disconnect_by_func(self.__nameChangedCb)
        self.bLayer.disconnect_by_func(self.__layerPriorityChangedCb)
        self.bTimeline.disconnect_by_func(self.__timelineLayerAddedCb)
        self.bTimeline.disconnect_by_func(self.__timelineLayerRemovedCb)
        super(LayerControls, self).__del__()

    def __nameChangedCb(self, unused_widget, unused_event):
        self.bLayer.ui.setName(self.name_entry.get_text())
        self.app.project_manager.current_project.setModificationState(True)

    def __layerPriorityChangedCb(self, unused_bLayer, unused_pspec):
        self.__updateActions()
        self.__updateName()

    def __timelineLayerAddedCb(self, unused_timeline, unused_bLayer):
        self.__updateActions()

    def __timelineLayerRemovedCb(self, unused_timeline, unused_bLayer):
        self.__updateActions()

    def __updateActions(self):
        priority = self.bLayer.get_priority()
        first = priority == 0
        self.__move_layer_up_action.props.enabled = not first
        self.__move_layer_top_action.props.enabled = not first
        layers_count = len(self.bTimeline.get_layers())
        last = priority == layers_count - 1
        self.__move_layer_down_action.props.enabled = not last
        self.__move_layer_bottom_action.props.enabled = not last
        self.__delete_layer_action.props.enabled = layers_count > 1

    def __updateName(self):
        self.name_entry.set_text(self.bLayer.ui.getName())

    def __createMenuModel(self):
        action_group = Gio.SimpleActionGroup()
        menu_model = Gio.Menu()

        self.__move_layer_top_action = Gio.SimpleAction.new("move_layer_to_top", None)
        action = self.__move_layer_top_action
        action.connect("activate", self._moveLayerCb, -2)
        action_group.add_action(action)
        menu_model.append(_("Move layer to top"), "layer.%s" % action.get_name().replace(" ", "."))

        self.__move_layer_up_action = Gio.SimpleAction.new("move_layer_up", None)
        action = self.__move_layer_up_action
        action.connect("activate", self._moveLayerCb, -1)
        action_group.add_action(action)
        menu_model.append(_("Move layer up"), "layer.%s" % action.get_name().replace(" ", "."))

        self.__move_layer_down_action = Gio.SimpleAction.new("move_layer_down", None)
        action = self.__move_layer_down_action
        action.connect("activate", self._moveLayerCb, 1)
        action_group.add_action(action)
        menu_model.append(_("Move layer down"), "layer.%s" % action.get_name().replace(" ", "."))

        self.__move_layer_bottom_action = Gio.SimpleAction.new("move_layer_to_bottom", None)
        action = self.__move_layer_bottom_action
        action.connect("activate", self._moveLayerCb, 2)
        action_group.add_action(action)
        menu_model.append(_("Move layer to bottom"), "layer.%s" % action.get_name().replace(" ", "."))

        self.__delete_layer_action = Gio.SimpleAction.new("delete_layer", None)
        action = self.__delete_layer_action
        action.connect("activate", self._deleteLayerCb)
        action_group.add_action(action)
        menu_model.append(_("Delete layer"), "layer.%s" % action.get_name())

        return menu_model, action_group

    def _deleteLayerCb(self, unused_action, unused_parametter):
        self.app.action_log.begin("delete layer")
        self.bTimeline.remove_layer(self.bLayer)
        self.bTimeline.get_asset().pipeline.commit_timeline()
        self.app.action_log.commit()

    def _moveLayerCb(self, unused_simple_action, unused_parametter, step):
        index = self.bLayer.get_priority()
        if abs(step) == 1:
            index += step
        elif step == -2:
            index = 0
        else:
            index = len(self.bTimeline.get_layers()) - 1
        self.bTimeline.ui.moveLayer(self.bLayer, index)
        self.app.project_manager.current_project.pipeline.commit_timeline()

    def update(self, media_types):
        self.props.height_request = self.bLayer.ui.props.height_request + ui.PADDING * 3

        if media_types & GES.TrackType.VIDEO:
            icon = "video-x-generic"
        else:
            icon = "audio-x-generic"
        image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
        self.menubutton.props.image = image

        # TODO: Use media_types to determine which controls to show.


class LayerLayout(Gtk.Layout, Loggable):
    """
    A GtkLayout that exclusivly container Clips.
    This allows us to properly handle the z order of
    """
    __gtype_name__ = "PitiviLayerLayout"

    def __init__(self, timeline):
        super(LayerLayout, self).__init__()
        Loggable.__init__(self)

        self._children = []
        self._changed = False
        self.timeline = timeline

        self.props.hexpand = True
        self.get_style_context().add_class("LayerLayout")

    def do_add(self, widget):
        self._children.append(widget)
        self._children.sort(key=lambda clip: clip.z_order)
        Gtk.Layout.do_add(self, widget)
        self._changed = True

        for child in self._children:
            if isinstance(child, elements.TransitionClip):
                window = child.get_window()
                if window is not None:
                    window.raise_()

    def do_remove(self, widget):
        self._children.remove(widget)
        self._changed = True
        Gtk.Layout.do_remove(self, widget)

    def put(self, child, x, y):
        self._children.append(child)
        self._children.sort(key=lambda clip: clip.z_order)
        Gtk.Layout.put(self, child, x, y)
        self._changed = True

    def do_draw(self, cr):
        if self._changed:
            self._children.sort(key=lambda clip: clip.z_order)
            for child in self._children:

                if isinstance(child, elements.TransitionClip):
                    window = child.get_window()
                    window.raise_()
            self._changed = False

        self.props.width = max(self.timeline.layout.get_allocation().width,
                               timelineUtils.Zoomable.nsToPixel(self.timeline.bTimeline.props.duration))
        self.props.width_request = max(self.timeline.layout.get_allocation().width,
                                       timelineUtils.Zoomable.nsToPixel(self.timeline.bTimeline.props.duration))

        for child in self._children:
            self.propagate_draw(child, cr)


class Layer(Gtk.EventBox, timelineUtils.Zoomable, Loggable):

    __gtype_name__ = "PitiviLayer"

    __gsignals__ = {
        "remove-me": (GObject.SignalFlags.RUN_LAST, None, (),)
    }

    def __init__(self, bLayer, timeline):
        super(Layer, self).__init__()
        Loggable.__init__(self)

        self.bLayer = bLayer
        self.bLayer.ui = self
        self.timeline = timeline
        self.app = timeline.app

        self.bLayer.connect("clip-added", self._clipAddedCb)
        self.bLayer.connect("clip-removed", self._clipRemovedCb)

        # FIXME Make the layer height user setable with 'Paned'
        self.props.height_request = ui.LAYER_HEIGHT / 2
        self.props.valign = Gtk.Align.START

        self._layout = LayerLayout(self.timeline)
        self._layout.connect("remove", self.__childWidgetRemovedCb)
        self.add(self._layout)

        self.media_types = GES.TrackType(0)
        for clip in bLayer.get_clips():
            self._addClip(clip)

        self.before_sep = SpacedSeparator(Gtk.PositionType.TOP)
        self.after_sep = SpacedSeparator(Gtk.PositionType.BOTTOM)

    def setName(self, name):
        self.bLayer.set_meta("video::name", name)

    def __nameIfSet(self):
        name = self.bLayer.get_meta("video::name")
        if not name:
            name = self.bLayer.get_meta("audio::name")
        return name

    def __nameIfMeaningful(self):
        name = self.__nameIfSet()
        if name:
            for pattern in ("video [0-9]+", "audio [0-9]+", "Layer [0-9]+"):
                if re.match(pattern, name):
                    return None
        return name

    def getName(self):
        name = self.__nameIfMeaningful()
        if not name:
            name = _('Layer %d') % self.bLayer.get_priority()
        return name

    def release(self):
        for clip in self.bLayer.get_clips():
            self._removeClip(clip)
        self.bLayer.disconnect_by_func(self._clipAddedCb)
        self.bLayer.disconnect_by_func(self._clipRemovedCb)

    def checkMediaTypes(self):
        if self.timeline.editing_context:
            self.info("Not updating media types as"
                      " we are editing the timeline")
            return
        old_media_types = self.media_types
        self.media_types = GES.TrackType(0)
        bClips = self.bLayer.get_clips()
        for bClip in bClips:
            for child in bClip.get_children(False):
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
            height += ui.LAYER_HEIGHT / 2
        if self.media_types & GES.TrackType.VIDEO:
            height += ui.LAYER_HEIGHT / 2

        self.props.height_request = height
        if hasattr(self.bLayer, "control_ui") and self.bLayer.control_ui:
            self.bLayer.control_ui.update(self.media_types)

        if old_media_types != self.media_types:
            self.updatePosition()

    def move(self, child, x, y):
        self._layout.move(child, x, y)

    def _childAddedToClipCb(self, bClip, child):
        self.checkMediaTypes()

    def _childRemovedFromClipCb(self, bClip, child):
        self.checkMediaTypes()

    def _clipAddedCb(self, layer, bClip):
        self._addClip(bClip)

    def _addClip(self, bClip):
        ui_type = elements.GES_TYPE_UI_TYPE.get(bClip.__gtype__, None)
        if ui_type is None:
            self.error("Implement UI for type %s?", bClip.__gtype__)
            return

        clip = ui_type(self, bClip)

        self._layout.put(clip, self.nsToPixel(bClip.props.start), 0)
        self.show_all()
        bClip.connect_after("child-added", self._childAddedToClipCb)
        bClip.connect_after("child-removed", self._childRemovedFromClipCb)
        self.checkMediaTypes()

    def _clipRemovedCb(self, bLayer, bClip):
        self._removeClip(bClip)

    def _removeClip(self, bClip):
        if not bClip.ui:
            return

        ui_type = elements.GES_TYPE_UI_TYPE.get(bClip.__gtype__, None)
        if ui_type is None:
            self.error("Implement UI for type %s?", bClip.__gtype__)
            return

        bClip.ui.release()
        self._layout.remove(bClip.ui)
        self.timeline.selection.unselect([bClip])

    def __childWidgetRemovedCb(self, layout, clip):
        bClip = clip.bClip
        if self.timeline.draggingElement is None:
            bClip.ui.release()
            bClip.ui = None

        bClip.disconnect_by_func(self._childAddedToClipCb)
        bClip.disconnect_by_func(self._childRemovedFromClipCb)
        self.checkMediaTypes()

    def updatePosition(self):
        for bClip in self.bLayer.get_clips():
            if hasattr(bClip, "ui"):
                bClip.ui.updatePosition()

    def do_draw(self, cr):
        Gtk.Box.do_draw(self, cr)
