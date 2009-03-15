import gtk
from pitivi.receiver import receiver, handler
import pitivi.stream as stream
from gettext import gettext as _
from common import LAYER_HEIGHT_EXPANDED, LAYER_HEIGHT_COLLAPSED, LAYER_SPACING

TRACK_CONTROL_WIDTH = 75

def track_name(track):
    stream_type = type(track.stream)
    if stream_type == stream.AudioStream:
        return _("<b>Audio:</b>")
    elif stream_type == stream.VideoStream:
        return _("<b>Video:</b>")
    elif stream_type == stream.TextStream:
        return _("<b>Text:</b>")

class TrackControls(gtk.Expander):

    __gtype_name__ = 'TrackControls'

    __gsignals__ = {
        "activate" : "override",
    }

    def __init__(self, track):
        gtk.Expander.__init__(self, track_name(track))
        self.props.use_markup = True
        self.set_expanded(track.expanded)
        self.set_sensitive(False)
        self.track = track
        self.set_size_request(TRACK_CONTROL_WIDTH, LAYER_HEIGHT_EXPANDED)

    def do_activate(self):
        self.track.expanded = not self.track.expanded 

    track = receiver()

    @handler(track, "max-priority-changed")
    def _maxPriorityChanged(self, track):
        self.set_size_request(TRACK_CONTROL_WIDTH, (1 +
            self.track.max_priority) * (LAYER_HEIGHT_EXPANDED +
            LAYER_SPACING))

    @handler(track, "expanded-changed")
    def _expandedChanged(self, track):
        if self.track.expanded:
            self.set_size_request(TRACK_CONTROL_WIDTH, LAYER_HEIGHT_EXPANDED)
        else:
            self.set_size_request(TRACK_CONTROL_WIDTH, LAYER_HEIGHT_COLLAPSED)
        self.set_expanded(self.track.expanded)

class TimelineControls(gtk.VBox):

    def __init__(self, timeline):
        gtk.VBox.__init__(self)
        self._tracks = []
        self.set_spacing(LAYER_SPACING)
        self.timeline = timeline

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

    @handler(timeline, "track-removed")
    def _trackRemoved(self, unused_timeline, position):
        track = self._tracks[position]
        del self._tracks[position]
        self.remove(track)
