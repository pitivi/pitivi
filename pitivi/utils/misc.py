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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

# set of utility functions

import sys
import gobject
import gst
import gtk
import bisect
import os
import struct
import time

from pitivi.configure import APPMANUALURL_OFFLINE, APPMANUALURL_ONLINE
from pitivi.utils.signal import Signallable
import pitivi.utils.loggable as log
from gettext import ngettext
try:
    import cProfile
except ImportError:
    pass


UNKNOWN_DURATION = 2 ** 63 - 1

native_endianness = struct.pack('=I', 0x34333231)

big_to_cairo_alpha_mask = struct.unpack('=i', '\xFF\x00\x00\x00')[0]
big_to_cairo_red_mask = struct.unpack('=i', '\x00\xFF\x00\x00')[0]
big_to_cairo_green_mask = struct.unpack('=i', '\x00\x00\xFF\x00')[0]
big_to_cairo_blue_mask = struct.unpack('=i', '\x00\x00\x00\xFF')[0]


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
    return "%01d:%02d:%02d.%03d" % (hours, mins, sec, ms)


def beautify_length(length):
    """
    Converts the given time in nanoseconds to a human readable string
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


def beautify_ETA(length):
    """
    Converts the given time in nanoseconds to a fuzzy estimate,
    intended for progress ETAs, not to indicate a clip's duration.
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

    if not hours and mins < 2 and sec:
        parts.append(ngettext("%d second", "%d seconds", sec) % sec)

    return ", ".join(parts)


def call_false(function, *args, **kwargs):
    """ Helper function for calling an arbitrary function once in the gobject
        mainloop.  Any positional or keyword arguments after the function will
        be provided to the function.

    @param function: the function to call
    @type function: callable({any args})
    @returns: False
    @rtype: bool
    """
    function(*args, **kwargs)
    return False


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
        mid = (low + high) / 2
        if (col[mid] < value):
            low = mid + 1
        else:
            #can't be high = mid-1: here col[mid] >= value,
            #so high can't be < mid if col[mid] == value
            high = mid
    return low


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


def linkDynamic(element, target):

    def pad_added(bin, pad, target):
        compatpad = target.get_compatible_pad(pad)
        if compatpad:
            pad.link_full(compatpad, gst.PAD_LINK_CHECK_NOTHING)
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
def isWritable(path):
    """Check if the file/path is writable"""
    try:
        # Needs to be "rw", not "w", otherwise you'll corrupt files
        f = open(path, "rw")
    except:
        return False
    f.close()
    return True


def uri_is_valid(uri):
    """Checks if the given uri is a valid uri (of type file://)

    Will also check if the size is valid (> 0).

    @param uri: The location to check
    @type uri: C{URI}
    """
    return (gst.uri_is_valid(uri) and
            gst.uri_get_protocol(uri) == "file" and
            len(os.path.basename(gst.uri_get_location(uri))) > 0)


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
            _("%s doesn't yet handle non-local projects") % APPNAME)
    return os.path.isfile(gst.uri_get_location(uri))


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
        mid = (lo + hi) // 2
        if a[mid].start < x.start:
            lo = mid + 1
        else:
            hi = mid
    a.insert(lo, x)


def start_insort_right(a, x, lo=0, hi=None):
    if hi is None:
        hi = len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if x.start < a[mid].start:
            hi = mid
        else:
            lo = mid + 1
    a.insert(lo, x)


def start_bisect_left(a, x, lo=0, hi=None):
    if hi is None:
        hi = len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid].start < x.start:
            lo = mid + 1
        else:
            hi = mid
    return lo


class Infinity(object):
    def __cmp__(self, other):
        if isinstance(other, Infinity):
            return 0

        return 1

infinity = Infinity()


def profile(func, profiler_filename="result.prof"):
    import os.path
    counter = 1
    output_filename = profiler_filename
    while os.path.exists(output_filename):
        output_filename = profiler_filename + str(counter)
        counter += 1

    def _wrapper(*args, **kwargs):
        local_func = func
        cProfile.runctx("result = local_func(*args, **kwargs)", globals(), locals(),
                        filename=output_filename)
        return locals()["result"]

    return _wrapper


def formatPercent(value):
    return "%3d%%" % (value * 100)


def quantize(input, interval):
    return (input // interval) * interval


def show_user_manual():
    time_now = int(time.time())
    for uri in (APPMANUALURL_OFFLINE, APPMANUALURL_ONLINE):
        try:
            gtk.show_uri(None, uri, time_now)
            return
        except Exception, e:
            log.debug("utils", "Failed loading URI %s: %s", uri, e)
            continue
    log.warning("utils", "Failed loading URIs")
    # TODO: Show an error message to the user.


#-----------------------------------------------------------------------------#
#                   Pipeline utils                                            #
def togglePlayback(pipeline):
    if int(pipeline.get_state()[1]) == int(gst.STATE_PLAYING):
        state = gst.STATE_PAUSED
    else:
        state = gst.STATE_PLAYING

    res = pipeline.set_state(state)
    if res == gst.STATE_CHANGE_FAILURE:
        gst.error("Could no set state to %s")
        state = gst.STATE_NULL
        pipeline.set_state(state)

    return state
