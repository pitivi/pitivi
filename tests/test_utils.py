#!/usr/bin/python2
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
from pitivi.utils.ui import beautify_length
from pitivi.check import *

second = Gst.SECOND
minute = second * 60
hour = minute * 60


class TestBeautifyLength(TestCase):
    def testBeautifySeconds(self):
        self.failUnlessEqual(beautify_length(second), "1 second")
        self.failUnlessEqual(beautify_length(second * 2), "2 seconds")

    def testBeautifyMinutes(self):
        self.failUnlessEqual(beautify_length(minute), "1 minute")
        self.failUnlessEqual(beautify_length(minute * 2), "2 minutes")

    def testBeautifyHours(self):
        self.failUnlessEqual(beautify_length(hour), "1 hour")
        self.failUnlessEqual(beautify_length(hour * 2), "2 hours")

    def testBeautifyMinutesAndSeconds(self):
        self.failUnlessEqual(beautify_length(minute + second),
                "1 minute, 1 second")

    def testBeautifyHoursAndMinutes(self):
        self.failUnlessEqual(beautify_length(hour + minute + second),
                "1 hour, 1 minute")


class TestDependencyChecks(TestCase):
    def testDependencies(self):
        gi_dep = GstDependency("Gst", "1.0.0")
        gi_dep.check()
        self.failUnless(gi_dep.satisfied)

        gi_dep = GstDependency("Gst", "9.9.9")
        gi_dep.check()
        self.failIf(gi_dep.satisfied)

        gi_dep = GstDependency("ThisShouldNotExist", None)
        gi_dep.check()
        self.failIf(gi_dep.satisfied)

        gi_dep = GtkOrClutterDependency("Gtk", "3.0.0")
        gi_dep.check()
        self.failUnless(gi_dep.satisfied)

        gi_dep = GtkOrClutterDependency("Gtk", "9.9.9")
        gi_dep.check()
        self.failIf(gi_dep.satisfied)

        cairo_dep = CairoDependency("1.0.0")
        cairo_dep.check()
        self.failUnless(cairo_dep.satisfied)

        cairo_dep = CairoDependency("9.9.9")
        cairo_dep.check()
        self.failIf(cairo_dep.satisfied)

        classic_dep = ClassicDependency("numpy", None)
        classic_dep.check()
        self.failUnless(classic_dep.satisfied)

        gst_plugin_dep = GstPluginDependency("gnonlin", "1.1.90")
        gst_plugin_dep.check()
        self.failUnless(gst_plugin_dep.satisfied)

        gst_plugin_dep = GstPluginDependency("gnonlin", "9.9.9")
        gst_plugin_dep.check()
        self.failIf(gst_plugin_dep.satisfied)
