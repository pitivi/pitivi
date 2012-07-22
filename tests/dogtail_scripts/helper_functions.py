#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
import os
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
            saveas = self.pitivi.child(name="Save As...", roleName='dialog', recursive=False)
            # In GTK3's file chooser, you can enter /tmp/foo.xptv directly
            # In GTK2 however, you must do it in two steps:
            path_dir, filename = os.path.split(path)
            text_field = saveas.child(roleName="text")
            text_field.text = path_dir
            dogtail.rawinput.pressKey("Enter")
            sleep(0.05)
            text_field.text = filename
            dogtail.rawinput.pressKey("Enter")
            # Save to the list of items to cleanup afterwards
            self.unlink.append(path)
        else:
            # Just save
            proj_menu.menuItem("Save").click()

    def loadProject(self, url, save=False):
        proj_menu = self.menubar.menu("Project")
        proj_menu.click()
        open_menu_item = proj_menu.child("Open...")
        open_menu_item.click()
        load = self.pitivi.child(roleName='dialog')
        load.child(name="Type a file name", roleName="toggle button").click()
        load.child(roleName='text').text = url
        load.button('Open').click()
        try:
            if save:
                load.child(name="Close without saving", roleName="push button")
        except:
            return

    def search_by_text(self, text, parent, name=None, roleName=None):
        """
        Search a parent widget for childs containing the given text
        """
        children = parent.findChildren(GenericPredicate(roleName=roleName, name=name))
        for child in children:
            if child.text == text:
                return child

    def insert_clip(self, icon, n=1):
        icon.select()
        lib = self.menubar.menu("Library")
        insert = lib.child("Insert at End of Timeline")
        for i in range(n):
            sleep(0.3)
            lib.click()
            sleep(0.1)
            insert.click()
        icon.deselect()

    def import_media(self, filename="1sec_simpsons_trailer.mp4"):
        dogtail.rawinput.pressKey("Esc")  # Ensure the welcome dialog is closed
        # Use the menus, as the main toolbar might be hidden
        lib_menu = self.menubar.menu("Library")
        lib_menu.click()
        import_menu_item = lib_menu.child("Import Files...")
        import_menu_item.click()

        # Force dogtail to look only one level deep, which is much faster
        # as it doesn't have to analyze the whole mainwindow.
        import_dialog = self.pitivi.child(name="Select One or More Files",
                                          roleName="dialog", recursive=False)
        # Instead of checking for the presence of the path text field and then
        # searching for the toggle button to enable it, use the fact that GTK's
        # file chooser allows typing the path directly if it starts with "/".
        dogtail.rawinput.pressKey("/")  # This text will be replaced later

        filepath = os.path.realpath(__file__).split("dogtail_scripts/")[0]
        filepath += "samples/" + filename
        import_dialog.child(roleName='text').text = filepath
        dogtail.rawinput.pressKey("Enter")  # Don't search for the Add button
        sleep(0.6)

        libtab = self.pitivi.tab("Media Library")
        for i in range(5):
            icons = libtab.findChildren(GenericPredicate(roleName="icon"))
            sample = None
            for icon in icons:
                if icon.text == filename:
                    sample = icon
            if sample is not None:
                break
            sleep(0.5)
        self.assertIsNotNone(sample)
        return sample

    def import_media_multiple(self, files):
        dogtail.rawinput.pressKey("Esc")  # Ensure the welcome dialog is closed
        # Use the menus, as the main toolbar might be hidden
        lib_menu = self.menubar.menu("Library")
        lib_menu.click()
        import_menu_item = lib_menu.child("Import Files...")
        import_menu_item.click()

        # Same performance hack as in the import_media method
        import_dialog = self.pitivi.child(name="Select One or More Files",
                                          roleName="dialog", recursive=False)
        dogtail.rawinput.pressKey("/")
        dir_path = os.path.realpath(__file__).split("dogtail_scripts/")[0] + "samples/"
        import_dialog.child(roleName='text').text = dir_path
        dogtail.rawinput.pressKey("Enter")

        # We are now in the samples directory, select various items
        code = dogtail.rawinput.keyNameToKeyCode("Control_L")
        registry.generateKeyboardEvent(code, None, KEY_PRESS)
        for f in files:
            sleep(1)
            import_dialog.child(name=f).click()
        registry.generateKeyboardEvent(code, None, KEY_RELEASE)
        import_dialog.button('Add').click()
        libtab = self.pitivi.tab("Media Library")
        samples = []
        for i in range(5):
            icons = libtab.findChildren(GenericPredicate(roleName="icon"))
            for icon in icons:
                for f in files:
                    if icon.text == f:
                        samples.append(icon)
                        files.remove(f)
            if len(files) == 0:
                break
            sleep(0.5)
        return samples

    def get_timeline(self):
        # TODO: find a better way to identify
        return self.pitivi.children[0].children[0].children[2].children[1].children[3]

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
