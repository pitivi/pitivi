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

"""
Simple view timeline widgets
"""

import os.path
from urllib import unquote
import gobject
import gtk
import gst

import pitivi.instance as instance
from pitivi.timeline.source import TimelineFileSource, TimelineSource
from pitivi.timeline.effects import TimelineTransition
from pitivi.timeline.objects import MEDIA_TYPE_AUDIO, MEDIA_TYPE_VIDEO
from pitivi.configure import get_pixmap_dir
import pitivi.dnd as dnd
from pitivi.signalgroup import SignalGroup

from sourcefactories import beautify_length
from gettext import gettext as _

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

    def __init__(self, **kw):
        gobject.GObject.__init__(self, **kw)

        self.hadjustment = self.get_property("hadjustment")

        # timeline and top level compositions
        self.timeline = instance.PiTiVi.current.timeline
        self.condensed = self.timeline.videocomp.condensed

        # TODO : connect signals for when the timeline changes

        # widgets correspondance dictionnary
        # MAPPING timelineobject => widget
        self.widgets = {}

        # Connect to timeline.  We must remove and reset the callbacks when
        # changing project.
        self.project_signals = SignalGroup()
        self._connectToTimeline(instance.PiTiVi.current.timeline)
        instance.PiTiVi.connect("new-project", self._newProjectCb)

        # size
        self.width = int(DEFAULT_WIDTH)
        self.height = int(DEFAULT_HEIGHT)
        self.childheight = int(DEFAULT_SIMPLE_ELEMENT_HEIGHT)
        self.set_size_request(int(MINIMUM_WIDTH), int(MINIMUM_HEIGHT))
        self.set_property("width", int(DEFAULT_WIDTH))
        self.set_property("height", int(DEFAULT_HEIGHT))

        # event callbacks
        self.connect("expose-event", self._exposeEventCb)
        self.connect("notify::width", self._widthChangedCb)
        self.connect("size-allocate", self._sizeAllocateCb)
        self.connect("realize", self._realizeCb)

        # drag and drop
        self.drag_dest_set(gtk.DEST_DEFAULT_DROP | gtk.DEST_DEFAULT_MOTION,
                           [dnd.FILESOURCE_TUPLE],
                           gtk.gdk.ACTION_COPY)
        self.connect("drag-data-received", self._dragDataReceivedCb)
        self.connect("drag-leave", self._dragLeaveCb)
        self.connect("drag-motion", self._dragMotionCb)
        self.slotposition = -1

        self.draggedelement = None

        self.show_all()


    ## Project callbacks

    def _connectToTimeline(self, timeline):
        self.timeline = timeline
        self.condensed = self.timeline.videocomp.condensed

        self.project_signals.connect(self.timeline.videocomp,
                                     "condensed-list-changed",
                                     None, self._condensedListChangedCb)

    def _newProjectCb(self, unused_pitivi, project):
        assert(instance.PiTiVi.current == project)

        for widget in self.widgets.itervalues():
            self.remove(widget)
        self.widgets = {}

        self._connectToTimeline(instance.PiTiVi.current.timeline)


    ## Timeline callbacks
        
    def _condensedListChangedCb(self, unused_videocomp, clist):
        """ add/remove the widgets """
        gst.debug("condensed list changed in videocomp")
        
        current = self.widgets.keys()
        self.condensed = clist
        
        new = [x for x in clist if not x in current]
        removed = [x for x in current if not x in clist]

        # new elements
        for element in new:
            # add the widget to self.widget
            gst.debug("Adding new element to the layout")
            if isinstance(element, TimelineFileSource):
                widget = SimpleSourceWidget(element)
                widget.connect("delete-me", self._sourceDeleteMeCb, element)
                widget.connect("drag-begin", self._sourceDragBeginCb, element)
                widget.connect("drag-end", self._sourceDragEndCb, element)
            else:
                widget = SimpleTransitionWidget(element)
            self.widgets[element] = widget
            self.put(widget, 0, 0)
            widget.show()

        # removed elements
        for element in removed:
            self.remove(self.widgets[element])
            del self.widgets[element]
            
        self._resizeChildrens()
        # call a redraw

    def _getNearestSourceSlot(self, x):
        """
        returns the nearest file slot position available for the given position
        Returns the value in condensed list position
        Returns n , the element before which it should go
        Return -1 if it's meant to go last
        """
        if not self.condensed or x < 0:
            return 0
        if x > self.width - DEFAULT_SIMPLE_SPACING:
            return -1
        
        pos = DEFAULT_SIMPLE_SPACING
        order = 0
        # TODO Need to avoid getting position between source and transition
        for source in self.condensed:
            if isinstance(source, TimelineSource):
                spacing = self.childheight
            elif isinstance(source, TimelineTransition):
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

    def _getNearestSourceSlotPixels(self, x):
        """
        returns the nearest file slot position available for the given position
        Returns the value in pixels
        """
        if not self.condensed or x < 0:
            return DEFAULT_SIMPLE_SPACING
        if x > self.width - DEFAULT_SIMPLE_SPACING:
            return self.width - 2 * DEFAULT_SIMPLE_SPACING
        
        pos = DEFAULT_SIMPLE_SPACING
        # TODO Need to avoid getting position between source and transition
        for source in self.condensed:
            if isinstance(source, TimelineSource):
                spacing = self.childheight
            elif isinstance(source, TimelineTransition):
                spacing = self.childheight / 2
            else:
                # this shouldn't happen !! The condensed list only contains
                # sources and/or transitions
                pass
            if x <= pos + spacing / 2:
                return pos
            pos = pos + spacing + DEFAULT_SIMPLE_SPACING
        return pos

    def _drawDragSlot(self):
        if self.slotposition == -1:
            return
        self.bin_window.draw_rectangle(self.style.black_gc, True,
                                       self.slotposition, DEFAULT_SIMPLE_SPACING,
                                       DEFAULT_SIMPLE_SPACING, self.childheight)

    def _eraseDragSlot(self):
        if self.slotposition == -1:
            return
        self.bin_window.draw_rectangle(self.style.white_gc, True,
                                       self.slotposition, DEFAULT_SIMPLE_SPACING,
                                       DEFAULT_SIMPLE_SPACING, self.childheight)        

    def _gotFileFactory(self, filefactory, x, unused_y):
        """ got a filefactory at the given position """
        # remove the slot
        self._eraseDragSlot()
        self.slotposition = -1
        if not filefactory or not filefactory.is_video:
            return
        pos = self._getNearestSourceSlot(x)

        # we just add it here, the drawing will be done in the condensed_list
        # callback
        source = TimelineFileSource(factory=filefactory,
                                    media_type=MEDIA_TYPE_VIDEO,
                                    name=filefactory.name)
        gst.debug("_got_filefactory pos : %d" % pos)
        if pos == -1:
            self.timeline.videocomp.appendSource(source)
        elif pos:
            self.timeline.videocomp.insertSourceAfter(source, self.condensed[pos - 1])
        else:
            self.timeline.videocomp.prependSource(source)

    def _moveElement(self, element, x):
        gst.debug("TimelineSource, move %s to x:%d" % (element, x))
        # remove the slot
        self._eraseDragSlot()
        self.slotposition = -1
        pos = self._getNearestSourceSlot(x)
        
        self.timeline.videocomp.moveSource(element, pos)

        # force flush, seek again at current position
        #cur = instance.PiTiVi.playground.getCurrentTimePosition()
        #instance.PiTiVi.playground.seekInCurrent(cur)

    def _widthChangedCb(self, unused_layout, property):
        if not property.name == "width":
            return
        self.width = self.get_property("width")

    def _motionNotifyEventCb(self, layout, event):
        pass


    ## Drag and Drop
    
    def _dragMotionCb(self, unused_layout, unused_context, x, unused_y,
                      unused_timestamp):
        # TODO show where the dragged item would go
        pos = self._getNearestSourceSlotPixels(x + (self.hadjustment.get_value()))
        rpos = self._getNearestSourceSlot(x + self.hadjustment.get_value())
        gst.log("SimpleTimeline x:%d , source would go at %d" % (x, rpos))
        if not pos == self.slotposition:
            if not self.slotposition == -1:
                # erase previous slot position
                self._eraseDragSlot()
            # draw new slot position
            self.slotposition = pos
            self._drawDragSlot()

    def _dragLeaveCb(self, unused_layout, unused_context, unused_timestamp):
        gst.log("SimpleTimeline")
        self._eraseDragSlot()
        self.slotposition = -1
        # TODO remove the drag emplacement

    def _dragDataReceivedCb(self, unused_layout, context, x, y, selection,
                            targetType, timestamp):
        gst.log("SimpleTimeline, targetType:%d, selection.data:%s" % (targetType, selection.data))
        if targetType == dnd.TYPE_PITIVI_FILESOURCE:
            uri = selection.data
        else:
            context.finish(False, False, timestamp)
        x = x + int(self.hadjustment.get_value())
        if self.draggedelement:
            self._moveElement(self.draggedelement, x)
        else:
            self._gotFileFactory(instance.PiTiVi.current.sources[uri], x, y)
        context.finish(True, False, timestamp)
        instance.PiTiVi.playground.switchToTimeline()


    ## Drawing
        
    def _realizeCb(self, unused_layout):
        self.modify_bg(gtk.STATE_NORMAL, self.style.white)

    def _areaIntersect(self, x, y, w, h, x2, y2, w2, h2):
        """ returns True if the area intersects, else False """
        # is zone to the left of zone2
        z1 = gtk.gdk.Rectangle(x, y, w, h)
        z2 = gtk.gdk.Rectangle(x2, y2, w2, h2)
        r = z1.intersect(z2)
        a, b, c, d = r
        if a or b or c or d:
            return True
        return False

    def _exposeEventCb(self, unused_layout, event):
        x, y, w, h = event.area
        # redraw the slot rectangle if there's one
        if not self.slotposition == -1:
            if self._areaIntersect(x, y, w, h,
                                   self.slotposition, DEFAULT_SIMPLE_SPACING,
                                   DEFAULT_SIMPLE_SPACING, self.childheight):
                self.bin_window.draw_rectangle(self.style.black_gc, True,
                                               self.slotposition, DEFAULT_SIMPLE_SPACING,
                                               DEFAULT_SIMPLE_SPACING, self.childheight)
 
        return False

    def _sizeAllocateCb(self, unused_layout, allocation):
        if not self.height == allocation.height:
            self.height = allocation.height
            self.childheight = self.height - 2 * DEFAULT_SIMPLE_SPACING
            self._resizeChildrens()
            
    def _resizeChildrens(self):
        # resize the childrens to self.height
        # also need to move them to their correct position
        # TODO : check if there already at the given position
        # TODO : check if they already have the good size
        pos = 2 * DEFAULT_SIMPLE_SPACING
        for source in self.condensed:
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


    ## Child callbacks
        
    def _sourceDeleteMeCb(self, unused_widget, element):
        # remove this element from the timeline
        self.timeline.videocomp.removeSource(element, collapse_neighbours=True)

    def _sourceDragBeginCb(self, unused_widget, unused_context, element):
        gst.log("Timeline drag beginning on %s" % element)
        if self.draggedelement:
            gst.error("We were already doing a DnD ???")
        self.draggedelement = element
        # this element is starting to be dragged

    def _sourceDragEndCb(self, unused_widget, unused_context, element):
        gst.log("Timeline drag ending on %s" % element)
        if not self.draggedelement == element:
            gst.error("The DnD that ended is not the one that started before ???")
        self.draggedelement = None
        # this element is no longer dragged


