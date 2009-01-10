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
from pitivi.factories.base import SourceFactory, SinkFactory
from pitivi.action import ActionError
from pitivi.stream import pad_compatible_stream, get_src_pads_for_stream, \
     get_sink_pads_for_stream
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

    The Pipeline is only responsible for:
     - State changes
     - Position seeking
     - Position Querying
       - Along with an periodic callback (optional)

    You can set C{Action}s on it, which are responsible for choosing which
    C{ObjectFactories} should be used, and how they should be linked.

    @ivar state: The current state. This is a cached value, use getState() for
    the exact actual C{gst.State} of the C{Pipeline}.
    @type state: C{gst.State}
    @ivar actions: The Action(s) currently used.
    @type actions: List of C{Action}
    @ivar factories: The ObjectFactories handled by the Pipeline.
    @type factories: List of C{ObjectFactory}
    @ivar bins: The gst.Bins used, FOR ACTION USAGE ONLY
    @type bins: Dictionnary of C{ObjectFactory} to C{gst.Bin}
    @ivar tees: The tees used after producers, FOR ACTION USAGE ONLY
    @type tees: Dictionnary of (C{SourceFactory},C{Stream}) to C{gst.Element}
    @ivar queues: The queues used before consumers, FOR ACTION USAGE ONLY
    @type queues: Dictionnary of (C{SinkFactory},C{Stream}) to C{gst.Element}
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
        self.factories = []
        self.bins = {} # factory => gst.Bin
        self.tees = {} # (producerfactory, stream) => gst.Element ("tee")
        self.queues = {} # (consumerfactory, stream) => gst.Element ("queue")
        self.actions = []
        self._state = STATE_NULL
        self._padSigIds = {} # (factory) => (paddaddedsigid,padremovedsigid)
        self._pendingStreams = {} # (factory,stream) => tee

    #{ Action-related methods

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

    #{ State-related methods

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
        if res == gst.STATE_CHANGE_SUCCESS:
            # the change to the request state was successful and not asynchronous
            self._state = state
            self.emit('state-changed', self._state)

    def getState(self):
        """
        Query the C{Pipeline} for the current state.

        This will do an actual query to the underlying GStreamer Pipeline.
        @return: The current state.
        @rtype: C{State}
        """
        change, state, pending = self._pipeline.get_state(0)
        gst.debug("change:%r, state:%r, pending:%r" % (change, state, pending))
        if change != gst.STATE_CHANGE_FAILURE and pending == gst.STATE_VOID_PENDING and state != self._state:
            self._state = state
            self.emit('state-changed', self._state)
        gst.debug("Returning %r" % self._state)
        return self._state

    @property
    def state(self):
        """
        The state of the C{Pipeline}.

        @warning: This doesn't query the underlying C{gst.Pipeline} but returns the cached
        state.
        """
        gst.debug("Returning state %r" % self._state)
        return self._state

    def play(self):
        """
        Sets the C{Pipeline} to PLAYING
        """
        self.setState(STATE_PLAYING)

    def pause(self):
        """
        Sets the C{Pipeline} to PAUSED
        """
        self.setState(STATE_PAUSED)

    def stop(self):
        """
        Sets the C{Pipeline} to READY
        """
        self.setState(STATE_READY)

    #{ ObjectFactory-related methods

    def addFactory(self, *factories):
        """
        Adds the given C{ObjectFactory} to be used in the C{Pipeline}.

        @precondition: The C{Pipeline} state must be READY or NULL.

        @param factories: The C{ObjectFactory}s to add
        @type factories: C{ObjectFactory}
        @raise PipelineError: If the C{Pipeline} isn't in READY or NULL.
        """
        if self._state in [STATE_PAUSED, STATE_PLAYING]:
            raise PipelineError("Can't add factories, Pipeline is not READY or NULL")
        for fact in factories:
            if not fact in self.factories:
                self.factories.append(fact)
                self.emit('factory-added', fact)

    def removeFactory(self, *factories):
        """
        Removes the given C{ObjectFactory}s from the C{Pipeline}.

        @precondition: The C{Pipeline} state must be READY or NULL and the
        C{Action}s controlling those factories must all be deactivated.

        @param factories: The C{ObjectFactory}s to remove.
        @type factories: C{ObjectFactory}
        @raise PipelineError: If the C{Pipeline} isn't in READY or NULL or if
        some of the factories are still used by active C{Action}s.
        """
        gst.debug("factories %r" % factories)
        if self._state in [STATE_PAUSED, STATE_PLAYING]:
            raise PipelineError("Can't remove factories, Pipeline is not READY or NULL")
        rfact = [f for f in factories if f in self.factories]
        # we can only remove factories that are used in inactive actions
        for act in [x for x in self.actions if x.isActive()]:
            for f in rfact:
                if f in act.producers or f in act.consumers:
                    raise PipelineError("Some factories belong to still active Action")
        # at this point we can remove the factories
        for f in rfact:
            self._removeFactory(f)

    def _removeFactory(self, factory):
        gst.debug("factory %r" % factory)
        # internal method
        # We should first remove the factory from all used Actions
        for a in self.actions:
            if factory in a.producers:
                a.removeProducers(factory)
            elif factory in a.consumers:
                a.removeConsumers(factory)

        # Then the bin (and not forget to release that bin from the
        # objectfactory)
        gst.debug("Getting corresponding gst.Bin")
        b = self.bins.pop(factory, None)
        if b:
            gst.debug("Really removing %r from gst.Pipeline" % b)
            self._pipeline.remove(b)
            factory.releaseBin(b)

        # And finally remove the factory itself from our list
        self.factories.remove(factory)
        self.emit("factory-removed", factory)

    #{ Position and Seeking methods

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

    def release(self):
        """
        Release the C{Pipeline} and all used C{ObjectFactory} and
        C{Action}s.

        Call this method when the C{Pipeline} is no longer used. Forgetting to do
        so will result in memory loss.

        @postcondition: The C{Pipeline} will no longer be usable.
        """
        raise NotImplementedError


    #{ GStreamer object methods

    def getBinForFactory(self, factory, automake=False):
        """
        Fetches the C{gst.Bin} currently used in the C{gst.Pipeline} for the
        given C{ObjectFactory}.

        @param factory: The factory to search.
        @type factory: C{ObjectFactory}
        @param automake: If set to True, then if there is not a C{gst.Bin}
        already created for the given factory, one will be created.
        @raise PipelineError: If the factory isn't used in this pipeline.
        @raise PipelineError: If a C{gst.Bin} needed to be created and the
        C{Pipeline} was not in the READY or NULL state.
        @raise PipelineError: If a C{gst.Bin} needed to be created but the
        creation of that c{gst.Bin} failed.
        @return: The bin corresponding to the given factory or None if there
        are none for the given factory.
        @rtype: C{gst.Bin}
        """
        gst.debug("factory:%r , automake:%r" % (factory, automake))
        if not factory in self.factories:
            raise PipelineError("Given ObjectFactory isn't handled by this Pipeline")
        res = self.bins.get(factory, None)
        if (res != None) or (automake == False):
            gst.debug("Returning %r" % res)
            return res
        # we need to create one
        if self._state not in [STATE_NULL, STATE_READY]:
            raise PipelineError("Pipeline not in NULL/READY, can not create bin")
        # create the bin (will raise exceptions if it fails
        return self._makeBin(factory)

    def getTeeForFactoryStream(self, factory, stream=None, automake=False):
        """
        Fetches the C{Tee} currently used in the C{gst.Pipeline} for the given
        L{SourceFactory}.

        @param factory: The factory to search.
        @type factory: L{SourceFactory}
        @param stream: The stream of the factory to use. If not specified, then
        a random stream from that factory will be used.
        @type stream: L{MultimediaStream}
        @param automake: If set to True, then if there is not a C{Tee}
        already created for the given factory/stream, one will be created, added
        to the list of controlled tees and added to the C{gst.Pipeline}.
        @raise PipelineError: If the factory isn't used in this pipeline.
        @raise PipelineError: If the factory isn't a L{SourceFactory}.
        @raise PipelineError: If a C{Tee} needed to be created and the
        L{Pipeline} was not in the READY or NULL state.
        @raise PipelineError: If a C{Tee} needed to be created but the
        creation of that C{Tee} failed.
        @return: The C{Tee} corresponding to the given factory/stream or None if
        there are none for the given factory.
        @rtype: C{gst.Element}
        """
        gst.debug("factory:%r , stream:%r, automake:%r" % (factory, stream, automake))
        if not factory in self.factories:
            raise PipelineError("Given ObjectFactory isn't handled by this Pipeline")
        if not isinstance(factory, SourceFactory):
            raise PipelineError("Given ObjectFactory isn't a SourceFactory")
        res = self.tees.get((factory,stream), None)
        if (res != None) or (automake == False):
            gst.debug("Returning %r" % res)
            return res
        # we need to create one
        if self._state not in [STATE_NULL, STATE_READY]:
            raise PipelineError("Pipeline not in NULL/READY, can not create tee")
        # create the tee
        return self._makeTee(factory, stream)

    def releaseTeeForFactoryStream(self, factory, stream):
        # release the tee for the given factory/stream
        # When nobody is using the tee => remove/free it
        raise NotImplementedError

    def getQueueForFactoryStream(self, factory, stream=None, automake=False):
        """
        Fetches the C{Queue} currently used in the C{gst.Pipeline} for the given
        L{SinkFactory}.

        @param factory: The factory to search.
        @type factory: L{SinkFactory}
        @param stream: The stream of the factory to use. If not specified, then
        a random stream from that factory will be used.
        @type stream: L{MultimediaStream}
        @param automake: If set to True, then if there is not a C{Queue}
        already created for the given factory/stream, one will be created, added
        to the list of controlled queues and added to the C{gst.Pipeline}.
        @raise PipelineError: If the factory isn't used in this pipeline.
        @raise PipelineError: If the factory isn't a L{SinkFactory}.
        @raise PipelineError: If a C{Queue} needed to be created and the
        L{Pipeline} was not in the READY or NULL state.
        @raise PipelineError: If a C{Queue} needed to be created but the
        creation of that C{Queue} failed.
        @return: The C{Queue} corresponding to the given factory/stream or None if
        there are none for the given factory.
        @rtype: C{gst.Element}
        """
        gst.debug("factory:%r , stream:%r, automake:%r" % (factory, stream, automake))
        if not factory in self.factories:
            raise PipelineError("Given ObjectFactory isn't handled by this Pipeline")
        if not isinstance(factory, SinkFactory):
            raise PipelineError("Given ObjectFactory isn't a SinkFactory")
        res = self.queues.get((factory,stream), None)
        if (res != None) or (automake == False):
            gst.debug("Returning %r" % res)
            return res
        # we need to create one
        if self._state not in [STATE_NULL, STATE_READY]:
            raise PipelineError("Pipeline not in NULL/READY, can not create queue")
        # create the queue
        return self._makeQueue(factory, stream)

    def releaseQueueForFactoryStream(self, factory, stream):
        # release the queue for the given factory/stream
        # When nobody is using the queue => remove/free it
        raise NotImplementedError

    #}
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

    def _makeBin(self, factory):
        """
        Creates a C{gst.Bin} from the given factory and puts it in the pipeline.

        @precondition: checks for the factory to be valid should be done before.
        """
        # FIXME : How do we figure out for which streams we need to create the
        # Bin.
        # Ex : There could be one action wanting one stream from a given bin, and
        # another action wanting another stream.
        # ==> It should figure out from all Actions what streams are being used
        gst.debug("factory %r" % factory)
        b = factory.makeBin()
        gst.debug("adding newly created bin [%r] to gst.Pipeline" % b)
        self._pipeline.add(b)
        gst.debug("Adding newly created bin to list of controlled bins")
        self.bins[factory] = b
        return b

    def _binPadAddedCb(self, bin, pad, factory):
        gst.debug("bin:%r, pad:%r" % (bin, pad))
        # try to find an existing tee for the given pad
        for fact, stream in self._pendingStreams.keys():
            if fact == factory and pad_compatible_stream(pad, stream):
                tee = self._pendingStreams
                gst.debug("Linking to the pending tee")
                pad.link(tee.get_pad("sink"))
                del self._pendingStreams[(fact,stream)]
                return
        gst.debug("Ignored pad since we don't seem to use it")

    def _binPadRemovedCb(self, bin, pad, factory):
        gst.debug("bin:%r, pad:%r" % (bin, pad))
        raise NotImplementedError

    def _listenToPads(self, bin, tee, factory,stream):
        # Listen on the given bin for pads being added/removed
        if not bin is self._padSigIds.keys():
            padaddedsigid = bin.connect('pad-added', self._teePadAddedCb,
                                        factory)
            padremovedsigid = bin.connect('pad-removed', self._teePadAddedCb,
                                          factory)
            self._padSigIds[bin] = (padaddedsigid, padremovedsigid)
        # add the stream to the list of pending streams
        self._pendingStreams[(factory,stream)] = tee

    def _makeTee(self, factory, stream):
        """
        - Create a C{Tee} for the given factory and stream
        - Add it to the list of controlled tees,
        - Add it to the gst.Pipeline,
        - Link the bin to the tee
          - If the bin doesn't have the corresponding pad yet, put a async
          handler.

        @precondition: checks for the factory and stream to be valid should be
        done before, including it's existence in the list of controlled tees.
        @raise PipelineError: If we can't figure out which pad to use from the
        source bin.
        """
        gst.debug("factory: %r, stream: %r" % (factory, stream))
        t = gst.element_factory_make("tee")
        self._pipeline.add(t)
        b = self.bins[factory]
        # find the source pads compatible with the given stream
        pads = get_src_pads_for_stream(b, stream)
        if len(pads) > 1:
            raise PipelineError("Can't figure out which source pad to use !")
        if pads == []:
            # if the pad isn't available yet, connect a 'pad-added' and
            # 'pad-removed' handler.
            gst.debug("No available pads, we assume it will produce a pad later on")
        else:
            gst.debug("Linking pad %r to tee" % pads[0])
            pads[0].link(t.get_pad("sink"))
        gst.debug("Adding newly created bin to list of controlled tees")
        self.tees[(factory, stream)] = t
        return t

    def _makeQueue(self, factory, stream):
        """
        - Create a C{Queue} for the given factory and stream
        - Add it to the list of controlled queues,
        - Add it to the gst.Pipeline,
        - Link the bin to the queue
          - If the bin doesn't have the corresponding pad yet, put a async
          handler.

        @precondition: checks for the factory and stream to be valid should be
        done before, including it's existence in the list of controlled queues.
        @raise PipelineError: If we can't figure out which pad to use from the
        source bin.
        """
        gst.debug("factory: %r, stream: %r" % (factory, stream))
        q = gst.element_factory_make("queue")
        self._pipeline.add(q)
        b = self.bins[factory]
        # find the source pads compatible with the given stream
        pads = get_sink_pads_for_stream(b, stream)
        if len(pads) > 1:
            raise PipelineError("Can't figure out which sink pad to use !")
        if pads == []:
            # FIXME : Maybe it's a request pad ?
            raise PipelineError("No compatible sink pads !")
        else:
            gst.debug("Linking pad %r to queue" % pads[0])
            q.get_pad("src").link(pads[0])
        gst.debug("Adding newly created bin to list of controlled queues")
        self.queues[(factory, stream)] = q
        return q
