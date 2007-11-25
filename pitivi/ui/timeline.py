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
import pango

from gettext import gettext as _

import pitivi.instance as instance
import pitivi.dnd as dnd

from timelineobjects import SimpleTimeline
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

        # (A) real simple timeline
        self.timeline = SimpleTimeline(hadjustment = self.twidget.hadjustment)
        self.layoutframe = gtk.Frame()
        self.layoutframe.add(self.timeline)


        # (B) Explanatory message label
        self.messageframe = gtk.Frame()
        self.messageframe.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.messageframe.show()

        self.textbox = gtk.EventBox()
        self.textbox.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('white'))
        self.textbox.add_events(gtk.gdk.ENTER_NOTIFY_MASK)
        self.textbox.show()
        self.messageframe.add(self.textbox)

        txtlabel = gtk.Label()
        txtlabel.set_padding(10, 10)
        txtlabel.set_line_wrap(True)
        txtlabel.set_line_wrap_mode(pango.WRAP_WORD)
        txtlabel.set_justify(gtk.JUSTIFY_CENTER)
        txtlabel.set_markup(
            _("<span size='x-large'>Add clips to the timeline by dragging them here.</span>"))
        self.textbox.add(txtlabel)
        self.txtlabel = txtlabel

        self.pack_start(self.messageframe, expand=True, fill=True)
        self.reorder_child(self.messageframe, 0)
        self.motionSigId = self.textbox.connect("drag-motion", self._dragMotionCb)
        self.textbox.drag_dest_set(gtk.DEST_DEFAULT_DROP | gtk.DEST_DEFAULT_MOTION,
                                   [dnd.URI_TUPLE, dnd.FILE_TUPLE],
                                   gtk.gdk.ACTION_COPY)

        self.showingTimeline = False
        self._displayTimeline()

    def _dragMotionCb(self, unused_layout, unused_context, unused_x, unused_y,
                      unused_timestamp):
        gst.log("motion...")
        self.showingTimeline = False
        gobject.idle_add(self._displayTimeline)

    def _dragLeaveCb(self, unused_layout, unused_context, unused_timestamp):
        gst.log("leave...")
        if len(instance.PiTiVi.current.timeline.videocomp):
            return
        self.showingTimeline = True
        gobject.idle_add(self._displayTimeline, False)

    def _displayTimeline(self, displayed=True):
        if displayed:
            if self.showingTimeline:
                return
            gst.debug("displaying timeline")
            self.remove(self.messageframe)
            self.txtlabel.hide()
            self.textbox.disconnect(self.motionSigId)
            self.motionSigId = None
            self.pack_start(self.layoutframe)
            self.reorder_child(self.layoutframe, 0)
            self.layoutframe.show_all()
            self.dragLeaveSigId = self.timeline.connect("drag-leave", self._dragLeaveCb)
            self.showingTimeline = True
        else:
            if not self.showingTimeline:
                return
            # only hide if there's nothing left in the timeline
            if not len(instance.PiTiVi.current.timeline.videocomp):
                gst.debug("hiding timeline")
                self.timeline.disconnect(self.dragLeaveSigId)
                self.dragLeaveSigId = None
                self.remove(self.layoutframe)
                self.layoutframe.hide()
                self.pack_start(self.messageframe)
                self.reorder_child(self.messageframe, 0)
                self.txtlabel.show()
                self.motionSigId = self.textbox.connect("drag-motion", self._dragMotionCb)
                self.showingTimeline = False
