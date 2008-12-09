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
    
# FIXME: use epydoc/whatever formatting for docstrings
class MultimediaStream(object):
    """
    Defines a media stream

    Properties:
    * raw (boolean) : True if the stream is a raw media format
    * fixed (boolean) : True if the stream is entirely defined
    * caps (gst.Caps) : Caps corresponding to the stream

    """
    
    def __init__(self, caps):
        gst.log("new with caps %s" % caps.to_string())
        self.caps = caps
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
    """

    def __init__(self, caps):
        self.width = None
        self.height = None
        self.framerate = None
        self.format = None

        MultimediaStream.__init__(self, caps)

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
    """
    def __init__(self, caps):
        # initialize properties here for clarity
        self.audiotype = None
        self.channels = None
        self.rate = None
        self.width = None
        self.height = None
        self.depth = None
        
        MultimediaStream.__init__(self, caps)

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

def get_stream_for_caps(caps):
    """
    Returns the appropriate MediaStream corresponding to the
    given caps.
    """
    # FIXME : we should have an 'unknown' data stream class
    ret = None

    val = caps.to_string()
    if val.startswith("video/"):
        ret = VideoStream(caps)
    elif val.startswith("audio/"):
        ret = AudioStream(caps)
    elif val.startswith("text/"):
        ret = TextStream(caps)
    return ret
