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


class TitleEditorTest(common.TestCase):
    """Tests for the TitleEditor class."""

    def test_create(self):
        """Exercise creating a title clip."""
        timeline_container = common.create_timeline_container(titleClipLength=1)
        project = timeline_container._project
        app = timeline_container.app

        # Wait until the project creates a layer in the timeline.
        common.create_main_loop().run(until_empty=True)

        title_editor = TitleEditor(app)
        title_editor._newProjectLoadedCb(None, project)
        project.pipeline.getPosition = mock.Mock(return_value=0)

        title_editor._createCb(None)
        layers = timeline_container.ges_timeline.get_layers()
        self.assertEqual(len(layers), 1, layers)
        clips = layers[0].get_clips()
        self.assertEqual(len(clips), 1, clips)
        self.assertIsInstance(clips[0], GES.TitleClip)
