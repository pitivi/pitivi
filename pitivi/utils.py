#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       utils.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
# Copyright (c) 2009, Alessandro Decina <alessandro.d@gmail.com>
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

# set of utility functions

import sys
import gobject
import gst, bisect
import os
from pitivi.signalinterface import Signallable
import pitivi.log.log as log
from gettext import ngettext
import cProfile

UNKNOWN_DURATION = 2 ** 63 - 1

def between(a, b, c):
    return (a <= b) and (b <= c)

def time_to_string(value):
    """
    Converts the given time in nanoseconds to a human readable string

    Format HH:MM:SS.XXX
    """
    if value == gst.CLOCK_TIME_NONE:
        return "--:--:--.---"
    ms = value / gst.MSECOND
    sec = ms / 1000
    ms = ms % 1000
    mins = sec / 60
    sec = sec % 60
    hours = mins / 60
    mins = mins % 60
    return "%02d:%02d:%02d.%03d" % (hours, mins, sec, ms)

def beautify_length(length):
    """
    Converts the given time in nanoseconds to a human readable string

    Format HHhMMmSSs
    """
    sec = length / gst.SECOND
    mins = sec / 60
    sec = sec % 60
    hours = mins / 60
    mins = mins % 60

    parts = []
    if hours:
        parts.append(ngettext("%d hour", "%d hours", hours) % hours)

    if mins:
        parts.append(ngettext("%d minute", "%d minutes", mins) % mins)

    if not hours and sec:
        parts.append(ngettext("%d second", "%d seconds", sec) % sec)

    return ", ".join(parts)

def bin_contains(bin, element):
    """ Returns True if the bin contains the given element, the search is recursive """
    if not isinstance(bin, gst.Bin):
        return False
    if not isinstance(element, gst.Element):
        return False
    for elt in bin:
        if element is elt:
            return True
        if isinstance(elt, gst.Bin) and bin_contains(elt, element):
            return True
    return False

# Python re-implementation of binary search algorithm found here:
# http://en.wikipedia.org/wiki/Binary_search
#
# This is the iterative version without the early termination branch, which
# also tells us the element of A that are nearest to Value, if the element we
# want is not found. This is useful for implementing edge snaping in the UI,
# where we repeatedly search through a list of control points for the one
# closes to the cursor. Because we don't care whether the cursor position
# matches the list, this function returns the index of the lement closest to
# value in the array.

def binary_search(col, value):
    low = 0
    high = len(col)
    while (low < high):
        mid = (low + high)/2
        if (col[mid] < value):
            low = mid + 1
        else:
            #can't be high = mid-1: here col[mid] >= value,
            #so high can't be < mid if col[mid] == value
            high = mid;
    return low

# Returns the element of seq nearest to item, and the difference between them

def closest_item(seq, item, lo=0):
    index = bisect.bisect(seq, item, lo)
    if index >= len(seq):
        index = len(seq) - 1
    res = seq[index]
    diff = abs(res - item)

    # binary_search returns largest element closest to item.
    # if there is a smaller element...
    if index - 1 >= 0:
        res_a = seq[index - 1]
        # ...and it is closer to the pointer...
        diff_a = abs(res_a - item)
        if diff_a < diff:
            # ...use it instead.
            res = res_a
            diff = diff_a
            index = index - 1

    return res, diff, index

def argmax(func, seq):
    """return the element of seq that gives max(map(func, seq))"""
    def compare(a1, b1):
        if a1[0] > b1[0]:
            return a1
        return b1
    # using a generator expression here should save memory
    objs = ((func(val), val) for val in seq)
    return reduce(compare, objs)[1]

def same(seq):
    i = iter(seq)
    first = i.next()
    for item in i:
        if first != item:
            return None
    return first

def data_probe(pad, data, section=""):
    """Callback to use for gst.Pad.add_*_probe.

    The extra argument will be used to prefix the debug messages
    """
    if section == "":
        section = "%s:%s" % (pad.get_parent().get_name(), pad.get_name())
    if isinstance(data, gst.Buffer):
        log.debug("probe","%s BUFFER timestamp:%s , duration:%s , size:%d , offset:%d , offset_end:%d",
                  section, gst.TIME_ARGS(data.timestamp), gst.TIME_ARGS(data.duration),
                  data.size, data.offset, data.offset_end)
        if data.flags & gst.BUFFER_FLAG_DELTA_UNIT:
            log.debug("probe","%s DELTA_UNIT", section)
        if data.flags & gst.BUFFER_FLAG_DISCONT:
            log.debug("probe","%s DISCONT", section)
        if data.flags & gst.BUFFER_FLAG_GAP:
            log.debug("probe","%s GAP", section)
        log.debug("probe","%s flags:%r", section, data.flags)
    else:
        log.debug("probe","%s EVENT %s", section, data.type)
        if data.type == gst.EVENT_NEWSEGMENT:
            upd, rat, fmt, start, stop, pos = data.parse_new_segment()
            log.debug("probe","%s Update:%r rate:%f fmt:%s, start:%s, stop:%s, pos:%s",
                      section, upd, rat, fmt, gst.TIME_ARGS(start),
                      gst.TIME_ARGS(stop), gst.TIME_ARGS(pos))
    return True

