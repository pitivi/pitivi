#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       objectfactory.py
#
# Copyright (c) 2005-2008, Edward Hervey <bilboed@bilboed.com>
#               2008, Alessandro Decina <alessandro.decina@collabora.co.uk>
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

"""
Providers of elements to use in a timeline
"""

import os.path
from urllib import unquote
import weakref
from random import randint
import gobject
import gst

from serializable import Serializable
from settings import ExportSettings
from stream import get_stream_for_caps

from gettext import gettext as _

from elements.singledecodebin import SingleDecodeBin
from elements.imagefreeze import ImageFreeze

class ObjectFactoryError(Exception):
    # FIXME: define a proper hierarchy
    pass

class ObjectFactory(object):
    """
    Base class for all factory implementations.

    Factories are objects that create GStreamer bins to produce, process or
    render streams.

    @ivar name: Factory name.
    @type name: C{str}
    @ivar displayname: Nicer name for the factory that could be used in an UI.
    @type displayname: C{str}
    @ivar input_streams: List of input streams.
    @type input_streams: C{list}
    @ivar output_streams: List of output streams.
    @type output_streams: C{list}
    @ivar duration: Duration in nanoseconds.
    @type duration: C{int}
    @ivar default_duration: Default duration in nanoseconds. For most factories,
    L{duration} and L{default_duration} are equivalent. Factories that have an
    infinite duration may specify a default duration that will be used when they
    are added to the timeline.
    @type default_duration: C{int}
    @ivar icon: Icon associated with the factory.
    @type icon: C{str}
    """
    
    def __init__(self, name="", displayname=""):
        gst.info("name:%s" % name)
        self.parent = None
        self.name = name
        self.displayname = displayname
        self.input_streams = []
        self.output_streams = []
        self.duration = gst.CLOCK_TIME_NONE
        self._default_duration = gst.CLOCK_TIME_NONE
        self._icon = None

    def _getDefaultDuration(self):
        if self._default_duration != gst.CLOCK_TIME_NONE:
            duration = self._default_duration
        elif self.duration != gst.CLOCK_TIME_NONE:
            duration = self.duration
        else:
            duration = gst.CLOCK_TIME_NONE

        return duration

    def _setDefaultDuration(self, default_duration):
        self._default_duration = default_duration

    default_duration = property(_getDefaultDuration, _setDefaultDuration)

    def _getIcon(self):
        icon = self._icon
        factory = self
        while icon is None and factory.parent:
            icon = factory.parent._icon
            factory = factory.parent

        return icon

    def _setIcon(self, icon):
        self._icon = icon

    icon = property(_getIcon, _setIcon)

    def addInputStream(self, stream):
        """
        Add a stream to the list of inputs the factory can consume.

        @param stream: Stream
        @type stream: Instance of a L{MultimediaStream} derived class
        """
        self.input_streams.append(stream)

    def removeInputStream(self, stream):
        """
        Remove a stream from the list of inputs the factory can consume.

        @param stream: Stream
        @type stream: Instance of a L{MultimediaStream} derived class
        """
        self.input_streams.remove(stream)

    def addOutputStream(self, stream):
        """
        Add a stream to the list of outputs the factory can produce.

        @param stream: Stream
        @type stream: Instance of a L{MultimediaStream} derived class
        """
        self.output_streams.append(stream)

    def removeOutputStream(self, stream):
        """
        Remove a stream from the list of inputs the factory can produce.

        @param stream: Stream
        @type stream: Instance of a L{MultimediaStream} derived class
        """
        self.output_streams.remove(stream)

    def __str__(self):
        return "<%s: %s>" % (self.__class__.__name__, self._displayname or self._name)

class SourceFactory(ObjectFactory):
    """
    Base class for factories that produce output and have no input.
    """
    
    def makeBin(self, output_stream=None):
        """
        Create a bin that outputs the stream described by C{output_stream}.

        If C{output_stream} is None, it's up to the implementations to return a
        suitable "default" bin.

        @param output_stream: A L{MultimediaStream}
        """
        
        if output_stream is not None and \
                output_stream not in self.output_streams:
            raise ObjectFactoryError('unknown stream')

        return self._makeBin(output_stream)

    def _makeBin(self, output_stream=None):
        raise NotImplementedError()

    def addInputStream(self, stream):
        raise AssertionError("source factories can't have input streams")

