# PiTiVi , Non-linear video editor
#
#       pitivi/sourcelist.py
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

from unittest import TestCase
from pitivi.sourcelist import SourceList, SourceListError
from pitivi.discoverer import Discoverer
from pitivi.factories.file import FileSourceFactory


class FakeDiscoverer(Discoverer):
    def _scheduleAnalysis(self):
        pass


class FakeSourceList(SourceList):
    discovererClass = FakeDiscoverer


class TestSourceList(TestCase):
    def setUp(self):
        self.sourcelist = SourceList()

    def testAddUriDiscoveryOk(self):
        """
        Test the simple case of adding an uri.
        """
        uri = "file:///ciao"
        factory = FileSourceFactory(uri)
        self.sourcelist.addUri(uri)
        self.failUnlessEqual(len(self.sourcelist.getSources()), 0)
        self.failUnlessRaises(SourceListError, self.sourcelist.addUri, uri)

        # mock discovery-done
        self.sourcelist.discoverer.emit("discovery-done", uri, factory)
        self.failUnlessEqual(len(self.sourcelist.getSources()), 1)

        # can't add again
        self.failUnlessRaises(SourceListError, self.sourcelist.addUri, uri)

    def testAddUriDiscoveryOkSourceGone(self):
        """
        Test that we don't explode if discoverer finishes analyzing a source
        that in the meantime was removed.
        """
        uri = "file:///ciao"
        factory = FileSourceFactory(uri)
        self.sourcelist.addUri(uri)
        self.sourcelist.removeUri(uri)

        self.sourcelist.discoverer.emit("discovery-done", uri, factory)
        self.failUnlessEqual(len(self.sourcelist.getSources()), 0)

        # this shouldn't fail since we removed the factory before the discovery
        # was complete
        self.sourcelist.addUri(uri)

    def testAddUriDiscoveryErrorSourceGone(self):
        """
        Same as the test above, but testing the discovery-error handler.
        """
        uri = "file:///ciao"
        factory = FileSourceFactory(uri)
        self.sourcelist.addUri(uri)
        self.sourcelist.removeUri(uri)

        self.sourcelist.discoverer.emit("discovery-error", uri,
                "error", "verbose debug")
        self.failUnlessEqual(len(self.sourcelist.getSources()), 0)

        # this shouldn't fail since we removed the factory before the discovery
        # was complete
        self.sourcelist.addUri(uri)

    def testAddUriDiscoveryError(self):
        uri = "file:///ciao"
        factory = FileSourceFactory(uri)
        self.sourcelist.addUri(uri)
        self.failUnlessEqual(len(self.sourcelist.getSources()), 0)
        self.failUnlessRaises(SourceListError, self.sourcelist.addUri, uri)

        # mock discovery-done
        self.sourcelist.discoverer.emit("discovery-error", uri,
                "error", "verbose debug")
        self.failUnlessEqual(len(self.sourcelist.getSources()), 0)

        # there was an error, the factory wasn't added so this shouldn't raise
        self.sourcelist.addUri(uri)
