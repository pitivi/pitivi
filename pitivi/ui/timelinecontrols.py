import gtk
import gobject
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
        self.set_expanded(True)
        self.set_sensitive(False)
        self.track = track
        self.set_size_request(TRACK_CONTROL_WIDTH, LAYER_HEIGHT_EXPANDED)

    def set_expanded(self, expanded):
        if expanded != self.props.expanded:
            if expanded:
                self.set_size_request(TRACK_CONTROL_WIDTH, LAYER_HEIGHT_EXPANDED)
            else:
                self.set_size_request(TRACK_CONTROL_WIDTH, LAYER_HEIGHT_COLLAPSED)

        gtk.Expander.set_expanded(self, expanded)

    def do_activate(self):
        self.props.expanded = not self.props.expanded

    track = receiver()

    @handler(track, "max-priority-changed")
    def _maxPriorityChanged(self, track, max_priority):
        self.set_size_request(TRACK_CONTROL_WIDTH, (1 +
            self.track.max_priority) * (LAYER_HEIGHT_EXPANDED +
            LAYER_SPACING))

class TimelineControls(gtk.VBox):
    __gsignals__ = {
        "track-expanded" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                (gobject.TYPE_PYOBJECT, gobject.TYPE_BOOLEAN))
    }

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
        self._connectToTrackControls(track)
        self._tracks.append(track)
        self.pack_start(track, False, False)

    @handler(timeline, "track-removed")
    def _trackRemoved(self, unused_timeline, position):
        track = self._tracks[position]
        self._disconnectFromTrackControls(track)
        del self._tracks[position]
        self.remove(track)

    def _connectToTrackControls(self, track_controls):
        track_controls.connect("notify::expanded",
                self._trackControlsExpandedCb)

    def _disconnectFromTrackControls(self, track_controls):
        track_controls.disconnect_by_func(self._trackControlsExpandedCb)

    def _trackControlsExpandedCb(self, track_controls, pspec):
        self.emit('track-expanded', track_controls.track,
                track_controls.props.expanded)
