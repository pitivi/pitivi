import gobject
gobject.threads_init()
import pygtk
pygtk.require("2.0")
import gtk
import goocanvas
from itertools import cycle
from util import *

LABELS = "one two three four five six seven".split()

box_a = (
    goocanvas.Rect,
    {
        "width" : 50,
        "height" : 30, 
        "stroke_color" : "black",
        "fill_color_rgba" : 0x556633FF
    },
    {}
)
box_b = (
    goocanvas.Rect,
    {
        "width" : 75,
        "height" : 30,
        "stroke_color" : "black",
        "fill_color_rgba" : 0x663333FF,
    },
    {}
)

box = cycle((box_a, box_b))

label = (
    Text,
    {
        "font" : "Sans 9",
        "text" : "will be replaced",
        "fill_color_rgba" : 0x66AA66FF,
        "anchor" : gtk.ANCHOR_CENTER
    },
    {}
)

def null_true(*args):
    return True

def null_false(*args):
    return False

def make_box(text):
    b = make_item(box.next())
    t = make_item(label)
    t.props.text = text
    set_pos(t, center(b))
    return group(b, t)

def make_widget(text):
    b = gtk.Label(text)
    d = gtk.EventBox()
    d.add(b)
    e = goocanvas.Rect(width=75, height=50, visibility=False)
    return group(goocanvas.Widget(widget=d, width=75,
        height=50), e)

c = goocanvas.Canvas()
t = HList(canvas=c)
c.get_root_item().add_child(t)
for word in LABELS:
    t.add(make_box(word))
t.reorderable = True
s = gtk.ScrolledWindow()
s.set_policy(gtk.POLICY_ALWAYS, gtk.POLICY_NEVER)
s.add(c)
w = gtk.Window()
w.add(s)
w.show_all()
w.connect("destroy", gtk.main_quit)
gtk.main()


