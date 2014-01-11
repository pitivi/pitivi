# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       pitivi/check.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
# Copyright (c) 2012, Jean-François Fortin Tam <nekohayo@gmail.com>
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

"""
This file is run by bin/pitivi on startup. Its purpose is to ensure that all
the important dependencies for running the pitivi UI can be imported and satisfy
our version number requirements.

The checks here are supposed to take a negligible amount of time (< 0.2 seconds)
and not impact startup. Module imports have no impact (they get imported later
by the app anyway). For more complex checks, you can measure (with time.time()),
when called from application.py instead of bin/pitivi, if it has an impact.
"""
from sys import modules
from gettext import gettext as _

# This list is meant to be a complete list for packagers.
# Unless otherwise noted, modules are accessed through gobject introspection
HARD_DEPS = {
    "cairo": "1.10.0",  # using static python bindings
    "Clutter": "1.12.0",
    "GES": "1.0.0.0",  # packagers: in reality 1.1.90, but that GES version erronously reports itself as 1.0.0.0
    "Gio": None,
    "gnonlin": "1.1.90",
    "Gst": "1.2.0",
    "Gtk": "3.8.0",
    "numpy": None,  # using static python bindings

    # The following are not checked, but needed for the rest to work:
    "gobject-introspection": "1.34.0",
    "gst-python": "1.1.90",
    "pygobject": "3.4.0",
}

# For the list of soft dependencies, see the "check_soft_dependencies" method,
# near the end of this file.
# (library_name, why_we_need_it) tuples:
missing_soft_deps = {}


def at_least_version(version, required):
    for i, item in enumerate(version):
        if required[i] != item:
            return item > required[i]

    return True


def _initiate_videosinks(Gst):
    # TODO: eventually switch to a clutter sink
    sink = Gst.ElementFactory.make("autovideosink", None)
    if not sink:
        return False
    return True


def _initiate_audiosinks(Gst):
    # Yes, this can still fail, if PulseAudio is non-responsive for example.
    sink = Gst.ElementFactory.make("autoaudiosink", None)
    if not sink:
        return False
    return True


def _try_import_from_gi(modulename):
    try:
        __import__("gi.repository." + modulename)
        return True
    except:
        return False


def _try_import(modulename):
    try:
        __import__(modulename)
        return True
    except:
        return False


def _version_to_string(version):
    return ".".join([str(x) for x in version])


def _string_to_list(version):
    return [int(x) for x in version.split(".")]


def _check_dependency(modulename, from_gobject_introspection):
    """
    Checks if the given module can be imported and is recent enough.

    "modulename" is case-sensitive
    "from_gobject_introspection" is a mandatory boolean variable.

    Returns: [satisfied, version_required, version_installed]
    """
    VERSION_REQ = HARD_DEPS[modulename]
    # What happens here is that we try to import the module. If it works,
    # assign it to a "module" variable and check the version reqs with it.
    module = None
    if from_gobject_introspection is True:
        if _try_import_from_gi(modulename):
            module = modules["gi.repository." + modulename]
    else:
        if _try_import(modulename):
            module = modules[modulename]

    if module is None:
        # Import failed, the dependency can't be satisfied, don't check versions
        return [False, VERSION_REQ, None]
    elif not VERSION_REQ:
        # Import succeeded but there is no requirement, skip further checks
        return [True, None, False]

    # The import succeeded and there is a version requirement, so check it out:
    if modulename == "Gst" or modulename == "GES":
        if list(module.version()) < _string_to_list(VERSION_REQ):
            return [False, VERSION_REQ, _version_to_string(module.version())]
        else:
            return [True, None, _version_to_string(module.version())]
    if modulename == "Gtk" or modulename == "Clutter":
        gtk_version_tuple = (module.MAJOR_VERSION, module.MINOR_VERSION, module.MICRO_VERSION)
        if list(gtk_version_tuple) < _string_to_list(VERSION_REQ):
            return [False, VERSION_REQ, _version_to_string(gtk_version_tuple)]
        else:
            return [True, None, _version_to_string(gtk_version_tuple)]
    if modulename == "cairo":
        if _string_to_list(module.cairo_version_string()) < _string_to_list(VERSION_REQ):
            return [False, VERSION_REQ, module.cairo_version_string()]
        else:
            return [True, None, module.cairo_version_string()]

    oops = 'Module "%s" is installed, but version checking is not defined in check_dependency' % modulename
    raise NotImplementedError(oops)


