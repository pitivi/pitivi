#!/usr/bin/env python
from helper_functions import HelpFunc
from dogtail.tree import SearchError
from dogtail.predicate import GenericPredicate, IsATextEntryNamed


class DialogsClipMediaPropsTest(HelpFunc):
    def test_clip_props_dialog(self):
        sample = self.import_media("flat_colour1_640x480.png")
        sample.click(3)
        buttons = self.pitivi.findChildren(GenericPredicate(name="Clip Properties..."))
        buttons[1].click()

        #Check if we have real info, can't check if in correct place.
        dialog = self.pitivi.child(name="Clip Properties", roleName="dialog")
        labels = {"640", "480"}
        real_labels = set([])
        for label in dialog.findChildren(GenericPredicate(roleName="label")):
            real_labels.add(label.text)
        self.assertEqual(len(labels.difference(real_labels)), 0, "Not all info is displayed")
        self.assertFalse(dialog.child(name="Audio:", roleName="panel").showing)
        dialog.child(name="Cancel").click()
        sample.deselect()

        sample = self.import_media()
        sample.select()
        self.menubar.menu("Library").click()
        self.menubar.menuItem("Clip Properties...").click()

        #Check if we have real info, can't check if in correct place.
        dialog = self.pitivi.child(name="Clip Properties", roleName="dialog")
        labels = {"1280", "544", "23.976 fps", "Square", "Stereo", "48 KHz", "16 bit"}
        real_labels = set([])
        for label in dialog.findChildren(GenericPredicate(roleName="label")):
            real_labels.add(label.text)
        self.assertEqual(len(labels.difference(real_labels)), 0, "Not all info is displayed")

        #Uncheck frame rate
        dialog.child(name="Frame rate:").click()
        dialog.child(name="Apply to project").click()

        #Check if correctly applied
        self.menubar.menu("Edit").click()
        self.pitivi.child(name="Project Settings", roleName="menu item").click()
        dialog = self.pitivi.child(name="Project Settings", roleName="dialog")

        children = dialog.findChildren(IsATextEntryNamed(""))
        childtext = {}
        for child in children:
                childtext[child.text] = child

        self.assertIn("25:1", childtext)
        self.assertIn("1:1", childtext)
        children = dialog.findChildren(GenericPredicate(roleName="spin button"))
        spintext = {}
        for child in children:
                spintext[child.text] = child
        self.assertIn("1280", spintext)
        self.assertIn("544", spintext)
