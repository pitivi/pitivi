# PiTiVi , Non-linear video editor
#
#       ui/slider.py
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

import gtk
import gst
import pitivi.instance as instance
from pitivi.timeline.source import TimelineFileSource

class PipelineSliderEndpoints(gtk.DrawingArea):
    """ Helper class which displays start and stop points within the upper and
    lower bounds of the adjustment"""
    def __init__(self):

        # basic initialization
        gtk.DrawingArea.__init__(self)
        self._lower = 0
        self._upper = 0
        self._start = 0
        self._duration = 0
        self._width = 0
        self._height = 0
        self._gc = None
        self._pixmap = None
        self._update = True

        self.set_size_request(0, 10)

        # signal handlers
        self.connect("realize", self._realizeCb)
        self.connect("configure-event", self._configureEventCb)
        self.connect("expose-event", self._exposeEventCb)

    def _drawData(self):
        if self._gc:
            self._pixmap = gtk.gdk.Pixmap(self.window, self._width, self._height)
            self._pixmap.draw_rectangle(self.style.black_gc, True,
                0, 0, self._width, self._height)

            # left_edge / self.width = start / (upper - lower)
            # right_edge / self.width = duration / (upper - lower)
            left_edge = ((self._start * self._width) / (self._upper -
                self._lower))
            right_edge = ((self._duration * self._width) /
                (self._upper - self._lower))
            self._pixmap.draw_rectangle(self.style.white_gc, True,
                left_edge, 0, right_edge, self._height)

        self._update = False

    def _realizeCb(self, unused_widget):
        self._gc = self.window.new_gc()
        self._drawData()
        return False

    def _configureEventCb(self, unused_layout, event):
        self._width = event.width
        self._height = event.height
        self._drawData()
        return False

    def _exposeEventCb(self, unused_widget, event):
        if self._update:
            self._drawData()
        x, y, w, h = event.area
        self.window.draw_drawable(self._gc, self._pixmap, x, y, x, y, w, h)
        return True

    def setEndpoints(self, lower, upper, start, duration):
        gst.log("lower:%s, upper:%s, start:%s, duration:%s" % (gst.TIME_ARGS(lower),
                                                               gst.TIME_ARGS(upper),
                                                               gst.TIME_ARGS(start),
                                                               gst.TIME_ARGS(duration)))
        self._lower = lower
        self._upper = upper
        self._start = start
        self._duration = duration
        self._update = True
        self.queue_draw()

class PipelineSlider(gtk.VBox):
    """
    Represents idea of a slider associated with a SmartBin. Optionally can 
    display editing endpoints (since may be used elsewhere in UI)

    Calling setPipeline implicitly sets slider range, and associates with
    pipeline. Value changes will result in pipeline seeks, and pipeline seeks
    will be represented by the slider
    
    Sider keeps track of whether it's pipeline is displayed in the viewer, and
    will automatically switch viewer to it if the slider's value changes
    """
    def __init__(self, pipeline=None, display_endpoints=False):
        """Creates a new PipelineSlider, optionally passing in the pipeline or
        wether or not the endpoints of the pipeline should be visible."""
        gst.log("New pipeline slider")
        gtk.VBox.__init__(self)

        self._mediaStartDurationChangedSigId = 0
        self._valueChangedSigId = 0
        self._displayEndpoints = display_endpoints
        self._pipeline = None
        self._source = None
        self._switchSource = False
        self._movingSlider = False
        self._createUi()

        if pipeline:
            self.setPipeline(pipeline)

        self._slider.connect("button-press-event", self._buttonPressEventCb)
        self._slider.connect("button-release-event",
            self._buttonReleaseEventCb)

        # connect to playground
        id = instance.PiTiVi.playground.connect("position",
            self._playgroundPositionCb)
        self._playgroundPositionSigId = id

        id = instance.PiTiVi.playground.connect("current-changed", 
            self._playgroundCurrentChangedCb)
        self._playgroundCurrentChangedSigId = id

    def _createUi(self):
        if self._displayEndpoints == True:
            self._endpoints = PipelineSliderEndpoints()
            self.pack_start(self._endpoints)

        self._slider = gtk.HScale()
        self._slider.set_draw_value(False)
        self.pack_start(self._slider)
        self.show_all()

    def _buttonPressEventCb(self, slider, unused_event):
        gst.info("button pressed")
        self._movingSlider = True
        id = self._slider.connect("value-changed", self._valueChangedCb)
        self._valueChangedSigId = id

        if self._switchSource == True:
            instance.PiTiVi.playground.switchToPipeline(self._pipeline)
        return False

    def _buttonReleaseEventCb(self, slider, unused_event):
        gst.info("slider button release")
        self._movingSlider = False
        if self._valueChangedSigId:
            self._slider.disconnect(self._valueChangedSigId)
            self._valueChangedSigId = 0

        return False

    def _valueChangedCb(self, slider):
        if self._movingSlider == True:
            position = long(self._slider.get_value())
            instance.PiTiVi.playground.seekInCurrent(position)

    def _playgroundCurrentChangedCb(self, unused_playground, current):
        gst.log("playground source changed to" + str(current) + "\n")
        if current == self._pipeline:
            # switch playground to current slider position
            position = long(self._slider.get_value())
            instance.PiTiVi.playground.seekInCurrent(position, gst.FORMAT_TIME)
            self._switchSource = False
        else:
            self._switchSource = True

    def _playgroundPositionCb(self, playground, bin, position):
        if (self._movingSlider == False) and (self._switchSource == False):
            self._slider.set_value(float(position))

    def setPipeline(self, pipeline):
        """Sets the pipeline associated with this slider.
        pipeline must be a smartbin that has been added to the playground
        """

        #TODO add assertions

        # set the slider range and endpoints
        self._pipeline = pipeline
        self._slider.set_range(0, pipeline.length)

        # set playground source
        instance.PiTiVi.playground.switchToPipeline(self._pipeline)

    def get_value(self):
        """returns the value of the slider"""
        return self._slider.get_value()

    def setStartDuration(self, start=-1, duration=-1):
        """only works if _displayEndpoints is true, changes the
        trimming region of the slider"""
        if start == -1:
            start = self._start
        else:
            self._start = start
        if duration == -1:
            duration = self._duration
        else:
            self._duration = duration
        if self._displayEndpoints:
            self._endpoints.setEndpoints(0, self._pipeline.length, start, 
                duration)
    
    def set_value(self, position):
        """Sets the position of the slider's cursor.
        """
        self._slider.set_value(position)
