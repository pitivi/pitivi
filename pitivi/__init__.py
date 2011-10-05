"""
Main PiTiVi package
"""

import gobject
import ges

# This call must be made before any "import gst" call!
gobject.threads_init()

ges.init()
