# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       tests/test_application.py
#
# Copyright (c) 2014, Alex Băluț <alexandru.balut@gmail.com>
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

from common import TestCase

from pitivi import application
from pitivi import configure


class MockGioFile(object):
    def load_contents_finish(self, result):
        return (True, result)


class TestPitivi(TestCase):

    def testBasic(self):
        app = application.Pitivi()
        app.emit("startup")
        self.assertTrue(app.shutdown())

    def testVersionInfo(self):
        app = application.Pitivi()
        app.emit("startup")
        self.assertTrue(app.isLatest())

        app = application.Pitivi()
        app.emit("startup")
        app._versionInfoReceivedCb(MockGioFile(), "invalid", None)
        self.assertTrue(app.isLatest())

        app = application.Pitivi()
        app.emit("startup")
        app._versionInfoReceivedCb(MockGioFile(), "%s=CURRENT" % configure.VERSION, None)
        self.assertTrue(app.isLatest())
        self.assertEqual(configure.VERSION, app.getLatest())

        app = application.Pitivi()
        app.emit("startup")
        app._versionInfoReceivedCb(MockGioFile(), "%s=current\n0=supported" % configure.VERSION, None)
        self.assertTrue(app.isLatest())
        self.assertEqual(configure.VERSION, app.getLatest())

        app = application.Pitivi()
        app.emit("startup")
        app._versionInfoReceivedCb(MockGioFile(), "999.0=CURRENT", None)
        self.assertFalse(app.isLatest())
        self.assertEqual("999.0", app.getLatest())

        app = application.Pitivi()
        app.emit("startup")
        app._versionInfoReceivedCb(MockGioFile(), "999.0=CURRENT\n%s=SUPPORTED" % configure.VERSION, None)
        self.assertFalse(app.isLatest())
        self.assertEqual("999.0", app.getLatest())

        app = application.Pitivi()
        app.emit("startup")
        app._versionInfoReceivedCb(MockGioFile(), "0.91=current", None)
        self.assertTrue(app.isLatest())
        self.assertEqual("0.91", app.getLatest())

        app = application.Pitivi()
        app.emit("startup")
        app._versionInfoReceivedCb(MockGioFile(), "0.100000000=current", None)
        self.assertFalse(app.isLatest())
        self.assertEqual("0.100000000", app.getLatest())
