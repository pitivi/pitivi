# -*- coding: utf-8 -*-
#
# Copyright (c) 2009, Alessandro Decina <alessandro.d@gmail.com>
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
import time

from unittest import TestCase, mock
from gi.repository import GES
from gi.repository import GLib
from gi.repository import Gst

from pitivi.application import Pitivi
from pitivi.project import ProjectManager, Project
from pitivi.utils.misc import uri_is_reachable
from pitivi.utils.proxy import ProxyingStrategy

from tests import common


def _createRealProject(name=None):
    app = common.getPitiviMock(proxyingStrategy=ProxyingStrategy.NOTHING)
    project_manager = ProjectManager(app)
    project_manager.newBlankProject()
    project = project_manager.current_project
    if name:
        project.name = name
    return project


class MockProject(object):
    settings = None
    format = None
    uri = None
    has_mods = True

    def hasUnsavedModifications(self):
        return self.has_mods

    def release(self):
        pass

    def disconnect_by_function(self, ignored):
        pass

    def finalize(self):
        pass


class ProjectManagerListener(object):

    def __init__(self, manager):
        self.manager = manager
        self.connectToProjectManager(self.manager)
        self._reset()

    def _reset(self):
        self.signals = []

    def connectToProjectManager(self, manager):
        for signal in ("new-project-loading", "new-project-loaded",
                       "new-project-created", "new-project-failed", "missing-uri",
                       "closing-project", "project-closed"):
            self.manager.connect(signal, self._recordSignal, signal)

    def _recordSignal(self, *args):
        signal = args[-1]
        args = args[1:-1]
        self.signals.append((signal, args))

        return True


