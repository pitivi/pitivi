# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2016, Alex Băluț <alexandru.balut@gmail.com>
# Copyright (c) 2017, Suhas Nayak <suhas2go@gmail.com>
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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
"""Tests for the effects module."""
# pylint: disable=attribute-defined-outside-init,protected-access
import os

from gi.repository import GES
from gi.repository import Gst
from gi.repository import Gtk

from pitivi.effects import AUDIO_EFFECT
from pitivi.effects import EffectInfo
from pitivi.effects import EffectsPropertiesManager
from pitivi.effects import PROPS_TO_IGNORE
from pitivi.effects import VIDEO_EFFECT
from pitivi.utils.widgets import DynamicWidget
from pitivi.utils.widgets import GstElementSettingsWidget
from pitivi.utils.widgets import NumericWidget
from tests import common


class EffectInfoTest(common.TestCase):
    """Tests for the EffectInfo class."""

    def test_bin_description(self):
        """Checks the bin_description property."""
        effect_info = EffectInfo("name", None, None, None, None)
        self.assertEqual(effect_info.bin_description, "name")

        effect_info = EffectInfo("glname", None, None, None, None)
        self.assertEqual(effect_info.bin_description, "glupload ! glname ! gldownload")

    def test_name_from_bin_description(self):
        """Checks the name_from_bin_description method."""
        self.assertEqual(EffectInfo.name_from_bin_description("name"), "name")
        self.assertEqual(EffectInfo.name_from_bin_description("glupload ! glname ! gldownload"), "glname")

    def test_good_for_track_element(self):
        """Checks the good_for_track_element method."""
        uri = common.get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        ges_clip = asset.extract()

        # Add the clip to a timeline so it gets tracks.
        ges_timeline = common.create_timeline_container().timeline.ges_timeline
        ges_timeline.append_layer()
        ges_layer, = ges_timeline.get_layers()
        ges_layer.add_clip(ges_clip)
        track_elements = {track_element.get_track_type(): track_element
                          for track_element in ges_clip.get_children(recursive=True)}
        audio_track_element = track_elements[GES.TrackType.AUDIO]
        video_track_element = track_elements[GES.TrackType.VIDEO]

        effect_info = EffectInfo(None, AUDIO_EFFECT, None, None, None)
        self.assertTrue(effect_info.good_for_track_element(audio_track_element))
        self.assertFalse(effect_info.good_for_track_element(video_track_element))

        effect_info = EffectInfo(None, VIDEO_EFFECT, None, None, None)
        self.assertFalse(effect_info.good_for_track_element(audio_track_element))
        self.assertTrue(effect_info.good_for_track_element(video_track_element))


