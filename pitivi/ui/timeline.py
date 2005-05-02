#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       ui/timeline.py
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
import gobject

class TimelineWidget(gtk.VBox):
    """ Widget for reprensenting Pitivi's Timeline """

    def __init__(self, pitivi):
        self.pitivi = pitivi
        gtk.VBox.__init__(self)
        self._create_gui()

    def _create_gui(self):
        """ draw the GUI """
        self.hadjustment = gtk.Adjustment()
        self.leftsizegroup = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

        self.content = SimpleTimelineContentWidget(self)
        #contentframe = gtk.Frame()
        #contentframe.add(self.content)
        self.pack_start(self.content)

        hbox = gtk.HBox()
        
        switchmenuframe = gtk.Frame()
        simpleview = gtk.Label("Simple View")
        simpleview.set_padding(5,0)
        switchmenuframe.add(simpleview)
        self.leftsizegroup.add_widget(switchmenuframe)
        
        hbox.pack_start(switchmenuframe, expand=False)
        hbox.pack_start(gtk.HScrollbar(self.hadjustment))

        self.pack_start(hbox, expand=False)
        
gobject.type_register(TimelineWidget)

class SimpleTimelineContentWidget(gtk.HBox):
    """ Widget for Simple Timeline content display """

    def __init__(self, twidget):
        """ init """
        self.twidget = twidget
        gtk.HBox.__init__(self)
        self._create_gui()
        self.layout.put(gtk.Label("pouet"), 0, 0)

    def _create_gui(self):
        """ draw the GUI """
        self.header = gtk.Label("Header")
        self.twidget.leftsizegroup.add_widget(self.header)
        self.pack_start(self.header, expand=False)

        self.layout = gtk.Layout(hadjustment = self.twidget.hadjustment)
        self.layout.set_size(1000, 0)
        self.layout.set_size_request(100, 50)
        self.layout.connect_after("realize", self.realize_after_cb)

        layoutframe = gtk.Frame()
        layoutframe.add(self.layout)
        self.pack_start(layoutframe)

    def realize_after_cb(self, widget):
        self.layout.realize()
        cmap = self.layout.bin_window.get_colormap()
        self.layout.bin_window.set_background(cmap.alloc_color(65000, 65000, 65000))

    def expose_event_cb(self, widget, event):
        print "expose", event.area.x, event.area.y, event.area.width, event.area.height
        cmap = self.layout.bin_window.get_colormap()
        white = cmap.alloc_color(65000, 65000, 65000)
        self.layout.bin_window.set_background(white)

gobject.type_register(SimpleTimelineContentWidget)
