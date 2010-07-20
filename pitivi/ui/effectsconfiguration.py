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

PROPS_TO_IGNORE = ['name', 'qos']

class EffectsPropertiesHandling:
    def __init__(self):
        self.cache_dict = {}
        self.pipeline = None
        self._current_effect_setting_ui = None

    def getEffectConfigurationUI(self, effect):
        """
            Permit to get a configuration GUI for the effect
            @param effect: The effect for which whe want the configuration UI
            @type effect: C{gst.Element}
        """
        if effect not in self.cache_dict:
            #Here we should handle special effects configuration UI
            effect_configuration_ui = gtk.ScrolledWindow()
            effect_set_ui = GstElementSettingsWidget()
            effect_set_ui.setElement(effect, ignore=PROPS_TO_IGNORE,
                                               default_btn=True, use_element_props=True)
            effect_configuration_ui.add_with_viewport(effect_set_ui)
            self._connectAllWidgetCbs(effect_set_ui, effect)
            self.cache_dict[effect] = effect_configuration_ui
        effect_set_ui = self.cache_dict[effect].get_children()[0].get_children()[0]
        self._current_effect_setting_ui = effect_set_ui
        return self.cache_dict[effect]

    def _flushSeekVideo(self):
        self.pipeline.pause()
        if self.pipeline is not None:
            try:
                self.pipeline.seekRelative(0)
            except PipelineError:
                pass

    def _connectAllWidgetCbs(self, effect_configuration_ui, effect):
        for prop, widget in effect_configuration_ui.properties.iteritems():
            if type(widget) in [gtk.SpinButton]:
                widget.connect("value-changed", self._onValueChangedCb)
            elif type(widget) in [gtk.Entry, gtk.ComboBox]:
                widget.connect("changed", self._onValueChangedCb)
            elif type(widget) in [gtk.CheckButton]:
                widget.connect("clicked", self._onValueChangedCb)

    def _onValueChangedCb(self, widget):
        for prop, value in self._current_effect_setting_ui.getSettings().iteritems():
            self._current_effect_setting_ui.element.set_property(prop, value)
        self._flushSeekVideo()
