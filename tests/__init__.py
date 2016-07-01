#!/usr/bin/env python3
"""
Pitivi unit tests
"""
import glob
import os
import sys
import unittest


def get_pitivi_dir():
    """Gets the pitivi root directory."""
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    pitivi_dir = os.path.join(tests_dir, os.path.pardir)
    return os.path.abspath(pitivi_dir)


def get_build_dir():
    """Gets the build directory."""
    from pitivi.configure import in_devel
    if in_devel():
        # It's the same.
        build_dir = get_pitivi_dir()
    else:
        # Probably running make distcheck. The path to the test files
        # is different than the build path, so we must use the current
        # dir which is build_path/tests.
        build_dir = os.path.join(
            os.path.abspath(os.path.curdir), os.path.pardir)
    return os.path.abspath(build_dir)


def _prepend_env_path(name, value):
    """Prepends one or more paths to an environment variable."""
    os.environ[name] = os.pathsep.join(value +
                                       os.environ.get(name, "").split(
                                           os.pathsep))


def setup():
    """Sets paths and initializes modules, to be able to run the tests."""
    res = True
    # Make available to configure.py the top level dir.
    pitivi_dir = get_pitivi_dir()
    sys.path.insert(0, pitivi_dir)

    os.environ.setdefault('PITIVI_TOP_LEVEL_DIR', pitivi_dir)

    _prepend_env_path("GST_PRESET_PATH", [
        os.path.join(pitivi_dir, "data", "videopresets"),
        os.path.join(pitivi_dir, "data", "audiopresets")])

    _prepend_env_path("GST_ENCODING_TARGET_PATH", [
        os.path.join(pitivi_dir, "data", "encoding-profiles")])

    # Make available the compiled C code.
    build_dir = get_build_dir()
    libs_dir = os.path.join(build_dir, "pitivi/coptimizations/.libs")
    sys.path.append(libs_dir)

    # Make sure the modules are initialized correctly.
    from pitivi import check
    check.initialize_modules()
    res = check.check_requirements()

    from pitivi.utils import loggable as log
    log.init('PITIVI_DEBUG')

    return res

if not setup():
    raise ImportError("Could not setup testsuite")
