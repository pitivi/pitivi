# -*- coding: utf-8 -*-
# PiTiVi , Non-linear video editor
#
#       pitivi/elements.py
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
import cairo

from gi.repository import Clutter, Cogl, GES, Gdk, Gst, GstController
from pitivi.utils.timeline import Zoomable, EditingContext, Selection, SELECT, UNSELECT, Selected
from previewers import VideoPreviewer, BORDER_WIDTH

import pitivi.configure as configure
from pitivi.utils.ui import EXPANDED_SIZE, SPACING, KEYFRAME_SIZE, CONTROL_WIDTH

from datetime import datetime


def get_preview_for_object(bElement, timeline):
    # Fixme special preview for transitions, titles
    if not isinstance(bElement.get_parent(), GES.UriClip):
        return Clutter.Actor()

    track_type = bElement.get_track_type()
    if track_type == GES.TrackType.AUDIO:
        # FIXME: RandomAccessAudioPreviewer doesn't work yet
        # previewers[key] = RandomAccessAudioPreviewer(instance, uri)
        # TODO: return waveform previewer
        return Clutter.Actor()
    elif track_type == GES.TrackType.VIDEO:
        if bElement.get_parent().is_image():
            # TODO: return still image previewer
            return Clutter.Actor()
        else:
            return VideoPreviewer(bElement, timeline)
    else:
        return Clutter.Actor()


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

    def get_border_color(color):
        return self._border_color

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
        self.set_background_color(Clutter.Color.new(255, 255, 255, 50))
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
        self.isSelected = False
        self.timelineElement = timelineElement
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
        self.timelineElement.bElement.selected.connect("selected-changed", self._selectedChangedCb)

    #Callbacks

    def _enterEventCb(self, actor, event):
        self.timelineElement.set_reactive(False)
        for elem in self.timelineElement.get_children():
            elem.set_reactive(False)
        self.set_reactive(True)

        self.set_from_file(os.path.join(configure.get_pixmap_dir(), "trimbar-focused.png"))
        if self.isLeft:
            self.timelineElement.timeline._container.embed.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.LEFT_SIDE))
        else:
            self.timelineElement.timeline._container.embed.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.RIGHT_SIDE))

    def _leaveEventCb(self, actor, event):
        self.timelineElement.set_reactive(True)

        actor = self.timelineElement.timeline._container.stage.get_actor_at_pos(Clutter.PickMode.ALL, event.x, event.y)
        try:
            element = actor.bElement
            if element != self.timelineElement.bELement and not self.isSelected:
                self.timelineElement.hideHandles()
        except AttributeError:
            if not self.isSelected:
                self.timelineElement.hideHandles()

        for elem in self.timelineElement.get_children():
            elem.set_reactive(True)
        self.set_from_file(os.path.join(configure.get_pixmap_dir(), "trimbar-normal.png"))
        self.timelineElement.timeline._container.embed.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.ARROW))

    def _elementEnterEventCb(self, actor, event):
        self.show()

    def _elementLeaveEventCb(self, actor, event):
        if not self.isSelected:
            self.hide()

    def _selectedChangedCb(self, selected, isSelected):
        self.isSelected = isSelected
        self.props.visible = isSelected

    def _dragBeginCb(self, action, actor, event_x, event_y, modifiers):
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
                                       set([]),
                                       None)

        self._context.connect("clip-trim", self.clipTrimCb)
        self._context.connect("clip-trim-finished", self.clipTrimFinishedCb)

    def _dragProgressCb(self, action, actor, delta_x, delta_y):
        # We can't use delta_x here because it fluctuates weirdly.
        coords = self.dragAction.get_motion_coords()
        delta_x = coords[0] - self.dragBeginStartX
        new_start = self._dragBeginStart + Zoomable.pixelToNs(delta_x)

        self._context.setMode(self.timelineElement.timeline._container.getEditionMode(isAHandle=True))
        self._context.editTo(new_start, self.timelineElement.bElement.get_parent().get_layer().get_priority())
        return False

    def _dragEndCb(self, action, actor, event_x, event_y, modifiers):
        self.timelineElement.setDragged(False)
        self._context.finish()

        self.timelineElement.set_reactive(True)
        for elem in self.timelineElement.get_children():
            elem.set_reactive(True)

        self.set_from_file(os.path.join(configure.get_pixmap_dir(), "trimbar-normal.png"))
        self.timelineElement.timeline._container.embed.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.ARROW))

    def clipTrimCb(self, unused_TrimStartContext, tl_obj, position):
        # While a clip is being trimmed, ask the viewer to preview it
        self.timelineElement.timeline._container.app.gui.viewer.clipTrimPreview(tl_obj, position)

    def clipTrimFinishedCb(self, unused_TrimStartContext):
        # When a clip has finished trimming, tell the viewer to reset itself
        self.timelineElement.timeline._container.app.gui.viewer.clipTrimPreviewFinished()


