 
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

