#!/usr/bin/env python3
"""
Pitivi unit tests
"""
import glob
import os
import sys
import unittest
from tempfile import mkdtemp

import gi.overrides


def get_pitivi_dir():
    """Gets the pitivi root directory."""
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    pitivi_dir = os.path.join(tests_dir, os.path.pardir)
    return os.path.abspath(pitivi_dir)


def _prepend_env_paths(**args):
    """Prepends one or more paths to an environment variable."""

    for name, value in args.items():
        if not isinstance(value, list):
            value = [value]

        os.environ[name] = os.pathsep.join(
            value + os.environ.get(name, "").split(
                os.pathsep))


def setup():
    """Sets paths and initializes modules, to be able to run the tests."""
    # Make sure xdg_*_home return temp dirs, to avoid touching
    # the config files of the developer.
    os.environ['XDG_DATA_HOME'] = mkdtemp()
    os.environ['XDG_CONFIG_HOME'] = mkdtemp()
    os.environ['XDG_CACHE_HOME'] = mkdtemp()

    # Make available to configure.py the top level dir.
    pitivi_dir = get_pitivi_dir()
    sys.path.insert(0, pitivi_dir)

    from pitivi import configure

    # Let Gst overrides from our prefix take precedence over any
    # other, making sure they are used. This allows us to ensure that
    # Gst overrides from gst-python are used when within flatpak
    local_overrides = os.path.join(configure.LIBDIR,
                                   "python" + sys.version[:3],
                                   "site-packages", "gi", "overrides")
    gi.overrides.__path__.insert(0, local_overrides)

    # Make available the compiled C code.
    sys.path.append(configure.BUILDDIR)
    subproject_paths = os.path.join(configure.BUILDDIR, "subprojects", "gst-transcoder")

    _prepend_env_paths(LD_LIBRARY_PATH=subproject_paths,
                       GST_PLUGIN_PATH=subproject_paths,
                       GI_TYPELIB_PATH=subproject_paths,
                       GST_PRESET_PATH=[os.path.join(pitivi_dir, "data", "videopresets"),
                                        os.path.join(pitivi_dir, "data", "audiopresets")],
                       GST_ENCODING_TARGET_PATH=[os.path.join(pitivi_dir, "tests", "test-encoding-targets"),
                                                 os.path.join(pitivi_dir, "data", "encoding-profiles")])
    os.environ.setdefault('PITIVI_TOP_LEVEL_DIR', pitivi_dir)

    # Make sure the modules are initialized correctly.
    from pitivi import check
    check.initialize_modules()
    res = check.check_requirements()

    from pitivi.utils import loggable as log
    log.init('PITIVI_DEBUG')

    return res

if not setup():
    raise ImportError("Could not setup testsuite")
