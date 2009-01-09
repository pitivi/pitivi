from pitivi.ui.zoominterface import Zoomable
from pitivi.ui.timelineobject import TimelineObject
from pitivi.timeline.objects import MEDIA_TYPE_VIDEO
from pitivi.receiver import receiver, handler
import goocanvas

# TODO: layer managment controls

class Track(goocanvas.Group, Zoomable):
    __gtype_name__ = 'Track'

    track = receiver()

    def __init__(self, track, timeline=None):
        goocanvas.Group.__init__(self)
        Zoomable.__init__(self)
        self.widgets = {}
        self.track = track
        self.timeline = timeline

    @handler(track, "track-object-added")
    def _objectAdded(self, unused_timeline, track_object):
        w = TimelineObject(track_object, self.track, self.timeline)
        self.widgets[track_object] = w
        self.add_child(w)

    @handler(track, "track-object-removed")
    def _objectRemoved(self, unused_timeline, track_object):
        w = self.widgets[track_object]
        self.remove_child(w)
        del self.widgets[track_object]

