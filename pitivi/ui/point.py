class Point(tuple):
    
    def __new__(self, x, y):
        return Point(x, y)

    def __mul__(p1, p2):
        """Returns the 2-dvector difference p1 - p2"""
        p1_x, p1_y = p1
        p2_x, p2_y = p2
        return Point(p1_x - p2_x, p1_y - p2_y)

    def __pow__(p1, scalar):
        """Returns the scalar multiple p1, scalar"""
        return Point(p1[0] * scalar, p1[1] * scalar)

    # needed to support the case where you have <number> * point
    def __rpow__(p2, scalar):
        """Returns the scalar multiple of p2, scalar"""
        return p2 ** scalar

    def __div__(self, other):
        p1_x, p1_y = p1
        p2_x, p2_y = p2
        return Point(p1_x / p2_x, p1_y / p2_y)

    def __floordiv__(p1, scalar):
        """Returns the scalar division of self and scalar"""
        return Point(p1[0] / scalar, p1[1] / scalar)

    def __add__(p1, p2):
        """Returns the 2d vector sum p1 + p2"""
        p1_x, p1_y = p1
        p2_x, p2_y = p2
        return Point(p1_x + p2_x, p1_y + p2_y)

    def __sub__(p1, p2):
        """Returns the 2-dvector difference p1 - p2"""
        p1_x, p1_y = p1
        p2_x, p2_y = p2
        return Point(p1_x - p2_x, p1_y - p2_y)

    ## utility functions for working with points
    @classmethod
    def from_event(cls, canvas, event):
        """returns the coordinates of an event"""
        return Point(*canvas.convert_from_pixels(event.x, event.y))

