from itertools import izip

class Point(tuple):
    
    def __new__(cls, x, y):
        return tuple.__new__(cls, (x, y))

    def __pow__(p1, scalar):
        """Returns the scalar multiple p1, scalar"""
        return Point(p1[0] * scalar, p1[1] * scalar)

    def __rpow__(p2, scalar):
        """Returns the scalar multiple of p2, scalar"""
        return p2 ** scalar

    def __mul__(p1, p2):
        return Point(*(a * b for a, b in izip(p1, p2)))

    def __div__(self, other):
        return Point(*(a / b for a, b in izip(p1, p2)))

    def __floordiv__(p1, scalar):
        """Returns the scalar division of self and scalar"""
        return Point(p1[0] / scalar, p1[1] / scalar)

    def __add__(p1, p2):
        """Returns the 2d vector sum p1 + p2"""
        return Point(*(a + b for a, b in izip(p1, p2)))

    def __sub__(p1, p2):
        """Returns the 2-dvector difference p1 - p2"""
        return Point(*(a - b for a, b in izip(p1, p2)))

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
