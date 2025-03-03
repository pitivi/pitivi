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
"""High-level pipelines."""
import contextlib
import os

from gi.repository import GES
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst

from pitivi.check import VIDEOSINK_FACTORY
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

DEFAULT_POSITION_LISTENING_INTERVAL = 10


class PipelineError(Exception):
    pass


class SimplePipeline(GObject.Object, Loggable):
    """High-level pipeline.

    The `SimplePipeline` is responsible for:
     - State changes
     - Position seeking
     - Position querying
     - Along with a periodic callback (optional)

    Signals:
        state-change: The state of the pipeline changed.
        position: The current position of the pipeline changed.
        eos: The Pipeline has finished playing.
        error: An error happened.

    Attributes:
        _pipeline (Gst.Pipeline): The low-level pipeline.
    """

    __gsignals__ = PIPELINE_SIGNALS

    class RecoveryState:
        NOT_RECOVERING = "not-recovering"
        STARTED_RECOVERING = "started-recovering"
        SEEKED_AFTER_RECOVERING = "seeked-after-recovering"

    def __init__(self, pipeline):
        GObject.Object.__init__(self)
        Loggable.__init__(self)

        self._pipeline = pipeline
        self._bus = self._pipeline.get_bus()
        self._bus.add_signal_watch()
        self._bus.connect("message", self._bus_message_cb)
        self._listening = False  # for the position handler
        self._listening_interval = DEFAULT_POSITION_LISTENING_INTERVAL
        self._listening_sig_id = 0
        self._duration = Gst.CLOCK_TIME_NONE
        # The last known position.
        self._last_position = 0 * Gst.SECOND
        self._recovery_state = self.RecoveryState.NOT_RECOVERING
        self._attempted_recoveries = 0
        # The position where the user intends to seek.
        self._next_seek = None
        self._timeout_async_id = 0
        self._force_position_listener = False

    def create_sink(self):
        """Creates a video sink and a widget for displaying it.

        Returns:
            (Gst.Element, Gtk.Widget): An element of type Gst.ElementFlags.SINK
            and a widget connected to it.
        """
        factory_name = VIDEOSINK_FACTORY.get_name()
        sink = Gst.ElementFactory.make(factory_name, None)
        widget = sink.props.widget

        if factory_name == "gtksink":
            self.info("Using gtksink")
            video_sink = sink
        else:
            self.info("Using glsinkbin around %s", VIDEOSINK_FACTORY.get_name())
            video_sink = Gst.ElementFactory.make("glsinkbin", None)
            video_sink.props.sink = sink

        return video_sink, widget

    def set_force_position_listener(self, force):
        self._force_position_listener = force

    def release(self):
        """Releases the low-level pipeline.

        Call this method when this instance is no longer used. Forgetting to do
        so will result in memory leaks.

        The instance will no longer be usable.
        """
        self._remove_waiting_for_async_done_timeout()
        self.deactivate_position_listener()
        self._bus.disconnect_by_func(self._bus_message_cb)
        self._bus.remove_signal_watch()

        self._pipeline.set_state(Gst.State.NULL)
        self._bus = None

    def flush_seek(self):
        if self.get_simple_state() == Gst.State.PLAYING:
            self.debug("Playing, no need to flush here!")
            return

        try:
            self.simple_seek(self.get_position())
        except PipelineError as e:
            self.warning("Could not flush because: %s", e)

    def set_simple_state(self, state):
        """Sets the low-level pipeline to the specified state.

        Raises:
            PipelineError: If the low-level pipeline could not be changed to
                the requested state. In this case the state is set to
                Gst.State.NULL
        """
        self.debug("Setting state to: %r", state)
        if state >= Gst.State.PAUSED:
            cstate = self.get_simple_state()
            if cstate < Gst.State.PAUSED:
                if cstate == Gst.State.NULL:
                    timeout = MAX_BRINGING_TO_PAUSED_DURATION
                else:
                    timeout = MAX_SET_STATE_DURATION

                self._add_waiting_for_async_done_timeout("set_simple_state: %s" % state, timeout)
        else:
            self._remove_waiting_for_async_done_timeout()

        res = self._pipeline.set_state(state)
        if res == Gst.StateChangeReturn.FAILURE:
            # reset to NULL
            self._pipeline.set_state(Gst.State.NULL)
            raise PipelineError(
                "Failure changing state of the Gst.Pipeline to %r, currently reset to NULL" % state)

    def get_simple_state(self):
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
        self.set_simple_state(Gst.State.PLAYING)

    def pause(self):
        """Sets the state to Gst.State.PAUSED."""
        self.set_simple_state(Gst.State.PAUSED)

    def stop(self):
        """Sets the state to Gst.State.READY."""
        self.set_simple_state(Gst.State.READY)

    def playing(self):
        return self.get_simple_state() == Gst.State.PLAYING

    def toggle_playback(self):
        if self.playing():
            self.pause()
        else:
            if self._duration <= self._last_position:
                self.simple_seek(0)
            self.play()

    # Position and Seeking methods

    def get_position(self, fails=True):
        """Gets the current position of the low-level pipeline.

        Returns:
            int: The current position or Gst.CLOCK_TIME_NONE.

        Raises:
            PipelineError: If the position couldn't be obtained.
        """
        try:
            res, cur = self._pipeline.query_position(Gst.Format.TIME)
        except Exception as e:
            self.handle_exception(e)
            raise PipelineError("Couldn't get position") from e

        if res:
            self._last_position = cur
        else:
            if fails:
                raise PipelineError("Position not available")

            cur = self._last_position

        self.log("Got position %s", format_ns(cur))
        return cur

    def get_duration(self):
        """Gets the duration of the low-level pipeline."""
        dur = self._get_duration()
        self.log("Got duration %s", format_ns(dur))
        if self._duration != dur:
            self.emit("duration-changed", dur)
        self._duration = dur
        return dur

    def activate_position_listener(self, interval=DEFAULT_POSITION_LISTENING_INTERVAL):
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
        self._listening_interval = interval
        # if we're in playing, switch it on
        self._listen_to_position(self.get_simple_state() == Gst.State.PLAYING)
        return True

    def deactivate_position_listener(self):
        """De-activates the position listener."""
        self._listen_to_position(False)
        self._listening = False

    def _position_listener_cb(self):
        try:
            try:
                position = self.get_position()
            except PipelineError as e:
                self.warning("Could not get position because: %s", e)
            else:
                if position != Gst.CLOCK_TIME_NONE:
                    self.emit("position", position)
        finally:
            # Call me again.
            return True  # pylint: disable=lost-exception

    def _listen_to_position(self, listen=True):
        # stupid and dumm method, not many checks done
        # i.e. it does NOT check for current state
        if listen:
            if self._listening and self._listening_sig_id == 0:
                self._listening_sig_id = GLib.timeout_add(
                    self._listening_interval,
                    self._position_listener_cb)
        elif self._listening_sig_id != 0:
            GLib.source_remove(self._listening_sig_id)
            self._listening_sig_id = 0

    def _async_done_not_received_cb(self, reason, timeout):
        self.error("Async operation timed out after %d seconds, aborting: %s", timeout, reason)
        self._remove_waiting_for_async_done_timeout()
        self._recover()
        return False

    def _remove_waiting_for_async_done_timeout(self):
        if not self._busy_async:
            return

        GLib.source_remove(self._timeout_async_id)
        self._timeout_async_id = 0

    def _add_waiting_for_async_done_timeout(self, reason, timeout=WATCHDOG_TIMEOUT):
        self._remove_waiting_for_async_done_timeout()
        self._timeout_async_id = GLib.timeout_add_seconds(timeout,
                                                          self._async_done_not_received_cb,
                                                          reason, timeout)

    @property
    def _busy_async(self):
        """Gets whether the pipeline is busy in the background.

        The following operations are performed in the background:
        - State changing from READY to PAUSED. For example a pipeline in
          NULL set to PLAYING, goes through each intermediary state
          including READY to PAUSED, so we consider it ASYNC.
        - Seeking.
        - Committing, but only if the timeline is not empty at the time of the commit.

        When the pipeline is working in the background, no seek nor commit
        should be performed.

        Returns:
            bool: True iff the pipeline is busy.
        """
        return bool(self._timeout_async_id)

    def simple_seek(self, position):
        """Seeks in the low-level pipeline to the specified position.

        Args:
            position (int): Position to seek to.

        Raises:
            PipelineError: When the seek fails.
        """
        if self._busy_async or self.get_simple_state() < Gst.State.PAUSED:
            self._next_seek = position
            self.info("Setting next seek to %s", self._next_seek)
            return

        self._next_seek = None

        # clamp between [0, duration]
        position = max(0, min(position, self.get_duration()))
        self.debug("Seeking to position: %s", format_ns(position))
        res = self._pipeline.seek(1.0,
                                  Gst.Format.TIME,
                                  Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                                  Gst.SeekType.SET,
                                  position,
                                  Gst.SeekType.NONE,
                                  -1)
        if not res:
            raise PipelineError(self.get_name() + " seek failed: " + str(position))

        self._add_waiting_for_async_done_timeout("simple_seek: %s" % position)

        self.emit('position', position)

    def seek_relative(self, time_delta):
        try:
            self.simple_seek(self.get_position() + int(time_delta))
        except PipelineError:
            self.error("Error while seeking %s relative", time_delta)

    # Private methods

    def _bus_message_cb(self, unused_bus, message):
        if message.type == Gst.MessageType.EOS:
            self.__emit_position()
            self.pause()
            self.emit('eos')
        elif message.type == Gst.MessageType.STATE_CHANGED:
            if message.src == self._pipeline:
                prev, new, pending = message.parse_state_changed()
                self.debug(
                    "Pipeline changed state. prev: %r, new: %r, pending: %r", prev, new, pending)

                emit_state_change = pending == Gst.State.VOID_PENDING
                if prev == Gst.State.READY and new == Gst.State.PAUSED:
                    # trigger duration-changed
                    try:
                        self.get_duration()
                    except PipelineError as e:
                        self.warning("Could not get duration because: %s", e)
                        # no sinks??

                    if self._recovery_state == self.RecoveryState.STARTED_RECOVERING:
                        if self._attempted_recoveries == MAX_RECOVERIES:
                            self._recovery_state = self.RecoveryState.NOT_RECOVERING
                            self._attempted_recoveries = 0
                            self.error("Too many tries to seek back to right position, "
                                       "not trying again, and going back to 0 instead")
                        else:
                            self.info("Performing seek after pipeline recovery")
                            self._recovery_state = self.RecoveryState.SEEKED_AFTER_RECOVERING
                            position = self._last_position
                            if self._next_seek is not None:
                                position = self._next_seek
                            self.simple_seek(position)
                    self._listen_to_position(self._force_position_listener)
                elif prev == Gst.State.PAUSED and new == Gst.State.PLAYING:
                    self._listen_to_position(True)
                elif prev == Gst.State.PLAYING and new == Gst.State.PAUSED:
                    self._listen_to_position(self._force_position_listener)

                if emit_state_change:
                    self.emit('state-change', new, prev)

        elif message.type == Gst.MessageType.ERROR:
            error, detail = message.parse_error()
            self._handle_error_message(error, detail, message.src)
            Gst.debug_bin_to_dot_file_with_ts(self._pipeline,
                                              Gst.DebugGraphDetails.ALL,
                                              "pitivi.error")
            if not self.rendering():
                self._remove_waiting_for_async_done_timeout()
                self._recover()
        elif message.type == Gst.MessageType.DURATION_CHANGED:
            self.debug("Querying duration async, because it changed")
            GLib.idle_add(self._query_duration_async)
        elif message.type == Gst.MessageType.ASYNC_DONE:
            self.debug("Async done, ready for action")
            self.emit("async-done")
            self._remove_waiting_for_async_done_timeout()
            if self._recovery_state == self.RecoveryState.SEEKED_AFTER_RECOVERING:
                self._recovery_state = self.RecoveryState.NOT_RECOVERING
                self._attempted_recoveries = 0
            self.__emit_position()
            if self._next_seek is not None:
                self.info("Performing seek after ASYNC_DONE")
                self.simple_seek(self._next_seek)
        else:
            self.log("%s [%r]", message.type, message.src)

    def __emit_position(self):
        # When the pipeline has been paused we need to update the
        # timeline/playhead position, as the 'position' signal
        # is only emitted every DEFAULT_POSITION_LISTENNING_INTERVAL
        # ms and the playhead jumps during the playback.
        try:
            position = self.get_position()
        except PipelineError as e:
            self.warning("Getting the position failed: %s", e)
            return None

        if position != Gst.CLOCK_TIME_NONE and position >= 0:
            self.emit("position", position)

        return position

    def _recover(self):
        if not self._bus:
            raise PipelineError("Should not try to recover after destroy")

        if self._attempted_recoveries == MAX_RECOVERIES:
            self.emit("died")
            self.error("Declaring pipeline dead, because %d successive reset attempts failed", MAX_RECOVERIES)
            return

        self._attempted_recoveries += 1
        self.error("Resetting pipeline because error detected during playback. "
                   "Try %d", self._attempted_recoveries)
        self.set_simple_state(Gst.State.NULL)
        self._recovery_state = self.RecoveryState.STARTED_RECOVERING
        self.pause()

    def _query_duration_async(self, *unused_args, **unused_kwargs):
        try:
            self.get_duration()
        except PipelineError as e:
            self.warning("Could not get duration because: %s", e)
        return False

    def _handle_error_message(self, error, detail, source):
        self.error("error from %s: %s (%s)", source, error, detail)
        self.emit('error', error.message, detail)

    def _get_duration(self):
        try:
            res, dur = self._pipeline.query_duration(Gst.Format.TIME)
        except Exception as e:
            self.handle_exception(e)
            raise PipelineError("Couldn't get duration") from e

        if not res:
            raise PipelineError("Couldn't get duration: Returned None")
        return dur

    def rendering(self):
        return False


