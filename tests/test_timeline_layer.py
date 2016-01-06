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

from unittest import mock

from gi.repository import GES

from tests import common

from pitivi.timeline.layer import Layer
from pitivi.timeline.timeline import Timeline


class TestLayerControl(common.TestCase):

    def testName(self):
        timeline = mock.MagicMock()
        bLayer = GES.Layer()
        layer = Layer(bLayer, timeline)
        self.assertEqual("Layer 0", layer.getName(), "Default name generation failed")
        bLayer.set_meta("audio::name", "a")
        self.assertEqual("a", layer.getName(), "Cannot use old audio name")
        bLayer.set_meta("video::name", "v")
        self.assertEqual("v", layer.getName(), "Cannot use old video name")
        layer.setName("vv")
        self.assertEqual("vv", layer.getName())


class TestLayer(common.TestCase):

    def testCheckMediaTypesWhenNoUI(self):
        bLayer = GES.Layer()
        png = common.getSampleUri("flat_colour1_640x480.png")
        video_clip = GES.UriClipAsset.request_sync(png).extract()
        self.assertTrue(bLayer.add_clip(video_clip))
        self.assertEqual(1, len(bLayer.get_clips()))
        timeline = Timeline(container=None, app=None)
        layer = Layer(bLayer, timeline)
