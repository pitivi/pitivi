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


##
## Multimedia streams, used for definition of media streams
##
from gettext import gettext as _

import gst

class MultimediaStream(object):
    """
    Defines a media stream

    Properties:
    * raw (boolean) : True if the stream is a raw media format
    * fixed (boolean) : True if the stream is entirely defined
    * codec (string) : User-friendly description of the codec used
    * caps (gst.Caps) : Caps corresponding to the stream
    """

    def __init__(self, caps):
        gst.log("new with caps %s" % caps.to_string())
        self._caps = caps
        self._raw = False
        if len(self._caps) > 1:
            self._fixed = False
        else:
            self._fixed = True
        self._codec = None
        self._analyzeCaps()

    ## read-only properties
    def _get_caps(self):
        return self._caps
    caps = property(_get_caps,
                    doc="Original gst.Caps")

    def _get_raw(self):
        return self._raw
    raw = property(_get_raw,
                   doc="True if the stream is a raw stream")

    def _get_fixed(self):
        return self._fixed
    fixed = property(_get_fixed,
                     doc="True if the stream has fixed caps")


    def _get_codec(self):
        return self._codec

    def _set_codec(self, codecstring=None):
        if codecstring and codecstring.strip():
            self._codec = codecstring.strip()
    codec = property(_get_codec, _set_codec,
                     doc="Codec used in the stream")

    @property
    def markup(self):
        """Pango-markup string definition"""
        return self._getMarkup()

    def _analyzeCaps(self):
        raise NotImplementedError

    def _getMarkup(self):
        """
        Returns a pango-markup string definition of the stream
        Subclasses need to implement this
        """
        raise NotImplementedError

    def __repr__(self):
        return "%s" % self.caps

class VideoStream(MultimediaStream):
    """
    Video Stream
    """

    # read-only properties
    @property
    def format(self):
        """YUV format of the raw video stream"""
        return self._format

    @property
    def width(self):
        """Width of the video stream in pixels"""
        return self._width

    @property
    def height(self):
        """Height of the video stream in pixels"""
        return self._height

    @property
    def framerate(self):
        """Framerate"""
        return self._framerate

    @property
    def par(self):
        """Pixel Aspect Ratio in fraction"""
        return self._par

    @property
    def dar(self):
        """Display Aspect Ratio in fraction"""
        return self._dar

    def _analyzeCaps(self):
        # WARNING/FIXME : Only analyses first structure !
        struct = self.caps[0]
        self.videotype = struct.get_name()
        if self.videotype.startswith("video/x-raw-"):
            self._raw = True
        else:
            self._raw = False

        try:
            self._format = struct["format"]
        except:
            self._format = None
        try:
            self._width = struct["width"]
        except:
            self._width = None
        try:
            self._height = struct["height"]
        except:
            self._height = None
        try:
            self._framerate = struct["framerate"]
        except:
            # if no framerate was given, use 1fps
            self._framerate = gst.Fraction(1, 1)
        try:
            self._par = struct["pixel-aspect-ratio"]
        except:
            # use a default setting, None is not valid !
            self._par = gst.Fraction(1, 1)

        if self.width and self.height and self.par:
            self._dar = gst.Fraction(self.width * self.par.num, self.height * self.par.denom)
        else:
            if self.width and self.height:
                self._dar = gst.Fraction(self.width, self.height)
            else:
                self._dar = gst.Fraction(4, 3)

    def _getMarkup(self):
        if self._raw:
            if self._framerate.num:
                templ = _("<b>Video:</b> %d x %d <i>pixels</i> at %.2f<i>fps</i>")
                templ = templ % (self.dar * self.height , self.height, float(self.framerate))
            else:
                templ = _("<b>Image:</b> %d x %d <i>pixels</i>")
                templ = templ % (self.dar * self.height, self.height)
            if self._codec:
                templ = templ + _(" <i>(%s)</i>") % self.codec
            return templ
        return _("<b>Unknown Video format:</b> %s") % self.videotype

class AudioStream(MultimediaStream):
    """
    Audio stream
    """

    @property
    def float(self):
        """True if the audio stream contains raw float data"""
        return self._float

    @property
    def channels(self):
        """Number of channels"""
        return self._channels

    @property
    def rate(self):
        """Rate in samples/seconds"""
        return self._rate

    @property
    def width(self):
        """Width of an individual sample (in bits)"""
        return self._width

    @property
    def depth(self):
        """Depth of an individual sample (in bits)"""
        return self._depth

    def _analyzeCaps(self):
        # WARNING/FIXME : Only analyses first structure !
        struct = self.caps[0]
        self.audiotype = struct.get_name()
        if self.audiotype.startswith("audio/x-raw-"):
            self._raw = True
        else:
            self._raw = False

        if self.audiotype == "audio/x-raw-float":
            self._float = True
        else:
            self._float = False

        try:
            self._channels = struct["channels"]
        except:
            self._channels = None
        try:
            self._rate = struct["rate"]
        except:
            self._rate = None
        try:
            self._width = struct["width"]
        except:
            self._width = None
        try:
            self._depth = struct["depth"]
        except:
            self._depth = self.width

    def _getMarkup(self):
        if self.raw:
            templ = _("<b>Audio:</b> %d channels at %d <i>Hz</i> (%d <i>bits</i>)")
            templ = templ % (self.channels, self.rate, self.width)
            if self.codec:
                templ = templ + _(" <i>(%s)</i>") % self.codec
            return templ
        return _("<b>Unknown Audio format:</b> %s") % self.audiotype

class TextStream(MultimediaStream):
    """
    Text media stream
    """

    def _analyzeCaps(self):
        self.texttype = self.caps[0].get_name()

    def _getMarkup(self):
        return _("<b>Text:</b> %s") % self.texttype

def get_stream_for_caps(caps):
    """
    Returns the appropriate MediaStream corresponding to the
    given caps.
    """
    # FIXME : we should have an 'unknow' data stream class
    ret = None

    val = caps.to_string()
    if val.startswith("video/"):
        ret = VideoStream(caps)
    elif val.startswith("audio/"):
        ret = AudioStream(caps)
    elif val.startswith("text/"):
        ret = TextStream(caps)
    return ret
