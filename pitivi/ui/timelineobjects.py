# PiTiVi , Non-linear video editor
#
#       pitivi/ui/timelineobjects.py
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

import os.path
from urllib import unquote
import gobject
import pango
import gtk
import gst
from gtk import gdk
from pitivi.timeline import Timeline, TimelineComposition, TimelineFileSource, TimelineSource, MEDIA_TYPE_AUDIO, MEDIA_TYPE_VIDEO
import pitivi.dnd as dnd
from sourcefactories import beautify_length

# Default width / height ratio for simple elements
DEFAULT_SIMPLE_SIZE_RATIO = 1.0 # default width / height ratio

# Default simple elements size
DEFAULT_SIMPLE_ELEMENT_WIDTH = 100
DEFAULT_SIMPLE_ELEMENT_HEIGHT = DEFAULT_SIMPLE_ELEMENT_WIDTH * DEFAULT_SIMPLE_SIZE_RATIO

# Default spacing between/above elements in simple timeline
DEFAULT_SIMPLE_SPACING = 10

# Simple Timeline's default values
DEFAULT_HEIGHT = DEFAULT_SIMPLE_ELEMENT_HEIGHT + 2 * DEFAULT_SIMPLE_SPACING
DEFAULT_WIDTH = 3 * DEFAULT_SIMPLE_SPACING # borders (2) + one holding place
MINIMUM_HEIGHT = DEFAULT_HEIGHT
MINIMUM_WIDTH = 3 * DEFAULT_HEIGHT

