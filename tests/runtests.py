#!/usr/bin/env python3

"""Pitivi tests runner."""

import os
import sys
import unittest


def _testcases(filenames):
    """Yield testcases out of filenames."""
    for filename in filenames:
        if filename.endswith(".py"):
            yield filename[:-3]


def _tests_suite():
    """Pick which tests to run."""
    testcase = os.getenv("TESTCASE")
    if testcase:
        testcases = [testcase]
    else:
        testcases = _testcases(sys.argv[1:])
    loader = unittest.TestLoader()
    return loader.loadTestsFromNames(testcases)


def get_pitivi_dir():
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    pitivi_dir = os.path.join(tests_dir, os.path.pardir)
    return os.path.abspath(pitivi_dir)


def get_build_dir():
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


def setup():
    res = True
    # Make available to configure.py the top level dir.
    pitivi_dir = get_pitivi_dir()
    os.environ.setdefault('PITIVI_TOP_LEVEL_DIR', pitivi_dir)

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

if __name__ == "__main__":
    setup()

    # Set verbosity.
    descriptions = 1
    verbosity = 1
    if 'VERBOSE' in os.environ:
        descriptions = 2
        verbosity = 2

    suite = _tests_suite()
    if not list(suite):
        raise Exception("No tests found")

    # Run the tests.
    testRunner = unittest.TextTestRunner(descriptions=descriptions,
                                         verbosity=verbosity)
    result = testRunner.run(suite)
    if result.failures or result.errors:
        sys.exit(1)
