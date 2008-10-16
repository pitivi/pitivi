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
import gst

import pitivi.instance as instance
import pitivi.dnd as dnd
from pitivi.timeline.source import TimelineFileSource, TimelineBlankSource
from pitivi.timeline.objects import MEDIA_TYPE_AUDIO, MEDIA_TYPE_VIDEO

from complextimeline import ComplexTimelineWidget

class TimelineWidget(gtk.VBox):
    """ Widget for reprensenting Pitivi's Timeline """

    def __init__(self):
        gst.log("New Timeline Widget")
        gtk.VBox.__init__(self)
        self._createUi()

        # drag and drop
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP | gtk.DEST_DEFAULT_MOTION, 
            [dnd.FILESOURCE_TUPLE],
            gtk.gdk.ACTION_COPY)
        self.connect("drag-data-received", self._dragDataReceivedCb)
        self.connect("drag-leave", self._dragLeaveCb)
        self.connect("drag-motion", self._dragMotionCb)

    def _createUi(self):
        """ draw the GUI """
        self.complexview = ComplexTimelineWidget()

    def showComplexView(self):
        """ Show the advanced timeline """
        self.pack_start(self.complexview, expand=True)
        self.complexview.show_all()

    def _simpleScrollCb(self, unused_simplet, event):
        gst.debug("state:%s" % event.state)
        self.hscroll.emit("scroll-event", event)

## Drag and Drop callbacks

    def _gotFileFactory(self, filefactory, x, y):
        """ got a filefactory at the given position """
        # remove the slot
        if not filefactory or not filefactory.is_video:
            return
        #pos_ = self.items.point_to_index(pixel_coords(self, (x, y)))
        pos_ = 0
        gst.debug("_got_filefactory pos : %d" % pos_)
        # we just add it here, the drawing will be done in the condensed_list
        # callback
        source = TimelineFileSource(factory=filefactory,
            media_type=MEDIA_TYPE_VIDEO,
            name=filefactory.name)

        # ONLY FOR SIMPLE TIMELINE : if video-only, we link a blank audio object
        if not filefactory.is_audio:
            audiobrother = TimelineBlankSource(factory=filefactory,
                media_type=MEDIA_TYPE_AUDIO, name=filefactory.name)
            source.setBrother(audiobrother)

        timeline = instance.PiTiVi.current.timeline
        if pos_ == -1:
            timeline.videocomp.appendSource(source)
        elif pos_:
            timeline.videocomp.insertSourceAfter(source,
                self.condensed[pos_ - 1])
        else:
            timeline.videocomp.prependSource(source)

    def _dragMotionCb(self, unused_layout, unused_context, x, y, timestamp):
        #TODO: temporarily add source to timeline, and put it in drag mode
        # so user can see where it will go
        gst.info("SimpleTimeline x:%d , source would go at %d" % (x, 0))

    def _dragLeaveCb(self, unused_layout, unused_context, unused_tstamp):
        gst.info("SimpleTimeline")
        #TODO: remove temp source from timeline

    def _dragDataReceivedCb(self, unused_layout, context, x, y, 
        selection, targetType, timestamp):
        gst.log("SimpleTimeline, targetType:%d, selection.data:%s" % 
            (targetType, selection.data))
        if targetType == dnd.TYPE_PITIVI_FILESOURCE:
            uri = selection.data
        else:
            context.finish(False, False, timestamp)
        self._gotFileFactory(instance.PiTiVi.current.sources[uri], x, y)
        context.finish(True, False, timestamp)
        instance.PiTiVi.playground.switchToTimeline()


