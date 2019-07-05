# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2013, Alex Băluț <alexandru.balut@gmail.com>
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

from pitivi.utils.timeline import EditingContext
from pitivi.utils.timeline import SELECT
from pitivi.utils.timeline import SELECT_ADD
from pitivi.utils.timeline import Selected
from pitivi.utils.timeline import Selection
from pitivi.utils.timeline import UNSELECT
from tests import common
from tests.test_timeline_timeline import BaseTestTimeline


class TestSelected(common.TestCase):

    def testBoolEvaluation(self):
        selected = Selected()
        self.assertFalse(selected)

        selected.selected = True
        self.assertTrue(selected)

        selected.selected = False
        self.assertFalse(selected)


class TestSelection(BaseTestTimeline):

    def testBoolEvaluation(self):
        clip1 = mock.MagicMock()
        selection = Selection()
        self.assertFalse(selection)
        selection.setSelection([clip1], SELECT)
        self.assertTrue(selection)
        selection.setSelection([clip1], SELECT_ADD)
        self.assertTrue(selection)
        selection.setSelection([clip1], UNSELECT)
        self.assertFalse(selection)

    def testGetSingleClip(self):
        selection = Selection()
        clip1 = common.create_test_clip(GES.UriClip)
        clip2 = common.create_test_clip(GES.TitleClip)

        # Selection empty.
        self.assertIsNone(selection.getSingleClip())
        self.assertIsNone(selection.getSingleClip(GES.UriClip))
        self.assertIsNone(selection.getSingleClip(GES.TitleClip))

        selection.setSelection([clip1], SELECT)
        self.assertEqual(selection.getSingleClip(), clip1)
        self.assertEqual(selection.getSingleClip(GES.UriClip), clip1)
        self.assertIsNone(selection.getSingleClip(GES.TitleClip))

        selection.setSelection([clip2], SELECT)
        self.assertEqual(selection.getSingleClip(), clip2)
        self.assertIsNone(selection.getSingleClip(GES.UriClip))
        self.assertEqual(selection.getSingleClip(GES.TitleClip), clip2)

        selection.setSelection([clip1, clip2], SELECT)
        self.assertIsNone(selection.getSingleClip())
        self.assertIsNone(selection.getSingleClip(GES.UriClip))
        self.assertIsNone(selection.getSingleClip(GES.TitleClip))

    def test_can_group_ungroup(self):
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        clip1, clip2 = self.addClipsSimple(timeline, 2)

        selection = Selection()
        self.assertFalse(selection.can_group)
        self.assertFalse(selection.can_ungroup)

        selection.setSelection([clip1], SELECT)
        self.assertFalse(selection.can_group)
        self.assertTrue(selection.can_ungroup)

        selection.setSelection([clip2], SELECT_ADD)
        self.assertTrue(selection.can_group)
        self.assertFalse(selection.can_ungroup)

        selection.setSelection([], SELECT)
        self.assertFalse(selection.can_group)
        self.assertFalse(selection.can_ungroup)

    def test_toplevels(self):
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        clip1, clip2, clip3, clip4 = self.addClipsSimple(timeline, 4)

        selection = Selection()

        selection.setSelection([clip1, clip2, clip3, clip4], SELECT)
        self.assertSetEqual(selection.toplevels, {clip1, clip2, clip3, clip4})

        group1 = GES.Container.group([clip1, clip2])
        group1.props.serialize = True
        self.assertSetEqual(selection.toplevels, {group1, clip3, clip4})

        group2 = GES.Container.group([group1, clip3])
        group2.props.serialize = True
        self.assertSetEqual(selection.toplevels, {group2, clip4})

        group1.props.serialize = True
        group1.props.serialize = False
        self.assertSetEqual(selection.toplevels, {group2, clip4})

        group1.props.serialize = False
        group2.props.serialize = False
        self.assertSetEqual(selection.toplevels, {clip1, clip2, clip3, clip4})

        group1.props.serialize = True
        group2.props.serialize = False
        self.assertSetEqual(selection.toplevels, {group1, clip3, clip4})


class TestEditingContext(common.TestCase):
    """Tests for the EditingContext class."""

    def test_with_video(self):
        """Checks the value of the with_video field."""
        audio_clip = common.get_sample_clip("mp3_sample.mp3")
        video_clip = common.get_sample_clip("one_fps_numeroted_blue.mkv")
        audio_video_clip = common.get_sample_clip("tears_of_steel.webm")

        # Add the clips to a layer so they have TrackElements.
        project = common.create_project()
        layer = project.ges_timeline.append_layer()
        layer.add_clip(audio_clip)
        layer.add_clip(video_clip)
        layer.add_clip(audio_video_clip)

        self.__check_with_video(audio_clip, False)
        self.__check_with_video(video_clip, True)
        self.__check_with_video(audio_video_clip, True)

        # Check the track elements of a clip with audio only.
        audio_track_element = audio_clip.find_track_element(None, GES.AudioSource)
        self.__check_with_video(audio_track_element, False)

        # Check the track elements of a clip with video only.
        video_track_element = video_clip.find_track_element(None, GES.VideoSource)
        self.__check_with_video(video_track_element, True)

        # Check the track elements of a clip with both audio and video.
        audio_track_element = audio_video_clip.find_track_element(None, GES.AudioSource)
        video_track_element = audio_video_clip.find_track_element(None, GES.VideoSource)
        self.__check_with_video(audio_track_element, True)
        self.__check_with_video(video_track_element, True)

    def __check_with_video(self, clip, expected):
        context = EditingContext(clip, None, None, None, None, None)
        if expected:
            self.assertTrue(context.with_video)
        else:
            self.assertFalse(context.with_video)
