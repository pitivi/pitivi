#Copyright (C) 2008 Brandon J. Lewis
#
#License:
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2 of the License, or (at your option) any later version.
#
#    This package is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this package; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
#
#On Debian systems, the complete text of the GNU Lesser General
#Public License can be found in `/usr/share/common-licenses/LGPL'.

import gobject
import goocanvas
import gtk
import pango
import pangocairo
from pitivi.utils import closest_item

## GooCanvas Convenience Functions

def null_true(*args):
    return True

def null_false(*args):
    return False

def printall(*args):
    print args

def event_coords(canvas, event):
    """returns the coordinates of an event"""
    return canvas.convert_from_pixels(canvas.props.scale_x * event.x, 
        canvas.props.scale_y * event.y)

def pixel_coords(canvas, point):
    return canvas.convert_from_pixels(canvas.props.scale_x * point[0], 
        canvas.props.scale_y * point[1])

def point_difference(p1, p2):
    """Returns the 2-dvector difference p1 - p2"""
    p1_x, p1_y = p1
    p2_x, p2_y = p2
    return (p1_x - p2_x, p1_y - p2_y)

def point_sum(p1, p2):
    """Returns the 2d vector sum p1 + p2"""
    p1_x, p1_y = p1
    p2_x, p2_y = p2
    return (p1_x + p2_x, p1_y + p2_y)

def point_mul(factor, point):
    """Returns a scalar multiple factor * point"""
    return tuple(factor * v for v in point)

def pos(item):
    """Returns a tuple x, y representing the position of the 
    supplied goocanvas Item"""
    return item.props.x, item.props.y

def pos_change_cb(item, prop, callback, data):
    """Used internally, don't call this function"""
    callback(pos(item), item, *data)

def size_change_cb(item, prop, callback):
    """Used internally, don't call this function"""
    callback(size(item))

def pos_change(item, callback, *data):
    """Connects the callback to the x and y property notificaitons.
    Do not call this function again without calling unlink_pos_change()
    first"""
    item.set_data("x_sig_hdl", item.connect("notify::x", pos_change_cb,
        callback, data))
    item.set_data("y_sig_hdl", item.connect("notify::y", pos_change_cb,
        callback, data))

def unlink_pos_change(item):
    """Disconnects signal handlers after calling pos_change()"""
    item.disconnect(item.get_data("x_sig_hdl"))
    item.disconnect(item.get_data("y_sig_hdl"))

def size(item):
    """Returns the tuple (<width>, <height>) of item"""
    return item.props.width, item.props.height

def size_change(item, callback):
    """Connects the callback to the width, height property notifications.
    """
    item.set_data("w_sig_hdl", item.connect("notify::width", 
        size_change_cb, callback))
    item.set_data("h_sig_hdl", item.connect("notify::height", 
        size_change_cb, callback))

def unlink_size_change(item):
    item.disconnect(item.get_data("w_sig_hdl"))
    item.disconnect(item.get_data("h_sig_hdl"))

def set_pos(item, pos):
    """Sets the position of item given pos, a tuple of (<x>, <y>)"""
    item.props.x, item.props.y = pos

def set_size(item, size):
    """Sets the size of the item given size, a tuple of 
    (<width>, <height>)"""
    item.props.width, item.props.height = size

def width(item):
    return item.props.width

def height(item):
    return item.props.height

def left(item):
    return item.props.x

def right(item):
    return item.props.x + item.props.width

def center(item):
    return point_sum(pos(item), point_mul(0.5, size(item)))

def magnetize(obj, coord, magnets, deadband):
    # remember that objects have two ends
    left_res, left_diff = closest_item(magnets, coord)
    right_res, right_diff = closest_item(magnets, coord + width(obj))

    if left_diff <= right_diff:
        res = left_res
        diff = left_diff
    else:
        res = right_res - width(obj)
        diff = right_diff
    if diff <= deadband:
        return res
    # otherwise, return x
    return coord

def make_item(factory):
    """Create a new goocanvas item given factory, a tuple of 
    * <class> - the class to create
    * <properties> - initial properties to set, such as color
    * <data> - initial data to set
    """
    klass, properties, data = factory
    ret = klass(**properties)
    for key, value in data.items():
        ret.set_data(key, value)
    return ret

