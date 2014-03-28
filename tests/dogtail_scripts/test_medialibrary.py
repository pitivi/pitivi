#!/usr/bin/env python2

from common import PitiviTestCase
from time import sleep


class MediaLibraryTest(PitiviTestCase):

    def test_medialibrary(self):
        # Some commonly-used widgets in this test:
        search = self.medialibrary.child(name="media_search_entry", roleName="text")
        unused_media_button = search.child(name="starred-symbolic", roleName="icon")

        self.force_medialibrary_iconview_mode()

        samples = []
        samples.append(self.import_media("flat_colour1_640x480.png"))
        samples.append(self.import_media("flat_colour2_640x480.png"))
        samples.append(self.import_media("flat_colour3_320x180.png"))
        self.insert_clip(samples[0])
        self.insert_clip(samples[2])

        unused_media_button.click()
        self.assertFalse(samples[0].isSelected)
        self.assertTrue(samples[1].isSelected)
        self.assertFalse(samples[2].isSelected)

        iconview = self.medialibrary.child(roleName="layered pane")
        self.assertEqual(len(iconview.children), 3)
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
        unused_media_button.click()
        self.insert_button.click()
        sleep(0.5)
        unused_media_button.click()
        sleep(0.5)
        for icon in iconview.children:
            self.assertFalse(icon.isSelected)
