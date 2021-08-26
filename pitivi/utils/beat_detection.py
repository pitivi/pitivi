# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2021, Piotr Brzeziński <thewildtreee@gmail.com>
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
import tempfile
import threading
from enum import Enum

from gi.repository import GES
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GstPbutils
from gi.repository import GstTranscoder

from pitivi.utils.markers import MarkerListManager


class DetectionState(Enum):
    """Represents individual states of the beat detection process.

    Each state's value represents the percentage of completion in relation
    to the entire procedure.
    """

    IDLE = 0
    TRANSCODING = 25
    PREPARING_DETECTION = 50
    DETECTING = 75
    FINISHED = 100


class BeatDetector(GObject.Object):
    """Class responsible for performing beat detection on audio clips.

    Takes in a GESAudioSource, exposes methods for starting beat detection and
    clearing previously detected beats, as well as properties such as detection progress.
    Emits "detection-percentage" signals during beat detection and "detection-failed"
    when an error occurs during said process.

    Relies on GstTranscoder usage to extract the audio asset into raw WAV data
    and passes it to a beat detection library which returns timestamps of each detected beat.
    """

    __gsignals__ = {
        "detection-percentage": (GObject.SignalFlags.RUN_LAST, None, (int,)),
        "detection-failed": (GObject.SignalFlags.RUN_LAST, None, (str,)),
    }

    def __init__(self, ges_source: GES.AudioSource):
        GObject.Object.__init__(self)
        self._ges_source = ges_source
        self._manager: MarkerListManager = ges_source.markers_manager
        self._state = DetectionState.IDLE

    @property
    def in_progress(self) -> bool:
        """Returns whether beat detection is currently in progress."""
        return DetectionState.IDLE.value < self.progress < DetectionState.FINISHED.value

    @property
    def progress(self) -> int:
        """Returns current percentage of completion of the beat detection process."""
        return self._state.value

    @property
    def beat_list_exists(self) -> bool:
        """Returns whether a marker list containing beat markers exists."""
        return self._manager.list_exists("beat_markers")

    def clear_beats(self):
        """Removes the marker list containing previously detected beats."""
        if self.in_progress or not self.beat_list_exists:
            return

        self._manager.remove_list("beat_markers")

    def detect_beats(self):
        """Starts beat detection on the asset given in the constructor.

        Will emit the "detection-percentage" signal during every step of the process.
        In case an error occurs, "detection-failed" will be emitted along with a string
        representing the cause of the failure.

        Will not do anything if beat detection is ongoing.
        """
        if self.in_progress:
            return

        GLib.idle_add(self._set_state, DetectionState.TRANSCODING)
        asset = self._ges_source.get_parent().get_asset()
        self.__perform_transcoding(asset)

    def _set_state(self, value):
        if self._state == value:
            return

        self._state = value
        self.emit("detection-percentage", self._state.value)

        # In case of the FINISHED state, we emit it
        # and then go back to idle without emitting.
        if self._state == DetectionState.FINISHED:
            self._state = DetectionState.IDLE

    def __perform_transcoding(self, asset: GES.Asset):
        profile = self.__create_encoding_profile()
        asset_uri = asset.get_id()

        result_file = tempfile.NamedTemporaryFile()  # pylint: disable=consider-using-with
        result_uri = Gst.filename_to_uri(result_file.name)
        transcoder = GstTranscoder.Transcoder.new_full(
            asset_uri, result_uri, profile)

        signals_emitter = transcoder.get_signal_adapter(None)
        # Passing transcoder here so the reference
        # doesn't get lost after the async call below.
        signals_emitter.connect("done", self.__transcoder_done_cb, result_file, transcoder)
        signals_emitter.connect(
            "error", self.__transcoder_error_cb, result_file, transcoder)

        transcoder.run_async()

    def __transcoder_done_cb(self, emitter, result_file, transcoder):
        self.__disconnect_transcoder(transcoder)
        thread = threading.Thread(target=self.__perform_beat_detection, args=(result_file,))
        thread.start()

    def __transcoder_error_cb(self, emitter, error, details, result_file, transcoder):
        result_file.close()
        self.__disconnect_transcoder(transcoder)
        GLib.idle_add(self._set_state, DetectionState.IDLE)
        self.emit("detection-failed", str(error))

    def __disconnect_transcoder(self, transcoder):
        signals_emitter = transcoder.get_signal_adapter(None)
        signals_emitter.disconnect_by_func(self.__transcoder_done_cb)
        signals_emitter.disconnect_by_func(self.__transcoder_error_cb)

    def __perform_beat_detection(self, audio_file):
        import librosa

        GLib.idle_add(self._set_state, DetectionState.PREPARING_DETECTION)
        y, sr = librosa.load(audio_file.name)

        GLib.idle_add(self._set_state, DetectionState.DETECTING)
        _, beat_times = librosa.beat.beat_track(y=y, sr=sr, units="time")

        audio_file.close()
        # Schedule marker creation in the UI thread.
        GLib.idle_add(self.__save_beat_markers, beat_times)

    def __save_beat_markers(self, beat_times):
        # Times from librosa are returned in seconds.
        marker_timestamps = [time * Gst.SECOND for time in beat_times]

        if self._manager.list_exists("beat_markers"):
            self._manager.remove_list("beat_markers")

        # Save the list, overwriting the current one if any.
        self._manager.add_list("beat_markers", marker_timestamps)
        self._manager.current_list_key = "beat_markers"
        self._set_state(DetectionState.FINISHED)

    def __create_encoding_profile(self):
        container_profile = GstPbutils.EncodingContainerProfile.new("wav-audio-profile",
                                                                    ("WAV audio-only container"),
                                                                    Gst.Caps("audio/x-wav"),
                                                                    None)
        audio_profile = GstPbutils.EncodingAudioProfile.new(
            Gst.Caps("audio/x-raw"), None, None, 0)
        container_profile.add_profile(audio_profile)
        return container_profile
