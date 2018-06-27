# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2009, Alessandro Decina <alessandro.decina@collabora.co.uk>
# Copyright (c) 2014, Mathieu Duponchelle <mduponchelle1@gmail.com>
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
import time
from gettext import gettext as _
from unittest import TestCase
from unittest.mock import Mock

from gi.repository import GLib
from gi.repository import Gst
from gi.repository import GstPbutils

from pitivi.check import CairoDependency
from pitivi.check import ClassicDependency
from pitivi.check import GstDependency
from pitivi.check import GtkDependency
from pitivi.utils.misc import fixate_caps_with_default_values
from pitivi.utils.ui import beautify_last_updated_timestamp
from pitivi.utils.ui import beautify_length
from pitivi.utils.ui import format_audiochannels
from pitivi.utils.ui import format_audiorate
from pitivi.utils.ui import format_framerate_value

second = Gst.SECOND
minute = second * 60
hour = minute * 60


class TestBeautifyTime(TestCase):
    """Tests time beautifying utility methods."""

    def test_beautify_length(self):
        """Tests beautification of time duration."""
        self.assertEqual(beautify_length(second), "1 second")
        self.assertEqual(beautify_length(second * 2), "2 seconds")

        self.assertEqual(beautify_length(minute), "1 minute")
        self.assertEqual(beautify_length(minute * 2), "2 minutes")

        self.assertEqual(beautify_length(hour), "1 hour")
        self.assertEqual(beautify_length(hour * 2), "2 hours")

        self.assertEqual(beautify_length(minute + second), "1 minute, 1 second")
        self.assertEqual(beautify_length(hour + minute + second), "1 hour, 1 minute")
        self.assertEqual(beautify_length(Gst.CLOCK_TIME_NONE), "")

    def test_beautify_last_updated_timestamp(self):
        """Tests beautification of project's updation timestamp."""
        now = time.time()
        self.assertEqual(beautify_last_updated_timestamp(now - 60 * 10), "Just now")
        self.assertEqual(beautify_last_updated_timestamp(now - 60 * 60), "An hour ago")
        self.assertEqual(beautify_last_updated_timestamp(now - 60 * 60 * 10), "Today")
        self.assertEqual(beautify_last_updated_timestamp(now - 60 * 60 * 36), "Yesterday")
        self.assertEqual(beautify_last_updated_timestamp(now - 60 * 60 * 24 * 3),
                         "%s" % ((time.strftime("%A", time.localtime(now - 60 * 60 * 24 * 3)))))
        self.assertEqual(beautify_last_updated_timestamp(now - 60 * 60 * 24 * 10),
                         "%s" % ((time.strftime("%B", time.localtime(now - 60 * 60 * 24 * 10)))))
        self.assertEqual(beautify_last_updated_timestamp(now - 60 * 60 * 24 * 365 * 1.2), "About a year ago")
        self.assertEqual(beautify_last_updated_timestamp(now - 60 * 60 * 24 * 365 * 2), "About 2 years ago")


class TestFormatFramerateValue(TestCase):

    def __check(self, num, denom, expected):
        stream = Mock(spec=GstPbutils.DiscovererVideoInfo)
        fraction = Mock(num=num, denom=denom)

        stream.get_framerate_num = Mock(return_value=num)
        stream.get_framerate_denom = Mock(return_value=denom)

        self.assertEqual(format_framerate_value(stream), expected)
        self.assertEqual(format_framerate_value(fraction), expected)

    def test_invalid_fps(self):
        self.__check(0, 1, "0")
        self.__check(0, 0, "0")
        self.__check(1, 0, "0")

    def test_int_fps(self):
        self.__check(1, 1, "1")
        self.__check(24, 1, "24")

    def test_float_fps(self):
        self.__check(24000, 1001, "23.976")
        self.__check(30000, 1001, "29.97")
        self.__check(60000, 1001, "59.94")

    def test_high_fps(self):
        self.__check(2500, 1, "2,500")
        self.__check(120, 1, "120")


class TestFormatAudiorate(TestCase):

    def __check(self, rate, expected):
        stream = Mock(spec=GstPbutils.DiscovererAudioInfo)
        stream.get_sample_rate = Mock(return_value=rate)

        self.assertEqual(format_audiorate(stream), expected)
        self.assertEqual(format_audiorate(rate), expected)

    def test_audiorates(self):
        self.__check(8000, "8 kHz")
        self.__check(11025, "11 kHz")
        self.__check(22050, "22 kHz")
        self.__check(44100, "44.1 kHz")
        self.__check(96000, "96 kHz")
        self.__check(960000, "960 kHz")