def group(*items):
    """Wrap all the canvas items in items in a smartgroup and return the
    resulting smartgroup. The item's current position is the offset
    within the smartgroup"""
    ret = SmartGroup()
    
    for item in items:
        ret.add_child(item, pos(item))
    
    return ret

# these are callbacks for implementing "dragable object features
def drag_start(item, target, event, canvas, start_cb, transform, cursor):
    """A callback which starts the drag operation of a dragable 
    object"""
    mask = (gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK 
        | gtk.gdk.POINTER_MOTION_MASK  | gtk.gdk.POINTER_MOTION_HINT_MASK 
        | gtk.gdk.ENTER_NOTIFY_MASK | gtk.gdk.LEAVE_NOTIFY_MASK)
    canvas.pointer_grab(item, mask, cursor, event.time)
    item.set_data("dragging", True)
    if start_cb:
        if start_cb(item):
            drag_end(item, target, event, canvas, None)
    if transform:
        coords = transform(event_coords(canvas, event))
    else:
        coords = event_coords(canvas, event)
    item.set_data("pendown", point_difference(pos(item), coords))
    return True

def drag_end(item, target, event, canvas, end_cb):
    """A callback which ends the drag operation of a dragable object"""
    item.set_data("dragging", False)
    canvas.pointer_ungrab(item, event.time)
    if end_cb:
        end_cb(item)
    return True

def drag_move(item, target, event, canvas, transform, move_cb):
    """A callback which handles updating the position during a drag
    operation"""
    if item.get_data("dragging"):
        pos = point_sum(item.get_data("pendown"), 
            event_coords(canvas, event))
        if transform:
            move_cb(item, transform(pos))
            return True
        move_cb(item, pos)
        return True
    return False

def make_dragable(canvas, item, transform=None, start=None, end=None, 
    moved=set_pos, cursor=None):
    """Make item dragable with respect to the canvas. Call this 
    after make_selectable, or it will prevent the latter from working.

        - canvas : the goocanvas.Canvas that contains item
        - item : the item which will become dragable
        - transform : callback which preforms arbitrary transformation
            on mouse coordinates, or None
        - start : callback to prepare object for draging, or None.
            if start() returns True, drag will be aborted and end()
            will not be called.
        - end : callback to clean up after draging, or None
        - moved : what to do with coordinates after transform() is called,
            default is set_pos(item, coords)
    """
    item.set_data("dragging", False)
    dwn = item.connect("button_press_event", drag_start, canvas, start, 
        transform, cursor)
    up = item.connect("button_release_event", drag_end, canvas, end)
    mv = item.connect("motion_notify_event", drag_move, canvas, transform,
        moved)
    item.set_data("drag_sigids", (up, dwn, mv))

def unmake_dragable(item):
    signals = item.get_data("drag_sigids")
    if signals:
        for sig in signals:
            item.disconnect(sig)

def make_resizable(canvas, item, transform=None, start=None, stop=None, 
    moved=None):
    pass

def unmake_resizable(item):
    pass

def normalize_rect(mouse_down, cur_pos):
    """Given two points, representing the upper left and bottom right 
    corners of a rectangle (the order is irrelevant), return the tuple
    ((x,y), (width, height))"""
    w, h = point_difference(cur_pos, mouse_down)
    x, y = mouse_down

    if w < 0:
        w = abs(w)
        x -= w
    if h < 0:
        h = abs(h)
        y -= h

    return (x, y), (w, h)

def object_select_cb(item, target, event, canvas, changed_cb):
    prev = canvas.get_data("selected_objects")
    if item in prev:
        return
    if (event.state & gtk.gdk.SHIFT_MASK):
        prev.add(item)
        changed_cb(prev, set())
    else:
        selected = set()
        selected.add(item)
        canvas.set_data("selected_objects", selected)
        changed_cb(selected, prev)
    return False

