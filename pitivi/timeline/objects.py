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

import weakref
from random import randint
import gobject
import gst
from pitivi.serializable import Serializable
from pitivi.objectfactory import ObjectFactory

MEDIA_TYPE_NONE = 0
MEDIA_TYPE_AUDIO = 1
MEDIA_TYPE_VIDEO = 2

## * Object Hierarchy

##   Object
##    |
##    +---- Source
##    |    |
##    |    +---- FileSource
##    |    |
##    |    +---- LiveSource
##    |    |
##    |    +---- Composition
##    |
##    +---- Effect
##         |
##         +---- Simple Effect (1->1)
##         |
##         +---- Transition
##         |
##         +---- Complex Effect (N->1)

class BrotherObjects(gobject.GObject, Serializable):
    """
    Base class for objects that can have a brother and be linked to something else

    Save/Load properties:
    * (optional) 'linked' (int) : UID of linked object
    * (optional) 'brother' (int) : UID of brother object
    """

    __data_type__ = "timeline-brother-objects"

    __gsignals__ = {
        "linked-changed" : (gobject.SIGNAL_RUN_LAST,
                            gobject.TYPE_NONE,
                            (gobject.TYPE_PYOBJECT, ))
        }

    # UID (int) => object (BrotherObjects) mapping.
    __instances__ = weakref.WeakValueDictionary()

    # dictionnary of objects waiting for pending objects for completion
    # pending UID (int) => objects (list of BrotherObjects and extra field)
    __waiting_for_pending_objects__ = {}

    def __init__(self, **unused_kw):
        gobject.GObject.__init__(self)
        self.linked = None
        self.brother = None
        self.uid = -1

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
        self.linked._linkObject(self)
        pass

    def getLinkedObject(self):
        """
        Returns the object currently linked to this one.
        This is NOT guaranteed to be the brother
        """
        return self.linked

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

    def setBrother(self, brother, autolink=True):
        """
        Force a brother on an object.
        This can be useful if it's the parent of the object that knows
        what his brother is.
        Use with caution
        """
        gst.log("brother:%r , autolink:%r" % (brother, autolink))
        self.brother = brother
        # set ourselves as our brother's brother
        self.brother.brother = self
        if autolink:
            self.relinkBrother()

    def _makeBrother(self):
        """
        Make the exact same object for the other media_type
        implemented in subclasses
        """
        raise NotImplementedError

    # Serializable methods

    def toDataFormat(self):
        ret = Serializable.toDataFormat(self)
        ret["uid"] = self.getUniqueID()
        if self.brother:
            ret["brother-uid"] = self.brother.getUniqueID()
        if self.linked:
            ret["linked-uid"] = self.linked.getUniqueID()
        return ret

    def fromDataFormat(self, obj):
        Serializable.fromDataFormat(self, obj)
        self.setUniqueID(obj["uid"])

        if "brother-uid" in obj:
            brother = BrotherObjects.getObjectByUID(obj["brother-uid"])
            if not brother:
                BrotherObjects.addPendingObjectRequest(self, obj["brother-uid"], "brother")
            else:
                self.setBrother(brother)

        if "linked-uid" in obj:
            linked = BrotherObjects.getObjectByUID(obj["linked-uid"])
            if not linked:
                BrotherObjects.addPendingObjectRequest(self, obj["linked-uid"], "linked")
            else:
                self.linkObject(linked)

    def pendingObjectCreated(self, obj, field):
        gst.log("field:%s, obj:%r" % (field, obj))
        if field == "brother":
            self.setBrother(obj, autolink=False)
        elif field == "linked":
            self.linkObject(obj)

    # Unique ID methods

    def getUniqueID(self):
        if self.uid == -1:
            i = randint(0, 2**32)
            while i in BrotherObjects.__instances__:
                i = randint(0, 2 ** 32)
            self.uid = i
            gst.log("Assigned uid %d to %r, adding to __instances__" % (self.uid, self))
            BrotherObjects.__instances__[self.uid] = self
        return self.uid

    def setUniqueID(self, uid):
        if not self.uid == -1:
            raise Exception("Trying to set uid [%d] on an object that already has one [%d]" % (uid, self.uid))
            return

        if uid in BrotherObjects.__instances__:
            raise Exception("Uid [%d] is already in use by another object [%r]" % (uid, BrotherObjects.__instances__[uid]))
            return

        self.uid = uid
        gst.log("Recording __instances__[uid:%d] = %r" % (self.uid, self))
        BrotherObjects.__instances__[self.uid] = self

        # Check if an object needs to be informed of our creation
        self._haveNewID(self.uid)

    @classmethod
    def getObjectByUID(cls, uid):
        """
        Returns the object with the given uid if it exists.
        Returns None if no object with the given uid exist.
        """
        gst.log("uid:%d" % uid)
        if uid in cls.__instances__:
            return cls.__instances__[uid]
        return None

    # Delayed object creation methods

    def _haveNewID(self, uid):
        """
        This method is called when an object gets a new ID.
        It will check to see if any object needs to be informed of the creation
        of this object.
        """
        gst.log("uid:%d" % uid)
        if uid in BrotherObjects.__waiting_for_pending_objects__ and uid in BrotherObjects.__instances__:
            for obj, extra in BrotherObjects.__waiting_for_pending_objects__[uid]:
                # obj is a weakref.Proxy object
                obj.pendingObjectCreated(BrotherObjects.__instances__[uid], extra)
            del BrotherObjects.__waiting_for_pending_objects__[uid]


    @classmethod
    def addPendingObjectRequest(cls, obj, uid, extra=None):
        """
        Ask to be called when the object with the given uid is created.
        obj : calling object
        uid : uid of the object we need to be informed of creation
        extra : extradata with which obj's callback will be called

        The class will call the calling object's when the requested object
        is available using the following method call:
        obj.pendingObjectCreated(new_object, extra)
        """
        if not uid in cls.__waiting_for_pending_objects__:
            cls.__waiting_for_pending_objects__[uid] = []
        cls.__waiting_for_pending_objects__[uid].append((weakref.proxy(obj), extra))

