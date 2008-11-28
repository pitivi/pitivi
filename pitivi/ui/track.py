from zoominterface import Zoomable
from timelineobject import TimelineObject
from pitivi.timeline.objects import MEDIA_TYPE_VIDEO
from pitivi.receiver import receiver, handler
import pitivi.instance as instance
import goocanvas

# TODO: layer managment controls

class Track(goocanvas.Group, Zoomable):
    __gtype_name__ = 'Track'

    comp = receiver()

    def __init__(self, comp=None):
        goocanvas.Group.__init__(self)
        Zoomable.__init__(self)
        self.widgets = {}
        self.comp = comp

    @handler(comp, "source-added")
    def _objectAdded(self, unused_timeline, element):
        w = TimelineObject(element, self.comp)
        self.widgets[element] = w
        self.add_child(w)

    @handler(comp, "source-removed")
    def _objectRemoved(self, unused_timeline, element):
        w = self.widgets[element]
        self.remove_child(w)
        del self.widgets[element]