def linkDynamic(element, target):

    def pad_added(bin, pad, target):
        if target.get_compatible_pad(pad):
            element.link(target)
    element.connect("pad-added", pad_added, target)

def element_make_many(*args):
    return tuple((gst.element_factory_make(arg) for arg in args))

def pipeline(graph):
    E = graph.iteritems()
    V = graph.iterkeys()
    p = gst.Pipeline()
    p.add(*V)
    for u, v in E:
        if v:
            try:
                u.link(v)
            except gst.LinkError:
                linkDynamic(u, v)
    return p

def filter_(caps):
    f = gst.element_factory_make("capsfilter")
    f.props.caps = gst.caps_from_string(caps)
    return f


## URI functions


def uri_is_valid(uri):
    """Checks if the given uri is a valid uri (of type file://)

    Will also check if the size is valid (> 0).

    @param uri: The location to check
    @type uri: C{URI}
    """
    res = gst.uri_is_valid(uri) and gst.uri_get_protocol(uri) == "file"
    if res:
        return len(os.path.basename(gst.uri_get_location(uri))) > 0
    return res

def uri_is_reachable(uri):
    """ Check whether the given uri is reachable and we can read/write
    to it.

    @param uri: The location to check
    @type uri: C{URI}
    @return: C{True} if the uri is reachable.
    @rtype: C{bool}
    """
    if not uri_is_valid(uri):
        raise NotImplementedError(
            # Translators: "non local" means the project is not stored
            # on a local filesystem
            _("%s doesn't yet handle non local projects") % APPNAME)
    return os.path.isfile(gst.uri_get_location(uri))

class PropertyChangeTracker(Signallable):

    __signals__ = {}

    def __init__(self):
        self.properties = {}
        self.obj = None

    def connectToObject(self, obj):
        self.obj = obj
        self.properties = self._takeCurrentSnapshot(obj)
        for property_name in self.property_names:
            signal_name = property_name + '-changed'
            self.__signals__[signal_name] = []
            obj.connect(signal_name,
                    self._propertyChangedCb, property_name)

    def _takeCurrentSnapshot(self, obj):
        properties = {}
        for property_name in self.property_names:
            properties[property_name] = \
                    getattr(obj, property_name.replace("-", "_"))

        return properties

    def disconnectFromObject(self, obj):
        self.obj = None
        obj.disconnect_by_func(self._propertyChangedCb)

    def _propertyChangedCb(self, object, value, property_name):
        old_value = self.properties[property_name]
        self.properties[property_name] = value

        self.emit(property_name + '-changed', object, old_value, value)

class Seeker(Signallable):
    __signals__ = {'seek': ['position', 'format']}

    def __init__(self, timeout):
        self.timeout = timeout
        self.pending_seek_id = None
        self.position = None
        self.format = None

    def seek(self, position, format=gst.FORMAT_TIME, on_idle=False):
        self.position = position
        self.format = format

        if self.pending_seek_id is None:
            if on_idle:
                gobject.idle_add(self._seekTimeoutCb)
            else:
                self._seekTimeoutCb()
            self.pending_seek_id = self._scheduleSeek(self.timeout,
                    self._seekTimeoutCb)

    def _scheduleSeek(self, timeout, callback):
        return gobject.timeout_add(timeout, callback)

    def _seekTimeoutCb(self):
        self.pending_seek_id = None
        if self.position != None and self.format != None:
            position, self.position = self.position, None
            format, self.format = self.format, None
            self.emit('seek', position, format)
        return False

def get_filesystem_encoding():
    return sys.getfilesystemencoding() or "utf-8"

