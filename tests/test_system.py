from unittest import TestCase
from pitivi.system import System


class TestSystem(TestCase):
    def setUp(self):
        self.system = System()

    def testScreensaverInhibit(self):
        #check that we start of uninhibited
        self.assertTrue(not self.system.screensaverIsInhibited())

        #inhibit and check that we are
        self.system.inhibitScreensaver("a")
        self.assertTrue(self.system.screensaverIsInhibited())
        #uninhibit and check that we are
        self.system.uninhibitScreensaver("a")
        self.assertTrue(not self.system.screensaverIsInhibited())

        #check that adding/removing is consistent with multiple keys
        for c in range(0, 5):
            self.system.inhibitScreensaver(str(c))
            self.assertTrue(self.system.screensaverIsInhibited(str(c)))

        for c in range(0, 5):
            self.system.uninhibitScreensaver(str(c))
            self.assertTrue(not self.system.screensaverIsInhibited(str(c)))

        self.assertTrue(not self.system.screensaverIsInhibited())

    def testSleepInhibit(self):
        #check that we start of uninhibited
        self.assertTrue(not self.system.sleepIsInhibited())

        #inhibit and check that we are
        self.system.inhibitSleep("a")
        self.assertTrue(self.system.sleepIsInhibited())
        #uninhibit and check that we are
        self.system.uninhibitSleep("a")
        self.assertTrue(not self.system.sleepIsInhibited())

        #check that adding/removing is consistent with multiple keys
        for c in range(0, 5):
            self.system.inhibitSleep(str(c))
            self.assertTrue(self.system.sleepIsInhibited(str(c)))

        for c in range(0, 5):
            self.system.uninhibitSleep(str(c))
            self.assertTrue(not self.system.sleepIsInhibited(str(c)))

        self.assertTrue(not self.system.sleepIsInhibited())
