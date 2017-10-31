# -*- coding: utf-8 -*-
# Pitivi video editor
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
"""Logic for ensuring important dependencies satisfy minimum requirements.

The checks here are supposed to take a negligible amount of time (< 0.2 seconds)
and not impact startup.

Package maintainers should look at the bottom section of this file.
"""
import os
import sys
from gettext import gettext as _

missing_soft_deps = {}
videosink_factory = None


def _version_to_string(version):
    return ".".join([str(x) for x in version])


def _string_to_list(version):
    return [int(x) for x in version.split(".")]


class Dependency(object):
    """Represents a module or component requirement.

    Args:
        modulename (str): The name identifying the component.
        version_required_string (Optional[str]): The minimum required version,
            if any, formatted like "X.Y.Z".
        additional_message (Optional[str]): Message displayed to the user to
            further explain the purpose of the missing component.
    """

    def __init__(self, modulename, version_required_string=None, additional_message=None):
        self.version_required_string = version_required_string
        self.modulename = modulename
        self.satisfied = False
        self.version_installed = None
        self.component = None
        self.additional_message = additional_message

    def check(self):
        """Checks whether the dependency is satisfied.

        Sets the `satisfied` field to True or False.
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
        """Performs the check.

        Returns:
            The dependent component.
        """
        raise NotImplementedError

    def _format_version(self, module):
        """Formats the version of the component.

        Args:
            module: The component returned by _try_importing_component.

        Returns:
            List[int]: The version number of the component.

            For example "1.2.10" should return [1, 2, 10].
        """
        raise NotImplementedError

    def __bool__(self):
        return self.satisfied

    def __repr__(self):
        if self.satisfied:
            return ""

        if not self.component:
            # Translators: %s is a Python module name or another os component
            message = _("- %s not found on the system") % self.modulename
        else:
            # Translators: %s is a Python module name or another os component
            message = _("- %s version %s is installed but Pitivi requires at least version %s") % (
                self.modulename, self.version_installed, self.version_required_string)

        if self.additional_message is not None:
            message += "\n    -> " + self.additional_message

        return message


class GIDependency(Dependency):

    def __init__(self, modulename, apiversion, version_required_string=None, additional_message=None):
        self.__api_version = apiversion
        Dependency.__init__(self, modulename, version_required_string, additional_message)

    def _try_importing_component(self):
        try:
            import gi
            try:
                gi.require_version(self.modulename, self.__api_version)
            except ValueError:
                return None

            __import__("gi.repository." + self.modulename)
            module = sys.modules["gi.repository." + self.modulename]
        except ImportError:
            module = None
        return module


class ClassicDependency(Dependency):

    def _try_importing_component(self):
        try:
            __import__(self.modulename)
            module = sys.modules[self.modulename]
        except ImportError:
            module = None
        return module


class GstPluginDependency(Dependency):

    def __init__(self, *args, **kwargs):
        self.__extra_modulenames = kwargs.pop("extra_modulenames", [])
        super().__init__(*args, **kwargs)

    def _try_importing_component(self):
        try:
            from gi.repository import Gst
        except ImportError:
            return None
        Gst.init(None)

        registry = Gst.Registry.get()
        plugin = registry.find_plugin(self.modulename)
        if not plugin and self.__extra_modulenames:
            for module in self.__extra_modulenames:
                plugin = registry.find_plugin(module)
                if plugin:
                    return plugin

        return plugin

    def _format_version(self, plugin):
        return _string_to_list(plugin.get_version())


class GstDependency(GIDependency):

    def _format_version(self, module):
        return list(module.version())


class GtkDependency(GIDependency):

    def _format_version(self, module):
        return [module.MAJOR_VERSION, module.MINOR_VERSION, module.MICRO_VERSION]


class CairoDependency(ClassicDependency):

    def __init__(self, version_required_string):
        ClassicDependency.__init__(self, "cairo", version_required_string)

    def _format_version(self, module):
        return _string_to_list(module.cairo_version_string())


def _check_audiosinks():
    from gi.repository import Gst
    # Yes, this can still fail, if PulseAudio is non-responsive for example.
    sink = Gst.ElementFactory.make("autoaudiosink", None)
    return sink


def _using_broadway_display():
    from gi.repository import Gdk
    from gi.repository import GObject
    try:
        gdk_broadway_display_type = GObject.type_from_name("GdkBroadwayDisplay")
    except RuntimeError:
        return False
    display = Gdk.Display.get_default()
    return GObject.type_is_a(display.__gtype__, gdk_broadway_display_type)


def _check_videosink():
    from gi.repository import Gst
    global videosink_factory

    # If using GdkBroadwayDisplay make sure not to try to use gtkglsink
    # as it would segfault right away.
    if not videosink_factory and \
            not _using_broadway_display() and \
            "gtkglsink" in os.environ.get("PITIVI_UNSTABLE_FEATURES", ""):
        sink = Gst.ElementFactory.make("gtkglsink", None)
        if sink:
            res = sink.set_state(Gst.State.READY)
            if res == Gst.StateChangeReturn.SUCCESS:
                videosink_factory = sink.get_factory()
                sink.set_state(Gst.State.NULL)

    if not videosink_factory:
        videosink_factory = Gst.ElementFactory.find("gtksink")

    return videosink_factory


def _check_vaapi():
    from gi.repository import Gst
    if "vaapi" in os.environ.get("PITIVI_UNSTABLE_FEATURES", ""):
        print("Vaapi decoders enabled.")
        return

    for feature in Gst.Registry.get().get_feature_list_by_plugin("vaapi"):
        if isinstance(feature, Gst.ElementFactory):
            klass = feature.get_klass()
            if "Decoder" in klass and "Video" in klass:
                feature.set_rank(Gst.Rank.MARGINAL)


def _check_gst_python():
    from gi.repository import Gst
    try:
        Gst.Fraction(9001, 1)  # It's over NINE THOUSANDS!
    except TypeError:
        return False  # What, nine thousands?! There's no way that can be right
    return True


class GICheck(ClassicDependency):
    def __init__(self, version_required_string):
        ClassicDependency.__init__(self, "gi", version_required_string)

    def _format_version(self, module):
        return list(module.version_info)


def check_requirements():
    """Checks Pitivi's dependencies are satisfied."""
    hard_dependencies_satisfied = True

    for dependency in HARD_DEPENDENCIES:
        dependency.check()
        if dependency.satisfied:
            continue
        if hard_dependencies_satisfied:
            hard_dependencies_satisfied = False
            header = _("ERROR - The following hard dependencies are unmet:")
            print(header)
            print("=" * len(header))
        print(dependency)

    for dependency in SOFT_DEPENDENCIES:
        dependency.check()
        if not dependency.satisfied:
            missing_soft_deps[dependency.modulename] = dependency
            print(_("Missing soft dependency:"))
            print(dependency)

    if not hard_dependencies_satisfied:
        return False

    if not _check_gst_python():
        print(_("ERROR — Could not create a Gst.Fraction — "
                "this means gst-python is not installed correctly."))
        return False

    if not _check_audiosinks():
        print(_("Could not create audio output sink. "
                "Make sure you have a valid one (pulsesink, alsasink or osssink)."))
        return False

    if not _check_videosink():
        print(_("Could not create video output sink. "
                "Make sure you have a gtksink available."))
        return False

    _check_vaapi()

    return True


