# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       pitivi/timeline/timeline.py
#
# Copyright (c) 2013, Mathieu Duponchelle <mduponchelle1@gmail.com>
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

from gettext import gettext as _

from gi.repository import GES
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gdk
from gi.repository import Gst
from gi.repository import Gtk

from pitivi.autoaligner import AlignmentProgressDialog, AutoAligner
from pitivi.configure import get_ui_dir
from pitivi.dialogs.prefs import PreferencesDialog
from pitivi.settings import GlobalSettings
from pitivi.timeline.elements import Clip, TransitionClip, TrimHandle
from pitivi.timeline.layer import Layer, LayerControls
from pitivi.timeline.ruler import ScaleRuler
from pitivi.utils.loggable import Loggable
from pitivi.utils.timeline import EditingContext, Selection, \
    TimelineError, Zoomable, \
    SELECT, SELECT_ADD
from pitivi.utils.ui import alter_style_class, \
    set_children_state_recurse, unset_children_state_recurse, \
    EXPANDED_SIZE, SPACING, CONTROL_WIDTH, \
    PLAYHEAD_WIDTH, LAYER_HEIGHT, SNAPBAR_WIDTH, \
    EFFECT_TARGET_ENTRY, URI_TARGET_ENTRY
from pitivi.utils.widgets import ZoomBox


GlobalSettings.addConfigOption('edgeSnapDeadband',
                               section="user-interface",
                               key="edge-snap-deadband",
                               default=5,
                               notify=True)

PreferencesDialog.addNumericPreference('edgeSnapDeadband',
                                       section=_("Behavior"),
                                       label=_("Snap distance"),
                                       description=_("Threshold (in pixels) at which two clips will snap together "
                                                     "when dragging or trimming."),
                                       lower=0)

GlobalSettings.addConfigOption('imageClipLength',
                               section="user-interface",
                               key="image-clip-length",
                               default=1000,
                               notify=True)

PreferencesDialog.addNumericPreference('imageClipLength',
                                       section=_("Behavior"),
                                       label=_("Image clip duration"),
                                       description=_(
                                           "Default clip length (in milliseconds) of images when inserting on the timeline."),
                                       lower=1)

GlobalSettings.addConfigOption('leftClickAlsoSeeks',
                               section="user-interface",
                               key="left-click-to-select",
                               default=True,
                               notify=True)

PreferencesDialog.addTogglePreference('leftClickAlsoSeeks',
                                      section=_("Behavior"),
                                      label=_("Left click also seeks"),
                                      description=_(
                                          "Whether left-clicking also seeks besides selecting and editing clips."))

"""
Convention throughout this file:
Every GES element which name could be mistaken with a UI element
is prefixed with a little b, example : bTimeline
"""


class VerticalBar(Gtk.DrawingArea, Loggable):
    """
    A simple vertical bar to be drawn on top of the timeline
    """
    __gtype_name__ = "PitiviVerticalBar"

    def __init__(self, css_class):
        super(VerticalBar, self).__init__()
        Loggable.__init__(self)
        self.get_style_context().add_class(css_class)

    def do_get_preferred_width(self):
        return PLAYHEAD_WIDTH, PLAYHEAD_WIDTH

    def do_get_preferred_height(self):
        return self.get_parent().get_allocated_height(), self.get_parent().get_allocated_height()


class Marquee(Gtk.Box, Loggable):
    """
    Marquee widget representing a selection area inside the timeline
    it should be drawn on top of the timeline layout.

    It provides an API that makes it easy to update its value directly
    from Gdk.Event
    """

    __gtype_name__ = "PitiviMarquee"

    def __init__(self, timeline):
        """
        @timeline: The #Timeline on which the marquee will
                   be used
        """
        super(Marquee, self).__init__()
        Loggable.__init__(self)

        self._timeline = timeline
        self.start_x = None
        self.start_y = None
        self.set_visible(False)

        self.get_style_context().add_class("Marquee")

    def hide(self):
        self.start_x = None
        self.start_y = None
        self.props.height_request = -1
        self.props.width_request = -1
        self.set_visible(False)

    def setStartPosition(self, event):
        event_widget = self._timeline.get_event_widget(event)
        x, y = event_widget.translate_coordinates(self._timeline, event.x, event.y)

        self.start_x, self.start_y = self._timeline.adjustCoords(x=x, y=y)

    def move(self, event):
        event_widget = self._timeline.get_event_widget(event)

        x, y = self._timeline.adjustCoords(coords=event_widget.translate_coordinates(self._timeline, event.x, event.y))

        start_x = min(x, self.start_x)
        start_y = min(y, self.start_y)

        self.get_parent().move(self, start_x, start_y)
        self.props.width_request = abs(self.start_x - x)
        self.props.height_request = abs(self.start_y - y)
        self.set_visible(True)

    def findSelected(self):
        x, y = self._timeline.layout.child_get(self, "x", "y")
        res = []

        w = self.props.width_request
        for layer in self._timeline.bTimeline.get_layers():
            intersects, unused_rect = layer.ui.get_allocation().intersect(self.get_allocation())
            if not intersects:
                continue

            for clip in layer.get_clips():
                if self.contains(clip, x, w):
                    toplevel = clip.get_toplevel_parent()
                    if isinstance(toplevel, GES.Group) and toplevel != self._timeline.current_group:
                        res.extend([c for c in clip.get_toplevel_parent().get_children(True)
                                    if isinstance(c, GES.Clip)])
                    else:
                        res.append(clip)

        self.debug("Result is %s", res)

        return tuple(set(res))

    def contains(self, clip, marquee_start, marquee_width):
        if clip.ui is None:
            return False

        child_start = clip.ui.get_parent().child_get(clip.ui, "x")[0]
        child_end = child_start + clip.ui.get_allocation().width

        marquee_end = marquee_start + marquee_width

        if child_start <= marquee_start <= child_end:
            return True

        if child_start <= marquee_end <= child_end:
            return True

        if marquee_start <= child_start and marquee_end >= child_end:
            return True

        return False


