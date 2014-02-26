# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       pitivi/timeline/elements.py
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

"""
Convention throughout this file:
Every GES element which name could be mistaken with a UI element
is prefixed with a little b, example : bTimeline
"""

import cairo
import math
import os
from datetime import datetime

import weakref

from gi.repository import Clutter, Gtk, GtkClutter, Cogl, GES, Gdk, Gst, GstController
from pitivi.utils.timeline import Zoomable, EditingContext, SELECT, UNSELECT, SELECT_ADD, Selected
from previewers import AudioPreviewer, VideoPreviewer

import pitivi.configure as configure
from pitivi.utils.ui import EXPANDED_SIZE, SPACING, KEYFRAME_SIZE, CONTROL_WIDTH, create_cogl_color

# Colors for keyframes and clips (RGBA)
KEYFRAME_LINE_COLOR = (237, 212, 0, 255)  # "Tango" yellow
KEYFRAME_NORMAL_COLOR = Clutter.Color.new(0, 0, 0, 200)
KEYFRAME_SELECTED_COLOR = Clutter.Color.new(200, 200, 200, 200)
CLIP_SELECTED_OVERLAY_COLOR = Clutter.Color.new(60, 60, 60, 100)
GHOST_CLIP_COLOR = Clutter.Color.new(255, 255, 255, 50)
TRANSITION_COLOR = create_cogl_color(35, 85, 125, 125)  # light blue

BORDER_NORMAL_COLOR = create_cogl_color(100, 100, 100, 255)
BORDER_SELECTED_COLOR = create_cogl_color(200, 200, 10, 255)

NORMAL_CURSOR = Gdk.Cursor.new(Gdk.CursorType.LEFT_PTR)
DRAG_CURSOR = Gdk.Cursor.new(Gdk.CursorType.HAND1)
DRAG_LEFT_HANDLEBAR_CURSOR = Gdk.Cursor.new(Gdk.CursorType.LEFT_SIDE)
DRAG_RIGHT_HANDLEBAR_CURSOR = Gdk.Cursor.new(Gdk.CursorType.RIGHT_SIDE)


class RoundedRectangle(Clutter.Actor):
    """
    Custom actor used to draw a rectangle that can have rounded corners
    """
    __gtype_name__ = 'RoundedRectangle'

    def __init__(self, width, height, arc, step,
                 color=None, border_color=None, border_width=0):
        """
        Creates a new rounded rectangle
        """
        Clutter.Actor.__init__(self)

        self.props.width = width
        self.props.height = height

        self._arc = arc
        self._step = step
        self._border_width = border_width
        self._color = color
        self._border_color = border_color

    def do_paint(self):
        # Set a rectangle for the clipping
        Cogl.clip_push_rectangle(0, 0, self.props.width, self.props.height)

        if self._border_color:
            # draw the rectangle for the border which is the same size as the
            # object
            Cogl.path_round_rectangle(0, 0, self.props.width, self.props.height,
                                      self._arc, self._step)
            Cogl.path_round_rectangle(self._border_width, self._border_width,
                                      self.props.width - self._border_width,
                                      self.props.height - self._border_width,
                                      self._arc, self._step)
            Cogl.path_set_fill_rule(Cogl.PathFillRule.EVEN_ODD)
            Cogl.path_close()

            # set color to border color
            Cogl.set_source_color(self._border_color)
            Cogl.path_fill()

        if self._color:
            # draw the content with is the same size minus the width of the border
            # finish the clip
            Cogl.path_round_rectangle(self._border_width, self._border_width,
                                      self.props.width - self._border_width,
                                      self.props.height - self._border_width,
                                      self._arc, self._step)
            Cogl.path_close()

            # set the color of the filled area
            Cogl.set_source_color(self._color)
            Cogl.path_fill()

        Cogl.clip_pop()

    def get_color(self):
        return self._color

    def set_color(self, color):
        self._color = color
        self.queue_redraw()

    def get_border_width(self):
        return self._border_width

    def set_border_width(self, width):
        self._border_width = width
        self.queue_redraw()

    def set_border_color(self, color):
        self._border_color = color
        self.queue_redraw()


