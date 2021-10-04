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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
"""Tests for the timeline.previewers module."""
# pylint: disable=protected-access,unused-argument
import functools
import os
import tempfile
from unittest import mock

import numpy
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GES
from gi.repository import Gst

from pitivi.timeline.previewers import delete_all_files_in_dir
from pitivi.timeline.previewers import get_wavefile_location_for_uri
from pitivi.timeline.previewers import Previewer
from pitivi.timeline.previewers import THUMB_HEIGHT
from pitivi.timeline.previewers import THUMB_PERIOD
from pitivi.timeline.previewers import ThumbnailCache
from pitivi.utils.timeline import EditingContext
from pitivi.utils.timeline import Zoomable
from tests import common
from tests.test_medialibrary import BaseTestMediaLibrary


SIMPSON_WAVFORM_VALUES = [
    0.10277689604421922, 0.5078891671078481, 0.913001438171477, 1.318113709235106,
    1.7232259802987349, 2.1283382513623637, 2.5334505224259924, 2.9385627934896212,
    3.34367506455325, 3.748787335616879, 3.7487873356168793, 3.697464549118655,
    3.646141762620431, 3.5948189761222067, 3.5434961896239825, 3.4921734031257583,
    3.440850616627534, 3.38952783012931, 3.3382050436310857, 3.2868822571328615,
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


class TestPreviewers(BaseTestMediaLibrary):

    def setup_trimmed_clips(self, frame_count):
        # Set the project videorate to match tears_of_steel.webm.
        self.project.videorate = Gst.Fraction(24, 1)
        Zoomable.set_zoom_level(78)

        timeline = self.timeline_container.timeline

        start_frame = 43
        start = self.timeline.get_frame_time(start_frame)
        self.assertEqual(start, 1791666667)

        clips = []
        starts = []
        asset = GES.UriClipAsset.request_sync(common.get_sample_uri("tears_of_steel.webm"))
        for delta_frame in range(frame_count):
            ges_layer = timeline.ges_timeline.append_layer()
            ges_clip = timeline.add_clip_to_layer(ges_layer, asset, start)

            editing_context = EditingContext(ges_clip, self.timeline, GES.EditMode.EDIT_TRIM, GES.Edge.EDGE_START, self.app)
            new_start = self.timeline.get_frame_time(start_frame + delta_frame)
            editing_context.edit_to(new_start, ges_layer)
            editing_context.finish()

            clips.append(ges_clip)
            starts.append(new_start)

        expected_starts = [1791666667, 1833333334, 1875000000, 1916666667, 1958333334, 2000000000, 2041666667, 2083333334, 2125000000, 2166666667,
                           2208333334, 2250000000, 2291666667, 2333333334, 2375000000, 2416666667, 2458333334, 2500000000, 2541666667, 2583333334,
                           2625000000, 2666666667, 2708333334, 2750000000, 2791666667, 2833333334, 2875000000, 2916666667, 2958333334, 3000000000,
                           3041666667, 3083333334, 3125000000, 3166666667, 3208333334, 3250000000, 3291666667, 3333333334, 3375000000, 3416666667,
                           3458333334, 3500000000, 3541666667, 3583333334, 3625000000, 3666666667, 3708333334, 3750000000][:frame_count]

        # Check we calculated correctly above where the clips should be placed.
        self.assertListEqual(starts, expected_starts)

        # Check the clips ended up exactly where we placed them.
        self.assertListEqual([c.start for c in clips], expected_starts,
                             "the clips have been placed in unexpected positions")

        expected_inpoints = [0, 41666667, 83333333, 125000000, 166666667, 208333333, 250000000, 291666667, 333333333, 375000000,
                             416666667, 458333333, 500000000, 541666667, 583333333, 625000000, 666666667, 708333333, 750000000, 791666667,
                             833333333, 875000000, 916666667, 958333333, 1000000000, 1041666667, 1083333333, 1125000000, 1166666667, 1208333333,
                             1250000000, 1291666667, 1333333333, 1375000000, 1416666667, 1458333333, 1500000000, 1541666667, 1583333333, 1625000000,
                             1666666667, 1708333333, 1750000000, 1791666667, 1833333333, 1875000000, 1916666667, 1958333333][:frame_count]
        self.assertListEqual([c.inpoint for c in clips], expected_inpoints)

        return clips


class TestVideoPreviewer(TestPreviewers):
    """Tests for the `VideoPreviewer` class."""

    @common.setup_timeline
    def test_thumbnails_position_quantization(self):
        clips = self.setup_trimmed_clips(48)

        # Check the video previewers.
        video_previewers = list(self.get_clip_element(c, GES.VideoSource).ui.previewer
                                for c in clips)

        mainloop = common.create_main_loop()

        # Acrobatics to run the mainloop until the pipelines of the previewers
        # are ready.
        updated_previewers = set()

        def update_thumbnails_func(previewer, original):
            nonlocal updated_previewers
            updated_previewers.add(previewer)

            # Restore the original method.
            previewer._update_thumbnails = original

            if set(updated_previewers) == set(video_previewers):
                mainloop.quit()

        for previewer in video_previewers:
            original = previewer._update_thumbnails
            previewer._update_thumbnails = functools.partial(update_thumbnails_func, previewer, original)

        mainloop.run()

        expected_queues = (
            [[0, 500000000, 1000000000, 1500000000]] * 12 +
            [[500000000, 1000000000, 1500000000]] * 12 +
            [[1000000000, 1500000000]] * 12 +
            [[1500000000]] * 12
        )

        expected_x_positions = (
            [[0, 237, 474, 712]] * 12 +
            [[0, 237, 474]] * 12 +
            [[0, 237]] * 12 +
            [[0]] * 12
        )

        for previewer, expected_queue, expected_xs in zip(video_previewers, expected_queues, expected_x_positions):
            self.assertEqual(previewer.thumb_width, 151)

            xs = []

            def move_put_func(thumb, x, y):
                # pylint: disable=cell-var-from-loop
                xs.append(x)

            previewer.move = move_put_func
            previewer.put = move_put_func
            try:
                previewer.refresh()
            finally:
                # These should not be called anymore.
                previewer.move = mock.Mock()
                previewer.put = mock.Mock()

            self.assertListEqual(previewer.queue, expected_queue)
            self.assertListEqual(xs, expected_xs)


class TestAudioPreviewer(TestPreviewers):
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
        with common.cloned_sample(sample_name):
            self.check_import([sample_name])

            sample_uri = common.get_sample_uri(sample_name)
            wavefile = get_wavefile_location_for_uri(sample_uri)

        self.assertTrue(os.path.exists(wavefile), wavefile)

        with open(wavefile, "rb") as fsamples:
            samples = list(numpy.load(fsamples))

        self.assertEqual(samples, SIMPSON_WAVFORM_VALUES)

    @common.setup_timeline
    def test_waveform_offset(self):
        clips = self.setup_trimmed_clips(10)

        # Check the audio previewers.
        audio_previewers = list(self.get_clip_element(c, GES.AudioSource).ui.previewer
                                for c in clips)

        offsets = []

        def set_source_surface(surface, offset_x, offset_y):
            offsets.append(offset_x)

        samples = list(range(199))
        for previewer in audio_previewers:
            previewer.samples = samples
            with mock.patch.object(Gdk, "cairo_get_clip_rectangle") as cairo_get_clip_rectangle:
                cairo_get_clip_rectangle.return_value = (True, mock.Mock(x=0, width=10000))
                from pitivi.timeline import previewers
                with mock.patch.object(previewers.renderer, "fill_surface") as fill_surface:
                    context = mock.Mock()
                    context.set_source_surface = set_source_surface
                    previewer.do_draw(context)
            fill_surface.assert_called_once_with(samples, 949, -1)

        expected_offsets = [0, -20, -40, -59, -79, -99, -119, -138, -158, -178]
        self.assertListEqual(offsets, expected_offsets)


class TestPreviewer(common.TestCase):
    """Tests for the `Previewer` class."""

    def test_thumb_interval(self):
        """Checks the `thumb_interval` method."""
        def run_thumb_interval(interval):
            """Runs thumb_interval."""
            with mock.patch("pitivi.utils.timeline.Zoomable.pixel_to_ns") as pixel_to_ns:
                pixel_to_ns.return_value = interval
                return Previewer.thumb_interval(1)

        self.assertEqual(run_thumb_interval(1), THUMB_PERIOD)
        self.assertEqual(run_thumb_interval(THUMB_PERIOD - 1), THUMB_PERIOD)
        self.assertEqual(run_thumb_interval(THUMB_PERIOD), THUMB_PERIOD)

        self.assertEqual(run_thumb_interval(THUMB_PERIOD + 1), 2 * THUMB_PERIOD)
        self.assertEqual(run_thumb_interval(2 * THUMB_PERIOD - 1), 2 * THUMB_PERIOD)
        self.assertEqual(run_thumb_interval(2 * THUMB_PERIOD), 2 * THUMB_PERIOD)


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
                self.assertEqual(thumb_cache.image_size, (0, 0))

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


class TestFunctions(BaseTestMediaLibrary):
    """Tests for the standalone functions."""

    def test_delete_all_files_in_dir(self):
        """Checks whether files in sub directories are deleted."""
        with tempfile.TemporaryDirectory() as dir_a, \
                tempfile.NamedTemporaryFile(dir=dir_a, delete=False), \
                tempfile.TemporaryDirectory(dir=dir_a) as dir_a_b, \
                tempfile.NamedTemporaryFile(dir=dir_a_b) as file_a_b1:
            self.assertEqual(len(os.listdir(dir_a)), 2)
            self.assertEqual(len(os.listdir(dir_a_b)), 1)
            delete_all_files_in_dir(dir_a)
            self.assertEqual(os.listdir(dir_a), [os.path.basename(dir_a_b)])
            self.assertEqual(os.listdir(dir_a_b), [os.path.basename(file_a_b1.name)])
