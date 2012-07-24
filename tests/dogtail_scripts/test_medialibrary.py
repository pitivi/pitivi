#!/usr/bin/env python
from helper_functions import HelpFunc
from time import sleep


class MediaLibraryTest(HelpFunc):

    def test_medialibrary(self):
        # FIXME: this test will fail if the media library is in listview mode
        samples = []
        samples.append(self.import_media("flat_colour1_640x480.png"))
        samples.append(self.import_media("flat_colour2_640x480.png"))
        samples.append(self.import_media("flat_colour3_320x180.png"))
        self.insert_clip(samples[0])
        self.insert_clip(samples[2])

        self.menubar.menu("Library").click()
        self.menubar.menu("Library").menuItem("Select Unused Media").click()
        self.assertFalse(samples[0].isSelected)
        self.assertTrue(samples[1].isSelected)
        self.assertFalse(samples[2].isSelected)

        tab = self.pitivi.tab("Media Library")
        iconview = tab.child(roleName="layered pane")
        self.assertEqual(len(iconview.children), 3)
        search = tab.textentry("")
        search.click()
        search.typeText("colour2")
        self.assertEqual(len(iconview.children), 1)
        search.text = ""
        search.typeText("640")
        self.assertEqual(len(iconview.children), 2)
        search.text = ""
        self.assertEqual(len(iconview.children), 3)
        search.doubleClick()  # Select all
        search.typeText("colour2")
        self.assertEqual(len(iconview.children), 1)

        # Check how search results react to importing new clips.
        search.text = ""
        search.typeText("colour")
        self.assertEqual(len(iconview.children), 3)
        self.import_media()  # Not appending to Samples, because it will be None
        # The default clip that gets imported does not have "colour" in its name
        self.assertEqual(len(iconview.children), 3)
        # However, these ones should show up immediately in the iconview:
        samples.append(self.import_media_multiple(["flat_colour4_1600x1200.jpg", "flat_colour5_1600x1200.jpg"]))
        self.assertEqual(len(iconview.children), 5)
        search.text = ""
        self.assertEqual(len(iconview.children), 6)

        # Search for the remaining clips that were not inserted in the timeline,
        # then insert them all at once.
        self.menubar.menu("Library").click()
        self.menubar.menu("Library").menuItem("Select Unused Media").click()
        self.menubar.menu("Library").click()
        self.menubar.menu("Library").menuItem("Insert at End of Timeline").click()
        sleep(0.5)
        self.menubar.menu("Library").click()
        self.menubar.menu("Library").menuItem("Select Unused Media").click()
        sleep(0.5)
        for icon in iconview.children:
            self.assertFalse(icon.isSelected)