class TimelineElement(Clutter.Actor, Zoomable):
    def __init__(self, bElement, track, timeline):
        """
        @param bElement : the backend GES.TrackElement
        @param track : the track to which the bElement belongs
        @param timeline : the containing graphic timeline.
        """
        Zoomable.__init__(self)
        Clutter.Actor.__init__(self)

        self.timeline = timeline
        self.bElement = bElement
        self.bElement.selected = Selected()
        self.bElement.ui_element = self
        self.track_type = self.bElement.get_track_type()  # This won't change
        self.isDragged = False
        self.lines = []
        self.keyframes = []
        self.source = None
        self.keyframedElement = None
        size = self.bElement.get_duration()

        self._createBackground(track)
        self._createPreview()
        self._createBorder()
        self._createMarquee()
        self._createHandles()
        self._createGhostclip()

        self.update(True)
        self.set_reactive(True)

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
            try:
                self.rightHandle.save_easing_state()
                self.rightHandle.set_easing_duration(600)
            except AttributeError:  # Element doesnt't have handles
                pass

        self.marquee.set_size(width, height)
        self.background.props.width = width
        self.background.props.height = height
        self.border.props.width = width
        self.border.props.height = height
        self.props.width = width
        self.props.height = height
        self.preview.set_size(width, height)
        try:
            self.rightHandle.set_position(width - self.rightHandle.props.width, 0)
        except AttributeError:  # Element doesnt't have handles
                pass

        if ease:
            self.background.restore_easing_state()
            self.border.restore_easing_state()
            self.preview.restore_easing_state()
            try:
                self.rightHandle.restore_easing_state()
            except AttributeError:  # Element doesnt't have handles
                pass
            self.restore_easing_state()

    def addKeyframe(self, value, timestamp):
        self.source.set(timestamp, value)
        self.updateKeyframes()

    def removeKeyframe(self, kf):
        self.source.unset(kf.value.timestamp)
        self.keyframes = sorted(self.keyframes, key=lambda keyframe: keyframe.value.timestamp)
        self.updateKeyframes()

    def showKeyframes(self, element, propname):
        binding = element.get_control_binding(propname.name)
        if not binding:
            source = GstController.InterpolationControlSource()
            source.props.mode = GstController.InterpolationMode.LINEAR
            if not (element.set_control_source(source, propname.name, "direct")):
                print "There was something like a problem captain"
                return
            val = float(propname.default_value) / (propname.maximum - propname.minimum)
            source.set(self.bElement.props.in_point, val)
            source.set(self.bElement.props.duration, val)
            binding = element.get_control_binding(propname.name)
        self.binding = binding
        self.source = self.binding.props.control_source
        self.prop = propname
        self.keyframedElement = element
        self.updateKeyframes()

    def hideKeyframes(self):
        for keyframe in self.keyframes:
            self.remove_child(keyframe)

        self.keyframes = []

        self.drawLines()

    def setKeyframePosition(self, keyframe, value):
        x = self.nsToPixel(value.timestamp) - KEYFRAME_SIZE / 2
        y = EXPANDED_SIZE - (value.value * EXPANDED_SIZE)

        keyframe.set_z_position(2)
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
        lastPoint = None

        for keyframe in self.keyframes:
            self.remove_child(keyframe)

        self.keyframes = []

        l = len(values)

        for i, value in enumerate(values):
            has_changable_time = True
            if i == 0 or i == l - 1:
                has_changable_time = False
            self._createKeyframe(value, has_changable_time)
            lastPoint = value

        self.drawLines()

    # private API

    def update(self, ease):
        size = self.bElement.get_duration()
        self.set_size(self.nsToPixel(size), EXPANDED_SIZE, ease)

    def setDragged(self, dragged):
        brother = self.timeline.findBrother(self.bElement)
        if brother:
            brother.isDragged = dragged
        self.isDragged = dragged

    def _setKeyframePosition(self, keyframe, value):
        x = self.nsToPixel(value.timestamp) - KEYFRAME_SIZE / 2
        y = EXPANDED_SIZE - (value.value * EXPANDED_SIZE)

        keyframe.set_z_position(2)
        keyframe.set_position(x, y)

    def _createKeyframe(self, value, has_changable_time):
        keyframe = Keyframe(self, value, has_changable_time)

        self.add_child(keyframe)
        self.keyframes.append(keyframe)
        self.setKeyframePosition(keyframe, value)

    def _createLine(self, keyframe, lastKeyframe, line):
        if not line:
            line = Line(self, keyframe, lastKeyframe)
            self.lines.append(line)
            self.add_child(line)

        adj = self.nsToPixel(keyframe.value.timestamp - lastKeyframe.value.timestamp)
        opp = (lastKeyframe.value.value - keyframe.value.value) * EXPANDED_SIZE
        hyp = math.sqrt(adj ** 2 + opp ** 2)
        sinX = opp / hyp
        line.props.width = hyp
        line.props.height = 6
        line.props.rotation_angle_z = math.degrees(math.asin(sinX))
        line.props.x = self.nsToPixel(lastKeyframe.value.timestamp)
        line.props.y = EXPANDED_SIZE - (EXPANDED_SIZE * lastKeyframe.value.value)
        line.canvas.invalidate()

    def _createGhostclip(self):
        pass

    def _createBorder(self):
        self.border = RoundedRectangle(0, 0, 0, 0)
        self.border.bElement = self.bElement
        color = Cogl.Color()

        color.init_from_4ub(100, 100, 100, 255)
        self.border.set_border_color(color)
        self.border.set_border_width(1)
        self.border.set_position(0, 0)

        self.add_child(self.border)

    def _createBackground(self, track):
        pass

    def _createHandles(self):
        pass

    def _createPreview(self):
        self.preview = get_preview_for_object(self.bElement, self.timeline)

        self.add_child(self.preview)

    def _createMarquee(self):
        # TODO: difference between Actor.new() and Actor()?
        self.marquee = Clutter.Actor()
        self.marquee.bElement = self.bElement
        self.marquee.set_background_color(Clutter.Color.new(60, 60, 60, 100))
        self.marquee.props.visible = False
        self.add_child(self.marquee)

    def _connectToEvents(self):
        self.dragAction = Clutter.DragAction()
        self.add_action(self.dragAction)
        self.dragAction.connect("drag-progress", self._dragProgressCb)
        self.dragAction.connect("drag-begin", self._dragBeginCb)
        self.dragAction.connect("drag-end", self._dragEndCb)
        self.bElement.selected.connect("selected-changed", self._selectedChangedCb)
        # We gotta go low-level cause Clutter.ClickAction["clicked"]
        # gets emitted after Clutter.DragAction["drag-begin"]
        self.connect("button-press-event", self._clickedCb)

    def _getLayerForY(self, y):
        if self.bElement.get_track_type() == GES.TrackType.AUDIO:
            y -= self.nbrLayers * (EXPANDED_SIZE + SPACING)
        priority = int(y / (EXPANDED_SIZE + SPACING))

        return priority

    # Interface (Zoomable)

    def zoomChanged(self):
        self.update(True)
        self.updateKeyframes()

    # Callbacks

    def _clickedCb(self, action, actor):
        pass

    def _dragBeginCb(self, action, actor, event_x, event_y, modifiers):
        pass

    def _dragProgressCb(self, action, actor, delta_x, delta_y):
        return False

    def _dragEndCb(self, action, actor, event_x, event_y, modifiers):
        pass

    def _selectedChangedCb(self, selected, isSelected):
        if not isSelected:
            self.hideKeyframes()
        elif self.keyframedElement:
            self.showKeyframes(self.keyframedElement, self.prop)
        self.marquee.props.visible = isSelected


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

    def _drawCb(self, canvas, cr, width, height):
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_source(self.linear)
        cr.rectangle(0, 0, 10, EXPANDED_SIZE)
        cr.fill()


