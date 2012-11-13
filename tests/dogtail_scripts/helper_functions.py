#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import os
import re
from dogtail.predicate import GenericPredicate
from test_base import BaseDogTail
import dogtail.rawinput
from time import sleep
from pyatspi import Registry as registry
from pyatspi import (KEY_SYM, KEY_PRESS, KEY_PRESSRELEASE, KEY_RELEASE)


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

    def loadProject(self, url, expect_unsaved_changes=False):
        proj_menu = self.menubar.menu("Project")
        proj_menu.click()
        proj_menu.menuItem("Open...").click()
        load = self.pitivi.child(roleName='file chooser', recursive=False)
        # Same performance hack as in the import_media method
        dogtail.rawinput.pressKey("/")
        load.child(roleName='text').text = url
        dogtail.rawinput.pressKey("Enter")  # Don't search for the Open button
        # If an unsaved changes confirmation dialog shows up, deal with it
        if expect_unsaved_changes:
            # Simply try searching for the existence of the dialog's widgets
            # If it fails, dogtail will fail with a SearchError, which is fine
            self.pitivi.child(name="Close without saving", roleName="push button").click()

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
                    print "Searching for", text, "in", child.text
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
        icon.deselect()

    def import_media(self, filename="tears of steel.webm"):
        dogtail.rawinput.pressKey("Esc")  # Ensure the welcome dialog is closed
        self.import_button.click()

        # Force dogtail to look only one level deep, which is much faster
        # as it doesn't have to analyze the whole mainwindow.
        import_dialog = self.pitivi.child(name="Select One or More Files",
                                          roleName="file chooser", recursive=False)
        # Instead of checking for the presence of the path text field and then
        # searching for the toggle button to enable it, use the fact that GTK's
        # file chooser allows typing the path directly if it starts with "/".
        dogtail.rawinput.pressKey("/")  # This text will be replaced later

        filepath = os.path.realpath(__file__).split("dogtail_scripts/")[0]
        filepath += "samples/" + filename
        import_dialog.child(roleName='text').text = filepath
        dogtail.rawinput.pressKey("Enter")  # Don't search for the Add button
        sleep(0.6)

        # Check if the item is now visible in the media library.
        for i in range(5):
            # The time it takes for the icon to appear is unpredictable,
            # therefore we try up to 5 times to look for it
            icons = self.medialibrary.findChildren(GenericPredicate(roleName="icon"))
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

        # Same performance hack as in the import_media method
        import_dialog = self.pitivi.child(name="Select One or More Files",
                                          roleName="file chooser", recursive=False)
        dogtail.rawinput.pressKey("/")
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