def make_selectable(canvas, object):
    """Make the object selectable with respect to canvas. This means
    that the item will be included in the current selection, and that
    clicking the object will select it. Must be called before 
    make_dragable, as it will block the action of this handler"""
    object.set_data("selectable", True)
    object.connect("button_press_event", object_select_cb, canvas,
        canvas.get_data("selection_callback"))

def delete_from_selection(canvas, item):
    selected = canvas.get_data("selected_objects")
    set_selection(canvas, selected - set([item]))

def set_selection(canvas, new):
    prev = canvas.get_data("selected_objects")
    deselected = prev - new
    canvas.set_data("selected_objects", new)
    canvas.get_data("selection_callback")(new, deselected)

def objects_under_marquee(event, canvas, overlap):
    pos, size = normalize_rect(canvas.mouse_down, event_coords(
        canvas, event))
    bounds = goocanvas.Bounds(*(pos + point_sum(pos, size)))
    selected = canvas.get_items_in_area(bounds, True, overlap, 
        True)
    if selected:
        return set((found for found in selected if 
            found.get_data("selectable")))
    return set()

def selection_start(item, target, event, canvas, marquee):
    root = canvas.get_root_item()
    root.add_child(marquee)
    cursor = event_coords(canvas, event)
    set_pos(marquee, cursor)
    canvas.selecting = True
    canvas.mouse_down = cursor
    set_pos(marquee, cursor) 
    set_size(marquee, (0, 0))
    return True

def selection_end(item, target, event, canvas, marquee, overlap, changed_cb):
    canvas.selecting = False
    marquee.remove()
    prev = canvas.get_data("selected_objects")
    selected = objects_under_marquee(event, canvas, overlap)
    canvas.set_data("selected_objects", selected)
    if changed_cb:
        changed_cb(selected, prev.difference(selected))
    return True

def selection_drag(item, target, event, canvas, marquee):
    if canvas.selecting:
        pos_, size_ = normalize_rect(canvas.mouse_down, 
            event_coords(canvas, event))
        set_size(marquee, size_)
        set_pos(marquee, pos_)
        return True
    return False


def manage_selection(canvas, marquee, overlap, changed_cb=None):
    """Keep track of the current selection in canvas, including
    * providing a rectangular selection marquee
    * tracking specific canvas objects
    Note: objects must be made selectable by calling make_selectable()
    on the object before they will be reported by any selection changes
    - overlap: True if you want items that merely intersect the 
        data field to be considered selected.
    - marquee: a goocanvas.Rectangle() to be used as the selection 
        marquee (really, any canvas item with x, y, width, height 
        properties). This object should not already be added to the
        canvas.
    - changed_cb: a callback with signature (selected, deselected)
      """

    canvas.selecting = False
    canvas.mouse_down = None
    canvas.set_data("selected_objects", set())
    canvas.set_data("selection_callback", changed_cb)
    root = canvas.get_root_item()
    root.connect("button_press_event", selection_start, canvas, marquee)
    root.connect("button_release_event", selection_end, canvas, marquee, overlap, changed_cb)
    root.connect("motion_notify_event", selection_drag, canvas, marquee)