class SimpleTimeline(gtk.Layout):
    """ Simple Timeline representation """

    def __init__(self, twidget, pitivi, **kw):
        gobject.GObject.__init__(self, **kw)
        self.twidget = twidget
        self.pitivi = pitivi

        self.hadjustment = self.get_property("hadjustment")

        # timeline and top level compositions
        self.timeline = self.pitivi.current.timeline
        self.condensed = self.timeline.videocomp.condensed

        # TODO : connect signals for when the timeline changes

        # widgets correspondance dictionnary
        self.widgets = {}

        self.timeline.videocomp.connect("condensed-list-changed",
                                        self._condensed_list_changed_cb)

        # size
        self.width = int(DEFAULT_WIDTH)
        self.height = int(DEFAULT_HEIGHT)
        self.childheight = int(DEFAULT_SIMPLE_ELEMENT_HEIGHT)
        self.set_size_request(int(MINIMUM_WIDTH), int(MINIMUM_HEIGHT))
        self.set_property("width", int(DEFAULT_WIDTH))
        self.set_property("height", int(DEFAULT_HEIGHT))

        # event callbacks
        self.connect("expose-event", self._expose_event_cb)
        self.connect("notify::width", self._width_changed_cb)
        self.connect("size-allocate", self._size_allocate_cb)
        self.connect("realize", self._realize_cb)

        # drag and drop
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP | gtk.DEST_DEFAULT_MOTION,
                           [dnd.DND_FILESOURCE_TUPLE],
                           gdk.ACTION_COPY)
        self.connect("drag-data-received", self._drag_data_received_cb)
        self.connect("drag-leave", self._drag_leave_cb)
        self.connect("drag-motion", self._drag_motion_cb)
        self.slotposition = -1

    def _condensed_list_changed_cb(self, videocomp, clist):
        """ add/remove the widgets """
        print "condensed list changed in videocomp:"
        for i in clist:
            print i, gst.TIME_ARGS(i.start), gst.TIME_ARGS(i.duration)
        current = self.widgets.keys()
        self.condensed = clist
        # go through the condensed list
        for element in clist:
            if element in current:
                # element stil exists
                current.remove(element)
            else:
                # new element
                # add the widget to self.widget
                print "Adding new element to the layout"
                if isinstance(element, TimelineFileSource):
                    widget = SimpleSourceWidget(element)
                else:
                    widget = SimpleTransitionWidget(element)
                self.widgets[element] = widget
                self.put(widget, 0, 0)
                widget.show()
        # the objects left in current have been removed
        for element in current:
            self.remove(self.widgets[element])
            del self.widgets[element]
        self._resize_childrens()
        # call a redraw

    def _get_nearest_source_slot(self, x):
        """
        returns the nearest file slot position available for the given position
        Returns the value in condensed list position
        Returns n , the element before which it should go
        Return -1 if it's meant to go last
        """
        if not len(self.condensed) or x < 0:
            return 0
        if x > self.width - DEFAULT_SIMPLE_SPACING:
            return -1
        
        pos = DEFAULT_SIMPLE_SPACING
        order = 0
        # TODO Need to avoid getting position between source and transition
        for source in self.condensed:
            if isinstance(source, TimelineSource):
                spacing = self.childheight
            elif insinstance(source, TimelineTransition):
                spacing = self.childheight / 2
            else:
                # this shouldn't happen !! The condensed list only contains
                # sources and/or transitions
                pass
            if x <= pos + spacing / 2:
                return order
            pos = pos + spacing + DEFAULT_SIMPLE_SPACING
            order = order + 1
        return -1

    def _get_nearest_source_slot_pixels(self, x):
        """
        returns the nearest file slot position available for the given position
        Returns the value in pixels
        """
        if not len(self.condensed) or x < 0:
            return DEFAULT_SIMPLE_SPACING
        if x > self.width - DEFAULT_SIMPLE_SPACING:
            return self.width - 2 * DEFAULT_SIMPLE_SPACING
        
        pos = DEFAULT_SIMPLE_SPACING
        # TODO Need to avoid getting position between source and transition
        for source in self.condensed:
            if isinstance(source, TimelineSource):
                spacing = self.childheight
            elif insinstance(source, TimelineTransition):
                spacing = self.childheight / 2
            else:
                # this shouldn't happen !! The condensed list only contains
                # sources and/or transitions
                pass
            if x <= pos + spacing / 2:
                return pos
            pos = pos + spacing + DEFAULT_SIMPLE_SPACING
        return pos

    def _draw_drag_slot(self):
        if self.slotposition == -1:
            return
        self.bin_window.draw_rectangle(self.style.black_gc, True,
                                       self.slotposition, DEFAULT_SIMPLE_SPACING,
                                       DEFAULT_SIMPLE_SPACING, self.childheight)

    def _erase_drag_slot(self):
        if self.slotposition == -1:
            return
        self.bin_window.draw_rectangle(self.style.white_gc, True,
                                       self.slotposition, DEFAULT_SIMPLE_SPACING,
                                       DEFAULT_SIMPLE_SPACING, self.childheight)        

    def _got_filefactory(self, filefactory, x, y):
        """ got a filefactory at the given position """
        # remove the slot
        self._erase_drag_slot()
        self.slotposition = -1
        if not filefactory or not filefactory.is_video:
            return
        pos = self._get_nearest_source_slot(x)

        # we just add it here, the drawing will be done in the condensed_list
        # callback
        source = TimelineFileSource(factory=filefactory,
                                    media_type=MEDIA_TYPE_VIDEO,
                                    name=filefactory.name)
        print "_got_filefactory pos=", pos
        if pos == -1:
            self.timeline.videocomp.append_source(source)
        elif pos:
            self.timeline.videocomp.insert_source_after(source, self.condensed[pos - 1])
        else:
            self.timeline.videocomp.prepend_source(source)

    def _width_changed_cb(self, layout, property):
        if not property.name == "width":
            return
        self.width = self.get_property("width")
        #print "width changed to :", self.width

    def _motion_notify_event_cb(self, layout, event):
        #print "motion notify", event.x, event.y
        pass

    def _drag_motion_cb(self, layout, context, x, y, timestamp):
        #print "drag motion", x, y
        # TODO show where the dragged item would go
        pos = self._get_nearest_source_slot_pixels(x + (self.hadjustment.get_value()))
        rpos = self._get_nearest_source_slot(x + self.hadjustment.get_value())
        gst.log("source would go at %d" % rpos)
        if not pos == self.slotposition:
            if not self.slotposition == -1:
                # erase previous slot position
                self._erase_drag_slot()
            # draw new slot position
            self.slotposition = pos
            self._draw_drag_slot()

    def _drag_leave_cb(self, layout, context, timestamp):
        #print "drag leaves layout"
        self._erase_drag_slot()
        self.slotposition = -1
        # TODO remove the drag emplacement

    def _drag_data_received_cb(self, layout, context, x, y, selection,
                               targetType, timestamp):
        #print "drag data received in simple timeline"
        if targetType == dnd.DND_TYPE_PITIVI_FILESOURCE:
            uri = selection.data
        else:
            context.finish(False, False, timestamp)
        x = x + int(self.hadjustment.get_value())
        self._got_filefactory(self.pitivi.current.sources[uri], x, y)
        context.finish(True, False, timestamp)

    def _realize_cb(self, layout):
        self.modify_bg(gtk.STATE_NORMAL, self.style.white)

    def _area_intersect(self, x, y, w, h, x2, y2, w2, h2):
        """ returns True if the area intersects, else False """
        # is zone to the left of zone2
        z1 = gdk.Rectangle(x, y, w, h)
        z2 = gdk.Rectangle(x2, y2, w2, h2)
        r = z1.intersect(z2)
        a, b, c, d = r
        if a or b or c or d:
            return True
        return False

    def _expose_event_cb(self, layout, event):
        #print "expose event"
        x, y, w, h = event.area
        # redraw the slot rectangle if there's one
        if not self.slotposition == -1:
            if self._area_intersect(x, y, w, h,
                                    self.slotposition, DEFAULT_SIMPLE_SPACING,
                                    DEFAULT_SIMPLE_SPACING, self.childheight):
                self.bin_window.draw_rectangle(self.style.black_gc, True,
                                               self.slotposition, DEFAULT_SIMPLE_SPACING,
                                               DEFAULT_SIMPLE_SPACING, self.childheight)
 
        return False

    def _size_allocate_cb(self, layout, allocation):
        if not self.height == allocation.height:
            self.height = allocation.height
            self.childheight = self.height - 2 * DEFAULT_SIMPLE_SPACING
            #print "height changed, now", self.height
            self._resize_childrens()
            
    def _resize_childrens(self):
        # resize the childrens to self.height
        # also need to move them to their correct position
        # TODO : check if there already at the given position
        # TODO : check if they already have the good size
        pos = 2 * DEFAULT_SIMPLE_SPACING
        for source in self.condensed:
            #print "resizing", source
            widget = self.widgets[source]
            if isinstance(source, TimelineFileSource):
                widget.set_size_request(self.childheight, self.childheight)
                self.move(widget, pos, DEFAULT_SIMPLE_SPACING)
                pos = pos + self.childheight + DEFAULT_SIMPLE_SPACING
            elif isinstance(source, SimpleTransitionWidget):
                widget.set_size_request(self.childheight / 2, self.childheight)
                self.move(widget, pos, DEFAULT_SIMPLE_SPACING)
                pos = pos + self.childheight + DEFAULT_SIMPLE_SPACING
        newwidth = pos + DEFAULT_SIMPLE_SPACING
        self.set_property("width", newwidth)




