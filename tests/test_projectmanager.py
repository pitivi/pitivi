# PiTiVi , Non-linear video editor
#
#       tests/test_projectmanager.py
#
# Copyright (c) 2009, Alessandro Decina <alessandro.d@gmail.com>
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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

from unittest import TestCase

from pitivi.projectmanager import ProjectManager
from pitivi.formatters.base import Formatter, \
        FormatterError, FormatterLoadError

class MockProject(object):
    def hasUnsavedModifications(self):
        return True

    def save(self):
        return True

    def release(self):
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
                "new-project-failed", "missing-uri", "closing-project",
                "project-closed"):
            self.manager.connect(signal, self._recordSignal, signal)

    def _recordSignal(self, *args):
        signal = args[-1]
        args = args[1:-1]
        self.signals.append((signal, args))

        return True


class TestProjectManager(TestCase):
    def setUp(self):
        self.manager = ProjectManager()
        self.listener = ProjectManagerListener(self.manager)
        self.signals = self.listener.signals

    def testLoadProjectFailedUnknownFormat(self):
        """
        Check that new-project-failed is emitted when we don't have a suitable
        formatter.
        """
        uri = "file:///Untitled.meh"
        self.manager.loadProject(uri)
        self.failUnlessEqual(len(self.signals), 2)

        # loading
        name, args = self.signals[0]
        self.failUnlessEqual(args[0], uri)

        # failed
        name, args = self.signals[1]
        self.failUnlessEqual(name, "new-project-failed")
        signalUri, exception = args
        self.failUnlessEqual(uri, signalUri)
        self.failUnless(isinstance(exception, FormatterLoadError))

    def testLoadProjectFailedCloseCurrent(self):
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
        self.manager.loadProject(uri)
        self.failUnlessEqual(len(self.signals), 2)

        # loading
        name, args = self.signals[0]
        self.failUnlessEqual(args[0], uri)

        # failed
        name, args = self.signals[1]
        self.failUnlessEqual(name, "new-project-failed")
        signalUri, exception = args
        self.failUnlessEqual(uri, signalUri)
        self.failUnless(isinstance(exception, FormatterLoadError))
        self.failUnless(state["tried-close"])

    def testLoadProjectFailedProxyFormatter(self):
        """
        Check that new-project-failed is proxied when a formatter emits it.
        """
        class FailFormatter(Formatter):
            def _validateUri(self, uri):
                pass

            def _loadProject(self, location, project=None):
                raise FormatterError()
        self.manager._getFormatterForUri = lambda uri: FailFormatter()

        uri = "file:///Untitled.xptv"
        self.manager.loadProject(uri)
        self.failUnlessEqual(len(self.signals), 2)

        # loading
        name, args = self.signals[0]
        self.failUnlessEqual(args[0], uri)

        # failed
        name, args = self.signals[1]
        self.failUnlessEqual(name, "new-project-failed")
        signalUri, exception = args
        self.failUnlessEqual(uri, signalUri)
        self.failUnless(isinstance(exception, FormatterError))

    def testLoadProjectMissingUri(self):
        class MissingUriFormatter(Formatter):
            def _validateUri(self, uri):
                pass

            def _loadProject(self, location, project=None):
                pass

            def _getSources(self):
                # this will emit missing-uri
                self.validateSourceURI("file:///icantpossiblyexist")
                return []

            def _fillTimeline(self):
                pass
        self.manager._getFormatterForUri = lambda uri: MissingUriFormatter()

        uri = "file:///Untitled.xptv"
        self.manager.loadProject(uri)
        self.failUnlessEqual(len(self.signals), 3)

        # loading
        name, args = self.signals[0]
        self.failUnlessEqual(args[0], uri)

        # failed
        name, args = self.signals[1]
        self.failUnlessEqual(name, "missing-uri")
        formatter, signalUri = args
        self.failUnlessEqual(signalUri, "file:///icantpossiblyexist")


    def testLoadProjectLoaded(self):
        class EmptyFormatter(Formatter):
            def _validateUri(self, uri):
                pass

            def _loadProject(self, location, project=None):
                pass

            def _getSources(self):
                return []

            def _fillTimeline(self):
                pass
        self.manager._getFormatterForUri = lambda uri: EmptyFormatter()

        uri = "file:///Untitled.xptv"
        self.manager.loadProject(uri)
        self.failUnlessEqual(len(self.signals), 2)

        # loading
        name, args = self.signals[0]
        self.failUnlessEqual(args[0], uri)

        # failed
        name, args = self.signals[1]
        self.failUnlessEqual(name, "new-project-loaded")
        project = args[0]
        self.failUnlessEqual(uri, project.uri)

    def testCloseRunningProjectNoProject(self):
        self.failUnless(self.manager.closeRunningProject())
        self.failIf(self.signals)

    def testCloseRunningProjectCantSaveModifications(self):
        self.manager.current = MockProject()
        self.manager.current.save = lambda: False
        self.failIf(self.manager.closeRunningProject())
        self.failIf(self.signals)

    def testCloseRunningProjectRefuseFromSignal(self):
        def closing(manager, project):
            return False

        self.manager.current = MockProject()
        self.manager.connect("closing-project", closing)

        self.failIf(self.manager.closeRunningProject())
        self.failUnlessEqual(len(self.signals), 1)
        name, args = self.signals[0]
        self.failUnlessEqual(name, "closing-project")
        project = args[0]
        self.failUnless(project is self.manager.current)

    def testCloseRunningProject(self):
        current = self.manager.current = MockProject()
        self.failUnless(self.manager.closeRunningProject())
        self.failUnlessEqual(len(self.signals), 2)

        name, args = self.signals[0]
        self.failUnlessEqual(name, "closing-project")
        project = args[0]
        self.failUnless(project is current)

        name, args = self.signals[1]
        self.failUnlessEqual(name, "project-closed")
        project = args[0]
        self.failUnless(project is current)

        self.failUnlessEqual(self.manager.current, None)

    def testNewBlankProjectCantCloseCurrent(self):
        current = self.manager.current = MockProject()
        current.save = lambda: False

        self.failIf(self.manager.newBlankProject())
        self.failIf(self.signals)

    def testNewBlankProject(self):
        self.failUnless(self.manager.newBlankProject())
        self.failUnlessEqual(len(self.signals), 2)

        name, args = self.signals[0]
        self.failUnlessEqual(name, "new-project-loading")
        uri = args[0]
        self.failUnlessEqual(uri, None)

        name, args = self.signals[1]
        self.failUnlessEqual(name, "new-project-loaded")
        project = args[0]
        self.failUnless(project is self.manager.current)