class Ghostclip(Clutter.Actor):
    """
    The concept of a ghostclip is to represent future actions without
    actually moving GESClips. They are created when the user wants
    to change a clip of layer, and when the user does a drag and drop
    from the media library.
    """
    def __init__(self, track_type, bElement=None):
        Clutter.Actor.__init__(self)
        self.track_type = track_type
        self.bElement = bElement
        self.set_background_color(GHOST_CLIP_COLOR)
        self.props.visible = False
        self.shouldCreateLayer = False

    def setNbrLayers(self, nbrLayers):
        self.nbrLayers = nbrLayers

    def setWidth(self, width):
        self.props.width = width

    def update(self, priority, y, isControlledByBrother):
        self.priority = priority
        # Only tricky part of the code, can be called by the linked track element.
        if priority < 0:
            return

        # Here we make it so the calculation is the same for audio and video.
        if self.track_type == GES.TrackType.AUDIO and not isControlledByBrother:
            y -= self.nbrLayers * (EXPANDED_SIZE + SPACING)

        # And here we take into account the fact that the pointer might actually be
        # on the other track element, meaning we have to offset it.
        if isControlledByBrother:
            if self.track_type == GES.TrackType.AUDIO:
                y += self.nbrLayers * (EXPANDED_SIZE + SPACING)
            else:
                y -= self.nbrLayers * (EXPANDED_SIZE + SPACING)

        # Would that be a new layer at the end or inserted ?
        if priority == self.nbrLayers or y % (EXPANDED_SIZE + SPACING) < SPACING:
            self.shouldCreateLayer = True
            self.set_size(self.props.width, SPACING)
            self.props.y = priority * (EXPANDED_SIZE + SPACING)
            if self.track_type == GES.TrackType.AUDIO:
                self.props.y += self.nbrLayers * (EXPANDED_SIZE + SPACING)
            self.props.visible = True
        else:
            self.shouldCreateLayer = False
            # No need to mockup on the same layer
            if self.bElement and priority == self.bElement.get_parent().get_layer().get_priority():
                self.props.visible = False
            # We would be moving to an existing layer.
            elif priority < self.nbrLayers:
                self.set_size(self.props.width, EXPANDED_SIZE)
                self.props.y = priority * (EXPANDED_SIZE + SPACING) + SPACING
                if self.track_type == GES.TrackType.AUDIO:
                    self.props.y += self.nbrLayers * (EXPANDED_SIZE + SPACING)
                self.props.visible = True

    def getLayerForY(self, y):
        if self.track_type == GES.TrackType.AUDIO:
            y -= self.nbrLayers * (EXPANDED_SIZE + SPACING)
        priority = int(y / (EXPANDED_SIZE + SPACING))

        return priority


class TrimHandle(Clutter.Texture):
    def __init__(self, timelineElement, isLeft):
        Clutter.Texture.__init__(self)

        self.isLeft = isLeft
        self.timelineElement = weakref.proxy(timelineElement)
        self.dragAction = Clutter.DragAction()

        self.set_from_file(os.path.join(configure.get_pixmap_dir(), "trimbar-normal.png"))
        self.set_size(-1, EXPANDED_SIZE)
        self.hide()
        self.set_reactive(True)

        self.add_action(self.dragAction)
        self.dragAction.connect("drag-begin", self._dragBeginCb)
        self.dragAction.connect("drag-end", self._dragEndCb)
        self.dragAction.connect("drag-progress", self._dragProgressCb)

        self.connect("enter-event", self._enterEventCb)
        self.connect("leave-event", self._leaveEventCb)

        self.timelineElement.connect("enter-event", self._elementEnterEventCb)
        self.timelineElement.connect("leave-event", self._elementLeaveEventCb)

    def cleanup(self):
        self.disconnect_by_func(self._enterEventCb)
        self.disconnect_by_func(self._leaveEventCb)
        self.timelineElement.disconnect_by_func(self._elementEnterEventCb)
        self.timelineElement.disconnect_by_func(self._elementLeaveEventCb)

    #Callbacks

    def _enterEventCb(self, unused_actor, unused_event):
        self.timelineElement.set_reactive(False)
        for elem in self.timelineElement.get_children():
            elem.set_reactive(False)
        self.set_reactive(True)

        self.set_from_file(os.path.join(configure.get_pixmap_dir(), "trimbar-focused.png"))
        if self.isLeft:
            self.timelineElement.timeline._container.embed.get_window().set_cursor(DRAG_LEFT_HANDLEBAR_CURSOR)
        else:
            self.timelineElement.timeline._container.embed.get_window().set_cursor(DRAG_RIGHT_HANDLEBAR_CURSOR)

    def _leaveEventCb(self, unused_actor, event):
        self.timelineElement.set_reactive(True)
        children = self.timelineElement.get_children()

        other_actor = self.timelineElement.timeline._container.stage.get_actor_at_pos(Clutter.PickMode.ALL, event.x, event.y)
        if other_actor not in children:
            self.timelineElement.hideHandles()

        for elem in children:
            elem.set_reactive(True)
        self.set_from_file(os.path.join(configure.get_pixmap_dir(), "trimbar-normal.png"))
        self.timelineElement.timeline._container.embed.get_window().set_cursor(NORMAL_CURSOR)

    def _elementEnterEventCb(self, unused_actor, unused_event):
        self.show()

    def _elementLeaveEventCb(self, unused_actor, unused_event):
        self.hide()

    def _dragBeginCb(self, unused_action, unused_actor, event_x, event_y, unused_modifiers):
        self.dragBeginStartX = event_x
        self.dragBeginStartY = event_y
        elem = self.timelineElement.bElement.get_parent()
        self.timelineElement.setDragged(True)

        if self.isLeft:
            edge = GES.Edge.EDGE_START
            self._dragBeginStart = self.timelineElement.bElement.get_parent().get_start()
        else:
            edge = GES.Edge.EDGE_END
            self._dragBeginStart = self.timelineElement.bElement.get_parent().get_duration() + \
                self.timelineElement.bElement.get_parent().get_start()

        self._context = EditingContext(elem,
                                       self.timelineElement.timeline.bTimeline,
                                       GES.EditMode.EDIT_TRIM,
                                       edge,
                                       None,
                                       self.timelineElement.timeline._container.app.action_log)

        self._context.connect("clip-trim", self.clipTrimCb)
        self._context.connect("clip-trim-finished", self.clipTrimFinishedCb)

    def _dragProgressCb(self, unused_action, unused_actor, delta_x, unused_delta_y):
        # We can't use delta_x here because it fluctuates weirdly.
        coords = self.dragAction.get_motion_coords()
        delta_x = coords[0] - self.dragBeginStartX
        new_start = self._dragBeginStart + Zoomable.pixelToNs(delta_x)

        self._context.setMode(self.timelineElement.timeline._container.getEditionMode(isAHandle=True))
        self._context.editTo(new_start, self.timelineElement.bElement.get_parent().get_layer().get_priority())
        return False

    def _dragEndCb(self, unused_action, unused_actor, unused_event_x, unused_event_y, unused_modifiers):
        self.timelineElement.setDragged(False)
        self._context.finish()

        self.timelineElement.set_reactive(True)
        for elem in self.timelineElement.get_children():
            elem.set_reactive(True)

        self.set_from_file(os.path.join(configure.get_pixmap_dir(), "trimbar-normal.png"))
        self.timelineElement.timeline._container.embed.get_window().set_cursor(NORMAL_CURSOR)

    def clipTrimCb(self, unused_TrimStartContext, tl_obj, position):
        # While a clip is being trimmed, ask the viewer to preview it
        self.timelineElement.timeline._container.app.gui.viewer.clipTrimPreview(tl_obj, position)

    def clipTrimFinishedCb(self, unused_TrimStartContext):
        # When a clip has finished trimming, tell the viewer to reset itself
        self.timelineElement.timeline._container.app.gui.viewer.clipTrimPreviewFinished()


