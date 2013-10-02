#!/usr/bin/env python2
#
#       pitivi/utils/pipeline.py
#
# Copyright (C) 2012 Thibault Saunier <thibault.saunier@collabora.com>
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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.

"""
High-level pipelines
"""
from pitivi.utils.loggable import Loggable
from pitivi.utils.signal import Signallable
from pitivi.utils.misc import format_ns

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GES

MAX_RECOVERIES = 5


# FIXME : define/document a proper hierarchy
class PipelineError(Exception):
    pass


class Seeker(Signallable, Loggable):
    """
    The Seeker is a singleton helper class to do various seeking
    operations in the pipeline.
    """
    _instance = None
    __signals__ = {
        'seek': ['position', 'format'],
        'seek-relative': ['time'],
    }

    def __new__(cls, *args, **kwargs):
        """
        Override the new method to return the singleton instance if available.
        Otherwise, create one.
        """
        if not cls._instance:
            cls._instance = super(Seeker, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, timeout=80):
        """
        @param timeout (optional): the amount of miliseconds for a seek attempt
        """
        Signallable.__init__(self)
        Loggable.__init__(self)

        self.timeout = timeout
        self.pending_seek_id = None
        self.position = None
        self.format = None
        self._time = None
        self.pending_position = None

    def seek(self, position, format=Gst.Format.TIME, on_idle=False):
        self.format = format
        self.position = position

        if self.pending_seek_id is None:
            if on_idle:
                self.pending_seek_id = self._scheduleSeek(self.timeout, self._seekTimeoutCb)
            else:
                self._seekTimeoutCb()
        else:
            self.pending_position = position

    def seekRelative(self, time, on_idle=False):
        if self.pending_seek_id is None:
            self._time = long(time)
            if on_idle:
                self.pending_seek_id = self._scheduleSeek(self.timeout, self._seekTimeoutCb, relative=True)
            else:
                self._seekTimeoutCb(relative=True)

    def flush(self, on_idle=False):
        self.seekRelative(0, on_idle)

    def _scheduleSeek(self, timeout, callback, relative=False):
        return GLib.timeout_add(timeout, callback, relative)

    def _seekTimeoutCb(self, relative=False):
        self.pending_seek_id = None

        if relative:
            try:
                self.emit('seek-relative', self._time)
            except PipelineError:
                self.error("Error while seeking %s relative", self._time)
                # if an exception happened while seeking, properly
                # reset ourselves
                return False

            self._time = None
        elif self.position is not None and self.format is not None:
            position, self.position = self.position, None
            format, self.format = self.format, None
            try:
                self.emit('seek', position, format)
            except PipelineError as e:
                self.error("Error while seeking to position:%s format: %r, reason: %s",
                          format_ns(position), format, e)
                # if an exception happened while seeking, properly
                # reset ourselves
                return False

        if self.pending_position:
            self.seek(self.pending_position, on_idle=True)
            self.pending_position = None

        return False


