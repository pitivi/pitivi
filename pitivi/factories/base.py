#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       base.py
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

import os.path
from urllib import unquote
import gst

from pitivi.log.loggable import Loggable
from pitivi.elements.singledecodebin import SingleDecodeBin
from pitivi.signalinterface import Signallable
from pitivi.stream import match_stream_groups_map, AudioStream

# FIXME: define a proper hierarchy
class ObjectFactoryError(Exception):
    pass

class ObjectFactoryStreamError(ObjectFactoryError):
    pass

class ObjectFactory(Signallable, Loggable):
    """
    Base class for all factory implementations.

    Factories are objects that create GStreamer bins to produce, process or
    render streams.

    @ivar name: Factory name.
    @type name: C{str}
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
    @ivar bins: Bins controlled by the factory.
    @type bins: List of C{gst.Bin}
    """

    def __init__(self, name=""):
        Loggable.__init__(self)
        self.info("name:%s", name)
        self.parent = None
        self.name = name
        self.input_streams = []
        self.output_streams = []
        self.duration = gst.CLOCK_TIME_NONE
        self._default_duration = gst.CLOCK_TIME_NONE
        self._icon = None
        self.bins = []

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

    def _addStream(self, stream, stream_list):
        if stream in stream_list:
            raise ObjectFactoryStreamError('stream already added')

        stream_list.append(stream)

    def addInputStream(self, stream):
        """
        Add a stream to the list of inputs the factory can consume.

        @param stream: Stream
        @type stream: Instance of a L{MultimediaStream} derived class
        """
        self._addStream(stream, self.input_streams)

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
        self._addStream(stream, self.output_streams)

    def removeOutputStream(self, stream):
        """
        Remove a stream from the list of inputs the factory can produce.

        @param stream: Stream
        @type stream: Instance of a L{MultimediaStream} derived class
        """
        self.output_streams.remove(stream)

    def getOutputStreams(self, stream_classes=None):
        """
        Return the output streams.

        If specified, only the stream of the provided steam classes will be
        returned.

        @param stream_classes: If specified, the L{MultimediaStream} classes to
        filter with.
        @type stream_classes: one or many L{MultimediaStream} classes
        @return: The output streams.
        @rtype: List of L{MultimediaStream}
        """
        return [stream for stream in self.output_streams
                if stream_classes is None or isinstance(stream, stream_classes)]

    def getInputStreams(self, stream_classes=None):
        """
        Return the input streams.

        If specified, only the stream of the provided steam classes will be
        returned.

        @param stream_classes: If specified, the L{MultimediaStream} classes to
        filter with.
        @type stream_classes: one or many L{MultimediaStream} classes
        @return: The input streams.
        @rtype: List of L{MultimediaStream}
        """
        return [stream for stream in self.input_streams
                if stream_classes is None or isinstance(stream, stream_classes)]

    def clean(self):
        """
        Clean up a factory.

        Some factories allocate resources that have to be cleaned when a factory
        is not needed anymore.
        This should be the last method called on a factory before its disposed.
        """

    def __str__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.name)

    def getInterpolatedProperties(self, stream):
        return {}