class TestProjectManager(TestCase):

    def setUp(self):
        app = mock.MagicMock()
        self.manager = ProjectManager(app)
        self.listener = ProjectManagerListener(self.manager)
        self.signals = self.listener.signals

    def testLoadProjectFailedUnknownFormat(self):
        """
        Check that new-project-failed is emitted when we don't have a suitable
        formatter.
        """
        uri = "file:///Untitled.meh"
        self.manager.loadProject(uri)

        # loading
        name, args = self.signals[0]
        self.assertEqual(uri, args[0], self.signals)

        # failed
        name, args = self.signals[1]
        self.assertEqual("new-project-failed", name)
        signalUri, unused_message = args
        self.assertEqual(uri, signalUri, self.signals)

    def testLoadProjectClosesCurrent(self):
        """
        Check that new-project-failed is emited if we can't close the current
        project instance.
        """
        state = {"tried-close": False}

        def close():
            state["tried-close"] = True
            return False
        self.manager.closeRunningProject = close

        uri = "file:///Untitled.xptv"
        self.manager.current_project = MockProject()
        self.manager.loadProject(uri)

        self.assertEqual(0, len(self.signals))
        self.assertTrue(state["tried-close"], self.signals)

    def testLoadProject(self):
        self.manager.newBlankProject()

        name, args = self.signals[0]
        self.assertEqual("new-project-loading", name, self.signals)

        name, args = self.signals[1]
        self.assertEqual("new-project-created", name, self.signals)

        name, args = self.signals[2]
        self.assertEqual("new-project-loaded", name, self.signals)

    def testMissingUriForwarded(self):
        def quit(mainloop):
            mainloop.quit()

        def missingUriCb(self, project, error, clip_asset, mainloop, result):
            print(project, error, clip_asset, mainloop, result)
            result[0] = True
            mainloop.quit()

        self.mainloop = GLib.MainLoop()

        result = [False]
        self.manager.connect(
            "missing-uri", missingUriCb, self.mainloop, result)

        # Load a project with a missing asset.
        unused, xges_path = tempfile.mkstemp()
        with open(xges_path, "w") as xges:
            xges.write("""<ges version='0.1'>
  <project>
    <ressources>
      <asset id='file:///icantpossiblyexist.png' extractable-type-name='GESUriClip' />
    </ressources>
    <timeline>
      <track caps='video/x-raw' track-type='4' track-id='0' />
      <layer priority='0'>
        <clip id='0' asset-id='file:///icantpossiblyexist.png' type-name='GESUriClip' layer-priority='0' track-types='4' start='0' duration='2590000000' inpoint='0' rate='0' />
      </layer>
    </timeline>
</project>
</ges>""")
        uri = "file://%s" % xges_path
        try:
            self.assertTrue(self.manager.loadProject(uri))

            GLib.timeout_add_seconds(5, quit, self.mainloop)
            self.mainloop.run()
            self.assertTrue(result[0], "missing not missing")
        finally:
            os.remove(xges_path)

    def testCloseRunningProjectNoProject(self):
        self.assertTrue(self.manager.closeRunningProject())
        self.assertFalse(self.signals)

    def testCloseRunningProjectRefuseFromSignal(self):
        def closing(manager, project):
            return False

        self.manager.current_project = MockProject()
        self.manager.current_project.uri = "file:///ciao"
        self.manager.connect("closing-project", closing)

        self.assertFalse(self.manager.closeRunningProject())
        self.assertEqual(1, len(self.signals))
        name, args = self.signals[0]
        self.assertEqual("closing-project", name)
        project = args[0]
        self.assertTrue(project is self.manager.current_project)

    def testCloseRunningProject(self):
        current = self.manager.current_project = MockProject()
        self.assertTrue(self.manager.closeRunningProject())
        self.assertEqual(2, len(self.signals))

        name, args = self.signals[0]
        self.assertEqual("closing-project", name)
        project = args[0]
        self.assertTrue(project is current)

        name, args = self.signals[1]
        self.assertEqual("project-closed", name)
        project = args[0]
        self.assertTrue(project is current)

        self.assertTrue(self.manager.current_project is None)

    def testNewBlankProjectCantCloseCurrent(self):
        def closing(manager, project):
            return False

        self.manager.current_project = MockProject()
        self.manager.current_project.uri = "file:///ciao"
        self.manager.connect("closing-project", closing)
        self.assertFalse(self.manager.newBlankProject())
        self.assertEqual(1, len(self.signals))
        signal, args = self.signals[0]
        self.assertEqual("closing-project", signal)

    def testNewBlankProject(self):
        self.assertTrue(self.manager.newBlankProject())
        self.assertEqual(3, len(self.signals))

        name, args = self.signals[0]
        self.assertEqual("new-project-loading", name)
        uri = args[0]
        self.assertTrue(uri is None)

        name, args = self.signals[1]
        self.assertEqual("new-project-created", name)
        project = args[0]
        self.assertEqual(uri, project.uri)

        name, args = self.signals[2]
        self.assertEqual("new-project-loaded", name)
        project = args[0]
        self.assertTrue(project is self.manager.current_project)

    def testSaveProject(self):
        self.assertTrue(self.manager.newBlankProject())

        unused, path = tempfile.mkstemp(suffix=".xges")
        unused, path2 = tempfile.mkstemp(suffix=".xges")
        try:
            uri = "file://" + os.path.abspath(path)
            uri2 = "file://" + os.path.abspath(path2)

            # Save the project.
            self.assertTrue(self.manager.saveProject(uri=uri, backup=False))
            self.assertTrue(uri_is_reachable(uri))

            # Wait a bit.
            time.sleep(0.1)

            # Save the project at a new location.
            self.assertTrue(self.manager.saveProject(uri2, backup=False))
            self.assertTrue(uri_is_reachable(uri2))

            # Make sure the old path and the new path have different mtimes.
            mtime = os.path.getmtime(path)
            mtime2 = os.path.getmtime(path2)
            self.assertLess(mtime, mtime2)

            # Wait a bit more.
            time.sleep(0.1)

            # Save project again under the new path (by omitting uri arg)
            self.assertTrue(self.manager.saveProject(backup=False))

            # regression test for bug 594396
            # make sure we didn't save to the old URI
            self.assertEqual(mtime, os.path.getmtime(path))
            # make sure we did save to the new URI
            self.assertLess(mtime2, os.path.getmtime(path2))
        finally:
            os.remove(path)
            os.remove(path2)

    def testMakeBackupUri(self):
        uri = "file:///tmp/x.xges"
        self.assertEqual(uri + "~", self.manager._makeBackupURI(uri))

    def testBackupProject(self):
        self.manager.newBlankProject()

        # Assign an uri to the project where it's saved by default.
        unused, xges_path = tempfile.mkstemp(suffix=".xges")
        uri = "file://" + os.path.abspath(xges_path)
        self.manager.current_project.uri = uri
        # This is where the automatic backup file is saved.
        backup_uri = self.manager._makeBackupURI(uri)

        # Save the backup
        self.assertTrue(self.manager.saveProject(
            self.manager.current_project, backup=True))
        self.assertTrue(uri_is_reachable(backup_uri))

        self.manager.closeRunningProject()
        self.assertFalse(uri_is_reachable(backup_uri),
                         "Backup file not deleted when project closed")


