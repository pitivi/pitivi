# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2021, Tyler Senne <tsenne2@huskers.unl.edu>
# Copyright (c) 2021, Michael Ervin <michael.ervin@huskers.unl.edu>
# Copyright (c) 2021, Aaron Friesen <afriesen4@huskers.unl.edu>
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
"""Tests for the pitivi.clipproperties module."""
# pylint: disable=protected-access,no-self-use,import-outside-toplevel,no-member
from gi.repository import Gst

from tests import common


class CompositingPropertiesTest(common.TestCase):

    @common.setup_project_with_clips(assets_names=["1sec_simpsons_trailer.mp4"])
    @common.setup_clipproperties
    def test_max_fade_duration(self):
        fade_in_adjustment = self.compositing_box._fade_in_adjustment
        fade_out_adjustment = self.compositing_box._fade_out_adjustment

        clip, = self.layer.get_clips()
        self.timeline_container.timeline.selection.select([clip])

        self.assertEqual(fade_in_adjustment.props.upper * Gst.SECOND, clip.duration)
        self.assertEqual(fade_out_adjustment.props.upper * Gst.SECOND, clip.duration)

        fade_in_adjustment.props.value = 0.5
        self.assertEqual(fade_out_adjustment.props.upper * Gst.SECOND, clip.duration - (0.5 * Gst.SECOND))

        fade_out_adjustment.props.value = 0.3
        self.assertEqual(fade_in_adjustment.props.upper * Gst.SECOND, clip.duration - (0.3 * Gst.SECOND))

    def _get_control_source(self, clip):
        source = self.get_clip_element(clip)
        control_binding = source.get_control_binding("alpha")
        self.assertIsNotNone(control_binding)
        control_source = control_binding.props.control_source
        self.assertIsNotNone(control_source)
        return control_source

    @common.setup_project_with_clips(assets_names=["1sec_simpsons_trailer.mp4"])
    @common.setup_clipproperties
    def test_apply_keyframes(self):
        clip, = self.layer.get_clips()
        self.timeline_container.timeline.selection.select([clip])

        fade_in_adjustment = self.compositing_box._fade_in_adjustment
        fade_out_adjustment = self.compositing_box._fade_out_adjustment
        fade_in_adjustment.props.value = 0.5
        fade_out_adjustment.props.value = 0.3

        control_source = self._get_control_source(clip)
        self.assert_control_source_values(control_source,
                                          [0, 1, 1, 0],
                                          [0, 0.5 * Gst.SECOND, clip.duration - 0.3 * Gst.SECOND, clip.duration])

    @common.setup_project_with_clips(assets_names=["1sec_simpsons_trailer.mp4"])
    @common.setup_clipproperties
    def test_move_keyframes(self):
        clip, = self.layer.get_clips()
        self.timeline_container.timeline.selection.select([clip])

        control_source = self._get_control_source(clip)
        control_source.set(0, 0)  # Necessary in order for fade-in to be recognized
        control_source.set(clip.duration, 0)  # Necessary in order for fade-out to be recognized
        control_source.set(0.6 * Gst.SECOND, 0.5)  # This keyframe should be unaffected
        control_source.set(0.1 * Gst.SECOND, 1)  # This keyframe should be the fade-in
        control_source.set(clip.duration - (0.2 * Gst.SECOND), 1)  # This keyframe should be the fade-out

        fade_in_adjustment = self.compositing_box._fade_in_adjustment
        fade_out_adjustment = self.compositing_box._fade_out_adjustment
        self.assertEqual(fade_in_adjustment.props.value, 0.1)
        self.assertEqual(fade_out_adjustment.props.value, 0.2)

        fade_in_adjustment.props.value = 0.5
        fade_out_adjustment.props.value = 0.3

        self.assert_control_source_values(control_source,
                                          [0, 1, 0.5, 1, 0],
                                          [0, 0.5 * Gst.SECOND, 0.6 * Gst.SECOND, clip.duration - 0.3 * Gst.SECOND, clip.duration])

    @common.setup_project_with_clips(assets_names=["1sec_simpsons_trailer.mp4", "30fps_numeroted_frames_blue.webm"])
    @common.setup_clipproperties
    def test_adjustments_updated_when_switching_clips(self):
        clip1, clip2 = self.layer.get_clips()
        self.timeline_container.timeline.selection.select([clip2])

        fade_in_adjustment = self.compositing_box._fade_in_adjustment
        fade_out_adjustment = self.compositing_box._fade_out_adjustment
        self.assertEqual(fade_in_adjustment.props.upper * Gst.SECOND, clip2.duration)
        self.assertEqual(fade_out_adjustment.props.upper * Gst.SECOND, clip2.duration)

        fade_in_adjustment.props.value = 1.3
        mainloop = common.create_main_loop()
        mainloop.run(until_empty=True)
        self.assertEqual(int(fade_out_adjustment.props.upper * Gst.SECOND), clip2.duration - int(1.3 * Gst.SECOND))

        fade_out_adjustment.props.value = 0.5
        self.assertEqual(int(fade_in_adjustment.props.upper * Gst.SECOND), clip2.duration - int(0.5 * Gst.SECOND))

        self.timeline_container.timeline.selection.select([clip1])
        self.assertEqual(fade_in_adjustment.props.value, 0)
        self.assertEqual(fade_out_adjustment.props.value, 0)
        self.assertEqual(fade_in_adjustment.props.upper * Gst.SECOND, clip1.duration)
        self.assertEqual(fade_out_adjustment.props.upper * Gst.SECOND, clip1.duration)

    @common.setup_project_with_clips(assets_names=["1sec_simpsons_trailer.mp4"])
    @common.setup_clipproperties
    def test_adjustments_updated_when_keyframes_updated(self):
        clip, = self.layer.get_clips()
        self.timeline_container.timeline.selection.select([clip])

        fade_in_adjustment = self.compositing_box._fade_in_adjustment
        fade_out_adjustment = self.compositing_box._fade_out_adjustment
        fade_in_adjustment.props.value = 0.5
        fade_out_adjustment.props.value = 0.3

        # Move the keyframes
        control_source = self._get_control_source(clip)
        control_source.unset(0.5 * Gst.SECOND)
        control_source.set(0.4 * Gst.SECOND, 1)
        control_source.unset(clip.duration - (0.3 * Gst.SECOND))
        control_source.set(clip.duration - (0.2 * Gst.SECOND), 1)

        self.assertEqual(fade_in_adjustment.props.value, 0.4)
        self.assertEqual(fade_out_adjustment.props.value, 0.2)