def check_hard_dependencies():
    missing_hard_deps = {}

    satisfied, req, inst = _check_dependency("Gst", True)
    if not satisfied:
        missing_hard_deps["GStreamer"] = (req, inst)
    satisfied, req, inst = _check_dependency("Clutter", True)
    if not satisfied:
        missing_hard_deps["Clutter"] = (req, inst)
    satisfied, req, inst = _check_dependency("GES", True)
    if not satisfied:
        missing_hard_deps["GES"] = (req, inst)
    satisfied, req, inst = _check_dependency("cairo", False)
    if not satisfied:
        missing_hard_deps["Cairo"] = (req, inst)
    satisfied, req, inst = _check_dependency("Gtk", True)
    if not satisfied:
        missing_hard_deps["GTK+"] = (req, inst)
    satisfied, req, inst = _check_dependency("numpy", False)
    if not satisfied:
        missing_hard_deps["NumPy"] = (req, inst)

    # Since we had to check Gst beforehand, we only do the import now:
    from gi.repository import Gst
    Gst.init(None)
    reg = Gst.Registry.get()
    # Special case: gnonlin is a plugin, not a python module to be imported,
    # we can't use check_dependency to determine the version:
    inst = Gst.Registry.get().find_plugin("gnonlin")
    if not inst:
        missing_hard_deps["GNonLin"] = (HARD_DEPS["gnonlin"], inst)
    else:
        inst = inst.get_version()
        if _string_to_list(inst) < _string_to_list(HARD_DEPS["gnonlin"]):
            missing_hard_deps["GNonLin"] = (HARD_DEPS["gnonlin"], inst)

    # GES is checked, import and intialize it
    from gi.repository import GES
    GES.init()

    # Prepare the list of hard deps errors to warn about later:
    for dependency in missing_hard_deps:
        req = missing_hard_deps[dependency][0]
        inst = missing_hard_deps[dependency][1]
        if req and not inst:
            message = "%s or newer is required, but was not found on your system." % req
        elif req and inst:
            message = "%s or newer is required, but only version %s was found." % (req, inst)
        else:
            message = "not found on your system."
        missing_hard_deps[dependency] = message

    # And finally, do a few last checks for basic sanity.
    # Yes, a broken/dead autoaudiosink is still possible in 2012 with PulseAudio
    if not _initiate_videosinks(Gst):
        missing_hard_deps["autovideosink"] = \
            "Could not initiate video output sink. "\
            "Make sure you have a valid one (xvimagesink or ximagesink)."
    if not _initiate_audiosinks(Gst):
        missing_hard_deps["autoaudiosink"] = \
            "Could not initiate audio output sink. "\
            "Make sure you have a valid one (pulsesink, alsasink or osssink)."

    return missing_hard_deps


def check_soft_dependencies():
    """
    Verify for the presence of optional modules that enhance the user experience

    If those are missing from the system, the user will be notified of their
    existence by the presence of a "Missing dependencies..." button at startup.
    """
    # Importing Gst again (even if we did it in hard deps checks), anyway it
    # seems to have no measurable performance impact the 2nd time:
    from gi.repository import Gst
    Gst.init(None)

    # Description strings are translatable as they are shown in the Pitivi UI.
    if not _try_import("pycanberra"):
        missing_soft_deps["PyCanberra"] = \
            _("enables sound notifications when rendering is complete")

    if not _try_import_from_gi("GnomeDesktop"):
        missing_soft_deps["libgnome-desktop"] = \
            _("file thumbnails provided by GNOME's thumbnailers")
    if not _try_import_from_gi("Notify"):
        missing_soft_deps["libnotify"] = \
            _("enables visual notifications when rendering is complete")

    registry = Gst.Registry.get()
    if not registry.find_plugin("libav"):
        missing_soft_deps["GStreamer Libav plugin"] = \
            _("additional multimedia codecs through the Libav library")

    # Apparently, doing a registry.find_plugin("frei0r") is not enough.
    # Sometimes it still returns something even when frei0r is uninstalled,
    # and anyway we're looking specifically for the scale0tilt filter.
    # Don't use Gst.ElementFactory.make for this check, it's very I/O intensive.
    # Instead, ask the registry with .lookup_feature or .check_feature_version:
    if not registry.lookup_feature("frei0r-filter-scale0tilt"):
        missing_soft_deps["Frei0r"] = \
            _("additional video effects, clip transformation feature")

    # TODO: we're not actually checking for gst bad and ugly... by definition,
    # gst bad is a set of plugins that can move to gst good or ugly, and anyway
    # distro packagers may split/combine the gstreamer plugins into any way they
    # see fit. We can do a registry.find_plugin for specific encoders, but we
    # don't really have something generic to rely on; ideas/patches welcome.
    return missing_soft_deps