class TestProjectLoading(common.TestCase):

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
        project = _createRealProject(name="noname")
        result = [False]
        project.connect("loaded", loaded, self.mainloop, result)

        self.assertTrue(project.createTimeline())
        GLib.timeout_add_seconds(5, quit, self.mainloop)
        self.mainloop.run()
        self.assertTrue(
            result[0], "Blank project creation failed to trigger signal: loaded")

        # Load the blank project and make sure "loaded" is triggered.
        unused, xges_path = tempfile.mkstemp()
        uri = "file://%s" % xges_path
        try:
            project.save(project.timeline, uri, None, overwrite=True)

            project2 = _createRealProject()
            self.assertTrue(project2.createTimeline())
            result = [False]
            project2.connect("loaded", loaded, self.mainloop, result)
            GLib.timeout_add_seconds(5, quit, self.mainloop)
            self.mainloop.run()
            self.assertTrue(
                result[0], "Blank project loading failed to trigger signal: loaded")
        finally:
            os.remove(xges_path)

    def testAssetAddingRemovingAdding(self):
        def loadingProgressCb(project, progress, estimated_time,
                              self, result, uris):

            def readd(mainloop, result, uris):
                project.addUris(uris)
                result[2] = True
                mainloop.quit()

            if progress < 100:
                return

            result[1] = True
            assets = project.list_assets(GES.UriClip)
            self.assertEqual(len(assets), 1)
            asset = assets[0]
            project.remove_asset(asset)
            GLib.idle_add(readd, self.mainloop, result, uris)

        def loadedCb(project, timeline, mainloop, result, uris):
            result[0] = True
            project.addUris(uris)

        # Create a blank project and add an asset.
        project = _createRealProject()
        result = [False, False, False]
        uris = [common.getSampleUri("tears_of_steel.webm")]
        project.connect("loaded", loadedCb, self.mainloop, result, uris)
        project.connect("asset-loading-progress",
                        loadingProgressCb, self,
                        result, uris)

        def quit(mainloop):
            mainloop.quit()

        self.assertTrue(project.createTimeline())
        GLib.timeout_add_seconds(5, quit, self.mainloop)
        self.mainloop.run()
        self.assertTrue(
            result[0], "Project creation failed to trigger signal: loaded")
        self.assertTrue(
            result[1], "Asset add failed to trigger asset-loading-progress"
            "with progress == 100")
        self.assertTrue(result[2], "Asset re-adding failed")


