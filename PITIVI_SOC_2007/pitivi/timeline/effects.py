# PiTiVi , Non-linear video editor
#
#       pitivi/timeline/effects.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""
Timeline Effect object
"""

import gst
from objects import TimelineObject

class TimelineEffect(TimelineObject):
    """
    Base class for effects (1->n input(s))
    """

    __data_type__ = "timeline-effect"

    def __init__(self, nbinputs=1, **kw):
        self.nbinputs = nbinputs
        TimelineObject.__init__(self, **kw)

    def _makeGnlObject(self):
        gnlobject = gst.element_factory_make("gnloperation", "operation-" + self.name)
        self._setUpGnlOperation(gnlobject)
        return gnlobject

    def _setUpGnlOperation(self, gnlobject):
        """ fill up the gnloperation for the first go """
        raise NotImplementedError

class TimelineSimpleEffect(TimelineEffect):
    """
    Simple effects (1 input)
    """

    __data_type__ = "timeline-simple-effect"

    def __init__(self, factory, **kw):
        self.factory = factory
        TimelineEffect.__init__(self, **kw)


class TimelineTransition(TimelineEffect):
    """
    Transition Effect
    """
    source1 = None
    source2 = None

    __data_type__ = "timeline-transition"

    def __init__(self, factory, source1=None, source2=None, **kw):
        self.factory = factory
        TimelineEffect.__init__(self, nbinputs=2, **kw)
        self.setSources(source1, source2)

    def setSources(self, source1, source2):
        """ changes the sources in between which the transition lies """
        self.source1 = source1
        self.source2 = source2


class TimelineComplexEffect(TimelineEffect):
    """
    Complex Effect
    """

    __data_type__ = "timeline-complex-effect"

    def __init__(self, factory, **kw):
        self.factory = factory
        # Find out the number of inputs
        nbinputs = 2
        TimelineEffect.__init__(self, nbinputs=nbinputs, **kw)
