# PiTiVi , Non-linear video editor
#
#       pitivi/medialibrary_undo.py
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

from pitivi.undo.undo import UndoableAction


class MediaLibrarySourceAddedAction(UndoableAction):
    def __init__(self, medialibrary, source):
        self.medialibrary = medialibrary
        self.source = source

    def undo(self):
        self.medialibrary.removeUri(self.source.get_uri())
        self._undone()

    def do(self):
        self.medialibrary.addDiscovererInfo(self.source)
        self._done()


class MediaLibrarySourceRemovedAction(UndoableAction):
    def __init__(self, medialibrary, uri, source):
        self.medialibrary = medialibrary
        self.uri = uri
        self.source = source

    def undo(self):
        self.medialibrary.addDiscovererInfo(self.source)
        self._undone()

    def do(self):
        self.medialibrary.removeUri(self.source.uri)
        self._done()


class MediaLibraryLogObserver(object):
    def __init__(self, log):
        self.log = log

    def startObserving(self, medialibrary):
        self._connectToSourcelist(medialibrary)

    def stopObserving(self, medialibrary):
        self._disconnectFromSourcelist(medialibrary)

    def _connectToSourcelist(self, medialibrary):
        medialibrary.connect("source-added", self._sourceAddedCb)
        medialibrary.connect("source-removed", self._sourceRemovedCb)

    def _disconnectFromSourcelist(self, medialibrary):
        medialibrary.disconnect_by_func(self._sourceAddedCb)
        medialibrary.disconnect_by_func(self._sourceRemovedCb)

    def _sourceAddedCb(self, medialibrary, factory):
        self.log.begin("add source")
        action = MediaLibrarySourceAddedAction(medialibrary, factory)
        self.log.push(action)
        self.log.commit()

    def _sourceRemovedCb(self, medialibrary, uri, factory):
        self.log.begin("remove source")
        action = MediaLibrarySourceRemovedAction(medialibrary, uri, factory)
        self.log.push(action)
        self.log.commit()
