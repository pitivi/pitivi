import gobject
# This call has to be made before any "import gst" call!
gobject.threads_init()

from pitivi.check import initial_checks


missing_deps = initial_checks()
if missing_deps:
    message, detail = missing_deps
    raise Exception("%s\n%s" % (message, detail))