class TimelineElement(Clutter.Actor, Zoomable):
    """
    @ivar bElement: the backend element.
    @type bElement: GES.TrackElement
    @ivar timeline: the containing graphic timeline.
    @type timeline: TimelineStage
    """

    def __init__(self, bElement, timeline):
        Zoomable.__init__(self)
        Clutter.Actor.__init__(self)

        self.timeline = timeline
        self.bElement = bElement
        self.bElement.selected = Selected()
        self.bElement.ui_element = weakref.proxy(self)
        self.track_type = self.bElement.get_track_type()  # This won't change
        self.isDragged = False
        self.lines = []
        self.keyframes = []
        self.keyframesVisible = False
        self.source = None
        self.keyframedElement = None
        self.rightHandle = None
        self.isSelected = False
        size = self.bElement.get_duration()

        self.background = self._createBackground()
        self.background.set_position(0, 0)
        self.add_child(self.background)

        self.preview = self._createPreview()
        self.add_child(self.preview)

        self.border = self._createBorder()
        self.add_child(self.border)

        self.marquee = self._createMarquee()
        self.add_child(self.marquee)

        self._createHandles()

        self._linesMarker = self._createMarker()
        self._keyframesMarker = self._createMarker()

        self._createGhostclip()

        self.update(True)
        self.set_reactive(True)

        self._createMixingKeyframes()

        self._connectToEvents()

    # Public API

    def set_size(self, width, height, ease):
        if ease:
            self.save_easing_state()
            self.set_easing_duration(600)
            self.background.save_easing_state()
            self.background.set_easing_duration(600)
            self.border.save_easing_state()
            self.border.set_easing_duration(600)
            self.preview.save_easing_state()
            self.preview.set_easing_duration(600)
            if self.rightHandle:
                self.rightHandle.save_easing_state()
                self.rightHandle.set_easing_duration(600)

        self.marquee.set_size(width, height)
        self.background.props.width = width
        self.background.props.height = height
        self.border.props.width = width
        self.border.props.height = height
        self.props.width = width
        self.props.height = height
        self.preview.set_size(width, height)
        if self.rightHandle:
            self.rightHandle.set_position(width - self.rightHandle.props.width, 0)

        if ease:
            self.background.restore_easing_state()
            self.border.restore_easing_state()
            self.preview.restore_easing_state()
            if self.rightHandle:
                self.rightHandle.restore_easing_state()
            self.restore_easing_state()

    def addKeyframe(self, value, timestamp):
        self.source.set(timestamp, value)
        self.updateKeyframes()

    def removeKeyframe(self, kf):
        self.source.unset(kf.value.timestamp)
        self.keyframes = sorted(self.keyframes, key=lambda keyframe: keyframe.value.timestamp)
        self.updateKeyframes()

    def showKeyframes(self, element, propname, isDefault=False):
        binding = element.get_control_binding(propname.name)
        if not binding:
            source = GstController.InterpolationControlSource()
            source.props.mode = GstController.InterpolationMode.LINEAR
            if not (element.set_control_source(source, propname.name, "direct")):
                print "There was something like a problem captain"
                return
            binding = element.get_control_binding(propname.name)

        self.binding = binding
        self.prop = propname
        self.keyframedElement = element
        self.source = self.binding.props.control_source

        if isDefault:
            self.default_prop = propname
            self.default_element = element

        self.keyframesVisible = True

        self.updateKeyframes()

    def hideKeyframes(self):
        for keyframe in self.keyframes:
            self.remove_child(keyframe)
        self.keyframes = []

        self.keyframesVisible = False

        if self.isSelected:
            self.showKeyframes(self.default_element, self.default_prop)

        self.drawLines()

    def setKeyframePosition(self, keyframe, value):
        x = self.nsToPixel(value.timestamp - self.bElement.props.in_point) - KEYFRAME_SIZE / 2
        y = EXPANDED_SIZE - (value.value * EXPANDED_SIZE) - KEYFRAME_SIZE / 2
        keyframe.set_position(x, y)

    def drawLines(self, line=None):
        for line_ in self.lines:
            if line_ != line:
                self.remove_child(line_)

        if line:
            self.lines = [line]
        else:
            self.lines = []

        lastKeyframe = None
        for keyframe in self.keyframes:
            if lastKeyframe and (not line or lastKeyframe != line.previousKeyframe):
                self._createLine(keyframe, lastKeyframe, None)
            elif lastKeyframe:
                self._createLine(keyframe, lastKeyframe, line)
            lastKeyframe = keyframe

    def updateKeyframes(self):
        if not self.source:
            return

        values = self.source.get_all()
        if len(values) < 2 and self.bElement.props.duration > 0:
            self.source.unset_all()
            val = float(self.prop.default_value) / (self.prop.maximum - self.prop.minimum)
            self.source.set(self.bElement.props.in_point, val)
            self.source.set(self.bElement.props.duration + self.bElement.props.in_point, val)

        for keyframe in self.keyframes:
            self.remove_child(keyframe)

        self.keyframes = []
        values = self.source.get_all()
        values_count = len(values)
        for i, value in enumerate(values):
            has_changeable_time = i > 0 and i < values_count - 1
            keyframe = self._createKeyframe(value, has_changeable_time)
            self.keyframes.append(keyframe)

        self.drawLines()

    def cleanup(self):
        Zoomable.__del__(self)
        self.disconnectFromEvents()

    def disconnectFromEvents(self):
        self.dragAction.disconnect_by_func(self._dragProgressCb)
        self.dragAction.disconnect_by_func(self._dragBeginCb)
        self.dragAction.disconnect_by_func(self._dragEndCb)
        self.remove_action(self.dragAction)
        self.bElement.selected.disconnect_by_func(self._selectedChangedCb)
        self.bElement.disconnect_by_func(self._durationChangedCb)
        self.bElement.disconnect_by_func(self._inpointChangedCb)
        self.disconnect_by_func(self._clickedCb)

    # private API

    def _createMarker(self):
        marker = Clutter.Actor()
        self.add_child(marker)
        return marker

    def update(self, ease):
        start = self.bElement.get_start()
        duration = self.bElement.get_duration()
        # The calculation of the duration assumes that the start is always
        # int(pixels_float). In that case, the rounding can add up and a pixel
        # might be lost if we ignore the start of the clip.
        size = self.nsToPixel(start + duration) - self.nsToPixel(start)
        # Avoid elements to become invisible.
        size = max(size, 1)
        self.set_size(size, EXPANDED_SIZE, ease)

    def setDragged(self, dragged):
        brother = self.timeline.findBrother(self.bElement)
        if brother:
            brother.isDragged = dragged
        self.isDragged = dragged

    def _createMixingKeyframes(self):
        if self.track_type == GES.TrackType.VIDEO:
            propname = "alpha"
        else:
            propname = "volume"

        for spec in self.bElement.list_children_properties():
            if spec.name == propname:
                self.showKeyframes(self.bElement, spec, isDefault=True)

        self.hideKeyframes()

    def _createKeyframe(self, value, has_changeable_time):
        keyframe = Keyframe(self, value, has_changeable_time)
        self.insert_child_above(keyframe, self._keyframesMarker)
        self.setKeyframePosition(keyframe, value)
        return keyframe

    def _createLine(self, keyframe, lastKeyframe, line):
        if not line:
            line = Line(self, keyframe, lastKeyframe)
            self.lines.append(line)
            self.insert_child_above(line, self._linesMarker)

        adj = self.nsToPixel(keyframe.value.timestamp - lastKeyframe.value.timestamp)
        opp = (lastKeyframe.value.value - keyframe.value.value) * EXPANDED_SIZE
        hyp = math.sqrt(adj ** 2 + opp ** 2)
        if hyp < 1:
            # line length would be less than one pixel
            return

        sinX = opp / hyp
        line.props.width = hyp
        line.props.height = KEYFRAME_SIZE
        line.props.rotation_angle_z = math.degrees(math.asin(sinX))
        line.props.x = self.nsToPixel(lastKeyframe.value.timestamp - self.bElement.props.in_point) - KEYFRAME_SIZE / 2
        line.props.y = EXPANDED_SIZE - (EXPANDED_SIZE * lastKeyframe.value.value) - KEYFRAME_SIZE / 2
        line.canvas.invalidate()

    def _createGhostclip(self):
        pass

    def _createBorder(self):
        border = RoundedRectangle(0, 0, 0, 0)
        border.bElement = self.bElement
        border.set_border_color(BORDER_NORMAL_COLOR)
        border.set_border_width(1)
        border.set_position(0, 0)
        return border

    def _createBackground(self):
        raise NotImplementedError()

    def _createHandles(self):
        pass

    def _createPreview(self):
        if isinstance(self.bElement, GES.AudioUriSource):
            previewer = AudioPreviewer(self.bElement, self.timeline)
            previewer.startLevelsDiscoveryWhenIdle()
            return previewer
        if isinstance(self.bElement, GES.VideoUriSource):
            return VideoPreviewer(self.bElement, self.timeline)
        # TODO: GES.AudioTransition, GES.VideoTransition, GES.ImageSource, GES.TitleSource
        return Clutter.Actor()

    def _createMarquee(self):
        marquee = Clutter.Actor()
        marquee.bElement = self.bElement
        marquee.set_background_color(CLIP_SELECTED_OVERLAY_COLOR)
        marquee.props.visible = False
        return marquee

    def _connectToEvents(self):
        self.dragAction = Clutter.DragAction()
        self.add_action(self.dragAction)
        self.dragAction.connect("drag-progress", self._dragProgressCb)
        self.dragAction.connect("drag-begin", self._dragBeginCb)
        self.dragAction.connect("drag-end", self._dragEndCb)
        self.bElement.selected.connect("selected-changed", self._selectedChangedCb)
        self.bElement.connect("notify::duration", self._durationChangedCb)
        self.bElement.connect("notify::in-point", self._inpointChangedCb)
        # We gotta go low-level cause Clutter.ClickAction["clicked"]
        # gets emitted after Clutter.DragAction["drag-begin"]
        self.connect("button-press-event", self._clickedCb)

    def _getLayerForY(self, y):
        if self.track_type == GES.TrackType.AUDIO:
            y -= self.nbrLayers * (EXPANDED_SIZE + SPACING)
        priority = int(y / (EXPANDED_SIZE + SPACING))
        return priority

    # Interface (Zoomable)

    def zoomChanged(self):
        self.update(True)
        if self.isSelected:
            self.updateKeyframes()

    # Callbacks

    def _clickedCb(self, action, actor):
        pass

    def _dragBeginCb(self, action, actor, event_x, event_y, modifiers):
        pass

    def _dragProgressCb(self, unused_action, unused_actor, unused_delta_x, unused_delta_y):
        return False

    def _dragEndCb(self, action, actor, event_x, event_y, modifiers):
        pass

    def _durationChangedCb(self, unused_element, unused_duration):
        if self.keyframesVisible:
            self.updateKeyframes()

    def _inpointChangedCb(self, unused_element, unused_inpoint):
        if self.keyframesVisible:
            self.updateKeyframes()

    def _selectedChangedCb(self, unused_selected, isSelected):
        self.isSelected = isSelected
        if not isSelected:
            self.hideKeyframes()
        self.marquee.props.visible = isSelected
        color = BORDER_SELECTED_COLOR if isSelected else BORDER_NORMAL_COLOR
        self.border.set_border_color(color)


