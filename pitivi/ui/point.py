from itertools import izip

class Point(tuple):

    def __new__(cls, x, y):
        return tuple.__new__(cls, (x, y))

    def __pow__(self, scalar):
        """Returns the scalar multiple self, scalar"""
        return Point(self[0] * scalar, self[1] * scalar)

    def __rpow__(self, scalar):
        """Returns the scalar multiple of self, scalar"""
        return self ** scalar

    def __mul__(self, p2):
        return Point(*(a * b for a, b in izip(self, p2)))

    def __div__(self, other):
        return Point(*(a / b for a, b in izip(self, p2)))

    def __floordiv__(self, scalar):
        """Returns the scalar division of self and scalar"""
        return Point(self[0] / scalar, self[1] / scalar)

    def __add__(self, p2):
        """Returns the 2d vector sum self + p2"""
        return Point(*(a + b for a, b in izip(self, p2)))

    def __sub__(self, p2):
        """Returns the 2-dvector difference self - p2"""
        return Point(*(a - b for a, b in izip(self, p2)))

    def __abs__(self):
        return Point(*(abs(a) for a in self))

    @classmethod
    def from_item_bounds(self, item):
        bounds = item.get_bounds()
        return Point(bounds.x1, bounds.y1), Point(bounds.x2, bounds.y2)

    @classmethod
    def from_widget_bounds(self, widget):
        x1, y1, x2, y2 = widget.get_bounds()
        return Point(x1, y1), Point(x2, y2)
