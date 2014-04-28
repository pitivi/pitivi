#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import re
import shutil
import tempfile
import time

import unittest

from dogtail.predicate import GenericPredicate
from dogtail.tree import SearchError
import dogtail.rawinput
from pyatspi import Registry as registry
from pyatspi import KEY_PRESS, KEY_RELEASE


# These are the timecodes we expect for "tears_of_steel.webm", depending on
# if we insert it once in a blank timeline or twice in a blank timeline.
DURATION_OF_ONE_CLIP = "00:01.999"
DURATION_OF_TWO_CLIPS = "00:03.999"

# Constants from pitivi.ui
# TODO: Use directly the constants from pitivi.ui when these UI tests are ported to Python3.
CONTROL_WIDTH = 250
EXPANDED_SIZE = 65
SPACING = 10


class PitiviTestCase(unittest.TestCase):

    def setUp(self):
        # Force the locale/language to English.
        # Otherwise we won't be able to grab the right widgets.
        os.environ["LC_ALL"] = 'C'
        # Try to speed up UI interaction a little.
        # Do not change "typingDelay" from its default (0.075 secs);
        # Setting it too low makes dogtail type characters in random order!
        from dogtail.config import config
        config.load({'actionDelay': 0.1,
                     'runTimeout': 1,
                     'searchCutoffCount': 5,
                     'defaultDelay': 0.1})
        # Specify custom xdg user dirs to not be influenced by the settings
        # chosen by the current user.
        if not hasattr(self, "user_dir"):
            self.user_dir = tempfile.mkdtemp()
            os.environ["PITIVI_USER_CONFIG_DIR"] = os.path.pathsep.join([self.user_dir, "config"])
            os.environ["PITIVI_USER_DATA_DIR"] = os.path.pathsep.join([self.user_dir, "data"])
            os.environ["PITIVI_USER_CACHE_DIR"] = os.path.pathsep.join([self.user_dir, "cache"])
        from dogtail.utils import run
        from dogtail.tree import root
        # Setting appName is critically important here.
        # Otherwise it will try to look for "bin/pitivi" through AT-SPI and fail,
        # making the tests take ages to start up.
        self.pid = run('bin/pitivi', dumb=False, appName="pitivi")
        # Apparently, if we start inspecting "too fast"... we slow down startup.
        # With GNOME 3.6, startup would be delayed to the point where the "Esc"
        # keypress to dismiss the welcome dialog would happen too soon.
        time.sleep(1)

        self.pitivi = root.application('pitivi')
        timer_start = time.time()
        # This is a performance hack to very quickly get the widgets we want,
        # by using their known position instead of searching.
        # Reuse those variables throughout your scripts for efficient access.
        mainwindow = self.pitivi.children[0]
        self.assertEqual('main window', mainwindow.name)
        headerbar, box = mainwindow.children
        contents = box.children[0]
        self.assertEqual('contents', contents.name)
        upper_half, timeline_area = contents.children
        self.assertEqual('upper half', upper_half.name)
        self.assertEqual('timeline area', timeline_area.name)
        primary_tabs = upper_half.children[0].child(name="primary tabs", recursive=False)
        secondary_tabs = upper_half.children[0].child(name="secondary tabs", recursive=False)
        # These are the "shortcut" variables you can use for better perfs:
        self.menubar = self.pitivi.children[0].child(name='headerbar', recursive=False)
        self.medialibrary = primary_tabs.children[0]
        self.effectslibrary = primary_tabs.children[1]
        self.clipproperties = secondary_tabs.children[0]
        self.transitions = secondary_tabs.children[1]
        self.titles = secondary_tabs.children[2]
        self.viewer = upper_half.child(name="viewer", recursive=False)
        self.zoom_best_fit_button = timeline_area.child(name="Zoom", recursive=True)
        self.timeline = timeline_area.child(name="timeline canvas", recursive=False)
        self.timeline_toolbar = timeline_area.child(name="timeline toolbar", recursive=False)
        # Used to speed up helper_functions in particular:
        self.import_button = self.medialibrary.child(name="media_import_button")
        self.insert_button = self.medialibrary.child(name="media_insert_button")
        start_time = time.time() - timer_start
        if start_time > 0.1:
            # When we were simply searching the toplevel for the menu bar,
            # startup time was 0.0043 seconds. Anything significantly longer
            # means there are optimizations to be done, avoid recursive searches
            print("\nWARNING: setUp in test_base took", start_time, "seconds, that's too slow.\n")
        try:
            self.unlink
        except AttributeError:
            self.unlink = []

    def tearDown(self, clean=True, kill=True):
        if kill:
            os.system("kill -9 %i" % self.pid)
        else:
            import dogtail.rawinput
            dogtail.rawinput.keyCombo("<Control>q")  # Quit the app
        if clean:
            try:
                shutil.rmtree(self.user_dir)
            except OSError:
                # No biggie.
                pass
            for filename in self.unlink:
                try:
                    os.unlink(filename)
                except OSError:
                    # No biggie.
                    pass

    def saveProject(self, path=None, saveAs=True):
        if saveAs:
            self.assertIsNotNone(path)
            dogtail.rawinput.keyCombo("<Control><Shift>s")  # Save project as
            save_dialog = self.pitivi.child(name="Save As...", roleName='file chooser', recursive=False)
            text_field = save_dialog.child(roleName="text")
            text_field.text = path
            time.sleep(0.2)
            dogtail.rawinput.pressKey("Enter")
            time.sleep(0.15)
            # Save to the list of items to cleanup afterwards
            self.unlink.append(path)
        else:
            # Just save
            dogtail.rawinput.keyCombo("<Control>s")  # Save project

    def loadProject(self, url, unsaved_changes=None):
        dogtail.rawinput.pressKey("Esc")  # Ensure the welcome dialog is closed
        dogtail.rawinput.keyCombo("<Control>o")  # Open project
        # If an "unsaved changes" prompt is expected to show up, deal with it:
        if unsaved_changes is not None:
            result = self._check_unsaved_changes_dialog(decision=unsaved_changes)
            if result is False:  # The user clicked "Cancel" (no decision)
                return

        load = self.pitivi.child(name="Open File...", roleName="file chooser", recursive=False)
        path_toggle = load.child(name="Type a file name", roleName="toggle button")
        if not path_toggle.checked:
            path_toggle.click()

        load.child(roleName='text').text = url
        # Speed hack: don't search for the Open button
        time.sleep(0.2)
        dogtail.rawinput.pressKey("Enter")

    def _check_unsaved_changes_dialog(self, decision):
        """
        Search for the presence of a dialog asking users about unsaved changes.
        If it is absent, Dogtail will fail with a SearchError, which is fine.

        The "decision" parameter must be either "discard", "cancel" or "save".
        """
        time.sleep(1)
        try:
            dialog = self.pitivi.child(name="unsaved changes dialog", roleName="dialog", recursive=False, retry=False)
        except SearchError:
            self.fail('The "unsaved changes" dialog/prompt was expected but did not appear')

        if decision is "discard":
            dialog.child(name="Close without saving", roleName="push button").click()
            return True
        elif decision is "cancel":
            dialog.child(name="Cancel", roleName="push button").click()
            return False  # Prevent us from expecting the file chooser in loadProject
        elif decision is "save":
            dialog.child(name="Save", roleName="push button").click()
            return True
        else:
            self.fail("You didn't provide a valid answer for the unsaved changes dialog!")

    def search_by_text(self, text, parent, name=None, roleName=None, exactMatchOnly=True):
        """
        Search a parent widget for the first child whose text matches exactly.
        If you want to search for a widget "containing" the text, set the
        "exactMatchOnly" parameter to False (it will also be case-insensitive).
        """
        children = parent.findChildren(GenericPredicate(roleName=roleName, name=name))
        for child in children:
            if hasattr(child, "text"):
                # This is cute and all, but we're not just searching inside
                # text entry widgets or labels... we can also be in a table cell
                # and that means we can't assume that it's a text cell. Many
                # listviews/treeviews/etc have cells for icons (text is None)
                if child.text is not None:
                    print("Searching for", text, "in", child.text)
                    if exactMatchOnly:
                        if text == child.text:
                            return child
                    elif text.lower() in child.text.lower():
                        return child

    def search_by_regex(self, regex, parent, name=None, roleName=None, regex_flags=0):
        """
        Search a parent widget for childs containing the given regular expression
        """
        children = parent.findChildren(GenericPredicate(roleName=roleName, name=name))
        r = re.compile(regex, regex_flags)
        for child in children:
            if child.text is not None and r.match(child.text):
                return child

    def insert_clip(self, icon, n=1):
        icon.select()
        for i in range(n):
            time.sleep(0.3)
            self.insert_button.click()
        time.sleep(n / 2.0)  # Inserting clips takes time!
        icon.deselect()
        self.zoom_best_fit_button.click()

    def import_media(self, filename="tears_of_steel.webm"):
        """
        @return: The icon widget.
        """
        dogtail.rawinput.pressKey("Esc")  # Ensure the welcome dialog is closed
        self.import_button.click()

        # Force dogtail to look only one level deep, which is much faster
        # as it doesn't have to analyze the whole mainwindow.
        import_dialog = self.pitivi.child(name="Select One or More Files",
                                          roleName="file chooser", recursive=False)

        path_toggle = import_dialog.child(name="Type a file name", roleName="toggle button")
        if not path_toggle.checked:
            path_toggle.click()

        filepath = os.path.realpath(__file__).split("dogtail_scripts/")[0]
        filepath += "samples/" + filename
        import_dialog.child(roleName='text').text = filepath
        time.sleep(0.2)
        dogtail.rawinput.pressKey("Enter")  # Don't search for the Add button
        time.sleep(0.6)

        # Check if the item is now visible in the media library.
        for i in range(5):
            # The time it takes for the icon to appear is unpredictable,
            # therefore we try up to 5 times to look for it
            try:
                icons = self.medialibrary.findChildren(GenericPredicate(roleName="icon"))
            except TypeError:
                # If no icon can be seen due to restrictive search results,
                # don't try to loop over "icons" (which will be a None type).
                # See further below for further checks that verify this.
                continue
            for icon in icons:
                if icon.text == filename:
                    return icon
            time.sleep(0.5)

        # Failure to find an icon might be because it is hidden due to a search
        current_search_text = self.medialibrary.child(name="media_search_entry", roleName="text").text.lower()
        self.assertNotEqual(current_search_text, "")
        self.assertNotIn(filename.lower(), current_search_text)
        return None

    def import_media_multiple(self, files):
        dogtail.rawinput.pressKey("Esc")  # Ensure the welcome dialog is closed
        self.import_button.click()

        import_dialog = self.pitivi.child(name="Select One or More Files",
                                          roleName="file chooser", recursive=False)

        path_toggle = import_dialog.child(name="Type a file name", roleName="toggle button")
        if not path_toggle.checked:
            path_toggle.click()

        dir_path = os.path.realpath(__file__).split("dogtail_scripts/")[0] + "samples/"
        import_dialog.child(roleName='text').text = dir_path
        time.sleep(0.2)
        dogtail.rawinput.pressKey("Enter")

        # We are now in the samples directory, select various items.
        # We use Ctrl click to select multiple items. However, since the first
        # row of the filechooser is always selected by default, we must not use
        # ctrl when selecting the first item of our list, in order to deselect.
        ctrl_code = dogtail.rawinput.keyNameToKeyCode("Control_L")
        file_list = import_dialog.child(name="Files", roleName="table")
        first = True
        for f in files:
            time.sleep(0.5)
            file_list.child(name=f).click()
            if first:
                registry.generateKeyboardEvent(ctrl_code, None, KEY_PRESS)
                first = False
        registry.generateKeyboardEvent(ctrl_code, None, KEY_RELEASE)
        import_dialog.button('Add').click()

        current_search_text = self.medialibrary.child(name="media_search_entry", roleName="text").text.lower()
        if current_search_text != "":
            # Failure to find some icons might be because of search filtering.
            # The following avoids searching for files that can't be found.
            for f in files:
                if current_search_text not in f.lower():
                    files.remove(f)
        # Check if non-filtered items are now visible in the media library.
        samples = []
        for i in range(5):
            # The time it takes for icons to appear is unpredictable,
            # therefore we try up to 5 times to look for them
            icons = self.medialibrary.findChildren(GenericPredicate(roleName="icon"))
            for icon in icons:
                for f in files:
                    if icon.text == f:
                        samples.append(icon)
                        files.remove(f)
            if len(files) == 0:
                break
            time.sleep(0.5)
        return samples

    def improved_drag(self, from_coords, to_coords, middle=[], absolute=True, moveAround=True):
        """
        Allow dragging from a set of coordinates to another set of coords,
        with an optional list of intermediate coordinates and the ability to
        wiggle the mouse slightly at each set of coordinates.
        """
        # Choose the default type of motion calculation
        if absolute:
            fun = dogtail.rawinput.absoluteMotion
        else:
            fun = dogtail.rawinput.relativeMotion

        # Do the initial click
        dogtail.rawinput.press(from_coords[0], from_coords[1])
        if moveAround:
            dogtail.rawinput.relativeMotion(5, 5)
            dogtail.rawinput.relativeMotion(-5, -5)

        # Do all the intermediate move operations
        for mid in middle:
            fun(mid[0], mid[1])
            if moveAround:
                dogtail.rawinput.relativeMotion(5, 5)
                dogtail.rawinput.relativeMotion(-5, -5)

        # Move to the final coordinates
        dogtail.rawinput.absoluteMotion(to_coords[0], to_coords[1])
        if moveAround:
            dogtail.rawinput.relativeMotion(5, 5)
            dogtail.rawinput.relativeMotion(-5, -5)

        # Release the mouse button
        dogtail.rawinput.release(to_coords[0], to_coords[1])

    # These two methods are needed since spinbuttons in GTK 3.4 and newer have
    # huge buttons, and simply asking dogtail to .click() or .doubleclick()
    # would end up triggering those buttons instead of (de)selecting the text.
    def spinbuttonClick(self, widget):
        """
        Do a single click in the text area of a spinbutton widget.
        This is mostly useful when you want to defocus another widget.
        """
        (x, y) = widget.position
        dogtail.rawinput.click(x + 10, y + 10)

    def spinbuttonDoubleClick(self, widget):
        """
        Do a double-click in the text area of a spinbutton widget.
        This is useful when you want to select all of its text.
        """
        (x, y) = widget.position
        dogtail.rawinput.doubleClick(x + 10, y + 10)

    def force_medialibrary_iconview_mode(self):
        """
        Many of our tests looking up clips in the media library don't handle
        the fact that iconview appears different than treeview to dogtail, and
        thus that we need to double the code. This dodges the issue by ensuring
        the tests run in iconview mode.
        """
        listview = self.medialibrary.child(name="media_listview_scrollwindow")
        if listview.showing:
            # Ensure the welcome dialog is closed.
            dogtail.rawinput.pressKey("Esc")
            # Make sure the list view is hidden.
            self.medialibrary.child(name="media_listview_button", roleName="panel").click()
            self.wait_for_node_hidden(listview, timeout=2)

    @staticmethod
    def center(obj):
        return obj.position[0] + obj.size[0] / 2, obj.position[1] + obj.size[1] / 2

    @staticmethod
    def wait_for_node_hidden(widget, timeout=10):
        while widget.showing and timeout > 0:
            time.sleep(1)
            timeout -= 1
        return not widget.showing

    @staticmethod
    def wait_for_file(path, timeout=10):
        """
        Check for the existence of a file, until a timeout is reached.
        This gives enough time for GES/Pitivi to do whatever it needs to do.

        Also checks that the file is not an empty (0 bytes) file.
        """
        time_elapsed = 0
        exists = False
        while (time_elapsed <= timeout) and not exists:
            time_elapsed += 1
            time.sleep(1)
            exists = os.path.isfile(path) and os.path.getsize(path) > 0
        return exists

    @staticmethod
    def wait_for_update(path, timestamp, timeout=20):
        time_elapsed = 0
        new_timestamp = False
        while (time_elapsed <= timeout) and new_timestamp == timestamp:
            time_elapsed += 2
            time.sleep(2)
            new_timestamp = os.path.getmtime(path)
        return new_timestamp != timestamp

    def getTimelineX(self, percent):
        assert percent >= 0
        assert percent <= 1
        perceived_width = self.timeline.size[0] - CONTROL_WIDTH
        return self.timeline.position[0] + CONTROL_WIDTH + percent * perceived_width

    def getTimelineY(self, layer, above=False):
        """
        Get the absolute y for the middle of the specified layer.

        @param layer: 0-based layer index.
        @param above: Whether instead middle of the space above.
        """
        assert layer >= 0
        perceived_top = layer * (EXPANDED_SIZE + SPACING)
        if above:
            perceived_top += SPACING / 2
        else:
            perceived_top += SPACING + EXPANDED_SIZE / 2
        return self.timeline.position[1] + perceived_top
