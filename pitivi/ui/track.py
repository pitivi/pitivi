from pitivi.ui.zoominterface import Zoomable
from pitivi.ui.trackobject import TrackObject
from pitivi.receiver import receiver, handler
from common import LAYER_HEIGHT_EXPANDED, LAYER_HEIGHT_COLLAPSED, LAYER_SPACING
import goocanvas

class Track(goocanvas.Group, Zoomable):
    __gtype_name__ = 'Track'

    def __init__(self, track, timeline=None):
        goocanvas.Group.__init__(self)
        Zoomable.__init__(self)
        self.widgets = {}
        self.track = track
        self.timeline = timeline
        self.max_priority = 0

## Properties

    def getHeight(self):
        if self.track.expanded:
            return (1 + self.track.max_priority) * (LAYER_HEIGHT_EXPANDED + LAYER_SPACING)
        else:
            return LAYER_HEIGHT_COLLAPSED + LAYER_SPACING

    height = property(getHeight)

## Public API

## track signals

    track = receiver()

    @handler(track, "track-object-added")
    def _objectAdded(self, unused_timeline, track_object):
        w = TrackObject(track_object, self.track, self.timeline)
        self.widgets[track_object] = w
        self.add_child(w)

    @handler(track, "track-object-removed")
    def _objectRemoved(self, unused_timeline, track_object):
        w = self.widgets[track_object]
        self.remove_child(w)
        del self.widgets[track_object]
        Zoomable.removeInstance(w)

    @handler(track, "expanded-changed")
    def _expandedChanged(self, track):
        for widget in self.widgets.itervalues():
            widget.expanded = track.expanded
        self.get_canvas().regroupTracks()

    @handler(track, "max-priority-changed")
    def _maxPriorityChanged(self, track):
        self.get_canvas().regroupTracks()
