# PiTiVi , Non-linear video editor
#
#       pitivi/ui/layerwidgets.py
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
import gst
from infolayer import InfoLayer
from tracklayer import TrackLayer
from ruler import ScaleRuler
from complexinterface import ZoomableWidgetInterface

class TimelineToolBar(gtk.HBox):

    def __init__(self):
        gtk.HBox.__init__(self, homogeneous=True)
        self._addButtons()

    def _addButtons(self):
        # zoom
        self.zoomInButton = gtk.Button(label="")
        image = gtk.image_new_from_stock(gtk.STOCK_ZOOM_IN,
                                         gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.zoomInButton.set_image(image)
        self.pack_start(self.zoomInButton, expand=False)
        self.zoomInButton.connect('clicked', self.zoomClickedCb)
        
        self.zoomOutButton = gtk.Button(label="")
        self.zoomOutButton.set_image(gtk.image_new_from_stock(gtk.STOCK_ZOOM_OUT,
                                                              gtk.ICON_SIZE_SMALL_TOOLBAR))
        self.pack_start(self.zoomOutButton, expand=False)
        self.zoomOutButton.connect('clicked', self.zoomClickedCb)

    def zoomClickedCb(self, button):
        if button == self.zoomInButton:
            gst.debug("Zooming IN button clicked")
            ratio = self.get_zoom_ratio() * 2.0
        elif button == self.zoomOutButton:
            gst.debug("Zooming OUT button clicked")
            ratio = self.get_zoom_ratio() / 2.0
        else:
            return
        self.set_zoom_ratio(ratio)

class TimelineLayer(gtk.HBox):

    leftWidgetClass = None
    rightWidgetClass = None

    def __init__(self, leftSizeGroup, hadj, layerInfo=None):
        gtk.HBox.__init__(self)
        self.layerInfo = layerInfo
        self.leftSizeGroup = leftSizeGroup
        self.hadj = hadj

        # Create/Pack left widget
        self.leftWidget = self.getLeftWidget()
        self.leftSizeGroup.add_widget(self.leftWidget)
        self.pack_start(self.leftWidget, expand=False)

        # Create/Pack right widget
        self.rightWidget = self.getRightWidget(hadj)
        self.pack_start(self.rightWidget, expand=True)
        
    def getLeftWidget(self):
        """ override in subclasses if needed """
        return self.leftWidgetClass()

    def getRightWidget(self, hadj):
        """ override in subclasses if needed """
        return self.rightWidgetClass(hadj)

    ## ZoomableWidgetInterface methods

    def zoomChanged(self):
        self.rightWidget.zoomChanged()

class TopLayer(TimelineLayer, ZoomableWidgetInterface):

    leftWidgetClass = TimelineToolBar
    rightWidgetClass = ScaleRuler

    def __init__(self, leftSizeGroup, hadj):
        TimelineLayer.__init__(self, leftSizeGroup, hadj)
        # The border width of the top layer needs to be set to
        # ComplexTimelineWidget.border_width + 1
        self.set_border_width(3)

    def overrideZoomableWidgetInterfaceMethods(self):
        # these override will cause the right widget to
        # call the container (ComplexTimelineWidget) methods
        # since the ScaleRuler has no clue what the duration
        # and size is
        self.rightWidget.get_duration = self.get_duration
        self.rightWidget.get_start_time = self.get_start_time
        self.leftWidget.get_zoom_ratio = self.get_zoom_ratio
        self.leftWidget.set_zoom_ratio = self.set_zoom_ratio

    def timelinePositionChanged(self, value, frame):
        self.rightWidget.timelinePositionChanged(value, frame)

    def start_duration_changed(self):
        self.rightWidget.start_duration_changed()

class CompositionLayer(TimelineLayer, ZoomableWidgetInterface):

    def __init__(self, leftSizeGroup, hadj, layerInfo):
        TimelineLayer.__init__(self, leftSizeGroup, hadj, layerInfo)

        # leftWidget's get_height() comes from the righWidget
        self.leftWidget.getNeededHeight = self.rightWidget.getNeededHeight
        

    def getLeftWidget(self):
        return InfoLayer(self.layerInfo)

    def getRightWidget(self, hadj):
        return TrackLayer(self.layerInfo, hadj)

    ## ZoomableWidgetInterface override

    def get_duration(self):
        return self.rightWidget.get_duration()

    def get_start_time(self):
        return self.rightWidget.get_start_time()
