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
from pitivi.factories.base import SourceFactory, SinkFactory
import gst

# TODO : Create a convenience class for Links

# FIXME : define/document a proper hierarchy
class ActionError(Exception):
    pass

class Action(object, Signallable):
    """
    Pipeline action.

    Controls the elements of a L{Pipeline}, including their creation,
    activation, and linking.

    Subclasses can also offer higher-level actions that automatically create
    the Producers(s)/Consumer(s), thereby simplifying the work required to do
    a certain multimedia 'Action' (Ex: Automatically create the appropriate
    Consumer for rendering a producer stream to a file).

    @ivar state: Whether the action is active or not
    @type state: C{ActionState}
    @ivar producers: The producers controlled by this L{Action}.
    @type producers: List of L{ObjectFactory}
    @ivar consumers: The consumers controlled by this L{Action}.
    @type consumers: List of L{ObjectFactory}
    @ivar pipeline: The L{Pipeline} controlled by this L{Action}.
    @type pipeline: L{Pipeline}
    @cvar compatible_producers: The list of compatible factories that
    this L{Action} can handle as producers.
    @type compatible_producers: List of L{ObjectFactory}
    @cvar compatible_consumers: The list of compatible factories that
    this L{Action} can handle as consumers.
    @type compatible_consumers: List of L{ObjectFactory}
    """

    compatible_producers = [ SourceFactory ]
    compatible_consumers = [ SinkFactory ]

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

        @precondition: Must be set to a L{Pipeline}.
        @precondition: All consumers/producers must be set on the L{Pipeline}.

        @return: Whether the L{Action} was activated (True) or not.
        @rtype: L{bool}
        @raise ActionError: If the L{Action} isn't set to a L{Pipeline}, or one
        of the consumers/producers isn't set on the Pipeline.
        @raise ActionError: If some producers or consumers remain unused.
        """
        if self.pipeline == None:
            raise ActionError("Action isn't set to a Pipeline")
        if self.state == STATE_ACTIVE:
            gst.debug("Action already activated, returning")
            return
        # FIXME : Maybe add an option to automatically add producer/consumer
        # to the pipeline
        for p in self.producers:
            if not p in self.pipeline.factories:
                raise ActionError("One of the Producers isn't set on the Pipeline")
        for p in self.consumers:
            if not p in self.pipeline.factories:
                raise ActionError("One of the Consumers isn't set on the Pipeline")
        self._ensurePipelineObjects()
        self.state = STATE_ACTIVE
        self.emit('state-changed', self.state)

    def deactivate(self):
        """
        De-activate the Action.

        @return: Whether the L{Action} was de-activated (True) or not.
        @rtype: L{bool}
        """
        if self.state == STATE_NOT_ACTIVE:
            gst.debug("Action already deactivated, returning")
        if self.pipeline == None:
            gst.warning("Attempting to deactivate Action without a Pipeline")
            # yes, gracefully return
            return
        self._releasePipelineObjects()
        self.state = STATE_NOT_ACTIVE
        self.emit('state-changed', self.state)

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
        Set the L{Action} on the given L{Pipeline}.

        @param pipeline: The L{Pipeline} to set the L{Action} onto.
        @type pipeline: L{Pipeline}
        @warning: This method should only be used by L{Pipeline}s when the given
        L{Action} is set on them.
        @precondition: The L{Action} must not be set to any other L{Pipeline}
        when this method is called.
        @raise ActionError: If the L{Action} is active or the pipeline is set to
        a different L{Pipeline}.
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
        Remove the L{Action} from the currently set L{Pipeline}.

        @warning: This method should only be used by L{Pipeline}s when the given
        L{Action} is removed from them.
        @precondition: The L{Action} must be deactivated before it can be removed from a
        L{Pipeline}.
        @raise ActionError: If the L{Action} is active.
        """
        if self.state != STATE_NOT_ACTIVE:
            raise ActionError("Action is active, can't unset Pipeline")
        self.pipeline = None

    #{ ObjectFactory methods

    def addProducers(self, *producers):
        """
        Add the given L{ObjectFactory}s as producers of the L{Action}.

        @type producers: List of L{ObjectFactory}
        @raise ActionError: If the L{Action} is active.
        """
        gst.debug("producers:%r" % producers)
        if self.state != STATE_NOT_ACTIVE:
            raise ActionError("Action is active, can't add Producers")
        # make sure producers are of the valid type
        if self.compatible_producers != []:
            for p in producers:
                val = False
                for t in self.compatible_producers:
                    if isinstance(p, t):
                        val = True
                        continue
                if val == False:
                    raise ActionError("Some producers are not of the compatible type")
        for p in producers:
            if not p in self.producers:
                gst.debug("really adding %r to our producers" % p)
                self.producers.append(p)

    def removeProducers(self, *producers):
        """
        Remove the given L{ObjectFactory}s as producers of the L{Action}.

        @type producers: List of L{ObjectFactory}
        @raise ActionError: If the L{Action} is active.
        """
        if self.state != STATE_NOT_ACTIVE:
            raise ActionError("Action is active, can't remove Producers")
        # FIXME : figure out what to do in regards with links
        for p in producers:
            if p in self.producers:
                self.producers.remove(p)

    def addConsumers(self, *consumers):
        """
        Set the given L{ObjectFactory}s as consumers of the L{Action}.

        @type consumers: List of L{ObjectFactory}
        @raise ActionError: If the L{Action} is active.
        """
        gst.debug("consumers: %r" % consumers)
        if self.state != STATE_NOT_ACTIVE:
            raise ActionError("Action is active, can't add Producers")
        # make sure consumers are of the valid type
        if self.compatible_consumers != []:
            for p in consumers:
                val = False
                for t in self.compatible_consumers:
                    if isinstance(p, t):
                        val = True
                        continue
                if val == False:
                    raise ActionError("Some consumers are not of the compatible type")
        for p in consumers:
            if not p in self.consumers:
                gst.debug("really adding %r to our consumers" % p)
                self.consumers.append(p)

    def removeConsumers(self, *consumers):
        """
        Remove the given L{ObjectFactory}s as consumers of the L{Action}.

        @type consumers: List of L{ObjectFactory}
        @raise ActionError: If the L{Action} is active.
        """
        if self.state != STATE_NOT_ACTIVE:
            raise ActionError("Action is active, can't remove Consumers")
        # FIXME : figure out what to do in regards with links
        for p in consumers:
            if p in self.consumers:
                self.consumers.remove(p)

    #{ Link methods

    def setLink(self, producer, consumer, producerstream=None,
                consumerstream=None):
        """
        Set a relationship (link) between producer and consumer.

        If the Producer and/or Consumer isn't already set to this L{Action},
        this method will attempt to add them.

        @param producer: The producer we wish to link.
        @type producer: L{ObjectFactory}
        @param consumer: The consumer we wish to link.
        @type consumer: L{ObjectFactory}
        @param producerstream: The L{MultimediaStream} to use from the producer. If not
        specified, the L{Action} will figure out a compatible L{MultimediaStream} between
        the producer and consumer.
        @type producerstream: L{MultimediaStream}
        @param consumerstream: The L{MultimediaStream} to use from the consumer. If not
        specified, the L{Action} will figure out a compatible L{MultimediaStream} between
        the consumer and consumer.
        @type consumerstream: L{MultimediaStream}
        @raise ActionError: If the L{Action} is active.
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
        @type producer: L{ObjectFactory}
        @param consumer: The consumer we wish to unlink.
        @type consumer: L{ObjectFactory}
        @param producerstream: The L{MultimediaStream} to use from the producer. If not
        specified, the L{Action} will figure out a compatible L{MultimediaStream} between
        the producer and consumer.
        @type producerstream: L{MultimediaStream}.
        @param consumerstream: The L{MultimediaStream} to use from the consumer. If not
        specified, the L{Action} will figure out a compatible L{MultimediaStream} between
        the consumer and consumer.
        @type consumerstream: L{MultimediaStream}.
        @raise ActionError: If the L{Action} is active.
        @raise ActionError: If the producerstream wasn't used in any links.
        @raise ActionError: If the consumerstream wasn't used in any links.
        """
        # If producer and consumer are not available, raise error
        # Search for the given link
        # If there are multiple compatible links, raise an Error
        # finally, remove link
        raise NotImplementedError

    def getLinks(self, autolink=True):
        """
        Returns the Links setup for this Action.

        Sub-classes can override this to fine-tune the linking:
         - Specify streams of producers
         - Specify streams of consumers
         - Add Extra links

        Sub-classes should chain-up to the parent class method BEFORE doing
        anything with the link list.

        @param autolink: If True and there were no links specified previously by
        setLink(), then a list of Links will be automatically created based on
        the available producers, consumers and their respective streams.
        @type autolink: C{bool}
        @return: A list of Links
        @rtype: List of (C{Producer}, C{Consumer}, C{ProducerStream}, C{ConsumerStream})
        """
        links = self._links[:]
        if links == [] and autolink == True:
            links = self.autoLink()
        gst.debug("Returning %d links" % len(links))
        return links


    def autoLink(self):
        """
        Based on the available consumers and producers, returns a list of
        compatibles C{Link}s.

        Sub-classes can override this method (without chaining up) to do their
        own auto-linking algorithm, although it is more recommended to
        implement getLinks().

        @raise ActionError: If there is any ambiguity as to which producerstream
        should be linked to which consumerstream.
        @return: List of compatible Links.
        """
        gst.debug("Creating automatic links")
        links = []
        # iterate producers and their output streams
        for p in self.producers:
            gst.debug("producer %r" % p)
            for ps in p.getOutputStreams():
                gst.debug(" stream %r" % ps)
                # for each, figure out a compatible (consumer, stream)
                for c in self.consumers:
                    compat = c.getInputStreams(type(ps))
                    # in case of ambiguity, raise an exception
                    if len(compat) > 1:
                        raise ActionError("Too many compatible streams in consumer")
                    if len(compat) == 1:
                        gst.debug("Got a compatible stream !")
                        links.append((p, c, ps, compat[0]))
        return links
    #}

    def _ensurePipelineObjects(self):
        """
        Makes sure all objects needed in the pipeline are properly created.

        @precondition: All checks relative to pipeline/action/factory validity
        must be done.
        @raise ActionError: If some producers or consumers remain unused.
        """
        # Get the links
        links = self.getLinks()
        # ensure all links are used
        p = self.producers[:]
        c = self.consumers[:]
        for prod, cons , ps, cs in links:
            if prod in p:
                p.remove(prod)
            if cons in c:
                c.remove(cons)
        if p != [] or c != []:
            raise ActionError("Some producers or consumers are not used !")

        gst.debug("make sure we have bins")
        # Make sure we have bins for our producers and consumers
        for p in self.producers:
            self.pipeline.getBinForFactory(p, automake=True)
        for p in self.consumers:
            self.pipeline.getBinForFactory(p, automake=True)

        gst.debug("iterating links")

        for producer, consumer, prodstream, consstream in links:
            gst.debug("producer:%r, consumer:%r, prodstream:%r, consstream:%r" % (\
                producer, consumer, prodstream, consstream))
            # Make sure we have tees for our (producer,stream)s
            t = self.pipeline.getTeeForFactoryStream(producer, prodstream,
                                                     automake=True)
            # Make sure we have queues for our (consumer, stream)s
            q = self.pipeline.getQueueForFactoryStream(consumer, consstream,
                                                       automake=True)
            # Link tees to queues
            t.link(q)

    def _releasePipelineObjects(self):
        gst.debug("Releasing pipeline objects")
        # get the links
        links = self.getLinks()
        for producer, consumer, prodstream, consstream in links:
            t = self.pipeline.getTeeForFactoryStream(producer, prodstream)
            q = self.pipeline.getQueueForFactoryStream(consumer, consstream)

            # figure out to which tee pad the queue is connected
            queuepad = q.get_pad("sink")
            teepad = queuepad.get_peer()

            # unlink
            teepad.unlink(queuepad)
            gst.debug("Releasing tee's request pad for that link")
            t.release_request_pad(teepad)

            # release tee/queue usage for that stream
            self.pipeline.releaseTeeForFactoryStream(producer, prodstream)
            self.pipeline.releaseQueueForFactoryStream(consumer, consstream)
