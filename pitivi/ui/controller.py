from pitivi.receiver import receiver, handler
from point import Point

# Controllers are reusable and implement specific behaviors. Currently this
# Includes only click, and drag. Multiple controllers could be attached to a
# given view, but might interfere with each other if they attempt to handle
# the same set of signals. It is probably better to define a new controller
# that explictly combines the functionality of both when custom behavior is
# desired.

#TODO: refactor to handle cursors

class Controller(object):

    """A controller which implements drag-and-drop bahavior on connected view
    objects. Subclasses may override the drag_start, drag_end, pos, and
    set_pos methods"""
    
    _view = receiver()

    _dragging = None
    _canvas = None
    _ptr_within = False
    _last_click = None
    _mousedown = None

    def __init__(self, view=None):
        object.__init__(self)
        self._view = view

## convenience functions

    def from_event(self, event):
        """returns the coordinates of an event"""
        return Point(*self._canvas.convert_from_pixels(event.x, event.y))

    def from_item_event(self, item, event):
        return Point(*self._canvas.convert_from_item_space(item,
            *self.from_event(event)))

    def pos(self, item):
        bounds = item.get_bounds()
        return Point(bounds.x1, bounds.y1)

## signal handlers

    @handler(_view, "enter_notify_event")
    def enter_notify_event(self, item, target, event):
        self.enter(item, target)
        self._ptr_within = True
        return True

    @handler(_view, "leave_notify_event")
    def leave_notify_event(self, item, target, event):
        self._ptr_within = False
        if not self._dragging:
            self.leave(item, target)
        return True

    @handler(_view, "button_press_event")
    def button_press_event(self, item, target, event):
        if not self._canvas:
            self._canvas = item.get_canvas()
        self._mousedown = self.pos(item) - self.transform(self.from_item_event(
            item, event))
        self._dragging = target
        self._drag_start(item, target, event)
        return True

    @handler(_view, "motion_notify_event")
    def motion_notify_event(self, item, target, event):
        if self._dragging:
            self.set_pos(self._dragging, 
                self.transform(self._mousedown + self.from_item_event(item,
                    event)))
            return True
        return False

    @handler(_view, "button_release_event")
    def button_release_event(self, item, target, event):
        self._drag_end(item, self._dragging, event)
        self._dragging = None
        return True

## internal callbacks

    def _drag_start(self, item, target, event):
        self._view.activate()
        self.drag_start()

    def _drag_end(self, item, target, event):
        self.drag_end()
        if self._ptr_within:
            self._view.focus()
            if self._last_click and (event.time - self._last_click < 400):
                self.double_click(Point.from_event(self._canvas, event))
            else:
                self.click(Point.from_event(self._canvas, event))
            self._last_click = event.time
        else:
            self._view.normal()

## protected interface for subclasses

    def click(self, pos):
        pass

    def double_click(self, pos):
        pass
 
    def drag_start(self):
        pass

    def drag_end(self):
        pass

    def set_pos(self, obj, pos):
        obj.props.x, obj.props.y = pos

    def transform(self, pos):
        return pos

    def enter(self, item, target):
        if not self._dragging:
            self._view.focus()

    def leave(self, item, target):
        if not self._dragging:
            self._view.normal()
