#!/usr/bin/env python
from helper_functions import HelpFunc
from time import time, sleep


class DialogsStartupWizardTest(HelpFunc):
    def test_welcome(self):
        filename = "test_project%i.xptv" % time()
        #Save project
        self.pitivi.child(name="New", roleName='push button').click()
        self.pitivi.child(name="OK", roleName="push button").click()
        self.saveProject("/tmp/" + filename)
        sleep(1)
        #Hacky, but we need to open once more
        self.tearDown(clean=False)
        self.setUp()
        welcome = self.pitivi.child(name="Welcome", roleName="frame")
        #We expect that just saved project will be in welcome window
        welcome.child(name=filename)