class Line(Clutter.Actor):
    def __init__(self, timelineElement, keyframe, lastKeyframe):
        Clutter.Actor.__init__(self)

        self.timelineElement = timelineElement

        self.canvas = Clutter.Canvas()
        self.canvas.set_size(1000, 4)
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

    def _drawCb(self, canvas, cr, width, height):
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        cr.set_source_rgb(255, 0, 0)
        cr.set_line_width(2.)
        cr.move_to(0, 2)
        cr.line_to(width, 2)
        cr.stroke()

    def transposeXY(self, x, y):
        x -= self.timelineElement.props.x + CONTROL_WIDTH - self.timelineElement.timeline._scroll_point.x
        y -= self.timelineElement.props.y
        return x, y

    def _ungrab(self):
        self.timelineElement.set_reactive(True)
        self.timelineElement.timeline._container.embed.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.ARROW))
        self.timelineElement.timeline._container.reactive = True

    def _clickedCb(self, actor, event):
        if self.gotDragged:
            self.gotDragged = False
            return
        x, y = self.transposeXY(event.x, event.y)
        value = 1.0 - (y / EXPANDED_SIZE)
        value = max(0.0, value)
        value = min(1.0, value)
        timestamp = Zoomable.pixelToNs(x)
        self.timelineElement.addKeyframe(value, timestamp)

    def _enterEventCb(self, actor, event):
        self.timelineElement.set_reactive(False)
        self.timelineElement.timeline._container.embed.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.HAND1))
        self.timelineElement.timeline._container.reactive = False

    def _leaveEventCb(self, actor, event):
        self._ungrab()

    def _motionEventCb(self, actor, event):
        pass

    def _dragBeginCb(self, action, actor, event_x, event_y, modifiers):
        self.dragBeginStartX = event_x
        self.dragBeginStartY = event_y
        self.origY = self.props.y
        self.previousKeyframe.startDrag(event_x, event_y, self)
        self.nextKeyframe.startDrag(event_x, event_y, self)

    def _dragProgressCb(self, action, actor, delta_x, delta_y):
        self.gotDragged = True
        coords = self.dragAction.get_motion_coords()
        delta_x = coords[0] - self.dragBeginStartX
        delta_y = coords[1] - self.dragBeginStartY

        self.previousKeyframe.updateValue(0, delta_y)
        self.nextKeyframe.updateValue(0, delta_y)

        return False

    def _dragEndCb(self, action, actor, event_x, event_y, modifiers):
        self.previousKeyframe.endDrag()
        self.nextKeyframe.endDrag()
        if self.timelineElement.timeline.getActorUnderPointer() != self:
            self._ungrab()


