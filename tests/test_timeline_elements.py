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
"""Tests for the timeline.elements module."""
# pylint: disable=protected-access,no-self-use,too-many-locals
from unittest import mock
from unittest import TestCase

from gi.overrides import GObject
from gi.repository import GES

from pitivi.timeline.elements import GES_TYPE_UI_TYPE
from tests.common import create_test_clip
from tests.common import create_timeline_container
from tests.test_timeline_timeline import BaseTestTimeline


class TestKeyframeCurve(BaseTestTimeline):
    """Tests for the KeyframeCurve class."""

    def test_keyframe_toggle(self):
        """Checks keyframes toggling at the playhead position."""
        timeline_container = create_timeline_container()
        timeline = timeline_container.timeline
        ges_layer = timeline.ges_timeline.append_layer()
        ges_clip1 = self.add_clip(ges_layer, 0)
        ges_clip2 = self.add_clip(ges_layer, 10)
        ges_clip3 = self.add_clip(ges_layer, 20, inpoint=100)
        # For variety, add TitleClip to the list of clips.
        ges_clip4 = create_test_clip(GES.TitleClip)
        ges_clip4.props.start = 30
        ges_clip4.props.duration = 4.5
        ges_layer.add_clip(ges_clip4)

        self.check_keyframe_toggle(ges_clip1, timeline_container)
        self.check_keyframe_toggle(ges_clip2, timeline_container)
        self.check_keyframe_toggle(ges_clip3, timeline_container)
        self.check_keyframe_toggle(ges_clip4, timeline_container)

    def check_keyframe_toggle(self, ges_clip, timeline_container):
        """Checks keyframes toggling on the specified clip."""
        timeline = timeline_container.timeline
        pipeline = timeline._project.pipeline

        start = ges_clip.props.start
        inpoint = ges_clip.props.in_point
        duration = ges_clip.props.duration
        offsets = (1, int(duration / 2), int(duration) - 1)
        timeline.selection.select([ges_clip])

        ges_video_source = None
        for child in ges_clip.get_children(recursive=False):
            if isinstance(child, GES.VideoSource):
                ges_video_source = child
        binding = ges_video_source.get_control_binding("alpha")
        control_source = binding.props.control_source

        values = [item.timestamp for item in control_source.get_all()]
        self.assertEqual(values, [inpoint, inpoint + duration])

        # Add keyframes.
        for offset in offsets:
            position = start + offset
            pipeline.getPosition = mock.Mock(return_value=position)
            timeline_container._keyframe_cb(None, None)
            values = [item.timestamp for item in control_source.get_all()]
            self.assertIn(inpoint + offset, values)

        # Remove keyframes.
        for offset in offsets:
            position = start + offset
            pipeline.getPosition = mock.Mock(return_value=position)
            timeline_container._keyframe_cb(None, None)
            values = [item.timestamp for item in control_source.get_all()]
            self.assertNotIn(inpoint + offset, values, offset)

        # Make sure the keyframes at the start and end of the clip
        # cannot be toggled.
        for offset in [0, duration]:
            position = start + offset
            pipeline.getPosition = mock.Mock(return_value=position)
            values = [item.timestamp for item in control_source.get_all()]
            self.assertIn(inpoint + offset, values)
            timeline_container._keyframe_cb(None, None)
            values = [item.timestamp for item in control_source.get_all()]
            self.assertIn(inpoint + offset, values)

        # Test out of clip range.
        for offset in [-1, duration + 1]:
            position = min(max(0, start + offset),
                           timeline.ges_timeline.props.duration)
            pipeline.getPosition = mock.Mock(return_value=position)
            timeline_container._keyframe_cb(None, None)
            values = [item.timestamp for item in control_source.get_all()]
            self.assertEqual(values, [inpoint, inpoint + duration])

    def test_no_clip_selected(self):
        """Checks nothing happens when no clip is selected."""
        timeline_container = create_timeline_container()
        # Make sure this does not raise any exception
        timeline_container._keyframe_cb(None, None)


class TestVideoSource(BaseTestTimeline):
    """Tests for the VideoSource class."""

    def test_video_source_scaling(self):
        """Checks the size of the scaled clips."""
        timeline_container = create_timeline_container()
        timeline = timeline_container.timeline
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
        """Checks the size of the clips flipped 90 degrees."""
        timeline_container = create_timeline_container()
        timeline = timeline_container.timeline

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


class TestClip(TestCase):
    """Tests for the Clip class."""

    def test_clip_subclasses(self):
        """Checks the constructors of the Clip class."""
        for gtype, widget_class in GES_TYPE_UI_TYPE.items():
            ges_object = GObject.new(gtype)
            widget = widget_class(mock.Mock(), ges_object)
            self.assertEqual(ges_object.ui, widget, widget_class)