class Timeline(Gtk.EventBox, Zoomable, Loggable):
    """
    Contains the layer controls and the layers representation.

    @type parent: L{pitivi.timeline.timeline.TimelineContainer}
    @type _project: L{pitivi.project.Project}
    """

    __gtype_name__ = "PitiviTimeline"

    def __init__(self, container, app):
        Gtk.EventBox.__init__(self)
        Zoomable.__init__(self)
        Loggable.__init__(self)

        self.parent = container
        self.app = app
        self._project = None
        self.bTimeline = None

        self.props.can_focus = False

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(hbox)

        # Stuff the layers representation in a Layout so we can have other
        # widgets there, see below.
        self.layout = Gtk.Layout()
        self.layout.props.can_focus = True
        self.layout.props.can_default = True
        self.__layers_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.__layers_vbox.props.width_request = self.get_allocated_width()
        self.__layers_vbox.props.height_request = self.get_allocated_height()
        self.layout.put(self.__layers_vbox, 0, 0)
        self.hadj = self.layout.get_hadjustment()
        self.vadj = self.layout.get_vadjustment()
        hbox.pack_end(self.layout, False, True, 0)

        # Stuff the layers controls in a Viewport so it can be scrolled.
        self.__layers_controls_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.__layers_controls_vbox.props.hexpand = False
        self.__layers_controls_vbox.props.valign = Gtk.Align.START

        # Stuff the layers controls in a viewport so it can be scrolled.
        viewport = Gtk.Viewport(vadjustment=self.vadj)
        viewport.add(self.__layers_controls_vbox)
        # Make sure the viewport has no border or other decorations.
        viewport_style = viewport.get_style_context()
        for css_class in viewport_style.list_classes():
            viewport_style.remove_class(css_class)
        hbox.pack_start(viewport, False, False, 0)

        self.get_style_context().add_class("Timeline")
        self.props.expand = True
        self.get_accessible().set_name("timeline canvas")
        self.__fake_event_widget = None

        # A lot of operations go through these callbacks.
        self.add_events(Gdk.EventType.BUTTON_PRESS | Gdk.EventType.BUTTON_RELEASE)
        self.connect("button-press-event", self.__buttonPressEventCb)
        self.connect("button-release-event", self.__buttonReleaseEventCb)
        self.connect("motion-notify-event", self.__motionNotifyEventCb)

        self._layers = []
        # Whether the user is dragging a layer.
        self.__moving_layer = None

        self.__last_position = 0
        self.__playhead = VerticalBar("PlayHead")
        self.layout.put(self.__playhead, self.nsToPixel(self.__last_position), 0)
        self._scrubbing = False
        self._scrolling = False

        self.__snap_position = 0
        self.__snap_bar = VerticalBar("SnapBar")
        self.__snap_bar.props.no_show_all = True
        self.layout.put(self.__snap_bar, 0, 0)

        # Clip selection.
        self.selection = Selection()
        self.current_group = None
        self.resetSelectionGroup()
        self.__marquee = Marquee(self)
        self.layout.put(self.__marquee, 0, 0)

        # Clip editing.
        self.draggingElement = None
        self.__clickedHandle = None
        self.editing_context = None
        # Whether draggingElement really got dragged.
        self.__got_dragged = False
        self.__drag_start_x = 0
        self.__on_separators = []
        self._on_layer = None

        # Drag & dropping assets from outside.

        # Set to True when a clip has been dragged because the first
        # button-release-event on the clip should be ignored.
        self.got_dragged = False
        # Whether the drop data has been received. See self.dropData below.
        self.dropDataReady = False
        # What's being dropped, for example asset URIs.
        self.dropData = None
        # Whether clips have been created in the current drag & drop.
        self._createdClips = False
        # The list of (Layer, Clip) tuples dragged into the timeline.
        self.__last_clips_on_leave = None

        # To be able to receive effects dragged on clips.
        self.drag_dest_set(0, [EFFECT_TARGET_ENTRY], Gdk.DragAction.COPY)
        # To be able to receive assets dragged from the media library.
        self.drag_dest_add_uri_targets()

        self.connect("drag-motion", self.__dragMotionCb)
        self.connect("drag-leave", self.__dragLeaveCb)
        self.connect("drag-drop", self.__dragDropCb)
        self.connect("drag-data-received", self.__dragDataReceivedCb)

    def sendFakeEvent(self, event, event_widget=None):
        # Member usefull for testsing
        self.__fake_event_widget = event_widget

        self.info("Faking %s", event)
        if event.type == Gdk.EventType.BUTTON_PRESS:
            self.__buttonPressEventCb(self, event)
        elif event.type == Gdk.EventType.BUTTON_RELEASE:
            self.__buttonReleaseEventCb(self, event)
        elif event.type == Gdk.EventType.MOTION_NOTIFY:
            self.__motionNotifyEventCb(self, event)
        else:
            self.parent.sendFakeEvent(event)

        self.__fake_event_widget = None

    def get_event_widget(self, event):
        if self.__fake_event_widget:
            return self.__fake_event_widget

        return Gtk.get_event_widget(event)

    def resetSelectionGroup(self):
        self.debug("Reset selection group")
        if self.current_group:
            GES.Container.ungroup(self.current_group, False)

        self.current_group = GES.Group()
        self.current_group.props.serialize = False

    def setProject(self, project):
        """
        Connects to the GES.Timeline holding the project.
        """
        if self.bTimeline is not None:
            self.bTimeline.disconnect_by_func(self._durationChangedCb)
            self.bTimeline.disconnect_by_func(self._layerAddedCb)
            self.bTimeline.disconnect_by_func(self._layerRemovedCb)
            self.bTimeline.disconnect_by_func(self._snapCb)
            self.bTimeline.disconnect_by_func(self._snapEndedCb)
            for bLayer in self.bTimeline.get_layers():
                self._removeLayer(bLayer)

            self.bTimeline.ui = None
            self.bTimeline = None

        self._project = project
        if self._project:
            self._project.pipeline.connect('position', self._positionCb)
            self.bTimeline = self._project.timeline

        if self.bTimeline is None:
            return

        for bLayer in self.bTimeline.get_layers():
            self._addLayer(bLayer)

        self.bTimeline.connect("notify::duration", self._durationChangedCb)
        self.bTimeline.connect("layer-added", self._layerAddedCb)
        self.bTimeline.connect("layer-removed", self._layerRemovedCb)
        self.bTimeline.connect("snapping-started", self._snapCb)
        self.bTimeline.connect("snapping-ended", self._snapEndedCb)
        self.bTimeline.ui = self

        self.queue_draw()

    def _durationChangedCb(self, bTimeline, pspec):
        self.queue_draw()

    def scrollToPlayhead(self, align=None, when_not_in_view=False):
        """
        Scroll so that the playhead is in view.

        @param align: Where the playhead should be post-scroll.
        @type align: L{Gtk.Align}
        @param when_not_in_view: Whether to scroll only if the playhead is not
                                 visible.
        """
        self.debug("Scrolling to playhead")
        self.__setLayoutSize()
        layout_width = self.layout.get_allocation().width
        if when_not_in_view:
            x = self.nsToPixel(self.__last_position) - self.hadj.get_value()
            if x >= 0 and x <= layout_width:
                return

        # Deciding the new position of the playhead in the timeline's view.
        if align == Gtk.Align.START:
            delta = 100
        elif align == Gtk.Align.END:
            delta = layout_width - 100
        else:
            # Center.
            delta = layout_width / 2
        self.hadj.set_value(self.nsToPixel(self.__last_position) - delta)

    def _positionCb(self, pipeline, position):
        if self.__last_position == position:
            return

        self.__last_position = position
        layout_width = self.layout.get_allocation().width
        x = max(0, self.nsToPixel(self.__last_position))
        self.layout.move(self.__playhead, x, 0)
        if pipeline.playing() and x - self.hadj.get_value() > layout_width - 100:
            self.scrollToPlayhead(Gtk.Align.START)

    # snapping indicator
    def _snapCb(self, unused_timeline, unused_obj1, unused_obj2, position):
        """
        Display or hide a snapping indicator line
        """
        self.layout.move(self.__snap_bar, self.nsToPixel(position), 0)
        self.__snap_bar.show()
        self.__snap_position = position

    def hideSnapBar(self):
        self.__snap_position = 0
        self.__snap_bar.hide()

    def _snapEndedCb(self, *unused_args):
        self.hideSnapBar()

    # Gtk.Widget virtual methods implementation
    def do_get_preferred_height(self):
        natural_height = max(1, len(self._layers)) * (LAYER_HEIGHT + 20)

        return LAYER_HEIGHT, natural_height

    def __setLayoutSize(self):
        if self.bTimeline:
            width = self._timelineLengthInPixels()
            if self.draggingElement:
                width = max(width, self.layout.props.width)

            self.__layers_vbox.props.width_request = width
            self.layout.set_size(width, len(self.bTimeline.get_layers()) * 200)

    def do_size_allocate(self, request):
        self.__setLayoutSize()
        Gtk.EventBox.do_size_allocate(self, request)

    def do_draw(self, cr):
        self.__setLayoutSize()
        Gtk.EventBox.do_draw(self, cr)

        self.__drawSnapIndicator(cr)
        self.__drawPlayHead(cr)

        self.layout.propagate_draw(self.__marquee, cr)

    def __drawSnapIndicator(self, cr):
        if self.__snap_position > 0:
            self.__snap_bar.props.height_request = self.layout.props.height
            self.__snap_bar.props.width_request = SNAPBAR_WIDTH

            self.layout.propagate_draw(self.__snap_bar, cr)
        else:
            self.__snap_bar.hide()

    def __drawPlayHead(self, cr):
        self.__playhead.props.height_request = self.layout.props.height
        self.__playhead.props.width_request = PLAYHEAD_WIDTH

        self.layout.propagate_draw(self.__playhead, cr)

    # ------------- #
    # util methods  #
    # ------------- #
    def _timelineLengthInPixels(self):
        if self.bTimeline is None:
            return 100

        space_at_the_end = self.layout.get_allocation().width * 2 / 3
        return self.nsToPixel(self.bTimeline.props.duration) + space_at_the_end

    def _getParentOfType(self, widget, _type):
        """
        Get a clip from a child widget, if the widget is a child of the clip
        """
        if isinstance(widget, _type):
            return widget

        parent = widget.get_parent()
        while parent is not None and parent != self:
            if isinstance(parent, _type):
                return parent

            parent = parent.get_parent()
        return None

    def adjustCoords(self, coords=None, x=None, y=None):
        """
        Adjust coordinates passed as parametter that are raw
        coordinates from the whole timeline into sensible
        coordinates inside the visible area of the timeline.
        """
        if coords:
            x = coords[0]
            y = coords[1]

        if x is not None:
            x += self.hadj.props.value
            x -= CONTROL_WIDTH

        if y is not None:
            y += self.vadj.props.value

            if x is None:
                return y
        else:
            return x

        return x, y

    # Gtk events management

    def do_scroll_event(self, event):
        res, delta_x, delta_y = event.get_scroll_deltas()
        if not res:
            res, direction = event.get_scroll_direction()
            if not res:
                self.error("Could not get scroll delta")
                return False

            if direction == Gdk.ScrollDirection.UP:
                delta_y = -1.0
            elif direction == Gdk.ScrollDirection.DOWN:
                delta_y = 1.0
            else:
                self.error("Could not handle %s scroll event", direction)
                return False

        event_widget = self.get_event_widget(event)
        x, y = event_widget.translate_coordinates(self, event.x, event.y)
        if event.get_state() & Gdk.ModifierType.SHIFT_MASK:
            if delta_y > 0:
                self.parent.scroll_down()
            elif delta_y < 0:
                self.parent.scroll_up()
        elif event.get_state() & (Gdk.ModifierType.CONTROL_MASK |
                                  Gdk.ModifierType.MOD1_MASK):
            x -= CONTROL_WIDTH
            # Figure out first where to scroll at the end
            if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
                # The time at the mouse cursor.
                position = self.pixelToNs(x + self.hadj.get_value())
            else:
                # The time at the playhead.
                position = self.__last_position
            if delta_y > 0:
                Zoomable.zoomOut()
            elif delta_y < 0:
                Zoomable.zoomIn()
            self.__setLayoutSize()
            if delta_y:
                self.queue_draw()
                # Scroll so position is at the current mouse cursor position.
                self.hadj.set_value(self.nsToPixel(position) - x)
        else:
            if delta_y > 0:
                self.parent.scroll_right()
            else:
                self.parent.scroll_left()

        return False

    def __buttonPressEventCb(self, unused_widget, event):
        self.debug("PRESSED %s", event)
        self.app.gui.focusTimeline()
        event_widget = self.get_event_widget(event)

        res, button = event.get_button()
        if res and button == 1:
            self.draggingElement = self._getParentOfType(event_widget, Clip)
            if isinstance(event_widget, TrimHandle):
                self.__clickedHandle = event_widget
            self.debug("Dragging element is %s", self.draggingElement)

            if self.draggingElement is not None:
                self.__drag_start_x = event.x
                self._on_layer = self.draggingElement.layer.bLayer
            else:
                layer_controls = self._getParentOfType(event_widget, LayerControls)
                if layer_controls:
                    self.__moving_layer = layer_controls.bLayer
                else:
                    self.__marquee.setStartPosition(event)

        self._scrubbing = res and button == 3
        if self._scrubbing:
            self._seek(event)
            clip = self._getParentOfType(event_widget, Clip)
            if clip:
                clip.shrinkTrimHandles()

        self._scrolling = res and button == 2
        if self._scrolling:
            self._scroll_start_x = event.x
            self._scroll_start_y = event.y

        return False

    def __buttonReleaseEventCb(self, unused_widget, event):
        allow_seek = not self.__got_dragged

        res, button = event.get_button()
        if self.draggingElement:
            self.dragEnd()
        elif self.__moving_layer:
            self.__endMovingLayer()
            return False
        elif res and button == 1:
            self._selectUnderMarquee()

        self._scrubbing = False

        self._scrolling = False

        if allow_seek and res and (button == 1 and self.app.settings.leftClickAlsoSeeks):
            self._seek(event)

        self._snapEndedCb()

        return False

    def __motionNotifyEventCb(self, unused_widget, event):
        if self.draggingElement:
            if type(self.draggingElement) == TransitionClip and \
                    not self.__clickedHandle:
                # Don't allow dragging a transition.
                return False

            state = event.get_state()
            if isinstance(state, tuple):
                state = state[1]
            if not state & Gdk.ModifierType.BUTTON1_MASK:
                self.dragEnd()
                return False

            if self.got_dragged or self.__drag_start_x != event.x:
                self.__dragUpdate(self.get_event_widget(event), event.x, event.y)
                self.got_dragged = True
        elif self.__moving_layer:
            event_widget = self.get_event_widget(event)
            unused_x, y = event_widget.translate_coordinates(self, event.x, event.y)
            layer, unused_on_sep = self.__getLayerAt(
                y, prefer_bLayer=self.__moving_layer, past_middle_when_adjacent=True)
            if layer != self.__moving_layer:
                priority = layer.get_priority()
                self.moveLayer(self.__moving_layer, priority)
        elif self.__marquee.start_x:
            self.__marquee.move(event)
        elif self._scrubbing:
            self._seek(event)
        elif self._scrolling:
            self.__scroll(event)

        return False

    def _seek(self, event):
        event_widget = self.get_event_widget(event)
        x, unused_y = event_widget.translate_coordinates(self, event.x, event.y)
        x -= CONTROL_WIDTH
        x += self.hadj.get_value()
        position = max(0, self.pixelToNs(x))
        self._project.pipeline.simple_seek(position)

    def __scroll(self, event):
        # determine how much to move the canvas
        x_diff = self._scroll_start_x - event.x
        self.hadj.set_value(self.hadj.get_value() + x_diff)
        y_diff = self._scroll_start_y - event.y
        self.vadj.set_value(self.vadj.get_value() + y_diff)

    def _selectUnderMarquee(self):
        self.resetSelectionGroup()
        if self.__marquee.props.width_request > 0:
            clips = self.__marquee.findSelected()
            for clip in clips:
                self.current_group.add(clip.get_toplevel_parent())
        else:
            clips = []
        self.selection.setSelection(clips, SELECT)

        self.__marquee.hide()

    def updatePosition(self):
        for layer in self._layers:
            layer.updatePosition()

        self.queue_draw()

    def __createClips(self, x, y):
        if self._createdClips:
            return False

        x = self.adjustCoords(x=x)

        placement = 0
        self.draggingElement = None
        self.resetSelectionGroup()
        self.selection.setSelection([], SELECT)
        assets = self._project.assetsForUris(self.dropData)
        if not assets:
            self._project.addUris(self.dropData)
            return False
        for asset in assets:
            if asset.is_image():
                clip_duration = self.app.settings.imageClipLength * \
                    Gst.SECOND / 1000.0
            else:
                clip_duration = asset.get_duration()

            bLayer, unused_on_sep = self.__getLayerAt(y)
            if not placement:
                placement = self.pixelToNs(x)
            placement = max(0, placement)

            self.debug("Creating %s at %s", asset.props.id, Gst.TIME_ARGS(placement))

            self.app.action_log.begin("add clip")
            bClip = bLayer.add_asset(asset,
                                     placement,
                                     0,
                                     clip_duration,
                                     asset.get_supported_formats())
            placement += clip_duration
            self.current_group.add(bClip.get_toplevel_parent())
            self.selection.setSelection([], SELECT_ADD)
            self.app.action_log.commit()
            self._project.pipeline.commit_timeline()

            if not self.draggingElement:
                self.draggingElement = bClip.ui
                self._on_layer = bLayer

            self._createdClips = True

        return True

    def __dragMotionCb(self, unused_widget, context, x, y, timestamp):
        target = self.drag_dest_find_target(context, None)
        if not self.dropDataReady:
            # We don't know yet the details of what's being dragged.
            # Ask for the details.
            self.drag_get_data(context, target, timestamp)
        else:
            if not self.__createClips(x, y):
                # The clips are already created.
                self.__dragUpdate(self, x, y)
        Gdk.drag_status(context, Gdk.DragAction.COPY, timestamp)
        return True

    def __dragLeaveCb(self, unused_widget, unused_context, unused_timestamp):
        self.__unsetHoverSeparators()
        if self.draggingElement:
            self.__last_clips_on_leave = [(clip.get_layer(), clip)
                                          for clip in self.current_group.get_children(False)]
            self.dropDataReady = False
            if self._createdClips:
                clips = self.current_group.get_children(False)
                self.resetSelectionGroup()
                self.selection.setSelection([], SELECT)
                for clip in clips:
                    clip.get_layer().remove_clip(clip)
                self._project.pipeline.commit_timeline()
                self.app.action_log.commit()

            self.draggingElement = None
            self.__got_dragged = False
            self._createdClips = False
        else:
            self.cleanDropData()

    def cleanDropData(self):
        self.dropDataReady = False
        self.dropData = None
        self._createdClips = False

    def __dragDropCb(self, unused_widget, context, x, y, timestamp):
        # Same as in insertEnd: this value changes during insertion, snapshot
        # it
        zoom_was_fitted = self.parent.zoomed_fitted

        target = self.drag_dest_find_target(context, None).name()
        success = True
        self.cleanDropData()
        if target == URI_TARGET_ENTRY.target:
            if self.__last_clips_on_leave:
                self.app.action_log.begin("add clip")

                if self.__on_separators:
                    created_layer = self.__getDroppedLayer()
                else:
                    created_layer = None
                for layer, clip in self.__last_clips_on_leave:
                    if created_layer:
                        layer = created_layer
                    layer.add_clip(clip)

                if zoom_was_fitted:
                    self.parent._setBestZoomRatio()
                self.dragEnd()
        else:
            success = False

        Gtk.drag_finish(context, success, False, timestamp)
        return success

    def __dragDataReceivedCb(self, unused_widget, unused_context, unused_x,
                             unused_y, selection_data, unused_info, timestamp):
        data_type = selection_data.get_data_type().name()
        if not self.dropDataReady:
            self.__last_clips_on_leave = None
            if data_type == URI_TARGET_ENTRY.target:
                self.dropData = selection_data.get_uris()
                self.dropDataReady = True
            elif data_type == EFFECT_TARGET_ENTRY.target:
                # Dragging an effect from the Effect Library.
                factory_name = str(selection_data.get_data(), "UTF-8")
                self.dropData = factory_name
                self.dropDataReady = True

    # Handle layers
    def _layerAddedCb(self, timeline, bLayer):
        self._addLayer(bLayer)

    def moveLayer(self, bLayer, index):
        layers = self.bTimeline.get_layers()
        layer = layers.pop(bLayer.get_priority())
        layers.insert(index, layer)

        for i, layer in enumerate(layers):
            layer.set_priority(i)

        self._project.setModificationState(True)

    def _addLayer(self, bLayer):
        layer = Layer(bLayer, self)
        bLayer.ui = layer
        self._layers.append(layer)
        layer.connect("remove-me", self._removeLayerCb)

        control = LayerControls(bLayer, self.app)
        control.show_all()
        self.__layers_controls_vbox.pack_start(control, False, False, 0)
        bLayer.control_ui = control
        # Check the media types so the controls are set up properly.
        layer.checkMediaTypes()

        layer_widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        layer_widget.pack_start(layer.before_sep, False, False, 0)
        layer_widget.pack_start(layer, True, True, 0)
        layer_widget.pack_start(layer.after_sep, False, False, 0)
        layer_widget.show_all()
        self.__layers_vbox.pack_start(layer_widget, True, True, 0)

        bLayer.connect("notify::priority", self.__layerPriorityChangedCb)

    def _removeLayerCb(self, layer):
        self.bTimeline.remove_layer(layer.bLayer)

    def __layerPriorityChangedCb(self, bLayer, pspec):
        self.__resetLayersByPriority()

    def __resetLayersByPriority(self, reset=False):
        self._layers.sort(key=lambda layer: layer.bLayer.props.priority)
        self.debug("Reseting layers priorities")
        for i, layer in enumerate(self._layers):
            if reset:
                layer.bLayer.props.priority = i

            self.__layers_vbox.child_set_property(layer.get_parent(),
                                                  "position",
                                                  layer.bLayer.props.priority)

            self.__layers_controls_vbox.child_set_property(layer.bLayer.control_ui,
                                                           "position",
                                                           layer.bLayer.props.priority)

    def _removeLayer(self, bLayer):
        self.info("Removing layer: %s", bLayer.props.priority)
        self.__layers_vbox.remove(bLayer.ui.get_parent())
        self.__layers_controls_vbox.remove(bLayer.control_ui)
        bLayer.disconnect_by_func(self.__layerPriorityChangedCb)

        self._layers.remove(bLayer.ui)
        bLayer.ui.release()
        bLayer.ui = None
        bLayer.control_ui = None

        self.__resetLayersByPriority(True)

    def _layerRemovedCb(self, unused_bTimeline, bLayer):
        self._removeLayer(bLayer)

    # Interface Zoomable
    def zoomChanged(self):
        self.updatePosition()
        x = max(0, self.nsToPixel(self.__last_position))
        self.layout.move(self.__playhead, x, 0)
        self.queue_draw()

    def __getEditingMode(self):
        if not self.editing_context:
            is_handle = False
        else:
            is_handle = self.editing_context.edge != GES.Edge.EDGE_NONE

        parent = self.get_parent()
        if parent._shiftMask or parent._autoripple_active:
            return GES.EditMode.EDIT_RIPPLE
        if is_handle and parent._controlMask:
            return GES.EditMode.EDIT_ROLL
        elif is_handle:
            return GES.EditMode.EDIT_TRIM
        return GES.EditMode.EDIT_NORMAL

    def __layerGetSeps(self, bLayer, sep_name):
        return [getattr(bLayer.ui, sep_name), getattr(bLayer.control_ui, sep_name)]

    def __getLayerAt(self, y, prefer_bLayer=None, past_middle_when_adjacent=False):
        bLayers = self.bTimeline.get_layers()
        if y < 20:
            # The cursor is at the top, above the first layer.
            self.debug("Returning very first layer")
            bLayer = bLayers[0]
            return bLayer, self.__layerGetSeps(bLayer, "before_sep")

        # This means if an asset is dragged directly on a separator,
        # it will prefer the layer below the separator, if any.
        # Otherwise, it helps choosing a layer as close to prefer_bLayer
        # as possible when having an option (y is between two layers).
        prefer_after = True

        if past_middle_when_adjacent:
            index_preferred = prefer_bLayer.get_priority()
            height_preferred = prefer_bLayer.ui.get_allocation().height

        for i, bLayer in enumerate(bLayers):
            layer_rect = bLayer.ui.get_allocation()
            layer_y = layer_rect.y
            layer_height = layer_rect.height
            if layer_y <= y < layer_y + layer_height:
                # The cursor is exactly on bLayer.
                if past_middle_when_adjacent:
                    # Check if far enough from prefer_bLayer.
                    delta = index_preferred - bLayer.get_priority()
                    if (delta == 1 and y >= layer_y + height_preferred) or \
                            (delta == -1 and y < layer_y + layer_height - height_preferred):
                        # bLayer is adjacent to prefer_bLayer, but the cursor
                        # is not far enough to warrant a change.
                        return prefer_bLayer, []
                return bLayer, []

            separators = self.__layerGetSeps(bLayer, "after_sep")
            try:
                next_bLayer = bLayers[i + 1]
            except IndexError:
                # The cursor is below the last layer.
                self.debug("Returning very last layer")
                return bLayer, separators

            if bLayer == prefer_bLayer:
                # Choose a layer as close to prefer_bLayer as possible.
                prefer_after = False

            if layer_y + layer_height <= y < next_bLayer.ui.get_allocation().y:
                # The cursor is between this layer and the one below.
                separators.extend(self.__layerGetSeps(next_bLayer, "before_sep"))
                if prefer_after:
                    bLayer = next_bLayer
                self.debug("Returning layer %s, separators: %s", bLayer, separators)
                return bLayer, separators

    def __setHoverSeparators(self, separators):
        self.__on_separators = separators
        for sep in self.__on_separators:
            set_children_state_recurse(sep, Gtk.StateFlags.PRELIGHT)

    def __unsetHoverSeparators(self):
        for sep in self.__on_separators:
            unset_children_state_recurse(sep, Gtk.StateFlags.PRELIGHT)
        self.__on_separators = []

    def __dragUpdate(self, event_widget, x, y):
        if not self.draggingElement:
            return

        if self.__got_dragged is False:
            self.__got_dragged = True
            if self.__clickedHandle:
                edit_mode = GES.EditMode.EDIT_TRIM
                dragging_edge = self.__clickedHandle.edge
            else:
                edit_mode = GES.EditMode.EDIT_NORMAL
                dragging_edge = GES.Edge.EDGE_NONE

            self.editing_context = EditingContext(self.draggingElement.bClip,
                                                  self.bTimeline,
                                                  edit_mode,
                                                  dragging_edge,
                                                  None,
                                                  self.app.action_log)

        x, y = event_widget.translate_coordinates(self, x, y)
        x -= CONTROL_WIDTH
        x += self.hadj.get_value()
        y += self.vadj.get_value()

        mode = self.__getEditingMode()
        self.editing_context.setMode(mode)

        if self.editing_context.edge is GES.Edge.EDGE_END:
            position = self.pixelToNs(x)
        else:
            position = self.pixelToNs(x - self.__drag_start_x)

        self.__unsetHoverSeparators()
        self._on_layer, on_separators = self.__getLayerAt(y,
                                                          prefer_bLayer=self._on_layer)
        if (mode != GES.EditMode.EDIT_NORMAL or
                self.current_group.props.height > 1):
            # When dragging clips from more than one layer, do not allow
            # them to be dragged between layers to create a new layer.
            on_separators = []
        self.__setHoverSeparators(on_separators)

        priority = self._on_layer.props.priority
        self.editing_context.editTo(position, priority)

    def createLayer(self, priority):
        new_bLayer = GES.Layer.new()
        new_bLayer.props.priority = priority
        self.bTimeline.add_layer(new_bLayer)

        bLayers = self.bTimeline.get_layers()
        if priority < len(bLayers):
            for bLayer in bLayers:
                if bLayer == new_bLayer:
                    continue

                if bLayer.get_priority() >= priority:
                    bLayer.props.priority += 1
                    self.__layers_vbox.child_set_property(bLayer.ui.get_parent(),
                                                          "position",
                                                          bLayer.props.priority)

                    self.__layers_controls_vbox.child_set_property(bLayer.control_ui,
                                                                   "position",
                                                                   bLayer.props.priority)

        self.__layers_vbox.child_set_property(new_bLayer.ui.get_parent(),
                                              "position",
                                              new_bLayer.props.priority)

        self.__layers_controls_vbox.child_set_property(new_bLayer.control_ui,
                                                       "position",
                                                       new_bLayer.props.priority)

        return new_bLayer

    def __getDroppedLayer(self):
        """
        Create the layer for a clip dropped on a separator.
        """
        priority = self._on_layer.props.priority
        if self.__on_separators[0] == self._on_layer.ui.after_sep:
            priority = self._on_layer.props.priority + 1

        self.createLayer(max(0, priority))
        return self.bTimeline.get_layers()[priority]

    def dragEnd(self):
        if self.editing_context:
            self._snapEndedCb()

            if self.__on_separators and self.__got_dragged:
                layer = self.__getDroppedLayer()
                self.editing_context.editTo(self.editing_context.new_position,
                                            layer.get_priority())
            self.layout.props.width = self._timelineLengthInPixels()

            self.editing_context.finish()

        self.draggingElement = None
        self.__clickedHandle = None
        self.__got_dragged = False
        self.editing_context = None
        self.hideSnapBar()

        for layer in self.bTimeline.get_layers():
            layer.ui.checkMediaTypes()

        self.__unsetHoverSeparators()

        self.queue_draw()

    def __endMovingLayer(self):
        self._project.pipeline.commit_timeline()
        self.__moving_layer = None


