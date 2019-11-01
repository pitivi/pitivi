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
from tests import common


class TestLayerControl(common.TestCase):

    def test_name(self):
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

    def test_name_meaningful(self):
        timeline = mock.MagicMock()
        ges_layer = GES.Layer()
        layer = Layer(ges_layer, timeline)
        layer.setName("Layer 0x")
        self.assertEqual(layer.getName(), "Layer 0x")


class TestLayer(common.TestCase):

    def test_check_media_types(self):
        """Checks media types when there is no control UI."""
        ges_layer = GES.Layer()
        png = common.get_sample_uri("flat_colour1_640x480.png")
        video_clip = GES.UriClipAsset.request_sync(png).extract()
        self.assertTrue(ges_layer.add_clip(video_clip))
        self.assertEqual(len(ges_layer.get_clips()), 1)
        timeline_container = common.create_timeline_container()
        timeline = timeline_container.timeline
        # This will add widgets for the clips in ges_layer and
        # the layer will use checkMediaTypes which updates the
        # height of layer.control_ui, which now it should not be set.
        self.assertFalse(hasattr(ges_layer, "control_ui"))
        unused_layer = Layer(ges_layer, timeline)
