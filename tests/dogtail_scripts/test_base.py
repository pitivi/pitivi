#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import os
from dogtail.predicate import GenericPredicate


class BaseDogTail(unittest.TestCase):
    def setUp(self):
        # Force the locale/language to English.
        # Otherwise we won't be able to grab the right widgets.
        os.environ["LC_ALL"] = 'C'
        # Try to speed up UI interaction a little
        from dogtail.config import config
        config.load({'actionDelay': 0.1,
                     'typingDelay': 0.02,
                     'runTimeout': 1,
                     'searchCutoffCount': 5,
                     'defaultDelay': 0.1})
        from dogtail.utils import run
        from dogtail.tree import root
        # Setting appName is critically important here.
        # Otherwise it will try to look for "bin/pitivi" through AT-SPI and fail,
        # making the tests take ages to start up.
        self.pid = run('bin/pitivi', dumb=False, appName="pitivi")
        self.pitivi = root.application('pitivi')
        self.menubar = self.pitivi.child(roleName='menu bar')
        try:
            self.unlink
        except AttributeError:
            self.unlink = []

    def tearDown(self, clean=True):
        # Try to kill pitivi before leaving test
        os.system("kill -9 %i" % self.pid)
        if clean:
            for filename in self.unlink:
                try:
                    os.unlink(filename)
                except:
                    None
