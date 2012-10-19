#!/usr/bin/env python
from helper_functions import HelpFunc
from dogtail.predicate import IsATextEntryNamed, GenericPredicate
from time import time, sleep
import os


class ProjectPropertiesTest(HelpFunc):
    def test_settings_video(self):
        welcome_dialog = self.pitivi.child(name="Welcome", roleName="frame", recursive=False)
        welcome_dialog.button("New").click()

        #Play with project settings, look if they are correctly represented
        dialog = self.pitivi.child(name="Project Settings", roleName="dialog", recursive=False)
        video = dialog.tab("Video")

        #Test presets
        video.child(name="720p24", roleName="table cell").click()
        children = video.findChildren(IsATextEntryNamed(""))
        childtext = {}
        for child in children:
            childtext[child.text] = child

        self.assertIn("1:1", childtext)
        self.assertIn("24M", childtext)
        self.assertIn("16:9", childtext)

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

        #Test pixel and display ascpect ratio
        pixelCombo = video.child(name="Square", roleName="combo box")
        pixelText = childtext["1:1"]
        displayCombo = video.child(name="DV Widescreen (16:9)", roleName="combo box")
        displayText = childtext["16:9"]

        pixelCombo.click()
        video.child(name="576p", roleName="menu item").click()
        self.assertEqual(pixelCombo.combovalue, "576p")
        self.assertEqual(pixelText.text, "12:11")
        #self.assertEqual(displayCombo.combovalue, "")
        self.assertEqual(displayText.text, "64:33")

        pixelText.doubleClick()
        pixelText.click()
        pixelText.typeText("3:4")
        #self.assertEqual(pixelCombo.combovalue, "")
        self.assertEqual(pixelText.text, "3:4")
        self.assertEqual(displayCombo.combovalue, "Standard (4:3)")
        self.assertEqual(displayText.text, "4:3")

        video.child(name="Display aspect ratio", roleName="radio button").click()
        displayCombo.click()
        video.child(name="Cinema (1.37)", roleName="menu item").click()
        #self.assertEqual(pixelCombo.combovalue, "")
        self.assertEqual(pixelText.text, "99:128")
        self.assertEqual(displayCombo.combovalue, "Cinema (1.37)")
        self.assertEqual(displayText.text, "11:8")

        displayText.doubleClick()
        displayText.click()
        displayText.typeText("37:20")
        #self.assertEqual(pixelCombo.combovalue, "")
        self.assertEqual(pixelText.text, "333:320")
        self.assertEqual(displayCombo.combovalue, "Cinema (1.85)")
        self.assertEqual(displayText.text, "37:20")

        #Test size spin buttons
        spin = video.findChildren(GenericPredicate(roleName="spin button"))
        oldtext = spin[1].text
        spin[0].doubleClick()
        spin[0].typeText("1000")
        self.assertEqual(spin[1].text, oldtext)
        spin[1].doubleClick()
        spin[1].typeText("2000")
        video.child(name="Link").click()
        spin[1].doubleClick()
        spin[1].typeText("1000")
        spin[0].click()
        self.assertEqual(spin[0].text, "500")

        # Finally create the blank project
        dialog.button("OK").click()

        # A blank project was created, test saving without any clips/objects
        settings_test_project_file = "/tmp/settings.xptv"
        self.unlink.append(settings_test_project_file)
        self.saveProject(settings_test_project_file)
        sleep(1)  # Give enough time for GES to save the project
        self.assertTrue(os.path.exists(settings_test_project_file))
        # Load project and test settings
        self.loadProject(settings_test_project_file)
        sleep(1)  # Give enough time for GES to load the project
        self.pitivi.menu("Edit").click()
        self.pitivi.menuItem("Project Settings").click()

        dialog = self.pitivi.child(name="Project Settings", roleName="dialog", recursive=False)
        video = dialog.tab("Video")
        children = video.findChildren(IsATextEntryNamed(""))
        childtext = {}
        for child in children:
            childtext[child.text] = child

        self.assertIn("333:320", childtext, "Pixel aspect ration not saved")
        self.assertIn("37:20", childtext, "Display aspect ratio not saved")

        children = video.findChildren(GenericPredicate(roleName="spin button"))
        spintext = {}
        for child in children:
            spintext[child.text] = child
        self.assertIn("500", spintext, "Video height is not saved")
        self.assertIn("1000", spintext, "Video width is not saved")

    def wait_for_file(self, path, time_out=20):
        sleeped = 0
        exists = False
        while (sleeped <= time_out) and not exists:
            sleeped += 2
            sleep(2)
            exists = os.path.exists(path)
        return exists

    def wait_for_update(self, path, timestamp, time_out=20):
        sleeped = 0
        new_timestamp = False
        while (sleeped <= time_out) and new_timestamp == timestamp:
            sleeped += 2
            sleep(2)
            new_timestamp = os.path.getmtime(path)
        return new_timestamp != timestamp

    def test_backup(self):
        #Create empty project
        sample = self.import_media()

        #Save project
        filename = "test_project-%i.xptv" % time()
        path = "/tmp/" + filename
        backup_path = path + "~"
        self.unlink.append(backup_path)
        self.saveProject(path)

        #Change somthing
        seektime = self.viewer.child(name="timecode_entry").child(roleName="text")
        self.assertIsNotNone(seektime)
        self.insert_clip(sample)
        self.goToEnd_button = self.viewer.child(name="goToEnd_button")
        self.goToEnd_button.click()
        self.assertEqual(seektime.text, "0:00:01.227")

        #It should save after 10 seconds if no changes made
        self.assertTrue(self.wait_for_file(backup_path), "Backup not created")
        self.assertTrue(os.path.getmtime(backup_path) -
                        os.path.getmtime(path) > 0,
                        "Backup is older than saved file")

        #Try to quit, it should warn us
        self.menubar.menu("Project").click()
        self.menubar.menu("Project").menuItem("Quit").click()

        #If finds button, means it warned
        self.pitivi.child(roleName="dialog", recursive=False).button("Cancel").click()
        self.saveProject(saveAs=False)
        #Backup should be deleted, and no warning displayed
        self.menubar.menu("Project").click()
        self.menubar.menu("Project").menuItem("Quit").click()
        self.assertFalse(os.path.exists(backup_path))
        #Test if backup is found
        self.setUp()
        welcome_dialog = self.pitivi.child(name="Welcome", roleName="frame", recursive=False)
        welcome_dialog.child(name=filename).doubleClick()
        sample = self.import_media("flat_colour1_640x480.png")
        self.assertTrue(self.wait_for_file(backup_path, 120), "Backup not created")
        self.tearDown(clean=False, kill=True)
        self.setUp()
        welcome_dialog = self.pitivi.child(name="Welcome", roleName="frame", recursive=False)
        welcome_dialog.child(name=filename).doubleClick()
        #Try restoring from backup
        self.pitivi.child(roleName="dialog", recursive=False).button("Restore from backup").click()
        samples = self.medialibrary.findChildren(GenericPredicate(roleName="icon"))
        self.assertEqual(len(samples), 2)
        self.menubar.menu("Project").click()
        self.assertFalse(self.menubar.menu("Project").menuItem("Save").sensitive)
        #Behaved as saveAs

        # Kill once more
        self.tearDown(clean=False, kill=True)
        timestamp = os.path.getmtime(backup_path)
        self.setUp()
        welcome_dialog = self.pitivi.child(name="Welcome", roleName="frame", recursive=False)
        welcome_dialog.child(name=filename).doubleClick()
        self.pitivi.child(roleName="dialog", recursive=False).button("Ignore backup").click()
        #Backup is not deleted, not changed
        self.assertEqual(timestamp, os.path.getmtime(backup_path))

        #Look if backup updated, even it is newer than saved project

        sample = self.import_media("flat_colour2_640x480.png")
        self.assertTrue(self.wait_for_update(backup_path, timestamp))
        #Try to quit, it should warn us (still newer version)
        self.menubar.menu("Project").click()
        self.menubar.menu("Project").menuItem("Quit").click()

        # Dismiss the unsaved changes warning by cancelling it:
        self.pitivi.child(roleName="dialog", recursive=False).button("Cancel").click()
        self.saveProject(saveAs=False)

        #Backup should be deleted, and no warning displayed
        self.menubar.menu("Project").click()
        self.menubar.menu("Project").menuItem("Quit").click()
        self.assertFalse(os.path.exists(backup_path))

    def test_load_save(self):
        self.goToEnd_button = self.viewer.child(name="goToEnd_button")
        seektime = self.viewer.child(name="timecode_entry").child(roleName="text")
        infobar_media = self.medialibrary.child(name="Information", roleName="alert")
        filename1 = "/tmp/test_project-%i.xptv" % time()
        filename2 = "/tmp/test_project-%i.xptv" % time()

        #Create project
        self.assertTrue(infobar_media.showing)
        sample = self.import_media()
        self.insert_clip(sample)
        self.saveProject(filename1)
        self.assertFalse(infobar_media.showing)

        #Create new, check if cleaned
        sleep(0.5)
        self.menubar.menu("Project").click()
        self.menubar.menu("Project").menuItem("New").click()
        self.pitivi.child(name="Project Settings", roleName="dialog", recursive=False).button("OK").click()

        icons = self.medialibrary.findChildren(GenericPredicate(roleName="icon"))
        self.goToEnd_button.click()
        self.assertEqual(len(icons), 0)
        self.assertTrue(infobar_media.showing)

        #Create bigger project
        sample = self.import_media()
        self.import_media("flat_colour1_640x480.png")
        self.insert_clip(sample, 2)
        self.saveProject(filename2)
        self.assertFalse(infobar_media.showing)

        #Load first, check if populated
        self.load_project(filename1)
        icons = self.medialibrary.findChildren(GenericPredicate(roleName="icon"))
        self.goToEnd_button.click()
        self.assertEqual(len(icons), 1)
        self.assertEqual(seektime.text, "0:00:01.227")
        self.assertFalse(infobar_media.showing)

        #Load second, check if populated
        self.load_project(filename2)
        icons = self.medialibrary.findChildren(GenericPredicate(roleName="icon"))
        self.goToEnd_button.click()
        self.assertEqual(len(icons), 2)
        self.assertEqual(seektime.text, "0:00:02.455")
        self.assertFalse(infobar_media.showing)
