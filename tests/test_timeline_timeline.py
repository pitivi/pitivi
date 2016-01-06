# -*- coding: utf-8 -*-
#
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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

from unittest import TestCase, mock
from tests.common import getPitiviMock
from gi.repository import Gdk

from pitivi.project import Project, ProjectManager
from pitivi.timeline.timeline import Timeline
from pitivi.utils import ui


SEPARATOR_HEIGHT = 4
THIN = ui.LAYER_HEIGHT / 2
THICK = ui.LAYER_HEIGHT


class TestLayers(TestCase):

    def createTimeline(self, layers_heights):
        app = getPitiviMock()
        project_manager = ProjectManager(app)
        project_manager.newBlankProject()
        project = project_manager.current_project
        timeline = Timeline(container=mock.MagicMock(), app=app)
        timeline.get_parent = mock.MagicMock()
        timeline.setProject(project)
        y = 0
        for priority, height in enumerate(layers_heights):
            bLayer = timeline.createLayer(priority=priority)
            rect = Gdk.Rectangle()
            rect.y = y
            rect.height = height
            bLayer.ui.set_allocation(rect)
            y += height + SEPARATOR_HEIGHT
        return timeline

    def testDraggingLayer(self):
        self.checkGetLayerAt([THIN, THIN, THIN], 1, True,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])
        self.checkGetLayerAt([THICK, THICK, THICK], 1, True,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])
        self.checkGetLayerAt([THIN, THICK, THIN], 1, True,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])
        self.checkGetLayerAt([THICK, THIN, THICK], 1, True,
                             [0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2])

    def testDraggingClipFromLayer(self):
        self.checkGetLayerAt([THIN, THIN, THIN], 1, False,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])
        self.checkGetLayerAt([THICK, THICK, THICK], 1, False,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])
        self.checkGetLayerAt([THIN, THICK, THIN], 1, False,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])
        self.checkGetLayerAt([THICK, THIN, THICK], 1, False,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2])

    def testDraggingClipFromOuterSpace(self):
        self.checkGetLayerAt([THIN, THIN, THIN], None, False,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2])
        self.checkGetLayerAt([THICK, THICK, THICK], None, False,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2])
        self.checkGetLayerAt([THIN, THICK, THIN], None, False,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2])
        self.checkGetLayerAt([THICK, THIN, THICK], None, False,
                             [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2])

    def checkGetLayerAt(self, heights, preferred, past_middle_when_adjacent, expectations):
        timeline = self.createTimeline(heights)
        bLayers = [layer.bLayer for layer in timeline._layers]
        if preferred is None:
            preferred_bLayer = None
        else:
            preferred_bLayer = bLayers[preferred]
        h = [layer.get_allocation().height for layer in timeline._layers]
        s = SEPARATOR_HEIGHT

        def assertLayerAt(bLayer, y):
            result = timeline._Timeline__getLayerAt(
                int(y),
                prefer_bLayer=preferred_bLayer,
                past_middle_when_adjacent=past_middle_when_adjacent)
            self.assertEqual(
                bLayer,
                result[0],
                "Expected %d, got %d at %d" % (bLayers.index(bLayer), bLayers.index(result[0]), y))

        # y on the top layer.
        assertLayerAt(bLayers[expectations[0]], 0)
        assertLayerAt(bLayers[expectations[1]], h[0] / 2 - 1)
        assertLayerAt(bLayers[expectations[2]], h[0] / 2)
        assertLayerAt(bLayers[expectations[3]], h[0] - 1)

        # y on the separator.
        assertLayerAt(bLayers[expectations[4]], h[0])
        assertLayerAt(bLayers[expectations[5]], h[0] + s - 1)

        # y on the middle layer.
        assertLayerAt(bLayers[expectations[6]], h[0] + s)
        assertLayerAt(bLayers[expectations[7]], h[0] + s + h[1] / 2 - 1)
        assertLayerAt(bLayers[expectations[8]], h[0] + s + h[1] / 2)
        assertLayerAt(bLayers[expectations[9]], h[0] + s + h[1] - 1)

        # y on the separator.
        assertLayerAt(bLayers[expectations[10]], h[0] + s + h[1])
        assertLayerAt(bLayers[expectations[11]], h[0] + s + h[1] + s - 1)

        # y on the bottom layer.
        assertLayerAt(bLayers[expectations[12]], h[0] + s + h[1] + s)
        assertLayerAt(bLayers[expectations[13]], h[0] + s + h[1] + s + h[2] / 2 - 1)
        assertLayerAt(bLayers[expectations[14]], h[0] + s + h[1] + s + h[2] / 2)
        assertLayerAt(bLayers[expectations[15]], h[0] + s + h[1] + s + h[2] - 1)
