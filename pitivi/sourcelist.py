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

import gobject
import gst
from discoverer import Discoverer

class SourceList(gobject.GObject):
    """
    Contains the sources for a project, stored as FileSourceFactory

    Signals:
    _ file-added (FileSourceFactory) :
                A file has been completely discovered and is valid.
    _ file-removed (string : uri) :
                A file was removed from the SourceList
    _ not-media-file (string : uri, string : reason)
                The given uri is not a media file
    _ tmp-is-ready (FileSourceFactory) :
                The temporary uri given to the SourceList is ready to use.
    """

    __gsignals__ = {
        "file_added" : (gobject.SIGNAL_RUN_LAST,
                        gobject.TYPE_NONE,
                        (gobject.TYPE_PYOBJECT, )),
        "file_removed" : (gobject.SIGNAL_RUN_LAST,
                          gobject.TYPE_NONE,
                          (gobject.TYPE_STRING, )),
        "not_media_file" : (gobject.SIGNAL_RUN_LAST,
                            gobject.TYPE_NONE,
                            (gobject.TYPE_STRING, gobject.TYPE_STRING)),
        "tmp_is_ready": (gobject.SIGNAL_RUN_LAST,
                         gobject.TYPE_NONE,
                         (gobject.TYPE_PYOBJECT, ))
        }

    def __init__(self, project):
        gst.log("new sourcelist for project %s" % project)
        gobject.GObject.__init__(self)
        self.project = project
        self.sources = {}
        self.tempsources = {}
        self.discoverer = Discoverer(self.project)
        self.discoverer.connect("not_media_file", self._notMediaFileCb)
        self.discoverer.connect("finished_analyzing", self._finishedAnalyzingCb)

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
            pass

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
            if not uri in self.sources.keys():
                self.sources[uri] = None
                rlist.append(uri)
        self.discoverer.addFiles(rlist)

    def addTmpUri(self, uri):
        """ Adds a temporary uri, will not be saved """
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

    def _finishedAnalyzingCb(self, unused_discoverer, factory):
        # callback from finishing analyzing factory
        if factory.name in self.tempsources:
            self.tempsources[factory.name] = factory
            self.emit("tmp-is-ready", factory)
        elif factory.name in self.sources:
            self.sources[factory.name] = factory
            self.emit("file-added", factory)

    def _notMediaFileCb(self, unused_discoverer, uri, reason):
        # callback from the discoverer's 'not_media_file' signal
        # remove it from the list
        self.emit("not_media_file", uri, reason)
        if uri in self.sources and not self.sources[uri]:
            del self.sources[uri]
        elif uri in self.tempsources:
            del self.tempsources[uri]
