#!/usr/bin/env python
from helper_functions import HelpFunc
from dogtail.tree import SearchError
from dogtail.predicate import GenericPredicate, IsATextEntryNamed


class DialogsClipMediaPropsTest(HelpFunc):
    def test_clip_props_dialog(self):
        sample = self.import_media("flat_colour1_640x480.png")
        sample.click()
        media_props_button = self.medialibrary.child(name="media_props_button")
        media_props_button.click()

        # Now check that a dialog shows up with the clip's properties:
        dialog = self.pitivi.child(name="Clip Properties", roleName="dialog", recursive=False)
        labels = {"640", "480"}
        real_labels = set([])
        for label in dialog.findChildren(GenericPredicate(roleName="label")):
            real_labels.add(label.text)
        self.assertEqual(len(labels.difference(real_labels)), 0,
            "Info seems incorrect\n\tExpected: %s \n\tObtained: %s" % (labels, real_labels))
        self.assertFalse(dialog.child(name="Audio:", roleName="panel").showing)
        dialog.child(name="Cancel").click()
        sample.deselect()

        # Do the same thing for "tears of steel.webm":
        sample = self.import_media()
        sample.select()
        media_props_button.click()

        # Check again for the presence of the dialog and its contents
        dialog = self.pitivi.child(name="Clip Properties", roleName="dialog", recursive=False)
        # These are the properties of "tears of steel.webm":
        labels = {"Video:", "960", "400", "25 fps", "Square",
                "Audio:", "Mono", "44.1 kHz", "32 bit"}
        real_labels = set([])
        for label in dialog.findChildren(GenericPredicate(roleName="label")):
            real_labels.add(label.text)
        self.assertEqual(len(labels.difference(real_labels)), 0,
            "Info seems incorrect.\n\tExpected: %s \n\tObtained: %s" % (labels, real_labels))

        # Uncheck the "mono" channels, so the project should stay stereo
        dialog.child(name="Channels:").click()
        dialog.child(name="Apply to project").click()

        #Check if correctly applied
        self.menubar.menu("Edit").click()
        self.menubar.menuItem("Project Settings").click()
        dialog = self.pitivi.child(name="Project Settings", roleName="dialog", recursive=False)

        children = dialog.findChildren(IsATextEntryNamed(""))
        childtext = {}
        for child in children:
            childtext[child.text] = child
        # Framerates and aspect ratio:
        self.assertIn("25:1", childtext)
        self.assertIn("1:1", childtext)
        children = dialog.findChildren(GenericPredicate(roleName="spin button"))
        spintext = {}
        for child in children:
            spintext[child.text] = child
        self.assertIn("960", spintext)
        self.assertIn("400", spintext)

        # Previously, we asked to not override the "stereo" setting with "mono"
        # Search for a combobox that currently has the label "Stereo":
        try:
            dialog.child(name="Stereo", roleName="combo box")
        except SearchError:
            self.fail('"Mono" clip property was applied to project settings. Expected the "Stereo" setting to be preserved.')