class SourceFactory(ObjectFactory):
    """
    Base class for factories that produce output and have no input.

    @ivar max_bins: Max number of bins the factory can create.
    @type max_bins: C{int}
    @ivar current_bins: Number of bin instances created and not released.
    @type current_bins: C{int}
    """

    __signals__ = {
        'bin-created': ['bin'],
        'bin-released': ['bin']
    }

    # make this an attribute to inject it from tests
    singleDecodeBinClass = SingleDecodeBin

    def __init__(self, uri, name=''):
        name = name or os.path.basename(unquote(uri))
        ObjectFactory.__init__(self, name)
        self.uri = uri
        self.max_bins = -1
        self.current_bins = 0

    def makeBin(self, output_stream=None):
        """
        Create a bin that outputs the stream described by C{output_stream}.

        If C{output_stream} is None, it's up to the implementations to return a
        suitable "default" bin.

        @param output_stream: A L{MultimediaStream}
        @return: The bin.
        @rtype: C{gst.Bin}

        @see: L{releaseBin}
        """

        compatible_stream = None
        self.debug("stream %r", output_stream)

        if output_stream is not None:
            self.debug("output_streams:%r", self.output_streams)
            stream_map = match_stream_groups_map([output_stream], self.output_streams)
            if output_stream not in stream_map:
                self.warning("stream not available in map %r", stream_map)
                raise ObjectFactoryError("can not create stream")

            compatible_stream = stream_map[output_stream]

        if self.max_bins != -1 and self.current_bins == self.max_bins:
            raise ObjectFactoryError('no bins available')

        bin = self._makeBin(compatible_stream)
        bin.factory = self
        self.bins.append(bin)
        self.current_bins += 1
        self.emit('bin-created', bin)

        return bin

    def releaseBin(self, bin):
        """
        Release a bin created with L{makeBin}.

        Some factories can create a limited number of bins or implement caching.
        You should call C{releaseBin} once you are done using a bin.
        """
        bin.set_state(gst.STATE_NULL)
        self._releaseBin(bin)
        self.debug("Finally releasing %r", bin)
        self.current_bins -= 1
        self.bins.remove(bin)
        self.emit('bin-released', bin)
        del bin.factory

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

        bin.decodebin = dbin
        return bin

    def _binNewDecodedPadCb(self, unused_dbin, pad, unused_is_last, bin):
        ghost_pad = gst.GhostPad(pad.get_name(), pad)
        ghost_pad.set_active(True)
        bin.add_pad(ghost_pad)

    def _binRemovedDecodedPadCb(self, unused_dbin, pad, bin):
        ghost_pad = bin.get_pad(pad.get_name())
        bin.remove_pad(ghost_pad)

    def _releaseBin(self, bin):
        try:
            # bin is a bin returned from makeDefaultBin
            bin.decodebin.disconnect_by_func(self._binNewDecodedPadCb)
            bin.decodebin.disconnect_by_func(self._binRemovedDecodedPadCb)
        except TypeError:
            # bin is a stream bin
            bin.decodebin.disconnect_by_func(self._singlePadAddedCb)
            bin.decodebin.disconnect_by_func(self._singlePadRemovedCb)

        del bin.decodebin

        if hasattr(bin, "volume"):
            # only audio bins have a volume element
            for elt in [bin.aconv, bin.ares, bin.volume]:
                elt.set_state(gst.STATE_NULL)
                bin.remove(elt)
            del bin.volume
            del bin.aconv
            del bin.ares

        if hasattr(bin, "ghostpad"):
            # singledecodebin found something on this pad
            bin.ghostpad.set_active(False)
            bin.remove_pad(bin.ghostpad)
            del bin.ghostpad

    def _makeStreamBin(self, output_stream):
        self.debug("output_stream:%r", output_stream)
        b = gst.Bin()
        b.decodebin = self.singleDecodeBinClass(uri=self.uri, caps=output_stream.caps,
                                           stream=output_stream)
        b.decodebin.connect("pad-added", self._singlePadAddedCb, b)
        b.decodebin.connect("pad-removed", self._singlePadRemovedCb, b)

        if isinstance(output_stream, AudioStream):
            self.debug("Adding volume element")
            # add a volume element
            b.aconv = gst.element_factory_make("audioconvert", "internal-aconv")
            b.ares = gst.element_factory_make("audioresample", "internal-audioresample")
            b.volume = gst.element_factory_make("volume", "internal-volume")
            b.add(b.volume, b.ares, b.aconv)
            gst.element_link_many(b.aconv, b.ares, b.volume)
            b.aconv.sync_state_with_parent()
            b.ares.sync_state_with_parent()
            b.volume.sync_state_with_parent()

        b.add(b.decodebin)
        return b

    def _singlePadAddedCb(self, dbin, pad, topbin):
        self.debug("dbin:%r, pad:%r, topbin:%r", dbin, pad, topbin)
        if hasattr(topbin, "volume"):
            pad.link(topbin.aconv.get_pad("sink"))
            topbin.ghostpad = gst.GhostPad("src", topbin.volume.get_pad("src"))
        else:
            topbin.ghostpad = gst.GhostPad("src", pad)

        if pad.props.caps is not None:
            topbin.ghostpad.set_caps(pad.props.caps)
        topbin.ghostpad.set_active(True)
        topbin.add_pad(topbin.ghostpad)

    def _singlePadRemovedCb(self, dbin, pad, topbin):
        self.debug("dbin:%r, pad:%r, topbin:%r", dbin, pad, topbin)
        topbin.remove_pad(topbin.ghostpad)
        del topbin.ghostpad
        if hasattr(topbin, "volume"):
            pad.unlink(topbin.aconv.get_pad("sink"))
            for elt in [topbin.volume, topbin.aconv, topbin.ares]:
                elt.set_state(gst.STATE_NULL)
            for elt in [topbin.volume, topbin.aconv, topbin.ares]:
                topbin.remove(elt)
            del topbin.volume
            del topbin.aconv
            del topbin.ares

    def addInputStream(self, stream):
        raise AssertionError("source factories can't have input streams")

