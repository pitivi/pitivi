#!/usr/bin/env python2

from helper_functions import HelpFunc
from dogtail.tree import SearchError
import dogtail.rawinput
from time import sleep
from pyatspi import Registry as registry
from pyatspi import KEY_PRESS, KEY_RELEASE

from test_base import DURATION_OF_ONE_CLIP, DURATION_OF_TWO_CLIPS


class TimelineTest(HelpFunc):
    def setUp(self):
        super(TimelineTest, self).setUp()
        self.goToEnd_button = self.viewer.child(name="goToEnd_button")
        self.goToStart_button = self.viewer.child(name="goToStart_button")

    def insertTwoClipsAndSeekToEnd(self):
        # Just a small helper method to facilitate timeline setup
        sample = self.import_media()
        self.insert_clip(sample, 2)
        try:
            self.goToEnd_button.click()
        except NotImplementedError:
            # That's a lie. pyatspi's Accessibility.py is just raising that
            # when it didn't have enough time to find and click the widget.
            # Wait and try again.
            sleep(0.5)
            self.goToEnd_button.click()

    def test_drag_clip(self):
        sample = self.import_media()
        timecode_widget = self.viewer.child(name="timecode_entry").child(roleName="text")
        self.assertIsNotNone(timecode_widget)

        self.improved_drag(self.center(sample), self.center(self.timeline))
        self.goToEnd_button.click()
        self.assertNotEqual(timecode_widget.text, "00:00.000")

    def test_multiple_drag(self):
        sample = self.import_media()
        timecode_widget = self.viewer.child(name="timecode_entry").child(roleName="text")
        timeline = self.timeline
        self.assertIsNotNone(timecode_widget)
        oldseek = timecode_widget.text
        # Provide three sets of coordinates (on three layers) at the end of the
        # timeline, where we will drag clips to. Here we don't have to worry
        # about the width of layer controls widget for our calculations.
        endpos = []
        drag_x = timeline.position[0] + timeline.size[0] - 30
        drag_y = timeline.position[1]
        endpos.append((drag_x, drag_y + 30))
        endpos.append((drag_x, drag_y + 120))
        endpos.append((drag_x, drag_y + 80))
        for i in range(20):
            if i % 4 == 0:
                # Drag to center, next layer, out, and then back in
                middle = [self.center(timeline), endpos[(i + 1) % 2], self.center(sample)]
                self.improved_drag(self.center(sample), endpos[i % 3], middle=middle)
            else:
                # Simple drag
                self.improved_drag(self.center(sample), endpos[i % 3])
            # Give time to insert the object. If you don't wait long enough,
            # dogtail won't be able to click goToEnd_button:
            sleep(0.7)
            dogtail.rawinput.keyCombo("<Control>minus")  # Zoom out
            try:
                self.goToEnd_button.click()
            except NotImplementedError:
                # That's a lie. pyatspi's Accessibility.py is just raising that
                # when it didn't have enough time to find and click the widget.
                # Wait and try again.
                sleep(0.5)
                self.goToEnd_button.click()
            seek = timecode_widget.text
            self.assertNotEqual(oldseek, seek)
            oldseek = seek

    def test_split(self):
        self.insertTwoClipsAndSeekToEnd()
        timecode_widget = self.viewer.child(name="timecode_entry").child(roleName="text")
        self.assertEqual(timecode_widget.text, DURATION_OF_TWO_CLIPS)

        dogtail.rawinput.click(self.getTimelineX(0.75), self.getTimelineY(0))
        self.timeline_toolbar.child(name="Split", roleName="push button").click()
        # Delete the first half of the split clip.
        dogtail.rawinput.click(self.getTimelineX(0.75 - 0.125), self.getTimelineY(0))
        self.timeline_toolbar.child(name="Delete", roleName="push button").click()
        self.goToEnd_button.click()
        self.assertEqual(timecode_widget.text, DURATION_OF_TWO_CLIPS)

        # Delete also the second half of the split clip.
        dogtail.rawinput.click(self.getTimelineX(0.75 + 0.125), self.getTimelineY(0))
        dogtail.rawinput.pressKey("Del")

        self.goToEnd_button.click()
        # Allow the UI to update
        sleep(0.1)
        self.assertEqual(timecode_widget.text, DURATION_OF_ONE_CLIP)

    def test_multiple_split(self):
        self.insertTwoClipsAndSeekToEnd()
        timecode_widget = self.viewer.child(name="timecode_entry").child(roleName="text")
        self.assertEqual(timecode_widget.text, DURATION_OF_TWO_CLIPS)
        pos = (0.05, 0.48, 0.17, 0.24, 0.35, 0.61, 0.41, 0.51)
        for k in pos:
            for p in pos:
                dogtail.rawinput.click(self.getTimelineX(p + k / 10), self.getTimelineY(0))
                # Allow the UI to update
                sleep(0.1)
                # Split
                dogtail.rawinput.pressKey("s")
                try:
                    self.pitivi.child(roleName="icon")
                except SearchError:
                    self.fail("App stopped responding while splitting clips")

    def test_transition(self):
        self.insertTwoClipsAndSeekToEnd()
        timecode_widget = self.viewer.child(name="timecode_entry").child(roleName="text")
        self.assertEqual(timecode_widget.text, DURATION_OF_TWO_CLIPS)

        sleep(0.1)
        dogtail.rawinput.press(self.getTimelineX(0.75), self.getTimelineY(0))
        # Drag in, this should create a transition.
        dogtail.rawinput.absoluteMotion(self.getTimelineX(0.5), self.getTimelineY(0))
        sleep(0.1)
        # Drag out, the transition should be gone.
        dogtail.rawinput.absoluteMotion(self.getTimelineX(0.9), self.getTimelineY(0))
        sleep(0.1)
        # Drag in again, this should create a transition.
        dogtail.rawinput.absoluteMotion(self.getTimelineX(0.25), self.getTimelineY(0))
        sleep(0.1)
        dogtail.rawinput.release(self.getTimelineX(0.5), self.getTimelineY(0))
        sleep(0.1)

        # Click the transition, make sure it's selected.
        dogtail.rawinput.click(self.getTimelineX(0.5 - 0.125), self.getTimelineY(0))
        sleep(0.1)
        iconlist = self.transitions.child(roleName="layered pane")
        self.assertTrue(iconlist.sensitive)
        iconlist.children[-2].select()
        self.assertTrue(self.transitions.child(roleName="slider").sensitive)
        self.transitions.child(roleName="slider").value = 50

    def search_clip_end(self, y, timecode_widget, timeline):
        minx = timeline.position[0] + 10.
        maxx = timeline.position[0] + timeline.size[0] - 10.
        minx = (minx + maxx) / 2
        y += timeline.position[1]
        dogtail.rawinput.click(maxx, y)
        maxseek = timecode_widget.text
        while maxx - minx > 2:
            middle = (maxx + minx) / 2
            dogtail.rawinput.click(middle, y)
            sleep(0.1)
            if timecode_widget.text == maxseek:
                maxx = middle
            else:
                minx = middle
        #+5 due to handle size
        return maxx - timeline.position[0] + 5

    def ripple_roll(self, from_percent, to_percent):
        dogtail.rawinput.click(self.getTimelineX(from_percent), self.getTimelineY(0))
        sleep(0.1)
        registry.generateKeyboardEvent(dogtail.rawinput.keyNameToKeyCode("Shift_L"), None, KEY_PRESS)
        try:
            dogtail.rawinput.press(self.getTimelineX(from_percent), self.getTimelineY(0))
            dogtail.rawinput.absoluteMotion(self.getTimelineX(to_percent), self.getTimelineY(0))
            sleep(0.1)
            dogtail.rawinput.release(self.getTimelineX(to_percent), self.getTimelineY(0))
        finally:
            registry.generateKeyboardEvent(dogtail.rawinput.keyNameToKeyCode("Shift_L"), None, KEY_RELEASE)
        sleep(0.1)

    def test_ripple_roll(self):
        self.insertTwoClipsAndSeekToEnd()
        timecode_widget = self.viewer.child(name="timecode_entry").child(roleName="text")
        self.assertEqual(timecode_widget.text, DURATION_OF_TWO_CLIPS)

        def ripple_roll(from_percent, to_percent):
            self.ripple_roll(from_percent, to_percent)
            self.goToEnd_button.click()
            sleep(0.1)
            self.assertGreater(timecode_widget.text, DURATION_OF_TWO_CLIPS)
            self.goToStart_button.click()
            sleep(0.1)
            self.ripple_roll(to_percent, from_percent)
            self.goToEnd_button.click()
            sleep(0.1)
            self.assertEqual(timecode_widget.text, DURATION_OF_TWO_CLIPS)
            self.goToStart_button.click()

        ripple_roll(from_percent=0.25, to_percent=0.75)

        # Check if adding an effect causes a regression in behavior.
        self.effectslibrary.click()
        self.clipproperties.click()
        table = self.clipproperties.child(roleName="table")
        effect_from_library = self.search_by_text("Agingtv", self.effectslibrary, roleName="table cell", exactMatchOnly=False)
        self.improved_drag(self.center(effect_from_library), self.center(table))
        sleep(1.1)
        ripple_roll(from_percent=0.25, to_percent=0.75)

    def test_image_video_mix(self):
        files = ["tears_of_steel.webm", "flat_colour2_640x480.png",
                 "flat_colour4_1600x1200.jpg", "flat_colour1_640x480.png",
                 "flat_colour3_320x180.png", "flat_colour5_1600x1200.jpg"]
        samples = self.import_media_multiple(files)
        timecode_widget = self.viewer.child(name="timecode_entry").child(roleName="text")
        tpos = self.timeline.position

        #One video, one image
        for sample in samples[1:]:
            self.insert_clip(sample)
            self.insert_clip(samples[0])

        sleep(0.3)
        end = self.search_clip_end(30, timecode_widget, self.timeline)
        cend = end / 11.139
        dogtail.rawinput.absoluteMotion(tpos[0] + cend - 2, tpos[1] + 30)
        registry.generateKeyboardEvent(dogtail.rawinput.keyNameToKeyCode("Shift_L"), None, KEY_PRESS)
        dogtail.rawinput.press(tpos[0] + cend - 2, tpos[1] + 30)
        sleep(0.5)
        dogtail.rawinput.absoluteMotion(tpos[0] + cend - 40, tpos[1] + 30)
        sleep(0.5)
        dogtail.rawinput.release(tpos[0] + cend - 40, tpos[1] + 30)
        registry.generateKeyboardEvent(dogtail.rawinput.keyNameToKeyCode("Shift_L"), None, KEY_RELEASE)
        self.goToEnd_button.click()
        self.assertNotEqual(timecode_widget.text, "00:11.139")

        #TODO: do something more with clips
