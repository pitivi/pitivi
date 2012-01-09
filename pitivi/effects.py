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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

"""
Effects global handling
"""
import gst
import gtk
import re
import os

from gettext import gettext as _

from pitivi.configure import get_pixmap_dir

# Note: Some effects are available through the frei0r
# library and the libavfilter0 library

# There are different types of effects available:
#  _ Simple Audio/Video Effects
#     GStreamer elements that only apply to audio OR video
#     Only take the elements who have a straightforward meaning/action
#  _ Expanded Audio/Video Effects
#     These are the Gstreamer elements that don't have a easy meaning/action or
#     that are too cumbersome to use as such
#  _ Complex Audio/Video Effects

(VIDEO_EFFECT, AUDIO_EFFECT) = range(2)

BLACKLISTED_EFFECTS = ["colorconvert", "coglogoinsert", "festival",
                       "alphacolor", "cogcolorspace", "videodetect",
                       "navigationtest", "videoanalyse"]

#FIXME Check if this is still true with GES
#We should unblacklist it when #650985 is solved
BLACKLISTED_PLUGINS = ["ldaspa"]


class Effect():
    """
    Factories that applies an effect on a stream
    """
    def __init__(self, effect, media_type, categories=[_("Uncategorized")],
                  human_name="", description="", icon=None):
        self.effectname = effect
        self.media_type = media_type
        self.categories = categories
        self.description = description
        self.human_name = human_name
        self._icon = icon

    def getHumanName(self):
        return self.human_name

    def getDescription(self):
        return self.description

    def getCategories(self):
        return self.categories


