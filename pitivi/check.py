# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       pitivi/check.py
#
# Copyright (c) 2014, Mathieu Duponchelle <mduponchelle1@gmail.com>
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

import sys

from gettext import gettext as _

missing_soft_deps = {}


class Dependency(object):
    """
    This abstract class represents a module or component requirement.
    @param modulename: The string allowing for import or lookup of the component.
    @param version_required_string: A string in the format X.Y.Z or None if no version
      check is necessary.
    @param additional_message: A string that will be displayed to the user to further
      explain the purpose of the missing component.
    """
    def __init__(self, modulename, version_required_string, additional_message=None):
        self.version_required_string = version_required_string
        self.modulename = modulename
        self.satisfied = False
        self.version_installed = None
        self.component = None
        self.additional_message = additional_message

    def check(self):
        """
        Sets the satisfied flag to True or False.
        """
        self.component = self._try_importing_component()

        if not self.component:
            self.satisfied = False
        elif self.version_required_string is None:
            self.satisfied = True
        else:
            formatted_version = self._format_version(self.component)
            self.version_installed = _version_to_string(formatted_version)

            if formatted_version >= _string_to_list(self.version_required_string):
                self.satisfied = True

    def _try_importing_component(self):
        """
        Subclasses must implement that method to return an object
        on which version will be inspectable.
        Return None on failure to import.
        """
        raise NotImplementedError

    def _format_version(self, module):
        """
        Subclasses must return the version number split
        in an iterable of ints.
        For example "1.2.10" should return [1, 2, 10]
        """
        raise NotImplementedError

    def __repr__(self):
        if self.satisfied:
            return ""

        message = "- " + self.modulename + " "
        if not self.component:
            message += _("not found on the system")
        else:
            message += self.version_installed + _(" is installed but ") +\
                self.version_required_string + _(" is required")

        if self.additional_message is not None:
            message += "\n    -> " + self.additional_message

        return message


class GIDependency(Dependency):
    def _try_importing_component(self):
        try:
            __import__("gi.repository." + self.modulename)
            module = sys.modules["gi.repository." + self.modulename]
        except ImportError:
            module = None
        return module

    def _format_version(self, module):
        pass


class ClassicDependency(Dependency):
    def _try_importing_component(self):
        try:
            __import__(self.modulename)
            module = sys.modules[self.modulename]
        except ImportError:
            module = None
        return module

    def _format_version(self, module):
        pass


class GstPluginDependency(Dependency):
    """
    Don't call check on its instances before actually checking
    Gst is importable.
    """
    def _try_importing_component(self):
        from gi.repository import Gst
        Gst.init(None)

        registry = Gst.Registry.get()
        plugin = registry.find_plugin(self.modulename)
        return plugin

    def _format_version(self, plugin):
        return _string_to_list(plugin.get_version())


class GstDependency(GIDependency):
    def _format_version(self, module):
        return list(module.version())


class GtkOrClutterDependency(GIDependency):
    def _format_version(self, module):
        return [module.MAJOR_VERSION, module.MINOR_VERSION, module.MICRO_VERSION]


class CairoDependency(ClassicDependency):
    def __init__(self, version_required_string):
        ClassicDependency.__init__(self, "cairo", version_required_string)

    def _format_version(self, module):
        return _string_to_list(module.cairo_version_string())


HARD_DEPENDENCIES = (CairoDependency("1.10.0"),
                     GtkOrClutterDependency("Clutter", "1.12.0"),
                     GtkOrClutterDependency("ClutterGst", "2.0.0"),
                     GstDependency("Gst", "1.2.0"),
                     GstDependency("GES", "1.0.0.0"),
                     GtkOrClutterDependency("Gtk", "3.8.0"),
                     ClassicDependency("numpy", None),
                     GIDependency("Gio", None),
                     GstPluginDependency("gnonlin", "1.1.90"))

SOFT_DEPENDENCIES = (ClassicDependency("pycanberra", None,
                                       _("enables sound notifications when rendering is complete")),
                     GIDependency("GnomeDesktop", None,
                                  _("file thumbnails provided by GNOME's thumbnailers")),
                     GIDependency("Notify", None,
                                  _("enables visual notifications when rendering is complete")),
                     GstPluginDependency("libav", None,
                                         _("additional multimedia codecs through the Libav library")))


def _check_audiosinks():
    from gi.repository import Gst

    # Yes, this can still fail, if PulseAudio is non-responsive for example.
    sink = Gst.ElementFactory.make("autoaudiosink", None)
    if not sink:
        return False
    return True


def _version_to_string(version):
    return ".".join([str(x) for x in version])


def _string_to_list(version):
    return [int(x) for x in version.split(".")]


def check_requirements():
    hard_dependencies_satisfied = True
    for dependency in HARD_DEPENDENCIES:
        dependency.check()
        if not dependency.satisfied:
            if hard_dependencies_satisfied:
                print _("\nERROR - The following hard dependencies are unmet:")
                print "=================================================="
            print dependency
            hard_dependencies_satisfied = False

    for dependency in SOFT_DEPENDENCIES:
        dependency.check()
        if not dependency.satisfied:
            missing_soft_deps[dependency.modulename] = dependency
            print _("Missing soft dependency:")
            print dependency

    if not hard_dependencies_satisfied:
        return False

    if not _check_audiosinks():
        print _("Could not create audio output sink. "
                "Make sure you have a valid one (pulsesink, alsasink or osssink).")
        return False

    return True


def initialize_modules():
    """
    Initialize the modules.

    This has to be done in a specific order otherwise the app
    crashes on some systems.
    """
    from gi.repository import Gdk
    Gdk.init([])
    from gi.repository import GtkClutter
    GtkClutter.init([])
    from gi.repository import ClutterGst
    ClutterGst.init([])

    import gi
    if not gi.version_info >= (3, 11):
        from gi.repository import GObject
        GObject.threads_init()

    from gi.repository import Gst
    Gst.init(None)
    from gi.repository import GES
    GES.init()

    # This is required because of:
    # https://bugzilla.gnome.org/show_bug.cgi?id=656314
    from gi.repository import GdkX11
    GdkX11  # noop