class TestFormatAudiochannels(TestCase):

    def __check(self, channels, expected):
        stream = Mock(spec=GstPbutils.DiscovererAudioInfo)
        stream.get_channels = Mock(return_value=channels)

        self.assertEqual(format_audiochannels(stream), expected)
        self.assertEqual(format_audiochannels(channels), expected)

    def test_audiochannels(self):
        self.__check(1, "Mono")
        self.__check(2, "Stereo")
        self.__check(6, "6 (5.1)")


class TestDependencyChecks(TestCase):

    def testDependencies(self):
        gi_dep = GstDependency("Gst", "1.0", "1.0.0")
        gi_dep.check()
        self.assertTrue(gi_dep.satisfied)

        gi_dep = GstDependency("Gst", "1.0", "9.9.9")
        gi_dep.check()
        self.assertFalse(gi_dep.satisfied)

        gi_dep = GstDependency("ThisShouldNotExist", None)
        gi_dep.check()
        self.assertFalse(gi_dep.satisfied)

        gi_dep = GtkDependency("Gtk", "3.0", "3.0.0")
        gi_dep.check()
        self.assertTrue(gi_dep.satisfied)

        gi_dep = GtkDependency("Gtk", "3.0", "9.9.9")
        gi_dep.check()
        self.assertFalse(gi_dep.satisfied)

        cairo_dep = CairoDependency("1.0.0")
        cairo_dep.check()
        self.assertTrue(cairo_dep.satisfied)

        cairo_dep = CairoDependency("9.9.9")
        cairo_dep.check()
        self.assertFalse(cairo_dep.satisfied)

        classic_dep = ClassicDependency("numpy", None)
        classic_dep.check()
        self.assertTrue(classic_dep.satisfied)