class EffectsHandler(object):
    """
    Handles all the effects
    """
    def __init__(self):
        object.__init__(self)
        self._pixdir = get_pixmap_dir()
        self._audio_categories_effects = ((_("All effects"), ("")),)
        self._video_categories_effects = (
            (_("All effects"), ("")),
            (_("Colors"), ("cogcolorspace", "alphacolor", "videobalance",
                  "gamma", "alpha", "frei0r-filter-color-distance",
                  "frei0r-filter-contrast0r", "frei0r-filter-invert0r",
                  "frei0r-filter-saturat0r", "frei0r-filter-r",
                  "frei0r-filter-white-balance", "frei0r-filter-brightness",
                  "frei0r-filter-b", "frei0r-filter-gamma",
                  "frei0r-filter-hueshift0r", "frei0r-filter-transparency",
                  "frei0r-filter-equaliz0r", "frei0r-filter-glow",
                  "frei0r-filter-g", "frei0r-filter-bw0r", "burn", "dodge",
                  "coloreffects", "chromium", "exclusion", "glfiltersobel",
                  "Solarize", "frei0r-filter-threshold0r",
                  "frei0r-filter-twolay0r",
                )
            ),
            (_("Noise"), ("videorate", "frei0r-filter-edgeglow",
                  "gaussianblur", "diffuse", "dilate", "marble", )),
            (_("Analysis"), ("videoanalyse", "videodetect", "videomark",
                 "revtv", "navigationtest", "frei0r-filter-rgb-parade",
                 "frei0r-filter-vectorscope", "frei0r-filter-luminance",
                          )),
            (_("Blur"), ("frei0r-filter-squareblur", "gaussianblur", "diffuse",
                 "dilate", "marble", )),
            (_("Geometry"), ("cogscale", "aspectratiocrop", "cogdownsample",
                  "videocrop", "videoflip", "videobox", "gdkpixbufscale",
                  "frei0r-filter-letterb0xed",
                  "frei0r-filter-k-means-clustering",
                  "videoscale", "frei0r-filter-lens-correction",
                  "frei0r-filter-perspective",
                  "frei0r-filter-scale0tilt", "frei0r-filter-pixeliz0r",
                  "frei0r-filter-flippo", "frei0r-filter-3dflippo",
                  "frei0r-filter-letterb0xed", "bulge", "circle", "fisheye",
                  "kaleidoscope", "mirror", "pinch", "sphere", "square",
                  "stretch", "twirl", "waterriple",
                  )
            ),
            (_("Fancy"), ("rippletv", "streaktv", "radioactv", "optv",
                 "quarktv", "vertigotv", "shagadelictv", "warptv", "dicetv",
                 "agingtv", "edgetv", "frei0r-filter-cartoon",
                 "frei0r-filter-water", "frei0r-filter-nosync0r",
                 "frei0r-filter-k-means-clustering", "frei0r-filter-delay0r",
                 "bulge", "circle", "fisheye", "kaleidoscope", "mirror",
                 "pinch", "sphere", "square", "stretch", "twirl", "waterriple",
             )
            ),
            (_("Time"), ("frei0r-filter-delay0r",)),
            (_("Uncategorized"), ("",))
        )
        self._audio_categories = set([])
        self._video_categories = set([])
        self.video_effects = []
        self.audio_effects = []
        self._effect_factories_dict = {}
        self._setAllEffects()

    def _setAllEffects(self):
        """
        go trough the list of element factories and
        add them to the correct list filtering if necessary
        """
        factlist = gst.registry_get_default().get_feature_list(
            gst.ElementFactory)
        for element_factory in factlist:
            klass = element_factory.get_klass()
            name = element_factory.get_name()
            if "Effect" in klass and name not in BLACKLISTED_EFFECTS and not\
                [bplug for bplug in BLACKLISTED_PLUGINS if bplug in name]:
                if 'Audio' in klass:
                    self.audio_effects.append(element_factory)
                    media_type = AUDIO_EFFECT
                elif 'Video' in klass:
                    self.video_effects.append(element_factory)
                    media_type = VIDEO_EFFECT
                effect = Effect(name, media_type,
                                   self._getEffectCategories(name),
                                   self._getEffectName(element_factory),
                                   self._getEffectDescripton(element_factory))
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
        self._effect_factories_dict[name] = factory

    def getFactoryFromName(self, name):
        """
        @ivar name: Factory name.
        @type name: C{str}
        @returns: The l{Effect} corresponding to the name
        @raises: KeyError if the name doesn't  exist
        """
        return self._effect_factories_dict.get(name)

    def _getEffectDescripton(self, element_factory):
        """
        @ivar element_factory: The element factory
        @type element_factory: L{gst.ElementFactory}
        @returns: A human description C{str} for the effect
        """
        return element_factory.get_description()

    def _getEffectCategories(self, effect_name):
        """
        @ivar effect_name: the name of the effect for wich we want the category
        @type effect_name: L{str}
        @returns: A C{list} of name C{str} of categories corresponding the
        effect
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
                    self._video_categories.add(categorie[0])

        if not categories:
            uncategorized = _("Uncategorized")
            categories.append(uncategorized)
            self._video_categories.add(uncategorized)
            self._audio_categories.add(uncategorized)

        categories.insert(0, self._video_categories_effects[0][0])
        categories.insert(0, self._audio_categories_effects[0][0])

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
        return uselessWords.sub("", element_factory.get_longname()).title()

    def getVideoCategories(self, aware=True):
        """
        @ivar  aware: C{True} if you want it to return only categories on
        whichs
        there are effects on the system, else C{False}
        @type aware: C{bool}
        @returns: All video effect categories names C{str} that are available
        on the system if it has been filled earlier, if it hasen't it will
        just return all categories
        """
        if not self._video_categories or not aware:
            for categorie in self._video_categories_effects[1:]:
                self._video_categories.add(categorie[0])

        ret = list(self._video_categories)
        ret.sort()
        ret.insert(0, self._video_categories_effects[0][0])

        return ret

    video_categories = property(getVideoCategories)

    def getAudioCategories(self, aware=True):
        """
        @ivar  aware: C{True} if you want it to return only categories on
        whichs there are effects on the system, else C{False}
        @type aware: C{bool}
        @returns: All audio effect categories names C{str}
        """
        if not self._audio_categories or not aware:
            for categorie in self._audio_categories_effects[1:]:
                self._audio_categories.add(categorie[0])

        ret = list(self._audio_categories)
        ret.sort()
        ret.insert(0, self._audio_categories_effects[0][0])

        return ret

    audio_categories = property(getAudioCategories)

    def getAllCategories(self):
        """
        @returns: All effect categories names C{str}
        """
        effects_categories = []
        return effects_categories.extended(self.video_categories).extended(
            self.audio_categories)

    def getEffectIcon(self, effect_name):
        effect_name = effect_name + ".png"
        icon = None
        try:
            icon = gtk.gdk.pixbuf_new_from_file(os.path.join(self._pixdir,
                effect_name))
        # empty except clause is bad but load_icon raises gio.Error.
        ## Right, *gio*.
        except:
            try:
                icon = gtk.gdk.pixbuf_new_from_file(os.path.join(self._pixdir,
                    "defaultthumbnail.svg"))
            except:
                return None

        return icon