class AssetPipeline(SimplePipeline):
    """Pipeline for playing a single asset.

    Attributes:
        uri (str): The low-level pipeline.
    """

    def __init__(self, uri=None, name=None):
        ges_pipeline = Gst.ElementFactory.make("playbin", name)
        ges_pipeline.props.video_filter = Gst.parse_bin_from_description("videoflip method=automatic", True)
        SimplePipeline.__init__(self, ges_pipeline)

        self.__uri = None
        if uri:
            self.uri = uri

    def create_sink(self):
        video_sink, sink_widget = SimplePipeline.create_sink(self)
        self._pipeline.set_property("video_sink", video_sink)
        return video_sink, sink_widget

    @property
    def uri(self):
        # We could maybe get it using `self._pipeline.get_property`, but
        # after setting the state to Gst.State.PAUSED, it becomes None.
        return self.__uri

    @uri.setter
    def uri(self, uri):
        self._pipeline.set_property("uri", uri)
        self.__uri = uri


class Pipeline(GES.Pipeline, SimplePipeline):
    """Helper to handle GES.Pipeline through the SimplePipeline API."""

    __gsignals__ = PIPELINE_SIGNALS

    def __init__(self, app):
        GES.Pipeline.__init__(self)
        SimplePipeline.__init__(self, self)

        self.app = app

        self._was_empty = False
        self._commit_wanted = False
        self._prevent_commits = 0

        self.props.audio_sink = Gst.parse_bin_from_description("level ! audioconvert ! audioresample ! autoaudiosink", True)

        if "watchdog" in os.environ.get("PITIVI_UNSTABLE_FEATURES", ''):
            watchdog = Gst.ElementFactory.make("watchdog", None)
            if watchdog:
                watchdog.props.timeout = WATCHDOG_TIMEOUT * 1000
                self.props.video_filter = watchdog
                watchdog = Gst.ElementFactory.make("watchdog", None)
                watchdog.props.timeout = WATCHDOG_TIMEOUT * 1000
                self.props.audio_filter = watchdog


    def set_mode(self, mode):
        self._next_seek = None
        return GES.Pipeline.set_mode(self, mode)

    def _get_duration(self):
        return self.props.timeline.get_duration()

    def do_change_state(self, state):
        if state == Gst.StateChange.PAUSED_TO_READY:
            self._remove_waiting_for_async_done_timeout()

        return GES.Pipeline.do_change_state(self, state)

    def step_frame(self, frames_offset):
        """Seeks backwards or forwards the specified amount of frames.

        This clamps the playhead to the project frames.

        Args:
            frames_offset (int): The number of frames to step. Negative number
                for stepping backwards.
        """
        try:
            position = self.get_position()
        except PipelineError:
            self.warning(
                "Couldn't get position (you're framestepping too quickly), ignoring this request")
            return

        cur_frame = self.props.timeline.get_frame_at(position)
        new_frame = max(0, cur_frame + frames_offset)
        new_pos = self.props.timeline.get_frame_time(new_frame)
        self.info("From frame %d to %d - seek to %s",
                  cur_frame, new_frame, new_pos)
        self.simple_seek(new_pos)

    def simple_seek(self, position):
        if self.props.timeline.is_empty():
            # Nowhere to seek.
            return

        if self.rendering():
            raise PipelineError("Trying to seek while rendering")

        st = Gst.Structure.new_empty("seek")
        if self.get_simple_state() == Gst.State.PLAYING:
            st.set_value("playback_time", float(
                self.get_position()) / Gst.SECOND)
        st.set_value("start", float(position / Gst.SECOND))
        st.set_value("flags", "accurate+flush")
        self.app.write_action(st)

        try:
            SimplePipeline.simple_seek(self, position)
        except PipelineError as e:
            self.error("Error while seeking to position: %s, reason: %s",
                       format_ns(position), e)

    def _bus_message_cb(self, bus, message):
        if message.type == Gst.MessageType.ASYNC_DONE:
            self.app.gui.editor.timeline_ui.timeline.update_visible_overlays()

        if message.type == Gst.MessageType.ASYNC_DONE and\
                self._commit_wanted:
            self.debug("Committing now that ASYNC is DONE")
            self._add_waiting_for_async_done_timeout("_bus_message_cb: committing")
            self.props.timeline.commit()
            self._commit_wanted = False
        else:
            SimplePipeline._bus_message_cb(self, bus, message)

    @contextlib.contextmanager
    def commit_timeline_after(self):
        self._prevent_commits += 1
        self.info("Disabling commits during action execution")
        try:
            yield
        finally:
            self._prevent_commits -= 1
            self.commit_timeline()

    def commit_timeline(self):
        if self._prevent_commits > 0 or self.get_simple_state() == Gst.State.NULL:
            # No need to commit. NLE will do it automatically when
            # changing state from READY to PAUSED.
            return

        is_empty = self.props.timeline.is_empty()
        if self._busy_async and not self._was_empty and not is_empty:
            self._commit_wanted = True
            self._was_empty = False
            self.log("commit wanted")
        else:
            self._add_waiting_for_async_done_timeout("commit_timeline")
            self.props.timeline.commit()
            self.debug("Committing right now")
            self._was_empty = is_empty

    def set_simple_state(self, state):
        SimplePipeline.set_simple_state(self, state)
        if state >= Gst.State.PAUSED and self.props.timeline.is_empty():
            self.debug("No ASYNC_DONE will be emitted on empty timelines")
            self._was_empty = True
            self._remove_waiting_for_async_done_timeout()

    def rendering(self):
        mask = GES.PipelineFlags.RENDER | GES.PipelineFlags.SMART_RENDER
        return self._pipeline.get_mode() & mask != 0
