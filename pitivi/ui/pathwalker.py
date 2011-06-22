# PiTiVi , Non-linear video editor
#
#       ui/pathwalker.py
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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

import os
import threading
from urllib import quote, unquote
from urlparse import urlsplit, urlunsplit
from pitivi.threads import Thread


def quote_uri(uri):
    parts = list(urlsplit(uri, allow_fragments=False))
    parts[2] = quote(parts[2])
    uri = urlunsplit(parts)
    return uri


class PathWalker(Thread):
    """
    Thread for recursively searching in a list of directories
    """

    def __init__(self, paths, callback):
        Thread.__init__(self)
        self.log("New PathWalker for %s" % paths)
        self.paths = paths
        self.callback = callback
        self.stopme = threading.Event()

    def process(self):
        for folder in self.paths:
            self.log("folder %s" % folder)
            if folder.startswith("file://"):
                folder = unquote(folder[len("file://"):])
            for path, dirs, files in os.walk(folder):
                if self.stopme.isSet():
                    return
                uris = []
                for afile in files:
                    uris.append(quote_uri("file://%s" %
                            os.path.join(path, afile)))
                if uris:
                    self.callback(uris)

    def abort(self):
        self.stopme.set()