class SimpleSourceWidget(gtk.DrawingArea):
    """
    Widget for representing a source in simple timeline view
    Takes a TimelineFileSource
    """

    __gsignals__ = {
        'delete-me' : (gobject.SIGNAL_RUN_LAST,
                       gobject.TYPE_NONE,
                       ( ))
        }

    border = 10

    # TODO change the factory argument into a TimelineFileSource
    def __init__(self, filesource):
        gobject.GObject.__init__(self)
        self.gc = None
        self.add_events(gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.ENTER_NOTIFY_MASK
                        | gtk.gdk.LEAVE_NOTIFY_MASK | gtk.gdk.BUTTON_PRESS_MASK
                        | gtk.gdk.BUTTON_RELEASE_MASK) # enter, leave, pointer-motion
        self.width = 0
        self.height = 0
        self.filesource = filesource
        if self.filesource.factory.thumbnail:
            self.thumbnail = gtk.gdk.pixbuf_new_from_file(self.filesource.factory.thumbnail)
        else:
            self.thumbnail = gtk.gdk.pixbuf_new_from_file(os.path.join(get_pixmap_dir(), "pitivi-video.png"))
        self.thratio = float(self.thumbnail.get_width()) / float(self.thumbnail.get_height())
        self.pixmap = None
        self.namelayout = self.create_pango_layout(os.path.basename(unquote(self.filesource.factory.name)))
        self.lengthlayout = self.create_pango_layout(beautify_length(self.filesource.factory.length))
        #self.layout.set_font_description(pango.FontDescription("sans serif 11"))
        self.connect("expose-event", self._exposeEventCb)
        self.connect("realize", self._realizeCb)
        self.connect("configure-event", self._configureEventCb)
        self.connect("button-press-event", self._buttonPressCb)

        # popup menus
        self._popupMenu = gtk.Menu()
        deleteitem = gtk.MenuItem(_("Remove"))
        deleteitem.connect("activate", self._deleteMenuItemCb)
        deleteitem.show()
        self._popupMenu.append(deleteitem)

        # drag and drop
        self.drag_source_set(gtk.gdk.BUTTON1_MASK,
                             [dnd.URI_TUPLE, dnd.FILESOURCE_TUPLE],
                             gtk.gdk.ACTION_COPY)
        self.connect("drag_data_get", self._dragDataGetCb)

        if not self.filesource.factory.video_info_stream:
            height = 64 * self.thumbnail.get_height() / self.thumbnail.get_width()
        else:
            vi = self.filesource.factory.video_info_stream
            height = 64 * vi.dar.denom / vi.dar.num
        smallthumbnail = self.thumbnail.scale_simple(64, height, gtk.gdk.INTERP_BILINEAR)
        
        self.drag_source_set_icon_pixbuf(smallthumbnail)


    ## Drawing

    def _drawData(self):
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
            subpixbuf = self.thumbnail.scale_simple(sw, sh, gtk.gdk.INTERP_BILINEAR)
            self.pixmap.draw_pixbuf(self.gc, subpixbuf, 0, 0,
                                    (self.width - sw) / 2,
                                    (self.height - sh) / 2,
                                    sw, sh)

            # draw length
            self.pixmap.draw_layout(self.gc,
                                    self.width - self.border - lengthwidth,
                                    self.height - self.border - lengthheight,
                                    self.lengthlayout)


    def _configureEventCb(self, unused_layout, event):
        self.width = event.width
        self.height = event.height
        self.border = event.width / 20
        # draw background pixmap
        if self.gc:
            self._drawData()
        return False

    def _realizeCb(self, unused_widget):
        self.gc = self.window.new_gc()
        self.gc.set_line_attributes(2, gtk.gdk.LINE_SOLID,
                                    gtk.gdk.CAP_ROUND, gtk.gdk.JOIN_ROUND)
        self.gc.set_background(self.style.white)
        self._drawData()

    def _exposeEventCb(self, unused_widget, event):
        x, y, w, h = event.area
        self.window.draw_drawable(self.gc, self.pixmap,
                                  x, y, x, y, w, h)
        return True

    def _deleteMenuItemCb(self, unused_menuitem):
        self.emit('delete-me')

    def _buttonPressCb(self, unused_widget, event):
        gst.debug("button %d" % event.button)
        if event.button == 3:
            self._popupMenu.popup(None,None,None,event.button,event.time)
        else:
            # FIXME: mark as being selected
            pass

    ## Drag and Drop

    def _dragDataGetCb(self, unused_widget, unused_context, selection,
                       targetType, unused_eventTime):
        gst.info("TimelineSource data get, type:%d" % targetType)
        if targetType in [dnd.TYPE_PITIVI_FILESOURCE, dnd.TYPE_URI_LIST]:
            selection.set(selection.target, 8, self.filesource.factory.name)


