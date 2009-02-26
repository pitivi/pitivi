#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       utils.py
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

# set of utility functions

import gst, bisect
from pitivi.signalinterface import Signallable
import pitivi.log.log as log

UNKNOWN_DURATION = 2 ** 63 - 1

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
    if mins < 60:
        return "%02dm%02ds" % (mins, sec)
    hours = mins / 60
    mins = mins % 60
    return "%02dh%02dm%02ds" % (hours, mins, sec)

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
            log.debug("probe","%s %r", section, list(data.parse_new_segment()))
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

def filter(caps):
    f = gst.element_factory_make("capsfilter")
    f.props.caps = gst.caps_from_string(caps)
    return f

class PropertyChangeTracker(object, Signallable):
    def __init__(self, timeline_object):
        self.properties = {}

        for property_name in self.property_names:
            self.properties[property_name] = \
                    getattr(timeline_object, property_name)

            timeline_object.connect(property_name + '-changed',
                    self._propertyChangedCb, property_name)

    def _propertyChangedCb(self, timeline_object, value, property_name):
        old_value = self.properties[property_name]
        self.properties[property_name] = value

        self.emit(property_name + '-changed', timeline_object, old_value, value)