class SimpleSourceWidget(gtk.DrawingArea):
    """
    Widget for representing a source in simple timeline view
    Takes a TimelineFileSource
    """

    border = 10

    # TODO change the factory argument into a TimelineFileSource
    def __init__(self, filesource):
        gobject.GObject.__init__(self)
        self.gc = None
        self.add_events(gdk.POINTER_MOTION_MASK | gdk.ENTER_NOTIFY_MASK
                        | gdk.LEAVE_NOTIFY_MASK) # enter, leave, pointer-motion
        self.width = 0
        self.height = 0
        self.filesource = filesource
        self.thumbnail = gdk.pixbuf_new_from_file(self.filesource.factory.thumbnail)
        self.thratio = float(self.thumbnail.get_width()) / float(self.thumbnail.get_height())
        self.pixmap = None
        self.namelayout = self.create_pango_layout(os.path.basename(unquote(self.filesource.factory.name)))
        self.lengthlayout = self.create_pango_layout(beautify_length(self.filesource.factory.length))
        #self.layout.set_font_description(pango.FontDescription("sans serif 11"))
        self.connect("expose-event", self._expose_event_cb)
        self.connect("realize", self._realize_cb)
        self.connect("configure-event", self._configure_event_cb)
        self.filesource.connect("start-duration-changed", self._start_duration_changed_cb)
        self.tooltips = gtk.Tooltips()
        self.tooltips.enable()

    def _draw_data(self):
        # actually do the drawing in the pixmap here
        if self.gc:
            self.pixmap = gtk.gdk.Pixmap(self.window, self.width, self.height)
            # background and border
            self.pixmap.draw_rectangle(self.style.bg_gc[gtk.STATE_NORMAL], True,
                                       0, 0, self.width, self.height)
            self.pixmap.draw_rectangle(self.gc, False,
                                       1, 1, self.width - 2, self.height - 2)

            namewidth, nameheight = self.namelayout.get_pixel_size()
            lengthwidth, lengthheight = self.lengthlayout.get_pixel_size()

            # maximal space left for thumbnail
            tw = self.width - 2 * self.border
            th = self.height - 4 * self.border - nameheight - lengthheight

            # try calculating the desired height using tw
            sw = tw
            sh = int(tw / self.thratio)
            if sh > tw or sh > th:
                #   calculate the width using th
                sw = int(th * self.thratio)
                sh = th
            if sw < 1 or sh < 1:
                return
            
            # draw name
            self.pixmap.draw_layout(self.gc, self.border, self.border, self.namelayout)
            
            # draw pixbuf
            subpixbuf = self.thumbnail.scale_simple(sw, sh, gdk.INTERP_BILINEAR)
            self.pixmap.draw_pixbuf(self.gc, subpixbuf, 0, 0,
                                    (self.width - sw) / 2,
                                    (self.height - sh) / 2,
                                    sw, sh)

            # draw length
            self.pixmap.draw_layout(self.gc,
                                    self.width - self.border - lengthwidth,
                                    self.height - self.border - lengthheight,
                                    self.lengthlayout)


    def _configure_event_cb(self, layout, event):
        #print "SimpleSoruceWidget configure_event"
        self.width = event.width
        self.height = event.height
        self.border = event.width / 20
        # draw background pixmap
        if self.gc:
            self._draw_data()
        return False

    def _realize_cb(self, widget):
        #print "SimpleSourceWidget realize"
        self.gc = self.window.new_gc()
        self.gc.set_line_attributes(2, gtk.gdk.LINE_SOLID,
                                    gtk.gdk.CAP_ROUND, gtk.gdk.JOIN_ROUND)
        self.gc.set_background(self.style.white)
        self._draw_data()
        self.tooltips.set_tip(self, "start:\t%s\nsduration:\t%s" % (beautify_length(self.filesource.start),
                                                                    beautify_length(self.filesource.duration)))


    def _expose_event_cb(self, widget, event):
        #print "SimpleSourcewidget expose_event"
        x, y, w, h = event.area
        self.window.draw_drawable(self.gc, self.pixmap,
                                  x, y, x, y, w, h)
        return True

    def _start_duration_changed_cb(self, filesource, start, duration):
        self.tooltips.set_tip(self, "start:\t%s\nduration:\t%s" % (beautify_length(start), beautify_length(duration)))