def get_controllable_properties(element):
    """
    Returns a list of controllable properties for the given
    element (and child if it's a container).

    The list is made of tuples containing:
    * The GstObject
    * The GParamspec
    """
    log.debug("utils", "element %r, %d", element, isinstance(element, gst.Bin))
    res = []
    if isinstance(element, gst.Bin):
        for child in element.elements():
            res.extend(get_controllable_properties(child))
    else:
        for prop in gobject.list_properties(element):
            if prop.flags & gst.PARAM_CONTROLLABLE:
                log.debug("utils", "adding property %r", prop)
                res.append((element, prop))
    return res

def start_insort_left(a, x, lo=0, hi=None):
    if hi is None:
        hi = len(a)
    while lo < hi:
        mid = (lo+hi)//2
        if a[mid].start < x.start: lo = mid+1
        else: hi = mid
    a.insert(lo, x)

def start_insort_right(a, x, lo=0, hi=None):
    if hi is None:
        hi = len(a)
    while lo < hi:
        mid = (lo+hi)//2
        if x.start < a[mid].start: hi = mid
        else: lo = mid+1
    a.insert(lo, x)

def start_bisect_left(a, x, lo=0, hi=None):
    if hi is None:
        hi = len(a)
    while lo < hi:
        mid = (lo+hi)//2
        if a[mid].start < x.start: lo = mid+1
        else: hi = mid
    return lo

class Infinity(object):
    def __cmp__(self, other):
        if isinstance(other, Infinity):
            return 0

        return 1

infinity = Infinity()

def findObject(obj, objects):
    low = 0
    high = len(objects)
    while low < high:
        low = start_bisect_left(objects, obj, lo=low)
        if low == high:
            break

        if objects[low] is obj:
            return low
        else:
            low = low + 1

    return low

def getPreviousObject(obj, objects, priority=-1, skip=None):
    if priority == -1:
        priority = obj.priority

    obj_index = findObject(obj, objects)
    if obj_index is None:
        raise Exception("woot this should never happen")
    # check if there are same-start objects
    prev_obj_index = obj_index + 1
    while prev_obj_index < len(objects):
        prev_obj = objects[prev_obj_index]
        prev_obj_index += 1
        if skip is not None and skip(prev_obj):
            continue

        if prev_obj.start != obj.start:
            break

        if priority is None or prev_obj.priority == priority:
            return prev_obj


    # check if there are objects with start < obj.start
    prev_obj_index = obj_index - 1
    while prev_obj_index >= 0:
        prev_obj = objects[prev_obj_index]
        if (priority is None or prev_obj.priority == priority) \
                and (skip is None or not skip(prev_obj)):
            return prev_obj

        prev_obj_index -= 1

    return None

def getNextObject(obj, objects, priority=-1, skip=None):
    if priority == -1:
        priority = obj.priority

    obj_index = findObject(obj, objects)
    next_obj_index = obj_index + 1
    objs_len = len(objects)
    while next_obj_index < objs_len:
        next_obj = objects[next_obj_index]
        if (priority is None or next_obj.priority == priority) and \
                (skip is None or not skip(next_obj)):
            return next_obj

        next_obj_index += 1

    return None


class CachedFactoryList(object):
    def __init__(self, factoryFilter=None):
        self._factoryFilter = factoryFilter
        self._factories = None
        self._registry = gst.registry_get_default()
        self._registry.connect("feature-added", self._registryFeatureAddedCb)

    def get(self):
        if self._factories is None:
            self._buildFactories()

        return self._factories

    def _buildFactories(self):
        # build the cache
        log.debug("utils", "Getting factories list")
        factories = self._registry.get_feature_list(gst.ElementFactory)
        if self._factoryFilter is not None:
            log.debug("utils", "filtering")
            factories = filter(self._factoryFilter, factories)

        log.debug("utils", "Sorting by rank")
        factories.sort(key=lambda factory: factory.get_rank(), reverse=True)
        self._factories = factories
        log.debug("utils", "Cached factories is now %r", self._factories)

    def _registryFeatureAddedCb(self, registry, feature):
        # invalidate the cache
        log.warning("utils", "New feature added, invalidating cached factories")
        self._factories = None

def profile(func, profiler_filename="result.prof"):
    import os.path
    counter = 1
    output_filename = profiler_filename
    while os.path.exists(output_filename):
        output_filename = profiler_filename + str(counter)
        counter += 1

    def _wrapper(*args,**kwargs):
        local_func = func
        cProfile.runctx("result = local_func(*args, **kwargs)", globals(), locals(),
                        filename=output_filename)
        return locals()["result"]

    return _wrapper

def formatPercent(value):
    return "%3d%%" % (value * 100)