class Keyframe(Clutter.Actor):
    """
    If has_changable_time is False, it means this is an edge keyframe.
    """
    def __init__(self, timelineElement, value, has_changable_time):
        Clutter.Actor.__init__(self)

        self.value = value
        self.timelineElement = timelineElement

        self.set_size(KEYFRAME_SIZE, KEYFRAME_SIZE)
        self.set_background_color(Clutter.Color.new(0, 255, 0, 255))

        self.dragAction = Clutter.DragAction()
        self.add_action(self.dragAction)

        self.has_changable_time = has_changable_time

        self.dragAction.connect("drag-begin", self._dragBeginCb)
        self.dragAction.connect("drag-end", self._dragEndCb)
        self.dragAction.connect("drag-progress", self._dragProgressCb)
        self.connect("key-press-event", self._keyPressEventCb)
        self.connect("enter-event", self._enterEventCb)
        self.connect("leave-event", self._leaveEventCb)

        self.connect("button-press-event", self._clickedCb)

        self.lastClick = datetime.now()

        self.set_reactive(True)

    def _unselect(self):
        self.timelineElement.set_reactive(True)
        self.set_background_color(Clutter.Color.new(0, 255, 0, 255))
        self.timelineElement.timeline._container.embed.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.ARROW))
        self.timelineElement.timeline._container.reactive = True

    def _remove(self):
        # Can't remove edge keyframes !
        if not self.has_changable_time:
            return

        self._unselect()
        self.timelineElement.removeKeyframe(self)

    def _clickedCb(self, actor, event):
        if (event.modifier_state & Clutter.ModifierType.CONTROL_MASK):
            self._remove()
        elif (datetime.now() - self.lastClick).total_seconds() < 0.5:
            self._remove()
        self.lastClick = datetime.now()

    def _keyPressEventCb(self, actor, event):
        print event, dir(event)

    def _enterEventCb(self, actor, event):
        self.timelineElement.set_reactive(False)
        self.set_background_color(Clutter.Color.new(0, 0, 0, 255))
        self.timelineElement.timeline._container.embed.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.HAND1))
        self.timelineElement.timeline._container.reactive = False

    def _leaveEventCb(self, actor, event):
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
        self.line = None

    def updateValue(self, delta_x, delta_y):
        newTs = self.tsStart + Zoomable.pixelToNs(delta_x)
        newValue = self.valueStart - (delta_y / EXPANDED_SIZE)

        newTs = min(max(newTs, self.inpoint), self.duration)

        newValue = min(max(newValue, 0.0), 1.0)

        if not self.has_changable_time:
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

    def _dragBeginCb(self, action, actor, event_x, event_y, modifiers):
        self.startDrag(event_x, event_y)

    def _dragProgressCb(self, action, actor, delta_x, delta_y):
        coords = self.dragAction.get_motion_coords()
        delta_x = coords[0] - self.dragBeginStartX
        delta_y = coords[1] - self.dragBeginStartY

        self.updateValue(delta_x, delta_y)

        return False

    def _dragEndCb(self, action, actor, event_x, event_y, modifiers):
        self.endDrag()
        if self.timelineElement.timeline.getActorUnderPointer() != self:
            self._unselect()


