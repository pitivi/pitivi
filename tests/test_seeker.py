# PiTiVi , Non-linear video editor
#
#       tests/test_timeline.py
#
# Copyright (c) 2009, Alessandro Decina <alessandro.decina@collabora.co.uk>
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
from pitivi.utils import Seeker
import gst

class StubSeeker(Seeker):
    seek_id = 0

    def _scheduleSeek(self, position, format):
        # mock Seeker._scheduleSeek so that we don't need a mainloop
        seek_id = self.seek_id
        self.seek_id += 1

        return seek_id

class TestSeeker(TestCase):
    def setUp(self):
        self.seek_count = 0
        self.seek_position = None
        self.seek_format = None

    def testSeek(self):
        def seek_cb(seeker, position, format):
            self.seek_count += 1
            self.seek_position = position
            self.seek_format = format

        seeker = StubSeeker(timeout=10)
        seeker.connect('seek', seek_cb)

        # first seek should happen immediately
        seeker.seek(1)
        self.failUnlessEqual(self.seek_count, 1)
        self.failUnlessEqual(self.seek_position, 1)
        self.failUnlessEqual(self.seek_format, gst.FORMAT_TIME)
        self.failUnlessEqual(seeker.pending_seek_id, 0)
        self.failUnlessEqual(seeker.position, None)
        self.failUnlessEqual(seeker.format, None)

        # second seek is queued
        seeker.seek(2, gst.FORMAT_BYTES)
        self.failUnlessEqual(seeker.pending_seek_id, 0)
        self.failUnlessEqual(seeker.position, 2)
        self.failUnlessEqual(seeker.format, gst.FORMAT_BYTES)

        # ... until the timeout triggers
        seeker._seekTimeoutCb()
        self.failUnlessEqual(self.seek_count, 2)
        self.failUnlessEqual(self.seek_position, 2)
        self.failUnlessEqual(self.seek_format, gst.FORMAT_BYTES)
        self.failUnlessEqual(seeker.pending_seek_id, None)
        self.failUnlessEqual(seeker.position, None)
        self.failUnlessEqual(seeker.format, None)

        # do another first-seek
        seeker.seek(3)
        self.failUnlessEqual(seeker.pending_seek_id, 1)
        self.failUnlessEqual(self.seek_count, 3)
        self.failUnlessEqual(seeker.position, None)
        self.failUnlessEqual(seeker.format, None)

        # timeout with None position
        seeker._seekTimeoutCb()
