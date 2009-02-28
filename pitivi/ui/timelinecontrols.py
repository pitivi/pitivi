import gtk
from pitivi.receiver import receiver, handler
import pitivi.stream as stream
from gettext import gettext as _
from common import LAYER_HEIGHT_EXPANDED, LAYER_SPACING

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

    def __init__(self, track):
        gtk.Expander.__init__(self, track_name(track))
        self.track = track
        self.set_size_request(TRACK_CONTROL_WIDTH, LAYER_HEIGHT_EXPANDED)
        self.tracks = {}

class TimelineControls(gtk.HBox):

    def __init__(self, timeline):
        gtk.HBox.__init__(self)
        self.timeline = timeline
        self.set_size_request(TRACK_CONTROL_WIDTH, 50)
        self.set_spacing(LAYER_SPACING)

    timeline = receiver()

    @handler(timeline, "track-added")
    def _trackAdded(self, timeline, track):
        tc = TrackControls(track)
        self.pack_start(tc)
        tc.show()
        self.tracks[track] = tc

    @handler(timeline, "track-removed")
    def _trackRemoved(self, timeline, track):
        self.remove(self.tracks[track])

