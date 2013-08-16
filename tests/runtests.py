import os
import sys
import unittest

from gi.repository import GObject
# This call has to be made before any "import Gst" call!
# We have to do this call here, even though it already is in __init__.py,
# because this tool is run directly, as an executable.
GObject.threads_init()

from pitivi.check import check_hard_dependencies

parent = os.path.abspath(os.path.join(os.getcwd(), os.pardir))

sys.path.append(os.path.join(parent, "pitivi/coptimizations/.libs"))

missing_hard_deps = check_hard_dependencies()
# This differs slightly from bin/pitivi.in as we don't check soft deps here:
if missing_hard_deps:
    print "\nERROR - The following hard dependencies are unmet:"
    print "=================================================="
    for dep in missing_hard_deps:
        print "-", dep + ":", missing_hard_deps[dep]
    print ""
    sys.exit(2)


def gettestnames(file_names):
    test_names = [file_name[:-3] for file_name in file_names]
    return test_names

loader = unittest.TestLoader()

# Set verbosity.
descriptions = 1
verbosity = 1
if 'VERBOSE' in os.environ:
    descriptions = 2
    verbosity = 2
from pitivi.utils import loggable as log
log.init('PITIVI_DEBUG', 1)

# Make available to configure.py the top level dir.
dir = os.path.dirname(os.path.abspath(__file__))
top_srcdir = os.path.split(dir)[0]
os.environ.setdefault('PITIVI_TOP_LEVEL_DIR', top_srcdir)

# Pick which tests to run.
TEST_CASE = os.getenv("TESTCASE")
if TEST_CASE:
    test_names = [TEST_CASE]
else:
    test_names = gettestnames(sys.argv[1:])
suite = loader.loadTestsFromNames(test_names)
if not list(suite):
    raise Exception("No tests found")

# Run the tests.
testRunner = unittest.TextTestRunner(descriptions=descriptions,
    verbosity=verbosity)
result = testRunner.run(suite)
if result.failures or result.errors:
    sys.exit(1)
