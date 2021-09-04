# -*- coding: utf-8 -*-
# Pitivi video editor
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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
import errno
import os
import subprocess
import sys
import threading
import time
from gettext import gettext as _
from urllib.parse import unquote
from urllib.parse import urlparse
from urllib.parse import urlsplit

from gi.repository import GdkPixbuf
from gi.repository import GES
from gi.repository import GLib
from gi.repository import Gst
from gi.repository import Gtk

import pitivi.utils.loggable as log
from pitivi.configure import APPMANUALURL_OFFLINE
from pitivi.configure import APPMANUALURL_ONLINE
from pitivi.utils.threads import Thread


ASSET_DURATION_META = "pitivi:asset-duration"


def scale_pixbuf(pixbuf, width, height):
    """Scales the given pixbuf preserving the original aspect ratio."""
    pixbuf_width = pixbuf.props.width
    pixbuf_height = pixbuf.props.height

    if pixbuf_width > width:
        pixbuf_height = width * pixbuf_height / pixbuf_width
        pixbuf_width = width

    if pixbuf_height > height:
        pixbuf_width = height * pixbuf_width / pixbuf_height
        pixbuf_height = height

    return pixbuf.scale_simple(pixbuf_width, pixbuf_height, GdkPixbuf.InterpType.BILINEAR)


# Work around https://bugzilla.gnome.org/show_bug.cgi?id=759249
def disconnect_all_by_func(obj, func):
    i = 0
    while True:
        i += 1
        try:
            obj.disconnect_by_func(func)
        except TypeError:
            return i


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
    """Calls the specified function and returns False.

    Helper function for calling an arbitrary function once in the gobject
    mainloop.  Any positional or keyword arguments after the function will
    be provided to the function.

    Args:
        function (function): The function to call.

    Returns:
        bool: False
    """
    function(*args, **kwargs)
    return False


# ------------------------------ URI helpers --------------------------------

def is_valid_file(path):
    """Returns whether a path is or can be a regular file."""
    if os.path.isfile(path):
        return True
    if os.path.exists(path):
        # The path is not a regular file
        return False

    try:
        # The path doesn't exist, so open(path, "w") is safe to use.
        # pylint: disable=consider-using-with
        open(path, "w", encoding="UTF-8").close()
        os.unlink(path)
        return True
    except IOError:
        return False


def is_writable(path):
    """Returns whether the file/path is writable."""
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
        return False


def uri_is_valid(uri):
    """Checks if the specified URI is usable (of type file://).

    Will also check if the size is valid (> 0).

    Args:
        uri (str): The location to check.
    """
    return (Gst.uri_is_valid(uri) and
            Gst.uri_get_protocol(uri) == "file" and
            len(os.path.basename(Gst.uri_get_location(uri))) > 0)


def path_from_uri(raw_uri):
    """Returns a path that can be used with Python's os.path."""
    uri = urlparse(raw_uri)
    assert uri.scheme == "file"
    return unquote(uri.path)


def filename_from_uri(uri):
    """Returns a filename for display.

    Excludes the path to the file.

    Can be used in UI elements.

    Returns:
        str: The markup escaped filename
    """
    base_name = os.path.basename(path_from_uri(uri))
    safe_base_name = GLib.markup_escape_text(base_name)
    return safe_base_name


def quote_uri(uri):
    """Encodes a URI according to RFC 2396.

    Does not touch the file:/// part.
    """
    # Split off the "file:///" part, if present.
    parts = urlsplit(uri, allow_fragments=False)
    # Make absolutely sure the string is unquoted before quoting again!
    raw_path = unquote(parts.path)
    # For computing thumbnail md5 hashes in the media library, we must adhere to
    # RFC 2396. It is quite tricky to handle all corner cases, leave it to Gst:
    return Gst.filename_to_uri(raw_path)


