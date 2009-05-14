# PiTiVi , Non-linear video editor
#
#       formatters/playlist.py
#
# Copyright (c) 2009, Edward Hervey <bilboed@bilboed.com>
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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import os.path
import gst
from pitivi.stream import AudioStream, VideoStream
from pitivi.formatters.base import LoadOnlyFormatter
from pitivi.timeline.track import Track

class PlaylistFormatter(LoadOnlyFormatter):
    """A simple playlist formatter"""

    description = "Playlist (one uri/location per line)"

    def __init__(self, *args, **kwargs):
        LoadOnlyFormatter.__init__(self, *args, **kwargs)
        self._uris = []
        self._basedir = None

    def _parseLine(self, ln):
        if ln.startswith('/'):
            # absolute path
            return 'file://' + ln.strip()
        return 'file://' + os.path.join(self._basedir, ln.strip())

    def _parse(self, location, project=None):
        path = location.split('file://', 1)[1]
        self._basedir = os.path.dirname(path)
        res = []
        # simple list of location/uri
        f = file(path)
        for ln in f.readlines():
            val = self.validateSourceURI(self._parseLine(ln))
            # FIXME : if the loading failed, we should insert a blank source
            if val:
                res.append(val)
        self._uris = res

    def _getSources(self):
        return self._uris

    def _fillTimeline(self):
        # audio and video track
        video = VideoStream(gst.Caps('video/x-raw-rgb; video/x-raw-yuv'))
        track = Track(video)
        self.project.timeline.addTrack(track)
        audio = AudioStream(gst.Caps('audio/x-raw-int; audio/x-raw-float'))
        track = Track(audio)
        self.project.timeline.addTrack(track)
        for u in self._uris:
            if u in self.project.sources:
                self.project.timeline.addSourceFactory(self.project.sources[u])

    @classmethod
    def canHandle(cls, uri):
        return uri.endswith('.pls')