gobject.type_register(BrotherObjects)

class TimelineObject(BrotherObjects):
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

    Save/Load properties
    * 'start' (int) : start position in nanoseconds
    * 'duration' (int) : duration in nanoseconds
    * 'name' (string) : name of the object
    * 'factory' (int) : UID of the objectfactory
    * 'mediatype' (int) : media type of the object
    """

    __data_type__ = "timeline-object"

    # Set this to False in sub-classes that don't require a factory in
    # order to create their gnlobject.
    __requires_factory__ = True

    __gsignals__ = {
        "start-duration-changed" : ( gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE,
                                 (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, ))
        }

    def __init__(self, factory=None, start=-1, duration=-1,
                 media_type=MEDIA_TYPE_NONE, name="", **kwargs):
        BrotherObjects.__init__(self, **kwargs)
        self.name = name
        gst.log("new TimelineObject :%s %r" % (name, self))
        self.start = start
        self.duration = duration
        self.factory = None
        # Set factory and media_type and then create the gnlobject
        self.media_type = media_type
        self.gnlobject = None
        self._setFactory(factory)

    def __repr__(self):
        if hasattr(self, "name"):
            return "<%s '%s' at 0x%x>" % (type(self).__name__, self.name, id(self))
        return "<%s at 0x%x>" % (type(self).__name__, id(self))

    def _makeGnlObject(self):
        """ create and return the gnl_object """
        raise NotImplementedError

    def _setFactory(self, factory):
        if self.factory:
            gst.warning("Can't set a factory, this object already has one : %r" % self.factory)
            return
        gst.log("factory:%r requires factory:%r" % (factory, self.__requires_factory__))
        self.factory = factory
        if not self.__requires_factory__ or self.factory:
            gst.log("%r Creating associated gnlobject" % self)
            self.gnlobject = self._makeGnlObject()
            self.gnlobject.connect("notify::start", self._startDurationChangedCb)
            self.gnlobject.log("got gnlobject !")
            self.gnlobject.connect("notify::duration", self._startDurationChangedCb)
            self._setStartDurationTime(self.start, self.duration, True)

    def _setStartDurationTime(self, start=-1, duration=-1, force=False):
        # really modify the start/duration time
        self.gnlobject.info("start:%s , duration:%s" %( gst.TIME_ARGS(start),
                                                        gst.TIME_ARGS(duration)))
        if not duration == -1 and (not self.duration == duration or force):
            self.duration = duration
            self.gnlobject.set_property("duration", long(duration))
        if not start == -1 and (not self.start == start or force):
            self.start = start
            self.gnlobject.set_property("start", long(start))

    def setStartDurationTime(self, start=-1, duration=-1):
        """ sets the start and/or duration time """
        self._setStartDurationTime(start, duration)
        if self.linked:
            self.linked._setStartDurationTime(start, duration)

    def _startDurationChangedCb(self, gnlobject, property):
        """ start/duration time has changed """
        gst.log("self:%r , gnlobject:%r" % (self, gnlobject))
        if not gnlobject == self.gnlobject:
            gst.warning("We're receiving signals from an object we dont' control (self.gnlobject:%r, gnlobject:%r)" % (self.gnlobject, gnlobject))
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


    # Serializable methods

    def toDataFormat(self):
        ret = BrotherObjects.toDataFormat(self)
        ret["start"] = self.start
        ret["duration"] = self.duration
        ret["name"] = self.name
        if self.factory:
            ret["factory-uid"] = self.factory.getUniqueID()
        ret["media_type"] = self.media_type
        return ret

    def fromDataFormat(self, obj):
        BrotherObjects.fromDataFormat(self, obj)
        self.start = obj["start"]
        self.duration = obj["duration"]

        self.name = obj["name"]

        self.media_type = obj["media_type"]

        if "factory-uid" in obj:
            factory = ObjectFactory.getObjectByUID(obj["factory-uid"])
            gst.log("For factory-id %d we got factory %r" % (obj["factory-uid"], factory))
            if not factory:
                ObjectFactory.addPendingObjectRequest(self, obj["factory-uid"], "factory")
            else:
                self._setFactory(factory)

    def pendingObjectCreated(self, obj, field):
        if field == "factory":
            self._setFactory(obj)
        else:
            BrotherObjects.pendingObjectCreated(self, obj, field)
