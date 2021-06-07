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
# pylint: disable=protected-access
from unittest import mock

from gi.repository import GES

from pitivi.timeline.layer import AUDIO_ICONS
from pitivi.timeline.layer import FullLayer
from pitivi.timeline.layer import VIDEO_ICONS
from pitivi.utils.ui import LAYER_HEIGHT
from tests import common


class TestLayerControl(common.TestCase):

    def test_name(self):
        timeline = mock.MagicMock()
        ges_layer = GES.Layer()
        layer = FullLayer(ges_layer, timeline)
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
        layer = FullLayer(ges_layer, timeline)
        layer.set_name("Layer 0x")
        self.assertEqual(layer.get_name(), "Layer 0x")

    def test_audio_toggle(self):
        """Checks that audio toggling is reflected in the UI."""
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        ges_layer = timeline.ges_timeline.append_layer()
        layer_controls = ges_layer.control_ui
        audio_button = layer_controls.audio_button

        for audio_track in layer_controls.timeline_audio_tracks:
            self.assertTrue(ges_layer.get_active_for_track(audio_track))
            self.assertEqual(audio_button.get_image().props.icon_name, AUDIO_ICONS[True])

            ges_layer.set_active_for_tracks(False, [audio_track])
            common.create_main_loop().run(until_empty=True)
            self.assertFalse(ges_layer.get_active_for_track(audio_track))
            self.assertEqual(audio_button.get_image().props.icon_name, AUDIO_ICONS[False])

            ges_layer.set_active_for_tracks(True, [audio_track])
            common.create_main_loop().run(until_empty=True)
            self.assertTrue(ges_layer.get_active_for_track(audio_track))
            self.assertEqual(audio_button.get_image().props.icon_name, AUDIO_ICONS[True])

    def test_audio_button(self):
        """Checks that the audio button toggles the audio track."""
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        ges_layer = timeline.ges_timeline.append_layer()
        layer_controls = ges_layer.control_ui
        audio_button = layer_controls.audio_button

        for audio_track in layer_controls.timeline_audio_tracks:
            self.assertTrue(ges_layer.get_active_for_track(audio_track))
        common.create_main_loop().run(until_empty=True)
        self.assertEqual(audio_button.get_image().props.icon_name, AUDIO_ICONS[True])

        audio_button.clicked()
        for audio_track in layer_controls.timeline_audio_tracks:
            self.assertFalse(ges_layer.get_active_for_track(audio_track))
        common.create_main_loop().run(until_empty=True)
        self.assertEqual(audio_button.get_image().props.icon_name, AUDIO_ICONS[False])

        audio_button.clicked()
        for audio_track in layer_controls.timeline_audio_tracks:
            self.assertTrue(ges_layer.get_active_for_track(audio_track))
        common.create_main_loop().run(until_empty=True)
        self.assertEqual(audio_button.get_image().props.icon_name, AUDIO_ICONS[True])

    def test_video_toggle(self):
        """Checks that video toggling is reflected in the UI."""
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        ges_layer = timeline.ges_timeline.append_layer()
        layer_controls = ges_layer.control_ui
        video_button = layer_controls.video_button

        for video_track in layer_controls.timeline_video_tracks:
            self.assertTrue(ges_layer.get_active_for_track(video_track))
            self.assertEqual(video_button.get_image().props.icon_name, VIDEO_ICONS[True])

            ges_layer.set_active_for_tracks(False, [video_track])
            common.create_main_loop().run(until_empty=True)
            self.assertFalse(ges_layer.get_active_for_track(video_track))
            self.assertEqual(video_button.get_image().props.icon_name, VIDEO_ICONS[False])

            ges_layer.set_active_for_tracks(True, [video_track])
            common.create_main_loop().run(until_empty=True)
            self.assertTrue(ges_layer.get_active_for_track(video_track))
            self.assertEqual(video_button.get_image().props.icon_name, VIDEO_ICONS[True])

    def test_video_button(self):
        """Checks that the video button toggles the video track."""
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        ges_layer = timeline.ges_timeline.append_layer()
        layer_controls = ges_layer.control_ui
        video_button = layer_controls.video_button

        for video_track in layer_controls.timeline_video_tracks:
            self.assertTrue(ges_layer.get_active_for_track(video_track))
        common.create_main_loop().run(until_empty=True)
        self.assertEqual(video_button.get_image().props.icon_name, VIDEO_ICONS[True])

        video_button.clicked()
        for video_track in layer_controls.timeline_video_tracks:
            self.assertFalse(ges_layer.get_active_for_track(video_track))
        common.create_main_loop().run(until_empty=True)
        self.assertEqual(video_button.get_image().props.icon_name, VIDEO_ICONS[False])

        video_button.clicked()
        for video_track in layer_controls.timeline_video_tracks:
            self.assertTrue(ges_layer.get_active_for_track(video_track))
        common.create_main_loop().run(until_empty=True)
        self.assertEqual(video_button.get_image().props.icon_name, VIDEO_ICONS[True])


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
        unused_layer = FullLayer(ges_layer, timeline)

    @common.setup_timeline
    def test_layer_heights(self):
        self.check_layer_height(GES.TrackType(0))

        clip_video = GES.UriClipAsset.request_sync(common.get_sample_uri("one_fps_numeroted_blue.mkv")).extract()
        self.timeline_container._insert_clips_and_assets([clip_video], 0, self.layer)
        self.check_layer_height(GES.TrackType.VIDEO)

        clip_audio = GES.UriClipAsset.request_sync(common.get_sample_uri("mp3_sample.mp3")).extract()
        self.timeline_container._insert_clips_and_assets([clip_audio], 0, self.layer)
        self.check_layer_height(GES.TrackType.AUDIO | GES.TrackType.VIDEO)

        self.click_clip(clip_video, expect_selected=True)
        self.timeline_container.delete_action.activate()
        self.check_layer_height(GES.TrackType.AUDIO)

        self.click_clip(clip_audio, expect_selected=True)
        self.timeline_container.delete_action.activate()
        self.check_layer_height(GES.TrackType(0))

        # Undo everything.
        self.action_log.undo()
        self.check_layer_height(GES.TrackType.AUDIO)

        self.action_log.undo()
        self.check_layer_height(GES.TrackType.AUDIO | GES.TrackType.VIDEO)

        self.action_log.undo()
        self.check_layer_height(GES.TrackType.VIDEO)

        self.action_log.undo()
        self.check_layer_height(GES.TrackType(0))

        # Redo everything.
        self.action_log.redo()
        self.check_layer_height(GES.TrackType.VIDEO)

        self.action_log.redo()
        self.check_layer_height(GES.TrackType.AUDIO | GES.TrackType.VIDEO)

        self.action_log.redo()
        self.check_layer_height(GES.TrackType.AUDIO)

        self.action_log.redo()
        self.check_layer_height(GES.TrackType(0))

    def check_layer_height(self, expected_media_types: GES.TrackType):
        self.assertEqual(self.timeline_container.timeline.media_types, expected_media_types)
        if expected_media_types == GES.TrackType.AUDIO | GES.TrackType.VIDEO:
            self.assertEqual(self.layer.ui.props.height_request, LAYER_HEIGHT)
        else:
            self.assertEqual(self.layer.ui.props.height_request, LAYER_HEIGHT // 2)