class SimpleTransitionWidget(gtk.DrawingArea):
    """ Widget for representing a transition in simple timeline view """

    # Change to use a TimelineTransitionEffect
    def __init__(self, transitionfactory):
        gobject.GObject.__init__(self)
        self.gc = None
        self.width = 0
        self.height = 0
        self.pixmap = None
        self.factory = filefactory
        self.connect("expose-event", self._expose_event_cb)
        self.connect("realize", self._realize_cb)
        self.connect("configure-event", self._configure_event_cb)

    def _draw_data(self):
        # actually do the drawing in the pixmap here
        if self.gc:
            self.pixmap = gtk.gdk.Pixmap(self.window, self.width, self.height)
            # background and border
            self.pixmap.draw_rectangle(self.style.white_gc, True,
                                       0, 0, self.width, self.height)
            self.pixmap.draw_rectangle(self.gc, False,
                                       1, 1, self.width - 2, self.height - 2)
            # draw name

    def _configure_event_cb(self, layout, event):
        print "SimpleSoruceWidget configure_event"
        self.width = event.width
        self.height = event.height
        # draw background pixmap
        if self.gc:
            self._draw_data()
        return False

    def _realize_cb(self, widget):
        print "SimpleSourceWidget realize"
        self.gc = self.window.new_gc()
        self.gc.set_line_attributes(2, gtk.gdk.LINE_SOLID,
                                    gtk.gdk.CAP_ROUND, gtk.gdk.JOIN_ROUND)
        self.gc.set_background(self.style.white)
        self._draw_data()

    def _expose_event_cb(self, widget, event):
        #print "SimpleSourcewidget expose_event"
        x, y, w, h = event.area
        print "area", x, y, w, h
        self.window.draw_drawable(self.gc, self.pixmap,
                                  x, y, x, y, w, h)
        return True
    
    
