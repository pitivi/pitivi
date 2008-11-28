from pitivi.receiver import Receiver, handler
from point import Point

# Controllers are reusable and implement specific behaviors. Currently this
# Includes only click, and drag. Multiple controllers could be attached to a
# given view, but might interfere with each other if they attempt to handle
# the same set of signals. It is probably better to define a new controller
# that explictly combines the functionality of both when custom behavior is
# desired.

#TODO: refactor to handle cursors

class BaseController(Receiver):

    def __init__(self, model=None, view=None):
        Receiver.__init__(self)
        self.model = model
        self.view = view

class Controller(BaseController):

    """A controller which implements drag-and-drop bahavior on connected view
    objects. Subclasses may override the drag_start, drag_end, pos, and
    set_pos methods"""

    _dragging = None
    _canvas = None
    _mouse_down = None
    _ptr_within = False
    _last_click = None

    def __init__(self, model=None, view=None):
        BaseController.__init__(self, model, view)

## signal handlers

    @handler("view", "enter_notify_event")
    def enter_notify_event(self, item, target, event):
        self.enter(item, target)
        self._ptr_within = True
        return True

    @handler("view", "leave_notify_event")
    def leave_notify_event(self, item, target, event):
        self._ptr_within = False
        if not self._dragging:
            self.leave(item, target)
        return True

    @handler("view", "button_press_event")
    def button_press_event(self, item, target, event):
        if not self._canvas:
            self._canvas = item.get_canvas()
        self._dragging = target
        self._mouse_down = self.pos - self.transform(Point.from_event,
            canvas, event)
        self._drag_start(item, target, event)
        return True

    @handler("view", "motion_notify_event")
    def motion_notify_event(self, item, target, event):
        if self._dragging:
            self.set_pos(self._dragging, 
                self.transform(self._mouse_down + Point.from_event(canvas,
                    event)))
            return True
        return False

    @handler("view", "button_release_event")
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
                self.double_click(event_coords(self._canvas, event))
            else:
                self.click(event_coords(self._canvas, event))
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

    def pos(self, obj):
        return obj.props.x, obj.props.y

    def transform(self, pos):
        return pos

    def enter(self, item, target):
        if not self._dragging:
            self._view.focus()

    def leave(self, item, target):
        if not self._dragging:
            self._view.normal()

class ClickController(Controller):

    def set_pos(self, obj, pos):
        pass