class Gradient(Clutter.Actor):
    def __init__(self, rb, gb, bb, re, ge, be):
        """
        Creates a rectangle with a gradient. The first three parameters
        are the gradient's RGB values at the top, the last three params
        are the RGB values at the bottom.
        """
        Clutter.Actor.__init__(self)
        self.canvas = Clutter.Canvas()
        self.linear = cairo.LinearGradient(0, 0, 10, EXPANDED_SIZE)
        self.linear.add_color_stop_rgb(0, rb / 255., gb / 255., bb / 255.)
        self.linear.add_color_stop_rgb(1, re / 255., ge / 255., be / 255.)
        self.canvas.set_size(10, EXPANDED_SIZE)
        self.canvas.connect("draw", self._drawCb)
        self.set_content(self.canvas)
        self.canvas.invalidate()

    def _drawCb(self, unused_canvas, cr, unused_width, unused_height):
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_source(self.linear)
        cr.rectangle(0, 0, 10, EXPANDED_SIZE)
        cr.fill()


class Line(Clutter.Actor):
    """
    A cairo line used for keyframe curves.
    """
    def __init__(self, timelineElement, keyframe, lastKeyframe):
        Clutter.Actor.__init__(self)
        self.timelineElement = weakref.proxy(timelineElement)

        self.canvas = Clutter.Canvas()
        self.canvas.set_size(1000, KEYFRAME_SIZE)
        self.canvas.connect("draw", self._drawCb)
        self.set_content(self.canvas)
        self.set_reactive(True)

        self.gotDragged = False

        self.dragAction = Clutter.DragAction()
        self.add_action(self.dragAction)

        self.dragAction.connect("drag-begin", self._dragBeginCb)
        self.dragAction.connect("drag-end", self._dragEndCb)
        self.dragAction.connect("drag-progress", self._dragProgressCb)

        self.connect("button-release-event", self._clickedCb)
        self.connect("motion-event", self._motionEventCb)
        self.connect("enter-event", self._enterEventCb)
        self.connect("leave-event", self._leaveEventCb)

        self.previousKeyframe = lastKeyframe
        self.nextKeyframe = keyframe

    def _drawCb(self, unused_canvas, cr, width, unused_height):
        """
        This is where we actually create the line segments for keyframe curves.
        We draw multiple lines (one-third of the height each) to add a "shadow"
        around the actual line segment to improve visibility.
        """
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        # The "height budget" to draw line components = the tallest component...
        _max_height = KEYFRAME_SIZE

        # While normally all three lines would have an equal height,
        # I make the shadow lines be 1/2 (3px) instead of 1/3 (2px),
        # while keeping their 1/3 position... this softens them up.

        # Upper shadow/border:
        cr.set_source_rgba(0, 0, 0, 0.5)  # 50% transparent black color
        cr.move_to(0, _max_height / 3)
        cr.line_to(width, _max_height / 3)
        cr.set_line_width(_max_height / 3)  # Special case: fuzzy 3px
        cr.stroke()
        # Lower shadow/border:
        cr.set_source_rgba(0, 0, 0, 0.5)  # 50% transparent black color
        cr.move_to(0, _max_height * 2 / 3)
        cr.line_to(width, _max_height * 2 / 3)
        cr.set_line_width(_max_height / 3)  # Special case: fuzzy 3px
        cr.stroke()
        # Draw the actual line in the middle.
        # Do it last, so that it gets drawn on top and remains sharp.
        cr.set_source_rgba(*KEYFRAME_LINE_COLOR)
        cr.move_to(0, _max_height / 2)
        cr.line_to(width, _max_height / 2)
        cr.set_line_width(_max_height / 3)
        cr.stroke()

    def transposeXY(self, x, y):
        x -= self.timelineElement.props.x + CONTROL_WIDTH - self.timelineElement.timeline._scroll_point.x
        x += Zoomable.nsToPixel(self.timelineElement.bElement.props.in_point)
        y -= self.timelineElement.props.y
        return x, y

    def _ungrab(self):
        self.timelineElement.set_reactive(True)
        self.timelineElement.timeline._container.embed.get_window().set_cursor(NORMAL_CURSOR)

    def _clickedCb(self, unused_actor, event):
        if self.gotDragged:
            self.gotDragged = False
            return
        x, y = self.transposeXY(event.x, event.y)
        value = 1.0 - (y / EXPANDED_SIZE)
        value = max(0.0, value)
        value = min(1.0, value)
        timestamp = Zoomable.pixelToNs(x)
        self.timelineElement.addKeyframe(value, timestamp)

    def _enterEventCb(self, unused_actor, unused_event):
        self.timelineElement.set_reactive(False)
        self.timelineElement.timeline._container.embed.get_window().set_cursor(DRAG_CURSOR)

    def _leaveEventCb(self, unused_actor, unused_event):
        self._ungrab()

    def _motionEventCb(self, actor, event):
        pass

    def _dragBeginCb(self, unused_action, unused_actor, event_x, event_y, unused_modifiers):
        self.dragBeginStartX = event_x
        self.dragBeginStartY = event_y
        self.origY = self.props.y
        self.previousKeyframe.startDrag(event_x, event_y, self)
        self.nextKeyframe.startDrag(event_x, event_y, self)

    def _dragProgressCb(self, unused_action, unused_actor, unused_delta_x, delta_y):
        self.gotDragged = True
        coords = self.dragAction.get_motion_coords()
        delta_x = coords[0] - self.dragBeginStartX
        delta_y = coords[1] - self.dragBeginStartY

        self.previousKeyframe.updateValue(0, delta_y)
        self.nextKeyframe.updateValue(0, delta_y)

        return False

    def _dragEndCb(self, unused_action, unused_actor, unused_event_x, unused_event_y, unused_modifiers):
        self.previousKeyframe.endDrag()
        self.nextKeyframe.endDrag()
        if self.timelineElement.timeline.getActorUnderPointer() != self:
            self._ungrab()


