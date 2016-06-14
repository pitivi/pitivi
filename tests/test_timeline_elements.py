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
