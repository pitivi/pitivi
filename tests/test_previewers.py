# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2015, Thibault Saunier <tsaunier@gnome.org>
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
import os
import pickle
import tempfile
from unittest import mock
from unittest import TestCase

from gi.repository import GES
from gi.repository import Gst

from pitivi.timeline.previewers import get_wavefile_location_for_uri
from pitivi.timeline.previewers import THUMB_HEIGHT
from pitivi.timeline.previewers import ThumbnailCache
from tests import common
from tests.test_media_library import BaseTestMediaLibrary


class TestPreviewers(BaseTestMediaLibrary):

    def testCreateThumbnailBin(self):
        pipeline = Gst.parse_launch("uridecodebin name=decode uri=file:///some/thing"
                                    " waveformbin name=wavebin ! fakesink qos=false name=faked")
        self.assertTrue(pipeline)
        wavebin = pipeline.get_by_name("wavebin")
        self.assertTrue(wavebin)

    def testWaveFormAndThumbnailCreated(self):
        sample_name = "1sec_simpsons_trailer.mp4"
        self.runCheckImport([sample_name])

        sample_uri = common.get_sample_uri(sample_name)
        asset = GES.UriClipAsset.request_sync(sample_uri)

        thumb_cache = ThumbnailCache.get(asset)
        width, height = thumb_cache.getImagesSize()
        self.assertEqual(height, THUMB_HEIGHT)
        self.assertTrue(thumb_cache[0] is not None)
        self.assertTrue(thumb_cache[Gst.SECOND / 2] is not None)

        wavefile = get_wavefile_location_for_uri(sample_uri)
        self.assertTrue(os.path.exists(wavefile), wavefile)

        with open(wavefile, "rb") as fsamples:
            samples = pickle.load(fsamples)

        self.assertTrue(bool(samples))


class TestThumbnailCache(TestCase):

    def test_get(self):
        with self.assertRaises(ValueError):
            ThumbnailCache.get(1)
        with mock.patch("pitivi.timeline.previewers.xdg_cache_home") as xdg_config_home,\
                tempfile.TemporaryDirectory() as temp_dir:
            xdg_config_home.return_value = temp_dir
            sample_uri = common.get_sample_uri("1sec_simpsons_trailer.mp4")
            cache = ThumbnailCache.get(sample_uri)
            self.assertIsNotNone(cache)

            asset = GES.UriClipAsset.request_sync(sample_uri)
            self.assertEqual(ThumbnailCache.get(asset), cache)
