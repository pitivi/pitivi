import unittest
import pitivi
import os
import os.path
from pitivi.pitivi import Pitivi
import pitivi.projectsaver as projectsaver
import gst
from time import sleep

#Test data
testUri = "file://%s/testProject.ptv" % os.getcwd()
testPath = gst.uri_get_location(testUri)
testSourceA = ""
testSourceB = ""
testSourceC = ""

testProjectTree = \
{
    "timeline" :
        {
            "sources" :
                [
                    {
                        "type" : "file-source",
                        "id" : 1234,
                        "start" : 2000.0
                    }
                ],
            "effects" :
                [

                ],
            "transitions" :
                [

                ],
        },
    "sources" :
        {
            "sourceA" :
                {

                },
            "sourceB" :
                {

                },
            "sourceC" :
                {

                },
        },
    "settings" :
        {

        },
}

class ApplicationLogicTest(unittest.TestCase):
    """
    Test that application logic works properly
    """

    def setUp(self):
        self.ptv = pitivi.pitivi.Pitivi(use_ui=False)
        # was the pitivi object created
        self.assert_(self.ptv)

        # remove any files that may have been created
        if os.path.exists(testPath):
            os.unlink(testPath)

        # initialize properties
        self._got_closing_project_requested_signal = False
        self._got_project_closed_signal = False
        self._got_save_uri_requested_signal = False
        self._got_confirm_overwrite_signal = False
        self._got_new_project_loading_signal = False
        self._got_new_project_loaded_signal = False
        self._got_new_project_failed_signal = False

    def tearDown(self):
        self.ptv= None
        pitivi.instance.PiTiVi = None

    def testShutdownNoSave(self):
        # check that closing ptv will not work unless unsaved changes are
        # written to disk
        self.ptv.connect("closing-project",
            self._closingProjectCb, True)
        self.ptv.current.connect("save-uri-requested",
            self._saveUriRequestedCb, None, False)
        self.ptv.connect("project-closed",
                         self._projectClosedCb)

        self.ptv.current.setModificationState(True)
        self.ptv.shutdown()

        self.assertTrue(self._got_save_uri_requested_signal)
        self.assertFalse(self._got_closing_project_requested_signal)
        self.assertFalse(self._got_project_closed_signal)

    def testShutdownSave(self):
        # check the closing ptv works when unsaved changes are written
        # to disk
        self.ptv.connect("closing-project",
            self._closingProjectCb, True)
        self.ptv.current.connect("save-uri-requested",
            self._saveUriRequestedCb, testUri, True)
        self.ptv.connect("project-closed",
                         self._projectClosedCb)

        self.ptv.current.setModificationState(True)
        self.ptv.shutdown()

        self.assertTrue(self._got_save_uri_requested_signal)
        self.assertTrue(self._got_closing_project_requested_signal)
        self.assertTrue(self._got_project_closed_signal)

    def testNewProjectSimple(self):
        # check that creating a new project works
        self.ptv.connect("new-project-loaded", self._newProjectLoadedCb)
        self.ptv.newBlankProject()
        self.assertTrue(self._got_new_project_loaded_signal)

    def testCloseProjectNoUnsaved(self):
        # tests that closing a project will prompt the user if the current
        # project has unsaved changes
        self.ptv.current.connect("save-uri-requested",
            self._saveUriRequestedCb, testUri, True)
        self.ptv.connect("closing-project",
            self._closingProjectCb, False)

        self.ptv._closeRunningProject()

        self.assertTrue(self._got_closing_project_requested_signal)
        self.assertFalse(self._got_save_uri_requested_signal)

    def testCloseProjectUnsaved(self):
        self.ptv.current.connect("save-uri-requested",
            self._saveUriRequestedCb, testUri, True)
        self.ptv.connect("closing-project",
            self._closingProjectCb, False)

        # set the modification bit
        self.ptv.current.setModificationState(True)

        self.ptv._closeRunningProject()
        self.assertTrue(self._got_save_uri_requested_signal)

    def testNewProjectComplex(self):
        # test creating new project when current project has unsaved changes
        self.ptv.current.connect("save-uri-requested",
            self._saveUriRequestedCb, testUri, True)
        self.ptv.current.connect("confirm-overwrite",
            self._confirmOverwriteCb, True)
        self.ptv.connect("new-project-loading",
            self._newProjectLoadingCb)
        self.ptv.connect("new-project-loaded",
            self._newProjectLoadedCb)
        self.ptv.connect("closing-project",
            self._closingProjectCb, True)

        # set the modification bit, create a new project
        self.assertFalse(os.path.exists(testPath))
        self.ptv.current.setModificationState(True)
        self.ptv.newBlankProject()
        self.assertTrue(self._got_save_uri_requested_signal)
        self.assertTrue(self._got_new_project_loading_signal)
        self.assertTrue(self._got_new_project_loaded_signal)
        self.assertFalse(self._got_confirm_overwrite_signal)
        self.assertTrue(os.path.exists(testPath))

    def testConfirmOverwrite(self):
        # test that the confirm-overwrite signal is properly issued when an
        # existing project is detected, and that returning true results in the
        # project being overwritten.
        self.ptv.current.connect("save-uri-requested",
            self._saveUriRequestedCb, testUri, True)
        self.ptv.current.connect("confirm-overwrite",
            self._confirmOverwriteCb, True)
        self.ptv.connect("closing-project",
            self._closingProjectCb, True)

        # currently, overwrite detection only looks at whether file
        # already exists. so, create the file
        os.system("touch %s" % testPath)
        sleep(1)
        then = os.path.getmtime(testPath)
        self.assertTrue(os.path.exists(testPath))
        self.ptv.current.save()
        self.assertTrue(os.path.exists(testPath))
        self.assertTrue(self._got_save_uri_requested_signal)
        self.assertTrue(self._got_confirm_overwrite_signal)
        now = os.path.getmtime(testPath)
        self.assertTrue(now > then)

    def testNewProjectFailed(self):
        self.ptv.connect("new-project-failed", self._newProjectFailedCb)
        self.assertFalse(os.path.exists(testPath))
        self.ptv.loadProject(uri=testUri)
        self.assertTrue(self._got_new_project_failed_signal)

    def testSaveProject(self):
        pass

    def testLoadProject(self):
        pass

    def _saveUriRequestedCb(self, unused_project, uri, retval):
        self._got_save_uri_requested_signal = True
        if retval:
            self.ptv.current.setUri(uri)
        return retval

    def _confirmOverwriteCb(self, unused_project, uri, argument):
        self._got_confirm_overwrite_signal = True
        return argument

    def _newProjectLoadingCb(self, unused_pitivi, unused_project):
        self._got_new_project_loading_signal = True

    def _newProjectLoadedCb(self, unused_pitivi, project):
        self._got_new_project_loaded_signal = True

    def _newProjectFailedCb(self, unused_pitivi, reason, uri):
        self._got_new_project_failed_signal = True

    def _closingProjectCb(self, unused_pitivi, project, argument):
        self._got_closing_project_requested_signal = True
        return argument

    def _projectClosedCb(self, unused_pitivi, project):
        self._got_project_closed_signal = True

class ProjectSaverTest(unittest.TestCase):
    """Given a properly serialized tree, test that ProjectSaver will correctly
    store and retrieve the file"""

    def setUp(self):
        #TODO: load file format plugins when the architecture is implemented
        formats = projectsaver.ProjectSaver.listFormats()
        self.projectsavers = {}
        for format in formats:
            saver = projectsaver.ProjectSaver.newProjectSaver(format[0])
            self.projectsavers[format] = saver

    def tearDown(self):
        self.projectSaver = None

    def testBasic(self):
        for saver in self.projectsavers.values():
            self.assertTrue(saver)

    def testSerializeAndDeserialize(self):
        for saver in self.projectsavers.values():
            try:
                output_file = open(testPath, "w")
                saver.saveToFile(testProjectTree, output_file)
                output_file.close()
                input_file = open(testPath, "r")
                read_tree = saver.openFromFile(input_file)
                input_file.close()
                self.assertTrue(read_tree == testProjectTree)
            except projectsaver.ProjectLoadError:
                raise self.fail("Failed to load project")
            except projectsaver.ProjectSaveError:
                raise self.fail("Failed to save project")
