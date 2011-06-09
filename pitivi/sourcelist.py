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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

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
    @ivar nb_file_to_import: The number of URIs on the last addUris call.
    @type nb_file_to_import: int
    @ivar nb_imported_files: The number of URIs loaded since the last addUris
    call.
    @type nb_imported_files: int

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
        "ready": [],
        "starting": [],
        "missing-plugins": ["uri", "factory", "details", "descriptions"],
        "source-added": ["factory"],
        "source-removed": ["uri"],
        "discovery-error": ["uri", "reason"],
        }

    def __init__(self):
        Loggable.__init__(self)
        Signallable.__init__(self)
        # A (URI -> SourceFactory) map.
        self._sources = {}
        # A list of SourceFactory objects.
        self._ordered_sources = []
        self.nb_file_to_import = 1
        self.nb_imported_files = 0

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
        self._sources[uri] = None
        # Tell the discoverer to investigate the URI and report back when
        # it has the info or failed.
        self.discoverer.addUri(uri)

    def addUris(self, uris):
        """
        Add c{uris} to the source list.

        The uris will be analyzed before being added.
        """
        self.nb_file_to_import = len(uris)
        self.nb_imported_files = 0
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
        factory = self._sources.get(uri)
        if factory is None:
            raise SourceListError("URI not in the sourcelist", uri)
        return factory

    def addFactory(self, factory):
        """
        Add the specified SourceFactory to the list of sources.
        """
        if self._sources.get(factory.uri, None) is not None:
            raise SourceListError("We already have a factory for this URI",
                    factory.uri)
        self._sources[factory.uri] = factory
        self._ordered_sources.append(factory)
        self.nb_imported_files += 1
        self.emit("source-added", factory)

    def getSources(self):
        """ Returns the list of sources used.

        The list will be ordered by the order in which they were added.

        @return: A list of SourceFactory objects which must not be changed.
        """
        return self._ordered_sources

    def _discoveryDoneCb(self, discoverer, uri, factory):
        """Handles the success of a URI info gathering operation."""
        if factory.uri not in self._sources:
            # The source was removed while it was being scanned. Nothing to do.
            return
        self.addFactory(factory)

    def _discoveryErrorCb(self, discoverer, uri, reason, extra):
        """Handles the failure of a URI info gathering operation."""
        try:
            del self._sources[uri]
        except KeyError:
            # The source was removed while it was being scanned. Nothing to do.
            pass
        self.emit("discovery-error", uri, reason, extra)

    def _discovererStartingCb(self, unused_discoverer):
        """Handles the start of the URI info gathering operations."""
        self.emit("starting")

    def _discovererReadyCb(self, unused_discoverer):
        """Handles the finish of the URI info gathering operations."""
        self.emit("ready")

    def _discovererMissingPluginsCb(self, discoverer, uri, factory,
            details, descriptions, missingPluginsCallback):
        if factory.uri not in self._sources:
            # The source was removed while it was being scanned. Nothing to do.
            return None
        return self.emit('missing-plugins', uri, factory,
                details, descriptions, missingPluginsCallback)