class TimelineContainer(Gtk.Grid, Zoomable, Loggable):

    """
    Container for zoom box, ruler, timeline, scrollbars and toolbar.
    """

    def __init__(self, instance):
        Zoomable.__init__(self)
        Gtk.Grid.__init__(self)
        Loggable.__init__(self)

        self.app = instance
        self._settings = self.app.settings
        self._autoripple_active = self._settings.timelineAutoRipple
        self._shiftMask = False
        self._controlMask = False

        # Whether the entire content is in the timeline view, in which case
        # it should be kept that way if it makes sense.
        self.zoomed_fitted = True

        self._projectmanager = None
        self._project = None
        self.bTimeline = None
        self.__copiedGroup = None

        self._createUi()
        self._createActions()

        self._settings.connect("edgeSnapDeadbandChanged",
                               self._snapDistanceChangedCb)
        self.setProjectManager(self.app.project_manager)

    # Public API

    def switchProxies(self, asset):
        proxy = asset.props.proxy
        unproxy = False

        if not proxy:
            unproxy = True
            proxy_uri = self.app.proxy_manager.getProxyUri(asset)
            proxy = GES.Asset.request(GES.UriClip,
                                      proxy_uri)
            if not proxy:
                self.debug("proxy_uri: %s does not have an asset associated",
                           proxy_uri)
                return

        layers = self.bTimeline.get_layers()
        for layer in layers:
            for clip in layer.get_clips():
                if unproxy:
                    if clip.get_asset() == proxy:
                        clip.set_asset(asset)
                elif clip.get_asset() == proxy.get_proxy_target():
                    clip.set_asset(proxy)
        self._project.pipeline.commit_timeline()

    def insertAssets(self, assets, position=None):
        """
        Add assets to the timeline and create clips on the longest layer.
        """
        layer = self._getLongestLayer()
        self._insertClipsAndAssets(assets, position, layer)

    def insertClips(self, clips, position=None):
        """
        Add clips to the timeline on the first layer.
        """
        layers = self._getLayers()
        layer = layers[0]
        self._insertClipsAndAssets(clips, position, layer)

    def _insertClipsAndAssets(self, objs, position, layer):
        if self.bTimeline is None:
            raise TimelineError("No bTimeline set, this is a bug")

        # We need to snapshot this value, because we only do the zoom fit at the
        # end of clip insertion, but inserting multiple clips eventually changes
        # the value of self.zoomed_fitted as clips get progressively
        # inserted...
        zoom_was_fitted = self.zoomed_fitted

        initial_position = self.__getInsertPosition(position)
        clip_position = initial_position

        self.app.action_log.begin("add asset")
        for obj in objs:
            if isinstance(obj, GES.Clip):
                obj.set_start(clip_position)
                layer.add_clip(obj)
                duration = obj.get_duration()
            elif isinstance(obj, GES.Asset):
                if obj.is_image():
                    duration = self.app.settings.imageClipLength * \
                        Gst.SECOND / 1000.0
                else:
                    duration = obj.get_duration()

                layer.add_asset(obj,
                                start=clip_position,
                                inpoint=0,
                                duration=duration,
                                track_types=obj.get_supported_formats())
            else:
                raise TimelineError("Cannot insert: %s" % type(obj))
            clip_position += duration
        self.app.action_log.commit()
        self._project.pipeline.commit_timeline()

        if zoom_was_fitted:
            self._setBestZoomRatio()
        else:
            self.scrollToPixel(Zoomable.nsToPixel(initial_position))

    def __getInsertPosition(self, position):
        if position is None:
            return self._project.pipeline.getPosition()
        if position < 0:
            return self.bTimeline.props.duration
        return position

    def purgeAsset(self, asset_id):
        """Remove all instances of an asset from the timeline."""
        layers = self.bTimeline.get_layers()
        for layer in layers:
            for clip in layer.get_clips():
                if asset_id == clip.get_id():
                    layer.remove_clip(clip)
        self._project.pipeline.commit_timeline()

    def setProjectManager(self, projectmanager):
        if self._projectmanager is not None:
            self._projectmanager.disconnect_by_func(self._projectChangedCb)

        self._projectmanager = projectmanager

        if projectmanager is not None:
            projectmanager.connect(
                "new-project-created", self._projectCreatedCb)
            projectmanager.connect(
                "new-project-loaded", self._projectChangedCb)

    def zoomFit(self):
        self.app.write_action("zoom-fit", {"optional-action-type": True})

        self._setBestZoomRatio(allow_zoom_in=True)
        self.hadj.set_value(0)

    def scrollToPixel(self, x):
        if x > self.hadj.props.upper:
            # We can't scroll yet, because the canvas needs to be updated
            GLib.idle_add(self._scrollToPixel, x)
        else:
            self._scrollToPixel(x)

    def setProject(self, project):
        self._project = project
        if self._project:
            self._project.connect("rendering-settings-changed",
                                  self._renderingSettingsChangedCb)
            self.bTimeline = project.timeline
        else:
            self.bTimeline = None

        self.timeline.setProject(self._project)
        self.timeline.selection.connect(
            "selection-changed", self._selectionChangedCb)

    def updateActions(self):
        selection_non_empty = bool(self.timeline.selection)
        self.delete_action.set_enabled(selection_non_empty)
        self.group_action.set_enabled(selection_non_empty)
        self.ungroup_action.set_enabled(selection_non_empty)
        self.copy_action.set_enabled(selection_non_empty)
        can_paste = bool(self.__copiedGroup)
        self.paste_action.set_enabled(can_paste)
        self.align_action.set_enabled(selection_non_empty)
        self.keyframe_action.set_enabled(selection_non_empty)

    # Internal API

    def _createUi(self):
        self.zoomBox = ZoomBox(self)

        self.timeline = Timeline(self, self.app)
        self.hadj = self.timeline.layout.get_hadjustment()
        self.vadj = self.timeline.layout.get_vadjustment()

        vscrollbar = Gtk.VScrollbar(adjustment=self.vadj)
        hscrollbar = Gtk.HScrollbar(adjustment=self.hadj)

        self.ruler = ScaleRuler(self, self.hadj)
        self.ruler.props.hexpand = True
        self.ruler.setProjectFrameRate(24.)
        self.ruler.hide()

        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "timelinetoolbar.ui"))
        self.toolbar = builder.get_object("timeline_toolbar")
        self.toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_INLINE_TOOLBAR)
        self.toolbar.get_accessible().set_name("timeline toolbar")

        self.gapless_button = builder.get_object("gapless_button")
        self.gapless_button.set_active(self._autoripple_active)

        alter_style_class(
            ".%s.trough" % Gtk.STYLE_CLASS_SCROLLBAR, vscrollbar,
            "border: alpha (@base_color, 0.0); background: alpha (@base_color, 0.0);")
        alter_style_class(
            ".%s.trough" % Gtk.STYLE_CLASS_SCROLLBAR, hscrollbar,
            "border: alpha (@base_color, 0.0); background: alpha (@base_color, 0.0);")

        self.attach(self.zoomBox, 0, 0, 1, 1)
        self.attach(self.ruler, 1, 0, 1, 1)
        self.attach(self.timeline, 0, 1, 2, 1)
        self.attach(vscrollbar, 2, 1, 1, 1)
        self.attach(hscrollbar, 1, 2, 1, 1)
        self.attach(self.toolbar, 3, 1, 1, 1)

        min_height = (self.ruler.get_size_request()[1] +
                      (EXPANDED_SIZE + SPACING) * 2 +
                      # Some more.
                      EXPANDED_SIZE)
        self.set_size_request(-1, min_height)
        self.set_margin_top(SPACING)

        self.show_all()

    def enableKeyboardAndMouseEvents(self):
        self.info("Unblocking timeline mouse and keyboard signals")
        self.timeline.disconnect_by_func(self._ignoreAllEventsCb)

    def disableKeyboardAndMouseEvents(self):
        """
        A safety measure to prevent interacting with the timeline
        """
        self.info("Blocking timeline mouse and keyboard signals")
        self.timeline.connect("event", self._ignoreAllEventsCb)

    def _ignoreAllEventsCb(self, *unused_args):
        return True

    def _getLayers(self):
        """
        Get the layers of the timeline.

        Makes sure there is at least one layer in the timeline.

        @rtype: list of GES.Layer
        """
        layers = self.bTimeline.get_layers()
        if not layers:
            layer = GES.Layer()
            layer.props.auto_transition = True
            self.bTimeline.add_layer(layer)
            return [layer]
        return layers

    def _getLongestLayer(self):
        """
        Return the longest layer.
        """
        layers = self._getLayers()
        if len(layers) == 1:
            return layers[0]
        # Create a list of (layer_length, layer) tuples.
        layer_lengths = [(max([(clip.get_start() + clip.get_duration()) for clip in layer.get_clips()] or [0]), layer)
                         for layer in layers]
        # Easily get the longest.
        unused_longest_time, longest_layer = max(layer_lengths)
        return longest_layer

    def _createActions(self):
        # The actions below are all added to this action group and they
        # are accessible only to the self.timeline.layout and self.toolbar
        # widgets (and their children) using the "timeline" prefix.
        # When the action for an accelerator is searched, due to the "timeline"
        # prefix, the accelerators work only when the focus is on one of these
        # two widgets: the layout with the layers representation (excluding the
        # controls) and the timeline toolbar.
        group = Gio.SimpleActionGroup()
        self.timeline.layout.insert_action_group("timeline", group)
        self.toolbar.insert_action_group("timeline", group)

        self.zoom_in_action = Gio.SimpleAction.new("zoom_in", None)
        self.zoom_in_action.connect("activate", self._zoomInCb)
        group.add_action(self.zoom_in_action)
        self.app.add_accelerator("<Control>plus", "timeline.zoom_in", None)
        self.app.add_accelerator("<Control>equal", "timeline.zoom_in", None)
        self.app.add_accelerator("<Control>KP_Add", "timeline.zoom_in", None)

        self.zoom_out_action = Gio.SimpleAction.new("zoom_out", None)
        self.zoom_out_action.connect("activate", self._zoomOutCb)
        group.add_action(self.zoom_out_action)
        self.app.add_accelerator("<Control>minus", "timeline.zoom_out", None)
        self.app.add_accelerator("<Control>KP_Subtract", "timeline.zoom_out", None)

        self.zoom_fit_action = Gio.SimpleAction.new("zoom_fit", None)
        self.zoom_fit_action.connect("activate", self._zoomFitCb)
        group.add_action(self.zoom_fit_action)
        self.app.add_accelerator("<Control>0", "timeline.zoom_fit", None)

        # Clips actions.
        self.delete_action = Gio.SimpleAction.new("delete_selected_clips", None)
        self.delete_action.connect("activate", self._deleteSelected)
        group.add_action(self.delete_action)
        self.app.add_accelerator("Delete", "timeline.delete_selected_clips", None)

        self.group_action = Gio.SimpleAction.new("group_selected_clips", None)
        self.group_action.connect("activate", self._groupSelected)
        group.add_action(self.group_action)
        self.app.add_accelerator("<Control>g", "timeline.group_selected_clips", None)

        self.ungroup_action = Gio.SimpleAction.new("ungroup_selected_clips", None)
        self.ungroup_action.connect("activate", self._ungroupSelected)
        group.add_action(self.ungroup_action)
        self.app.add_accelerator("<Shift><Control>g", "timeline.ungroup_selected_clips", None)

        self.copy_action = Gio.SimpleAction.new("copy_selected_clips", None)
        self.copy_action.connect("activate", self.__copyClipsCb)
        group.add_action(self.copy_action)
        self.app.add_accelerator("<Control>c", "timeline.copy_selected_clips", None)

        self.paste_action = Gio.SimpleAction.new("paste_clips", None)
        self.paste_action.connect("activate", self.__pasteClipsCb)
        group.add_action(self.paste_action)
        self.app.add_accelerator("<Control>v", "timeline.paste_clips", None)

        self.align_action = Gio.SimpleAction.new("align_selected_clips", None)
        self.align_action.connect("activate", self._alignSelectedCb)
        group.add_action(self.align_action)
        self.app.add_accelerator("<Shift><Control>a", "timeline.align_selected_clips", None)

        self.gapless_action = Gio.SimpleAction.new("toggle_gapless_mode", None)
        self.gapless_action.connect("activate", self._gaplessmodeToggledCb)
        group.add_action(self.gapless_action)

        # Playhead actions.
        self.play_action = Gio.SimpleAction.new("play", None)
        self.play_action.connect("activate", self._playPauseCb)
        group.add_action(self.play_action)
        self.app.add_accelerator("space", "timeline.play", None)

        self.split_action = Gio.SimpleAction.new("split_clips", None)
        self.split_action.connect("activate", self._splitCb)
        group.add_action(self.split_action)
        self.app.add_accelerator("S", "timeline.split_clips", None)
        self.split_action.set_enabled(True)

        self.keyframe_action = Gio.SimpleAction.new("keyframe_selected_clips", None)
        self.keyframe_action.connect("activate", self._keyframeCb)
        group.add_action(self.keyframe_action)
        self.app.add_accelerator("K", "timeline.keyframe_selected_clips", None)

    def _setBestZoomRatio(self, allow_zoom_in=False):
        """
        Set the zoom level so that the entire timeline is in view.
        """
        ruler_width = self.ruler.get_allocation().width
        duration = 0 if not self.bTimeline else self.bTimeline.get_duration()
        if not duration:
            return

        # Add Gst.SECOND - 1 to the timeline duration to make sure the
        # last second of the timeline will be in view.
        timeline_duration = duration + Gst.SECOND - 1
        timeline_duration_s = int(timeline_duration / Gst.SECOND)
        self.debug(
            "Adjusting zoom for a timeline duration of %s secs", timeline_duration_s)

        ideal_zoom_ratio = float(ruler_width) / timeline_duration_s
        nearest_zoom_level = Zoomable.computeZoomLevel(ideal_zoom_ratio)
        if nearest_zoom_level >= Zoomable.getCurrentZoomLevel():
            # This means if we continue we'll zoom in.
            if not allow_zoom_in:
                # For example when the user zoomed out and is adding clips
                # to the timeline, zooming in would be confusing.
                self.log(
                    "Zoom not changed because the entire timeline is already visible")

                return

        Zoomable.setZoomLevel(nearest_zoom_level)
        self.bTimeline.set_snapping_distance(
            Zoomable.pixelToNs(self._settings.edgeSnapDeadband))

        # Only do this at the very end, after updating the other widgets.
        self.log("Setting 'zoomed_fitted' to True")
        self.zoomed_fitted = True

    def scroll_left(self):
        # This method can be a callback for our events, or called by ruler.py
        self.hadj.set_value(self.hadj.get_value() -
                            self.hadj.props.page_size ** (2.0 / 3.0))

    def scroll_right(self):
        # This method can be a callback for our events, or called by ruler.py
        self.hadj.set_value(self.hadj.get_value() +
                            self.hadj.props.page_size ** (2.0 / 3.0))

    def scroll_up(self):
        self.vadj.set_value(self.vadj.get_value() -
                            self.vadj.props.page_size ** (2.0 / 3.0))

    def scroll_down(self):
        self.vadj.set_value(self.vadj.get_value() +
                            self.vadj.props.page_size ** (2.0 / 3.0))

    def _scrollToPixel(self, x):
        self.log("Scroll to: %s %s %s", x, self.hadj.props.lower, self.hadj.props.upper)
        if x > self.hadj.props.upper:
            self.warning(
                "Position %s is bigger than the hscrollbar's upper bound (%s) - is the position really in pixels?",
                x, self.hadj.props.upper)
        elif x < self.hadj.props.lower:
            self.warning(
                "Position %s is smaller than the hscrollbar's lower bound (%s)",
                x, self.hadj.props.lower)

        self.hadj.set_value(x)

        self.timeline.updatePosition()
        self.timeline.queue_draw()
        return False

    def _deleteSelected(self, unused_action, unused_parameter):
        if self.bTimeline:
            self.app.action_log.begin("delete clip")

            for clip in self.timeline.selection:
                layer = clip.get_layer()
                if isinstance(clip, GES.TransitionClip):
                    continue
                layer.remove_clip(clip)

            self._project.pipeline.commit_timeline()
            self.app.action_log.commit()

            self.timeline.selection.setSelection([], SELECT)

    def _ungroupSelected(self, unused_action, unused_parameter):
        if not self.bTimeline:
            self.info("No bTimeline set yet!")
            return

        self.app.action_log.begin("ungroup")

        for obj in self.timeline.selection:
            toplevel = obj.get_toplevel_parent()
            if toplevel == self.timeline.current_group:
                for child in toplevel.get_children(False):
                    child.ungroup(False)

        self.timeline.resetSelectionGroup()
        self.timeline.selection.setSelection([], SELECT)

        self.app.action_log.commit()
        self._project.pipeline.commit_timeline()

    def _groupSelected(self, unused_action, unused_parameter):
        if not self.bTimeline:
            self.info("No timeline set yet?")
            return

        self.app.action_log.begin("group")
        containers = set()
        new_group = None
        for obj in self.timeline.selection:
            toplevel = obj.get_toplevel_parent()
            if toplevel == self.timeline.current_group:
                for child in toplevel.get_children(False):
                    containers.add(child)
                toplevel.ungroup(False)
            else:
                containers.add(toplevel)

        if containers:
            new_group = GES.Container.group(list(containers))

        self.timeline.resetSelectionGroup()

        if new_group:
            self.timeline.current_group.add(new_group)

        self._project.pipeline.commit_timeline()
        self.app.action_log.commit()

    def __copyClipsCb(self, unused_action, unused_parameter):
        if self.timeline.current_group:
            self.__copiedGroup = self.timeline.current_group.copy(True)
            self.updateActions()

    def __pasteClipsCb(self, unused_action, unused_parameter):
        if self.__copiedGroup:
            save = self.__copiedGroup.copy(True)
            position = self._project.pipeline.getPosition()
            self.__copiedGroup.paste(position)
            self.__copiedGroup = save
            self._project.pipeline.commit_timeline()

    def _alignSelectedCb(self, unused_action, unused_parameter):
        if not self.bTimeline:
            self.error(
                "Trying to use the autoalign feature with an empty timeline")
            return

        progress_dialog = AlignmentProgressDialog(self.app)
        progress_dialog.window.show()
        self.app.action_log.begin("align")

        def alignedCb():  # Called when alignment is complete
            self.app.action_log.commit()
            self._project.pipeline.commit_timeline()
            progress_dialog.window.destroy()

        auto_aligner = AutoAligner(self.timeline.selection, alignedCb)
        try:
            progress_meter = auto_aligner.start()
            progress_meter.addWatcher(progress_dialog.updatePosition)
        except Exception as e:
            self.error("Could not start the autoaligner: %s", e)
            progress_dialog.window.destroy()

    def _splitCb(self, unused_action, unused_parameter):
        """
        If clips are selected, split them at the current playhead position.
        Otherwise, split all clips at the playhead position.
        """
        self.app.action_log.begin("split clip")
        self._splitElements(self.timeline.selection.selected)
        self.app.action_log.commit()

        self.timeline.hideSnapBar()
        self._project.pipeline.commit_timeline()

    def _splitElements(self, clips=None):
        splitting_selection = clips is not None
        if clips is None:
            clips = []
            for layer in self.timeline.bTimeline.get_layers():
                clips.extend(layer.get_clips())

        position = self._project.pipeline.getPosition()
        splitted = False
        for clip in clips:
            start = clip.get_start()
            end = start + clip.get_duration()
            if start < position and end > position:
                clip.get_layer().splitting_object = True

                self.app.write_action("split-clip", {
                    "clip-name": clip.get_name(),
                    "position": float(position / Gst.SECOND)})

                clip.split(position)
                clip.get_layer().splitting_object = False
                splitted = True

        if not splitted and splitting_selection:
            self._splitElements()

    def _keyframeCb(self, unused_action, unused_parameter):
        """
        Add or remove a keyframe at the current position of the selected clip.
        """
        selected = self.timeline.selection.getSelectedTrackElements()

        for obj in selected:
            keyframe_exists = False
            position = self._project.pipeline.getPosition()
            position_in_obj = (position - obj.props.start) + obj.props.in_point
            interpolators = obj.getInterpolators()
            for value in interpolators:
                interpolator = obj.getInterpolator(value)
                keyframes = interpolator.getInteriorKeyframes()
                for kf in keyframes:
                    if kf.getTime() == position_in_obj:
                        keyframe_exists = True
                        self.app.action_log.begin("remove volume point")
                        interpolator.removeKeyframe(kf)
                        self.app.action_log.commit()
                if keyframe_exists is False:
                    self.app.action_log.begin("add volume point")
                    interpolator.newKeyframe(position_in_obj)
                    self.app.action_log.commit()

    def _playPauseCb(self, unused_action, unused_parameter):
        self._project.pipeline.togglePlayback()

    def transposeXY(self, x, y):
        height = self.ruler.get_allocation().height
        x += self.timeline.get_scroll_point().x
        return x - CONTROL_WIDTH, y - height

    # Zoomable

    def zoomChanged(self):
        if self.bTimeline:
            # zoomChanged might be called various times before the UI is ready
            self.bTimeline.set_snapping_distance(
                Zoomable.pixelToNs(self._settings.edgeSnapDeadband))
        self.zoomed_fitted = False

    # Gtk widget virtual methods

    def sendFakeEvent(self, event):
        self.info("Faking %s", event)
        if event.type == Gdk.EventType.KEY_PRESS:
            self.do_key_press_event(event)
        elif event.type == Gdk.EventType.KEY_RELEASE:
            self.do_key_release_event(event)

    def do_key_press_event(self, event):
        # This is used both for changing the selection modes and for affecting
        # the seek keyboard shortcuts further below
        if event.keyval == Gdk.KEY_Shift_L:
            self._shiftMask = True
        elif event.keyval == Gdk.KEY_Control_L:
            self._controlMask = True

        # Now the second (independent) part: framestepping and seeking
        # shortcuts
        if event.keyval == Gdk.KEY_Left:
            if self._shiftMask:
                self._project.pipeline.seekRelative(0 - Gst.SECOND)
            else:
                self._project.pipeline.stepFrame(self._framerate, -1)
            self.timeline.scrollToPlayhead(align=Gtk.Align.CENTER, when_not_in_view=True)
            return True
        elif event.keyval == Gdk.KEY_Right:
            if self._shiftMask:
                self._project.pipeline.seekRelative(Gst.SECOND)
            else:
                self._project.pipeline.stepFrame(self._framerate, 1)
            self.timeline.scrollToPlayhead(align=Gtk.Align.CENTER, when_not_in_view=True)
            return True
        return False

    def do_key_release_event(self, event):
        if event.keyval == Gdk.KEY_Shift_L:
            self._shiftMask = False
        elif event.keyval == Gdk.KEY_Control_L:
            self._controlMask = False

    def do_focus_in_event(self, unused_event):
        self.log("Timeline has grabbed focus")
        self.updateActions()

    def do_focus_out_event(self, unused_event):
        self.log("Timeline has lost focus")
        self.updateActions()

    # Callbacks
    def _renderingSettingsChangedCb(self, project, item, value):
        """
        Called when any Project metadata changes, we filter out the one
        we are interested in.

        if @item is None, it mean we called it ourself, and want to force
        getting the project videorate value
        """
        if item == "videorate" or item is None:
            if value is None:
                value = project.videorate
            self._framerate = value

            self.ruler.setProjectFrameRate(self._framerate)

        if item == "width" or item == "height" or item == "videorate":
            project.update_restriction_caps()

    def _snapDistanceChangedCb(self, unused_settings):
        if self.bTimeline:
            self.bTimeline.set_snapping_distance(
                Zoomable.pixelToNs(self._settings.edgeSnapDeadband))

    def _projectChangedCb(self, unused_app, project, unused_fully_loaded):
        """
        When a project is loaded, we connect to its pipeline
        """
        assert self._project is project
        if self._project:
            self.ruler.setPipeline(self._project.pipeline)

            self.ruler.setProjectFrameRate(self._project.videorate)
            self.ruler.zoomChanged()

            self._renderingSettingsChangedCb(self._project, None, None)
            self._setBestZoomRatio()
            if self.bTimeline:
                self.bTimeline.set_snapping_distance(
                    Zoomable.pixelToNs(self._settings.edgeSnapDeadband))

    def _projectCreatedCb(self, unused_app, project):
        """
        When a project is created, we connect to it timeline
        """
        if self._project:
            self._project.disconnect_by_func(self._renderingSettingsChangedCb)
            try:
                self.timeline._pipeline.disconnect_by_func(
                    self.timeline.positionCb)
            except AttributeError:
                pass
            except TypeError:
                pass  # We were not connected no problem

            self.timeline._pipeline = None

        self.setProject(project)

    def _zoomInCb(self, unused_action, unused_parameter):
        Zoomable.zoomIn()

    def _zoomOutCb(self, unused_action, unused_parameter):
        Zoomable.zoomOut()

    def _zoomFitCb(self, unused_action, unused_parameter):
        self.zoomFit()

    def _selectionChangedCb(self, selection):
        """
        The selected clips on the timeline have changed.
        """
        self.updateActions()

    def _gaplessmodeToggledCb(self, unused_action, unused_parameter):
        self._autoripple_active = self.gapless_button.get_active()
        self.info("Automatic ripple: %s", self._autoripple_active)
        self._settings.timelineAutoRipple = self._autoripple_active