class SinkFactory(ObjectFactory):
    """
    Base class for factories that consume input and have no output.

    @ivar max_bins: Max number of bins the factory can create.
    @type max_bins: C{int}
    @ivar current_bins: Number of bin instances created and not released.
    @type current_bins: C{int}
    """

    __signals__ = {
        'bin-created': ['bin'],
        'bin-released': ['bin']
    }

    def __init__(self, name=''):
        ObjectFactory.__init__(self, name)
        self.max_bins = -1
        self.current_bins = 0

    def makeBin(self, input_stream=None):
        """
        Create a bin that consumes the stream described by C{input_stream}.

        If C{input_stream} is None, it's up to the implementations to return a
        suitable "default" bin.

        @param input_stream: A L{MultimediaStream}
        @return: The bin.
        @rtype: C{gst.Bin}

        @see: L{releaseBin}
        """

        self.debug("stream %r", input_stream)
        compatible_stream = None
        if input_stream is not None:
            self.debug("Streams %r", self.input_streams)
            for stream in self.input_streams:
                if input_stream.isCompatible(stream):
                    compatible_stream = stream
                    break

            if compatible_stream is None:
                raise ObjectFactoryError('unknown stream')

        if self.max_bins != -1 and self.current_bins == self.max_bins:
            raise ObjectFactoryError('no bins available')

        bin = self._makeBin(input_stream)
        bin.factory = self
        self.bins.append(bin)
        self.current_bins += 1
        self.emit('bin-created', bin)

        return bin

    def _makeBin(self, input_stream=None):
        raise NotImplementedError()

    def requestNewInputStream(self, bin, input_stream):
        """
        Request a new input stream on a bin.

        @param bin: The C{gst.Bin} on which we request a new stream.
        @param input_stream: The new input C{MultimediaStream} we're requesting.
        @raise ObjectFactoryStreamError: If the L{input_stream} isn't compatible
        with one of the factory's L{input_streams}.
        @return: The pad corresponding to the newly created input stream.
        @rtype: C{gst.Pad}
        """
        if not hasattr(bin, 'factory') or bin.factory != self:
            raise ObjectFactoryError("The provided bin isn't handled by this Factory")
        for ins in self.input_streams:
            if ins.isCompatible(input_stream):
                return self._requestNewInputStream(bin, input_stream)
        raise ObjectFactoryError("Incompatible stream")

    def _requestNewInputStream(self, bin, input_stream):
        raise NotImplementedError

    def releaseBin(self, bin):
        """
        Release a bin created with L{makeBin}.

        Some factories can create a limited number of bins or implement caching.
        You should call C{releaseBin} once you are done using a bin.
        """
        bin.set_state(gst.STATE_NULL)
        self._releaseBin(bin)
        self.bins.remove(bin)
        self.current_bins -= 1
        del bin.factory
        self.emit('bin-released', bin)

    def _releaseBin(self, bin):
        # default implementation does nothing
        pass

    def addOutputStream(self, stream):
        raise AssertionError("sink factories can't have output streams")

