import gtk
from pitivi.receiver import receiver, handler
import pitivi.stream as stream
from gettext import gettext as _
from common import LAYER_HEIGHT_EXPANDED, LAYER_SPACING

TRACK_CONTROL_WIDTH = 75


def track_name(track):
    stream_type = type(track.stream)
    if stream_type == stream.AudioStream:
        track_name = _("Audio:")
    elif stream_type == stream.VideoStream:
        track_name = _("Video:")
    elif stream_type == stream.TextStream:
        track_name = _("Text:")
    return "<b>%s</b>" % track_name


class TrackControls(gtk.Label):
    """Contains a timeline track name."""

    __gtype_name__ = 'TrackControls'

    def __init__(self, track):
        gtk.Label.__init__(self)
        self.set_alignment(0.5, 0.1)
        self.set_markup(track_name(track))
        self.track = track
        self._setSize(layers_count=1)

    def _setTrack(self):
        if self.track:
            self._maxPriorityChanged(None, self.track.max_priority)

    track = receiver(_setTrack)

    @handler(track, "max-priority-changed")
    def _maxPriorityChanged(self, track, max_priority):
        self._setSize(max_priority + 1)

    def _setSize(self, layers_count):
        assert layers_count >= 1
        height = layers_count * (LAYER_HEIGHT_EXPANDED + LAYER_SPACING)
        self.set_size_request(TRACK_CONTROL_WIDTH, height)


class TimelineControls(gtk.VBox):
    """Contains the timeline track names."""

    def __init__(self):
        gtk.VBox.__init__(self)
        self._tracks = []
        self.set_spacing(LAYER_SPACING)
        self.set_size_request(TRACK_CONTROL_WIDTH, -1)

## Timeline callbacks

    def _set_timeline(self):
        while self._tracks:
            self._trackRemoved(None, 0)
        if self.timeline:
            for track in self.timeline.tracks:
                self._trackAdded(None, track)

    timeline = receiver(_set_timeline)

    @handler(timeline, "track-added")
    def _trackAdded(self, timeline, track):
        track = TrackControls(track)
        self._tracks.append(track)
        self.pack_start(track, False, False)
        track.show()

    @handler(timeline, "track-removed")
    def _trackRemoved(self, unused_timeline, position):
        track = self._tracks[position]
        del self._tracks[position]
        self.remove(track)