class PathWalker(Thread):
    """Thread for recursively searching in a list of directories."""

    def __init__(self, uris, callback):
        Thread.__init__(self)
        self.log("New PathWalker for %s", uris)
        self.uris = uris
        self.callback = callback
        self.stopme = threading.Event()

    def _scan(self, uris):
        """Scans the URIs and yields the file URIs."""
        for uri in uris:
            if self.stopme.is_set():
                return
            url = urlparse(uri)
            if not url.scheme == 'file':
                self.fixme("Unsupported URI: %s", uri)
                continue
            path = unquote(url.path)
            if os.path.isfile(path):
                yield uri
            elif os.path.isdir(path):
                yield from self._scan_dir(path)
            else:
                self.warning("Unusable, not a file nor a dir: %s, %s", uri, path)

    def _scan_dir(self, folder):
        """Scans the folder recursively and yields the URIs of the files."""
        self.log("Scanning folder %s", folder)
        for path, unused_dirs, files in os.walk(folder):
            if self.stopme.is_set():
                return
            for afile in files:
                yield Gst.filename_to_uri(os.path.join(path, afile))

    def process(self):
        uris = list(self._scan(self.uris))
        if uris:
            GLib.idle_add(self.callback, uris)

    def abort(self):
        self.stopme.set()


