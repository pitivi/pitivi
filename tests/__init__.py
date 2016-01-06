#!/usr/bin/env python3

from . import runtests
if not runtests.setup():
    raise ImportError("Could not setup testsuite")
