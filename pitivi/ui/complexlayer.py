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

import gtk
import gobject
import gst

from complexinterface import ZoomableWidgetInterface

#
# Layer system v1 (01 Feb 2006)
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
# . currentHeight (pixels)
# . minimumHeight (pixels)
# . previousHeight (pixels)
#
#
# LayerInfoList (gobject.GObject)
# -------------------------------
# Provides the common python list accessors
# Signals:
# . 'layer-expanded' (layerposition (int), expanded (boolean))
#       The given layer is now expanded or not
# . 'layer-height-changed' (layerposition (int))
#       The given layer's height has changed
# . 'layer-added'
#       A layer was added
# . 'layer-removed'
#       A layer was removed
#

class LayerInfo:
    """ Information on a layer for the complex timeline widgets """

    def __init__(self, composition, minimumHeight,
                 expanded=True, currentHeight=None,
                 yposition=0):
        """
        If currentHeight is None, it will be set to the given minimumHeight.
        """
        self.composition = composition
        self.minimumHeight = minimumHeight
        self.expanded = expanded
        self.yposition = 0
        self.currentHeight = currentHeight or self.minimumHeight
        self.previousHeight = self.minimumHeight

class LayerInfoList(gobject.GObject):
    """ List, on steroids, of the LayerInfo"""

    __gsignals__ = {
        'layer-expanded' : ( gobject.SIGNAL_RUN_LAST,
                             gobject.TYPE_NONE,
                             ( gobject.TYPE_INT, gobject.TYPE_BOOLEAN )),
        'layer-height-changed' : ( gobject.SIGNAL_RUN_LAST,
                                   gobject.TYPE_NONE,
                                   ( gobject.TYPE_INT, )),
        'layer-added' : ( gobject.SIGNAL_RUN_LAST,
                          gobject.TYPE_NONE,
                          ( gobject.TYPE_INT, ) ),
        'layer-removed' : ( gobject.SIGNAL_RUN_LAST,
                          gobject.TYPE_NONE,
                          ( gobject.TYPE_INT, ) ),
        }

    __defaultLayerMinimumHeight = 20
    __defaultLayerHeight = 50

    def __init__(self, timeline, layerminimumheight=None):
        gobject.GObject.__init__(self)
        self.timeline = timeline
        self.layerMinimumHeight = layerminimumheight or self.__defaultLayerMinimumHeight
        self.totalHeight = 0
        self.topSizeGroup = gtk.SizeGroup(gtk.SIZE_GROUP_VERTICAL)
        self._list = []
        self.__fillList()

    def __fillList(self):
        gst.debug("filling up LayerInfoList")
        self.addComposition(self.timeline.videocomp)
        self.addComposition(self.timeline.audiocomp, minimumHeight=50)

    def addComposition(self, composition, pos=-1, minimumHeight=None):
        """
        Insert the composition at the given position (default end)
        Returns the created LayerInfo
        """
        gst.debug("adding a LayerInfo for composition %r" % composition)
        if self.findCompositionLayerInfo(composition):
            gst.warning("composition[%r] is already controlled!" % composition)
            return
        layer = LayerInfo(composition, minimumHeight or self.layerMinimumHeight)
        if pos == -1:
            self._list.append(layer)
        else:
            self._list.insert(pos, layer)
        self.totalHeight += layer.currentHeight
        self.recalculatePositions()
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
        self.totalHeight -= layer.currentHeight
        self.recalculatePositions()
        self.emit('layer-removed', position)

    def findCompositionLayerInfo(self, composition):
        """ Returns the LayerInfo corresponding to the given composition """
        for layer in self._list:
            if layer.composition == composition:
                return layer
        return None

    def recalculatePositions(self):
        """ Recalculate the Y Position of each layer """
        ypos = 0
        for layer in self._list:
            layer.yposition = ypos
            ypos += layer.currentHeight

    def __iter__(self):
        return self._list.__iter__()

    def __len__(self):
        return self._list.__len__()

    def __getitem__(self, y):
        return self._list.__getitem__(y)

    def expandLayer(self, position, expanded):
        """ expand (or reduce) the layer at given position """
        try:
            layer = self._list[position]
        except:
            return
        if layer.expanded == expanded:
            return
        layer.expanded = expanded
        
        if expanded:
            # update total height
            self.currentHeight += (layer.previousHeight - layer.currentHeight)
            # set back to the previous height
            layer.currentHeight = layer.previousHeight
        else:
            # update total height
            self.currentHeight -= (layer.currentHeight - layer.minimumHeight)
            # save height and set currentHeight to minimum
            layer.previousHeight = layer.currentHeight
            layer.currentHeight = layer.minimumHeight

        self.recalculatePositions()
        self.emit('layer-expanded', position, expanded)

    def changeLayerHeight(self, position, height):
        """ change the height for the layer at given position """
        try:
            layer = self._list[position]
        except:
            return
        
        # you can't resize reduced layers
        if not layer.expanded:
            return
        
        # don't resize below the minimumHeight
        height = max(height, layer.minimumHeight)
        if layer.currentHeight == height:
            return

        # update total height
        self.currentHeight += (height - layer.currentHeight)
        
        # save previous height
        layer.previousHeight = layer.currentHeight
        layer.currentHeight = height

        self.recalculatePositions()
        self.emit('layer-height-changed', position, height)
        

class InfoLayer(gtk.Expander):

    def __init__(self, layerInfo):
        gtk.Expander.__init__(self, "pouet")
        self.layerInfo = layerInfo
        self.set_expanded(self.layerInfo.expanded)
        self.add(gtk.Label("A track"))

        # TODO :
        # . react on 'expand' virtual method
        # . put content

class TrackLayer(gtk.Layout, ZoomableWidgetInterface):

    # Safe adding zone on the left/right
    border = 5

    def __init__(self, layerInfo):
        gst.log("new TrackLayer for composition %r" % layerInfo.composition)
        gtk.Layout.__init__(self)
        self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(1,0,0))
        self.layerInfo = layerInfo
        self.layerInfo.composition.connect('start-duration-changed', self.compStartDurationChangedCb)
        self.set_property("width-request", self.get_pixel_width())
        self.set_property("height-request", self.layerInfo.currentHeight)

    def compStartDurationChangedCb(self, composition, start, duration):
        gst.info("setting width-request to %d" % self.get_pixel_width())
        self.set_property("width-request", self.get_pixel_width())
        self.set_property("height-request", self.layerInfo.currentHeight)
        self.start_duration_changed()


    ## ZoomableWidgetInterface methods

    def get_duration(self):
        return self.layerInfo.composition.duration

    def get_start_time(self):
        return self.layerInfo.composition.start

    def get_pixel_width(self):
        return ZoomableWidgetInterface.get_pixel_width(self) + 2 * self.border
