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
    1.0000000180025155e-33, 1.0000000180025155e-33, 9.466735608724685e-05,
    0.0016802854651403348, 0.2298099638424507, 2.3616320439402143, 4.049185439556839,
    3.284195196383849, 4.05835985413913, 4.586676466667793, 4.940914967594509,
    3.5891955340346477, 2.2974444692377567, 1.5337796548101932, 3.015340518747337,
    4.402133429862438, 4.773357722910441, 4.779009324079252, 4.655537541962497,
    4.543942909514233, 4.9320770351156735, 3.7114167237366957, 2.6811979044348884,
    5.377787572575852, 5.136230693687676, 5.419229650541714, 5.35647659134891,
    4.5933491070305665, 5.460428009340401, 4.645073622414212, 4.378695790226624,
    5.259486582101626, 4.5281589368036546, 5.265094016436164, 5.00708854897167,
    4.513459848980695, 3.792516292044058, 3.836904642287806, 4.531396212120468,
    5.362651864191655, 5.408963618250316, 5.120883787773891, 4.934966728544448,
    6.175705535014139, 5.444842919425695, 4.957031005987477, 5.53745374776641,
    5.580341542054587, 4.611911374969583, 4.845084505605837, 5.450476172859177,
    5.7348769111251405, 4.443313266936532, 4.367055669701466, 3.9572188728697317,
    3.305387555242148, 4.614435114384071, 3.5434378665402257, 4.452167697134032,
    3.3425208440888636, 3.5801852530575835]


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

        samples = list(range(99))
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