class SimplePipeline(Signallable, Loggable):
    """
    The Pipeline is only responsible for:
     - State changes
     - Position seeking
     - Position Querying
       - Along with an periodic callback (optional)

    Signals:
     - C{state-change} : The state of the pipeline changed.
     - C{position} : The current position of the pipeline changed.
     - C{eos} : The Pipeline has finished playing.
     - C{error} : An error happened.
    """

    __signals__ = {
        "state-change": ["state"],
        "position": ["position"],
        "duration-changed": ["duration"],
        "eos": [],
        "error": ["message", "details"]
    }

    def __init__(self, pipeline, video_overlay):
        Loggable.__init__(self)
        Signallable.__init__(self)
        self._pipeline = pipeline
        self._bus = self._pipeline.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect("message", self._busMessageCb)
        self._listening = False  # for the position handler
        self._listeningInterval = 300  # default 300ms
        self._listeningSigId = 0
        self._duration = Gst.CLOCK_TIME_NONE
        self.video_overlay = video_overlay
        self.lastPosition = long(0 * Gst.SECOND)
        self.pendingRecovery = False
        self._attempted_recoveries = 0
        self._waiting_for_async_done = True
        self._next_seek = None
        self._timeout_async_id = 0

    def release(self):
        """
        Release the L{Pipeline} and all used L{ObjectFactory} and
        L{Action}s.

        Call this method when the L{Pipeline} is no longer used. Forgetting to do
        so will result in memory loss.

        @postcondition: The L{Pipeline} will no longer be usable.
        """
        self.deactivatePositionListener()
        self._bus.disconnect_by_func(self._busMessageCb)
        self._bus.remove_signal_watch()

        self._pipeline.setState(Gst.State.NULL)
        self._bus = None

    def flushSeek(self):
        self.pause()
        try:
            self.seekRelative(0)
        except PipelineError:
            pass

    def setState(self, state):
        """
        Set the L{Pipeline} to the given state.

        @raises PipelineError: If the C{Gst.Pipeline} could not be changed to
        the requested state.
        """
        self.debug("state set to: %r", state)
        res = self._pipeline.set_state(state)
        if res == Gst.StateChangeReturn.FAILURE:
            # reset to NULL
            self._pipeline.set_state(Gst.State.NULL)
            raise PipelineError("Failure changing state of the Gst.Pipeline to %r, currently reset to NULL" % state)

    def getState(self):
        """
        Query the L{Pipeline} for the current state.

        @see: L{setState}

        This will do an actual query to the underlying GStreamer Pipeline.
        @return: The current state.
        @rtype: C{State}
        """
        change, state, pending = self._pipeline.get_state(timeout=0)  # No timeout
        self.debug("change: %r, state: %r, pending: %r", change, state, pending)
        return state

    def play(self):
        """
        Sets the L{Pipeline} to PLAYING
        """
        self.setState(Gst.State.PLAYING)

    def pause(self):
        """
        Sets the L{Pipeline} to PAUSED
        """
        self.setState(Gst.State.PAUSED)

        # When the pipeline has been paused we need to update the
        # timeline/playhead position, as the 'position' signal
        # is only emitted every 300ms and the playhead jumps
        # during the playback.
        try:
            position = self.getPosition()
        except PipelineError:
            # Getting the position failed
            return
        if position != Gst.CLOCK_TIME_NONE and position >= 0:
            self.emit("position", position)

    def stop(self):
        """
        Sets the L{Pipeline} to READY
        """
        self.setState(Gst.State.READY)

    def togglePlayback(self):
        if self.getState() == Gst.State.PLAYING:
            self.pause()
        else:
            self.play()

    #{ Position and Seeking methods

    def getPosition(self, format=Gst.Format.TIME):
        """
        Get the current position of the L{Pipeline}.

        @param format: The format to return the current position in
        @type format: C{Gst.Format}
        @return: The current position or Gst.CLOCK_TIME_NONE
        @rtype: L{long}
        @raise PipelineError: If the position couldn't be obtained.
        """
        try:
            res, cur = self._pipeline.query_position(format)
        except Exception, e:
            self.handleException(e)
            raise PipelineError("Couldn't get position")

        if not res:
            raise PipelineError("Couldn't get position")

        self.log("Got position %s", format_ns(cur))
        return cur

    def getDuration(self, format=Gst.Format.TIME):
        """
        Get the duration of the C{Pipeline}.
        """
        self.log("format %r", format)

        dur = self._getDuration(format)
        if dur is None:
            self.info("Invalid duration: None")
        else:
            self.log("Got duration %s", format_ns(dur))
        if self._duration != dur:
            self.emit("duration-changed", dur)

        self._duration = dur

        return dur

    def activatePositionListener(self, interval=500):
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
        self._listenToPosition(self.getState() == Gst.State.PLAYING)
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
            if cur != Gst.CLOCK_TIME_NONE:
                self.emit('position', cur)
                self.lastPosition = cur
        except PipelineError:
            pass
        finally:
            return True

    def _listenToPosition(self, listen=True):
        # stupid and dumm method, not many checks done
        # i.e. it does NOT check for current state
        if listen:
            if self._listening and self._listeningSigId == 0:
                self._listeningSigId = GLib.timeout_add(self._listeningInterval,
                    self._positionListenerCb)
        elif self._listeningSigId != 0:
            GLib.source_remove(self._listeningSigId)
            self._listeningSigId = 0

    def _resetWaitingForAsyncDone(self):
        self.warning("we didn't get async done, this is a bug")
        self._waiting_for_async_done = False
        return False

    def simple_seek(self, position, format=Gst.Format.TIME):
        """
        Seeks in the L{Pipeline} to the given position.

        @param position: Position to seek to
        @type position: L{long}
        @param format: The C{Format} of the seek position
        @type format: C{Gst.Format}
        @raise PipelineError: If seek failed
        """
        if self._waiting_for_async_done is True:
            self._next_seek = (position, format)
            self.info("Setting next seek to %s", self._next_seek)
            return

        if format == Gst.Format.TIME:
            self.debug("position: %s", format_ns(position))
        else:
            self.debug("position: %d, format: %d", position, format)

        # clamp between [0, duration]
        if format == Gst.Format.TIME:
            position = max(0, min(position, self.getDuration()) - 1)

        res = self._pipeline.seek(1.0, format, Gst.SeekFlags.FLUSH,
                                  Gst.SeekType.SET, position,
                                  Gst.SeekType.NONE, -1)
        self._waiting_for_async_done = True

        if self._timeout_async_id:
            GLib.source_remove(self._timeout_async_id)
            self._timeout_async_id = 0

        self._timeout_async_id = GLib.timeout_add(1000, self._resetWaitingForAsyncDone)

        if not res:
            self.debug("seeking failed")
            raise PipelineError("seek failed")

        self.lastPosition = position

        self.debug("seeking successful")
        self.emit('position', position)

    def seekRelative(self, time):
        seekvalue = max(0, min(self.getPosition() + time, self.getDuration()))
        self.simple_seek(seekvalue)

    #}
    ## Private methods

    def _busMessageCb(self, unused_bus, message):
        if message.type == Gst.MessageType.EOS:
            self.pause()
            self.emit('eos')
        elif message.type == Gst.MessageType.STATE_CHANGED:
            prev, new, pending = message.parse_state_changed()

            if message.src == self._pipeline:
                self.debug("Pipeline change state prev: %r, new: %r, pending: %r", prev, new, pending)

                emit_state_change = pending == Gst.State.VOID_PENDING
                if prev == Gst.State.READY and new == Gst.State.PAUSED:
                    # trigger duration-changed
                    try:
                        self.getDuration()
                    except PipelineError:
                        # no sinks??
                        pass
                    if self.pendingRecovery:
                        self.simple_seek(self.lastPosition)
                        self.pendingRecovery = False
                        self.info("Seeked back to the last position after pipeline recovery")
                elif prev == Gst.State.PAUSED and new == Gst.State.PLAYING:
                    self._listenToPosition(True)
                elif prev == Gst.State.PLAYING and new == Gst.State.PAUSED:
                    self._listenToPosition(False)

                if emit_state_change:
                    self.emit('state-change', new)

        elif message.type == Gst.MessageType.ERROR:
            error, detail = message.parse_error()
            self._handleErrorMessage(error, detail, message.src)
            self._waiting_for_async_done = False
            if not (self._pipeline.get_mode() & GES.PipelineFlags.RENDER):
                self._recover()
        elif message.type == Gst.MessageType.DURATION_CHANGED:
            self.debug("Duration might have changed, querying it")
            GLib.idle_add(self._queryDurationAsync)
        elif message.type == Gst.MessageType.ASYNC_DONE:
            self._attempted_recoveries = 0
            self._waiting_for_async_done = False
            if self._next_seek is not None:
                self.simple_seek(self._next_seek[0], self._next_seek[1])
                self._next_seek = None
            if self._timeout_async_id:
                GLib.source_remove(self._timeout_async_id)
                self._timeout_async_id = 0
        else:
            self.log("%s [%r]", message.type, message.src)

    def _recover(self):
        if self._attempted_recoveries > MAX_RECOVERIES:
            self.warning("Pipeline error detected multiple times in a row, not resetting anymore")
            return
        self.warning("Pipeline error detected during playback, resetting")
        self.pendingRecovery = True
        self._pipeline.set_state(Gst.State.NULL)
        self._pipeline.set_state(Gst.State.PAUSED)
        self._attempted_recoveries += 1

    def _queryDurationAsync(self, *unused_args, **unused_kwargs):
        try:
            self.getDuration()
        except:
            self.log("Duration failed... but we don't care")
        return False

    def _handleErrorMessage(self, error, detail, source):
        self.error("error from %s: %s (%s)" % (source, error, detail))
        self.emit('error', error.message, detail)

    def _getDuration(self, format=Gst.Format.TIME):
        try:
            res, dur = self._pipeline.query_duration(format)
        except Exception, e:
            self.handleException(e)
            raise PipelineError("Couldn't get duration: %s" % e)

        if not res:
            raise PipelineError("Couldn't get duration: Returned None")
        return dur


