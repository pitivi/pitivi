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

import gtk
import gobject
import gst
from timelineobjects import SimpleSourceWidget, SimpleTimeline

class TimelineWidget(gtk.VBox):
    """ Widget for reprensenting Pitivi's Timeline """

    def __init__(self, pitivi):
        gst.info("New Timeline Widget")
        self.pitivi = pitivi
        gtk.VBox.__init__(self)
        self._create_gui()

    def _create_gui(self):
        """ draw the GUI """
        self.hadjustment = gtk.Adjustment()
        self.leftsizegroup = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)

        self.simpleview = SimpleTimelineContentWidget(self)
        self.complexview = ComplexTimelineContentWidget(self)
        #contentframe = gtk.Frame()
        #contentframe.add(self.content)
        #self.pack_start(self.content)

        hbox = gtk.HBox()
        
        #switchmenuframe = gtk.Frame()
        liststore = gtk.ListStore(gobject.TYPE_STRING)
        combobox = gtk.ComboBox(liststore)
        cell = gtk.CellRendererText()
        combobox.pack_start(cell, True)
        combobox.add_attribute(cell, 'text', 0)
        liststore.append(["Simple View"])
        liststore.append(["Complex View"])
        combobox.set_active(0)
        combobox.connect("changed", self._combobox_changed)

        #switchmenuframe.add(combobox)
        self.leftsizegroup.add_widget(combobox)
        
        hbox.pack_start(combobox, expand=False)
        self.hscroll = gtk.HScrollbar(self.hadjustment)
        hbox.pack_start(self.hscroll)

        self.pack_end(hbox, expand=False)
        self._show_simple_view()

    def _combobox_changed(self, cbox):
        if cbox.get_active():
            self._show_complex_view()
        else:
            self._show_simple_view()

    def _show_simple_view(self):
        if self.complexview in self.get_children():
            self.remove(self.complexview)
        self.pack_start(self.simpleview, expand=True)
        self.simpleview.connect("scroll-event", self._simple_scroll_cb)

    def _show_complex_view(self):
        if self.simpleview in self.get_children():
            self.remove(self.simpleview)
        self.pack_start(self.complexview, expand=True)

    def _simple_scroll_cb(self, simplet, event):
        self.hscroll.emit("scroll-event", event)
        
        

class SimpleTimelineContentWidget(gtk.HBox):
    """ Widget for Simple Timeline content display """

    def __init__(self, twidget):
        """ init """
        self.twidget = twidget
        gtk.HBox.__init__(self)
        self._create_gui()

    def _create_gui(self):
        """ draw the GUI """
        self.header = gtk.Label("Timeline")
        self.twidget.leftsizegroup.add_widget(self.header)
        self.pack_start(self.header, expand=False)

        self.timeline = SimpleTimeline(self.twidget, self.twidget.pitivi,
                                       hadjustment = self.twidget.hadjustment)
        
        layoutframe = gtk.Frame()
        layoutframe.add(self.timeline)
        self.pack_start(layoutframe)


class ComplexTimelineContentWidget(gtk.HBox):
    """ Widget for complex timeline content display """

    def __init__(self, twidget):
        self.twidget = twidget
        gtk.HBox.__init__(self)
        self._create_gui()

    def _create_gui(self):
        pass