class TestMiscUtils(TestCase):

    def test_fixate_caps_with_defalt_values(self):
        voaacenc_caps = Gst.Caps.from_string(
            "audio/x-raw, format=(string)S16LE, layout=(string)interleaved, rate=(int){ 8000, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000, 64000, 88200, 96000 }, channels=(int)1;"
            "audio/x-raw, format=(string)S16LE, layout=(string)interleaved, rate=(int){ 8000, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000, 64000, 88200, 96000 }, channels=(int)2, channel-mask=(bitmask)0x0000000000000003")
        yt_audiorest = Gst.Caps("audio/x-raw,channels=6,channel-mask=0x3f,rate={48000,96000};"
            "audio/x-raw,channels=2,rate={48000,96000}")

        vorbis_caps = Gst.Caps("audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)[ 1, 200000 ], channels=(int)1;"
                               "audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)[ 1, 200000 ], channels=(int)2, channel-mask=(bitmask)0x0000000000000003;"
                               "audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)[ 1, 200000 ], channels=(int)3, channel-mask=(bitmask)0x0000000000000007;"
                               "audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)[ 1, 200000 ], channels=(int)4, channel-mask=(bitmask)0x0000000000000033;"
                               "audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)[ 1, 200000 ], channels=(int)5, channel-mask=(bitmask)0x0000000000000037;"
                               "audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)[ 1, 200000 ], channels=(int)6, channel-mask=(bitmask)0x000000000000003f;"
                               "audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)[ 1, 200000 ], channels=(int)7, channel-mask=(bitmask)0x0000000000000d0f;"
                               "audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)[ 1, 200000 ], channels=(int)8, channel-mask=(bitmask)0x0000000000000c3f;"
                               "audio/x-raw, format=(string)F32LE, layout=(string)interleaved, rate=(int)[ 1, 200000 ], channels=(int)[ 9, 255 ], channel-mask=(bitmask)0x0000000000000000")

        avenc_ac3_caps = Gst.Caps("audio/x-raw, channel-mask=(bitmask)0x0000000000000000, channels=(int)1, rate=(int){ 48000, 44100, 32000 }, layout=(string)interleaved, format=(string)F32LE;"
                " audio/x-raw, channel-mask=(bitmask)0x0000000000000003, channels=(int)2, rate=(int){ 48000, 44100, 32000 }, layout=(string)interleaved, format=(string)F32LE;"
                " audio/x-raw, channel-mask=(bitmask)0x0000000000000103, channels=(int)3, rate=(int){ 48000, 44100, 32000 }, layout=(string)interleaved, format=(string)F32LE;"
                " audio/x-raw, channel-mask=(bitmask)0x0000000000000007, channels=(int)3, rate=(int){ 48000, 44100, 32000 }, layout=(string)interleaved, format=(string)F32LE;"
                " audio/x-raw, channel-mask=(bitmask)0x0000000000000c03, channels=(int)4, rate=(int){ 48000, 44100, 32000 }, layout=(string)interleaved, format=(string)F32LE;"
                " audio/x-raw, channel-mask=(bitmask)0x0000000000000033, channels=(int)4, rate=(int){ 48000, 44100, 32000 }, layout=(string)interleaved, format=(string)F32LE;"
                " audio/x-raw, channel-mask=(bitmask)0x0000000000000107, channels=(int)4, rate=(int){ 48000, 44100, 32000 }, layout=(string)interleaved, format=(string)F32LE;"
                " audio/x-raw, channel-mask=(bitmask)0x0000000000000c07, channels=(int)5, rate=(int){ 48000, 44100, 32000 }, layout=(string)interleaved, format=(string)F32LE;"
                " audio/x-raw, channel-mask=(bitmask)0x0000000000000037, channels=(int)5, rate=(int){ 48000, 44100, 32000 }, layout=(string)interleaved, format=(string)F32LE;"
                " audio/x-raw, channel-mask=(bitmask)0x000000000000000c, channels=(int)2, rate=(int){ 48000, 44100, 32000 }, layout=(string)interleaved, format=(string)F32LE;"
                " audio/x-raw, channel-mask=(bitmask)0x000000000000000b, channels=(int)3, rate=(int){ 48000, 44100, 32000 }, layout=(string)interleaved, format=(string)F32LE;"
                " audio/x-raw, channel-mask=(bitmask)0x000000000000010b, channels=(int)4, rate=(int){ 48000, 44100, 32000 }, layout=(string)interleaved, format=(string)F32LE;"
                " audio/x-raw, channel-mask=(bitmask)0x000000000000000f, channels=(int)4, rate=(int){ 48000, 44100, 32000 }, layout=(string)interleaved, format=(string)F32LE;"
                " audio/x-raw, channel-mask=(bitmask)0x0000000000000c0b, channels=(int)5, rate=(int){ 48000, 44100, 32000 }, layout=(string)interleaved, format=(string)F32LE;"
                " audio/x-raw, channel-mask=(bitmask)0x000000000000003b, channels=(int)5, rate=(int){ 48000, 44100, 32000 }, layout=(string)interleaved, format=(string)F32LE;"
                " audio/x-raw, channel-mask=(bitmask)0x000000000000010f, channels=(int)5, rate=(int){ 48000, 44100, 32000 }, layout=(string)interleaved, format=(string)F32LE;"
                " audio/x-raw, channel-mask=(bitmask)0x0000000000000c0f, channels=(int)6, rate=(int){ 48000, 44100, 32000 }, layout=(string)interleaved, format=(string)F32LE;"
                " audio/x-raw, channel-mask=(bitmask)0x000000000000003f, channels=(int)6, rate=(int){ 48000, 44100, 32000 }, layout=(string)interleaved, format=(string)F32LE;")

        audio_defaults = {"channels": Gst.IntRange(range(1, 2147483647)),
                          "rate": Gst.IntRange(range(8000, GLib.MAXINT))}

        dataset = [
            (voaacenc_caps, yt_audiorest, audio_defaults, None, Gst.Caps("audio/x-raw, channels=2,rate=48000,channel-mask=(bitmask)0x03")),
            (vorbis_caps, None, audio_defaults, None, Gst.Caps("audio/x-raw,channels=1,rate=8000")),
            (avenc_ac3_caps, None, audio_defaults, Gst.Caps("audio/x-raw, channels=(int)6, rate=(int)44100"), Gst.Caps("audio/x-raw, channels=(int)6, rate=(int)44100")),
        ]

        for template, restrictions, default_values, prev_vals, expected in dataset:
            res = fixate_caps_with_default_values(template, restrictions, default_values, prev_vals)
            self.assertTrue(res.is_equal_fixed(expected), "%s != %s" % (res, expected))
