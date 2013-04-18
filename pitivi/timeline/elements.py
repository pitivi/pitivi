"""
Convention throughout this file:
Every GES element which name could be mistaken with a UI element
is prefixed with a little b, example : bTimeline
"""

import os

from gi.repository import Clutter, Cogl, GES, Gdk
from pitivi.utils.timeline import Zoomable, EditingContext, Selection, SELECT, UNSELECT, Selected
from previewers import VideoPreviewer, BORDER_WIDTH

import pitivi.configure as configure
from pitivi.utils.ui import EXPANDED_SIZE, SPACING


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
    def __init__(self, track_type, bElement=None):
        Clutter.Actor.__init__(self)

        self.track_type = track_type
        self.bElement = bElement

        self.set_background_color(Clutter.Color.new(100, 100, 100, 50))
        self.props.visible = False

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

        # Would that be a new layer ?
        if priority == self.nbrLayers:
            self.set_size(self.props.width, SPACING)
            self.props.y = priority * (EXPANDED_SIZE + SPACING)
            if self.track_type == GES.TrackType.AUDIO:
                self.props.y += self.nbrLayers * (EXPANDED_SIZE + SPACING)
            self.props.visible = True
        else:
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

    def _dragProgressCb(self, action, actor, delta_x, delta_y):
        # We can't use delta_x here because it fluctuates weirdly.
        coords = self.dragAction.get_motion_coords()
        delta_x = coords[0] - self.dragBeginStartX
        new_start = self._dragBeginStart + Zoomable.pixelToNs(delta_x)

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
        self.track_type = self.bElement.get_track_type()  # This won't change
        self.isDragged = False
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

    def update(self, ease):
        size = self.bElement.get_duration()
        self.set_size(self.nsToPixel(size), EXPANDED_SIZE, ease)

    def setDragged(self, dragged):
        brother = self.timeline.findBrother(self.bElement)
        if brother:
            brother.isDragged = dragged
        self.isDragged = dragged

    # Internal API

    def _createGhostclip(self):
        pass

    def _createBorder(self):
        self.border = RoundedRectangle(0, 0, 5, 5)
        self.border.bElement = self.bElement
        color = Cogl.Color()

        color.init_from_4ub(100, 100, 100, 255)
        self.border.set_border_color(color)
        self.border.set_border_width(3)
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
        self.marquee.props.visible = isSelected


class ClipElement(TimelineElement):
    def __init__(self, bElement, track, timeline):
        TimelineElement.__init__(self, bElement, track, timeline)

    # public API

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
        self.background = RoundedRectangle(0, 0, 5, 5)
        self.background.bElement = self.bElement

        if track.type == GES.TrackType.AUDIO:
            color = Cogl.Color()
            color.init_from_4ub(70, 79, 118, 255)
        else:
            color = Cogl.Color()
            color.init_from_4ub(225, 232, 238, 255)

        self.background.set_color(color)
        self.background.set_border_width(3)
        self.background.set_position(0, 0)

        self.add_child(self.background)

    # Callbacks
    def _clickedCb(self, action, actor):
        #TODO : Let's be more specific, masks etc ..
        self.timeline.selection.setToObj(self.bElement, SELECT)

    def _dragBeginCb(self, action, actor, event_x, event_y, modifiers):
        self._context = EditingContext(self.bElement,
                                       self.timeline.bTimeline,
                                       GES.EditMode.EDIT_NORMAL,
                                       GES.Edge.EDGE_NONE,
                                       self.timeline.selection.getSelectedTrackElements(),
                                       None)
        # This can't change during a drag, so we can safely compute it now for drag events.
        nbrLayers = len(self.timeline.bTimeline.get_layers())
        self.brother = self.timeline.findBrother(self.bElement)
        self._dragBeginStart = self.bElement.get_start()
        self.dragBeginStartX = event_x
        self.dragBeginStartY = event_y

        self.ghostclip.setNbrLayers(nbrLayers)
        self.ghostclip.setWidth(self.props.width)
        if self.brother:
            self.ghostclip.setWidth(self.props.width)
            self.brother.ghostclip.setNbrLayers(nbrLayers)

        # We can also safely find if the object has a brother element
        self.setDragged(True)

    def _dragProgressCb(self, action, actor, delta_x, delta_y):
        # We can't use delta_x here because it fluctuates weirdly.
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

        self._context.editTo(new_start, priority)
        self._context.finish()

    def _selectedChangedCb(self, selected, isSelected):
        self.marquee.props.visible = isSelected


class TransitionElement(TimelineElement):
    def __init__(self, bElement, track, timeline):
        TimelineElement.__init__(self, bElement, track, timeline)
        self.isDragged = True

    def _createBackground(self, track):
        self.background = RoundedRectangle(0, 0, 5, 5)
        color = Cogl.Color()

        color.init_from_4ub(100, 100, 100, 125)
        self.background.set_color(color)
        self.background.set_border_width(3)
        self.background.set_position(0, 0)

        self.add_child(self.background)
