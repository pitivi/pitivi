# PiTiVi , Non-linear video editor
#
#       pitivi/pitivi.py
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

import gobject
from discoverer import Discoverer

class SourceList(gobject.GObject):
    """
    Contains the sources for a project, stored as FileSourceFactory
    """

    __gsignals__ = {
        "file_added" : (gobject.SIGNAL_RUN_LAST,
                        gobject.TYPE_NONE,
                        (gobject.TYPE_STRING, )),
        "file_is_valid" : (gobject.SIGNAL_RUN_LAST,
                           gobject.TYPE_NONE,
                           (gobject.TYPE_PYOBJECT, )),
        "file_removed" : (gobject.SIGNAL_RUN_LAST,
                          gobject.TYPE_NONE,
                          (gobject.TYPE_STRING, )),
        "tmp_is_ready": (gobject.SIGNAL_RUN_LAST,
                         gobject.TYPE_NONE,
                         (gobject.TYPE_PYOBJECT, ))
        }

    def __init__(self, project):
        gobject.GObject.__init__(self)
        self.project = project
        self.sources = {}
        self.tempsources = {}
        self.discoverer = Discoverer()
        self.discoverer.connect("new_sourcefilefactory", self._new_sourcefilefactory_cb)
        self.discoverer.connect("not_media_file", self._not_media_file_cb)
        self.discoverer.connect("finished_analyzing", self._finished_analyzing_cb)

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
        
    def add_uri(self, uri):
        # here we add the uri and emit a signal
        # later on the existence of the file will be confirmed or not
        # Until it's confirmed, the uri stays in the temporary list
        # for the moment, we pass it on to the Discoverer
        if uri in self.sources.keys():
            return
        self.sources[uri] = None
        self.emit("file_added", uri)
        self.discoverer.add_file(uri)

    def add_uris(self, uris):
        # same as above but for a list
        rlist = []
        for uri in uris:
            if not uri in self.sources.keys():
                self.sources[uri] = None
                self.emit("file_added", uri)
                rlist.append(uri)
        self.discoverer.add_files(rlist)

    def add_tmp_uri(self, uri):
        """ Adds a temporary uri, will not be saved """
        if uri in self.sources.keys():
            return
        self.tempsources[uri] = None
        self.discoverer.add_file(uri)

    def remove_factory(self, factory):
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

    def _new_sourcefilefactory_cb(self, discoverer, factory):
        # callback from the discoverer's 'new_sourcefilefactory' signal
        if factory.name in self and not self[factory.name]:
            self.sources[factory.name] = factory
            self.emit("file_is_valid", factory)

    def _finished_analyzing_cb(self, discoverer, factory):
        # callback from finishing analyzing factory
        if factory.name in self.tempsources:
            self.tempsources[factory.name] = factory
            self.emit("tmp_is_ready", factory)

    def _not_media_file_cb(self, discoverer, uri):
        # callback from the discoverer's 'not_media_file' signal
        # remove it from the list
        if uri in self and not self[uri]:
            del self[uri]
        elif uri in self.tempsources:
            del self.tempsources[uri]

gobject.type_register(SourceList)