class SimpleTransitionWidget(gtk.DrawingArea):
    """ Widget for representing a transition in simple timeline view """

    # Change to use a TimelineTransitionEffect
    def __init__(self, transitionfactory):
        gobject.GObject.__init__(self)
        self.gc = None
        self.width = 0
        self.height = 0
        self.pixmap = None
        self.factory = transitionfactory
        self.connect("expose-event", self._exposeEventCb)
        self.connect("realize", self._realizeCb)
        self.connect("configure-event", self._configureEventCb)

    def _drawData(self):
        # actually do the drawing in the pixmap here
        if self.gc:
            self.pixmap = gtk.gdk.Pixmap(self.window, self.width, self.height)
            # background and border
            self.pixmap.draw_rectangle(self.style.white_gc, True,
                                       0, 0, self.width, self.height)
            self.pixmap.draw_rectangle(self.gc, False,
                                       1, 1, self.width - 2, self.height - 2)
            # draw name

    def _configureEventCb(self, unused_layout, event):
        self.width = event.width
        self.height = event.height
        # draw background pixmap
        if self.gc:
            self._drawData()
        return False

    def _realizeCb(self, unused_widget):
        self.gc = self.window.new_gc()
        self.gc.set_line_attributes(2, gtk.gdk.LINE_SOLID,
                                    gtk.gdk.CAP_ROUND, gtk.gdk.JOIN_ROUND)
        self.gc.set_background(self.style.white)
        self._drawData()

    def _exposeEventCb(self, unused_widget, event):
        x, y, w, h = event.area
        self.window.draw_drawable(self.gc, self.pixmap,
                                  x, y, x, y, w, h)
        return True
    
    