class TestProjectSettings(common.TestCase):

    def setUp(self):
        self.mainloop = GLib.MainLoop()

    def tearDown(self):
        pass

    def testAudio(self):
        project = _createRealProject(name="noname")
        project.audiochannels = 2
        self.assertEqual(2, project.audiochannels)
        project.audiorate = 44100
        self.assertEqual(44100, project.audiorate)

    def testVideo(self):
        project = _createRealProject(name="noname")
        project.videowidth = 1920
        self.assertEqual(1920, project.videowidth)
        project.videoheight = 1080
        self.assertEqual(1080, project.videoheight)
        project.videorate = Gst.Fraction(50, 7)
        self.assertEqual(Gst.Fraction(50, 7), project.videorate)
        project.videopar = Gst.Fraction(2, 7)
        self.assertEqual(Gst.Fraction(2, 7), project.videopar)

    def testInitialization(self):
        def loadedCb(project, timeline, mainloop, uris):
            project.addUris(uris)

        def progressCb(project, progress, estimated_time, mainloop):
            if progress == 100:
                mainloop.quit()

        def quit(mainloop):
            mainloop.quit()

        # Create a blank project and add some assets.
        project = _createRealProject()
        self.assertTrue(project._has_default_video_settings)
        self.assertTrue(project._has_default_audio_settings)

        uris = [common.getSampleUri("flat_colour1_640x480.png"),
                common.getSampleUri("tears_of_steel.webm"),
                common.getSampleUri("1sec_simpsons_trailer.mp4")]
        project.connect("loaded", loadedCb, self.mainloop, uris)
        project.connect("asset-loading-progress", progressCb, self.mainloop)

        self.assertTrue(project.createTimeline())
        GLib.timeout_add_seconds(5, quit, self.mainloop)
        self.mainloop.run()

        assets = project.list_assets(GES.UriClip)
        self.assertEqual(3, len(assets), assets)

        self.assertFalse(project._has_default_video_settings)
        self.assertFalse(project._has_default_audio_settings)

        # The audio settings should match tears_of_steel.webm
        self.assertEqual(1, project.audiochannels)
        self.assertEqual(44100, project.audiorate)

        # The video settings should match tears_of_steel.webm
        self.assertEqual(960, project.videowidth)
        self.assertEqual(400, project.videoheight)
        self.assertEqual(Gst.Fraction(24, 1), project.videorate)
        self.assertEqual(Gst.Fraction(1, 1), project.videopar)

    def testLoad(self):
        ptv = common.getPitiviMock(proxyingStrategy=ProxyingStrategy.NOTHING)
        project = Project(uri="fake.xges", app=ptv)
        self.assertFalse(project._has_default_video_settings)
        self.assertFalse(project._has_default_audio_settings)


class TestExportSettings(TestCase):

    """Test the project.MultimediaSettings class."""

    def testMasterAttributes(self):
        self._testMasterAttribute('muxer', dependant_attr='containersettings')
        self._testMasterAttribute('vencoder', dependant_attr='vcodecsettings')
        self._testMasterAttribute('aencoder', dependant_attr='acodecsettings')

    def _testMasterAttribute(self, attr, dependant_attr):
        """Test changing the specified attr has effect on its dependant attr."""
        project = _createRealProject()

        attr_value1 = "%s_value1" % attr
        attr_value2 = "%s_value2" % attr

        setattr(project, attr, attr_value1)
        setattr(project, dependant_attr, {})
        getattr(project, dependant_attr)["key1"] = "v1"

        setattr(project, attr, attr_value2)
        setattr(project, dependant_attr, {})
        getattr(project, dependant_attr)["key2"] = "v2"

        setattr(project, attr, attr_value1)
        self.assertTrue("key1" in getattr(project, dependant_attr))
        self.assertFalse("key2" in getattr(project, dependant_attr))
        self.assertEqual("v1", getattr(project, dependant_attr)["key1"])
        setattr(project, dependant_attr, {})

        setattr(project, attr, attr_value2)
        self.assertFalse("key1" in getattr(project, dependant_attr))
        self.assertTrue("key2" in getattr(project, dependant_attr))
        self.assertEqual("v2", getattr(project, dependant_attr)["key2"])
        setattr(project, dependant_attr, {})

        setattr(project, attr, attr_value1)
        self.assertFalse("key1" in getattr(project, dependant_attr))
        self.assertFalse("key2" in getattr(project, dependant_attr))

        setattr(project, attr, attr_value2)
        self.assertFalse("key1" in getattr(project, dependant_attr))
        self.assertFalse("key2" in getattr(project, dependant_attr))
