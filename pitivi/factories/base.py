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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

import os.path
from urllib import unquote
import gst

from pitivi.log.loggable import Loggable
from pitivi.signalinterface import Signallable
from pitivi.utils import formatPercent

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
