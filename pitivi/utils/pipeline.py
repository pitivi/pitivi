#!/usr/bin/env python3
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
import os


from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GES

from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import format_ns


PIPELINE_SIGNALS = {
    "state-change": (GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_INT, GObject.TYPE_INT)),
    "position": (GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_UINT64,)),
    "duration-changed": (GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_UINT64,)),
    "eos": (GObject.SignalFlags.RUN_LAST, None, ()),
    "error": (GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_STRING, GObject.TYPE_STRING)),
    "died": (GObject.SignalFlags.RUN_LAST, None, ()),
}

MAX_RECOVERIES = 3
WATCHDOG_TIMEOUT = 3
MAX_BRINGING_TO_PAUSED_DURATION = 5
MAX_SET_STATE_DURATION = 1


class PipelineError(Exception):
    pass


class Seeker(GObject.Object, Loggable):

    """
    The Seeker is a singleton helper class to do various seeking
    operations in the pipeline.
    """

    _instance = None

    __gsignals__ = {
        "seek": (GObject.SIGNAL_RUN_LAST, None, (GObject.TYPE_UINT64,)),
        "seek-relative": (GObject.SIGNAL_RUN_LAST, None, (GObject.TYPE_INT64,)),
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
        GObject.Object.__init__(self)
        Loggable.__init__(self)

        self.timeout = timeout
        self.pending_seek_id = None
        self.position = None
        self._time = None
        self.pending_position = None

    def seek(self, position, on_idle=False):
        self.position = position

        if self.pending_seek_id is None:
            if on_idle:
                self.pending_seek_id = self._scheduleSeek(
                    self.timeout, self._seekTimeoutCb)
            else:
                self._seekTimeoutCb()
        else:
            self.pending_position = position

    def seekRelative(self, time, on_idle=False):
        if self.pending_seek_id is None:
            self._time = int(time)
            if on_idle:
                self.pending_seek_id = self._scheduleSeek(
                    self.timeout, self._seekTimeoutCb, relative=True)
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
        elif self.position is not None:
            position = max(0, self.position)
            self.position = None
            try:
                self.emit('seek', position)
            except PipelineError as e:
                self.error("Error while seeking to position: %s, reason: %s",
                           format_ns(position), e)
                # if an exception happened while seeking, properly
                # reset ourselves
                return False

        if self.pending_position:
            self.seek(self.pending_position, on_idle=True)
            self.pending_position = None

        return False


class SimplePipeline(GObject.Object, Loggable):

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

    __gsignals__ = PIPELINE_SIGNALS

    class RecoveryState(object):
        NOT_RECOVERING = "not-recovering"
        STARTED_RECOVERING = "started-recovering"
        SEEKED_AFTER_RECOVERING = "seeked-after-recovering"

    def __init__(self, pipeline):
        GObject.Object.__init__(self)
        Loggable.__init__(self)

        self._pipeline = pipeline
        self._bus = self._pipeline.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect("message", self._busMessageCb)
        self._listening = False  # for the position handler
        self._listeningInterval = 50  # default 300ms
        self._listeningSigId = 0
        self._duration = Gst.CLOCK_TIME_NONE
        self._last_position = int(0 * Gst.SECOND)
        self._recovery_state = self.RecoveryState.NOT_RECOVERING
        self._attempted_recoveries = 0
        self._waiting_for_async_done = False
        self._next_seek = None
        self._timeout_async_id = 0
        self._force_position_listener = False

        sink = Gst.ElementFactory.make("glsinkbin", None)
        sink.props.sink = Gst.ElementFactory.make("gtkglsink", None)
        self.setSink(sink)

    def setSink(self, sink):
        self.video_sink = sink
        if isinstance(self._pipeline, GES.Pipeline):
            self._pipeline.preview_set_video_sink(self.video_sink)
        else:
            self._pipeline.set_property("video_sink", self.video_sink)

    def setForcePositionListener(self, force):
        self._force_position_listener = force

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

        self._pipeline.set_state(Gst.State.NULL)
        self._bus = None

    def flushSeek(self):
        if self.getState() == Gst.State.PLAYING:
            self.debug("Playing, no need to flush here!")
            return

        try:
            self.seekRelative(0)
        except PipelineError as e:
            self.warning("Could not flush because: %s", e)
            pass

    def setState(self, state):
        """
        Set the L{Pipeline} to the given state.

        @raises PipelineError: If the C{Gst.Pipeline} could not be changed to
        the requested state.
        """
        self.debug("state set to: %r", state)
        if state >= Gst.State.PAUSED:
            cstate = self.getState()
            if cstate < Gst.State.PAUSED:
                if cstate == Gst.State.NULL:
                    timeout = MAX_BRINGING_TO_PAUSED_DURATION
                else:
                    timeout = MAX_SET_STATE_DURATION

                self._addWaitingForAsyncDoneTimeout(timeout)
        else:
            self._removeWaitingForAsyncDoneTimeout()

        res = self._pipeline.set_state(state)
        if res == Gst.StateChangeReturn.FAILURE:
            # reset to NULL
            self._pipeline.set_state(Gst.State.NULL)
            raise PipelineError(
                "Failure changing state of the Gst.Pipeline to %r, currently reset to NULL" % state)

    def getState(self):
        """
        Query the L{Pipeline} for the current state.

        @see: L{setState}

        This will do an actual query to the underlying GStreamer Pipeline.
        @return: The current state.
        @rtype: C{State}
        """
        # No timeout
        change, state, pending = self._pipeline.get_state(timeout=0)
        self.debug(
            "change: %r, state: %r, pending: %r", change, state, pending)
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

    # Position and Seeking methods

    def getPosition(self, blocks=False):
        """
        Get the current position of the L{Pipeline}.

        @return: The current position or Gst.CLOCK_TIME_NONE
        @rtype: L{long}
        @raise PipelineError: If the position couldn't be obtained.
        """
        maincontext = GLib.main_context_default()
        if blocks and self._recovery_state == self.RecoveryState.NOT_RECOVERING:
            while self._waiting_for_async_done and self._recovery_state == self.RecoveryState.NOT_RECOVERING:
                self.info("Iterating mainloop waiting for the pipeline to be ready to be queried")
                maincontext.iteration(True)

        try:
            res, cur = self._pipeline.query_position(Gst.Format.TIME)
        except Exception as e:
            self.handleException(e)
            raise PipelineError("Couldn't get position")

        if not res:
            raise PipelineError("Position not available")

        self.log("Got position %s", format_ns(cur))
        return cur

    def getDuration(self):
        """
        Get the duration of the C{Pipeline}.
        """
        dur = self._getDuration()
        self.log("Got duration %s", format_ns(dur))
        if self._duration != dur:
            self.emit("duration-changed", dur)
        self._duration = dur
        return dur

    def activatePositionListener(self, interval=50):
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
        # if we're in playing, switch it on
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
            try:
                position = self.getPosition()
            except PipelineError as e:
                self.warning("Could not get position because: %s", e)
            else:
                if position != Gst.CLOCK_TIME_NONE:
                    self.emit('position', position)
                    self._last_position = position
        finally:
            return True

    def _listenToPosition(self, listen=True):
        # stupid and dumm method, not many checks done
        # i.e. it does NOT check for current state
        if listen:
            if self._listening and self._listeningSigId == 0:
                self._listeningSigId = GLib.timeout_add(
                    self._listeningInterval,
                    self._positionListenerCb)
        elif self._listeningSigId != 0:
            GLib.source_remove(self._listeningSigId)
            self._listeningSigId = 0

    def _asyncDoneNotReceivedCb(self):
        self.error("we didn't get async done, this is a bug")
        self._recover()
        # Source is being removed
        self._removeWaitingForAsyncDoneTimeout()
        return False

    def _removeWaitingForAsyncDoneTimeout(self):
        if self._timeout_async_id:
            GLib.source_remove(self._timeout_async_id)
        self._timeout_async_id = 0

    def _addWaitingForAsyncDoneTimeout(self, timeout=WATCHDOG_TIMEOUT):
        self._removeWaitingForAsyncDoneTimeout()

        self._timeout_async_id = GLib.timeout_add_seconds(timeout,
                                                          self._asyncDoneNotReceivedCb)
        self._waiting_for_async_done = True

    def simple_seek(self, position):
        """
        Seeks in the L{Pipeline} to the given position.

        @param position: Position to seek to
        @type position: L{long}
        @raise PipelineError: If seek failed
        """
        if self._waiting_for_async_done is True:
            self._next_seek = position
            self.info("Setting next seek to %s", self._next_seek)
            return

        self.debug("position: %s", format_ns(position))

        # clamp between [0, duration]
        position = max(0, min(position, self.getDuration()))

        res = self._pipeline.seek(1.0, Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                                  Gst.SeekType.SET, position,
                                  Gst.SeekType.NONE, -1)
        self._addWaitingForAsyncDoneTimeout()

        if not res:
            raise PipelineError(self.get_name() + " seek failed: " + str(position))

        self._last_position = position

        self.debug("seeking successful")
        self.emit('position', position)

    def seekRelative(self, time_delta):
        self.simple_seek(self.getPosition() + time_delta)

    # Private methods

    def _busMessageCb(self, unused_bus, message):
        if message.type == Gst.MessageType.EOS:
            self.pause()
            self.emit('eos')
        elif message.type == Gst.MessageType.STATE_CHANGED:
            prev, new, pending = message.parse_state_changed()

            if message.src == self._pipeline:
                self.debug(
                    "Pipeline change state prev: %r, new: %r, pending: %r", prev, new, pending)

                emit_state_change = pending == Gst.State.VOID_PENDING
                if prev == Gst.State.READY and new == Gst.State.PAUSED:
                    # trigger duration-changed
                    try:
                        self.getDuration()
                    except PipelineError as e:
                        self.warning("Could not get duration because: %s", e)
                        # no sinks??
                        pass

                    if self._recovery_state == self.RecoveryState.STARTED_RECOVERING:
                        if self._attempted_recoveries == MAX_RECOVERIES:
                            self._recovery_state = self.RecoveryState.NOT_RECOVERING
                            self._attempted_recoveries = 0
                            self.error("Too many tries to seek back to right position"
                                       "not trying again, and going back to 0 instead")
                        else:
                            self._recovery_state = self.RecoveryState.SEEKED_AFTER_RECOVERING
                            self.simple_seek(self._last_position)
                            self.info(
                                "Seeked back to the last position after pipeline recovery")
                    self._listenToPosition(self._force_position_listener)
                elif prev == Gst.State.PAUSED and new == Gst.State.PLAYING:
                    self._listenToPosition(True)
                elif prev == Gst.State.PLAYING and new == Gst.State.PAUSED:
                    self._listenToPosition(self._force_position_listener)

                if emit_state_change:
                    self.emit('state-change', new, prev)

        elif message.type == Gst.MessageType.ERROR:
            error, detail = message.parse_error()
            self._handleErrorMessage(error, detail, message.src)
            Gst.debug_bin_to_dot_file_with_ts(self, Gst.DebugGraphDetails.ALL,
                                              "pitivi.error")
            if not (self._pipeline.get_mode() & GES.PipelineFlags.RENDER):
                self._recover()
        elif message.type == Gst.MessageType.DURATION_CHANGED:
            self.debug("Duration might have changed, querying it")
            GLib.idle_add(self._queryDurationAsync)
        elif message.type == Gst.MessageType.ASYNC_DONE:
            if self._recovery_state == self.RecoveryState.SEEKED_AFTER_RECOVERING:
                self._recovery_state = self.RecoveryState.NOT_RECOVERING
                self._attempted_recoveries = 0
            self._waiting_for_async_done = False
            self.__emitPosition()
            if self._next_seek is not None:
                self.simple_seek(self._next_seek)
                self._next_seek = None
            self._removeWaitingForAsyncDoneTimeout()
        else:
            self.log("%s [%r]", message.type, message.src)

    def __emitPosition(self):
        # When the pipeline has been paused we need to update the
        # timeline/playhead position, as the 'position' signal
        # is only emitted every 300ms and the playhead jumps
        # during the playback.
        try:
            position = self.getPosition()
        except PipelineError as e:
            self.warning("Getting the position failed: %s", e)
            return None

        if position != Gst.CLOCK_TIME_NONE and position >= 0:
            self.emit("position", position)

        return position

    @property
    def _waiting_for_async_done(self):
        return self.__waiting_for_async_done

    @_waiting_for_async_done.setter
    def _waiting_for_async_done(self, value):
        self.__waiting_for_async_done = value

    def _recover(self):
        if self._attempted_recoveries > MAX_RECOVERIES:
            self.emit("died")
            self.error(
                "Pipeline error detected multiple times in a row, not resetting anymore")
            return

        self.error("Pipeline error detected during playback, resetting"
                   " -- num tries: %d", self._attempted_recoveries)

        self.setState(Gst.State.NULL)
        self._recovery_state = self.RecoveryState.STARTED_RECOVERING
        self.pause()

        self._attempted_recoveries += 1

    def _queryDurationAsync(self, *unused_args, **unused_kwargs):
        try:
            self.getDuration()
        except Exception as e:
            self.warning("Could not get duration because: %s", e)
        return False

    def _handleErrorMessage(self, error, detail, source):
        self.error("error from %s: %s (%s)" % (source, error, detail))
        self.emit('error', error.message, detail)

    def _getDuration(self):
        try:
            res, dur = self._pipeline.query_duration(Gst.Format.TIME)
        except Exception as e:
            self.handleException(e)
            raise PipelineError("Couldn't get duration: %s" % e)

        if not res:
            raise PipelineError("Couldn't get duration: Returned None")
        return dur


class AssetPipeline(SimplePipeline):

    """
    Pipeline for playing a single clip.
    """

    def __init__(self, clip=None, name=None):
        bPipeline = Gst.ElementFactory.make("playbin", name)
        SimplePipeline.__init__(self, bPipeline)

        self.clip = clip
        if self.clip:
            self.setClipUri(self.clip.props.uri)

    def setClipUri(self, uri):
        self._pipeline.set_property("uri", uri)


class Pipeline(GES.Pipeline, SimplePipeline):

    """
    Helper to handle GES.Pipeline through the SimplePipeline API
    and handle the Seeker properly
    """

    __gsignals__ = PIPELINE_SIGNALS

    def __init__(self, app, pipeline=None):
        GES.Pipeline.__init__(self)
        SimplePipeline.__init__(self, self)

        self.app = app

        self._was_empty = False
        self._commit_wanted = False

        self._timeline = None
        self._seeker = Seeker()
        self._seeker.connect("seek", self._seekCb)
        self._seeker.connect("seek-relative", self._seekRelativeCb)

        if "watchdog" in os.environ.get("PITIVI_UNSTABLE_FEATURES", ''):
            watchdog = Gst.ElementFactory.make("watchdog", None)
            if watchdog:
                watchdog.props.timeout = WATCHDOG_TIMEOUT * 1000
                self.props.video_filter = watchdog
                watchdog = Gst.ElementFactory.make("watchdog", None)
                watchdog.props.timeout = WATCHDOG_TIMEOUT * 1000
                self.props.audio_filter = watchdog

    def _getDuration(self):
        return self._timeline.get_duration()

    def set_timeline(self, timeline):
        if not GES.Pipeline.set_timeline(self, timeline):
            raise PipelineError("Cannot set the timeline to the pipeline")
        self._timeline = timeline

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

    def _seekRelativeCb(self, unused_seeker, time_delta):
        self.seekRelative(time_delta)

    def stepFrame(self, framerate, frames_offset):
        """
        Seek backwards or forwards a certain amount of frames (frames_offset).
        This clamps the playhead to the project frames.
        """
        try:
            position = self.getPosition()
        except PipelineError:
            self.warning(
                "Couldn't get position (you're framestepping too quickly), ignoring this request")
            return

        cur_frame = int(
            round(position * framerate.num / float(Gst.SECOND * framerate.denom), 2))
        new_frame = cur_frame + frames_offset
        new_pos = int(new_frame * Gst.SECOND * framerate.denom / framerate.num) + \
            int((Gst.SECOND * framerate.denom / framerate.num) / 2)
        Loggable.info(self, "From frame %d to %d at %f fps, seek to %s s",
                      cur_frame,
                      new_frame,
                      framerate.num / framerate.denom,
                      new_pos / float(Gst.SECOND))
        self.simple_seek(new_pos)

    def _seekCb(self, unused_seeker, position):
        """
        The app's main seek method used when the user seeks manually.

        We clamp the seeker position so that it cannot go past 0 or the
        end of the timeline.
        """
        self.simple_seek(position)

    def simple_seek(self, position):
        st = Gst.Structure.new_empty("seek")

        if self.getState() == Gst.State.PLAYING:
            st.set_value("playback_time", float(
                self.getPosition()) / Gst.SECOND)

        st.set_value("start", float(position / Gst.SECOND))
        st.set_value("flags", "accurate+flush")
        self.app.write_action(st)

        SimplePipeline.simple_seek(self, position)

    def _busMessageCb(self, bus, message):
        if message.type == Gst.MessageType.ASYNC_DONE and\
                self._commit_wanted:
            self.debug("Commiting now that ASYNC is DONE")
            self._addWaitingForAsyncDoneTimeout()
            self._timeline.commit()
            self._commit_wanted = False
        else:
            super(Pipeline, self)._busMessageCb(bus, message)

    def commit_timeline(self):
        if self._waiting_for_async_done and not self._was_empty\
                and not self._timeline.is_empty():
            self._commit_wanted = True
            self._was_empty = False
            self.debug("commit wanted")
        else:
            self._addWaitingForAsyncDoneTimeout()
            self._timeline.commit()
            self.debug("Commiting right now")
            if self._timeline.is_empty():
                self._was_empty = True
            else:
                self._was_empty = False

    def setState(self, state):
        super(Pipeline, self).setState(state)
        if state >= Gst.State.PAUSED and self._timeline.is_empty():
            self.debug("No ASYNC_DONE will be emited on empty timelines")
            self._was_empty = True
            self._removeWaitingForAsyncDoneTimeout()
