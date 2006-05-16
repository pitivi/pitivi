#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       pitivi/ui/timeline.py
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
Main timeline widget
"""

import gtk
import gobject
import gst

from timelineobjects import SimpleSourceWidget, SimpleTimeline
from complextimeline import ComplexTimelineWidget

class TimelineWidget(gtk.VBox):
    """ Widget for reprensenting Pitivi's Timeline """

    def __init__(self):
        gst.log("New Timeline Widget")
        gtk.VBox.__init__(self)
        self._createUi()

    def _createUi(self):
        """ draw the GUI """
        self.hadjustment = gtk.Adjustment()
        self.vadjustment = gtk.Adjustment()

        self.simpleview = SimpleTimelineContentWidget(self)
        self.complexview = ComplexTimelineWidget(self)

        self.simpleview.connect("scroll-event", self._simpleScrollCb)
        self.complexview.connect("scroll-event", self._simpleScrollCb)

        self.hscroll = gtk.HScrollbar(self.hadjustment)
        self.pack_end(self.hscroll, expand=False)

    def showSimpleView(self):
        """ Show the simple timeline """
        if self.complexview in self.get_children():
            self.remove(self.complexview)
            self.complexview.hide()
        self.pack_start(self.simpleview, expand=True)
        self.simpleview.show_all()

    def showComplexView(self):
        """ Show the advanced timeline """
        if self.simpleview in self.get_children():
            self.remove(self.simpleview)
            self.simpleview.hide()
        self.pack_start(self.complexview, expand=True)
        self.complexview.show_all()

    def _simpleScrollCb(self, unused_simplet, event):
        gst.debug("state:%s" % event.state)
        self.hscroll.emit("scroll-event", event)

class SimpleTimelineContentWidget(gtk.HBox):
    """ Widget for Simple Timeline content display """
    def __init__(self, twidget):
        """ init """
        self.twidget = twidget
        gtk.HBox.__init__(self)
        self._createUi()
        self.show_all()

    def _createUi(self):
        """ draw the GUI """
        self.timeline = SimpleTimeline(hadjustment = self.twidget.hadjustment)
        
        layoutframe = gtk.Frame()
        layoutframe.add(self.timeline)
        self.pack_start(layoutframe)
