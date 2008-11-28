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

    ## utility functions for working with points
    @classmethod
    def from_event(cls, canvas, event):
        """returns the coordinates of an event"""
        return Point(*canvas.convert_from_pixels(event.x, event.y))

    def from_item_space(self, canvas, item):
        return Point(*canvas.convert_from_item_space(item, self[0], self[1]))

    @classmethod
    def from_item_event(cls, canvas, item, event):
        return Point.from_event(canvas, event).from_item_space(canvas, item)
