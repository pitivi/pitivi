#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       pitivi/ui/complexlayer.py
#
# Copyright (c) 2006, Edward Hervey <bilboed@bilboed.com>
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
Layer system for the complex view
"""

import gobject
import gst

#
# Layer system v2 (16 Feb 2006)
#
#
# The layer information are stored in a LayerInfo.
# The complete layers information is stored in a LayerInfoList which is a
# standard python list with signals capabilities.
#
# LayerInfo
# ---------
# Contents:
# . composition (Model.TimelineComposition)
# . expanded (boolean, default=True)
#
#
# LayerInfoList (gobject.GObject)
# -------------------------------
# Provides the common python list accessors
# Signals:
# . 'layer-added'
#       A layer was added
# . 'layer-removed'
#       A layer was removed
#

class LayerInfo:
    """ Information on a layer for the complex timeline widgets """

    def __init__(self, composition, expanded=True):
        """
        If currentHeight is None, it will be set to the given minimumHeight.
        """
        self.composition = composition
        self.expanded = expanded

class LayerInfoList(gobject.GObject):
    """ List, on steroids, of the LayerInfo"""

    __gsignals__ = {
        'layer-added' : ( gobject.SIGNAL_RUN_LAST,
                          gobject.TYPE_NONE,
                          ( gobject.TYPE_INT, ) ),
        'layer-removed' : ( gobject.SIGNAL_RUN_LAST,
                          gobject.TYPE_NONE,
                          ( gobject.TYPE_INT, ) ),
        }

    def __init__(self, timeline):
        gobject.GObject.__init__(self)
        self.timeline = timeline
        self._list = []
        self._fillList()

    def _fillList(self):
        gst.debug("filling up LayerInfoList")
        self.addComposition(self.timeline.videocomp)
        self.addComposition(self.timeline.audiocomp)

    def addComposition(self, composition, pos=-1):
        """
        Insert the composition at the given position (default end)
        Returns the created LayerInfo
        """
        gst.debug("adding a LayerInfo for composition %r" % composition)
        if self.findCompositionLayerInfo(composition):
            gst.warning("composition[%r] is already controlled!" % composition)
            return
        layer = LayerInfo(composition)
        if pos == -1:
            self._list.append(layer)
        else:
            self._list.insert(pos, layer)
        self.emit('layer-added', pos)
        return layer

    def removeComposition(self, composition):
        """
        Remove the given composition from the List
        Returns True if it was removed
        """
        layer = self.findCompositionLayerInfo(composition)
        if not layer:
            gst.warning("composition[%r] is not controlled by LayerInfoList" % composition)
            return False
        position = self._list.index(layer)
        self._list.remove(layer)
        self.emit('layer-removed', position)

    def findCompositionLayerInfo(self, composition):
        """ Returns the LayerInfo corresponding to the given composition """
        for layer in self._list:
            if layer.composition == composition:
                return layer
        return None

    def __iter__(self):
        return self._list.__iter__()

    def __len__(self):
        return self._list.__len__()

    def __getitem__(self, y):
        return self._list.__getitem__(y)
