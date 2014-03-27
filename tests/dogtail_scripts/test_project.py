#!/usr/bin/env python2

from common import PitiviTestCase, DURATION_OF_ONE_CLIP, DURATION_OF_TWO_CLIPS
from dogtail.predicate import IsATextEntryNamed, GenericPredicate
from dogtail.tree import SearchError
import dogtail.rawinput
from time import time, sleep
import os


class ProjectPropertiesTest(PitiviTestCase):

    def test_cancelling_load_with_no_fallback(self):
        """
        Test the scenario where you have no unsaved changes, go to choose
        a project to load but cancel the file chooser, then try to import clips
        """
        dogtail.rawinput.pressKey("Esc")  # Dismiss the welcome dialog
        dogtail.rawinput.keyCombo("<Control>o")  # Open project
        # The file chooser shows up, dismiss it without choosing any project:
        chooser = self.pitivi.child(name="Open File...", roleName="file chooser", recursive=False)
        chooser.child(name="Cancel", roleName="push button").click()
        # We should be able to import clips in the media library
        # without failing due to a missing app project instance:
        try:
            the_clip = self.import_media()
        except AssertionError:
            self.fail("The clip import dialog didn't work, something is broken")
        self.force_medialibrary_iconview_mode()
        iconview = self.medialibrary.child(roleName="layered pane")
        self.assertEqual(len(iconview.children), 1)
        self.insert_clip(the_clip)
        # Try to quit, it should warn us about unsaved changes.
        dogtail.rawinput.keyCombo("<Control>q")  # Quit the app
        unsaved_changes = self.pitivi.child(name="unsaved changes dialog", roleName="dialog", recursive=False)
        unsaved_changes.button("Close without saving").click()

    def test_settings_video(self):
        # TODO: test the audio and metadata tabs too
        welcome_dialog = self.pitivi.child(name="Welcome", roleName="frame", recursive=False)
        welcome_dialog.button("New").click()
        dialog = self.pitivi.child(name="Project Settings", roleName="dialog", recursive=False)
        video = dialog.tab("Video")

        # Select a different preset
        # CAUTION: changing the resolution changes the pixel aspect ratio!
        video.child(name="720p24", roleName="table cell").click()
        children = video.findChildren(IsATextEntryNamed(""))
        childtext = {}  # The framerate, DAR and PAR custom text entry widgets
        for child in children:
            childtext[child.text] = child
        # Do a quick check to ensure we have all three text entry widgets:
        self.assertIn("1:1", childtext)
        self.assertIn("24M", childtext)
        self.assertIn("16:9", childtext)
        # Then verify the resolution was set correctly from the preset:
        children = video.findChildren(GenericPredicate(roleName="spin button"))
        spintext = {}
        for child in children:
            spintext[child.text] = child
        self.assertIn("1280", spintext)
        self.assertIn("720", spintext)

        #Test frame rate combinations, link button
        frameCombo = video.child(name="23.976 fps", roleName="combo box")
        frameText = childtext["24M"]
        frameCombo.click()
        video.child(name="120 fps", roleName="menu item").click()
        self.assertEqual(frameText.text, "120:1")
        frameText.click()
        frameText.typeText("0")
        video.child(name="12 fps", roleName="combo box")

        # Test pixel and display aspect ratio (PAR and DAR)
        pixelCombo = video.child(name="Square", roleName="combo box")
        pixelText = childtext["1:1"]
        displayCombo = video.child(name="DV Widescreen (16:9)", roleName="combo box")
        displayText = childtext["16:9"]

        pixelCombo.click()
        video.child(name="576p", roleName="menu item").click()
        self.assertEqual(pixelCombo.combovalue, "576p")
        self.assertEqual(pixelText.text, "12:11")
        self.assertEqual(displayText.text, "64:33")

        pixelText.text = "3:4"
        self.assertEqual(pixelText.text, "3:4")
        self.assertEqual(displayCombo.combovalue, "Standard (4:3)")
        self.assertEqual(displayText.text, "4:3")

        video.child(name="Display aspect ratio", roleName="radio button").click()
        displayCombo.click()
        video.child(name="Cinema (1.37)", roleName="menu item").click()
        self.assertEqual(displayCombo.combovalue, "Cinema (1.37)")
        self.assertEqual(displayText.text, "11:8")
        self.assertEqual(pixelText.text, "99:128")

        displayText.text = "37:20"
        self.assertEqual(displayCombo.combovalue, "Cinema (1.85)")
        self.assertEqual(pixelText.text, "333:320")  # It changes further below
        # This check is probably useless, but we never know:
        self.assertEqual(displayText.text, "37:20")

        # Test size spin buttons
        # spinbuttonClick and spinbuttonDoubleClick are methods from HelperFunc
        spin = video.findChildren(GenericPredicate(roleName="spin button"))
        oldtext = spin[1].text
        self.spinbuttonDoubleClick(spin[0])
        spin[0].typeText("1000")
        self.assertEqual(spin[1].text, oldtext)
        self.spinbuttonDoubleClick(spin[1])
        spin[1].typeText("2000")
        video.child(name="Link").click()
        self.spinbuttonDoubleClick(spin[1])
        spin[1].typeText("1000")
        self.spinbuttonClick(spin[0])
        self.assertEqual(spin[0].text, "500")  # Final resolution: 500x1000

        # Apply the changes to the newly created project
        dialog.button("OK").click()

        # A blank project was created, test saving without any clips/objects
        settings_test_project_file = "/tmp/auto_pitivi_test_project_settings.xges"
        self.unlink.append(settings_test_project_file)
        self.saveProject(settings_test_project_file)
        self.assertTrue(self.wait_for_file(settings_test_project_file))
        # Really quit to be sure the stuff was correctly serialized
        self.tearDown(clean=False, kill=False)
        self.setUp()
        self.loadProject(settings_test_project_file)
        sleep(1)  # Give enough time for GES to load the project
        self.pitivi.menu("Edit").click()
        self.pitivi.menuItem("Project Settings").click()
        # Since we shut down the whole app, we must reset our shortcut variables:
        dialog = self.pitivi.child(name="Project Settings", roleName="dialog", recursive=False)
        video = dialog.tab("Video")

        # Check the resolution:
        children = video.findChildren(GenericPredicate(roleName="spin button"))
        spintext = {}
        for child in children:
            spintext[child.text] = child
        self.assertIn("500", spintext, "Video height was not saved")
        self.assertIn("1000", spintext, "Video width was not saved")

        # Check the aspect ratios:
        dialog = self.pitivi.child(name="Project Settings", roleName="dialog", recursive=False)
        video = dialog.tab("Video")
        children = video.findChildren(IsATextEntryNamed(""))
        childtext = {}  # The framerate, DAR and PAR custom text entry widgets
        for child in children:
            childtext[child.text] = child
        # You'd expect a PAR of 333:320 and DAR of 37:20... but we changed the
        # resolution (500x1000) right before saving, so the PAR changed to 37:10
        self.assertIn("37:10", childtext, "Pixel aspect ratio was not saved")
        # However, the DAR is expected to be unaffected by the image resolution:
        self.assertEqual(displayCombo.combovalue, "Cinema (1.85)")
        self.assertIn("37:20", childtext, "Display aspect ratio was not saved")

    def test_backup(self):
        # FIXME: this test would fail in listview mode - for now we just force iconview mode.
        self.force_medialibrary_iconview_mode()

        # Import a clip into an empty project and save the project
        sample = self.import_media()
        filename = "auto_pitivi_test_project-%i.xges" % time()
        path = "/tmp/" + filename
        backup_path = path + "~"
        self.unlink.append(backup_path)

        # Set up one clip in the timeline, then save.
        seektime = self.viewer.child(name="timecode_entry").child(roleName="text")
        self.assertIsNotNone(seektime)
        self.insert_clip(sample)
        self.goToEnd_button = self.viewer.child(name="goToEnd_button")
        self.goToEnd_button.click()
        self.assertEqual(seektime.text, DURATION_OF_ONE_CLIP)
        self.saveProject(path)
        self.assertFalse(os.path.exists(backup_path))

        # Now make some (unsaved) change by inserting a second clip instance:
        self.insert_clip(sample)
        self.goToEnd_button = self.viewer.child(name="goToEnd_button")
        self.goToEnd_button.click()
        self.assertEqual(seektime.text, DURATION_OF_TWO_CLIPS)
        # A backup should appear after 10 secs if no further changes were made
        self.assertTrue(self.wait_for_file(backup_path, timeout=11), "Backup not created")
        self.assertTrue(os.path.getmtime(backup_path) - os.path.getmtime(path) > 0,
                        "Backup is older than saved file")

        # Try to quit, it should warn us about unsaved changes.
        dogtail.rawinput.keyCombo("<Control>q")  # Quit the app
        self.pitivi.child(name="unsaved changes dialog", roleName="dialog", recursive=False).button("Cancel").click()
        # Check again to ensure the backup didn't disappear - and then save
        dogtail.rawinput.keyCombo("<Control>q")  # Quit the app
        self.pitivi.child(name="unsaved changes dialog", roleName="dialog", recursive=False).button("Save").click()
        # The backup should now be deleted, and should not come back:
        sleep(1)
        self.assertFalse(os.path.exists(backup_path))
        sleep(10)
        self.assertFalse(os.path.exists(backup_path))

        # Start the app again, make a trivial change, ensure the backup exists
        self.setUp()
        welcome_dialog = self.pitivi.child(name="Welcome", roleName="frame", recursive=False)
        welcome_dialog.child(name=filename).doubleClick()
        sample = self.import_media("flat_colour1_640x480.png")
        # Go figure why, this one takes much longer (~27 secs) to appear:
        self.assertTrue(self.wait_for_file(backup_path, timeout=35), "Backup not created")
        self.tearDown(clean=False, kill=True)
        sleep(0.5)

        # After another "crash", try loading from the backup.
        self.setUp()
        seektime = self.viewer.child(name="timecode_entry").child(roleName="text")
        welcome_dialog = self.pitivi.child(name="Welcome", roleName="frame", recursive=False)
        welcome_dialog.child(name=filename).doubleClick()
        self.pitivi.child(name="restore from backup dialog", roleName="dialog", recursive=False).button("Restore from backup").click()
        # Ensure the backup ACTUALLY LOADED instead of a blank project. Really.
        sleep(5)
        iconview = self.medialibrary.child(roleName="layered pane")
        self.assertEqual(len(iconview.children), 2, "Loaded from backup but the media library does not have the expected amount of clips")
        self.goToEnd_button = self.viewer.child(name="goToEnd_button")
        self.goToEnd_button.click()
        self.assertEqual(seektime.text, DURATION_OF_TWO_CLIPS)
        # ...and that clicking "Save" actually triggers "Save As":
        dogtail.rawinput.keyCombo("<Control>s")  # Save project
        try:
            _save_as_dialog = self.pitivi.child(name="Save As...", roleName="file chooser", recursive=False, retry=False)
            dogtail.rawinput.pressKey("Esc")  # Dismiss the dialog
        except SearchError:
            self.fail('Clicking "Save" after loading a backup project should have triggered the "Save As" dialog')
        # Do not save, kill once more - the backup should be preserved
        # and the user should be prompted again on the next startup
        self.tearDown(clean=False, kill=True)
        timestamp = os.path.getmtime(backup_path)
        sleep(0.5)
        self.setUp()
        welcome_dialog = self.pitivi.child(name="Welcome", roleName="frame", recursive=False)
        welcome_dialog.child(name=filename).doubleClick()
        self.pitivi.child(name="restore from backup dialog", roleName="dialog", recursive=False).button("Ignore backup").click()
        # The backup file must not have changed or vanished:
        self.assertEqual(timestamp, os.path.getmtime(backup_path))

        #Look if backup updated, even it is newer than saved project
        sample = self.import_media("flat_colour2_640x480.png")
        self.assertTrue(self.wait_for_update(backup_path, timestamp))

        # Quitting should warn us about unsaved changes (still in a newer version)
        dogtail.rawinput.keyCombo("<Control>q")  # Quit the app
        # Dismiss the unsaved changes warning by cancelling it:
        self.pitivi.child(name="unsaved changes dialog", roleName="dialog", recursive=False).button("Cancel").click()
        # Save stuff behind the scenes...
        self.saveProject(saveAs=False)
        # The backup file should now be gone, and no warning displayed:
        dogtail.rawinput.keyCombo("<Control>q")  # Quit the app
        self.assertFalse(os.path.exists(backup_path))

    def test_load_save(self):
        self.goToEnd_button = self.viewer.child(name="goToEnd_button")
        seektime = self.viewer.child(name="timecode_entry").child(roleName="text")
        infobar_media = self.medialibrary.child(name="Information", roleName="alert")
        iconview = self.medialibrary.child(roleName="layered pane")
        filename1 = "/tmp/auto_pitivi_test_project-1.xges"
        filename2 = "/tmp/auto_pitivi_test_project-2.xges"
        self.unlink.append(filename1)
        self.unlink.append(filename2)

        # FIXME: this test would fail in listview mode - for now we just force iconview mode.
        self.force_medialibrary_iconview_mode()

        # Create project #1 - one clip with only one instance on the timeline
        self.assertTrue(infobar_media.showing)
        project1_sample1 = self.import_media()
        self.assertTrue(self.wait_for_node_hidden(infobar_media, timeout=4))
        self.insert_clip(project1_sample1)
        self.saveProject(filename1)

        # Creating a blank project should clear the library and show its infobar
        sleep(0.5)
        dogtail.rawinput.keyCombo("<Control>n")  # Create a new project
        self.pitivi.child(name="Project Settings", roleName="dialog", recursive=False).button("OK").click()

        self.assertEqual(len(iconview.children), 0,
            "Created a new project, but the media library is not empty")
        self.assertTrue(infobar_media.showing)
        # We don't have a very good way to check that the timeline was cleared,
        # but this is better than nothing as a quick sanity check:
        self.goToEnd_button.click()
        sleep(0.5)
        self.assertEqual(seektime.text, "00:00.000", "The timeline is not empty")

        # Create project #2 - 2 clips with 2 timeline instances of the first one
        # We use only the first one on the timeline because we know its duration
        project2_sample1 = self.import_media()
        __project2_sample2 = self.import_media("flat_colour1_640x480.png")
        self.assertFalse(infobar_media.showing)
        sleep(0.5)
        self.insert_clip(project2_sample1, 2)
        sleep(1)
        self.assertEqual(len(iconview.children), 2)
        self.goToEnd_button.click()
        self.assertEqual(seektime.text, DURATION_OF_TWO_CLIPS)
        self.saveProject(filename2)

        # Provoke an unsaved change and switch back to project #1.
        # - We should be warned about unsaved changes
        # - The number of clips in the library should have changed
        # - The timeline length should have changed
        sleep(1)
        project2_sample1.click()
        sleep(0.5)
        self.medialibrary.child(name="media_remove_button").click()
        self.assertEqual(len(iconview.children), 1,
            "A clip has just been removed so only one should be left")
        self.loadProject(filename1, unsaved_changes="discard")
        sleep(3)
        self.assertEqual(len(iconview.children), 1)
        self.assertFalse(infobar_media.showing)
        self.goToEnd_button.click()
        self.assertEqual(seektime.text, DURATION_OF_ONE_CLIP)

        # Switch back to project #2, expect the same thing.
        self.loadProject(filename2)
        sleep(3)
        self.assertEqual(len(iconview.children), 2)
        self.assertFalse(infobar_media.showing)
        self.goToEnd_button.click()
        self.assertEqual(seektime.text, DURATION_OF_TWO_CLIPS)
