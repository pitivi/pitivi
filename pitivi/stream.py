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

from gettext import gettext as _
import gst

class MultimediaStream(object):
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
        gst.log("new with caps %s" % caps.to_string())
        self.caps = caps
        self.pad_name = pad_name
        self.fixed = caps.is_fixed()
        self.raw = None

        self._analyzeCaps()

    def _analyzeCaps(self):
        """
        Override to extract properties from caps.
        """
        # NOTE: current implementations only parse the first structure. It could
        # be a bit limited but on the other hand, Streams are just a thin layer
        # on top of caps. For more complex things caps should be used.

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
    @cvar is_image: If the stream is an image.
    @type is_image: C{bool}
    @cvar thumbnail: The thumbnail associated with this stream
    """

    def __init__(self, caps, pad_name=None, is_image=False):
        self.width = None
        self.height = None
        self.framerate = None
        self.format = None
        self.is_image = is_image
        self.thumbnail = None

        MultimediaStream.__init__(self, caps, pad_name)

    def _analyzeCaps(self):
        struct = self.caps[0]
        self.videotype = struct.get_name()
        self.raw = self.videotype.startswith("video/x-raw-")

        for property_name in ('width', 'height', 'framerate', 'format'):
            try:
                setattr(self, property_name, struct[property_name])
            except KeyError:
                # property not in caps
                pass

        if self.framerate is None:
            self.framerate = gst.Fraction(1, 1)

        try:
            self.par = struct['pixel-aspect-ratio']
        except:
            self.par = gst.Fraction(1, 1)

        # compute display aspect ratio
        if self.width and self.height and self.par:
            self.dar = gst.Fraction(self.width * self.par.num,
                    self.height * self.par.denom)
        elif self.width and self.height:
            self.dar = gst.Fraction(self.width, self.height)
        else:
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
        # FIXME : height ?????
        self.height = None
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

    def _getMarkup(self):
        return _("<b>Text:</b> %s") % self.texttype

def find_decoder(pad):
    if isinstance(pad, gst.GhostPad):
        target = pad.get_target()
    else:
        target = pad
    element = target.get_parent()
    if element is None:
        return None

    klass = element.get_factory().get_klass()
    if 'Decoder' in klass:
        return element
    return None

def get_type_from_decoder(decoder):
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

def get_stream_for_caps(caps, pad=None):
    """
    Returns the appropriate MediaStream corresponding to the
    given caps.
    """
    # FIXME : we should have an 'unknown' data stream class
    ret = None

    if pad is not None:
        pad_name = pad.get_name()
        stream_type = get_pad_type(pad)
    else:
        val = caps.to_string()
        stream_type = pad.get_caps()[0].get_name().spit('/', 1)[0]

    if stream_type in ('video', 'image'):
        ret = VideoStream(caps, pad_name, stream_type == 'image')
    elif stream_type == 'audio':
        ret = AudioStream(caps, pad_name)
    elif stream_type == 'text':
        ret = TextStream(caps, pad_name)
    return ret

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
    ls = [x for x in element.pads() if pad_compatible_stream(x, stream)]
    # FIXME : I'm not 100% certain that checking against the stream pad_name
    # is a good idea ....
    if stream.pad_name:
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
    return [x for x in get_pads_for_stream(element,stream) if x.get_direction() == gst.PAD_SRC]

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
    return [x for x in get_pads_for_stream(element,stream) if x.get_direction() == gst.PAD_SINK]
