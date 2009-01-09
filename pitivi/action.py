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
import gst

# FIXME : define/document a proper hierarchy
class ActionError(Exception):
    pass

class Action(object, Signallable):
    """
    Pipeline action.

    Controls the elements of a C{Pipeline}, including their creation,
    activation, and linking.

    Subclasses can also offer higher-level actions that automatically create
    the Producers(s)/Consumer(s), thereby simplifying the work required to do
    a certain multimedia 'Action' (Ex: Automatically create the appropriate
    Consumer for rendering a producer stream to a file).

    @ivar state: Whether the action is active or not
    @type state: C{ActionState}
    @ivar producers: The producers controlled by this C{Action}.
    @type producers: List of C{ObjectFactory}
    @ivar consumers: The consumers controlled by this C{Action}.
    @type consumers: List of C{ObjectFactory}
    @ivar pipeline: The C{Pipeline} controlled by this C{Action}.
    @type pipeline: C{Pipeline}
    @cvar compatible_producers: The list of compatible factories that
    this C{Action} can handle as producers.
    @type compatible_producers: List of C{ObjectFactory}
    @cvar compatible_consumers: The list of compatible factories that
    this C{Action} can handle as consumers.
    @type compatible_consumers: List of C{ObjectFactory}
    """

    compatible_producers = []
    compatible_consumers = []

    __signals__ = {
        "state-changed" : ["state"]
        }

    def __init__(self):
        self.state = STATE_NOT_ACTIVE
        self.producers = []
        self.consumers = []
        self.pipeline = None
        self._links = [] # list of (producer, consumer, prodstream, consstream)

    #{ Activation methods

    def activate(self):
        """
        Activate the action.

        For each of the consumers/producers it will create the relevant
        GStreamer objects for the Pipeline (if they don't already exist).

        @precondition: Must be set to a C{Pipeline}.
        @precondition: All consumers/producers must be set on the C{Pipeline}.

        @return: Whether the C{Action} was activated (True) or not.
        @rtype: L{bool}
        @raise ActionError: If the C{Action} isn't set to a C{Pipeline}, or one
        of the consumers/producers isn't set on the Pipeline.
        """
        if self.pipeline == None:
            raise ActionError("Action isn't set to a Pipeline")
        if self.state == STATE_ACTIVE:
            gst.debug("Action already activated, returning")
            return
        # FIXME : Add an overrideable method for subclasses to add some
        # consumers or producers, or modify/set the properties of those.
        for p in self.producers:
            if not p in self.pipeline.factories:
                raise ActionError("One of the Producers isn't set on the Pipeline")
        for p in self.consumers:
            if not p in self.pipeline.factories:
                raise ActionError("One of the Consumers isn't set on the Pipeline")
        # TODO : Create bins (if needed), tees, queues, link
        self.state = STATE_ACTIVE
        self.emit('state-changed', self.state)
        raise NotImplementedError

    def deactivate(self):
        """
        De-activate the Action.

        @return: Whether the C{Action} was de-activated (True) or not.
        @rtype: L{bool}
        """
        if self.state == STATE_NOT_ACTIVE:
            gst.debug("Action already deactivated, returning")
        if self.pipeline == None:
            gst.warning("Attempting to deactivate Action without a Pipeline")
            # yes, gracefully return
            return
        # TODO : unlink
        # TODO : remove queues
        # TODO : remove tees
        self.state = STATE_NOT_ACTIVE
        self.emit('state-changed', self.state)
        raise NotImplementedError

    def isActive(self):
        """
        Whether the Action is active or not

        @return: True if the Action is active.
        @rtype: L{bool}
        """
        return self.state == STATE_ACTIVE

    #{ Pipeline methods

    def setPipeline(self, pipeline):
        """
        Set the C{Action} on the given C{Pipeline}.

        @param pipeline: The C{Pipeline} to set the C{Action} onto.
        @type pipeline: C{Pipeline}
        @warning: This method should only be used by C{Pipeline}s when the given
        C{Action} is set on them.
        @precondition: The C{Action} must not be set to any other C{Pipeline}
        when this method is called.
        @raise ActionError: If the C{Action} is active or the pipeline is set to
        a different C{Pipeline}.
        """
        if self.pipeline == pipeline:
            gst.debug("New pipeline is the same as the currently set one")
            return
        if self.pipeline != None:
            raise ActionError("Action already set to a Pipeline")
        if self.state != STATE_NOT_ACTIVE:
            raise ActionError("Action is active, can't change Pipeline")
        self.pipeline = pipeline

    def unsetPipeline(self):
        """
        Remove the C{Action} from the currently set C{Pipeline}.

        @warning: This method should only be used by C{Pipeline}s when the given
        C{Action} is removed from them.
        @precondition: The C{Action} must be deactivated before it can be removed from a
        C{Pipeline}.
        @raise ActionError: If the C{Action} is active.
        """
        if self.state != STATE_NOT_ACTIVE:
            raise ActionError("Action is active, can't unset Pipeline")
        self.pipeline = None

    #{ ObjectFactory methods

    def setProducers(self, *producers):
        """
        Set the given C{ObjectFactories} as producers of the C{Action}.

        @type producers: List of C{ObjectFactory}
        @raise ActionError: If the C{Action} is active.
        """
        if self.state != STATE_NOT_ACTIVE:
            raise ActionError("Action is active, can't add Producers")
        raise NotImplementedError

    def removeProducers(self, *producers):
        """
        Remove the given C{ObjectFactories} as producers of the C{Action}.

        @type producers: List of C{ObjectFactory}
        @raise ActionError: If the C{Action} is active.
        """
        if self.state != STATE_NOT_ACTIVE:
            raise ActionError("Action is active, can't remove Producers")
        raise NotImplementedError

    def setConsumers(self, *consumers):
        """
        Set the given C{ObjectFactories} as consumers of the C{Action}.

        @type consumers: List of C{ObjectFactory}
        @raise ActionError: If the C{Action} is active.
        """
        if self.state != STATE_NOT_ACTIVE:
            raise ActionError("Action is active, can't add Producers")
        raise NotImplementedError

    def removeConsumers(self, *consumers):
        """
        Remove the given C{ObjectFactories} as consumers of the C{Action}.

        @type consumers: List of C{ObjectFactory}
        @raise ActionError: If the C{Action} is active.
        """
        if self.state != STATE_NOT_ACTIVE:
            raise ActionError("Action is active, can't remove Consumers")
        raise NotImplementedError

    #{ Link methods

    def setLink(self, producer, consumer, producerstream=None,
                consumerstream=None):
        """
        Set a relationship (link) between producer and consumer.

        If the Producer and/or Consumer isn't already set to this C{Action},
        this method will attempt to add them.

        @param producer: The producer we wish to link.
        @type producer: C{ObjectFactory}
        @param consumer: The consumer we wish to link.
        @type consumer: C{ObjectFactory}
        @param producerstream: The C{Stream} to use from the producer. If not
        specified, the C{Action} will figure out a compatible C{Stream} between
        the producer and consumer.
        @type producerstream: C{Stream}
        @param consumerstream: The C{Stream} to use from the consumer. If not
        specified, the C{Action} will figure out a compatible C{Stream} between
        the consumer and consumer.
        @type consumerstream: C{Stream}
        @raise ActionError: If the C{Action} is active.
        @raise ActionError: If the producerstream isn't available on the
        producer.
        @raise ActionError: If the consumerstream isn't available on the
        consumer.
        @raise ActionError: If the producer and consumer are incompatible.
        """
        # If streams are specified, make sure they exist in their respective factories
        # Make sure producer and consumer are compatible
        # If needed, add producer and consumer to ourselves
        # store the link
        raise NotImplementedError

    def removeLink(self, producer, consumer, producerstream=None,
                   consumerstream=None):
        """
        Remove a relationship (link) between producer and consumer.

        @param producer: The producer we wish to unlink.
        @type producer: C{ObjectFactory}
        @param consumer: The consumer we wish to unlink.
        @type consumer: C{ObjectFactory}
        @param producerstream: The C{Stream} to use from the producer. If not
        specified, the C{Action} will figure out a compatible C{Stream} between
        the producer and consumer.
        @type producerstream: C{Stream}.
        @param consumerstream: The C{Stream} to use from the consumer. If not
        specified, the C{Action} will figure out a compatible C{Stream} between
        the consumer and consumer.
        @type consumerstream: C{Stream}.
        @raise ActionError: If the C{Action} is active.
        @raise ActionError: If the producerstream wasn't used in any links.
        @raise ActionError: If the consumerstream wasn't used in any links.
        """
        # If producer and consumer are not available, raise error
        # Search for the given link
        # If there are multiple compatible links, raise an Error
        # finally, remove link
        raise NotImplementedError
