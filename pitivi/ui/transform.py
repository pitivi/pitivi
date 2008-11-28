# This is an idea i got from reading an article on SmallTalk MVC. 
# FIXME/TODO: do we really need windoing transformation? or would just the
# coordinate system class be enough. Then you could have
# view.cs.convertTo(point, model.cs) or something similar.

class WindowingTransformation(object):

    """Represents a transformation between two arbitrary 2D coordinate system"""

    class System(object):

        def __init__(self, *args, **kwargs):
            object.__init__(self)

        def setBounds(self, min, max):
            self._min = min
            self._max = max
            self._range = point_difference(max, min)

        def getMin(self):
            return self._min

        def getRange(self):
            return self._range

        def convertTo(self, point, other):
            # ((point - min) * other.range / (self.range)) + other.min) 
            return point_sum(
                point_div(
                    point_mul(
                        point_difference(point, self._min), 
                        other.getRange()),
                self._range), 
                other.getMin())

    def __init__(self, A=None, B=None, *args, **kwargs):
        super(WindowingTransformation, self).__init__(*args, **kwargs)
        self._A = self.System()
        self._B = self.System()

    def setBounds(self, a, b):
        self._A.setBounds(*a)
        self._B.setBounds(*b)

    def aToB(self, point):
        return self._A.convertTo(point, self._B)

    def bToA(self, point):
        return self._B.convertTo(point, self._A)

