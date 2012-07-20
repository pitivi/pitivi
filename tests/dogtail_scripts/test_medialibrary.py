#!/usr/bin/env python
from test_help_func import HelpFunc


class MediaLibraryTest(HelpFunc):
    def test_medialibrary(self):
        #Load few samples
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
        search.text = "colour2"
        self.assertEqual(len(iconview.children), 1)
        search.text = "640"
        self.assertEqual(len(iconview.children), 2)
        search.text = ""
        self.assertEqual(len(iconview.children), 3)