class KeyframeMenu(GtkClutter.Actor):
    def __init__(self, keyframe):
        GtkClutter.Actor.__init__(self)
        self.keyframe = keyframe
        vbox = Gtk.VBox()

        button = Gtk.Button()
        button.set_label("Remove")
        button.connect("clicked", self._removeClickedCb)
        vbox.pack_start(button, False, False, False)

        self.get_widget().add(vbox)
        self.vbox = vbox
        self.vbox.hide()
        self.set_reactive(True)

    def show(self):
        GtkClutter.Actor.show(self)
        self.vbox.show_all()

    def hide(self):
        GtkClutter.Actor.hide(self)
        self.vbox.hide()

    def _removeClickedCb(self, unused_button):
        self.keyframe.remove()


class Keyframe(Clutter.Actor):
    """
    @ivar has_changeable_time: if False, it means this is an edge keyframe.
    @type has_changeable_time: bool
    """

    def __init__(self, timelineElement, value, has_changeable_time):
        Clutter.Actor.__init__(self)

        self.value = value
        self.timelineElement = weakref.proxy(timelineElement)
        self.has_changeable_time = has_changeable_time
        self.lastClick = datetime.now()

        self.set_size(KEYFRAME_SIZE, KEYFRAME_SIZE)
        self.set_background_color(KEYFRAME_NORMAL_COLOR)

        self.dragAction = Clutter.DragAction()
        self.add_action(self.dragAction)

        self.dragAction.connect("drag-begin", self._dragBeginCb)
        self.dragAction.connect("drag-end", self._dragEndCb)
        self.dragAction.connect("drag-progress", self._dragProgressCb)
        self.connect("enter-event", self._enterEventCb)
        self.connect("leave-event", self._leaveEventCb)
        self.connect("button-press-event", self._clickedCb)

        self.createMenu()
        self.dragProgressed = False
        self.set_reactive(True)

    def createMenu(self):
        self.menu = KeyframeMenu(self)
        self.timelineElement.timeline._container.stage.connect("button-press-event", self._stageClickedCb)
        self.timelineElement.timeline.add_child(self.menu)

    def _unselect(self):
        self.timelineElement.set_reactive(True)
        self.set_background_color(KEYFRAME_NORMAL_COLOR)
        self.timelineElement.timeline._container.embed.get_window().set_cursor(NORMAL_CURSOR)

    def remove(self):
        # Can't remove edge keyframes !
        if not self.has_changeable_time:
            return

        self.timelineElement.timeline.remove_child(self.menu)
        self._unselect()
        self.timelineElement.removeKeyframe(self)

    def _stageClickedCb(self, stage, event):
        actor = stage.get_actor_at_pos(Clutter.PickMode.REACTIVE, event.x, event.y)
        if actor != self.menu:
            self.menu.hide()

    def _clickedCb(self, unused_actor, event):
        if (event.modifier_state & Clutter.ModifierType.CONTROL_MASK):
            self.remove()
        elif (datetime.now() - self.lastClick).total_seconds() < 0.5:
            self.remove()

        self.lastClick = datetime.now()

    def _enterEventCb(self, unused_actor, unused_event):
        self.timelineElement.set_reactive(False)
        self.set_background_color(KEYFRAME_SELECTED_COLOR)
        self.timelineElement.timeline._container.embed.get_window().set_cursor(DRAG_CURSOR)

    def _leaveEventCb(self, unused_actor, unused_event):
        self._unselect()

    def startDrag(self, event_x, event_y, line=None):
        self.dragBeginStartX = event_x
        self.dragBeginStartY = event_y
        self.lastTs = self.value.timestamp
        self.valueStart = self.value.value
        self.tsStart = self.value.timestamp
        self.duration = self.timelineElement.bElement.props.duration
        self.inpoint = self.timelineElement.bElement.props.in_point
        self.start = self.timelineElement.bElement.props.start
        self.line = line

    def endDrag(self):
        if not self.dragProgressed and not self.line:
            timeline = self.timelineElement.timeline
            self.menu.set_position(self.timelineElement.props.x + self.props.x + 10, self.timelineElement.props.y + self.props.y + 10)
            self.menu.show()

        self.line = None

    def updateValue(self, delta_x, delta_y):
        newTs = self.tsStart + Zoomable.pixelToNs(delta_x)
        newValue = self.valueStart - (delta_y / EXPANDED_SIZE)

        # Don't overlap first and last keyframes.
        newTs = min(max(newTs, self.inpoint + 1), self.duration + self.inpoint - 1)

        newValue = min(max(newValue, 0.0), 1.0)

        if not self.has_changeable_time:
            newTs = self.lastTs

        self.timelineElement.source.unset(self.lastTs)
        if (self.timelineElement.source.set(newTs, newValue)):
            self.value = Gst.TimedValue()
            self.value.timestamp = newTs
            self.value.value = newValue
            self.lastTs = newTs

            self.timelineElement.setKeyframePosition(self, self.value)
            # Resort the keyframes list each time. Should be cheap as there should never be too much keyframes,
            # if optimization is needed, check if resorting is needed, should not be in 99 % of the cases.
            self.timelineElement.keyframes = sorted(self.timelineElement.keyframes, key=lambda keyframe: keyframe.value.timestamp)
            self.timelineElement.drawLines(self.line)
            # This will update the viewer. nifty.
            if not self.line:
                self.timelineElement.timeline._container.seekInPosition(newTs + self.start)

    def _dragBeginCb(self, unused_action, unused_actor, event_x, event_y, unused_modifiers):
        self.dragProgressed = False
        self.startDrag(event_x, event_y)

    def _dragProgressCb(self, unused_action, unused_actor, delta_x, delta_y):
        self.dragProgressed = True
        coords = self.dragAction.get_motion_coords()
        delta_x = coords[0] - self.dragBeginStartX
        delta_y = coords[1] - self.dragBeginStartY
        self.updateValue(delta_x, delta_y)
        return False

    def _dragEndCb(self, unused_action, unused_actor, unused_event_x, unused_event_y, unused_modifiers):
        self.endDrag()
        if self.timelineElement.timeline.getActorUnderPointer() != self:
            self._unselect()


