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
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk
import hashlib
import os
import struct
import time
import threading

from gettext import gettext as _

from urlparse import urlsplit, urlunsplit, urlparse
from urllib import quote, unquote

import pitivi.utils.loggable as log
from pitivi.utils.threads import Thread

from pitivi.configure import APPMANUALURL_OFFLINE, APPMANUALURL_ONLINE, APPNAME

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


def print_ns(time):
    if time == Gst.CLOCK_TIME_NONE:
        return "CLOCK_TIME_NONE"

    return str(time / (Gst.SECOND * 60 * 60)) + ':' + \
           str((time / (Gst.SECOND * 60)) % 60) + ':' + \
           str((time / Gst.SECOND) % 60) + ':' + \
           str(time % Gst.SECOND)


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
    if not isinstance(bin, Gst.Bin):
        return False
    if not isinstance(element, Gst.Element):
        return False
    for elt in bin:
        if element is elt:
            return True
        if isinstance(elt, Gst.Bin) and bin_contains(elt, element):
            return True
    return False


def in_devel():
    """
    Returns True if the current PiTiVi instance is run from a git checkout
    """
    try:
        # This code is the same as in the configure files
        rd = '/'.join(os.path.dirname(os.path.abspath(__file__)).split('/')[:-1])
        return os.path.exists(os.path.join(rd, '.git'))
    except:
        return False


#------------------------------ URI helpers   --------------------------------#
def isWritable(path):
    """Check if the file/path is writable"""
    if os.path.isdir(path):
        # The given path is an existing directory.
        # To properly check if it is writable, you need to use os.access.
        return os.access(path, os.W_OK)
    else:
        # The given path is supposed to be a file.
        # Avoid using open(path, "w"), as it might corrupt existing files.
        # And yet, even if the parent directory is actually writable,
        # open(path, "rw") will IOError if the file doesn't already exist.
        # Therefore, simply check the directory permissions instead:
        return os.access(os.path.dirname(path), os.W_OK)
    return True


def uri_is_valid(uri):
    """Checks if the given uri is a valid uri (of type file://)

    Will also check if the size is valid (> 0).

    @param uri: The location to check
    @type uri: C{URI}
    """
    return (Gst.uri_is_valid(uri) and
            Gst.uri_get_protocol(uri) == "file" and
            len(os.path.basename(Gst.uri_get_location(uri))) > 0)


def uri_is_reachable(uri):
    """ Check whether the given uri is reachable by GStreamer.

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
    return os.path.isfile(Gst.uri_get_location(uri))


def get_filesystem_encoding():
    return sys.getfilesystemencoding() or "utf-8"


def path_from_uri(uri):
    """
    Return a human-readable path that can be used with python's os.path
    """
    foo = urlparse(uri)
    path = foo.netloc + foo.path
    return unquote(path)


def quote_uri(uri):
    """
    Encode a URI according to RFC 2396, without touching the file:/// part.
    """
    parts = list(urlsplit(uri, allow_fragments=False))
    # Make absolutely sure the string is unquoted before quoting again!
    raw = unquote(parts[2])
    # For computing thumbnail md5 hashes in the source list, we must adhere to
    # RFC 2396. However, urllib's quote method only uses alphanumeric and "/"
    # as their safe chars. We need to add both the reserved and unreserved chars
    RFC_2396_RESERVED = ";/?:@&=+$,"
    RFC_2396_UNRESERVED = "-_.!~*'()"
    URIC_SAFE_CHARS = "/" + "%" + RFC_2396_RESERVED + RFC_2396_UNRESERVED
    parts[2] = quote(raw, URIC_SAFE_CHARS)
    uri = urlunsplit(parts)
    return uri


class PathWalker(Thread):
    """
    Thread for recursively searching in a list of directories
    """

    def __init__(self, paths, callback):
        Thread.__init__(self)
        self.log("New PathWalker for %s" % paths)
        self.paths = paths
        self.callback = callback
        self.stopme = threading.Event()

    def process(self):
        for folder in self.paths:
            self.log("folder %s" % folder)
            if folder.startswith("file://"):
                folder = unquote(folder[len("file://"):])
            for path, dirs, files in os.walk(folder):
                if self.stopme.isSet():
                    return
                uris = []
                for afile in files:
                    uris.append(quote_uri("file://%s" %
                            os.path.join(path, afile)))
                if uris:
                    self.callback(uris)

    def abort(self):
        self.stopme.set()


def hash_file(uri):
    """Hashes the first 256KB of the specified file"""
    sha256 = hashlib.sha256()
    with open(uri, "rb") as file:
        for _ in range(1024):
            chunk = file.read(256)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


#------------------------------ Gst helpers   --------------------------------#
def get_controllable_properties(element):
    """
    Returns a list of controllable properties for the given
    element (and child if it's a container).

    The list is made of tuples containing:
    * The GstObject
    * The GParamspec
    """
    log.debug("utils", "element %r, %d", element, isinstance(element, Gst.Bin))
    res = []
    if isinstance(element, Gst.Bin):
        for child in element.elements():
            res.extend(get_controllable_properties(child))
    else:
        for prop in GObject.list_properties(element):
            if prop.flags & Gst.PARAM_CONTROLLABLE:
                log.debug("utils", "adding property %r", prop)
                res.append((element, prop))
    return res


def linkDynamic(element, target):

    def pad_added(bin, pad, target):
        compatpad = target.get_compatible_pad(pad)
        if compatpad:
            pad.link_full(compatpad, Gst.PAD_LINK_CHECK_NOTHING)
    element.connect("pad-added", pad_added, target)


def element_make_many(*args):
    return tuple((Gst.ElementFactory.make(arg) for arg in args))


def pipeline(graph):
    E = graph.iteritems()
    V = graph.iterkeys()
    p = Gst.Pipeline()
    p.add(*V)
    for u, v in E:
        if v:
            try:
                u.link(v)
            except Gst.LinkError:
                linkDynamic(u, v)
    return p


def filter_(caps):
    f = Gst.ElementFactory.make("capsfilter")
    f.props.caps = Gst.caps_from_string(caps)
    return f


#-------------------------- Sorting helpers   --------------------------------#
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


def show_user_manual(page=None):
    """
    Display the user manual with Yelp.
    Optional: for contextual help, a page ID can be specified.
    """
    time_now = int(time.time())
    for uri in (APPMANUALURL_OFFLINE, APPMANUALURL_ONLINE):
        if page is not None:
            uri += "#" + page
        try:
            Gtk.show_uri(None, uri, time_now)
            return
        except Exception, e:
            log.debug("utils", "Failed loading URI %s: %s", uri, e)
            continue
    log.warning("utils", "Failed loading URIs")
    # TODO: Show an error message to the user.
