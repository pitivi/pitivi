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
from pitivi.factories.operation import EffectFactory
from pitivi.stream import get_stream_for_pad

# There are different types of effects available:
#  _ Simple Audio/Video Effects
#     GStreamer elements that only apply to audio OR video
#     Only take the elements who have a straightforward meaning/action
#  _ Expanded Audio/Video Effects
#     These are the Gstreamer elements that don't have a easy meaning/action or
#     that are too cumbersome to use as such
#  _ Complex Audio/Video Effects

class Magician:
    """
    Handles all the effects
    """

    def __init__(self):
        self.simple_video = []
        self.simple_audio = []
        self.effect_factories_dict = {}
        self.transitions = []
        self._getSimpleFilters()
        self._getEffectPlugins()

    def _getSimpleFilters(self):
        # go trough the list of element factories and
        # add them to the correct list
        factlist = gst.registry_get_default().get_feature_list(gst.ElementFactory)
        for fact in factlist:
            klass = fact.get_klass()
            if "Effect" in klass:
                factory = EffectFactory(fact.get_name(), fact.get_name())
                added = self.addStreams(fact, factory)
                if added is True:
                    if 'Audio' in klass:
                        self.simple_audio.append(fact)
                    elif 'Video' in klass:
                        self.simple_video.append(fact)
                    self.addFactory(fact.get_name(), factory)


    def _getEffectPlugins(self):
        # find all the pitivi plugins that provide effects
        # TODO : implement
        pass

    def addFactory(self, name, factory):
        self.effect_factories_dict[name]=factory

    def getFactory(self, name):
        return self.effect_factories_dict.get(name)

    def addStreams(self, element, factory):
        pads = element.get_static_pad_templates()

        if not factory:
            return False

        for padTmp in pads:
            pad = gst.Pad (padTmp.get())
            if pad.get_caps() == "ANY": #FIXME, I don't understand that!
                return False

            if padTmp.direction == gst.PAD_SRC:
                stream = get_stream_for_pad(pad)
                factory.addInputStream(stream)
            elif padTmp.direction == gst.PAD_SINK:
                stream = get_stream_for_pad(pad)
                factory.addOutputStream(stream)

        return True
