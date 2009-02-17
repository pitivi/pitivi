# PiTiVi , Non-linear video editor
#
#       pitivi/encode.py
#
# Copyright (c) 2009, Edward Hervey <bilboed@bilboed.com>
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
Encoding-related utilities and classes
"""

import gst

class RenderFactory(OperationFactory):
    """
    Handles factories that consume streams and output one (and only one
    output stream according to the given encoding settings.
    """

    def __init__(self, settings=None, *args, **kwargs):
        self.settings = settings

    def _makeBin(self, input_stream=None, output_stream=None):
        # create encoding bin for provided stream
        raise NotImplementedError

def get_compatible_sink_caps(factoryname, caps):
    """
    Returns the compatible caps between 'caps' and the sink pad caps of 'factoryname'
    """
    gst.log("factoryname : %s , caps : %s" % (factoryname, caps.to_string()))
    factory = gst.registry_get_default().lookup_feature(factoryname)
    if factory == None:
        gst.warning("%s is not a valid factoryname" % factoryname)
        return None

    res = []
    sinkcaps = [x.get_caps() for x in factory.get_static_pad_templates() if x.direction == gst.PAD_SINK]
    for c in sinkcaps:
        gst.log("sinkcaps %s" % c.to_string())
        inter = caps.intersect(c)
        gst.log("intersection %s" % inter.to_string())
        if inter:
            res.append(inter)

    if len(res) > 0:
        return res[0]
    return None

def list_compat(a1, b1):
    for x1 in a1:
        if not x1 in b1:
            return False
    return True

def my_can_sink_caps(muxer, ocaps):
    """ returns True if the given caps intersect with some of the muxer's
    sink pad templates' caps.
    """
    sinkcaps = [x.get_caps() for x in muxer.get_static_pad_templates() if x.direction == gst.PAD_SINK]
    for x in sinkcaps:
        if not x.intersect(ocaps).is_empty():
            return True
    return False

def available_muxers():
    """ return all available muxers """
    flist = gst.registry_get_default().get_feature_list(gst.ElementFactory)
    res = []
    for fact in flist:
        if list_compat(["Codec", "Muxer"], fact.get_klass().split('/')):
            res.append(fact)
    gst.log(str(res))
    return res

def available_video_encoders():
    """ returns all available video encoders """
    flist = gst.registry_get_default().get_feature_list(gst.ElementFactory)
    res = []
    for fact in flist:
        if list_compat(["Codec", "Encoder", "Video"], fact.get_klass().split('/')):
            res.append(fact)
        elif list_compat(["Codec", "Encoder", "Image"], fact.get_klass().split('/')):
            res.append(fact)
    gst.log(str(res))
    return res

def available_audio_encoders():
    """ returns all available audio encoders """
    flist = gst.registry_get_default().get_feature_list(gst.ElementFactory)
    res = []
    for fact in flist:
        if list_compat(["Codec", "Encoder", "Audio"], fact.get_klass().split('/')):
            res.append(fact)
    gst.log(str(res))
    return res

def encoders_muxer_compatible(encoders, muxer):
    """ returns the list of encoders compatible with the given muxer """
    res = []
    for encoder in encoders:
        for caps in [x.get_caps() for x in encoder.get_static_pad_templates() if x.direction == gst.PAD_SRC]:
            if my_can_sink_caps(muxer, caps):
                res.append(encoder)
                break
    return res

def muxer_can_sink_raw_audio(muxer):
    """ Returns True if given muxer can accept raw audio """
    return my_can_sink_caps(muxer, gst.Caps("audio/x-raw-float;audio/x-raw-int"))

def muxer_can_sink_raw_video(muxer):
    """ Returns True if given muxer can accept raw video """
    return my_can_sink_caps(muxer, gst.Caps("video/x-raw-yuv;video/x-raw-rgb"))

def available_combinations(muxers, vencoders, aencoders):
    res = []
    for mux in muxers:
        noaudio = (encoders_muxer_compatible(aencoders, mux) == []) and not muxer_can_sink_raw_audio(mux)
        novideo = (encoders_muxer_compatible(vencoders, mux) == []) and not muxer_can_sink_raw_video(mux)
        if (noaudio == False) and (novideo == False):
            res.append(mux)
    return res
