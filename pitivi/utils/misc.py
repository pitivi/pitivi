# Pitivi video editor
#
#       pitivi/utils/misc.py
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

import bisect
import hashlib
import os
import threading
import time
from urllib.parse import urlparse, unquote, urlsplit

from gi.repository import GLib
from gi.repository import Gst
from gi.repository import Gtk

from gettext import gettext as _

import pitivi.utils.loggable as log
from pitivi.utils.threads import Thread
from pitivi.configure import APPMANUALURL_OFFLINE, APPMANUALURL_ONLINE, APPNAME


def format_ns(timestamp):
    if timestamp is None:
        return None
    if timestamp == Gst.CLOCK_TIME_NONE:
        return "CLOCK_TIME_NONE"

    return str(timestamp / (Gst.SECOND * 60 * 60)) + ':' + \
        str((timestamp / (Gst.SECOND * 60)) % 60) + ':' + \
        str((timestamp / Gst.SECOND) % 60) + ':' + \
        str(timestamp % Gst.SECOND)


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


# ------------------------------ URI helpers --------------------------------

def isWritable(path):
    """
    Return whether the file/path is writable.
    """
    try:
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
    except UnicodeDecodeError:
        unicode_error_dialog()


def uri_is_valid(uri):
    """
    Checks if the given uri is a valid uri (of type file://)

    Will also check if the size is valid (> 0).

    @param uri: The location to check
    @type uri: C{str}
    """
    return (Gst.uri_is_valid(uri) and
            Gst.uri_get_protocol(uri) == "file" and
            len(os.path.basename(Gst.uri_get_location(uri))) > 0)


def uri_is_reachable(uri):
    """
    Check whether the given uri is reachable by GStreamer.

    @param uri: The location to check
    @type uri: C{str}
    @return: Whether the uri is reachable.
    """
    if not uri_is_valid(uri):
        raise NotImplementedError(
            # Translators: "non local" means the project is not stored
            # on a local filesystem
            _("%s doesn't yet handle non-local projects") % APPNAME)
    return os.path.isfile(Gst.uri_get_location(uri))


def path_from_uri(raw_uri):
    """
    Return a path that can be used with Python's os.path.
    """
    uri = urlparse(raw_uri)
    assert uri.scheme == "file"
    return unquote(uri.path)


def filename_from_uri(uri):
    """
    Return a human-readable filename (excluding the path to the file) to be
    used in UI elements or to shorten debug statements
    """
    return os.path.basename(path_from_uri(uri))


def quote_uri(uri):
    """
    Encode a URI/path according to RFC 2396, without touching the file:/// part.
    """
    # Split off the "file:///" part, if present.
    parts = urlsplit(uri, allow_fragments=False)
    # Make absolutely sure the string is unquoted before quoting again!
    raw_path = unquote(parts.path)
    # For computing thumbnail md5 hashes in the media library, we must adhere to
    # RFC 2396. It is quite tricky to handle all corner cases, leave it to Gst:
    return Gst.filename_to_uri(raw_path)


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
                    GLib.idle_add(self.callback, uris)

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


def quantize(input, interval):
    return (input // interval) * interval


def binary_search(elements, value):
    """Returns the index of the element closest to value.

    @param elements: A sorted list.
    """
    if not elements:
        return -1
    closest_index = bisect.bisect_left(elements, value, 0, len(elements) - 1)
    element = elements[closest_index]
    closest_distance = abs(element - value)
    if closest_distance == 0:
        return closest_index
    for index in (closest_index - 1,):
        if index < 0:
            continue
        distance = abs(elements[index] - value)
        if closest_distance > distance:
            closest_index = index
            closest_distance = distance
    return closest_index


def show_user_manual(page=None):
    """
    Display the user manual with Yelp.
    Optional: for contextual help, a page ID can be specified.
    """
    time_now = int(time.time())
    if "APPDIR" in os.environ:
        uris = (APPMANUALURL_ONLINE,)
    else:
        uris = (APPMANUALURL_OFFLINE, APPMANUALURL_ONLINE)

    for uri in uris:
        if page is not None:
            uri += "#" + page
        try:
            Gtk.show_uri(None, uri, time_now)
            return
        except Exception as e:
            log.debug("utils", "Failed loading URI %s: %s", uri, e)
            continue
    log.warning("utils", "Failed loading URIs")
    # TODO: Show an error message to the user.


def unicode_error_dialog():
    message = _("The system's locale that you are using is not UTF-8 capable. "
                "Unicode support is required for Python3 software like Pitivi. "
                "Please correct your system settings; if you try to use Pitivi "
                "with a broken locale, weird bugs will happen.")
    dialog = Gtk.MessageDialog(transient_for=None,
                               modal=True,
                               message_type=Gtk.MessageType.ERROR,
                               buttons=Gtk.ButtonsType.OK,
                               text=message)
    dialog.set_icon_name("pitivi")
    dialog.set_title(_("Error while decoding a string"))
    dialog.run()
    dialog.destroy()
