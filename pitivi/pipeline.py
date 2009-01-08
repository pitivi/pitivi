# PiTiVi , Non-linear video editor
#
#       pitivi/pipeline.py
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
High-level pipelines
"""
from pitivi.signalinterface import Signallable
import gst
(NULL,
 READY,
 PAUSED,
 PLAYING) = (gst.STATE_NULL, gst.STATE_READY, gst.STATE_PAUSED, gst.STATE_PLAYING)

# TODO : Add a convenience method to automatically do the following process:
#  * Creating a Pipeline
#  * Creating an Action
#  * Setting the Action on the Pipeline
#  * (optional) Adding producer/consumer factories in the Pipeline
#  * (optional) Setting the producer/consumer on the Action
#  * (optional) Activating the Action
# Maybe that convenience method could be put in a higher-level module, like the
# one that handles all the Pipelines existing in the application.

class Pipeline(object, Signallable):
    """
    A container for all multimedia processing.

    You can set C{Action}s on it.

    @ivar state: The current state.
    @type state: C{gst.State}
    @ivar actions: The Action(s) currently used.
    @type actions: List of C{Action}
    """

    __signal__ = {
        "action-added" : ["action"],
        "action-removed" : ["action"],
        "factory-added" : ["factory"],
        "factory-removed" : ["factory"],
        "state-changed" : ["state"],
        "position" : ["position"],
        "eos" : [],
        "error" : ["message", "details"]
        }

    def __init__(self):
        self._pipeline = gst.Pipeline()
        # TODO : Listen to the pipeline bus for state changes
        self._factories = {} # factory => gst.Bin
        self._tees = {} # (producerfactory, stream) => gst.Element ("tee")
        self._queues = {} # (consumerfactory, stream) => gst.Element ("queue")
        self.actions = []
        self._state = None

    def addAction(self, action):
        """
        Add the given C{Action} to the Pipeline.

        @return: The C{Action} that was set
        @rtype: C{Action}
        """
        raise NotImplementedError

    def setAction(self, action):
        """
        Set the given C{Action} on the C{Pipeline}.
        If an C{Action} of the same type already exists in the C{Pipeline} the
        C{Action} will not be set.

        @param action: The C{Action} to set on the C{Pipeline}
        @type action: C{Action}
        @rtype: C{Action}
        @return: The C{Action} used. Might be different from the one given as
        input.
        """
        raise NotImplementedError

    def removeAction(self, action):
        """
        Remove the given C{Action} from the C{Pipeline}.

        @precondition: Can only be done if both:
         - The C{Pipeline} is in READY or NULL
         - The C{Action} is de-activated

        @param action: The C{Action} to remove from the C{Pipeline}
        @type action: C{Action}
        @rtype: L{bool}
        @return: Whether the C{Action} was removed from the C{Pipeline} or not.
        """
        raise NotImplementedError

    def _setState(self, state):
        """
        Set the C{Pipeline} to the given state.
        """
        raise NotImplementedError

    def _getState(self):
        """
        Returns the state of the C{Pipeline}.

        This doesn't query the underlying C{gst.Pipeline} but returns the cached
        state.
        """
        return self._state

    state = property(_getState, _setState,
                     doc="""The C{gst.State} of the C{Pipeline}""")

    def addFactory(self, *factories):
        """
        Adds the given C{ObjectFactory} to be used in the C{Pipeline}.

        @param factories: The C{ObjectFactory}s to add
        @type factories: C{ObjectFactory}
        """
        raise NotImplementedError

    def removeFactory(self, *factories):
        """
        Removes the given C{ObjectFactory}s from the C{Pipeline}.

        @precondition: The C{Pipeline} state must be READY or NULL.

        @param factories: The C{ObjectFactory}s to remove.
        @type factories: C{ObjectFactory}
        """
        raise NotImplementedError

    def getPosition(self, format=gst.FORMAT_TIME):
        """
        Get the current position of the C{Pipeline}.

        @param format: The format to return the current position in
        @type format: C{gst.Format}
        @return: The current position or gst.CLOCK_TIME_NONE
        @rtype: L{long}
        """
        raise NotImplementedError

    def activatePositionListener(self, interval=300):
        """
        Activate the position listener.

        When activated, the Pipeline will emit the 'position' signal at the
        specified interval when it is the PLAYING or PAUSED state.

        @param interval: Interval between position queries in milliseconds
        @type interval: L{int} milliseconds
        @return: Whether the position listener was activated or not
        @rtype: L{bool}
        """
        raise NotImplementedError

    def deactivatePositionListener(self):
        """
        De-activates the position listener.
        """
        raise NotImplementedError

    def seek(self, position, format=gst.FORMAT_TIME):
        """
        Seeks in the C{Pipeline} to the given position.

        @param position: Position to seek to
        @type position: L{long}
        @param format: The C{Format} of the seek position
        @type format: C{gst.Format}
        @return: Whether the seek succeeded or not
        @rtype: L{bool}
        """
        raise NotImplementedError

    def play(self):
        """
        Sets the C{Pipeline} to PLAYING
        """
        raise NotImplementedError

    def pause(self):
        """
        Sets the C{Pipeline} to PAUSED
        """
        raise NotImplementedError

    def release(self):
        """
        Release the C{Pipeline} and all used C{ObjectFactory} and
        C{Action}s.

        Call this method when the C{Pipeline} is no longer used. Forgetting to do
        so will result in memory loss.

        @postcondition: The C{Pipeline} will no longer be usable.
        """
        raise NotImplementedError
