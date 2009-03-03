# PiTiVi , Non-linear video editor
#
#       pitivi/sourcelist.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
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
from pitivi.serializable import Serializable, to_object_from_data_type
from pitivi.signalinterface import Signallable
from pitivi.log.loggable import Loggable

class SourceList(Serializable, Signallable, Loggable):
    """
    Contains the sources for a project, stored as FileSourceFactory

    Signals:
     - C{file_added} : A file has been completely discovered and is valid.
     - C{file_removed} : A file was removed from the SourceList.
     - C{not_media_file} : The given uri is not a media file.
     - C{tmp_is_ready} : The temporary uri given to the SourceList is ready to use.
     - C{ready} : No more files are being discovered/added.
     - C{starting} : Some files are being discovered/added.
    """

    __signals__ = {
        "file_added" : ["factory"],
        "file_removed" : ["uri"],
        "not_media_file" : ["uri", "reason"],
        "tmp_is_ready": ["factory"],
        "ready" : None,
        "starting" : None,
        "missing-plugins": ["uri", "detail", "description"]
        }

    __data_type__ = "source-list"

    def __init__(self, project=None):
        Loggable.__init__(self)
        self.log("new sourcelist for project %s", project)
        self.project = project
        self.sources = {}
        self.tempsources = {}
        self.discoverer = Discoverer()
        self.discoverer.connect("not_media_file", self._notMediaFileCb)
        self.discoverer.connect("finished_analyzing", self._finishedAnalyzingCb)
        self.discoverer.connect("starting", self._discovererStartingCb)
        self.discoverer.connect("ready", self._discovererReadyCb)
        self.discoverer.connect("missing-plugins",
                self._discovererMissingPluginsCb)
        self.missing_plugins = {}

    def __contains__(self, uri):
        return self.sources.__contains__(uri)

    def __delitem__(self, uri):
        try:
            self.sources.__delitem__(uri)
        except KeyError:
            pass
        else:
            # emit deleted item signal
            self.emit("file_removed", uri)

    def __getitem__(self, uri):
        try:
            res = self.sources.__getitem__(uri)
        except KeyError:
            res = None
        return res

    def __iter__(self):
        """ returns an (uri, factory) iterator over the sources """
        return self.sources.iteritems()

    def addUri(self, uri):
        """ Add the uri to the list of sources, will be discovered """
        # here we add the uri and emit a signal
        # later on the existence of the file will be confirmed or not
        # Until it's confirmed, the uri stays in the temporary list
        # for the moment, we pass it on to the Discoverer
        if uri in self.sources.keys():
            return
        self.sources[uri] = None
        self.discoverer.addFile(uri)

    def addUris(self, uris):
        """ Add the list of uris to the list of sources, they will be discovered """
        # same as above but for a list
        rlist = []
        for uri in uris:
            uri = urllib.unquote(uri)
            if not uri in self.sources.keys():
                self.sources[uri] = None
                rlist.append(uri)

        self.discoverer.addFiles(rlist)

    def addTmpUri(self, uri):
        """ Adds a temporary uri, will not be saved """
        uri = urllib.unquote(uri)
        if uri in self.sources.keys():
            return
        self.tempsources[uri] = None
        self.discoverer.addFile(uri)

    def removeFactory(self, factory):
        """ Remove a file using it's objectfactory """
        # TODO
        # remove an item using the factory as a key
        # otherwise just use the __delitem__
        # del self[uri]
        rmuri = []
        for uri, fact in self.sources.iteritems():
            if fact == factory:
                rmuri.append(uri)
        for uri in rmuri:
            del self[uri]

    def addFactory(self, uri, factory):
        """
        Add an objectfactory for the given uri.
        """
        if uri in self and self[uri]:
            raise Exception("We already have an objectfactory for uri %s", uri)
        self.sources[uri] = factory
        self.emit("file_added", factory)

    def _finishedAnalyzingCb(self, unused_discoverer, factory):
        # callback from finishing analyzing factory
        if factory.name in self.tempsources:
            self.tempsources[factory.name] = factory
            self.emit("tmp_is_ready", factory)
        elif factory.name in self.sources:
            self.addFactory(factory.name, factory)

    def _notMediaFileCb(self, unused_discoverer, uri, reason, extra):
        if self.missing_plugins.pop(uri, None) is None:
            # callback from the discoverer's 'not_media_file' signal
            # remove it from the list
            self.emit("not_media_file", uri, reason, extra)

        if uri in self.sources and not self.sources[uri]:
            del self.sources[uri]
        elif uri in self.tempsources:
            del self.tempsources[uri]

    def _discovererStartingCb(self, unused_discoverer):
        self.emit("starting")

    def _discovererReadyCb(self, unused_discoverer):
        self.emit("ready")

    def _discovererMissingPluginsCb(self, discoverer, uri, detail, description):
        self.missing_plugins[uri] = True
        return self.emit('missing-plugins', uri, detail, description)

    ## Serializable methods

    def toDataFormat(self):
        ret = Serializable.toDataFormat(self)
        d = {}
        for uri, factory in self:
            d[uri] = factory.toDataFormat()
        ret["sources-factories"] = d
        return ret

    def fromDataFormat(self, obj):
        Serializable.fromDataFormat(self, obj)
        # FIXME : We're supposing we have complete objectfactories
        # with all information !!!
        if "sources-factories" in obj:
            for uri, factory in obj["sources-factories"].iteritems():
                self.addFactory(uri, to_object_from_data_type(factory))
