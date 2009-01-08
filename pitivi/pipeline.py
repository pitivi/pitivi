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
from pitivi.action import ActionError
import gst

(STATE_NULL,
 STATE_READY,
 STATE_PAUSED,
 STATE_PLAYING) = (gst.STATE_NULL, gst.STATE_READY, gst.STATE_PAUSED, gst.STATE_PLAYING)

# FIXME : define/document a proper hierarchy
class PipelineError(Exception):
    pass

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

    __signals__ = {
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
        self._bus = self._pipeline.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect("message", self._busMessageCb)
        self._factories = {} # factory => gst.Bin
        self._tees = {} # (producerfactory, stream) => gst.Element ("tee")
        self._queues = {} # (consumerfactory, stream) => gst.Element ("queue")
        self.actions = []
        self._state = STATE_NULL

    def addAction(self, action):
        """
        Add the given C{Action} to the Pipeline.

        @return: The C{Action} that was set
        @rtype: C{Action}
        @raise PipelineError: If the given C{Action} is already set to another
        Pipeline
        """
        gst.debug("action:%r" % action)
        if action in self.actions:
            gst.debug("Action is already used by this Pipeline, returning")
            return action

        if action.pipeline != None:
            raise PipelineError("Action is set to another pipeline (%r)" % action.pipeline)

        action.setPipeline(self)
        gst.debug("Adding action to list of actions")
        self.actions.append(action)
        gst.debug("Emitting 'action-added' signal")
        self.emit("action-added", action)
        gst.debug("Returning")
        return action

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
        gst.debug("action:%r" % action)
        for ac in self.actions:
            if type(action) == type(ac):
                gst.debug("We already have a %r Action : %r" % (type(action), ac))
                return ac
        return self.addAction(action)

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
        @raise PipelineError: If C{Action} is activated or C{Pipeline} is not
        READY or NULL
        """
        gst.debug("action:%r" % action)
        if not action in self.actions:
            gst.debug("action not controlled by this Pipeline, returning")
            return
        if self._state in [STATE_PAUSED, STATE_PLAYING]:
            raise PipelineError("Actions can not be in a PLAYING or PAUSED Pipeline")
        try:
            action.unsetPipeline()
        except ActionError:
            raise PipelineError("Can't unset Action from Pipeline")
        self.actions.remove(action)
        self.emit('action-removed', action)

    def setState(self, state):
        """
        Set the C{Pipeline} to the given state.

        @raises PipelineError: If the C{gst.Pipeline} could not be changed to
        the requested state.
        """
        gst.debug("state:%r" % state)
        if self._state == state:
            gst.debug("Already at the required state, returning")
            return
        res = self._pipeline.set_state(state)
        if res == gst.STATE_CHANGE_FAILURE:
            raise PipelineError("Failure changing state of the gst.Pipeline")

    @property
    def state(self):
        """
        The state of the C{Pipeline}.

        @warning: This doesn't query the underlying C{gst.Pipeline} but returns the cached
        state.
        """
        gst.debug("Returning state %r" % self._state)
        return self._state

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

    ## Private methods

    def _busMessageCb(self, unused_bus, message):
        gst.info("%s [%r]" % (message.type, message.src))
        if message.type == gst.MESSAGE_EOS:
            self.emit('eos')
        elif message.type == gst.MESSAGE_STATE_CHANGED and message.src == self._pipeline:
            prev, new, pending = message.parse_state_changed()
            gst.debug("Pipeline change state prev:%r, new:%r, pending:%r" % (prev, new, pending))
            if self._state != new:
                self._state = new
                self.emit('state-changed', self._state)
        elif message.type == gst.MESSAGE_ERROR:
            error, detail = message.parse_error()
            self._handleErrorMessage(error, detail, message.src)
