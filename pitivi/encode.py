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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

"""
Encoding-related utilities and classes
"""

import gst
import pitivi.log.log as log


def get_compatible_sink_pad(factoryname, caps):
    """
    Returns the pad name of a (request) pad from factoryname which is
    compatible with the given caps.
    """
    factory = gst.registry_get_default().lookup_feature(factoryname)
    if factory == None:
        log.warning("encode", "%s is not a valid factoryname", factoryname)
        return None

    res = []
    sinkpads = [x for x in factory.get_static_pad_templates() if x.direction == gst.PAD_SINK]
    for p in sinkpads:
        c = p.get_caps()
        log.log("encode", "sinkcaps %s", c.to_string())
        inter = caps.intersect(c)
        log.log("encode", "intersection %s", inter.to_string())
        if inter:
            res.append(p.name_template)
    if len(res) > 0:
        return res[0]
    return None


def get_compatible_sink_caps(factoryname, caps):
    """
    Returns the compatible caps between 'caps' and the sink pad caps of 'factoryname'
    """
    log.log("encode", "factoryname : %s , caps : %s", factoryname, caps.to_string())
    factory = gst.registry_get_default().lookup_feature(factoryname)
    if factory == None:
        log.warning("encode", "%s is not a valid factoryname", factoryname)
        return None

    res = []
    sinkcaps = [x.get_caps() for x in factory.get_static_pad_templates() if x.direction == gst.PAD_SINK]
    for c in sinkcaps:
        log.log("encode", "sinkcaps %s", c.to_string())
        inter = caps.intersect(c)
        log.log("encode", "intersection %s", inter.to_string())
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


def my_can_sink_caps(muxer, ocaps, muxsinkcaps=[]):
    """ returns True if the given caps intersect with some of the muxer's
    sink pad templates' caps.
    """
    # fast version
    if muxsinkcaps != []:
        for c in muxsinkcaps:
            if not c.intersect(ocaps).is_empty():
                return True
        return False
    # slower default
    for x in muxer.get_static_pad_templates():
        if x.direction == gst.PAD_SINK:
            if not x.get_caps().intersect(ocaps).is_empty():
                return True
    return False

    # sinkcaps = (x.get_caps() for x in muxer.get_static_pad_templates() if x.direction == gst.PAD_SINK)
    # for x in sinkcaps:
    #     if not x.intersect(ocaps).is_empty():
    #         return True
    # return False


class CachedEncoderList(object):
    def __init__(self):
        self._factories = None
        self._registry = gst.registry_get_default()
        self._registry.connect("feature-added", self._registryFeatureAddedCb)

    def _ensure_factories(self):
        if self._factories is None:
            self._buildFactories()

    def _buildFactories(self):
        self._factories = self._registry.get_feature_list(gst.ElementFactory)
        self._audioEncoders = []
        self._videoEncoders = []
        self._muxers = []
        for fact in self._factories:
            klist = fact.get_klass().split('/')
            if list_compat(("Codec", "Muxer"), klist):
                self._muxers.append(fact)
            elif list_compat(("Codec", "Encoder", "Video"), klist) or list_compat(("Codec", "Encoder", "Image"), klist):
                self._videoEncoders.append(fact)
            elif list_compat(("Codec", "Encoder", "Audio"), klist):
                self._audioEncoders.append(fact)

    def available_muxers(self):
        if self._factories is None:
            self._buildFactories()
        return self._muxers

    def available_audio_encoders(self):
        if self._factories is None:
            self._buildFactories()
        return self._audioEncoders

    def available_video_encoders(self):
        if self._factories is None:
            self._buildFactories()
        return self._videoEncoders

    def _registryFeatureAddedCb(self, registry, feature):
        self._factories = None

_cached_encoder_list = None


def encoderlist():
    global _cached_encoder_list
    if _cached_encoder_list is None:
        _cached_encoder_list = CachedEncoderList()
    return _cached_encoder_list


def available_muxers():
    """ return all available muxers """
    enclist = encoderlist()
    return enclist.available_muxers()


def available_video_encoders():
    """ returns all available video encoders """
    enclist = encoderlist()
    return enclist.available_video_encoders()


def available_audio_encoders():
    """ returns all available audio encoders """
    enclist = encoderlist()
    return enclist.available_audio_encoders()


def encoders_muxer_compatible(encoders, muxer, muxsinkcaps=[]):
    """ returns the list of encoders compatible with the given muxer """
    res = []
    if muxsinkcaps == []:
        muxsinkcaps = [x.get_caps() for x in muxer.get_static_pad_templates() if x.direction == gst.PAD_SINK]
    for encoder in encoders:
        for tpl in encoder.get_static_pad_templates():
            if tpl.direction == gst.PAD_SRC:
                if my_can_sink_caps(muxer, tpl.get_caps(), muxsinkcaps):
                    res.append(encoder)
                    break
    return res


raw_audio_caps = gst.Caps("audio/x-raw-float;audio/x-raw-int")
raw_video_caps = gst.Caps("video/x-raw-yuv;video/x-raw-rgb")


def muxer_can_sink_raw_audio(muxer):
    """ Returns True if given muxer can accept raw audio """
    return my_can_sink_caps(muxer, raw_audio_caps)


def muxer_can_sink_raw_video(muxer):
    """ Returns True if given muxer can accept raw video """
    return my_can_sink_caps(muxer, raw_video_caps)


def available_combinations():
    """Return a 3-tuple of (muxers, audio, video), where:
        - muxers is a list of muxer factories
        - audio is a dictionary from muxer names to compatible audio encoders
        - video is a dictionary from muxer names to compatible video encoders
    """

    aencoders = available_audio_encoders()
    vencoders = available_video_encoders()
    muxers = available_muxers()

    audio = {}
    video = {}
    containers = []
    for muxer in muxers:
        mux = muxer.get_name()
        aencs = encoders_muxer_compatible(aencoders, muxer)
        vencs = encoders_muxer_compatible(vencoders, muxer)
        # only include muxers with audio and video

        if aencs and vencs:
            audio[mux] = aencs
            video[mux] = vencs
            containers.append(muxer)

    return containers, audio, video
