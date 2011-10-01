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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.


####
#
# FIXME reimplement after GES port
#
####

#from unittest import TestCase

#from pitivi.projectmanager import ProjectManager
#from pitivi.formatters.base import Formatter, \
        #FormatterError, FormatterLoadError
#import os
#import gst
#from pitivi.utils import uri_is_reachable
#import time


#class MockProject(object):
    #settings = None
    #format = None
    #uri = None
    #has_mods = True

    #def hasUnsavedModifications(self):
        #return self.has_mods

    #def release(self):
        #pass

    #def disconnect_by_function(self, ignored):
        #pass


#class ProjectManagerListener(object):
    #def __init__(self, manager):
        #self.manager = manager
        #self.connectToProjectManager(self.manager)
        #self._reset()

    #def _reset(self):
        #self.signals = []

    #def connectToProjectManager(self, manager):
        #for signal in ("new-project-loading", "new-project-loaded",
                #"new-project-created", "new-project-failed", "missing-uri",
                #"closing-project", "project-closed"):
            #self.manager.connect(signal, self._recordSignal, signal)

    #def _recordSignal(self, *args):
        #signal = args[-1]
        #args = args[1:-1]
        #self.signals.append((signal, args))

        #return True


#class TestProjectManager(TestCase):
    #def setUp(self):
        #self.manager = ProjectManager()
        #self.listener = ProjectManagerListener(self.manager)
        #self.signals = self.listener.signals

    #def testLoadProjectFailedUnknownFormat(self):
        #"""
        #Check that new-project-failed is emitted when we don't have a suitable
        #formatter.
        #"""
        #uri = "file:///Untitled.meh"
        #self.manager.loadProject(uri)
        #self.failUnlessEqual(len(self.signals), 2)

        ## loading
        #name, args = self.signals[0]
        #self.failUnlessEqual(args[0], uri)

        ## failed
        #name, args = self.signals[1]
        #self.failUnlessEqual(name, "new-project-failed")
        #signalUri, exception = args
        #self.failUnlessEqual(uri, signalUri)
        #self.failUnless(isinstance(exception, FormatterLoadError))

    #def testLoadProjectFailedCloseCurrent(self):
        #"""
        #Check that new-project-failed is emited if we can't close the current
        #project instance.
        #"""
        #state = {"tried-close": False}

        #def close():
            #state["tried-close"] = True
            #return False
        #self.manager.closeRunningProject = close

        #uri = "file:///Untitled.xptv"
        #self.manager.loadProject(uri)
        #self.failUnlessEqual(len(self.signals), 2)

        ## loading
        #name, args = self.signals[0]
        #self.failUnlessEqual(args[0], uri)

        ## failed
        #name, args = self.signals[1]
        #self.failUnlessEqual(name, "new-project-failed")
        #signalUri, exception = args
        #self.failUnlessEqual(uri, signalUri)
        #self.failUnless(isinstance(exception, FormatterLoadError))
        #self.failUnless(state["tried-close"])

    #def testLoadProjectFailedProxyFormatter(self):
        #"""
        #Check that new-project-failed is proxied when a formatter emits it.
        #"""
        #class FailFormatter(Formatter):
            #def _validateUri(self, uri):
                #pass

            #def _loadProject(self, location, project=None):
                #raise FormatterError()
        #self.manager._getFormatterForUri = lambda uri: FailFormatter([])

        #uri = "file:///Untitled.xptv"
        #self.manager.loadProject(uri)
        #self.failUnlessEqual(len(self.signals), 3)

        ## loading
        #name, args = self.signals[0]
        #self.failUnlessEqual(name, "new-project-loading")
        #self.failUnlessEqual(args[0], uri)

        ## created
        #name, args = self.signals[1]
        #self.failUnlessEqual(name, "new-project-created")

        ## failed
        #name, args = self.signals[2]
        #self.failUnlessEqual(name, "new-project-failed")
        #signalUri, exception = args
        #self.failUnlessEqual(uri, signalUri)
        #self.failUnless(isinstance(exception, FormatterError))

    #def testLoadProjectMissingUri(self):
        #class MissingUriFormatter(Formatter):
            #def _validateUri(self, uri):
                #pass

            #def _loadProject(self, location, project):
                #self._finishLoadingProject(project)

            #def _getSources(self):
                ## this will emit missing-uri
                #self.validateSourceURI("file:///icantpossiblyexist", None)
                #return []

            #def _fillTimeline(self):
                #pass
        #self.manager._getFormatterForUri = lambda uri: MissingUriFormatter([])

        #uri = "file:///Untitled.xptv"
        #self.manager.loadProject(uri)
        #self.failUnlessEqual(len(self.signals), 4)

        ## loading
        #name, args = self.signals[0]
        #self.failUnlessEqual(name, "new-project-loading")
        #self.failUnlessEqual(args[0], uri)

        #name, args = self.signals[1]
        #self.failUnlessEqual(name, "new-project-created")
        #self.failUnlessEqual(args[0].uri, uri)

        ## failed
        #name, args = self.signals[2]
        #self.failUnlessEqual(name, "missing-uri")
        #formatter, signalUri, unused_factory = args
        #self.failUnlessEqual(signalUri, "file:///icantpossiblyexist")

    #def testLoadProjectLoaded(self):
        #class EmptyFormatter(Formatter):
            #def _validateUri(self, uri):
                #pass

            #def _loadProject(self, location, project):
                #self._finishLoadingProject(project)

            #def _getSources(self):
                #return []

            #def _fillTimeline(self):
                #pass
        #self.manager._getFormatterForUri = lambda uri: EmptyFormatter([])

        #uri = "file:///Untitled.xptv"
        #self.manager.loadProject(uri)
        #self.failUnlessEqual(len(self.signals), 3)

        ## loading
        #name, args = self.signals[0]
        #self.failUnlessEqual(args[0], uri)

        #name, args = self.signals[1]
        #self.failUnlessEqual(name, "new-project-created")
        #project = args[0]
        #self.failUnlessEqual(uri, project.uri)

        #name, args = self.signals[2]
        #self.failUnlessEqual(name, "new-project-loaded")
        #project = args[0]
        #self.failUnlessEqual(uri, project.uri)

    #def testCloseRunningProjectNoProject(self):
        #self.failUnless(self.manager.closeRunningProject())
        #self.failIf(self.signals)

    #def testCloseRunningProjectRefuseFromSignal(self):
        #def closing(manager, project):
            #return False

        #self.manager.current = MockProject()
        #self.manager.current.has_mods = False
        #self.manager.current.uri = "file:///ciao"
        #self.manager.connect("closing-project", closing)

        #self.failIf(self.manager.closeRunningProject())
        #self.failUnlessEqual(len(self.signals), 1)
        #name, args = self.signals[0]
        #self.failUnlessEqual(name, "closing-project")
        #project = args[0]
        #self.failUnless(project is self.manager.current)

    #def testCloseRunningProject(self):
        #current = self.manager.current = MockProject()
        #self.manager.current.has_mods = False
        #self.failUnless(self.manager.closeRunningProject())
        #self.failUnlessEqual(len(self.signals), 2)

        #name, args = self.signals[0]
        #self.failUnlessEqual(name, "closing-project")
        #project = args[0]
        #self.failUnless(project is current)

        #name, args = self.signals[1]
        #self.failUnlessEqual(name, "project-closed")
        #project = args[0]
        #self.failUnless(project is current)

        #self.failUnlessEqual(self.manager.current, None)

    #def testNewBlankProjectCantCloseCurrent(self):
        #def closing(manager, project):
            #return False

        #self.manager.current = MockProject()
        #self.manager.current.has_mods = False
        #self.manager.current.uri = "file:///ciao"
        #self.manager.connect("closing-project", closing)
        #self.failIf(self.manager.newBlankProject())
        #self.failUnlessEqual(len(self.signals), 1)
        #signal, args = self.signals[0]
        #self.failUnlessEqual(signal, "closing-project")

    #def testNewBlankProject(self):
        #self.failUnless(self.manager.newBlankProject())
        #self.failUnlessEqual(len(self.signals), 3)

        #name, args = self.signals[0]
        #self.failUnlessEqual(name, "new-project-loading")
        #uri = args[0]
        #self.failUnlessEqual(uri, None)

        #name, args = self.signals[1]
        #self.failUnlessEqual(name, "new-project-created")
        #project = args[0]
        #self.failUnlessEqual(uri, project.uri)

        #name, args = self.signals[2]
        #self.failUnlessEqual(name, "new-project-loaded")
        #project = args[0]
        #self.failUnless(project is self.manager.current)

    #def testSaveProject(self):
        #uri = "file://" + os.path.abspath("testproject.xptv")
        #uri2 = "file://" + os.path.abspath("testproject2.xptv")
        #path = gst.uri_get_location(uri)
        #path2 = gst.uri_get_location(uri2)

        ## unlink any existing project files
        #try:
            #os.unlink(path)
            #os.unlink(path2)
        #except OSError:
            #pass

        ## save a project
        #self.failUnless(self.manager.newBlankProject())
        #self.failUnless(self.manager.saveProject(
            #self.manager.current, uri, True))
        #self.failUnless(uri_is_reachable(uri))

        ## wait a bit
        #time.sleep(1.0)

        ## save project under new path
        #self.failUnless(self.manager.saveProject(
            #self.manager.current, uri2, True))
        #self.failUnless(uri_is_reachable(uri2))

        ## make sure the old path and the new path have different mtime
        #mtime = os.path.getmtime(path)
        #mtime2 = os.path.getmtime(path2)
        #self.failUnless(mtime < mtime2)

        ## wait a bit more
        #time.sleep(1.0)

        ## save project again under new path (by omitting uri arg)
        #self.failUnless(self.manager.saveProject(
            #self.manager.current, overwrite=True))

        ## regression test for bug 594396
        ## make sure we didn't save to the old URI
        #self.failUnlessEqual(mtime, os.path.getmtime(path))
        ## make sure we did save to the new URI
        #self.failUnless(mtime2 < os.path.getmtime(path2))

        ## unlink any existing project files
        #try:
            #os.unlink(path)
            #os.unlink(path2)
        #except OSError:
            #pass

    #def testBackupProject(self):
        #uri = "file://" + os.path.abspath("testproject.xptv")

        ## Create and save the project
        #self.manager.newBlankProject()
        #self.manager.saveProject(self.manager.current, uri, True)

        ## Save the backup
        #self.manager._saveBackupCb(self.manager.current, uri)
        #backup_uri = self.manager._makeBackupURI(uri)
        #self.failUnless(uri_is_reachable(uri))
        #self.failUnless(uri_is_reachable(backup_uri))

        ## When closing it should clean the backup
        #self.manager.closeRunningProject()
        #self.failUnless(not uri_is_reachable(backup_uri))

        ## unlink any existing project files
        #try:
            #os.unlink(uri)
            #os.unlink(backup_uri)
        #except OSError:
            #pass
