from pitivi.ui.zoominterface import Zoomable
from pitivi.ui.trackobject import TrackObject
from pitivi.timeline.track import TrackEffect
from pitivi.receiver import receiver, handler
from pitivi.ui.common import LAYER_HEIGHT_EXPANDED, LAYER_HEIGHT_COLLAPSED, LAYER_SPACING
import goocanvas
import ges
import gobject


class Transition(goocanvas.Rect, Zoomable):

    def __init__(self, transition):
        goocanvas.Rect.__init__(self)
        Zoomable.__init__(self)
        self.props.fill_color_rgba = 0xFFFFFF99
        self.props.stroke_color_rgba = 0x00000099
        self.set_simple_transform(0, - LAYER_SPACING + 3, 1.0, 0)
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
        start = transition.get_start()
        duration = transition.get_duration()
        priority = transition.get_priority()
        self._updateStart(transition, start)
        self._updateDuration(transition, duration)
        self._updatePriority(transition, priority)

    transition = receiver(_setTransition)

    @handler(transition, "notify::start")
    def _updateStart(self, transition, start):
        self.props.x = self.nsToPixel(start)

    @handler(transition, "notify::duration")
    def _updateDuration(self, transition, duration):
        width = max(0, self.nsToPixel(duration))
        if width == 0:
            self.props.visibility = goocanvas.ITEM_INVISIBLE
        else:
            self.props.visibility = goocanvas.ITEM_VISIBLE
        self.props.width = width

    @handler(transition, "notify::priority")
    def _updatePriority(self, transition, priority):
        self.props.y = (LAYER_HEIGHT_EXPANDED + LAYER_SPACING) * transition.get_priority()

    def zoomChanged(self):
        self._updateAll()


class Track(goocanvas.Group, Zoomable):
    __gtype_name__ = 'Track'

    def __init__(self, instance, track, timeline=None):
        goocanvas.Group.__init__(self)
        Zoomable.__init__(self)
        self.app = instance
        self.widgets = {}
        self.transitions = []
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
        track_objects = self.track.get_objects()
        max_priority = 0
        for track_object in track_objects:
            if isinstance(track_object, ges.TrackAudioTestSource):
                continue
            if isinstance(track_object, ges.TrackVideoTestSource):
                continue
            priority = track_object.get_timeline_object().get_layer().get_property("priority")
            if priority > max_priority:
                max_priority = priority
        self.track.max_priority = max_priority
        if self.track.max_priority < 0:
            self.track.max_priority = 0
        if self._expanded:
            return (1 + self.track.max_priority) * (LAYER_HEIGHT_EXPANDED + LAYER_SPACING)
            #return LAYER_HEIGHT_EXPANDED + LAYER_SPACING
        else:
            return LAYER_HEIGHT_COLLAPSED + LAYER_SPACING

    height = property(getHeight)

## Public API

## track signals

    def _setTrack(self):
        if self.track:
            for trackobj in self.track.get_objects():
                self._objectAdded(None, trackobj)

    track = receiver(_setTrack)

    @handler(track, "track-object-added")
    def _objectAdded(self, unused_timeline, track_object):
        if isinstance(track_object, ges.TrackParseLaunchEffect):
            return
        if isinstance(track_object, ges.TrackAudioTestSource):
            return
        if isinstance(track_object, ges.TrackVideoTestSource):
            return
        if isinstance(track_object, ges.TrackVideoTestSource):
            return
        if isinstance(track_object, ges.TrackAudioTransition):
            self._transitionAdded(track_object)
            return
        if isinstance(track_object, ges.TrackVideoTransition):
            self._transitionAdded(track_object)
            return
        gobject.timeout_add(1, self.check, track_object)

    def check(self, tr_obj):
        if tr_obj.get_timeline_object():
            w = TrackObject(self.app, tr_obj, self.track, self.timeline, self)
            self.app.current.sources.addUri(tr_obj.get_timeline_object().get_uri())
            self.widgets[tr_obj] = w
            self.add_child(w)
            self.app.gui.setBestZoomRatio()

    @handler(track, "track-object-removed")
    def _objectRemoved(self, unused_timeline, track_object):
        if isinstance(track_object, ges.TrackVideoTestSource) or \
            isinstance(track_object, ges.TrackAudioTestSource) or \
            isinstance(track_object, ges.TrackParseLaunchEffect):
            return
        w = self.widgets[track_object]
        self.remove_child(w)
        del self.widgets[track_object]
        Zoomable.removeInstance(w)

    def _transitionAdded(self, transition):
        w = TrackObject(self.app, transition, self.track, self.timeline, self, True)
        self.widgets[transition] = w
        self.add_child(w)
        self.transitions.append(w)
        w.raise_(None)
