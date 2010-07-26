#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       effects.py
#
# Copyright (c) 2010, Thibault Saunier <tsaunier@gnome.org>
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
import gtk
import re
import os

from xml.sax.saxutils import escape
from gettext import gettext as _

from pitivi.factories.operation import EffectFactory
from pitivi.stream import get_stream_for_pad
from pitivi.configure import get_pixmap_dir

from xdg import IconTheme

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

#AspectratioCrop is Blacklisted because of this bug:
#https://bugzilla.gnome.org/show_bug.cgi?id=624882
BLACKLISTED_EFFECTS = ["colorconvert", "coglogoinsert", "festival", "aspectratiocrop"]



class EffectsHandler(object):
    """
    Handles all the effects
    """
    def __init__(self):
        object.__init__(self)
        self._audio_categories_effects = (("All effects", ("")),)
        self._video_categories_effects = (
            (_("All effects"), ("")),
            (_("Colors"), ("cogcolorspace", "alphacolor", "videobalance",
                  "gamma", "alpha", "frei0r-filter-color-distance",
                  "frei0r-filter-contrast0r", "frei0r-filter-invert0r",
                  "frei0r-filter-saturat0r", "frei0r-filter-r",\
                  "frei0r-filter-white-balance", "frei0r-filter-brightness",
                  "frei0r-filter-b", "frei0r-filter-gamma",
                  "frei0r-filter-hueshift0r", "frei0r-filter-transparency",
                  "frei0r-filter-equaliz0r", "frei0r-filter-glow",
                  "frei0r-filter-g", "frei0r-filter-bw0r",
                )
            ),
            (_("Noise"), ("videorate", "frei0r-filter-edgeglow", )),
            (_("Analysis"), ("videoanalyse", "videodetect", "videomark", "revtv",
                             "navigationtest", "frei0r-filter-rgb-parade",
                             "frei0r-filter-vectorscope",
                             "frei0r-filter-luminance",\
                          )),
            (_("Blur"), ("frei0r-filter-squareblur", )),
            (_("Geometry"), ("cogscale", "aspectratiocrop", "cogdownsample",
                  "videocrop", "videoflip", "videobox", "gdkpixbufscale",
                  "frei0r-filter-letterb0xed", "frei0r-filter-k-means-clustering",
                  "videoscale", "frei0r-filter-lens-correction",
                  "frei0r-filter-perspective",
                  "frei0r-filter-scale0tilt", "frei0r-filter-pixeliz0r",\
                  "frei0r-filter-flippo", "frei0r-filter-3dflippo",
                  "frei0r-filter-letterb0xed",
                  )
            ),
            (_("Fancy"),("rippletv", "streaktv", "radioactv", "optv",\
                         "quarktv", "vertigotv", "shagadelictv", "warptv",\
                         "dicetv", "agingtv", "edgetv", "frei0r-filter-cartoon",\
                         "frei0r-filter-water", "frei0r-filter-nosync0r",\
                         "frei0r-filter-k-means-clustering", "frei0r-filter-delay0r",
                     )
            ),
            (_("Time"), ("frei0r-filter-delay0r",)),
            (_("Uncategorized"), ("",))
        )
        self._audio_categories = []
        self._video_categories = []
        self.video_effects = []
        self.audio_effects = []
        self._effect_factories_dict = {}
        self._setAllEffects()

    def _setAllEffects(self):
        """
        go trough the list of element factories and
        add them to the correct list filtering if necessary
        """
        factlist = gst.registry_get_default().get_feature_list(gst.ElementFactory)
        for element_factory in factlist:
            klass = element_factory.get_klass()
            if "Effect" in klass and element_factory.get_name()\
              not in BLACKLISTED_EFFECTS:
                name = element_factory.get_name()
                effect = EffectFactory(name, name,
                                       self._getEffectCategories(name),
                                       self._getEffectName(element_factory),
                                       self._getEffectDescripton(element_factory),
                                       self._getEffectIcon(name))
                added = self.addStreams(element_factory, effect)

                if added is True:
                    if 'Audio' in klass:
                        self.audio_effects.append(element_factory)
                    elif 'Video' in klass:
                        self.video_effects.append(element_factory)
                    self._addEffectToDic(name, effect)

    def getAllAudioEffects(self):
        """
        @returns:  the list off available audio effects elements
        """
        return self.audio_effects

    def getAllVideoEffects(self):
        """
        @returns: the list off available video effects elements
        """
        return self.video_effects

    def _addEffectToDic(self, name, factory):
        self._effect_factories_dict[name]=factory

    def getFactoryFromName(self, name):
        """
        @ivar name: Factory name.
        @type name: C{str}
        @returns: The l{EffectFactory} corresponding to the name
        @raises: KeyError if the name doesn't  exist
        """
        return self._effect_factories_dict.get(name)

    def addStreams(self, element, factory):
        """
        Adds the good streams to the corresponding factory
        """
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

    def _getEffectDescripton(self, element_factory):
        """
        @ivar element_factory: The element factory
        @type element_factory: L{gst.ElementFactory}
        @returns: A human description C{str} for the effect
        """
        return (escape(element_factory.get_description()))

    def _getEffectCategories(self, effect_name):
        """
        @ivar effect_name: the name of the effect for wich we want the category
        @type effect_name: L{str}
        @returns: A C{list} of name C{str} of categories corresponding the effect
        """
        categories = []

        for categorie in self._audio_categories_effects:
            for name in categorie[1]:
                if name == effect_name:
                    categories.append(categorie[0])
                    self._audio_categories.append(categorie[0])

        for categorie in self._video_categories_effects:
            for name in categorie[1]:
                if name == effect_name:
                    categories.append(categorie[0])
                    self._video_categories.append(categorie[0])

        if not categories:
            uncategorized = _("Uncategorized")
            categories.append(uncategorized)
            self._video_categories.append(uncategorized)
            self._audio_categories.append(uncategorized)

        categories.append(self._video_categories_effects[0][0])
        self._audio_categories.append(self._video_categories_effects[0][0])
        self._video_categories.append(self._video_categories_effects[0][0])

        return categories

    def _getEffectName(self, element_factory):
        """
        @ivar element_factory: The element factory
        @type element_factory: L{gst.ElementFactory}
        @returns: A human readable name C{str} for the effect
        """
        #TODO check if it is the good way to make it translatable
        #And to filter actually!
        video = _("Video")
        audio = _("Audio |audio")
        effect = _("effect")
        pipe = " |"
        uselessWords = re.compile(video + pipe + audio + pipe + effect)
        return uselessWords.sub("", (escape(element_factory.get_longname()))).title()

    def getVideoCategories(self, aware=True):
        """
        @ivar  aware: C{True} if you want it to return only categories on whichs
        there are effects on the system, else C{False}
        @type aware: C{bool}
        @returns: All video effect categories names C{str} that are available on
        the system if it has been filled earlier, if it hasen't it will just
        return all categories
        """
        if not self._video_categories or not aware:
            for categorie in self._video_categories_effects:
                self._video_categories.append(categorie[0])
        self._video_categories = list(set(self._video_categories))
        self._video_categories.sort()
        return self._video_categories

    video_categories = property(getVideoCategories)

    def getAudioCategories(self, aware=True):
        """
        @ivar  aware: C{True} if you want it to return only categories on whichs
        there are effects on the system, else C{False}
        @type aware: C{bool}
        @returns: All audio effect categories names C{str}
        """
        if not self._audio_categories or not aware:
            for categorie in self._audio_categories_effects:
                self._audio_categories.append(categorie[0])
        self._audio_categories = list(set(self._audio_categories))
        self._audio_categories.sort()
        return self._audio_categories

    audio_categories = property(getAudioCategories)

    def getAllCategories(self):
        """
        @returns: All effect categories names C{str}
        """
        effects_categories = []
        return effects_categories.extended(self.video_categories).extended(self.audio_categories)

    def _getEffectIcon(self, effect_name):
        #TODO, create icons for effects
        #Shouldn't we use pyxdg to make things cleaner and more optimized?
        icontheme = gtk.icon_theme_get_default()
        pixdir = get_pixmap_dir()
        icon = None
        try:
            icon = icontheme.load_icon(effect_name, 32, 0)
        except:
            # empty except clause is bad but load_icon raises gio.Error.
            ## Right, *gio*.
            if not icon:
                effect_name = effect_name + ".png"
                try:
                    icon = gtk.gdk.pixbuf_new_from_file(os.path.join(pixdir, effect_name))
                except:
                    return None
        return icon
