#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       effects.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
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
Effects global handling
"""

import gst
import re

from xml.sax.saxutils import escape

from pitivi.factories.operation import EffectFactory
from pitivi.stream import get_stream_for_pad

# Note: Some effects are available through the frei0r library and the libavfilter0 library

# There are different types of effects available:
#  _ Simple Audio/Video Effects
#     GStreamer elements that only apply to audio OR video
#     Only take the elements who have a straightforward meaning/action
#  _ Expanded Audio/Video Effects
#     These are the Gstreamer elements that don't have a easy meaning/action or
#     that are too cumbersome to use as such
#  _ Complex Audio/Video Effects

(VIDEO_EFFECT, AUDIO_EFFECT)  = range(2)
USELESS_EFFECTS = ["colorconvert", "coglogoinsert", "festival",]


video_categories = (
    ("All video effects", ("")),
    ("Colors", ("cogcolorspace", "alphacolor", "videobalance", "gamma", "alpha",\
                "frei0r-filter-color-distance", "frei0r-filter-contrast0r", \
                "frei0r-filter-invert0r", "frei0r-filter-saturat0r", "frei0r-filter-r",\
                "frei0r-filter-white-balance", "frei0r-filter-brightness", "frei0r-filter-b",\
                "frei0r-filter-gamma", "frei0r-filter-hueshift0r", "frei0r-filter-transparency",\
                "frei0r-filter-equaliz0r", "frei0r-filter-glow ", "frei0r-filter-g", "frei0r-filter-bw0r"\
                )
    ),
    ("Noise", ("videorate", "frei0r-filter-edgeglow" )),
    ("Analysis", ("videoanalyse", "videodetect", "videomark", "revtv", "navigationtest",\
                  "frei0r-filter-rgb-parade", "frei0r-filter-vectorscope", "frei0r-filter-luminance",\
                  )),
    ("Blur", ("frei0r-filter-squareblur", )),
    ("Geometry", ("cogscale", "aspectratiocrop", "cogdownsample", "videocrop", "videoflip",\
                  "videobox", "gdkpixbufscale", "frei0r-filter-letterb0xed" \
                  "frei0r-filter-k-means-clustering", "videoscale", "frei0r-filter-lens-correction",
                  "frei0r-filter-perspective", "frei0r-filter-scale0tilt", "frei0r-filter-pixeliz0r",\
                  "frei0r-filter-flippo", "frei0r-filter-3dflippo"
                 )
    ),
    ("Fancy",("rippletv", "streaktv", "radioactv", "optv", "quarktv", "vertigotv",\
              "shagadelictv", "warptv", "dicetv", "agingtv", "edgetv", "frei0r-filter-cartoon",\
              "frei0r-filter-water", "frei0r-filter-nosync0r"
             )
    ),
    ("Time", ("frei0r-filter-delay0r")),
    ("Uncategorized", (""))
)

audio_categories = (("All audio effects", ("")),)

def get_categories(effect, effectType):

    effectName = effect.get_name()
    categories = []

    if effectType is AUDIO_EFFECT:
        categories.append(audio_categories[0][0])
        for categorie in audio_categories:
            for name in categorie[1]:
                if name == effectName:
                    categories.append(categorie[0])
        return categories

    for categorie in video_categories:
        for name in categorie[1]:
            if name == effectName:
                categories.append(categorie[0])

    if categories == []:
        categories.append("Uncategorized")

    categories.append(video_categories[0][0])

    return categories

#Convenience function for better effect properties lisibility
def getNiceEffectName(effect):
    uselessWords = re.compile('(Video |effect |Audio )')
    return uselessWords.sub("", (escape(effect.get_longname()))).title()

def getNiceEffectDescription(effect):
    return (escape(effect.get_description()))

class Magician:
    """
    Handles all the effects
    """

    def __init__(self):
        self.simple_video = []
        self.simple_audio = []
        self.effect_factories_dict = {}
        self.transitions = []
        self._getAllEffects()

    def _getAllEffects(self):
        # go trough the list of element factories and
        # add them to the correct list filtering if necessary
        factlist = gst.registry_get_default().get_feature_list(gst.ElementFactory)
        for element_factory in factlist:
            klass = element_factory.get_klass()
            if "Effect" in klass and element_factory.get_name() not in USELESS_EFFECTS:
                factory = EffectFactory(element_factory.get_name(), element_factory.get_name())
                added = self.addStreams(element_factory, factory)
                if added is True:
                    if 'Audio' in klass:
                        self.simple_audio.append(element_factory)
                    elif 'Video' in klass:
                        self.simple_video.append(element_factory)
                    self.addFactory(element_factory.get_name(), factory)

    def addFactory(self, name, factory):
        self.effect_factories_dict[name]=factory

    def getFactory(self, name):
        return self.effect_factories_dict.get(name)

    def getElementFromFactoryName(self, name, effectType):
        if effectType == VIDEO_EFFECT:
            for element_factory in self.simple_video:
                if element_factory.get_name() == name:
                    return element_factory
        elif effectType == AUDIO_EFFECT:
            for element_factory in self.simple_audio:
                if element_factory.get_name() == name:
                    return element_factory

    def addStreams(self, element, factory):
        pads = element.get_static_pad_templates()

        if not factory:
            return False

        for padTmp in pads:
            pad = gst.Pad (padTmp.get())
            if pad.get_caps() == "ANY": #FIXME
                return False

            if padTmp.direction == gst.PAD_SRC:
                stream = get_stream_for_pad(pad)
                factory.addInputStream(stream)
            elif padTmp.direction == gst.PAD_SINK:
                stream = get_stream_for_pad(pad)
                factory.addOutputStream(stream)
        return True
