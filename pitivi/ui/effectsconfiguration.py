#
#       ui/effectsconfiguration.py
#
# Copyright (C) 2010 Thibault Saunier <tsaunier@gnome.org>
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
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.

import gtk

from gettext import gettext as _

from pitivi.ui.common import SPACING

class EffectUIFactory(object):
    def __init__(self):
        self.cache_dict = {}

    def getEffectConfigurationUI(self, effect):
        if "videobalance" in effect.get_name():
            if effect not in self.cache_dict:
                video_balance_ui =  VideoBalanceConfig(effect)
                self.cache_dict[effect] = video_balance_ui
                return video_balance_ui
            else:
                return self.cache_dict[effect]
        else:
            return None


class VideoBalanceConfig(gtk.HBox):
    def __init__(self, effect):
        gtk.HBox.__init__(self, spacing=SPACING)

        self.balance = effect
        brightness = effect.get_property("brightness")
        contrast = effect.get_property("contrast")
        hue = effect.get_property("hue")
        saturation = effect.get_property("saturation")

        properties = [(_("contrast"), 0, 2, brightness),
                      (_("brightness"), -1, 1, contrast),
                      (_("hue"), -1, 1, hue),
                      (_("saturation"), 0, 2, saturation)]


        controls = gtk.VBox()
        labels = gtk.VBox()

        for prop, lower, upper, default in properties:
            widget = gtk.HScale()
            label = gtk.Label("\n  "+ prop + " :")
            widget.set_update_policy(gtk.UPDATE_CONTINUOUS)
            widget.set_value(default)
            widget.set_draw_value(True)
            widget.set_range(lower, upper)
            widget.connect("value-changed", self.onValueChangedCb, prop)

            controls.pack_start(widget, True, True)
            labels.pack_start(label, True, True)

        self.pack_start(labels, expand=False, fill=True)
        self.pack_end(controls, expand=True, fill=True)

    def onValueChangedCb(self, widget, prop):
        self.balance.set_property(prop, widget.get_value())
