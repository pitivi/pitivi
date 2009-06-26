# PiTiVi , Non-linear video editor
#
#       pitivi/sourcelist_undo.py
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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

from pitivi.undo import UndoableAction

class SourceListSourceAddedAction(UndoableAction):
    def __init__(self, sourcelist, source):
        self.sourcelist = sourcelist
        self.source = source

    def undo(self):
        self.sourcelist.removeUri(self.source.uri)
        self._undone()

    def do(self):
        self.sourcelist.addFactory(self.source)
        self._done()

class SourceListSourceRemovedAction(UndoableAction):
    def __init__(self, sourcelist, uri, source):
        self.sourcelist = sourcelist
        self.uri = uri
        self.source = source

    def undo(self):
        self.sourcelist.addFactory(self.source)
        self._undone()

    def do(self):
        self.sourcelist.removeUri(self.source.uri)
        self._done()

class SourceListLogObserver(object):
    def __init__(self, log):
        self.log = log

    def startObserving(self, sourcelist):
        self._connectToSourcelist(sourcelist)

    def stopObserving(self, sourcelist):
        self._disconnectFromSourcelist(sourcelist)

    def _connectToSourcelist(self, sourcelist):
        sourcelist.connect("source-added", self._sourceAddedCb)
        sourcelist.connect("source-removed", self._sourceRemovedCb)

    def _disconnectFromSourcelist(self, sourcelist):
        sourcelist.disconnect_by_func(self._sourceAddedCb)
        sourcelist.disconnect_by_func(self._sourceRemovedCb)

    def _sourceAddedCb(self, sourcelist, factory):
        self.log.begin("add source")
        action = SourceListSourceAddedAction(sourcelist, factory)
        self.log.push(action)
        self.log.commit()

    def _sourceRemovedCb(self, sourcelist, uri, factory):
        self.log.begin("remove source")
        action = SourceListSourceRemovedAction(sourcelist, uri, factory)
        self.log.push(action)
        self.log.commit()