class SmartGroup(goocanvas.Group):
    """Extends goocanvas.Group() with 
    through gobject properties x, y, and width/height"""
    __gtype_name__ = 'SmartGroup'

    x = gobject.property(type=float, default=0)
    y = gobject.property(type=float, default=0)
    width = gobject.property(type=float, default=0)
    height = gobject.property(type=float, default=0)

    def __init__(self, canvas=None, background=None, *args, **kwargs):
        goocanvas.Group.__init__(self, *args, **kwargs)
        self.children = {}
        self.signals = {}
        self.connect("notify::x", self.move_x_children)
        self.connect("notify::y", self.move_y_children)
        self.set_canvas(canvas)
        self.background = None
        self.set_background(background)

    def set_background(self, bg):
        if self.background:
            self.background.remove()
            goocanvas.Group.add_child(self, bg, 0)
        self.background = bg
        #TODO: move background beneath lowest item

    def set_canvas(self, canvas):
        self.canvas = canvas

    def move_x_children(self, object, prop):
        if self.background:
            self.background.props.x = self.x
        for child, (x, y) in self.children.items():
            child.set_property('x', self.x + x)

    def move_y_children(self, object, prop):
        if self.background:
            self.background.props.y = self.y
        for child, (x, y) in self.children.items():
            child.set_property('y', self.y + y)

    def update_width(self, obj, prop):
        def compute(c, p):
            return (c.get_property('width') + p[0])
        widths = (compute(c, p) for c, p in self.children.items())
        self.width = max(widths) if len(self.children) else float(0)
        if self.background:
            self.background.props.width = self.width

    def update_height(self, obj, prop):
        def compute(c, p):
            return (c.get_property('height') + p[1])
        heights = (compute(c, p) for c, p in self.children.items())
        self.height = max(heights) if len(self.children) else float(0)
        if self.background:
            self.background.props.height = self.height

    def set_child_pos(self, child, pos_):
        set_pos(child, point_sum(pos(self), pos_))
        self.children[child] = pos_

    def add_child(self, child, p=None):
        goocanvas.Group.add_child(self, child)
        cw = child.connect("notify::width", self.update_width)
        ch = child.connect("notify::height", self.update_height)
        self.signals[child] = (cw, ch)
        if not p:
            self.children[child] = pos(child)
        else:
            self.set_child_pos(child, p)
        self.update_width(None, None)
        self.update_height(None, None)

    def remove_child(self, child):
        goocanvas.Group.remove_child(self, child)
        for s in self.signals[child]:
            child.disconnect(s)
        del self.children[child]
        self.update_width(None, None)
        self.update_height(None, None)

class Text(goocanvas.ItemSimple, goocanvas.Item):
    '''A replacement for the stock goocanvas.Text widget, which
    doesn't have a height property, and the width property doesn't do
    quite what you'd expect it might. To set where the text should
    wrap, we provide this wrap_width, property. The width, height
    property clip the text appropriately.'''

    __gtype_name__ = 'SmartText'

    alignment = gobject.property(type=int)
    font = gobject.property(type=str)
    font_desc = gobject.property(type=gobject.TYPE_PYOBJECT,default=None)
    height = gobject.property(type=float)
    justification = gobject.property(type=int)
    text = gobject.property(type=str, default="")
    use_markup = gobject.property(type=bool, default=False)
    width = gobject.property(type=float)
    wrap_width = gobject.property(type=float)
    x = gobject.property(type=float)
    y = gobject.property(type=float)

    def __init__(self, *args, **kwargs):
        super(Text, self).__init__(*args, **kwargs)
        self.connect("notify::text", self.do_set_text)
        self.connect("notify::font", self.do_set_font)

    def do_simple_create_path(self, cr):
        context = pangocairo.CairoContext(cr)
        cr.move_to(self.x, self.y)
        layout = context.create_layout()
        layout.set_alignment(self.alignment)
        layout.set_font_description(self.font_desc)
        if not self.use_markup:
            layout.set_text(self.text)
        else:
            layout.set_markup(self.text)
        context.show_layout(layout)

    @gobject.property
    def layout(self):
        return self._layout

    def do_set_font(self, *args):
        self.font_desc = pango.FontDescription(self.font)
        self.changed(True)

    def do_set_text(self, *args):
        self.changed(True)
 
