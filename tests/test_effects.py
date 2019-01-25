# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2016, Alex Băluț <alexandru.balut@gmail.com>
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
"""Tests for the effects module."""
from gi.repository import GES
from gi.repository import Gst

from pitivi.effects import AUDIO_EFFECT
from pitivi.effects import EffectInfo
from pitivi.effects import EffectsPropertiesManager
from pitivi.effects import VIDEO_EFFECT
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
        track_elements = dict([(track_element.get_track_type(), track_element)
                               for track_element in ges_clip.get_children(recursive=True)])
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

    def test_dependent_properties(self):
        """Checks dependent properties updating is handled correctly."""
        mainloop = common.create_main_loop()
        app = common.create_pitivi()
        app.project_manager.newBlankProject()
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

        effect_widget = manager.getEffectConfigurationUI(effect)

        widgets = {prop.name: widget
                   for prop, widget in effect_widget.properties.items()}
        # Simulate the user choosing an aspect-ratio.
        widgets["aspect-ratio"].setWidgetValue(Gst.Fraction(4, 3))

        mainloop.run(until_empty=True)

        self.assertTrue(called)