def require_version(modulename, version):
    import gi

    try:
        gi.require_version(modulename, version)
    except ValueError:
        print(_("Could not import '%s'. Make sure you have it available.")
              % modulename)
        exit(1)


def initialize_modules():
    """Initializes the modules.

    This has to be done in a specific order otherwise the app
    crashes on some systems.
    """
    try:
        import gi
    except ImportError:
        print(_("Could not import 'gi'. "
                "Make sure you have pygobject available."))
        exit(1)

    require_version("Gtk", GTK_API_VERSION)
    require_version("Gdk", GTK_API_VERSION)
    from gi.repository import Gdk
    Gdk.init([])
    from gi.repository import Gtk

    # Monkey patch deprecated methods to use the new variant by default
    Gtk.Layout.get_vadjustment = Gtk.Scrollable.get_vadjustment
    Gtk.Layout.get_hadjustment = Gtk.Scrollable.get_hadjustment

    if not gi.version_info >= (3, 11):
        from gi.repository import GObject
        GObject.threads_init()

    require_version("Gst", GST_API_VERSION)
    require_version("GstController", GST_API_VERSION)
    require_version("GstTranscoder", GST_API_VERSION)
    from gi.repository import Gst
    from pitivi.configure import get_audiopresets_dir, get_videopresets_dir
    Gst.init(None)

    require_version("GstPbutils", GST_API_VERSION)
    from gi.repository import GstPbutils

    # Monky patch an helper method to retrieve the size of a video
    # when using square pixels.
    GstPbutils.DiscovererVideoInfo.get_square_width = \
        lambda i: i.get_width() * i.get_par_num() / i.get_par_denom()

    if not os.environ.get("GES_DISCOVERY_TIMEOUT"):
        os.environ["GES_DISCOVERY_TIMEOUT"] = "5"

    require_version("GES", GST_API_VERSION)
    from gi.repository import GES
    res, sys.argv = GES.init_check(sys.argv)
    # Monkey patch deprecated methods to use the new variant by default
    GES.TrackElement.list_children_properties = GES.TimelineElement.list_children_properties

    from pitivi.utils import validate
    if validate.init() and "--inspect-action-type" in sys.argv:
        try:
            action_type = [sys.argv[1 + sys.argv.index("--inspect-action-type")]]
        except IndexError:
            action_type = []
        if validate.GstValidate.print_action_types(action_type):
            exit(0)
        else:
            exit(1)


