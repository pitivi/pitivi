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
        # FIXME: dummy implementation
        props = RandomAccessSourceFactory.getInterpolatedProperties(self, 
            stream)
        if isinstance(stream, AudioStream):
            props.update({"volume" : (0.0, 5.0)})
        elif isinstance(stream, VideoStream):
            props.update({"alpha" : None})
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

    def _makeStreamBin(self, output_stream):
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
        # let's get a single stream provider
        dbin = FileSourceFactory._makeStreamBin(self, output_stream)
        res.add(dbin, scale, freeze)
        scale.link(freeze)

        dbin.connect("pad-added", self._dbinPadAddedCb,
                     scale, freeze, res)
        dbin.connect("pad-removed", self._dbinPadRemovedCb,
                     scale, freeze, res)
        self.debug("Returning %r", res)

        res.decodebin = dbin
        return res

    def _dbinPadAddedCb(self, unused_dbin, pad, scale, freeze, container):
        pad.link(scale.get_pad("sink"))
        ghost = gst.GhostPad("src", freeze.get_pad("src"))
        ghost.set_active(True)
        container.add_pad(ghost)

    def _dbinPadRemovedCb(self, unused_dbin, pad, scale, freeze, container):
        ghost = container.get_pad("src")
        # FIXME: what we want to do here is ghost.set_target(None). Since that
        # isn't possible as of pygst 0.10.15
        # (http://bugzilla.gnome.org/show_bug.cgi?id=590735) we create a
        # throw away srcpad and retarget the ghostpad we are removing to it.
        # This hopefully fixes deadlocks, abort() and other weird stuff we're
        # having with freeze.
        die = gst.Pad("die", gst.PAD_SRC)
        ghost.set_target(die)
        container.remove_pad(ghost)
        pad.unlink(scale.get_pad("sink"))

    def _releaseBin(self, bin):
        try:
            bin.decodebin.disconnect_by_func(self._dbinPadAddedCb)
            bin.decodebin.disconnect_by_func(self._dbinPadRemovedCb)
        except TypeError:
            # bin is a bin returned from makeDefaultBin
            pass
        FileSourceFactory._releaseBin(self, bin.decodebin)

class URISinkFactory(SinkFactory):
    """ A simple sink factory """

    def __init__(self, uri, *args, **kwargs):
        self.uri = uri
        SinkFactory.__init__(self, *args, **kwargs)
        self.addInputStream(MultimediaStream(caps=gst.caps_new_any()))

    def _makeBin(self, input_stream=None):
        return gst.element_make_from_uri(gst.URI_SINK, self.uri)
