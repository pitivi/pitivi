from pitivi.ui.zoominterface import Zoomable
from pitivi.ui.trackobject import TrackObject
from pitivi.timeline.track import TrackEffect
from pitivi.receiver import receiver, handler
from pitivi.ui.common import LAYER_HEIGHT_EXPANDED, LAYER_HEIGHT_COLLAPSED, LAYER_SPACING
import goocanvas


class Transition(goocanvas.Rect, Zoomable):

    def __init__(self, transition):
        goocanvas.Rect.__init__(self)
        Zoomable.__init__(self)
        self.props.fill_color_rgba = 0xFFFFFF99
        self.props.stroke_color_rgba = 0x00000099
        self.set_simple_transform(0, -LAYER_SPACING + 3, 1.0, 0)
        self.props.height = LAYER_SPACING - 6
        self.props.pointer_events = goocanvas.EVENTS_NONE
        self.props.radius_x = 2
        self.props.radius_y = 2
        self.transition = transition

    def _setTransition(self):
        if self.transition:
            self._updateAll()

    def _updateAll(self):
        transition = self.transition
        start = transition.start
        duration = transition.duration
        priority = transition.priority
        self._updateStart(transition, start)
        self._updateDuration(transition, duration)
        self._updatePriority(transition, priority)

    transition = receiver(_setTransition)

    @handler(transition, "start-changed")
    def _updateStart(self, transition, start):
        self.props.x = self.nsToPixel(start)

    @handler(transition, "duration-changed")
    def _updateDuration(self, transition, duration):
        width = max(0, self.nsToPixel(duration))
        if width == 0:
            self.props.visibility = goocanvas.ITEM_INVISIBLE
        else:
            self.props.visibility = goocanvas.ITEM_VISIBLE
        self.props.width = width

    @handler(transition, "priority-changed")
    def _updatePriority(self, transition, priority):
        self.props.y = (LAYER_HEIGHT_EXPANDED + LAYER_SPACING) * priority

    def zoomChanged(self):
        self._updateAll()


class Track(goocanvas.Group, Zoomable):
    __gtype_name__ = 'Track'

    def __init__(self, instance, track, timeline=None):
        goocanvas.Group.__init__(self)
        Zoomable.__init__(self)
        self.app = instance
        self.widgets = {}
        self.timeline = timeline
        self.track = track
        self.max_priority = 0
        self._expanded = True

## Properties

    def setExpanded(self, expanded):
        if expanded != self._expanded:
            self._expanded = expanded

            for widget in self.widgets.itervalues():
                widget.expanded = expanded
            self.get_canvas().regroupTracks()

    def getHeight(self):
        if self._expanded:
            return (1 + self.track.max_priority) * (LAYER_HEIGHT_EXPANDED + LAYER_SPACING)
        else:
            return LAYER_HEIGHT_COLLAPSED + LAYER_SPACING

    height = property(getHeight)

## Public API

## track signals

    def _setTrack(self):
        if self.track:
            for trackobj in self.track.track_objects:
                self._objectAdded(None, trackobj)
            for transition in self.track.transitions.itervalues():
                self._transitionAdded(None, transition)

    track = receiver(_setTrack)

    @handler(track, "track-object-added")
    def _objectAdded(self, unused_timeline, track_object):
        if not isinstance(track_object, TrackEffect):
            w = TrackObject(self.app, track_object, self.track, self.timeline)
            self.widgets[track_object] = w
            self.add_child(w)

    @handler(track, "track-object-removed")
    def _objectRemoved(self, unused_timeline, track_object):
        if not isinstance(track_object, TrackEffect):
            w = self.widgets[track_object]
            self.remove_child(w)
            del self.widgets[track_object]
            Zoomable.removeInstance(w)

    @handler(track, "transition-added")
    def _transitionAdded(self, unused_timeline, transition):
        w = Transition(transition)
        self.widgets[transition] = w
        self.add_child(w)

    @handler(track, "transition-removed")
    def _transitionRemoved(self, unused_timeline, transition):
        w = self.widgets[transition]
        self.remove_child(w)
        del self.widgets[transition]
        Zoomable.removeInstance(w)

    @handler(track, "max-priority-changed")
    def _maxPriorityChanged(self, track, max_priority):
        self.get_canvas().regroupTracks()
