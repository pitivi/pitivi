#!/usr/bin/env python2
from helper_functions import HelpFunc
from time import time, sleep


class DialogsStartupWizardTest(HelpFunc):
    def test_welcome(self):
        filename = "auto_pitivi_test_project-%i.xges" % time()
        filename_full_path = "/tmp/" + filename
        self.unlink.append(filename_full_path)
        # Create a new project and save it
        self.pitivi.child(name="New", roleName='push button').click()
        self.pitivi.child(name="OK", roleName="push button").click()
        self.saveProject(filename_full_path)
        sleep(1)
        # To show the welcome dialog, we need to restart the app
        self.tearDown(clean=False)
        self.setUp()
        welcome = self.pitivi.child(name="Welcome", roleName="frame")
        # We expect to find the project we just saved in the welcome dialog:
        welcome.child(name=filename)
