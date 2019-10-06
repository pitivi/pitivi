# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2019, Alex Băluț <alexandru.balut@gmail.com>
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
"""Tests for the titleeditor module."""
# pylint: disable=protected-access
from unittest import mock

from gi.repository import GES

from pitivi.titleeditor import TitleEditor
from tests import common
from tests.test_undo_timeline import BaseTestUndoTimeline


class TitleEditorTest(BaseTestUndoTimeline):
    """Tests for the TitleEditor class."""

    def test_create(self):
        """Exercise creating a title clip."""
        # Wait until the project creates a layer in the timeline.
        common.create_main_loop().run(until_empty=True)

        title_editor = TitleEditor(self.app)

        from pitivi.timeline.timeline import TimelineContainer
        timeline_container = TimelineContainer(self.app)
        timeline_container.setProject(self.project)
        self.app.gui.editor.timeline_ui = timeline_container

        title_editor._newProjectLoadedCb(None, self.project)
        self.project.pipeline.getPosition = mock.Mock(return_value=0)

        title_editor._createCb(None)
        clips = self.layer.get_clips()
        self.assertEqual(len(clips), 1, clips)
        self.assertIsInstance(clips[0], GES.TitleClip)

        self.action_log.undo()
        clips = self.layer.get_clips()
        self.assertEqual(len(clips), 0, clips)

        self.action_log.redo()
        clips = self.layer.get_clips()
        self.assertEqual(len(clips), 1, clips)
