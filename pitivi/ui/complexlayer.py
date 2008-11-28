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

import pitivi.timeline.timeline

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

# FIXME: this code has completely the wrong semantics. It's original intent
# was to support layer editing (as-in priority), but we can do this in other
# ways. Currently, it's actually used to implement tracks. In either case,
# it's a needless level of indirection. Why can't the timeline composition
# emit track-added, track-removed signals directly?


class LayerInfo:
    """ Information on a layer for the complex timeline widgets """

    def __init__(self, composition, sigid, expanded=True):
        """
        If currentHeight is None, it will be set to the given minimumHeight.
        """
        self.composition = composition
        self.expanded = expanded
        self.sigid = sigid

class LayerInfoList(gobject.GObject):
    """ List, on steroids, of the LayerInfo"""

    __gsignals__ = {
        'layer-added' : (
            gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            (gobject.TYPE_PYOBJECT, gobject.TYPE_INT, )
        ),
        'layer-removed' : (
            gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            (gobject.TYPE_INT, )
        ),
        'start-duration-changed' : (
            gobject.SIGNAL_RUN_LAST,
            gobject.TYPE_NONE,
            ()
        )
    }

    def __init__(self):
        gobject.GObject.__init__(self)
        self.timeline = None
        self._list = []

    def setTimeline(self, timeline):
        """ Set the given timeline on this layer """
        self._clear()
        self.timeline = timeline
        if self.timeline:
            self._fillList()

    def _fillList(self):
        gst.debug("filling up LayerInfoList")
        self.addComposition(self.timeline.audiocomp)
        self.addComposition(self.timeline.videocomp)

    def _start_duration_changed_cb(self, timeline, start, duration):
        self.emit("start-duration-changed")

    def addComposition(self, composition, pos=-1):
        """
        Insert the composition at the given position (default end)
        Returns the created LayerInfo
        """
        gst.debug("adding a LayerInfo for composition %r" % composition)
        if self.findCompositionLayerInfo(composition):
            gst.warning("composition[%r] is already controlled!" % composition)
            return
        if composition.media_type == pitivi.timeline.timeline.MEDIA_TYPE_AUDIO:
            expanded = False
        else:
            expanded = True
        sigid = composition.connect("start-duration-changed",
            self._start_duration_changed_cb)
        layer = LayerInfo(composition, sigid, expanded)
        if pos == -1:
            self._list.append(layer)
        else:
            self._list.insert(pos, layer)
        self.emit('layer-added', layer, pos)
        print 'added layer'
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
        layer.composition.disconnect(layer.sigid)
        self.emit('layer-removed', position)

    def _clear(self):
        while len(self._list):
            layer = self._list[0]
            self.removeComposition(layer.composition)

    def findCompositionLayerInfo(self, composition):
        """ Returns the LayerInfo corresponding to the given composition """
        for layer in self._list:
            if layer.composition == composition:
                return layer
        return None

    def __iter__(self):
        return self._list.__iter__()

    def __getitem__(self, item):
        return self._list.__getitem__(item)
