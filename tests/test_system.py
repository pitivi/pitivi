# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       tests/test_system.py
#
# Copyright (c) 2012, Jean-François Fortin Tam <nekohayo@gmail.com>
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

from unittest import TestCase

from pitivi.utils.system import System, getSystem, GnomeSystem, \
    INHIBIT_LOGOUT, INHIBIT_SUSPEND, INHIBIT_SESSION_IDLE, \
    INHIBIT_USER_SWITCHING


class TestSystem(TestCase):

    def setUp(self):
        self.system = System()

    def testGetUniqueFilename(self):
        self.assertNotEqual(self.system.getUniqueFilename("a/b"),
                            self.system.getUniqueFilename("a%47b"))
        self.assertNotEqual(self.system.getUniqueFilename("a%b"),
                            self.system.getUniqueFilename("a%37b"))
        self.assertNotEqual(self.system.getUniqueFilename("a%/b"),
                            self.system.getUniqueFilename("a%37%3747b"))
        self.assertEqual("a b", self.system.getUniqueFilename("a b"))

    def testScreensaverInhibit(self):
        # check that we start of uninhibited
        self.assertTrue(not self.system.screensaverIsInhibited())

        # inhibit and check that we are
        self.system.inhibitScreensaver("a")
        self.assertTrue(self.system.screensaverIsInhibited())
        # uninhibit and check that we are
        self.system.uninhibitScreensaver("a")
        self.assertTrue(not self.system.screensaverIsInhibited())

        # check that adding/removing is consistent with multiple keys
        for c in range(0, 5):
            self.system.inhibitScreensaver(str(c))
            self.assertTrue(self.system.screensaverIsInhibited(str(c)))

        for c in range(0, 5):
            self.system.uninhibitScreensaver(str(c))
            self.assertTrue(not self.system.screensaverIsInhibited(str(c)))

        self.assertTrue(not self.system.screensaverIsInhibited())

    def testSleepInhibit(self):
        # check that we start of uninhibited
        self.assertTrue(not self.system.sleepIsInhibited())

        # inhibit and check that we are
        self.system.inhibitSleep("a")
        self.assertTrue(self.system.sleepIsInhibited())
        # uninhibit and check that we are
        self.system.uninhibitSleep("a")
        self.assertTrue(not self.system.sleepIsInhibited())

        # check that adding/removing is consistent with multiple keys
        for c in range(0, 5):
            self.system.inhibitSleep(str(c))
            self.assertTrue(self.system.sleepIsInhibited(str(c)))

        for c in range(0, 5):
            self.system.uninhibitSleep(str(c))
            self.assertTrue(not self.system.sleepIsInhibited(str(c)))

        self.assertTrue(not self.system.sleepIsInhibited())


class TestGnomeSystem(TestCase):

    def setUp(self):
        self.system = getSystem()

    def testPowerInhibition(self):
        if not isinstance(self.system, GnomeSystem):
            # We can only test this on a Gnome system.
            return

        if not self.system.session_iface.IsInhibited(
                INHIBIT_LOGOUT | INHIBIT_USER_SWITCHING | INHIBIT_SUSPEND |
                INHIBIT_SESSION_IDLE):
            # Other programs are inhibiting, cannot test.
            return

        self.system.inhibitScreensaver('1')
        self.assertTrue(self.system.session_iface.IsInhibited(
            INHIBIT_SESSION_IDLE))

        self.system.inhibitSleep('2')
        # Screensaver should be able to turn off, but
        self.assertFalse(self.system.session_iface.IsInhibited(
            INHIBIT_SESSION_IDLE))
        # suspend (sleep, suspend, shutdown) and logout should be inhibited.
        # IsInhibited will return True if just one is inhibited, so we
        # check both separately.
        self.assertTrue(self.system.session_iface.IsInhibited(
            INHIBIT_SUSPEND))
        self.assertTrue(self.system.session_iface.IsInhibited(
            INHIBIT_LOGOUT))

        self.system.uninhibitSleep('2')
        # Screensaver should now be blocked.
        self.assertTrue(self.system.session_iface.IsInhibited(
            INHIBIT_SESSION_IDLE))
        # Suspend and logout should be unblocked.
        self.assertFalse(self.system.session_iface.IsInhibited(
            INHIBIT_SUSPEND))
        self.assertFalse(self.system.session_iface.IsInhibited(
            INHIBIT_LOGOUT))

        self.system.uninhibitScreensaver('1')
        # Now everything should be unblocked.
        self.assertFalse(self.system.session_iface.IsInhibited(
            INHIBIT_LOGOUT | INHIBIT_USER_SWITCHING | INHIBIT_SUSPEND |
            INHIBIT_SESSION_IDLE))
