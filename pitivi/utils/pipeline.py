#!/usr/bin/env python
#
#       pipeline.py
#
# Copyright (C) 2012 Thibault Saunier <thibaul.saunier@collabora.com>
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
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.

"""
High-level pipelines
"""
from pitivi.utils.loggable import Loggable
import gobject
import gst
import ges


# FIXME : define/document a proper hierarchy
class PipelineError(Exception):
    pass


class Pipeline(ges.TimelinePipeline, Loggable):
    """

    The Pipeline is only responsible for:
     - State changes
     - Position seeking
     - Position Querying
       - Along with an periodic callback (optional)

    Signals:
     - C{state-changed} : The state of the pipeline changed.
     - C{position} : The current position of the pipeline changed.
     - C{eos} : The Pipeline has finished playing.
     - C{error} : An error happened.
    """

    __gsignals__ = {
        "state-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                        (gobject.TYPE_INT,)),
        "position": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                        (gobject.TYPE_UINT64,)),
        "duration-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                        (gobject.TYPE_UINT64,)),
        "eos": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                        ()),
        "error": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                        (gobject.TYPE_POINTER, gobject.TYPE_POINTER)),
        "element-message": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                        (gobject.TYPE_POINTER,))}

    def __init__(self):
        Loggable.__init__(self)
        ges.TimelinePipeline.__init__(self)
        self._bus = self.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect("message", self._busMessageCb)
        self._bus.set_sync_handler(self._busSyncMessageHandler)
        self._listening = False  # for the position handler
        self._listeningInterval = 300  # default 300ms
        self._listeningSigId = 0

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
        self.setState(gst.STATE_NULL)
        self._bus = None

    def flushSeekVideo(self):
        self.pause()
        try:
            self.seekRelative(0)
        except PipelineError:
            pass

    def setState(self, state):
        """
        Set the L{Pipeline} to the given state.

        @raises PipelineError: If the C{gst.Pipeline} could not be changed to
        the requested state.
        """
        self.debug("state:%r" % state)
        res = self.set_state(state)
        if res == gst.STATE_CHANGE_FAILURE:
            # reset to NULL
            self.set_state(gst.STATE_NULL)
            raise PipelineError("Failure changing state of the gst.Pipeline to %r, currently reset to NULL" % state)

    def getState(self):
        """
        Query the L{Pipeline} for the current state.

        @see: L{setState}

        This will do an actual query to the underlying GStreamer Pipeline.
        @return: The current state.
        @rtype: C{State}
        """
        change, state, pending = self.get_state(0)
        self.debug("change:%r, state:%r, pending:%r" % (change, state, pending))
        return state

    def play(self):
        """
        Sets the L{Pipeline} to PLAYING
        """
        self.setState(gst.STATE_PLAYING)

    def pause(self):
        """
        Sets the L{Pipeline} to PAUSED
        """
        self.setState(gst.STATE_PAUSED)

        # When the pipeline has been paused we need to update the
        # timeline/playhead position, as the 'position' signal
        # is only emitted every 300ms and the playhead jumps
        # during the playback.
        try:
            self.emit("position", self.getPosition())
        except PipelineError:
            # Getting the position failed
            pass

    def stop(self):
        """
        Sets the L{Pipeline} to READY
        """
        self.setState(gst.STATE_READY)

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
        self.log("format %r" % format)
        try:
            cur, format = self.query_position(format)
        except Exception, e:
            self.handleException(e)
            raise PipelineError("Couldn't get position")

        self.log("Got position %s" % gst.TIME_ARGS(cur))
        return cur

    def getDuration(self, format=gst.FORMAT_TIME):
        """
        Get the duration of the C{Pipeline}.
        """
        self.log("format %r" % format)
        try:
            dur, format = self.query_duration(format)
        except Exception, e:
            self.handleException(e)
            raise PipelineError("Couldn't get duration")

        self.log("Got duration %s" % gst.TIME_ARGS(dur))
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
        if self._listening:
            return True
        self._listening = True
        self._listeningInterval = interval
        # if we're in paused or playing, switch it on
        self._listenToPosition(self.getState() == gst.STATE_PLAYING)
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
        if listen:
            if self._listening and self._listeningSigId == 0:
                self._listeningSigId = gobject.timeout_add(self._listeningInterval,
                    self._positionListenerCb)
        elif self._listeningSigId != 0:
            gobject.source_remove(self._listeningSigId)
            self._listeningSigId = 0

    def simple_seek(self, position, format=gst.FORMAT_TIME):
        """
        Seeks in the L{Pipeline} to the given position.

        @param position: Position to seek to
        @type position: L{long}
        @param format: The C{Format} of the seek position
        @type format: C{gst.Format}
        @raise PipelineError: If seek failed
        """
        if format == gst.FORMAT_TIME:
            self.debug("position : %s" % gst.TIME_ARGS(position))
        else:
            self.debug("position : %d , format:%d" % (position, format))

        # clamp between [0, duration]
        if format == gst.FORMAT_TIME:
            position = max(0, min(position, self.getDuration()))

        res = self.seek(1.0, format, gst.SEEK_FLAG_FLUSH,
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

    #}
    ## Private methods

    def _busMessageCb(self, unused_bus, message):
        if message.type == gst.MESSAGE_EOS:
            self.pause()
            self.emit('eos')
        elif message.type == gst.MESSAGE_STATE_CHANGED:
            prev, new, pending = message.parse_state_changed()
            self.debug("element %s state change %s" % (message.src,
                    (prev, new, pending)))

            if message.src == self:
                self.debug("Pipeline change state prev:%r, new:%r, pending:%r" % (prev, new, pending))

                emit_state_change = pending == gst.STATE_VOID_PENDING
                if prev == gst.STATE_READY and new == gst.STATE_PAUSED:
                    # trigger duration-changed
                    try:
                        self.getDuration()
                    except PipelineError:
                        # no sinks??
                        pass
                elif prev == gst.STATE_PAUSED and new == gst.STATE_PLAYING:
                    self._listenToPosition(True)
                elif prev == gst.STATE_PLAYING and new == gst.STATE_PAUSED:
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
            self.info("%s [%r]" % (message.type, message.src))

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
