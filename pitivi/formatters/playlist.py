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
import ConfigParser
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

    def _loadProject(self, location, project):
        path = location.split('file://', 1)[1]
        self._basedir = os.path.dirname(path)
        if path.endswith('.pls'):
            self._parsePLS(path)
        else:
            self._parseM3U(path)
        self._finishLoadingProject(project)

    def _parseLine(self, ln):
        if ln.startswith('#'):
            return
        elif ln.startswith('/'):
            # absolute path
            return 'file://' + ln.strip()
        return 'file://' + os.path.join(self._basedir, ln.strip())

    def _parseM3U(self, path):
        res = []
        # simple list of location/uri
        f = file(path)
        for ln in f.readlines():
            val = self.validateSourceURI(self._parseLine(ln))
            # FIXME : if the loading failed, we should insert a blank source
            res.append(val)
        self._uris = res

    def _parsePLS(self, filename):
        # load and parse pls format
        # http://en.wikipedia.org/wiki/PLS_%28file_format%29
        config = ConfigParser.ConfigParser()
        config.read((filename, ))
        res = []
        for i in range(config.getint('playlist', 'NumberOfEntries')):
            ln = config.get('playlist', 'File%d' % (i+1))
            val = self.validateSourceURI(self._parseLine(ln))
            # FIXME : if the loading failed, we should insert a blank source
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
        for uri in self._uris:
            factory = self.project.sources.getUri(uri)
            self.project.timeline.addSourceFactory(factory)

    @classmethod
    def canHandle(cls, uri):
        return os.path.splitext(uri)[-1] in ('.pls', '.m3u')
