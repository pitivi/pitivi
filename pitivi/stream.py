# PiTiVi , Non-linear video editor
#
#       pitivi/stream.py
#
# Copyright (c) 2008, Edward Hervey <bilboed@bilboed.com>
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
Multimedia stream, used for definition of media streams
"""

from pitivi.log.loggable import Loggable
import pitivi.log.log as log
import gst

class MultimediaStream(Loggable):
    """
    Defines a media stream

    @cvar raw: The stream is a raw media format.
    @type raw: C{bool}
    @cvar fixed: The stream is entirely defined.
    @type fixed: C{bool}
    @cvar caps: The caps corresponding to the stream
    @type caps: C{gst.Caps}
    @cvar pad_name: The name of the pad from which this stream originated.
    @type pad_name: C{str}
    """

    def __init__(self, caps, pad_name=None):
        Loggable.__init__(self)
        self.caps = caps
        self.pad_name = pad_name
        self.fixed = caps.is_fixed()
        self.raw = None
        self._analyzeCaps()
        self.log("new with caps %s" % self.caps.to_string())

    def _analyzeCaps(self):
        """
        Override to extract properties from caps.
        """
        # NOTE: current implementations only parse the first structure. It could
        # be a bit limited but on the other hand, Streams are just a thin layer
        # on top of caps. For more complex things caps should be used.

    def isCompatible(self, other):
        """
        Checks whether the stream is compatible with the other streams.

        That means they have compatible caps

        @param other: another stream
        @type other: L{MultimediaStream}
        @return: C{True} if the stream is compatible.
        @rtype: C{bool}
        """
        return not self.caps.intersect(other.caps).is_empty()

    def isCompatibleWithName(self, other):
        """
        Checks whether the stream is compatible with the other streams caps
        and pad name.

        @param other: another stream
        @type other: L{MultimediaStream}
        @return: C{True} if the stream is compatible.
        @rtype: C{bool}
        """
        #if self.pad_name and other.pad_name:
        self.log("self.pad_name:%r, other.pad_name:%r",
                 self.pad_name, other.pad_name)
        return self.pad_name == other.pad_name and self.isCompatible(other)
        #return self.isCompatible(other)

    def __repr__(self):
        return "<%s(%s) '%s'>" % (self.__class__.__name__,
                                  self.pad_name, self.caps.to_string()[:30])

    def __str__(self):
        return "%s" % self.caps

class VideoStream(MultimediaStream):
    """
    Video Stream

    @cvar width: Width of the video in pixels.
    @type width: C{int}
    @cvar height: Height of the video in pixels.
    @type height: C{int}
    @cvar framerate: Framerate of the video.
    @type framerate: C{gst.Fraction}
    @cvar format: The subtype of video type
    @cvar par: The pixel-aspect-ratio of the video stream.
    @type par: C{gst.Fraction}
    @cvar dar: The display-aspect-ratio of the video stream.
    @type dar: C{gst.Fraction}
    @cvar is_image: If the stream is an image.
    @type is_image: C{bool}
    @cvar thumbnail: The thumbnail associated with this stream
    """

    def __init__(self, caps, pad_name=None, is_image=False):
        self.width = None
        self.height = None
        self.framerate = gst.Fraction(1, 1)
        self.format = None
        self.is_image = is_image
        self.thumbnail = None
        self.par = gst.Fraction(1, 1)
        self.dar = gst.Fraction(4, 3)

        MultimediaStream.__init__(self, caps, pad_name)

    def _analyzeCaps(self):
        if len(self.caps) == 0:
            # FIXME: rendering still images triggers this as we aren't using
            # decodebin2 and caps are still not negotiated when this happens. We
            # should fix this, but for the moment just returning makes rendering
            # work
            self.error("can't analyze %s", self.caps)
            return

        struct = self.caps[0]
        self.videotype = struct.get_name()
        self.raw = self.videotype.startswith("video/x-raw-")

        for property_name in ('width', 'height', 'framerate', 'format'):
            try:
                setattr(self, property_name, struct[property_name])
            except KeyError:
                # property not in caps
                pass

        try:
            self.par = struct['pixel-aspect-ratio']
        except KeyError:
            pass

        # compute display aspect ratio
        try:
            if self.width and self.height and self.par:
                self.dar = gst.Fraction(self.width * self.par.num,
                                        self.height * self.par.denom)
            elif self.width and self.height:
                self.dar = gst.Fraction(self.width, self.height)
        except:
            self.dar = gst.Fraction(4, 3)

class AudioStream(MultimediaStream):
    """
    Audio stream

    @cvar audiotype: Type of the audio stream (Ex: audio/x-raw-int)
    @type audiotype: C{str}
    @cvar channels: The number of channels handled by this Stream
    @type channels: C{int}
    @cvar rate: The sample rate
    @type rate: C{int}
    @cvar width: The number of bits taken by an individual sample.
    @type width: C{int}
    @cvar depth: The number of useful bits used by an individual sample.
    @type depth: C{int}
    """
    def __init__(self, caps, pad_name=None):
        # initialize properties here for clarity
        self.audiotype = None
        self.channels = None
        self.rate = None
        self.width = None
        self.depth = None

        MultimediaStream.__init__(self, caps, pad_name)

    def _analyzeCaps(self):
        struct = self.caps[0]
        self.audiotype = struct.get_name()
        self.raw = self.audiotype.startswith('audio/x-raw-')

        for property_name in ('channels', 'rate', 'width', 'height', 'depth'):
            try:
                setattr(self, property_name, struct[property_name])
            except KeyError:
                # property not in the caps
                pass

        if self.width and not self.depth:
            self.depth = self.width

class TextStream(MultimediaStream):
    """
    Text media stream
    """

    def _analyzeCaps(self):
        self.texttype = self.caps[0].get_name()

def find_decoder(pad):
    decoder = None
    while pad is not None:
        if pad.props.direction == gst.PAD_SINK:
            pad = pad.get_peer()
            continue

        if isinstance(pad, gst.GhostPad):
            pad = pad.get_target()
            continue

        element = pad.get_parent()
        if element is None or isinstance(element, gst.Bin):
            return None

        factory = element.get_factory()
        if factory is not None and ('Decoder' in factory.get_klass() or \
                'Codec/Demuxer/Audio' == factory.get_klass()):
            decoder = element
            break

        pad = element.get_pad('sink')

    return decoder

def find_upstream_demuxer_and_pad(pad):
    while pad:
        if pad.props.direction == gst.PAD_SRC \
                and isinstance(pad, gst.GhostPad):
            pad = pad.get_target()
            continue

        if pad.props.direction == gst.PAD_SINK:
            pad = pad.get_peer()
            continue

        element = pad.get_parent()
        if isinstance(element, gst.Pad):
            # pad is a proxy pad
            element = element.get_parent()

        if element is None:
            pad = None
            continue

        element_factory = element.get_factory()
        element_klass = element_factory.get_klass()

        if 'Demuxer' in element_klass:
            return element, pad

        sink_pads = list(element.sink_pads())
        if len(sink_pads) > 1:
            if element_factory.get_name() == 'multiqueue':
                pad = element.get_pad(pad.get_name().replace('src', 'sink'))
            else:
                raise Exception('boom!')

        elif len(sink_pads) == 0:
            pad = None
        else:
            pad = sink_pads[0]

    return None, None

def get_type_from_decoder(decoder):
    log.debug("stream","%r" % decoder)
    klass = decoder.get_factory().get_klass()
    parts = klass.split('/', 2)
    if len(parts) != 3:
        return None

    return parts[2].lower()

def get_pad_type(pad):
    decoder = find_decoder(pad)
    if decoder:
        return get_type_from_decoder(decoder)

    return pad.get_caps()[0].get_name().split('/', 1)[0]

def get_pad_id(pad):
    lst = []
    while pad:
        demuxer, pad = find_upstream_demuxer_and_pad(pad)
        if (demuxer, pad) != (None, None):
            lst.append([demuxer.get_factory().get_name(), pad.get_name()])

            # FIXME: we always follow back the first sink
            try:
                pad = list(demuxer.sink_pads())[0]
            except IndexError:
                pad = None

    return lst

def get_stream_for_caps(caps, pad=None):
    """
    Returns the appropriate MediaStream corresponding to the
    given caps.
    """
    log.debug("stream","caps:%s, pad:%r" % (caps.to_string(), pad))
    # FIXME : we should have an 'unknown' data stream class
    ret = None

    if pad is not None:
        pad_name = pad.get_name()
        stream_type = get_pad_type(pad)
    else:
        pad_name = None
        stream_type = caps[0].get_name().split('/', 1)[0]

    log.debug("stream","stream_type:%s" % stream_type)
    if stream_type in ('video', 'image'):
        ret = VideoStream(caps, pad_name, stream_type == 'image')
    elif stream_type == 'audio':
        ret = AudioStream(caps, pad_name)
    elif stream_type == 'text':
        ret = TextStream(caps, pad_name)
    return ret

def get_stream_for_pad(pad):
    caps = pad.props.caps
    if caps is None:
        caps = pad.get_caps()
    pad_id = get_pad_id(pad)
    stream = get_stream_for_caps(caps, pad)
    stream.pad_id = pad_id

    return stream

def pad_compatible_stream(pad, stream):
    """
    Checks whether the given pad is compatible with the given stream.

    @param pad: The pad
    @type pad: C{gst.Pad}
    @param stream: The stream to match against.
    @type stream: L{MultimediaStream}
    @return: Whether the pad is compatible with the given stream
    @rtype: C{bool}
    """
    log.debug("stream","pad:%r, stream:%r" % (pad, stream))
    if stream == None:
        # yes, None is the magical stream that takes everything
        return True
    # compatible caps
    if stream.caps:
        return not stream.caps.intersect(pad.get_caps()).is_empty()
    raise Exception("Can't figure out compatibility since the stream doesn't have any caps")

def get_pads_for_stream(element, stream):
    """
    Fetches the pads of the given element which are compatible with the given
    stream.

    @param element: The element to search on.
    @type element: C{gst.Element}
    @param stream: The stream to match against.
    @type stream: L{MultimediaStream}
    @return: The compatible pads
    @rtype: List of C{gst.Pad}
    """
    log.debug("stream","element:%r, stream:%r" % (element, stream))
    while True:
        try:
            ls = [x for x in element.pads() if pad_compatible_stream(x, stream)]
            break
        except:
            continue
    # FIXME : I'm not 100% certain that checking against the stream pad_name
    # is a good idea ....
    # only filter the list if there's more than one choice
    if stream and len(ls) > 1 and stream.pad_name:
        return [x for x in ls if x.get_name() == stream.pad_name]
    return ls

def get_src_pads_for_stream(element, stream):
    """
    Fetches the source pads of the given element which are compatible with the
    given stream.

    @param element: The element to search on.
    @type element: C{gst.Element}
    @param stream: The stream to match against.
    @type stream: L{MultimediaStream}
    @return: The compatible source pads
    @rtype: List of C{gst.Pad}
    """
    return [x for x in get_pads_for_stream(element, stream) if x.get_direction() == gst.PAD_SRC]

def get_sink_pads_for_stream(element, stream):
    """
    Fetches the sink pads of the given element which are compatible with the
    given stream.

    @param element: The element to search on.
    @type element: C{gst.Element}
    @param stream: The stream to match against.
    @type stream: L{MultimediaStream}
    @return: The compatible sink pads
    @rtype: List of C{gst.Pad}
    """
    return [x for x in get_pads_for_stream(element, stream) if x.get_direction() == gst.PAD_SINK]