class LiveSourceFactory(SourceFactory):
    """
    Base class for factories that produce live streams.

    The duration of a live source is unknown and it's possibly infinite. The
    default duration is set to 5 seconds to a live source can be managed in a
    timeline.
    """
    
    def __init__(self, name, displayname, default_duration=None):
        SourceFactory.__init__(self, name, displayname)
        if default_duration is None:
            default_duration = 5 * gst.SECOND

        self.default_duration = default_duration

class RandomAccessSourceFactory(SourceFactory):
    """
    Base class for source factories that support random access.

    @ivar offset: Offset from the beginning in nanoseconds. If the source has a
    parent, offset is relative to the parent's offset.
    @type offset: C{int}
    @ivar offset_length: Length in nanoseconds. If the source has a parent,
    length can potentially be clipped.
    @type offset_length: C{int}
    """
    offset = 0
    offset_length = -1

class URISourceFactoryMixin(object):
    """
    Abstract mixin for sources that access an URI.
    """

    # make this an attribute to inject it from tests
    singleDecodeBinClass = SingleDecodeBin

    def __init__(self, uri):
        self.uri = uri

    def _makeBin(self, output_stream):
        if output_stream is None:
            return self._makeDefaultBin()

        return self._makeStreamBin(output_stream)

    def _makeDefaultBin(self):
        """
        Return a bin that decodes all the available streams.

        This is generally used to get an overview of the source media before
        splitting it in separate streams.
        """
        bin = gst.Bin("%s" % self.name)
        src = gst.element_make_from_uri(gst.URI_SRC, self.uri)
        try:
            dbin = gst.element_factory_make("decodebin2")
        except:
            dbin = gst.element_factory_make("decodebin")
        bin.add(src, dbin)
        src.link(dbin)

        dbin.connect("new-decoded-pad", self._binNewDecodedPadCb, bin)
        dbin.connect("removed-decoded-pad", self._binRemovedDecodedPadCb, bin)

        return bin

    def _binNewDecodedPadCb(self, unused_dbin, pad, unused_is_last, bin):
        ghost_pad = gst.GhostPad(pad.get_name(), pad)
        ghost_pad.set_active(True)
        bin.add_pad(ghost_pad)

    def _binRemovedDecodedPadCb(self, unused_dbin, pad, bin):
        ghost_pad = bin.get_pad(pad.get_name())
        bin.remove_pad(ghost_pad)

    def _makeStreamBin(self, output_stream):
        return self.singleDecodeBinClass(uri=self.uri, caps=output_stream.caps,
                stream=output_stream)

class LiveURISourceFactory(URISourceFactoryMixin, LiveSourceFactory):
    """
    Factory for live sources accessible at a given URI.

    @see L{LiveSourceFactory}.
    """
    def __init__(self, uri, name='', displayname='', default_duration=None):
        URISourceFactoryMixin.__init__(self, uri)
        LiveSourceFactory.__init__(self, name, displayname, default_duration)

class FileSourceFactory(URISourceFactoryMixin, RandomAccessSourceFactory):
    """
    Factory for local files.

    @see: L{RandomAccessSourceFactory}.
    """

    def __init__(self, filename, name='', displayname=''):
        name = name or filename
        displayname = displayname or os.path.basename(filename)
        self.filename = filename
        URISourceFactoryMixin.__init__(self, filename)
        RandomAccessSourceFactory.__init__(self, name, displayname)

class PictureFileSourceFactory(FileSourceFactory):
    """
    Factory for image sources.

    @see: L{FileSourceFactory}, L{RandomAccessSourceFactory}.
    """

    duration = 3600 * gst.SECOND

    # make this overridable in tests
    ffscale_factory = 'ffvideoscale'

    def _makeStreamBin(self, output_stream):
        gst.debug("making picture bin for %s" % self.name)
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
        gst.debug("Returning %r" % res)
        
        return res

    def _dbinPadAddedCb(self, unused_dbin, pad, scale, freeze, container):
        pad.link(scale.get_pad("sink"))
        ghost = gst.GhostPad("src", freeze.get_pad("src"))
        ghost.set_active(True)
        container.add_pad(ghost)

    def _dbinPadRemovedCb(self, unused_dbin, pad, scale, freeze, container):
        ghost = container.get_pad("src")
        target = ghost.get_target()
        peer = target.get_peer()
        target.unlink(peer)
        container.remove_pad(ghost)
        pad.unlink(scale.get_pad("sink"))
