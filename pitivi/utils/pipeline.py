# -*- coding: utf-8 -*-
# Pitivi video editor
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
"""High-level pipelines."""
import os

from gi.repository import GES
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst

from pitivi.check import videosink_factory
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import format_ns


PIPELINE_SIGNALS = {
    "state-change": (GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_INT, GObject.TYPE_INT)),
    "position": (GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_UINT64,)),
    "duration-changed": (GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_UINT64,)),
    "eos": (GObject.SignalFlags.RUN_LAST, None, ()),
    "error": (GObject.SignalFlags.RUN_LAST, None, (GObject.TYPE_STRING, GObject.TYPE_STRING)),
    "died": (GObject.SignalFlags.RUN_LAST, None, ()),
    "async-done": (GObject.SignalFlags.RUN_LAST, None, ()),
}

MAX_RECOVERIES = 3
WATCHDOG_TIMEOUT = 3
MAX_BRINGING_TO_PAUSED_DURATION = 5
MAX_SET_STATE_DURATION = 1

DEFAULT_POSITION_LISTENNING_INTERVAL = 500


class PipelineError(Exception):
    pass


class SimplePipeline(GObject.Object, Loggable):
    """High-level pipeline.

    The `SimplePipeline` is responsible for:
     - State changes
     - Position seeking
     - Position querying
     - Along with an periodic callback (optional)

    Signals:
        state-change: The state of the pipeline changed.
        position: The current position of the pipeline changed.
        eos: The Pipeline has finished playing.
        error: An error happened.

    Attributes:
        _pipeline (Gst.Pipeline): The low-level pipeline.
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
        self._listeningInterval = DEFAULT_POSITION_LISTENNING_INTERVAL
        self._listeningSigId = 0
        self._duration = Gst.CLOCK_TIME_NONE
        self._last_position = int(0 * Gst.SECOND)
        self._recovery_state = self.RecoveryState.NOT_RECOVERING
        self._attempted_recoveries = 0
        self._waiting_for_async_done = False
        self._next_seek = None
        self._timeout_async_id = 0
        self._force_position_listener = False

        self.video_sink = None
        self.sink_widget = None

    def create_sink(self):
        sink = Gst.ElementFactory.make(videosink_factory.get_name(), None)
        self.sink_widget = sink.props.widget

        if videosink_factory.get_name() == "gtksink":
            self.info("Using gtksink")
            self.video_sink = sink
        else:
            self.info("Using glsinkbin around %s", videosink_factory.get_name())
            sinkbin = Gst.ElementFactory.make("glsinkbin", None)
            sinkbin.props.sink = sink
            self.video_sink = sinkbin

    def setForcePositionListener(self, force):
        self._force_position_listener = force

    def release(self):
        """Releases the low-level pipeline.

        Call this method when this instance is no longer used. Forgetting to do
        so will result in memory leaks.

        The instance will no longer be usable.
        """
        self._removeWaitingForAsyncDoneTimeout()
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
            self.simple_seek(self.getPosition())
        except PipelineError as e:
            self.warning("Could not flush because: %s", e)
            pass

    def setState(self, state):
        """Sets the low-level pipeline to the specified state.

        Raises:
            PipelineError: If the low-level pipeline could not be changed to
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
        """Queries the low-level pipeline for the current state.

        This will do an actual query to the underlying GStreamer Pipeline.

        Returns:
            State: The current state.
        """
        # No timeout
        change, state, pending = self._pipeline.get_state(timeout=0)
        self.debug(
            "change: %r, state: %r, pending: %r", change, state, pending)
        return state

    def play(self):
        """Sets the state to Gst.State.PLAYING."""
        self.setState(Gst.State.PLAYING)

    def pause(self):
        """Sets the state to Gst.State.PAUSED."""
        self.setState(Gst.State.PAUSED)

    def stop(self):
        """Sets the state to Gst.State.READY."""
        self.setState(Gst.State.READY)

    def playing(self):
        return self.getState() == Gst.State.PLAYING

    def togglePlayback(self):
        if self.playing():
            self.pause()
        else:
            self.play()

    # Position and Seeking methods

    def getPosition(self, fails=True):
        """Gets the current position of the low-level pipeline.

        Returns:
            int: The current position or Gst.CLOCK_TIME_NONE.

        Raises:
            PipelineError: If the position couldn't be obtained.
        """
        try:
            res, cur = self._pipeline.query_position(Gst.Format.TIME)
        except Exception as e:
            self.handleException(e)
            raise PipelineError("Couldn't get position")

        if not res:
            if fails:
                raise PipelineError("Position not available")

            cur = self._last_position

        self.log("Got position %s", format_ns(cur))
        return cur

    def getDuration(self):
        """Gets the duration of the low-level pipeline."""
        dur = self._getDuration()
        self.log("Got duration %s", format_ns(dur))
        if self._duration != dur:
            self.emit("duration-changed", dur)
        self._duration = dur
        return dur

    def activatePositionListener(self, interval=DEFAULT_POSITION_LISTENNING_INTERVAL):
        """Activates the position listener.

        When activated, the instance will emit the `position` signal at the
        specified interval when it is the PLAYING or PAUSED state.

        Args:
            interval (int): Interval between position queries in milliseconds.

        Returns:
            bool: Whether the position listener was activated.
        """
        if self._listening:
            return True
        self._listening = True
        self._listeningInterval = interval
        # if we're in playing, switch it on
        self._listenToPosition(self.getState() == Gst.State.PLAYING)
        return True

    def deactivatePositionListener(self):
        """De-activates the position listener."""
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
        """Seeks in the low-level pipeline to the specified position.

        Args:
            position (int): Position to seek to.

        Raises:
            PipelineError: When the seek fails.
        """
        if self._waiting_for_async_done is True:
            self._next_seek = position
            self.info("Setting next seek to %s", self._next_seek)
            return

        self.debug("position: %s", format_ns(position))

        # clamp between [0, duration]
        position = max(0, min(position, self.getDuration()))

        res = self._pipeline.seek(1.0,
                                  Gst.Format.TIME,
                                  Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                                  Gst.SeekType.SET,
                                  position,
                                  Gst.SeekType.NONE,
                                  -1)

        if not res:
            raise PipelineError(self.get_name() + " seek failed: " + str(position))

        self._addWaitingForAsyncDoneTimeout()
        self._last_position = position

        self.debug("seeking successful")
        self.emit('position', position)

    def seekRelative(self, time_delta):
        try:
            self.simple_seek(self.getPosition() + int(time_delta))
        except PipelineError:
            self.error("Error while seeking %s relative", time_delta)

    # Private methods

    def _busMessageCb(self, unused_bus, message):
        if message.type == Gst.MessageType.EOS:
            self.__emitPosition()
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
                            self.error("Too many tries to seek back to right position, "
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
            Gst.debug_bin_to_dot_file_with_ts(self._pipeline,
                                              Gst.DebugGraphDetails.ALL,
                                              "pitivi.error")
            if not self._rendering():
                self._recover()
        elif message.type == Gst.MessageType.DURATION_CHANGED:
            self.debug("Duration might have changed, querying it")
            GLib.idle_add(self._queryDurationAsync)
        elif message.type == Gst.MessageType.ASYNC_DONE:
            self.emit("async-done")
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
        # is only emitted every DEFAULT_POSITION_LISTENNING_INTERVAL
        # ms and the playhead jumps during the playback.
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
        if not self._bus:
            raise PipelineError("Should not try to recover after destroy")
        if self._attempted_recoveries == MAX_RECOVERIES:
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
        self.error("error from %s: %s (%s)", source, error, detail)
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

    def _rendering(self):
        return False


class AssetPipeline(SimplePipeline):
    """Pipeline for playing a single clip."""

    def __init__(self, clip=None, name=None):
        ges_pipeline = Gst.ElementFactory.make("playbin", name)
        SimplePipeline.__init__(self, ges_pipeline)

        self.create_sink()

        self.clip = clip
        if self.clip:
            self.setClipUri(self.clip.props.uri)

    def create_sink(self):
        SimplePipeline.create_sink(self)
        self._pipeline.set_property("video_sink", self.video_sink)

    def setClipUri(self, uri):
        self._pipeline.set_property("uri", uri)


class Pipeline(GES.Pipeline, SimplePipeline):
    """Helper to handle GES.Pipeline through the SimplePipeline API."""

    __gsignals__ = PIPELINE_SIGNALS

    def __init__(self, app):
        GES.Pipeline.__init__(self)
        SimplePipeline.__init__(self, self)

        self.app = app

        self._was_empty = False
        self._commit_wanted = False

        if "watchdog" in os.environ.get("PITIVI_UNSTABLE_FEATURES", ''):
            watchdog = Gst.ElementFactory.make("watchdog", None)
            if watchdog:
                watchdog.props.timeout = WATCHDOG_TIMEOUT * 1000
                self.props.video_filter = watchdog
                watchdog = Gst.ElementFactory.make("watchdog", None)
                watchdog.props.timeout = WATCHDOG_TIMEOUT * 1000
                self.props.audio_filter = watchdog

    def create_sink(self):
        SimplePipeline.create_sink(self)
        self._pipeline.preview_set_video_sink(self.video_sink)

    def set_mode(self, mode):
        self._next_seek = None
        return GES.Pipeline.set_mode(self, mode)

    def _getDuration(self):
        return self.props.timeline.get_duration()

    def do_change_state(self, state):
        if state == Gst.StateChange.PAUSED_TO_READY:
            self._removeWaitingForAsyncDoneTimeout()

        return GES.Pipeline.do_change_state(self, state)

    def stepFrame(self, framerate, frames_offset):
        """Seeks backwards or forwards the specified amount of frames.

        This clamps the playhead to the project frames.

        Args:
            frames_offsets (int): The number of frames to step. Negative number
                for stepping backwards.
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

    def simple_seek(self, position):
        if self.props.timeline.is_empty():
            # Nowhere to seek.
            return

        if self._rendering():
            raise PipelineError("Trying to seek while rendering")

        st = Gst.Structure.new_empty("seek")
        if self.getState() == Gst.State.PLAYING:
            st.set_value("playback_time", float(
                self.getPosition()) / Gst.SECOND)
        st.set_value("start", float(position / Gst.SECOND))
        st.set_value("flags", "accurate+flush")
        self.app.write_action(st)

        try:
            SimplePipeline.simple_seek(self, position)
        except PipelineError as e:
            self.error("Error while seeking to position: %s, reason: %s",
                       format_ns(position), e)

    def _busMessageCb(self, bus, message):
        if message.type == Gst.MessageType.ASYNC_DONE:
            self.commiting = False
            self.app.gui.timeline_ui.timeline.update_visible_overlays()

        if message.type == Gst.MessageType.ASYNC_DONE and\
                self._commit_wanted:
            self.debug("Commiting now that ASYNC is DONE")
            self._addWaitingForAsyncDoneTimeout()
            self.props.timeline.commit()
            self._commit_wanted = False
        else:
            SimplePipeline._busMessageCb(self, bus, message)

    def commit_timeline(self):
        if self._waiting_for_async_done and not self._was_empty\
                and not self.props.timeline.is_empty():
            self._commit_wanted = True
            self._was_empty = False
            self.debug("commit wanted")
        else:
            self._addWaitingForAsyncDoneTimeout()
            self.props.timeline.commit()
            self.debug("Commiting right now")
            self._was_empty = self.props.timeline.is_empty()

    def setState(self, state):
        SimplePipeline.setState(self, state)
        if state >= Gst.State.PAUSED and self.props.timeline.is_empty():
            self.debug("No ASYNC_DONE will be emited on empty timelines")
            self._was_empty = True
            self._removeWaitingForAsyncDoneTimeout()

    def _rendering(self):
        mask = GES.PipelineFlags.RENDER | GES.PipelineFlags.SMART_RENDER
        return self._pipeline.get_mode() & mask != 0
