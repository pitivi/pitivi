# PiTiVi , Non-linear video editor
#
#       pitivi/timeline/objects.py
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
Timeline objects
"""

import gobject
import gst

MEDIA_TYPE_NONE = 0
MEDIA_TYPE_AUDIO = 1
MEDIA_TYPE_VIDEO = 2

class TimelineObject(gobject.GObject):
    """
    Base class for all timeline objects

    * Properties
      _ Start/Duration Time
      _ Media Type
      _ Gnonlin Object
      _ Linked Object
	_ Can be None
	_ Must have same duration
      _ Brother object
        _ This is the same object but with the other media_type

    * signals
      _ 'start-duration-changed' : start position, duration position
      _ 'linked-changed' : new linked object
    """

    __gsignals__ = {
        "start-duration-changed" : ( gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE,
                                 (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, )),
        "linked-changed" : ( gobject.SIGNAL_RUN_LAST,
                             gobject.TYPE_NONE,
                             (gobject.TYPE_PYOBJECT, ))
        }
    
##     start = -1  # start time
##     duration = -1   # duration time
##     linked = None       # linked object
##     brother = None      # brother object, the other-media equivalent of this object
##     factory = None      # the Factory with more details about this object
##     gnlobject = None    # The corresponding GnlObject
##     media_type = MEDIA_TYPE_NONE        # The Media Type of this object

    def __init__(self, factory=None, start=-1, duration=-1,
                 media_type=MEDIA_TYPE_NONE, name=""):
        gobject.GObject.__init__(self)
        gst.log("new TimelineObject :%s" % name)
        self.start = -1
        self.duration = -1
        self.linked = None
        self.brother = None
        self.name = name
        # Set factory and media_type and then create the gnlobject
        self.factory = factory
        self.media_type = media_type
        self.gnlobject = self._makeGnlObject()
        self.gnlobject.connect("notify::start", self._startDurationChangedCb)
        self.gnlobject.connect("notify::duration", self._startDurationChangedCb)
        self._setStartDurationTime(start, duration)

    def __repr__(self):
        return '<%s %s>' % (type(self).__name__, self.name)

    def _makeGnlObject(self):
        """ create and return the gnl_object """
        raise NotImplementedError

    def _unlinkObject(self):
        # really unlink the objects
        if self.linked:
            self.linked = None
            self.emit("linked-changed", None)

    def _linkObject(self, object):
        # really do the link
        self.linked = object
        self.emit("linked-changed", self.linked)

    def linkObject(self, object):
        """
        link another object to this one.
        If there already is a linked object ,it will unlink it
        """
        if self.linked and not self.linked == object:
            self.unlinkObject()
        self._linkObject(object)
        pass

    def unlinkObject(self):
        """
        unlink from the current linked object
        """
        self.linked._unlinkObject()
        self._unlinkObject()

    def relinkBrother(self):
        """
        links the object back to it's brother
        """
        # if already linked, unlink from previous
        if self.linked:
            self.unlinkObject()

        # link to brother
        if self.brother:
            self.linkObject(self.brother)

    def getBrother(self, autolink=True):
        """
        returns the brother element if it's possible,
        if autolink, then automatically link it to this element
        """
        if not self.brother:
            self.brother = self._makeBrother()
            if not self.brother:
                return None
        if autolink and not self.linked == self.brother:
            self.relinkBrother()
        return self.brother

    def _makeBrother(self):
        """
        Make the exact same object for the other media_type
        implemented in subclasses
        """
        raise NotImplementedError
    
    def _setStartDurationTime(self, start=-1, duration=-1):
        # really modify the start/duration time
        self.gnlobject.info("start:%s , duration:%s" %( gst.TIME_ARGS(start),
                                                        gst.TIME_ARGS(duration)))
        if not duration == -1 and not self.duration == duration:
            self.duration = duration
            self.gnlobject.set_property("duration", long(duration))
        if not start == -1 and not self.start == start:
            self.start = start
            self.gnlobject.set_property("start", long(start))
            
    def setStartDurationTime(self, start=-1, duration=-1):
        """ sets the start and/or duration time """
        self._setStartDurationTime(start, duration)
        if self.linked:
            self.linked._setStartDurationTime(start, duration)

    def _startDurationChangedCb(self, gnlobject, property):
        """ start/duration time has changed """
        self.gnlobject.debug("property:%s" % property.name)
        start = -1
        duration = -1
        if property.name == "start":
            start = gnlobject.get_property("start")
            if start == self.start:
                start = -1
            else:
                self.start = long(start)
        elif property.name == "duration":
            duration = gnlobject.get_property("duration")
            if duration == self.duration:
                duration = -1
            else:
                self.gnlobject.debug("duration changed:%s" % gst.TIME_ARGS(duration))
                self.duration = long(duration)
        #if not start == -1 or not duration == -1:
        self.emit("start-duration-changed", self.start, self.duration)
            
