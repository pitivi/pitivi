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
import unittest

from gi.repository import GES

from pitivi.effects import AUDIO_EFFECT
from pitivi.effects import EffectInfo
from pitivi.effects import VIDEO_EFFECT
from tests.common import create_timeline_container
from tests.common import get_sample_uri


class EffectInfoTest(unittest.TestCase):
    """Tests for the EffectInfo class."""

    def test_bin_description(self):
        """Tests the bin_description property."""
        effect_info = EffectInfo("name", None, None, None, None)
        self.assertEqual(effect_info.bin_description, "name")

        effect_info = EffectInfo("glname", None, None, None, None)
        self.assertEqual(effect_info.bin_description, "glupload ! glname ! gldownload")

    def test_name_from_bin_description(self):
        """Tests the name_from_bin_description method."""
        self.assertEqual(EffectInfo.name_from_bin_description("name"), "name")
        self.assertEqual(EffectInfo.name_from_bin_description("glupload ! glname ! gldownload"), "glname")

    def test_good_for_track_element(self):
        """Tests the good_for_track_element method."""
        uri = get_sample_uri("tears_of_steel.webm")
        asset = GES.UriClipAsset.request_sync(uri)
        ges_clip = asset.extract()

        # Add the clip to a timeline so it gets tracks.
        ges_timeline = create_timeline_container().timeline.ges_timeline
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
