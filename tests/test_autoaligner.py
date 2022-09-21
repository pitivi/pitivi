# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2022, Thejas Kiran P S <thejaskiranps@gmail.com>
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
import os

from gi.repository import GES
from gi.repository import Gst

from pitivi.autoaligner import AutoAligner
from pitivi.timeline.previewers import AudioPreviewer
from pitivi.timeline.previewers import get_wavefile_location_for_uri
from pitivi.undo.timeline import CommitTimelineFinalizingAction
from tests import common


class TestAutoAligner(common.TestCase):
    """Tests for AutoAligner class."""

    def __generate_wavefile(self, clip):
        wavefile = get_wavefile_location_for_uri(clip.props.uri)
        if os.path.exists(wavefile):
            return

        for source in clip.get_children(False):
            if isinstance(source, GES.AudioUriSource):
                source_clip = source

        mainloop = common.create_main_loop()
        previewer = AudioPreviewer(source_clip, 90)
        previewer.connect("done", lambda x: mainloop.quit())
        previewer.start_generation()
        mainloop.run()
        self.assertTrue(os.path.exists(wavefile))

    @common.setup_timeline
    def test_auto_aligner(self):
        # Prevent magnetic snapping from interfering with the alignment of clips.
        self.timeline.props.snapping_distance = 0
        self.timeline.append_layer()
        layers = self.timeline.get_layers()
        # Add clips(tears_of_steel.webm) to both layers with a
        # slight difference in their starting positions.
        clip1 = self.add_clip(layers[0], start=0, duration=Gst.SECOND)
        clip2 = self.add_clip(layers[1], start=Gst.SECOND, duration=Gst.SECOND)
        self.__generate_wavefile(clip1)

        self.assertNotEqual(clip1.start, clip2.start)
        autoaligner = AutoAligner([clip1, clip2])
        autoaligner.run()
        self.assertEqual(clip1.start, clip2.start)

    @common.setup_timeline
    def test_negative_shifts(self):
        """Tests shifts causing negative clip.start are handled properly."""
        self.timeline.props.snapping_distance = 0
        self.timeline.append_layer()
        layers = self.timeline.get_layers()
        clip1 = self.add_clip(layers[0], start=0, inpoint=Gst.SECOND // 2, duration=Gst.SECOND)
        clip2 = self.add_clip(layers[1], start=0, duration=Gst.SECOND)
        self.__generate_wavefile(clip1)

        autoaligner = AutoAligner([clip1, clip2])
        autoaligner.run()
        self.assertEqual(clip1.start, Gst.SECOND // 2)
        self.assertEqual(clip2.start, 0)

    @common.setup_timeline
    def test_align_undo_redo(self):
        self.timeline.props.snapping_distance = 0
        self.timeline.append_layer()
        layers = self.timeline.get_layers()

        clip1 = self.add_clip(layers[0], start=0, duration=Gst.SECOND)
        clip2 = self.add_clip(layers[1], start=Gst.SECOND, duration=Gst.SECOND)
        self.__generate_wavefile(clip1)

        with self.action_log.started("Align clips",
                                     finalizing_action=CommitTimelineFinalizingAction(self.project.pipeline),
                                     toplevel=True):
            autoaligner = AutoAligner([clip1, clip2])
            autoaligner.run()
        self.assertEqual([clip1.start, clip2.start], [0, 0])

        self.action_log.undo()
        self.assertEqual([clip1.start, clip2.start], [0, Gst.SECOND])
        self.action_log.redo()
        self.assertEqual([clip1.start, clip2.start], [0, 0])