class List(SmartGroup):
    __gytpe_name__ = 'List'

    spacing = gobject.property(type=float, default=5.0)
    reorderable = gobject.property(type=bool, default=False)

    def __len__(self):
        return len(self.order)

    def __iter__(self):
        return self.order.__iter__()

    def __init__(self, *args, **kwargs):
        SmartGroup.__init__(self, *args, **kwargs)
        self.cur_pos = 0
        self.order = []
        if kwargs.has_key("spacing"):
            self.spacing = kwargs["spacing"]
        self.draging = None
        self.right = None
        self.left = None
        self.initial = None
        self.l_thresh = None
        self.r_thresh = None
        self.connect("notify::spacing", self._set_spacing)
        self.connect("notify::reorderable", self._set_reorderable)
    
    def _set_spacing(self, unused_object, unused_property):
        self.tidy()

    def _set_reorderable(self, unused_object, unused_property):
        if self.reorderable:
            for child in self.order:
                self.make_reorderable(child)
        else:
            for child in self.order:
                self.unmake_reorderable(child)
    
    def end(self, child):
        return self.position(child) + self.dimension(child)

    def tidy(self):
        cur = 0
        i = 0
        for child in self.order:
            self.set_child_pos(child, self.cur(cur))
            child.set_data("index", i)
            cur += self.spacing + self.dimension(child)
            i += 1
        self.cur_pos = cur
        if self.draging:
            self._set_drag_thresholds()
    
    def item_at(self, index):
        return self.order[index]

    def index(self, child):
        return child.get_data("index")

    def point_to_index(self, point):
        x, y = point
        bounds = goocanvas.Bounds(x, y, x, y)
        items = self.canvas.get_items_in_area(bounds, True, True, True)
        if items:
            return [i for i in items if i.get_data("index")][0]
        return None

    def _reorder(self, new_order):
        order = []
        for index in new_order:
            order.append(self.order[index])
        self.order = order

    def reorder(self, new_order):
        self._reorder(new_order)
        self.tidy()

    def _child_drag_start(self, child):
        child.raise_(None)
        self.draging = child
        self.dwidth = self.dimension(child)
        self._set_drag_thresholds()
        return True

    def _set_drag_thresholds(self):
        index = self.draging.get_data("index")
        self.left = None
        self.right = None
        if index > 0:
            self.left = self.order[index - 1]
            self.l_thresh = (self.end(self.left) - 0.5 * self.dimension(self.left)
                + self.spacing)
        if index < len(self.order) - 1:
            self.right = self.order[index + 1]
            self.r_thresh = (self.position(self.right) + 0.5 * self.dimension(self.right)
                - self.dimension(self.draging) + self.spacing)

    def _child_drag_end(self, child):
        self.left = None
        self.right = None
        self.initial = None
        self.draging = None
        self.tidy()
        return True

    def swap(self, a, b):
        a_index = a.get_data("index")
        b_index = b.get_data("index")
        self.order[a_index] = b
        self.order[b_index] = a
        a.set_data("index", b_index)
        b.set_data("index", a_index)
        self.tidy()
        return True

    def _child_drag(self, pos_):
        coord = self.coord(pos_)
        coord = (min(self.dimension(self) - self.dimension(self.draging),  max(0, coord)))
        if self.left:
            if coord <= self.l_thresh:
               self.swap(self.draging, self.left)
        if self.right:
            if coord >= self.r_thresh:
               self.swap(self.draging, self.right)
        return self.cur(coord)

    def remove_child(self, child):
        SmartGroup.remove_child(self, child)
        self.order.remove(child)
        if self.reorderable:
            self.unmake_reorderable(child)
        self.tidy()

    def remove_all(self):
        while len(self.order):
            self.remove_child(self.order[0])
    
    def make_reorderable(self, child):
        make_dragable(self.canvas, child, self._child_drag,
            self._child_drag_start, self._child_drag_end)

    def unmake_reorderable(self, child):
        unmake_dragable(child)

    def add_child(self, child):
        SmartGroup.add_child(self, child, self.cur(self.cur_pos))
        self.cur_pos += self.spacing + self.dimension(child)
        self.order.append(child)
        child.set_data("index", len(self.order) - 1)
        if self.reorderable:
            self.make_reorderable(child)

    def add(self, child):
        self.add_child(child)

    def insert_child(self, child, index):
        SmartGroup.add_child(self, child, self.cur(self.cur_pos))
        self.order.insert(index, child)
        self.tidy()

class VList(List):
    __gtype_name__ = 'VList'

    def __init__(self, *args, **kwargs):
        List.__init__(self, *args, **kwargs)
    
    def cur(self, value):
        return (0, value)

    def coord(self, point):
        return point[1]

    def position(self, child):
        return child.props.y

    def dimension(self, child):
        return child.props.height

class HList(List):
    __gtype_name__ = 'HList'

    def __init__(self, *args, **kwargs):
        List.__init__(self, *args, **kwargs)

    def coord(self, point):
        return point[0]

    def cur(self, value):
        return (value, 0)

    def position(self, child):
        return child.props.x

    def dimension(self, child):
        return child.props.width

