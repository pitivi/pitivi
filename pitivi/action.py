# PiTiVi , Non-linear video editor
#
#       pitivi/action.py
#
# Copyright (c) 2009, Edward Hervey <bilboed@bilboed.com>
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
Pipeline actions
"""

"""@var states: Something
@type states: C{ActionState}"""
states = (STATE_NOT_ACTIVE,
          STATE_ACTIVE) = range(2)

from pitivi.signalinterface import Signallable

class Action(object, Signallable):
    """
    Pipeline action.

    Controls the linking of Producers and Consumers in a
    Pipeline.

    @ivar state: Whether the action is active or not
    @type state: C{ActionState}
    @ivar producers: The producers controlled by this C{Action}.
    @type producers: List of C{ObjectFactory}
    @ivar consumers: The consumers controlled by this C{Action}.
    @type consumers: List of C{ObjectFactory}
    @ivar pipeline: The C{Pipeline} controlled by this C{Action}.
    @type pipeline: C{Pipeline}
    """

    __signals__ = {
        "state-changed" : ["state"]
        }

    def __init__(self):
        self.state = STATE_NOT_ACTIVE
        self.producers = []
        self.consumers = []
        self.pipeline = None

    #{ state methods

    def activate(self):
        """
        Activate the action.

        For each of the consumers/producers it will create the relevant
        GStreamer objects for the Pipeline (if they don't already exist).

        @precondition: Must be set to a C{Pipeline}

        @return: Whether the C{Action} was activated (True) or not.
        @rtype: L{bool}
        """
        raise NotImplementedError

    def deactivate(self):
        """
        De-activate the Action.

        @return: Whether the C{Action} was de-activated (True) or not.
        @rtype: L{bool}
        """
        raise NotImplementedError

    #{ Pipeline methods

    def setPipeline(self, pipeline):
        """
        Set the C{Action} on the given C{Pipeline}.

        @precondition: The C{Action} must not be set to any other C{Pipeline}
        when this method is called.
        """
        raise NotImplementedError

    def unsetPipeline(self):
        """
        Remove the C{Action} from the currently set C{Pipeline}.

        @precondition: The C{Action} must be deactivated before it can be removed from a
        C{Pipeline}.
        """
        raise NotImplementedError

    #{ ObjectFactory methods

    def setProducers(self, *producers):
        """
        Set the given C{ObjectFactories} as producers of the C{Action}.

        @type producers: List of C{ObjectFactory}
        """
        raise NotImplementedError

    def setConsumers(self, *consumers):
        """
        Set the given C{ObjectFactories} as consumers of the C{Action}.

        @type consumers: List of C{ObjectFactory}
        """
        raise NotImplementedError