class AssetPipeline(SimplePipeline):
    """
    Pipeline for playing a single clip.
    """

    def __init__(self, clip):
        bPipeline = Gst.ElementFactory.make("playbin", None)
        bPipeline.set_property("uri", clip.props.uri)
        SimplePipeline.__init__(self, bPipeline, bPipeline)

        self.clip = clip


class Pipeline(GES.Pipeline, SimplePipeline):
    """
    Helper to handle GES.Pipeline through the SimplePipeline API
    and handle the Seeker properly

    Signals:
     - C{state-changed} : The state of the pipeline changed.
     - C{position} : The current position of the pipeline changed.
     - C{eos} : The Pipeline has finished playing.
     - C{error} : An error happened.
    """

    __gsignals__ = {
        "state-change": (GObject.SignalFlags.RUN_LAST, None,
                        (GObject.TYPE_INT,)),
        "position": (GObject.SignalFlags.RUN_LAST, None,
                        (GObject.TYPE_UINT64,)),
        "duration-changed": (GObject.SignalFlags.RUN_LAST, None,
                        (GObject.TYPE_UINT64,)),
        "eos": (GObject.SignalFlags.RUN_LAST, None, ()),
        "error": (GObject.SignalFlags.RUN_LAST, None,
                (GObject.TYPE_STRING, GObject.TYPE_STRING))
    }

    def __init__(self, pipeline=None):
        GES.Pipeline.__init__(self)
        SimplePipeline.__init__(self, self, self)

        self._clutter_sink = Gst.ElementFactory.make("cluttersink", None)
        self.preview_set_video_sink(self._clutter_sink)

        self._seeker = Seeker()
        self._seeker.connect("seek", self._seekCb)
        self._seeker.connect("seek-relative", self._seekRelativeCb)

    def _getDuration(self, format=Gst.Format.TIME):
        return self._timeline.get_duration()

    def set_timeline(self, timeline):
        if GES.Pipeline.set_timeline(self, timeline):
            self._timeline = timeline
            return True

        return False

    def release(self):
        """
        Release the L{Pipeline} and all used L{ObjectFactory} and
        L{Action}s.

        Call this method when the L{Pipeline} is no longer used. Forgetting to do
        so will result in memory loss.

        @postcondition: The L{Pipeline} will no longer be usable.
        """
        self._seeker.disconnect_by_func(self._seekRelativeCb)
        self._seeker.disconnect_by_func(self._seekCb)
        SimplePipeline.release(self)

    def _seekRelativeCb(self, unused_seeker, time):
        self.seekRelative(time)

    def stepFrame(self, framerate, frames_offset):
        """
        Seek backwards or forwards a certain amount of frames (frames_offset).
        This clamps the playhead to the project frames.
        """
        try:
            position = self.getPosition()
        except PipelineError:
            self.warning("Couldn't get position (you're framestepping too quickly), ignoring this request")
            return

        cur_frame = int(round(position * framerate.num / float(Gst.SECOND * framerate.denom), 2))
        new_frame = cur_frame + frames_offset
        new_pos = long(new_frame * Gst.SECOND * framerate.denom / framerate.num)
        Loggable.info(self, "From frame %d to %d at %f fps, seek to %s s",
                    cur_frame,
                    new_frame,
                    framerate.num / framerate.denom,
                    new_pos / float(Gst.SECOND))
        self.simple_seek(new_pos)

    def _seekCb(self, unused_ruler, position, unused_format):
        """
        The app's main seek method used when the user seeks manually.

        We clamp the seeker position so that it cannot go past 0 or the
        end of the timeline.
        """
        self.simple_seek(position)
