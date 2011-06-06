# PiTiVi , Non-linear video editor
#
#       :base.py
#
# Copyright (c) 2005-2008, Edward Hervey <bilboed@bilboed.com>
#               2008,2009 Alessandro Decina <alessandro.decina@collabora.co.uk>
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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

import gst
import os

from pitivi.factories.base import RandomAccessSourceFactory, \
        SinkFactory
from pitivi.stream import MultimediaStream, AudioStream, VideoStream


class FileSourceFactory(RandomAccessSourceFactory):
    """
    Factory for local files.

    @see: L{RandomAccessSourceFactory}.
    """

    def __init__(self, uri, name=''):
        name = name or os.path.basename(uri)
        RandomAccessSourceFactory.__init__(self, uri, name)
        # FIXME: backward compatibility
        self.filename = uri


class PictureFileSourceFactory(FileSourceFactory):
    """
    Factory for image sources.

    @see: L{FileSourceFactory}, L{RandomAccessSourceFactory}.
    """

    duration = 3600 * gst.SECOND
    default_duration = 5 * gst.SECOND

    def _makeDefaultBin(self):
        return self._makeStreamBin(self.output_streams[0])

    def _makeStreamBin(self, output_stream, child_bin=None):
        self.debug("making picture bin for %s", self.name)
        freeze = gst.element_factory_make("imagefreeze")

        self.debug("Chaining up with %r", freeze)

        ret = FileSourceFactory._makeStreamBin(self, output_stream,
            freeze)
        self.debug("Returning %r", ret)

        return ret


class URISinkFactory(SinkFactory):
    """ A simple sink factory """

    def __init__(self, uri, *args, **kwargs):
        self.uri = uri
        SinkFactory.__init__(self, *args, **kwargs)
        self.addInputStream(MultimediaStream(caps=gst.caps_new_any()))

    def _makeBin(self, input_stream=None):
        sink_element = gst.element_make_from_uri(gst.URI_SINK, self.uri)
        sink_element.set_property("async", False)
        return sink_element