class URISourceElement(TimelineElement):
    def __init__(self, bElement, track, timeline):
        TimelineElement.__init__(self, bElement, track, timeline)

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

    def _createBackground(self, track):
        if track.type == GES.TrackType.AUDIO:
            # Audio clips go from dark green to light green
            # (27, 46, 14, 255) to (73, 108, 33, 255)
            self.background = Gradient(27, 46, 14, 73, 108, 33)
        else:
            # Video clips go from almost black to gray
            # (15, 15, 15, 255) to (45, 45, 45, 255)
            self.background = Gradient(15, 15, 15, 45, 45, 45)

        self.background.bElement = self.bElement

        self.add_child(self.background)
        self.background.set_position(0, 0)

    # Callbacks
    def _clickedCb(self, action, actor):
        #TODO : Let's be more specific, masks etc ..
        self.timeline.selection.setToObj(self.bElement, SELECT)
        return False

    def _dragBeginCb(self, action, actor, event_x, event_y, modifiers):
        mode = self.timeline._container.getEditionMode()
        self._context = EditingContext(self.bElement,
                                       self.timeline.bTimeline,
                                       mode,
                                       GES.Edge.EDGE_NONE,
                                       self.timeline.selection.getSelectedTrackElements(),
                                       None)
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

        self._context.editTo(new_start, priority)
        self._context.finish()


class TransitionElement(TimelineElement):
    def __init__(self, bElement, track, timeline):
        TimelineElement.__init__(self, bElement, track, timeline)
        self.isDragged = True

    def _createBackground(self, track):
        self.background = RoundedRectangle(0, 0, 0, 0)
        color = Cogl.Color()
        color.init_from_4ub(35, 85, 125, 125)  # light blue
        self.background.set_color(color)
        self.background.set_border_width(1)
        self.background.set_position(0, 0)
        self.add_child(self.background)
