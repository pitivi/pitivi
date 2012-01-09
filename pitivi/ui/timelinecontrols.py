import gtk
from pitivi.receiver import receiver, handler
from gettext import gettext as _
from pitivi.utils.ui import LAYER_HEIGHT_EXPANDED, LAYER_SPACING
from pitivi.utils.loggable import Loggable

TRACK_CONTROL_WIDTH = 75


class TrackControls(gtk.Label, Loggable):
    """Contains a timeline track name.

    @ivar track: The track for which to display the name.
    @type track: An L{pitivi.timeline.track.Track} object
    """

    __gtype_name__ = 'TrackControls'

    def __init__(self, track):
        gtk.Label.__init__(self)
        Loggable.__init__(self)
        # Center the label horizontally.
        self.set_alignment(0.5, 0)
        # The value below is arbitrarily chosen so the text appears
        # centered vertically when the represented track has a single layer.
        self.set_padding(0, LAYER_SPACING * 2)
        self.set_markup(self._getTrackName(track))
        self.track = track
        self._setSize(layers_count=1)

    def _setTrack(self):
        if self.track:
            self._maxPriorityChanged(None, self.track.max_priority)

    # FIXME Stop using the receiver
    #
    # TODO implement in GES
    #track = receiver(_setTrack)
    #@handler(track, "max-priority-changed")
    #def _maxPriorityChanged(self, track, max_priority):
    #    self._setSize(max_priority + 1)

    def _setSize(self, layers_count):
        assert layers_count >= 1
        height = layers_count * (LAYER_HEIGHT_EXPANDED + LAYER_SPACING)
        self.set_size_request(TRACK_CONTROL_WIDTH, height)

    @staticmethod
    def _getTrackName(track):
        track_name = ""
        #FIXME check that it is the best way to check the type
        if track.props.track_type.first_value_name == 'GES_TRACK_TYPE_AUDIO':
            track_name = _("Audio:")
        elif track.props.track_type.first_value_name == 'GES_TRACK_TYPE_VIDEO':
            track_name = _("Video:")
        elif track.props.track_type.first_value_name == 'GES_TRACK_TYPE_TEXT':
            track_name = _("Text:")
        return "<b>%s</b>" % track_name


class TimelineControls(gtk.VBox, Loggable):
    """Contains the timeline track names."""

    def __init__(self):
        gtk.VBox.__init__(self)
        Loggable.__init__(self)
        self._tracks = []
        self._timeline = None
        self.set_spacing(LAYER_SPACING)
        self.set_size_request(TRACK_CONTROL_WIDTH, -1)

## Timeline callbacks

    def getTimeline(self):
        return self._timeline

    def setTimeline(self, timeline):
        self.debug("Setting timeline %s", timeline)

        while self._tracks:
            self._trackRemovedCb(None, 0)

        if self._timeline:
            for track in self._timeline.get_tracks():
                self._trackAddedCb(None, track)

            self._timeline.connect("track-added", self._trackAddedCb)
            self._timeline.connect("track-removed", self._trackRemovedCb)

    timeline = property(getTimeline, setTimeline, None, "The timeline property")

    def _trackAddedCb(self, timeline, track):
        track = TrackControls(track)
        self._tracks.append(track)
        self.pack_start(track, False, False)
        track.show()

    def _trackRemovedCb(self, unused_timeline, position):
        self.timeline.disconnect_by_function(self._trackAddedCb)
        self.timeline.disconnect_by_function(self._trackRemovedCb)
        track = self._tracks[position]
        del self._tracks[position]
        self.remove(track)
