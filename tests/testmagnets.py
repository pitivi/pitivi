import sys, os, gtk, goocanvas

root = os.path.abspath(os.path.curdir)
print root
if not root in sys.path:
    sys.path.insert(0, root)

from pitivi.ui.util import *
from pitivi.utils import binary_search

RECT = (
    goocanvas.Rect,
    {
        "width" : 50,
        "height" : 50,
        "fill-color" : "blue"
    },
    {}
)

LINE = (
    goocanvas.Rect,
    {
        "width" : 1,
        "height" : 50,
        "line-width" : 0.5
    },
    {}
)
magnets = [0, 100, 230, 500, 600]
deadband = 7

def transform(pos):
    x, y = pos
    global magnets, deadband, i
    return (magnetize(i, x, magnets, deadband), 0)

c = goocanvas.Canvas()
c.set_bounds(0, 0, 700, 100)
i = make_item(RECT)
c.get_root_item().add_child(i)
make_dragable(c, i, transform=transform)
for m in magnets:
    l = make_item(LINE)
    l.props.x = m
    c.get_root_item().add_child(l)
w = gtk.Window()
w.connect("destroy", gtk.main_quit)
w.add(c)
w.show_all()
gtk.main()
