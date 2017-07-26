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
from unittest import TestCase

from gi.repository import GLib
from gi.repository import Gst

from pitivi.check import CairoDependency
from pitivi.check import ClassicDependency
from pitivi.check import GstDependency
from pitivi.check import GtkDependency
from pitivi.utils.misc import fixate_caps_with_default_values
from pitivi.utils.ui import beautify_length

second = Gst.SECOND
minute = second * 60
hour = minute * 60


class TestBeautifyLength(TestCase):

    def test_beautify_seconds(self):
        self.assertEqual(beautify_length(second), "1 second")
        self.assertEqual(beautify_length(second * 2), "2 seconds")

    def test_beautify_minutes(self):
        self.assertEqual(beautify_length(minute), "1 minute")
        self.assertEqual(beautify_length(minute * 2), "2 minutes")

    def test_beautify_hours(self):
        self.assertEqual(beautify_length(hour), "1 hour")
        self.assertEqual(beautify_length(hour * 2), "2 hours")

    def test_beautify_minutes_and_seconds(self):
        self.assertEqual(beautify_length(minute + second),
                         "1 minute, 1 second")

    def test_beautify_hours_and_minutes(self):
        self.assertEqual(beautify_length(hour + minute + second),
                         "1 hour, 1 minute")

    def test_beautify_nothing(self):
        self.assertEqual(beautify_length(Gst.CLOCK_TIME_NONE), "")


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

        audio_defaults = {'channels': Gst.IntRange(range(1, 2147483647)),
                          "rate": Gst.IntRange(range(8000, GLib.MAXINT))}

        dataset = [
            (voaacenc_caps, yt_audiorest, audio_defaults, None, Gst.Caps("audio/x-raw, channels=2,rate=48000,channel-mask=(bitmask)0x03")),
            (vorbis_caps, None, audio_defaults, Gst.Caps('audio/x-raw,channels=1,rate=8000'))
        ]

        for data in dataset:
            res = fixate_caps_with_default_values(*data[:-1])
            print(res)
            self.assertTrue(res.is_equal_fixed(data[-1]), "%s != %s" % (res, data[-1]))