# Package maintainers, this is where you can see the list of requirements.
# -----------------------------------------------------------------------------
#
# Those are either:
# - Classic Python modules
# - Dynamic Python bindings through GObject introspection ("GIDependency")
# - Something else. For example, there are various GStreamer plugins/elements
#   for which there is no clear detection method other than trying to instantiate;
#   there are special snowflakes like gst-python that are GI bindings "overrides"
#   for which there is no way to detect the version either.
#
# Some of our dependencies have version numbers requirements; for those without
# a specific version requirement, they have the "None" value.

GST_API_VERSION = "1.0"
GST_VERSION = "1.12.3"
GTK_API_VERSION = "3.0"
GLIB_API_VERSION = "2.0"
HARD_DEPENDENCIES = [GICheck("3.20.0"),
                     CairoDependency("1.10.0"),
                     GstDependency("Gst", GST_API_VERSION, GST_VERSION),
                     GstDependency("GES", GST_API_VERSION, GST_VERSION),
                     GIDependency("GstTranscoder", GST_API_VERSION),
                     GIDependency("GstVideo", GST_API_VERSION),
                     GtkDependency("Gtk", GTK_API_VERSION, "3.20.0"),
                     ClassicDependency("numpy"),
                     GIDependency("Gio", "2.0"),
                     GstPluginDependency("gtk"),
                     GstPluginDependency("gdkpixbuf"),
                     ClassicDependency("matplotlib"),
                     ]

SOFT_DEPENDENCIES = (
    GIDependency("GSound", "1.0", None,
                 _("enables sound notifications when rendering is complete")),
    GIDependency("Notify", "0.7", None,
                 _("enables visual notifications when rendering is complete")),
    GstPluginDependency("libav", None,
                        _("additional multimedia codecs through the GStreamer Libav library")),
    GstPluginDependency("debugutilsbad", None,
                        _("enables a watchdog in the GStreamer pipeline."
                          " Use to detect errors happening in GStreamer"
                          " and recover from them")))
