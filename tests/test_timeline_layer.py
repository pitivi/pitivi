# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2015, Alex Băluț <alexandru.balut@gmail.com>
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
from unittest import mock

from gi.repository import GES

from pitivi.timeline.layer import Layer
from tests import common


class TestLayerControl(common.TestCase):

    def test_name(self):
        timeline = mock.MagicMock()
        ges_layer = GES.Layer()
        layer = Layer(ges_layer, timeline)
        self.assertEqual(layer.get_name(), "Layer 0", "Default name generation failed")

        ges_layer.set_meta("audio::name", "a")
        self.assertEqual(layer.get_name(), "a", "Cannot use old audio name")

        ges_layer.set_meta("video::name", "v")
        self.assertEqual(layer.get_name(), "v", "Cannot use old video name")

        layer.set_name("vv")
        self.assertEqual(layer.get_name(), "vv")

    def test_name_meaningful(self):
        timeline = mock.MagicMock()
        ges_layer = GES.Layer()
        layer = Layer(ges_layer, timeline)
        layer.set_name("Layer 0x")
        self.assertEqual(layer.get_name(), "Layer 0x")

    def test_mute_and_unmute_layer(self):
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        ges_layer = timeline.ges_timeline.append_layer()
        layer_controls = ges_layer.control_ui
        mute_toggle_button = layer_controls.mute_toggle_button

        for audio_track in layer_controls.timeline_audio_tracks:
            self.assertTrue(ges_layer.get_active_for_track(audio_track))
            self.assertFalse(mute_toggle_button.get_active())

            ges_layer.set_active_for_tracks(False, [audio_track])
            common.create_main_loop().run(until_empty=True)
            self.assertFalse(ges_layer.get_active_for_track(audio_track))
            self.assertTrue(mute_toggle_button.get_active())

            ges_layer.set_active_for_tracks(True, [audio_track])
            common.create_main_loop().run(until_empty=True)
            self.assertTrue(ges_layer.get_active_for_track(audio_track))
            self.assertFalse(mute_toggle_button.get_active())

    def test_mute_and_unmute_layer_button(self):
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        ges_layer = timeline.ges_timeline.append_layer()
        layer_controls = ges_layer.control_ui
        mute_toggle_button = layer_controls.mute_toggle_button

        for audio_track in layer_controls.timeline_audio_tracks:
            self.assertTrue(ges_layer.get_active_for_track(audio_track))
        common.create_main_loop().run(until_empty=True)
        self.assertFalse(mute_toggle_button.get_active())

        mute_toggle_button.clicked()
        for audio_track in layer_controls.timeline_audio_tracks:
            self.assertFalse(ges_layer.get_active_for_track(audio_track))
        common.create_main_loop().run(until_empty=True)
        self.assertTrue(mute_toggle_button.get_active())

        mute_toggle_button.clicked()
        for audio_track in layer_controls.timeline_audio_tracks:
            self.assertTrue(ges_layer.get_active_for_track(audio_track))
        common.create_main_loop().run(until_empty=True)
        self.assertFalse(mute_toggle_button.get_active())

    def test_layer_hide_video(self):
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        ges_layer = timeline.ges_timeline.append_layer()
        layer_controls = ges_layer.control_ui
        video_toggle_button = layer_controls.video_toggle_button

        for video_track in layer_controls.timeline_video_tracks:
            self.assertTrue(ges_layer.get_active_for_track(video_track))
            self.assertFalse(video_toggle_button.get_active())

            ges_layer.set_active_for_tracks(False, [video_track])
            common.create_main_loop().run(until_empty=True)
            self.assertFalse(ges_layer.get_active_for_track(video_track))
            self.assertTrue(video_toggle_button.get_active())

            ges_layer.set_active_for_tracks(True, [video_track])
            common.create_main_loop().run(until_empty=True)
            self.assertTrue(ges_layer.get_active_for_track(video_track))
            self.assertFalse(video_toggle_button.get_active())

    def test_layer_hide_video_button(self):
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        ges_layer = timeline.ges_timeline.append_layer()
        layer_controls = ges_layer.control_ui
        video_toggle_button = layer_controls.video_toggle_button

        for video_track in layer_controls.timeline_video_tracks:
            self.assertTrue(ges_layer.get_active_for_track(video_track))
        common.create_main_loop().run(until_empty=True)
        self.assertFalse(video_toggle_button.get_active())

        video_toggle_button.clicked()
        for video_track in layer_controls.timeline_video_tracks:
            self.assertFalse(ges_layer.get_active_for_track(video_track))
        common.create_main_loop().run(until_empty=True)
        self.assertTrue(video_toggle_button.get_active())

        video_toggle_button.clicked()
        for video_track in layer_controls.timeline_video_tracks:
            self.assertTrue(ges_layer.get_active_for_track(video_track))
        common.create_main_loop().run(until_empty=True)
        self.assertFalse(video_toggle_button.get_active())


class TestLayer(common.TestCase):

    def test_check_media_types(self):
        """Checks media types when there is no control UI."""
        ges_layer = GES.Layer()
        png = common.get_sample_uri("flat_colour1_640x480.png")
        video_clip = GES.UriClipAsset.request_sync(png).extract()
        self.assertTrue(ges_layer.add_clip(video_clip))
        self.assertEqual(len(ges_layer.get_clips()), 1)
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        # This will add widgets for the clips in ges_layer and
        # the layer will use check_media_types which updates the
        # height of layer.control_ui, which now it should not be set.
        self.assertFalse(hasattr(ges_layer, "control_ui"))
        unused_layer = Layer(ges_layer, timeline)
