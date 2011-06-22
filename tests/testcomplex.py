import gobject
gobject.threads_init()
import gst
import pygtk
pygtk.require("2.0")
import gtk
import goocanvas
import sys
import os
from itertools import cycle
from util import *


root = os.path.abspath(os.path.curdir)
print root
if not root in sys.path:
    sys.path.insert(0, root)

from complextimeline import ComplexTrack
from pitivi.timeline.objects import MEDIA_TYPE_VIDEO

SOURCES = (
    ("source1", 300 * gst.SECOND),
    ("source2", 200 * gst.SECOND),
    ("source3", 10 * gst.SECOND),
)


class TestComposition(gobject.GObject):
    __gtype_name__ = "TestComposition"
    __gsignals__ = {
        "source-added": (gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            (gobject.TYPE_PYOBJECT, )),
        "source-removed": (gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            (gobject.TYPE_PYOBJECT, )),
    }

    def __init__(self, *args, **kwargs):
        gobject.GObject.__init__(self, *args, **kwargs)
        self.media_type = MEDIA_TYPE_VIDEO

    def addSource(self, source, position):
        self.emit("source-added", source)

    def removeSource(self, source):
        self.emit("source-removed", source)


class TestTimelineObject(gobject.GObject):
    __gtype_name__ = "TestObject"
    __gsignals__ = {
        "start-duration-changed": (gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, )),
    }

    class Factory:
        name = None

    def __init__(self, name, start, duration):
        gobject.GObject.__init__(self)
        self.start = start
        self.duration = duration
        self.factory = self.Factory()
        self.factory.name = name

    def setStartDurationTime(self, start=-1, duration=-1):
        if start != -1:
            self.start = start
        if duration != -1:
            self.duration = duration
        self.emit("start-duration-changed", self.start, self.duration)

c = goocanvas.Canvas()
t = ComplexTrack(c)
model = TestComposition()
t.set_composition(model)
c.get_root_item().add_child(t)
cur = long(0)
for name, duration in SOURCES:
    model.addSource(TestTimelineObject(name, cur, duration), None)
    cur += duration
print t.width
c.set_size_request(int(t.width), int(t.height))
s = gtk.ScrolledWindow()
s.set_policy(gtk.POLICY_ALWAYS, gtk.POLICY_NEVER)
s.add(c)
z = gtk.HScale(t.get_zoom_adjustment())
b = gtk.VBox()
b.pack_start(s, True, True)
b.pack_start(z, False, False)
w = gtk.Window()
w.add(b)
w.show_all()
w.connect("destroy", gtk.main_quit)
gtk.main()
