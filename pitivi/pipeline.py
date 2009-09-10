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
from threading import Lock
from pitivi.signalinterface import Signallable
from pitivi.factories.base import SourceFactory, SinkFactory
from pitivi.action import ActionError
from pitivi.stream import get_src_pads_for_stream, \
     get_sink_pads_for_stream, get_stream_for_caps
from pitivi.log.loggable import Loggable
import gobject
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

class FactoryEntry(object):
    def __init__(self, factory):
        self.factory = factory
        self.streams = {}

    def __str__(self):
        return "<FactoryEntry %s>" % self.factory

class StreamEntry(object):
    def __init__(self, factory_entry, stream, parent=None):
        self.factory_entry = factory_entry
        self.stream = stream
        self.bin = None
        self.bin_use_count = 0
        self.tee = None
        self.tee_use_count = 0
        self.queue = None
        self.queue_use_count = 0
        self.parent = parent

    def findBinEntry(self):
        entry = self
        while entry is not None:
            if entry.bin is not None:
                break

            entry = entry.parent

        return entry

    def __str__(self):
        return "<StreamEntry %s '%s'>" % (self.factory_entry.factory, self.stream)

class Pipeline(Signallable, Loggable):
    """
    A container for all multimedia processing.

    The Pipeline is only responsible for:
     - State changes
     - Position seeking
     - Position Querying
       - Along with an periodic callback (optional)

    You can set L{Action}s on it, which are responsible for choosing which
    C{ObjectFactories} should be used, and how they should be linked.

    Signals:
     - C{action-added} : A new L{Action} was added.
     - C{action-removed} : An L{Action} was removed.
     - C{factory-added} : An L{ObjectFactory} was added.
     - C{factory-removed} : An L{ObjectFactory} was removed.
     - C{state-changed} : The state of the pipeline changed.
     - C{position} : The current position of the pipeline changed.
     - C{unhandled-stream} : A factory produced a stream which wasn't handled
       by any of the L{Action}s.
     - C{eos} : The Pipeline has finished playing.
     - C{error} : An error happened.

    @ivar actions: The Action(s) currently used.
    @type actions: List of L{Action}
    @ivar factories: The ObjectFactories handled by the Pipeline.
    @type factories: List of L{ObjectFactory}
    @ivar bins: The gst.Bins used, FOR ACTION USAGE ONLY
    @type bins: Dictionnary of L{ObjectFactory} to C{gst.Bin}
    @ivar tees: The tees used after producers, FOR ACTION USAGE ONLY
    @type tees: Dictionnary of (L{SourceFactory},L{MultimediaStream}) to C{gst.Element}
    @ivar queues: The queues used before consumers, FOR ACTION USAGE ONLY
    @type queues: Dictionnary of (L{SinkFactory},L{MultimediaStream}) to C{gst.Element}
    """

    __signals__ = {
        "action-added" : ["action"],
        "action-removed" : ["action"],
        "factory-added" : ["factory"],
        "factory-removed" : ["factory"],
        "state-changed" : ["state"],
        "position" : ["position"],
        "duration-changed" : ["duration"],
        "unhandled-stream" : ["factory", "stream"],
        "eos" : [],
        "error" : ["message", "details"],
        "element-message": ["message"]
        }

    def __init__(self):
        Loggable.__init__(self)
        self._lock = Lock()
        self._pipeline = gst.Pipeline()
        self._bus = self._pipeline.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect("message", self._busMessageCb)
        self._bus.set_sync_handler(self._busSyncMessageHandler)
        self.factories = {}
        self.actions = []
        self._listening = False # for the position handler
        self._listeningInterval = 300 # default 300ms
        self._listeningSigId = 0
        self._stream_entry_from_pad = {}

    def release(self):
        """
        Release the L{Pipeline} and all used L{ObjectFactory} and
        L{Action}s.

        Call this method when the L{Pipeline} is no longer used. Forgetting to do
        so will result in memory loss.

        @postcondition: The L{Pipeline} will no longer be usable.
        """
        self._listenToPosition(False)
        self._bus.disconnect_by_func(self._busMessageCb)
        self._bus.remove_signal_watch()
        self._bus.set_sync_handler(None)
        self.setState(STATE_NULL)
        self._bus = None
        self._pipeline = None
        self.factories = {}
        for i in [x for x in self.actions if x.isActive()]:
            i.deactivate()
            self.removeAction(i)

    #{ Action-related methods

    def addAction(self, action):
        """
        Add the given L{Action} to the Pipeline.

        @return: The L{Action} that was set
        @rtype: L{Action}
        @raise PipelineError: If the given L{Action} is already set to another
        Pipeline
        """
        self.debug("action:%r", action)
        if action in self.actions:
            self.debug("Action is already used by this Pipeline, returning")
            return action

        if action.pipeline != None:
            raise PipelineError("Action is set to another pipeline (%r)" % action.pipeline)

        action.setPipeline(self)
        self.debug("Adding action to list of actions")
        self.actions.append(action)
        self.debug("Emitting 'action-added' signal")
        self.emit("action-added", action)
        self.debug("Returning")
        return action

    def setAction(self, action):
        """
        Set the given L{Action} on the L{Pipeline}.
        If an L{Action} of the same type already exists in the L{Pipeline} the
        L{Action} will not be set.

        @see: L{addAction}, L{removeAction}

        @param action: The L{Action} to set on the L{Pipeline}
        @type action: L{Action}
        @rtype: L{Action}
        @return: The L{Action} used. Might be different from the one given as
        input.
        """
        self.debug("action:%r", action)
        for ac in self.actions:
            if type(action) == type(ac):
                self.debug("We already have a %r Action : %r", type(action), ac)
                return ac
        return self.addAction(action)

    def removeAction(self, action):
        """
        Remove the given L{Action} from the L{Pipeline}.

        @precondition: Can only be done if both:
         - The L{Pipeline} is in READY or NULL
         - The L{Action} is de-activated

        @see: L{addAction}, L{setAction}

        @param action: The L{Action} to remove from the L{Pipeline}
        @type action: L{Action}
        @rtype: L{bool}
        @return: Whether the L{Action} was removed from the L{Pipeline} or not.
        @raise PipelineError: If L{Action} is activated and L{Pipeline} is not
        READY or NULL
        """
        self.debug("action:%r", action)
        if not action in self.actions:
            self.debug("action not controlled by this Pipeline, returning")
            return
        if action.isActive():
            res, current, pending = self._pipeline.get_state(0)
            if current > STATE_READY or pending > STATE_READY:
                raise PipelineError("Active actions can't be removed from PLAYING or PAUSED Pipeline")
        try:
            action.unsetPipeline()
        except ActionError:
            raise PipelineError("Can't unset Pipeline from Action")
        self.actions.remove(action)
        self.emit('action-removed', action)

    #{ State-related methods

    def setState(self, state):
        """
        Set the L{Pipeline} to the given state.

        @raises PipelineError: If the C{gst.Pipeline} could not be changed to
        the requested state.
        """
        self.debug("state:%r", state)
        res = self._pipeline.set_state(state)
        if res == gst.STATE_CHANGE_FAILURE:
            raise PipelineError("Failure changing state of the gst.Pipeline")

    def getState(self):
        """
        Query the L{Pipeline} for the current state.

        @see: L{setState}

        This will do an actual query to the underlying GStreamer Pipeline.
        @return: The current state.
        @rtype: C{State}
        """
        change, state, pending = self._pipeline.get_state(0)
        self.debug("change:%r, state:%r, pending:%r", change, state, pending)
        return state

    def play(self):
        """
        Sets the L{Pipeline} to PLAYING
        """
        self.setState(STATE_PLAYING)

    def pause(self):
        """
        Sets the L{Pipeline} to PAUSED
        """
        self.setState(STATE_PAUSED)

    def stop(self):
        """
        Sets the L{Pipeline} to READY
        """
        self.setState(STATE_READY)

    def togglePlayback(self):
        if self.getState() == gst.STATE_PLAYING:
            self.pause()
        else:
            self.play()

    #{ Position and Seeking methods

    def getPosition(self, format=gst.FORMAT_TIME):
        """
        Get the current position of the L{Pipeline}.

        @param format: The format to return the current position in
        @type format: C{gst.Format}
        @return: The current position or gst.CLOCK_TIME_NONE
        @rtype: L{long}
        @raise PipelineError: If the position couldn't be obtained.
        """
        self.log("format %r", format)
        try:
            cur, format = self._pipeline.query_position(format)
        except Exception, e:
            self.handleException(e)
            raise PipelineError("Couldn't get position")
        self.log("Got position %s", gst.TIME_ARGS(cur))
        return cur

    def getDuration(self, format=gst.FORMAT_TIME):
        """
        Get the duration of the C{Pipeline}.
        """
        self.log("format %r", format)
        try:
            dur, format = self._pipeline.query_duration(format)
        except Exception, e:
            self.handleException(e)
            raise PipelineError("Couldn't get duration")
        self.log("Got duration %s", gst.TIME_ARGS(dur))
        self.emit("duration-changed", dur)
        return dur

    def activatePositionListener(self, interval=300):
        """
        Activate the position listener.

        When activated, the Pipeline will emit the 'position' signal at the
        specified interval when it is the PLAYING or PAUSED state.

        @see: L{deactivatePositionListener}
        @param interval: Interval between position queries in milliseconds
        @type interval: L{int} milliseconds
        @return: Whether the position listener was activated or not
        @rtype: L{bool}
        """
        if self._listening == True:
            return True
        self._listening = True
        self._listeningInterval = interval
        # if we're in paused or playing, switch it on
        self._listenToPosition(self.getState() == STATE_PLAYING)
        return True

    def deactivatePositionListener(self):
        """
        De-activates the position listener.

        @see: L{activatePositionListener}
        """
        self._listenToPosition(False)
        self._listening = False

    def _positionListenerCb(self):
        try:
            cur = self.getPosition()
            if cur != gst.CLOCK_TIME_NONE:
                self.emit('position', cur)
        finally:
            return True

    def _listenToPosition(self, listen=True):
        # stupid and dumm method, not many checks done
        # i.e. it does NOT check for current state
        if listen == True:
            if self._listening == True and self._listeningSigId == 0:
                self._listeningSigId = gobject.timeout_add(self._listeningInterval,
                                                           self._positionListenerCb)
        elif self._listeningSigId != 0:
            gobject.source_remove(self._listeningSigId)
            self._listeningSigId = 0

    def seek(self, position, format=gst.FORMAT_TIME):
        """
        Seeks in the L{Pipeline} to the given position.

        @param position: Position to seek to
        @type position: L{long}
        @param format: The C{Format} of the seek position
        @type format: C{gst.Format}
        @raise PipelineError: If seek failed
        """
        if format == gst.FORMAT_TIME:
            self.debug("position : %s", gst.TIME_ARGS (position))
        else:
            self.debug("position : %d , format:%d", position, format)
        # FIXME : temporarily deactivate position listener
        #self._listenToPosition(False)

        # clamp between [0, duration]
        if format==gst.FORMAT_TIME:
            position = max(0, min(position, self.getDuration()))

        res = self._pipeline.seek(1.0, format, gst.SEEK_FLAG_FLUSH,
                                  gst.SEEK_TYPE_SET, position,
                                  gst.SEEK_TYPE_NONE, -1)
        if not res:
            self.debug("seeking failed")
            raise PipelineError("seek failed")
        self.debug("seeking succesfull")
        self.emit('position', position)

    def seekRelative(self, time):
        seekvalue = max(0, min(self.getPosition() + time,
            self.getDuration()))
        self.seek(seekvalue)

    #{ GStreamer object methods (For Action usage only)

    def _getFactoryEntryForStream(self, factory, stream, create=False):
        self.debug("factory %r, stream %r" , factory, stream)
        try:
            factory_entry = self.factories[factory]
        except KeyError:
            if not create:
                raise PipelineError()

            change, current, pending = self._pipeline.get_state(0)

            if (current > STATE_READY or pending > STATE_READY) and \
                    isinstance(factory, SourceFactory):
                raise PipelineError("Pipeline not in NULL/READY,"
                        " can not create source bin")

            factory_entry = FactoryEntry(factory)
            self.factories[factory] = factory_entry

        self.debug("Returning %s", factory_entry)
        return factory_entry

    def _getStreamEntryForFactoryStream(self, factory, stream=None, create=False):
        self.debug("factory %r, stream %r, create:%r", factory, stream, create)
        factory_entry = self._getFactoryEntryForStream(factory, stream, create)
        for k, v in factory_entry.streams.iteritems():
            self.debug("Stream:%r  ==>  %s", k, v)

        stream_entry = None
        if stream is None:
            stream_entry = factory_entry.streams.get(stream, None)
        else:
            for factory_stream, entry in factory_entry.streams.iteritems():
                if factory_stream is None:
                    continue

                if stream.isCompatibleWithName(factory_stream):
                    if stream_entry is None:
                        stream_entry = entry
                    elif stream is factory_stream:
                        stream_entry = entry
                        break

        if stream_entry is None:
            if not create:
                self.debug("Failure getting stream %s", stream)
                raise PipelineError()

            self.debug("Creating StreamEntry")
            stream_entry = StreamEntry(factory_entry, stream)
            factory_entry.streams[stream] = stream_entry

        self.debug("Returning %r", stream_entry)
        return stream_entry

    def getBinForFactoryStream(self, factory, stream=None, automake=False):
        """
        Fetches the C{gst.Bin} currently used in the C{gst.Pipeline} for the
        given L{ObjectFactory}. If no bin exists for the given factory and
        automake is True, one is created.

        The returned bin will have its reference count incremented. When you are
        done with the bin, you must call L{releaseBinForFactoryStream}.

        @param factory: The factory to search.
        @type factory: L{ObjectFactory}
        @param stream: stream to create a bin for
        @type stream: L{MultimediaStream} derived instance
        @param automake: If set to True, then if there is not a C{gst.Bin}
        already created for the given factory, one will be created, added to the
        list of controlled bins and added to the C{gst.Pipeline}.
        @raise PipelineError: If the factory isn't used in this pipeline.
        @raise PipelineError: If a source C{gst.Bin} needed to be created and the
        L{Pipeline} was not in the READY or NULL state.
        @raise PipelineError: If a C{gst.Bin} needed to be created but the
        creation of that C{gst.Bin} failed.
        @return: The bin corresponding to the given factory or None if there
        are none for the given factory.
        @rtype: C{gst.Bin}
        """
        self.debug("factory:%r , stream:%r , automake:%r", factory, stream, automake)

        stream_entry = self._getStreamEntryForFactoryStream(factory,
                                                            stream, automake)

        bin_entry = stream_entry.findBinEntry()
        if bin_entry is not None and bin_entry.bin is not None:
            bin_entry.bin_use_count += 1
            return bin_entry.bin

        if not automake:
            raise PipelineError()

        bin = stream_entry.bin = factory.makeBin(stream)
        stream_entry.bin_use_count += 1
        self._connectToPadSignals(bin)
        self._pipeline.add(bin)

        if stream is None:
            factory_entry = self._getFactoryEntryForStream(factory, stream)

            for stream in factory.output_streams:
                factory_entry.streams[stream] = StreamEntry(factory_entry,
                        stream, parent=stream_entry)
            for stream in factory.input_streams:
                factory_entry.streams[stream] = StreamEntry(factory_entry,
                        stream, parent=stream_entry)

        self.debug("Setting bin to current state")
        bin.set_state(self.getState())

        return bin

    def releaseBinForFactoryStream(self, factory, stream=None):
        """
        Release a bin returned by L{getBinForFactoryStream}.

        @see getBinForFactoryStream
        """
        stream_entry = self._getStreamEntryForFactoryStream(factory, stream)
        bin_stream_entry = stream_entry.findBinEntry()

        if bin_stream_entry == None:
            self.warning("couldn't find stream entry")
            return

        if bin_stream_entry.bin_use_count == 1 and \
                (stream_entry.tee_use_count > 0 or \
                stream_entry.queue_use_count > 0):
            raise PipelineError()

        bin_stream_entry.bin_use_count -= 1
        if bin_stream_entry.bin_use_count == 0:
            # do cleanup on our side
            self.debug("cleaning up")
            self._disconnectFromPadSignals(bin_stream_entry.bin)
            bin_stream_entry.bin.set_state(gst.STATE_NULL)
            self._pipeline.remove(bin_stream_entry.bin)
            factory_entry = bin_stream_entry.factory_entry
            del factory_entry.streams[bin_stream_entry.stream]

            # ask the factory to finish cleanup
            factory_entry.factory.releaseBin(bin_stream_entry.bin)

            bin_stream_entry.bin = None
            if not factory_entry.streams:
                del self.factories[factory_entry.factory]

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
        @raise PipelineError: If a C{Tee} needed to be created but the
        creation of that C{Tee} failed.
        @return: The C{Tee} corresponding to the given factory/stream or None if
        there are none for the given factory.
        @rtype: C{gst.Element}
        """
        self.debug("factory:%r , stream:%r, automake:%r", factory, stream, automake)
        if not isinstance(factory, SourceFactory):
            raise PipelineError("Given ObjectFactory isn't a SourceFactory")

        stream_entry = self._getStreamEntryForFactoryStream(factory, stream)
        bin_stream_entry = stream_entry.findBinEntry()
        if bin_stream_entry is None:
            raise PipelineError()

        bin = bin_stream_entry.bin

        if stream_entry.tee is not None:
            stream_entry.tee_use_count += 1
            # have an existing tee, return it
            return stream_entry.tee

        if not automake:
            raise PipelineError()

        self.debug("Really creating a tee")
        pads = get_src_pads_for_stream(bin, stream)
        if not pads or len(pads) > 1:
            raise PipelineError("Can't figure out which source pad to use !")

        srcpad = pads[0]
        self.debug("Using pad %r", srcpad)

        stream_entry.tee = gst.element_factory_make("tee")
        self._pipeline.add(stream_entry.tee)
        stream_entry.tee_use_count += 1
        stream_entry.tee.set_state(STATE_PAUSED)
        self.debug("Linking pad %r to tee", pads[0])
        srcpad.link(stream_entry.tee.get_pad("sink"))

        return stream_entry.tee

    def releaseTeeForFactoryStream(self, factory, stream=None):
        """
        Release the tee associated with the given source factory and stream.
        If this was the last action to release the given (factory,stream), then the
        tee will be removed.

        This should be called by Actions when they deactivate, after having called
        releaseQueueForFactoryStream() for the consumers.

        @see: L{getTeeForFactoryStream}

        @param factory: The factory
        @type factory: L{SinkFactory}
        @param stream: The stream
        @type stream: L{MultimediaStream}
        @raise PipelineError: If the Pipeline isn't in NULL or READY.
        """
        self.debug("factory:%r, stream:%r", factory, stream)
        stream_entry = self._getStreamEntryForFactoryStream(factory, stream)

        if stream_entry.tee_use_count == 0:
            raise PipelineError()

        stream_entry.tee_use_count -= 1
        if stream_entry.tee_use_count == 0:
            bin = self.getBinForFactoryStream(factory, stream, automake=False)
            if stream_entry.tee is not None:
                bin.unlink(stream_entry.tee)
                stream_entry.tee.set_state(gst.STATE_NULL)
                self._pipeline.remove(stream_entry.tee)
                stream_entry.tee = None
            self.releaseBinForFactoryStream(factory, stream)

    def getQueueForFactoryStream(self, factory, stream=None, automake=False,
                                 queuesize=1):
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
        @param queuesize: The size of the queue in seconds.
        @raise PipelineError: If the factory isn't used in this pipeline.
        @raise PipelineError: If the factory isn't a L{SinkFactory}.
        @raise PipelineError: If a C{Queue} needed to be created but the
        creation of that C{Queue} failed.
        @return: The C{Queue} corresponding to the given factory/stream or None if
        there are none for the given factory.
        @rtype: C{gst.Element}
        """
        self.debug("factory %r, stream %r" , factory, stream)
        if not isinstance(factory, SinkFactory):
            raise PipelineError("Given ObjectFactory isn't a SinkFactory")

        stream_entry = self._getStreamEntryForFactoryStream(factory, stream)
        if stream_entry.queue is not None:
            stream_entry.queue_use_count += 1
            return stream_entry.queue

        if not automake:
            raise PipelineError()

        self.debug("Really creating a queue")

        bin_entry = stream_entry.findBinEntry()
        bin = bin_entry.bin
        # find the source pads compatible with the given stream
        pads = get_sink_pads_for_stream(bin, stream)
        if len(pads) > 1:
            raise PipelineError("Can't figure out which sink pad to use !")

        if pads == []:
            raise PipelineError("No compatible sink pads !")

        stream_entry.queue = gst.element_factory_make("queue")
        stream_entry.queue.props.max_size_time = queuesize * gst.SECOND
        stream_entry.queue.props.max_size_buffers = 0
        stream_entry.queue.props.max_size_bytes = 0
        self._pipeline.add(stream_entry.queue)
        stream_entry.queue.set_state(STATE_PAUSED)

        self.debug("Linking pad %r to queue", pads[0])
        stream_entry.queue.get_pad("src").link(pads[0])

        stream_entry.queue_use_count += 1
        return stream_entry.queue

    def releaseQueueForFactoryStream(self, factory, stream=None):
        """
        Release the queue associated with the given sink factory and stream.

        The queue object will be internally removed from the gst.Pipeline, along
        with the link with tee.

        This should be called by Actions when they deactivate.

        @see: L{getQueueForFactoryStream}

        @param factory: The factory
        @type factory: L{SinkFactory}
        @param stream: The stream
        @type stream: L{MultimediaStream}
        @raise PipelineError: If the Pipeline isn't in NULL or READY.
        """
        if not isinstance(factory, SinkFactory):
            raise PipelineError()

        stream_entry = self._getStreamEntryForFactoryStream(factory, stream)
        if stream_entry.queue is None:
            raise PipelineError()

        stream_entry.queue_use_count -= 1
        if stream_entry.queue_use_count == 0:
            self.debug("Found a corresponding queue, unlink it from the consumer")

            if stream_entry.bin:
                # first set the bin to NULL
                stream_entry.bin.set_state(gst.STATE_NULL)

                # unlink it from the sink bin
                stream_entry.queue.unlink(stream_entry.bin)

            self.debug("Unlinking it from the tee, if present")
            queue_sinkpad = stream_entry.queue.get_pad("sink")
            stream_entry.queue.set_state(gst.STATE_NULL)
            # figure out the peerpad
            tee_srcpad = queue_sinkpad.get_peer()
            if tee_srcpad:
                tee = tee_srcpad.get_parent()
                tee_srcpad.unlink(queue_sinkpad)
                tee.release_request_pad(tee_srcpad)
            self.debug("Removing from gst.Pipeline")
            self._pipeline.remove(stream_entry.queue)
            stream_entry.queue = None

    #}
    ## Private methods

    def _busMessageCb(self, unused_bus, message):
        if message.type == gst.MESSAGE_EOS:
            self.emit('eos')
        elif message.type == gst.MESSAGE_STATE_CHANGED:
            prev, new, pending = message.parse_state_changed()
            self.debug("element %s state change %s" % (message.src,
                    (prev, new, pending)))

            if message.src == self._pipeline:
                self.debug("Pipeline change state prev:%r, new:%r, pending:%r", prev, new, pending)

                emit_state_change = pending == gst.STATE_VOID_PENDING
                if prev == STATE_READY and new == STATE_PAUSED:
                    # trigger duration-changed
                    try:
                        self.getDuration()
                    except PipelineError:
                        # no sinks??
                        pass
                elif prev == STATE_PAUSED and new == STATE_PLAYING:
                    self._listenToPosition(True)
                elif prev == STATE_PLAYING and new == STATE_PAUSED:
                    self._listenToPosition(False)

                if emit_state_change:
                    self.emit('state-changed', new)
        elif message.type == gst.MESSAGE_ERROR:
            error, detail = message.parse_error()
            self._handleErrorMessage(error, detail, message.src)
        elif message.type == gst.MESSAGE_DURATION:
            self.debug("Duration might have changed, querying it")
            gobject.idle_add(self._queryDurationAsync)
        else:
            self.info("%s [%r]" , message.type, message.src)

    def _queryDurationAsync(self, *args, **kwargs):
        try:
            self.getDuration()
        except:
            self.log("Duration failed... but we don't care")
        return False

    def _handleErrorMessage(self, error, detail, source):
        self.error("error from %s: %s (%s)" % (source, error, detail))
        self.emit('error', error, detail)

    def _busSyncMessageHandler(self, unused_bus, message):
        if message.type == gst.MESSAGE_ELEMENT:
            # handle element message synchronously
            self.emit('element-message', message)
        return gst.BUS_PASS

    def _binPadAddedCb(self, bin, pad):
        # Our (semi)automatic linking logic is based on caps.
        # gst_pad_get_caps returns all the caps a pad can handle, not
        # necessarily those set with gst_pad_set_caps.
        # Some of our utility elements (like ImageFreeze and FixSeekStart) have
        # template caps ANY but they do caps negotiation (call gst_pad_set_caps)
        # asap, before pushing anything. Therefore we try to get the negotiated
        # caps first here, and fallback on the template caps.
        caps = pad.props.caps
        if caps is None:
            caps = pad.get_caps()

        if caps.is_any():
            self.error("got ANY caps, this should never happen")

        self.debug("bin:%r, pad:%r (%s)", bin, pad, caps.to_string())
        self._lock.acquire()

        try:
            factory = None
            stream = None
            stream_entry = None
            for factory_entry in self.factories.itervalues():
                for stream_entry in factory_entry.streams.itervalues():
                    if stream_entry.bin == bin:
                        factory = factory_entry.factory
                        stream = stream_entry.stream
                        break
                if factory is not None:
                    break

            if factory is None:
                raise PipelineError("New pad on an element we don't control ??")

            stream = get_stream_for_caps(caps, pad)
            if stream not in factory_entry.streams:
                factory_entry.streams[stream] = StreamEntry(factory_entry,
                        stream, parent=stream_entry)
                stream_entry = factory_entry.streams[stream]

            self._stream_entry_from_pad[pad] = stream_entry

            # ask all actions using this producer if they handle it
            compatactions = [action for action in self.actions
                             if factory in action.producers]
            self.debug("Asking all actions (%d/%d) using that producer [%r] if they can handle it",
                      len(compatactions), len(self.actions), factory)
            for a in self.actions:
                self.debug("Action %r, producers %r", a, a.producers)
            handled = False
            for action in compatactions:
                handled |= action.handleNewStream(factory, stream)

            if handled == False:
                self.debug("No action handled this Stream")
                self.emit('unhandled-stream', stream)
        finally:
            self.debug("Done handling new pad")
            self._lock.release()


    def _binPadRemovedCb(self, bin, pad):
        self._lock.acquire()
        try:
            self.debug("bin:%r, pad:%r", bin, pad)
            if not pad in self._stream_entry_from_pad:
                self.warning("Pad not controlled by this pipeline")
                self._lock.release()
                return
            stream_entry = self._stream_entry_from_pad.pop(pad)
            factory = stream_entry.factory_entry.factory
            stream = stream_entry.stream

            for action in [action for action in self.actions
                    if factory in action.producers]:
                action.streamRemoved(factory, stream)
        except:
            self._lock.release()
        self._lock.release()

    def _connectToPadSignals(self, bin):
        # Listen on the given bin for pads being added/removed
        bin.connect('pad-added', self._binPadAddedCb)
        bin.connect('pad-removed', self._binPadRemovedCb)

    def _disconnectFromPadSignals(self, bin):
        bin.disconnect_by_func(self._binPadAddedCb)
        bin.disconnect_by_func(self._binPadRemovedCb)
