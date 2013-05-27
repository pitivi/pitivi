from unittest import TestCase
from pitivi.utils.system import getSystem, GnomeSystem, \
    INHIBIT_LOGOUT, INHIBIT_SUSPEND, INHIBIT_SESSION_IDLE, \
    INHIBIT_USER_SWITCHING


class TestGnomeSystem(TestCase):
    def setUp(self):
        self.system = getSystem()

    def testPowerInhibition(self):
        if not isinstance(self.system, GnomeSystem):
            # We can only test this on a Gnome system.
            return

        #check that no other programs are inhibiting, otherwise the
        #test is compromised
        self.assertTrue(not self.system.session_iface.IsInhibited(
            INHIBIT_LOGOUT | INHIBIT_USER_SWITCHING | INHIBIT_SUSPEND |
            INHIBIT_SESSION_IDLE))

        self.system.inhibitScreensaver('1')
        self.assertTrue(self.system.session_iface.IsInhibited(
            INHIBIT_SESSION_IDLE))

        self.system.inhibitSleep('2')
        #screensaver should be able to turn off, but
        self.assertTrue(not self.system.session_iface.IsInhibited(
            INHIBIT_SESSION_IDLE))
        #suspend (sleep, suspend, shutdown), logout should be inhibited
        #IsInhibited will return true if just one is inhibited, so we
        #check both separately.
        self.assertTrue(self.system.session_iface.IsInhibited(
            INHIBIT_SUSPEND))
        self.assertTrue(self.system.session_iface.IsInhibited(
            INHIBIT_LOGOUT))

        self.system.uninhibitSleep('2')
        #screensaver should now be blocked
        self.assertTrue(self.system.session_iface.IsInhibited(
            INHIBIT_SESSION_IDLE))
        #suspend and logout should be unblocked
        self.assertTrue(not self.system.session_iface.IsInhibited(
            INHIBIT_SUSPEND))
        self.assertTrue(not self.system.session_iface.IsInhibited(
            INHIBIT_LOGOUT))

        self.system.uninhibitScreensaver('1')
        #now everything should be unblocked
        self.assertTrue(not self.system.session_iface.IsInhibited(
            INHIBIT_LOGOUT | INHIBIT_USER_SWITCHING | INHIBIT_SUSPEND |
            INHIBIT_SESSION_IDLE))
