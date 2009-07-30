from pitivi.ui.zoominterface import Zoomable
from pitivi.ui.trackobject import TrackObject
from pitivi.receiver import receiver, handler
from pitivi.ui.common import LAYER_HEIGHT_EXPANDED, LAYER_HEIGHT_COLLAPSED, LAYER_SPACING
import goocanvas

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
                if trackobj is self.track.default_track_object:
                    continue
                self._objectAdded(None, trackobj)

    track = receiver(_setTrack)

    @handler(track, "track-object-added")
    def _objectAdded(self, unused_timeline, track_object):
        w = TrackObject(self.app, track_object, self.track, self.timeline)
        self.widgets[track_object] = w
        self.add_child(w)

    @handler(track, "track-object-removed")
    def _objectRemoved(self, unused_timeline, track_object):
        w = self.widgets[track_object]
        self.remove_child(w)
        del self.widgets[track_object]
        Zoomable.removeInstance(w)

    @handler(track, "max-priority-changed")
    def _maxPriorityChanged(self, track, max_priority):
        self.get_canvas().regroupTracks()