class OperationFactory(ObjectFactory):
    """
    Base class for factories that process data (inputs data AND outputs data).
    @ivar max_bins: Max number of bins the factory can create.
    @type max_bins: C{int}
    @ivar current_bins: Number of bin instances created and not released.
    @type current_bins: C{int}
    """

    __signals__ = {
        'bin-created': ['bin'],
        'bin-released': ['bin']
    }

    def __init__(self, name=''):
        ObjectFactory.__init__(self, name)
        self.max_bins = -1
        self.current_bins = 0

    def makeBin(self, input_stream=None, output_stream=None):
        """
        Create a bin that consumes the stream described by C{input_stream}.

        If C{input_stream} and/or C{output_stream} are None, it's up to the
        implementations to return a suitable "default" bin.

        @param input_stream: A L{MultimediaStream}
        @param output_stream: A L{MultimediaStream}
        @return: The bin.
        @rtype: C{gst.Bin}

        @see: L{releaseBin}
        """

        if input_stream is not None and \
                input_stream not in self.input_streams:
            raise ObjectFactoryError('unknown stream')

        bin = self._makeBin(input_stream)
        bin.factory = self
        self.bins.append(bin)
        self.current_bins += 1
        self.emit('bin-created', bin)

        return bin

    def _makeBin(self, input_stream=None, output_stream=None):
        raise NotImplementedError()

    def requestNewInputStream(self, bin, input_stream):
        """
        Request a new input stream on a bin.

        @param bin: The C{gst.Bin} on which we request a new stream.
        @param input_stream: The new input C{MultimediaStream} we're requesting.
        @raise ObjectFactoryStreamError: If the L{input_stream} isn't compatible
        with one of the factory's L{input_streams}.
        @return: The pad corresponding to the newly created input stream.
        @rtype: C{gst.Pad}
        """
        if not hasattr(bin, 'factory') or bin.factory != self:
            raise ObjectFactoryError("The provided bin isn't handled by this Factory")
        for ins in self.input_streams:
            if ins.isCompatible(input_stream):
                return self._requestNewInputStream(bin, input_stream)
        raise ObjectFactoryError("Incompatible stream")

    def _requestNewInputStream(self, bin, input_stream):
        raise NotImplementedError

    def releaseBin(self, bin):
        """
        Release a bin created with L{makeBin}.

        Some factories can create a limited number of bins or implement caching.
        You should call C{releaseBin} once you are done using a bin.
        """
        bin.set_state(gst.STATE_NULL)
        self._releaseBin(bin)
        self.bins.remove(bin)
        self.current_bins -= 1
        del bin.factory
        self.emit('bin-released', bin)

    def _releaseBin(self, bin):
        # default implementation does nothing
        pass


class LiveSourceFactory(SourceFactory):
    """
    Base class for factories that produce live streams.

    The duration of a live source is unknown and it's possibly infinite. The
    default duration is set to 5 seconds to a live source can be managed in a
    timeline.
    """

    def __init__(self, uri, name='', default_duration=None):
        SourceFactory.__init__(self, uri, name)
        if default_duration is None:
            default_duration = 5 * gst.SECOND

        self.default_duration = default_duration

class RandomAccessSourceFactory(SourceFactory):
    """
    Base class for source factories that support random access.

    @ivar offset: Offset in nanoseconds from the beginning of the stream.
    @type offset: C{int}
    @ivar offset_length: Length in nanoseconds.
    @type offset_length: C{int}
    @ivar abs_offset: Absolute offset from the beginning of the stream.
    @type abs_offset: C{int}
    @ivar abs_offset_length: Length in nanoseconds, clamped to avoid overflowing
    the parent's length if any.
    @type abs_offset_length: C{int}
    """

    def __init__(self, uri, name='',
            offset=0, offset_length=gst.CLOCK_TIME_NONE):
        self.offset = offset
        self.offset_length = offset_length

        SourceFactory.__init__(self, uri, name)

    def _getAbsOffset(self):
        if self.parent is None:
            offset = self.offset
        else:
            parent_offset = self.parent.offset
            parent_length = self.parent.offset_length

            offset = min(self.parent.offset + self.offset,
                    self.parent.offset + self.parent.offset_length)

        return offset

    abs_offset = property(_getAbsOffset)

    def _getAbsOffsetLength(self):
        if self.parent is None:
            offset_length = self.offset_length
        else:
            parent_end = self.parent.abs_offset + self.parent.abs_offset_length
            end = self.abs_offset + self.offset_length
            abs_end = min(end, parent_end)
            offset_length = abs_end - self.abs_offset

        return offset_length

    abs_offset_length = property(_getAbsOffsetLength)
