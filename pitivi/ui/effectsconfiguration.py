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

from pitivi.ui.gstwidget import GstElementSettingsWidget
from pitivi.pipeline import PipelineError

PROPERTIES_TO_IGNORE = ['name', 'qos']

class EffectsPropertiesHandling:
    def __init__(self):
        self.cache_dict = {}
        self.pipeline = None

    def getEffectConfigurationUI(self, effect):
        """
            Permit to get a configuration GUI for the effect
            @param effect: The effect for which whe want the configuration UI
            @type effect: C{gst.Element}
        """
        if effect in self.cache_dict:
            return self.cache_dict[effect]
        #elif "videobalance" in effect.get_name():
            #Here we should handle special effects
        else:
            effect_configuration_ui =  GstElementSettingsWidget()
            effect_configuration_ui.setElement(effect, ignore=PROPERTIES_TO_IGNORE)
            self._connectAllWidgetCbs(effect_configuration_ui, effect)
            self.cache_dict[effect] = effect_configuration_ui
        return effect_configuration_ui

    def _flushSeekVideo(self):
        self.pipeline.pause()
        if self.pipeline is not None:
            try:
                self.pipeline.seekRelative(0)
            except PipelineError:
                pass

    def _connectAllWidgetCbs(self, video_balance_ui, effect):
        for prop, widget in video_balance_ui.properties.iteritems():
            if type(widget) in [gtk.SpinButton]:
                widget.connect("value-changed", self._onValueChangedCb, prop.name, effect)
            elif type(widget) in [gtk.Entry]:
                widget.connect("changed", self._onEntryChangedCb, prop.name, effect)
            elif type(widget) in [gtk.ComboBox]:
                widget.connect("changed", self._onComboboxChangedCb, prop.name, effect)
            elif type(widget) in [gtk.CheckButton]:
                widget.connect("clicked", self._onCheckButtonClickedCb, prop.name, effect)

    def _onValueChangedCb(self, widget, prop, element):
        element.set_property(prop, widget.get_value())
        self._flushSeekVideo()

    def _onComboboxChangedCb(self, widget, prop, element):
        element.set_property(prop, widget.get_active_text())
        self._flushSeekVideo()

    def _onCheckButtonClickedCb(self, widget, prop, element):
        element.set_property(prop, widget.get_active())
        self._flushSeekVideo()

    def _onEntryChangedCb(self, widget, prop, element):
        element.set_property(prop, widget.get_text())
        self._flushSeekVideo()