class URISourceElement(TimelineElement):
    def __init__(self, bElement, timeline):
        TimelineElement.__init__(self, bElement, timeline)
        self.gotDragged = False

    # public API

    def hideHandles(self):
        self.rightHandle.hide()
        self.leftHandle.hide()

    # private API

    def _createGhostclip(self):
        self.ghostclip = Ghostclip(self.track_type, self.bElement)
        self.timeline.add_child(self.ghostclip)

    def _createHandles(self):
        self.leftHandle = TrimHandle(self, True)
        self.rightHandle = TrimHandle(self, False)

        self.leftHandle.set_position(0, 0)

        self.add_child(self.leftHandle)
        self.add_child(self.rightHandle)

    def _createBackground(self):
        if self.track_type == GES.TrackType.AUDIO:
            # Audio clips go from dark green to light green
            # (27, 46, 14, 255) to (73, 108, 33, 255)
            background = Gradient(27, 46, 14, 73, 108, 33)
        else:
            # Video clips go from almost black to gray
            # (15, 15, 15, 255) to (45, 45, 45, 255)
            background = Gradient(15, 15, 15, 45, 45, 45)
        background.bElement = self.bElement
        return background

    # Callbacks
    def _clickedCb(self, unused_action, unused_actor):
        #TODO : Let's be more specific, masks etc ..
        mode = SELECT
        if self.timeline._container._controlMask:
            if not self.bElement.selected:
                mode = SELECT_ADD
                self.timeline.current_group.add(self.bElement.get_toplevel_parent())
            else:
                self.timeline.current_group.remove(self.bElement.get_toplevel_parent())
                mode = UNSELECT
        elif not self.bElement.selected:
            GES.Container.ungroup(self.timeline.current_group, False)
            self.timeline.current_group = GES.Group()
            self.timeline.current_group.add(self.bElement.get_toplevel_parent())
            self.timeline._container.app.gui.switchContextTab(self.bElement)

        children = self.bElement.get_toplevel_parent().get_children(True)
        selection = filter(lambda elem: isinstance(elem, GES.Source), children)

        self.timeline.selection.setSelection(selection, mode)

        if self.keyframedElement:
            self.showKeyframes(self.keyframedElement, self.prop)

        return False

    def _dragBeginCb(self, action, actor, event_x, event_y, modifiers):
        self.gotDragged = False
        mode = self.timeline._container.getEditionMode()

        # This can't change during a drag, so we can safely compute it now for drag events.
        nbrLayers = len(self.timeline.bTimeline.get_layers())
        self.brother = self.timeline.findBrother(self.bElement)
        self._dragBeginStart = self.bElement.get_start()
        self.dragBeginStartX = event_x
        self.dragBeginStartY = event_y

        self.nbrLayers = nbrLayers
        self.ghostclip.setNbrLayers(nbrLayers)
        self.ghostclip.setWidth(self.props.width)
        if self.brother:
            self.brother.ghostclip.setWidth(self.props.width)
            self.brother.ghostclip.setNbrLayers(nbrLayers)

        # We can also safely find if the object has a brother element
        self.setDragged(True)

    def _dragProgressCb(self, action, actor, delta_x, delta_y):
        # We can't use delta_x here because it fluctuates weirdly.
        if not self.gotDragged:
            self.gotDragged = True
            self._context = EditingContext(self.bElement,
                                           self.timeline.bTimeline,
                                           None,
                                           GES.Edge.EDGE_NONE,
                                           None,
                                           self.timeline._container.app.action_log)

        mode = self.timeline._container.getEditionMode()
        self._context.setMode(mode)

        coords = self.dragAction.get_motion_coords()
        delta_x = coords[0] - self.dragBeginStartX
        delta_y = coords[1] - self.dragBeginStartY
        y = coords[1] + self.timeline._container.point.y
        priority = self._getLayerForY(y)
        new_start = self._dragBeginStart + self.pixelToNs(delta_x)

        self.ghostclip.props.x = max(0, self.nsToPixel(self._dragBeginStart) + delta_x)
        self.ghostclip.update(priority, y, False)
        if self.brother:
            self.brother.ghostclip.props.x = max(0, self.nsToPixel(self._dragBeginStart) + delta_x)
            self.brother.ghostclip.update(priority, y, True)

        if not self.ghostclip.props.visible:
            self._context.editTo(new_start, self.bElement.get_parent().get_layer().get_priority())
        else:
            self._context.editTo(self._dragBeginStart, self.bElement.get_parent().get_layer().get_priority())

        self.timeline._updateSize(self.ghostclip)
        return False

    def _dragEndCb(self, action, actor, event_x, event_y, modifiers):
        coords = self.dragAction.get_motion_coords()
        delta_x = coords[0] - self.dragBeginStartX
        new_start = self._dragBeginStart + self.pixelToNs(delta_x)
        priority = self._getLayerForY(coords[1] + self.timeline._container.point.y)
        priority = min(priority, len(self.timeline.bTimeline.get_layers()))
        priority = max(0, priority)

        self.timeline._snapEndedCb()
        self.setDragged(False)

        self.ghostclip.props.visible = False
        if self.brother:
            self.brother.ghostclip.props.visible = False

        if self.ghostclip.shouldCreateLayer:
            self.timeline.insertLayer(self.ghostclip)

        if self.gotDragged:
            self._context.editTo(new_start, priority)
            self._context.finish()

    def cleanup(self):
        if self.preview and not type(self.preview) is Clutter.Actor:
            self.preview.cleanup()
        self.leftHandle.cleanup()
        self.leftHandle = None
        self.rightHandle.cleanup()
        self.rightHandle = None
        TimelineElement.cleanup(self)


class TransitionElement(TimelineElement):
    def __init__(self, bElement, timeline):
        TimelineElement.__init__(self, bElement, timeline)
        self.isDragged = True
        self.set_reactive(True)

    def _createBackground(self):
        background = RoundedRectangle(0, 0, 0, 0)
        background.set_color(TRANSITION_COLOR)
        background.set_border_width(1)
        return background

    def _selectedChangedCb(self, selected, isSelected):
        TimelineElement._selectedChangedCb(self, selected, isSelected)

        if isSelected:
            self.timeline._container.app.gui.trans_list.activate(self.bElement)
        else:
            self.timeline._container.app.gui.trans_list.deactivate()

    def _clickedCb(self, action, actor):
        selection = {self.bElement}
        self.timeline.selection.setSelection(selection, SELECT)
        return False
