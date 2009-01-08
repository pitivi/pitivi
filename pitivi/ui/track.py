from pitivi.ui.zoominterface import Zoomable
from pitivi.ui.timelineobject import TimelineObject
from pitivi.timeline.objects import MEDIA_TYPE_VIDEO
from pitivi.receiver import receiver, handler
import goocanvas

# TODO: layer managment controls

class Track(goocanvas.Group, Zoomable):
    __gtype_name__ = 'Track'

    timeline_track = receiver()

    def __init__(self, timeline_track, timeline=None):
        goocanvas.Group.__init__(self)
        Zoomable.__init__(self)
        self.widgets = {}
        self.timeline_track = timeline_track
        self.timeline = timeline

    @handler(timeline_track, "track-object-added")
    def _objectAdded(self, unused_timeline, element):
        w = TimelineObject(element, self.timeline_track, self.timeline)
        self.widgets[element] = w
        self.add_child(w)

    @handler(timeline_track, "track-object-removed")
    def _objectRemoved(self, unused_timeline, element):
        w = self.widgets[element]
        self.remove_child(w)
        del self.widgets[element]