class EffectsPropertiesManagerTest(common.TestCase):
    """Tests for the EffectsPropertiesManager class."""

    def create_alpha_widget_cb(self, unused_manager, unused_container, unused_effect, widgets):
        """Handles the request to create an effect widget."""
        self.builder = Gtk.Builder()
        path = os.path.join(os.path.dirname(__file__), "plugins", "test_alpha.ui")
        self.builder.add_objects_from_file(path, widgets)
        self.element_settings_widget.map_builder(self.builder)
        return self.builder.get_object("GstAlpha::black-sensitivity")

    def _register_alpha_widget(self, widgets):
        """Sets up an EffectsPropertiesManager instance to create custom effect UI."""
        self.alpha_effect = GES.Effect.new("alpha")
        self.prop_name = "black-sensitivity"
        _, _, self.prop = self.alpha_effect.lookup_child(self.prop_name)

        self.effects_prop_manager = EffectsPropertiesManager(self.app)
        self.effects_prop_manager.connect("create-widget", self.create_alpha_widget_cb, widgets)
        self.element_settings_widget = GstElementSettingsWidget(self.alpha_effect, PROPS_TO_IGNORE)

        self.effects_prop_manager.emit("create-widget", self.element_settings_widget, self.alpha_effect)
        self.effects_prop_manager._connect_all_widget_callbacks(self.element_settings_widget, self.alpha_effect)
        self.effects_prop_manager._post_configuration(self.alpha_effect, self.element_settings_widget)

    def test_wrapping(self):
        """Checks UI updating results in updating the effect."""
        self.app = common.create_pitivi_mock()
        self._register_alpha_widget(("black_sens_adjustment", "GstAlpha::black-sensitivity"))

        # Check if the widget is wrapped correctly
        wrapped_spin_button = self.element_settings_widget.properties[self.prop]
        self.assertTrue(isinstance(wrapped_spin_button, DynamicWidget))
        self.assertTrue(isinstance(wrapped_spin_button, NumericWidget))

        # Check if the wrapper has the correct default value
        self.assertEqual(self.prop.default_value, wrapped_spin_button.get_widget_default())

        # Check if the callbacks are functioning
        value = (1 + self.prop.default_value) % self.prop.maximum
        wrapped_spin_button.set_widget_value(value)
        self.assertEqual(wrapped_spin_button.get_widget_value(), value)
        _, prop_value = self.alpha_effect.get_child_property(self.prop_name)
        self.assertEqual(prop_value, value)

    def test_prop_keyframe(self):
        """Checks the keyframe button effect."""
        uri = common.get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        ges_clip = asset.extract()

        # Add the clip to a timeline so it gets tracks.
        timeline = common.create_timeline_container()
        self.app = timeline.app
        ges_timeline = timeline.ges_timeline
        ges_timeline.append_layer()
        ges_layer, = ges_timeline.get_layers()
        ges_layer.add_clip(ges_clip)

        self._register_alpha_widget(
            ("black_sens_adjustment", "GstAlpha::black-sensitivity", "GstAlpha::black-sensitivity::keyframe"))
        ges_clip.add(self.alpha_effect)
        track_element = self.element_settings_widget._GstElementSettingsWidget__get_track_element_of_same_type(
            self.alpha_effect)
        prop_keyframe_button = \
            list(self.element_settings_widget._GstElementSettingsWidget__widgets_by_keyframe_button.keys())[0]

        # Control the self.prop property on the timeline
        prop_keyframe_button.set_active(True)
        self.assertEqual(track_element.ui._TimelineElement__controlled_property, self.prop)
        # Revert to controlling the default property
        prop_keyframe_button.set_active(False)
        self.assertNotEqual(track_element.ui._TimelineElement__controlled_property, self.prop)

    def test_prop_reset(self):
        """Checks the reset button resets the property."""
        self.app = common.create_pitivi_mock()
        self._register_alpha_widget(
            ("black_sens_adjustment", "GstAlpha::black-sensitivity", "GstAlpha::black-sensitivity::reset", "image1"))
        wrapped_spin_button = self.element_settings_widget.properties[self.prop]
        _, prop_value = self.alpha_effect.get_child_property(self.prop_name)
        self.assertEqual(self.prop.default_value, prop_value)
        self.assertEqual(self.prop.default_value, wrapped_spin_button.get_widget_value())

        # Set the property value to a different value than the default
        wrapped_spin_button.set_widget_value((1 + self.prop.default_value) % self.prop.maximum)
        _, prop_value = self.alpha_effect.get_child_property(self.prop_name)
        self.assertEqual(prop_value, (1 + self.prop.default_value) % self.prop.maximum)

        # Reset the value of the property to default
        prop_reset_button = \
            list(self.element_settings_widget._GstElementSettingsWidget__widgets_by_reset_button.keys())[0]
        prop_reset_button.clicked()
        _, prop_value = self.alpha_effect.get_child_property(self.prop_name)
        self.assertEqual(self.prop.default_value, prop_value)
        self.assertEqual(self.prop.default_value, wrapped_spin_button.get_widget_value())

    def test_dependent_properties(self):
        """Checks dependent properties updating is handled correctly."""
        mainloop = common.create_main_loop()
        app = common.create_pitivi()
        app.project_manager.new_blank_project()
        manager = EffectsPropertiesManager(app)

        called = False

        def set_child_property(prop_name, value):
            nonlocal called
            called = True

            self.assertEqual(prop_name, "aspect-ratio")
            GES.Effect.set_child_property(effect, prop_name, value)

            # When setting the aspect-ratio property, and the stars align,
            # the effect also changes the left/right properties.
            # Here we simulate the updating of the dependent properties.
            GES.Effect.set_child_property(effect, "left", 100)
            GES.Effect.set_child_property(effect, "right", 100)

        effect = GES.Effect.new("aspectratiocrop")
        effect.set_child_property = set_child_property

        effect_widget = manager.get_effect_configuration_ui(effect)

        widgets = {prop.name: widget
                   for prop, widget in effect_widget.properties.items()}
        # Simulate the user choosing an aspect-ratio.
        widgets["aspect-ratio"].set_widget_value(Gst.Fraction(4, 3))

        mainloop.run(until_empty=True)

        self.assertTrue(called)
