# -*- coding: utf-8 -*-
# Pitivi video editor
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

from pitivi.timeline.layer import Layer
from pitivi.timeline.timeline import Timeline
from tests import common


class TestLayerControl(common.TestCase):

    def testName(self):
        timeline = mock.MagicMock()
        ges_layer = GES.Layer()
        layer = Layer(ges_layer, timeline)
        self.assertEqual(layer.getName(), "Layer 0", "Default name generation failed")
        ges_layer.set_meta("audio::name", "a")
        self.assertEqual(layer.getName(), "a", "Cannot use old audio name")
        ges_layer.set_meta("video::name", "v")
        self.assertEqual(layer.getName(), "v", "Cannot use old video name")
        layer.setName("vv")
        self.assertEqual(layer.getName(), "vv")


class TestLayer(common.TestCase):

    def testCheckMediaTypesWhenNoUI(self):
        ges_layer = GES.Layer()
        png = common.get_sample_uri("flat_colour1_640x480.png")
        video_clip = GES.UriClipAsset.request_sync(png).extract()
        self.assertTrue(ges_layer.add_clip(video_clip))
        self.assertEqual(len(ges_layer.get_clips()), 1)
        timeline = Timeline(container=None, app=None)
        layer = Layer(ges_layer, timeline)
