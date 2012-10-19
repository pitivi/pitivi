#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import os
from time import time, sleep
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
        # Apparently, if we start inspecting "too fast"... we slow down startup.
        # With GNOME 3.6, startup would be delayed to the point where the "Esc"
        # keypress to dismiss the welcome dialog would happen too soon.
        sleep(1)

        self.pitivi = root.application('pitivi')
        timer_start = time()
        # This is a performance hack to very quickly get the widgets we want,
        # by using their known position instead of searching.
        # Reuse those variables throughout your scripts for efficient access.
        # FIXME: this will probably break with detached tabs.
        mainwindow = self.pitivi.children[0].children[0]  # this is a vbox
        mainwindow_upper = mainwindow.children[2].children[0]
        mainwindow_lower = mainwindow.children[2].children[1]
        primary_tabs = mainwindow_upper.children[0].children[0]
        secondary_tabs = mainwindow_upper.children[0].children[1]
        # These are the "shortcut" variables you can use for better perfs:
        self.menubar = mainwindow.child(roleName='menu bar')
        self.medialibrary = primary_tabs.children[0]
        self.effectslibrary = primary_tabs.children[1]
        self.clipproperties = secondary_tabs.children[0]
        self.transitions = secondary_tabs.children[0]
        self.titles = secondary_tabs.children[0]
        self.viewer = mainwindow_upper.children[1]
        self.timeline = mainwindow_lower.children[0].child(name="timeline canvas", recursive=False)
        self.timeline_toolbar = mainwindow_lower.child(name="timeline toolbar", recursive=False)
        # Used to speed up helper_functions in particular:
        self.import_button = self.medialibrary.child(name="media_import_button")
        self.insert_button = self.medialibrary.child(name="media_insert_button")
        start_time = time() - timer_start
        if start_time > 0.1:
            # When we were simply searching the toplevel for the menu bar,
            # startup time was 0.0043 seconds. Anything significantly longer
            # means there are optimizations to be done, avoid recursive searches
            print "\nWARNING: setUp in test_base took", start_time, "seconds, that's too slow.\n"
        try:
            self.unlink
        except AttributeError:
            self.unlink = []

    def tearDown(self, clean=True, kill=True):
        if kill:
            os.system("kill -9 %i" % self.pid)
        else:
            proj_menu = self.menubar.menu("Project")
            proj_menu.click()
            proj_menu.child("Quit").click()
        if clean:
            for filename in self.unlink:
                try:
                    os.unlink(filename)
                except:
                    None
