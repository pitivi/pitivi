#!/usr/bin/python
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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import gst
import os

from pitivi.factories.base import RandomAccessSourceFactory, \
        SinkFactory
from pitivi.elements.imagefreeze import ImageFreeze
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

    def getInterpolatedProperties(self, stream):
        self.debug("stream:%r", stream)
        # FIXME: dummy implementation
        props = RandomAccessSourceFactory.getInterpolatedProperties(self, 
            stream)
        if isinstance(stream, AudioStream):
            props.update({"volume" : (0.0, 2.0)})
        elif isinstance(stream, VideoStream):
            props.update({"alpha" : (0.0, 1.0)})
        self.debug("returning %r", props)
        return props

class PictureFileSourceFactory(FileSourceFactory):
    """
    Factory for image sources.

    @see: L{FileSourceFactory}, L{RandomAccessSourceFactory}.
    """

    duration = 3600 * gst.SECOND
    default_duration = 5 * gst.SECOND

    # make this overridable in tests
    ffscale_factory = 'ffvideoscale'

    def _makeDefaultBin(self):
        return self._makeStreamBin(self.output_streams[0])

    def _makeStreamBin(self, output_stream, child_bin=None):
        self.debug("making picture bin for %s", self.name)
        res = gst.Bin("picture-%s" % self.name)

        # use ffvideoscale only if available AND width < 2048
        if output_stream.width < 2048:
            try:
                scale = gst.element_factory_make(self.ffscale_factory, "scale")
                scale.props.method = 9
            except gst.ElementNotFoundError:
                scale = gst.element_factory_make("videoscale", "scale")
                scale.props.method = 2
        else:
            scale = gst.element_factory_make("videoscale", "scale")
            scale.props.method = 2

        freeze = ImageFreeze()
        res.add(scale, freeze)
        scale.link(freeze)

        self.debug("Chaining up with %r", res)

        src_pad = freeze.get_pad("src")
        sink_pad = scale.get_pad("sink")
        src_ghost = gst.GhostPad("src", src_pad)
        sink_ghost = gst.GhostPad("sink", sink_pad)
        src_ghost.set_active(True)
        sink_ghost.set_active(True)
        src_ghost.set_caps(src_pad.props.caps)
        sink_ghost.set_caps(sink_pad.props.caps)
        res.add_pad(sink_ghost)
        res.add_pad(src_ghost)

        ret = FileSourceFactory._makeStreamBin(self, output_stream,
            res)
        self.debug("Returning %r", ret)

        return ret

class URISinkFactory(SinkFactory):
    """ A simple sink factory """

    def __init__(self, uri, *args, **kwargs):
        self.uri = uri
        SinkFactory.__init__(self, *args, **kwargs)
        self.addInputStream(MultimediaStream(caps=gst.caps_new_any()))

    def _makeBin(self, input_stream=None):
        return gst.element_make_from_uri(gst.URI_SINK, self.uri)
