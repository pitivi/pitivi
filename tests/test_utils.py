#!/usr/bin/python3
# Pitivi video editor
#
#       test_utils.py
#
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

from gi.repository import Gst

from pitivi.check import *  # noqa
from pitivi.utils.ui import beautify_length

second = Gst.SECOND
minute = second * 60
hour = minute * 60


class TestBeautifyLength(TestCase):

    def testBeautifySeconds(self):
        self.assertEqual(beautify_length(second), "1 second")
        self.assertEqual(beautify_length(second * 2), "2 seconds")

    def testBeautifyMinutes(self):
        self.assertEqual(beautify_length(minute), "1 minute")
        self.assertEqual(beautify_length(minute * 2), "2 minutes")

    def testBeautifyHours(self):
        self.assertEqual(beautify_length(hour), "1 hour")
        self.assertEqual(beautify_length(hour * 2), "2 hours")

    def testBeautifyMinutesAndSeconds(self):
        self.assertEqual(beautify_length(minute + second),
                         "1 minute, 1 second")

    def testBeautifyHoursAndMinutes(self):
        self.assertEqual(beautify_length(hour + minute + second),
                         "1 hour, 1 minute")


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
