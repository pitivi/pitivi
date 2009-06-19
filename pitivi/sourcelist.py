# PiTiVi , Non-linear video editor
#
#       pitivi/sourcelist.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""
Handles the list of source for a project
"""

import urllib
from pitivi.discoverer import Discoverer
from pitivi.signalinterface import Signallable
from pitivi.log.loggable import Loggable

class SourceListError(Exception):
    pass

class SourceList(Signallable, Loggable):
    discovererClass = Discoverer

    """
    Contains the sources for a project, stored as SourceFactory objects.

    @ivar discoverer: The discoverer object used internally
    @type discoverer: L{Discoverer}

    Signals:
     - C{source-added} : A source has been discovered and added to the SourceList.
     - C{source-removed} : A source was removed from the SourceList.
     - C{missing-plugins} : A source has been discovered but some plugins are
       missing in order to decode all of its streams.
     - C{discovery-error} : The given uri is not a media file.
     - C{ready} : No more files are being discovered/added.
     - C{starting} : Some files are being discovered/added.
    """

    __signals__ = {
        "ready" : [],
        "starting" : [],
        "missing-plugins": ["uri", "factory", "details", "descriptions"],
        "source-added" : ["factory"],
        "source-removed" : ["uri"],
        "discovery-error" : ["uri", "reason"],
        }

    def __init__(self):
        Loggable.__init__(self)
        Signallable.__init__(self)
        self._sources = {}
        self._ordered_sources = []

        self.discoverer = self.discovererClass()
        self.discoverer.connect("discovery-error", self._discoveryErrorCb)
        self.discoverer.connect("discovery-done", self._discoveryDoneCb)
        self.discoverer.connect("starting", self._discovererStartingCb)
        self.discoverer.connect("ready", self._discovererReadyCb)
        self.discoverer.connect("missing-plugins",
                self._discovererMissingPluginsCb)


    def addUri(self, uri):
        """
        Add c{uri} to the source list.

        The uri will be analyzed before being added.
        """
        if uri in self._sources:
            raise SourceListError("URI already present in the source list", uri)

        uri = urllib.unquote(uri)
        self._sources[uri] = None

        self.discoverer.addUri(uri)

    def addUris(self, uris):
        """
        Add c{uris} to the source list.

        The uris will be analyzed before being added.
        """
        for uri in uris:
            self.addUri(uri)

    def removeUri(self, uri):
        """
        Remove the factory for c{uri} from the source list.
        """
        try:
            factory = self._sources.pop(uri)
        except KeyError:
            raise SourceListError("URI not in the sourcelist", uri)

        try:
            self._ordered_sources.remove(factory)
        except ValueError:
            # this can only happen if discoverer hasn't finished scanning the
            # source, so factory must be None
            assert factory is None

        self.emit("source-removed", uri, factory)

    def getUri(self, uri):
        """
        Get the source corresponding to C{uri}.
        """
        factory = self._sources.get(uri, None)
        if factory is None:
            raise SourceListError("URI not in the sourcelist", uri)

        return factory

    def addFactory(self, factory):
        """
        Add an objectfactory for the given uri.
        """
        if self._sources.get(factory.uri, None) is not None:
            raise SourceListError("We already have a factory for this uri",
                    factory.uri)

        self._sources[factory.uri] = factory
        self._ordered_sources.append(factory)
        self.emit("source-added", factory)

    def getSources(self):
        """ Returns the list of sources used.

        The list will be ordered by the order in which they were added
        """
        return self._ordered_sources

    def _discoveryDoneCb(self, discoverer, uri, factory):
        if factory.uri not in self._sources:
            # the source was removed while it was being scanned
            return

        self.addFactory(factory)

    def _discoveryErrorCb(self, discoverer, uri, reason, extra):
        try:
            del self._sources[uri]
        except KeyError:
            # the source was removed while it was being scanned
            pass

        self.emit("discovery-error", uri, reason, extra)

    def _discovererStartingCb(self, unused_discoverer):
        self.emit("starting")

    def _discovererReadyCb(self, unused_discoverer):
        self.emit("ready")

    def _discovererMissingPluginsCb(self, discoverer, uri, factory,
            details, descriptions, missingPluginsCallback):
        if factory.uri not in self._sources:
            # the source was removed while it was being scanned
            return None

        return self.emit('missing-plugins', uri, factory,
                details, descriptions, missingPluginsCallback)
