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
"""Tests for the timeline.previewers module."""
# pylint: disable=protected-access
import os
import tempfile
from unittest import mock

import numpy
from gi.repository import GdkPixbuf
from gi.repository import GES
from gi.repository import Gst

from pitivi.timeline.previewers import get_wavefile_location_for_uri
from pitivi.timeline.previewers import THUMB_HEIGHT
from pitivi.timeline.previewers import ThumbnailCache
from tests import common
from tests.test_media_library import BaseTestMediaLibrary


SIMPSON_WAVFORM_VALUES = [
    0.10277689599093834, 0.50788916706114862, 0.91300143813135892, 1.3181137092015693,
    1.7232259802717795, 2.1283382513419897, 2.5334505224121999, 2.9385627934824101,
    3.3436750645526203, 3.7487873356228305, 3.748787335622831, 3.6974645491239455,
    3.6461417626250601, 3.5948189761261746, 3.5434961896272892, 3.4921734031284037,
    3.4408506166295183, 3.3895278301306329, 3.3382050436317474, 3.286882257132862,
    3.2868822571328606, 3.4364524655420996, 3.5860226739513386, 3.7355928823605775,
    3.8851630907698165, 4.034733299179055, 4.1843035075882939, 4.3338737159975329,
    4.4834439244067719, 4.6330141328160108, 4.6330141328160108, 4.6166031969548991,
    4.6001922610937873, 4.5837813252326756, 4.5673703893715638, 4.5509594535104521,
    4.5345485176493403, 4.5181375817882286, 4.5017266459271168, 4.485315710066005,
    4.4853157100660033, 4.5547060070202106, 4.6240963039744178, 4.6934866009286251,
    4.7628768978828324, 4.8322671948370397, 4.901657491791247, 4.9710477887454543,
    5.0404380856996616, 5.1098283826538689, 5.109828382653868, 5.0866990072166436,
    5.0635696317794192, 5.0404402563421948, 5.0173108809049705, 4.9941815054677461,
    4.9710521300305217, 4.9479227545932973, 4.924793379156073, 4.9016640037188486,
    4.901664003718845, 4.8508680589687616, 4.8000721142186782, 4.7492761694685948,
    4.6984802247185113, 4.6476842799684279, 4.5968883352183445, 4.5460923904682611,
    4.4952964457181777, 4.4445005009680942, 4.4445005009680925, 4.5544001248210364,
    4.6642997486739803, 4.7741993725269243, 4.8840989963798682, 4.9939986202328122,
    5.1038982440857561, 5.2137978679387, 5.323697491791644, 5.4335971156445879,
    5.433597115644587, 5.3988578703107724, 5.3641186249769577, 5.329379379643143,
    5.2946401343093283, 5.2599008889755137, 5.225161643641699, 5.1904223983078843,
    5.1556831529740696, 5.120943907640255, 5.120943907640255, 5.0895954243424724,
    5.0582469410446897, 5.0268984577469071, 4.9955499744491245, 4.9642014911513419,
    4.9328530078535593, 4.9015045245557767, 4.8701560412579941, 4.8388075579602114,
    4.8388075579602079, 4.7336937056290518, 4.6285798532978957, 4.5234660009667396,
    4.4183521486355835, 4.3132382963044273, 4.2081244439732712, 4.1030105916421151,
    3.9978967393109586, 3.892782886979802, 3.8927828869797994, 3.8630968485705619,
    3.8334108101613245, 3.803724771752087, 3.7740387333428496, 3.7443526949336121,
    3.7146666565243747, 3.6849806181151372, 3.6552945797058998, 3.6256085412966623,
    3.6256085412966614, 0.0]


class TestAudioPreviewer(BaseTestMediaLibrary):
    """Tests for the `AudioPreviewer` class."""

    def test_create_thumbnail_bin(self):
        """Checks our `waveformbin` element is usable."""
        pipeline = Gst.parse_launch("uridecodebin name=decode uri=file:///some/thing"
                                    " waveformbin name=wavebin ! fakesink qos=false name=faked")
        self.assertTrue(pipeline)
        wavebin = pipeline.get_by_name("wavebin")
        self.assertTrue(wavebin)

    def test_waveform_creation(self):
        """Checks the waveform generation."""
        sample_name = "1sec_simpsons_trailer.mp4"
        self.runCheckImport([sample_name])

        sample_uri = common.get_sample_uri(sample_name)
        wavefile = get_wavefile_location_for_uri(sample_uri)
        self.assertTrue(os.path.exists(wavefile), wavefile)

        with open(wavefile, "rb") as fsamples:
            samples = list(numpy.load(fsamples))

        self.assertEqual(samples, SIMPSON_WAVFORM_VALUES)


class TestThumbnailCache(BaseTestMediaLibrary):
    """Tests for the ThumbnailCache class."""

    def test_get(self):
        """Checks the `get` method returns the same thing for asset and URI."""
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

    def test_image_size(self):
        """Checks the `image_size` property."""
        with tempfile.TemporaryDirectory() as tmpdirname:
            with mock.patch("pitivi.timeline.previewers.xdg_cache_home") as xdg_cache_home:
                xdg_cache_home.return_value = tmpdirname
                sample_uri = common.get_sample_uri("1sec_simpsons_trailer.mp4")
                thumb_cache = ThumbnailCache(sample_uri)
                self.assertEqual(thumb_cache.image_size, (None, None))

                pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,
                                              False, 8, 20, 10)
                thumb_cache[0] = pixbuf
                self.assertEqual(thumb_cache.image_size, (20, 10))

    def test_containment(self):
        """Checks the __contains/getitem/setitem__ methods."""
        with tempfile.TemporaryDirectory() as tmpdirname:
            with mock.patch("pitivi.timeline.previewers.xdg_cache_home") as xdg_cache_home:
                xdg_cache_home.return_value = tmpdirname
                sample_uri = common.get_sample_uri("1sec_simpsons_trailer.mp4")
                thumb_cache = ThumbnailCache(sample_uri)
                self.assertFalse(Gst.SECOND in thumb_cache)
                with self.assertRaises(KeyError):
                    # pylint: disable=pointless-statement
                    thumb_cache[Gst.SECOND]

                pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB,
                                              False, 8,
                                              int(THUMB_HEIGHT * 1280 / 544), THUMB_HEIGHT)
                thumb_cache[Gst.SECOND] = pixbuf
                self.assertTrue(Gst.SECOND in thumb_cache)
                self.assertIsNotNone(thumb_cache[Gst.SECOND])
                thumb_cache.commit()

                thumb_cache = ThumbnailCache(sample_uri)
                self.assertTrue(Gst.SECOND in thumb_cache)
                self.assertIsNotNone(thumb_cache[Gst.SECOND])
