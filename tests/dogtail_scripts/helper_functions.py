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
    def saveProject(self, url=None, saveAs=True):
        self.menubar.menu("Project").click()
        if saveAs:
            #FIXME: cant get working with searching for Save As…
            self.menubar.menu("Project").children[4].click()
            saveas = self.pitivi.child(roleName='dialog')
            saveas.child(roleName='text').text = url
            #Click the Save button.
            saveas.button('Save').click()
            #Save for deleting afterwards
            self.unlink.append(url)
        else:
            #Just save
            self.menubar.menu("Project").menuItem("Save").click()

    def loadProject(self, url, save=False):
        self.menubar.menu("Project").click()
        self.menubar.menu("Project").children[2].click()
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
        children = parent.findChildren(GenericPredicate(roleName=roleName,
                                                        name=name))
        searched = None
        for child in children:
            if child.text == text:
                searched = child
        return searched

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
        #Just try search for object without retries
        dogtail.rawinput.pressKey("Esc")
        self.pitivi.child(name="Import Files...",
                          roleName="push button").click()
        add = self.pitivi.child(roleName='dialog')
        textf = add.findChildren(GenericPredicate(roleName="text"))
        if len(textf) == 0:
            add.child(name="Type a file name", roleName="toggle button").click()
        filepath = os.path.realpath(__file__).split("dogtail_scripts/")[0]
        filepath += "samples/" + filename
        add.child(roleName='text').text = filepath
        add.button('Add').click()
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
        dogtail.rawinput.pressKey("Esc")
        self.pitivi.child(name="Import Files...",
                          roleName="push button").click()
        add = self.pitivi.child(roleName='dialog')
        textf = add.findChildren(GenericPredicate(roleName="text"))
        if len(textf) == 0:
            add.child(name="Type a file name", roleName="toggle button").click()
        filepath = os.path.realpath(__file__).split("dogtail_scripts/")[0]
        filepath += "samples/"
        add.child(roleName='text').click()
        add.child(roleName='text').text = filepath
        dogtail.rawinput.pressKey("Enter")
        #Now select them
        code = dogtail.rawinput.keyNameToKeyCode("Control_L")
        registry.generateKeyboardEvent(code, None, KEY_PRESS)
        for f in files:
            sleep(1)
            add.child(name=f).click()
        registry.generateKeyboardEvent(code, None, KEY_RELEASE)
        add.button('Add').click()
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
        #TODO: found better way to identify
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
