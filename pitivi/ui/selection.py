
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


