# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2016, Jakub Brindza <jakub.brindza@gmail.com>
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
from unittest import mock

from gi.repository import GES

from tests import common
from tests.test_timeline_timeline import BaseTestTimeline


class TestKeyframeCurve(BaseTestTimeline):

    def test_keyframe_toggle(self):
        timeline = self.createTimeline()
        pipeline = timeline._project.pipeline
        self.addClipsSimple(timeline, 2)
        ges_layer = timeline.ges_timeline.get_layers()[0]
        # For variety, add TitleClip to the list of clips.
        ges_clip = common.create_test_clip(GES.TitleClip)
        ges_clip.props.duration = 4.5
        ges_layer.add_clip(ges_clip)

        for ges_clip in ges_layer.get_clips():
            start = ges_clip.props.start
            offsets = list(range(1, int(ges_clip.props.duration)))
            timeline.selection.select([ges_clip])

            ges_video_source = None
            for child in ges_clip.get_children(recursive=False):
                if isinstance(child, GES.VideoSource):
                    ges_video_source = child
            binding = ges_video_source.get_control_binding("alpha")
            control_source = binding.props.control_source

            # Test adding of keyframes.
            for offset in offsets:
                position = start + offset
                pipeline.getPosition = mock.Mock(return_value=position)
                timeline.parent._keyframe_cb(None, None)
                values = [item.timestamp for item in control_source.get_all()]
                self.assertIn(offset, values)

            # Test removing of keyframes.
            for offset in offsets:
                position = start + offset
                pipeline.getPosition = mock.Mock(return_value=position)
                timeline.parent._keyframe_cb(None, None)
                values = [item.timestamp for item in control_source.get_all()]
                self.assertNotIn(offset, values)

            # Make sure the keyframes at the start and end of the clip
            # cannot be toggled.
            for offset in [0, ges_clip.props.duration]:
                position = start + offset
                pipeline.getPosition = mock.Mock(return_value=position)
                values = [item.timestamp for item in control_source.get_all()]
                self.assertIn(offset, values)
                timeline.parent._keyframe_cb(None, None)
                values = [item.timestamp for item in control_source.get_all()]
                self.assertIn(offset, values)

            # Test out of clip range.
            for offset in [-1, ges_clip.props.duration + 1]:
                position = min(max(0, start + offset),
                               timeline.ges_timeline.props.duration)
                pipeline.getPosition = mock.Mock(return_value=position)
                timeline.parent._keyframe_cb(None, None)
                values = [item.timestamp for item in control_source.get_all()]
                self.assertEqual(values, [0, ges_clip.props.duration])

    def test_no_clip_selected(self):
        # When no clip is selected, pressing key should yield no action.
        # Make sure this does not raise any exception
        timeline = self.createTimeline()
        timeline.parent._keyframe_cb(None, None)


class TestVideoSourceScaling(BaseTestTimeline):
    def test_video_source_scaling(self):
        timeline = self.createTimeline()
        project = timeline.app.project_manager.current_project

        clip = self.addClipsSimple(timeline, 1)[0]

        video_source = clip.find_track_element(None, GES.VideoUriSource)
        sinfo = video_source.get_asset().get_stream_info()

        width = video_source.get_child_property("width")[1]
        height = video_source.get_child_property("height")[1]
        self.assertEqual(sinfo.get_width(), 960)
        self.assertEqual(sinfo.get_height(), 400)
        self.assertEqual(project.videowidth, sinfo.get_width())
        self.assertEqual(project.videoheight, sinfo.get_height())
        self.assertEqual(project.videowidth, width)
        self.assertEqual(project.videoheight, height)

        project.videowidth = sinfo.get_width() * 2
        project.videoheight = sinfo.get_height() * 2
        width = video_source.get_child_property("width")[1]
        height = video_source.get_child_property("height")[1]
        self.assertEqual(project.videowidth, width)
        self.assertEqual(project.videoheight, height)

        project.videowidth = 150
        project.videoheight = 200
        width = video_source.get_child_property("width")[1]
        height = video_source.get_child_property("height")[1]

        expected_width = project.videowidth
        expected_height = int(sinfo.get_height() * (project.videowidth / sinfo.get_width()))
        self.assertEqual(width, expected_width)
        self.assertEqual(height, expected_height)

        video_source.set_child_property("posx", 50)
        width = video_source.get_child_property("width")[1]
        height = video_source.get_child_property("height")[1]
        self.assertEqual(width, expected_width)
        self.assertEqual(height, expected_height)

        project.videowidth = 1920
        project.videoheight = 1080
        self.assertEqual(width, expected_width)
        self.assertEqual(height, expected_height)

        expected_default_position = {
            "width": 1920,
            "height": 800,
            "posx": 0,
            "posy": 140}
        self.assertEqual(video_source.ui.default_position,
                         expected_default_position)

    def test_rotation(self):
        timeline = self.createTimeline()
        project = timeline.app.project_manager.current_project

        clip = self.addClipsSimple(timeline, 1)[0]

        video_source = clip.find_track_element(None, GES.VideoUriSource)
        sinfo = video_source.get_asset().get_stream_info()

        width = video_source.get_child_property("width")[1]
        height = video_source.get_child_property("height")[1]
        self.assertEqual(sinfo.get_width(), 960)
        self.assertEqual(sinfo.get_height(), 400)
        self.assertEqual(width, 960)
        self.assertEqual(height, 400)

        videoflip = GES.Effect.new("videoflip")
        videoflip.set_child_property("method", 1)  # clockwise

        clip.add(videoflip)
        # The video is flipped 90 degrees
        width = video_source.get_child_property("width")[1]
        height = video_source.get_child_property("height")[1]
        self.assertEqual(width, 167)
        self.assertEqual(height, 400)

        videoflip.props.active = False
        width = video_source.get_child_property("width")[1]
        height = video_source.get_child_property("height")[1]
        self.assertEqual(width, 960)
        self.assertEqual(height, 400)

        videoflip.props.active = True
        width = video_source.get_child_property("width")[1]
        height = video_source.get_child_property("height")[1]
        self.assertEqual(width, 167)
        self.assertEqual(height, 400)

        clip.remove(videoflip)
        width = video_source.get_child_property("width")[1]
        height = video_source.get_child_property("height")[1]
        self.assertEqual(width, 960)
        self.assertEqual(height, 400)
