# -*- coding: utf-8 -*-
#
# Copyright (c) 2013, Alex Băluț <alexandru.balut@gmail.com>
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
import tempfile

from unittest import TestCase

from gi.repository import GES
from gi.repository import GLib

from pitivi.project import Project


class TestProjectLoading(TestCase):

    def setUp(self):
        self.mainloop = GLib.MainLoop()

    def tearDown(self):
        pass

    def testLoadedCallback(self):
        def loaded(project, timeline, mainloop, result):
            result[0] = True
            mainloop.quit()

        def quit(mainloop):
            mainloop.quit()

        # Create a blank project and save it.
        project = Project("noname")
        result = [False]
        project.connect("loaded", loaded, self.mainloop, result)

        self.assertTrue(project.createTimeline())
        GLib.timeout_add_seconds(5, quit, self.mainloop)
        self.mainloop.run()
        self.assertTrue(result[0], "Blank project creation failed to trigger signal: loaded")

        # Load the blank project and make sure "loaded" is triggered.
        unused, xges_path = tempfile.mkstemp()
        uri = "file://%s" % xges_path
        try:
            project.save(project.timeline, uri, None, overwrite=True)

            project2 = Project(uri=uri)
            self.assertTrue(project2.createTimeline())
            result = [False]
            project2.connect("loaded", loaded, self.mainloop, result)
            GLib.timeout_add_seconds(5, quit, self.mainloop)
            self.mainloop.run()
            self.assertTrue(result[0], "Blank project loading failed to trigger signal: loaded")
        finally:
            os.remove(xges_path)

    def testAssetAddingRemovingAdding(self):
        def loaded(project, timeline, mainloop, result, uris):
            result[0] = True
            project.addUris(uris)

        def added(project, mainloop, result, uris):
            result[1] = True
            assets = project.list_assets(GES.UriClip)
            asset = assets[0]
            project.remove_asset(asset)
            GLib.idle_add(readd, mainloop, result, uris)

        def readd(mainloop, result, uris):
            project.addUris(uris)
            result[2] = True
            mainloop.quit()

        def quit(mainloop):
            mainloop.quit()

        # Create a blank project and save it.
        project = Project("noname")
        result = [False, False, False]
        uris = ["file://%s/samples/tears of steel.webm" % os.path.abspath(".")]
        project.connect("loaded", loaded, self.mainloop, result, uris)
        project.connect("done-importing", added, self.mainloop, result, uris)

        self.assertTrue(project.createTimeline())
        GLib.timeout_add_seconds(5, quit, self.mainloop)
        self.mainloop.run()
        self.assertTrue(result[0], "Project creation failed to trigger signal: loaded")
        self.assertTrue(result[1], "Asset add failed to trigger signal: done-importing")
        self.assertTrue(result[2], "Asset re-adding failed")


class TestExportSettings(TestCase):
    """Test the project.MultimediaSettings class."""

    def setUp(self):
        self.project = Project()

    def testMasterAttributes(self):
        self._testMasterAttribute('muxer', dependant_attr='containersettings')
        self._testMasterAttribute('vencoder', dependant_attr='vcodecsettings')
        self._testMasterAttribute('aencoder', dependant_attr='acodecsettings')

    def _testMasterAttribute(self, attr, dependant_attr):
        """Test changing the specified attr has effect on its dependant attr."""
        attr_value1 = "%s_value1" % attr
        attr_value2 = "%s_value2" % attr

        setattr(self.project, attr, attr_value1)
        setattr(self.project, dependant_attr, {})
        getattr(self.project, dependant_attr)["key1"] = "v1"

        setattr(self.project, attr, attr_value2)
        setattr(self.project, dependant_attr, {})
        getattr(self.project, dependant_attr)["key2"] = "v2"

        setattr(self.project, attr, attr_value1)
        self.assertTrue("key1" in getattr(self.project, dependant_attr))
        self.assertFalse("key2" in getattr(self.project, dependant_attr))
        self.assertEqual("v1", getattr(self.project, dependant_attr)["key1"])
        setattr(self.project, dependant_attr, {})

        setattr(self.project, attr, attr_value2)
        self.assertFalse("key1" in getattr(self.project, dependant_attr))
        self.assertTrue("key2" in getattr(self.project, dependant_attr))
        self.assertEqual("v2", getattr(self.project, dependant_attr)["key2"])
        setattr(self.project, dependant_attr, {})

        setattr(self.project, attr, attr_value1)
        self.assertFalse("key1" in getattr(self.project, dependant_attr))
        self.assertFalse("key2" in getattr(self.project, dependant_attr))

        setattr(self.project, attr, attr_value2)
        self.assertFalse("key1" in getattr(self.project, dependant_attr))
        self.assertFalse("key2" in getattr(self.project, dependant_attr))
