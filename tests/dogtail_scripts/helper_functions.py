#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import re
from dogtail.predicate import GenericPredicate
from dogtail.tree import SearchError
from test_base import BaseDogTail
import dogtail.rawinput
from time import sleep
from pyatspi import Registry as registry
from pyatspi import KEY_PRESS, KEY_RELEASE


class HelpFunc(BaseDogTail):

    def saveProject(self, path=None, saveAs=True):
        proj_menu = self.menubar.menu("Project")
        proj_menu.click()
        if saveAs:
            self.assertIsNotNone(path)
            proj_menu.menuItem("Save As...").click()
            save_dialog = self.pitivi.child(name="Save As...", roleName='file chooser', recursive=False)
            text_field = save_dialog.child(roleName="text")
            text_field.text = path
            dogtail.rawinput.pressKey("Enter")
            sleep(0.15)
            # Save to the list of items to cleanup afterwards
            self.unlink.append(path)
        else:
            # Just save
            proj_menu.menuItem("Save").click()

    def loadProject(self, url, unsaved_changes=None):
        dogtail.rawinput.pressKey("Esc")  # Ensure the welcome dialog is closed
        proj_menu = self.menubar.menu("Project")
        proj_menu.click()
        proj_menu.menuItem("Open...").click()
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
        dogtail.rawinput.pressKey("Enter")

    def _check_unsaved_changes_dialog(self, decision):
        """
        Search for the presence of a dialog asking users about unsaved changes.
        If it is absent, Dogtail will fail with a SearchError, which is fine.

        The "decision" parameter must be either "discard", "cancel" or "save".
        """
        sleep(1)
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
            sleep(0.3)
            self.insert_button.click()
        sleep(n / 2.0)  # Inserting clips takes time!
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
        dogtail.rawinput.pressKey("Enter")  # Don't search for the Add button
        sleep(0.6)

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
            sleep(0.5)

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
        dogtail.rawinput.pressKey("Enter")

        # We are now in the samples directory, select various items.
        # We use Ctrl click to select multiple items. However, since the first
        # row of the filechooser is always selected by default, we must not use
        # ctrl when selecting the first item of our list, in order to deselect.
        ctrl_code = dogtail.rawinput.keyNameToKeyCode("Control_L")
        file_list = import_dialog.child(name="Files", roleName="table")
        first = True
        for f in files:
            sleep(0.5)
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
            sleep(0.5)
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
            sleep(1)
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
            sleep(1)
            exists = os.path.isfile(path) and os.path.getsize(path) > 0
        return exists

    @staticmethod
    def wait_for_update(path, timestamp, timeout=20):
        time_elapsed = 0
        new_timestamp = False
        while (time_elapsed <= timeout) and new_timestamp == timestamp:
            time_elapsed += 2
            sleep(2)
            new_timestamp = os.path.getmtime(path)
        return new_timestamp != timestamp
