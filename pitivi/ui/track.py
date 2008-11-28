from util import *
from complexinterface import Zoomable
from timelineobject import TimelineObject
from pitivi.timeline.objects import MEDIA_TYPE_VIDEO
import pitivi.instance as instance

class Track(SmartGroup, Zoomable):
    __gtype_name__ = 'Track'

    def __init__(self, *args, **kwargs):
        SmartGroup.__init__(self, *args, **kwargs)
        # FIXME: all of these should be private
        self.widgets = {}
        self.elements = {}
        self.sig_ids = None
        self.comp = None
        self.object_style = None

    # FIXME: this should be set_model(), overriding BaseView
    def set_composition(self, comp):
        if self.sig_ids:
            for sig in self.sig_ids:
                comp.disconnect(sig)
        self.comp = comp
        if comp:
            added = comp.connect("source-added", self._objectAdded)
            removed = comp.connect("source-removed", self._objectRemoved)
            self.sig_ids = (added, removed)

    def _objectAdded(self, unused_timeline, element):
        w = TimelineObject(element, self.comp, self.object_style)
        w.setZoomAdjustment(self.getZoomAdjustment())
        self.widgets[element] = w
        self.elements[w] = element
        self.add_child(w)

    def _objectRemoved(self, unused_timeline, element):
        w = self.widgets[element]
        self.remove_child(w)
        w.comp = None
        del self.widgets[element]
        del self.elements[w]

    def setChildZoomAdjustment(self, adj):
        for widget in self.elements:
            widget.setZoomAdjustment(adj)