def quantize(value, interval):
    return (value // interval) * interval


def round05(value):
    return (2 * value) // 2 + 0.5


def show_user_manual(page=None):
    """Displays the user manual.

    First tries with Yelp and then tries opening the online version.

    Args:
        page (Optional[str]): A page ID to display instead of the index page,
            for contextual help.
    """
    def get_page_uri(uri, page):
        if page:
            if uri.startswith("http://"):
                return "%s/%s.html" % (uri, page)
            if uri.startswith("ghelp://"):
                return "%s/%s" % (uri, page)
            if uri.startswith("help:"):
                return "%s/%s" % (uri, page)
        return uri

    time_now = int(time.time())
    uris = (APPMANUALURL_OFFLINE, APPMANUALURL_ONLINE)
    for uri in uris:
        page_uri = get_page_uri(uri, page)
        try:
            Gtk.show_uri(None, page_uri, time_now)
            return
        except GLib.Error as e:
            log.info("utils", "Failed loading URI %s: %s", uri, e)

    # Last try calling yelp directly (used in flatpak while we do
    # not have a portal to access system wild apps)
    page_uri = get_page_uri(APPMANUALURL_OFFLINE, page)
    try:
        # pylint: disable=consider-using-with
        subprocess.Popen(["yelp", page_uri])
    except FileNotFoundError as e:
        log.warning("utils", "Failed loading %s: %s", page_uri, e)
        dialog = Gtk.MessageDialog(modal=True,
                                   message_type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.OK,
                                   text=_("Failed to open the user manual."
                                          " Make sure to have either the `yelp` GNOME"
                                          " documentation viewer or a web browser"
                                          " installed"))
        dialog.run()
        dialog.destroy()


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


def intersect(v1, v2):
    structure = Gst.Structure('t', t=v1).intersect(Gst.Structure('t', t=v2))
    if structure:
        return structure['t']

    return None


def fixate_caps_with_default_values(template, restrictions, default_values,
                                    prev_vals=None):
    """Fixates @template taking into account other restriction values.

    The resulting caps will only contain the fields from @default_values,
    @restrictions and @prev_vals

    Args:
        template (Gst.Caps) : The pad template to fixate.
        restrictions (Gst.Caps): Restriction caps to be used to fixate
            @template. This is the minimum requested
            restriction. Can be None
        default_values (dict) : Dictionary containing the minimal fields
            to be fixated and some default values (can be ranges).
        prev_vals (Optional[Gst.Caps]) : Some values that were previously
            used, and should be kept instead of the default values if possible.

    Returns:
        Gst.Caps: The caps resulting from the previously defined operations.
    """
    log.log("utils",
            "\ntemplate=Gst.Caps(\"%s\"),"
            "\nrestrictions=%s,\n"
            "default_values=%s,\n"
            "prev_vals=Gst.Caps(\"%s\"),\n",
            "\"\n        \"".join(template.to_string().split(";")),
            "Gst.Caps(\"%s\')" % restrictions if restrictions is not None else "None",
            default_values,
            "Gst.Caps(\"%s\')" % prev_vals if prev_vals is not None else "None")
    res = Gst.Caps.new_empty()
    fields = set(default_values.keys())
    if restrictions:
        for struct in restrictions:
            fields.update(struct.keys())

        log.log("utils", "Intersect template %s with the restriction %s",
                template, restrictions)
        tmp = template.intersect(restrictions)

        if not tmp:
            log.warning("utils",
                        "No common format between template %s and restrictions %s",
                        template, restrictions)
        else:
            template = tmp

    for struct in template:
        struct = struct.copy()
        for field in fields:
            prev_val = None
            default_val = default_values.get(field)
            if prev_vals and prev_vals[0].has_field(field):
                prev_val = prev_vals[0][field]

            if not struct.has_field(field):
                if prev_val:
                    struct[field] = prev_val
                elif default_val:
                    struct[field] = default_val
            else:
                value = None
                struct_val = struct[field]
                if prev_val:
                    value = intersect(struct_val, prev_val)
                    if value is not None:
                        struct[field] = value
                if value is None and default_val:
                    value = intersect(struct_val, default_val)
                    if value is not None:
                        struct[field] = value
                else:
                    log.debug("utils", "Field %s from %s is plainly fixated",
                              field, struct)

        struct = struct.copy()
        for key in struct.keys():
            if key not in fields:
                struct.remove_field(key)

        if prev_vals and struct.is_equal(prev_vals[0]):
            res = Gst.Caps.new_empty()
            res.append_structure(prev_vals[0])
            res.mini_object.refcount += 1
            res = res.fixate()
            log.debug("utils", "Returning previous caps %s as it is fully compatible"
                      " with the template", res)
            return res

        log.debug("utils", "Adding %s to resulting caps", struct)

        res.append_structure(struct)

    res.mini_object.refcount += 1
    log.debug("utils", "Fixating %s", res)
    res = res.fixate()
    log.debug("utils", "Fixated %s", res)
    return res


# GstDiscovererInfo helpers
def _get_square_width(video_info):
    width = video_info.get_width()
    par_num = video_info.get_par_num()
    par_denom = video_info.get_par_denom()
    # We observed GStreamer does a simple int(), so we leave it like this.
    return int(width * par_num / par_denom)


def video_info_get_rotation(video_info):
    tags = video_info.get_tags()
    if not tags:
        return 0

    is_rotated, rotation_string = tags.get_string(Gst.TAG_IMAGE_ORIENTATION)
    if is_rotated:
        try:
            return int(rotation_string.replace('rotate-', ''))
        except ValueError as e:
            log.error("utils", "Did not understand orientation: %s (%s)", rotation_string, e)
            return 0

    return 0


def video_info_get_natural_width(video_info):
    """Gets the width by applying the pixel aspect ratio and rotation.

    Args:
        video_info (GstPbutils.DiscovererVideoInfo): The video info.

    Returns:
        int: The width calculated exactly as GStreamer does.
    """
    rotation = video_info.get_rotation()
    if rotation in [90, 270]:
        width = video_info.get_height()
        par_num = video_info.get_par_num()
        par_denom = video_info.get_par_denom()
        # We observed GStreamer does a simple int(), so we leave it like this.
        return int(width * par_num / par_denom)

    return _get_square_width(video_info)


def video_info_get_natural_height(video_info):
    """Applies the rotation information to the height of the video.

    Args:
        video_info (GstPbutils.DiscovererVideoInfo): The video info.

    Returns:
        int: The height calculated exactly as GStreamer does.
    """
    rotation = video_info.get_rotation()
    if rotation in [90, 270]:
        return _get_square_width(video_info)

    return video_info.get_height()


def asset_get_duration(asset):
    assert isinstance(asset, GES.UriClipAsset)

    # Use pitivi information before the information provided by GStreamer.
    # We can't handle that kind of information in GES itself as it is
    # related to Pitivi' own way of handling proxies.
    res, duration = asset.get_uint64(ASSET_DURATION_META)
    if res:
        return duration

    return asset.get_duration()


def cmp(item1, item2):
    return (item1 > item2) - (item1 < item2)


# Windows-specific error code indicating an invalid pathname.
# See Also
# ----------
# https://docs.microsoft.com/en-us/windows/win32/debug/system-error-codes--0-499-
#     Official listing of all such codes.
ERROR_INVALID_NAME = 123


def is_pathname_valid(pathname: str) -> bool:
    """`True` if the passed pathname is a valid pathname for the current OS `False` otherwise."""
    # If this pathname is either not a string or is but is empty, this pathname
    # is invalid.
    try:
        if not isinstance(pathname, str) or not pathname:
            return False

        # Strip this pathname's Windows-specific drive specifier (e.g., `C:\`)
        # if any. Since Windows prohibits path components from containing `:`
        # characters, failing to strip this `:`-suffixed prefix would
        # erroneously invalidate all valid absolute Windows pathnames.
        _, pathname = os.path.splitdrive(pathname)

        # Directory guaranteed to exist. If the current OS is Windows, this is
        # the drive to which Windows was installed (e.g., the "%HOMEDRIVE%"
        # environment variable); else, the typical root directory.
        root_dirname = os.environ.get('HOMEDRIVE', 'C:') \
            if sys.platform == 'win32' else os.path.sep
        assert os.path.isdir(root_dirname)   # ...Murphy and her ironclad Law

        # Append a path separator to this directory if needed.
        root_dirname = root_dirname.rstrip(os.path.sep) + os.path.sep

        # Test whether each path component split from this pathname is valid or
        # not, ignoring non-existent and non-readable path components.
        for pathname_part in pathname.split(os.path.sep):
            try:
                os.lstat(root_dirname + pathname_part)
            # If an OS-specific exception is raised, its error code
            # indicates whether this pathname is valid or not. Unless this
            # is the case, this exception implies an ignorable kernel or
            # filesystem complaint (e.g., path not found or inaccessible).
            #
            # Only the following exceptions indicate invalid pathnames:
            #
            # * Instances of the Windows-specific "WindowsError" class
            #   defining the "winerror" attribute whose value is
            #   "ERROR_INVALID_NAME". Under Windows, "winerror" is more
            #   fine-grained and hence useful than the generic "errno"
            #   attribute. When a too-long pathname is passed, for example,
            #   "errno" is "ENOENT" (i.e., no such file or directory) rather
            #   than "ENAMETOOLONG" (i.e., file name too long).
            # * Instances of the cross-platform "OSError" class defining the
            #   generic "errno" attribute whose value is either:
            #   * Under most POSIX-compatible OSes, "ENAMETOOLONG".
            #   * Under some edge-case OSes (e.g., SunOS, *BSD), "ERANGE".
            except OSError as exc:
                if hasattr(exc, 'winerror'):
                    if exc.winerror == ERROR_INVALID_NAME:
                        return False
                elif exc.errno in {errno.ENAMETOOLONG, errno.ERANGE}:
                    return False
    # If a "TypeError" exception was raised, it almost certainly has the
    # error message "embedded NUL character" indicating an invalid pathname.
    except TypeError:
        return False
    # If no exception was raised, all path components and hence this
    # pathname itself are valid. (Praise be to the curmudgeonly python.)
    else:
        return True
    # If any other exception was raised, this is an unrelated fatal issue
    # (e.g., a bug). Permit this exception to unwind the call stack.
    #
    # Did we mention this should be shipped with Python already?
