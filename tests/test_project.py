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
        self.assertTrue(project.createTimeline())
        result = [False]
        project.connect("loaded", loaded, self.mainloop, result)
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
