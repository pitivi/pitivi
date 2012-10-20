#!/usr/bin/env python
from helper_functions import HelpFunc
from dogtail.predicate import GenericPredicate
import dogtail.rawinput
from time import sleep
from pyatspi import Registry as registry
from pyatspi import (KEY_SYM, KEY_PRESS, KEY_PRESSRELEASE, KEY_RELEASE)

# These are the timecodes we expect for "tears of steel.webm", depending on
# if we insert it once in a blank timeline or twice in a blank timeline.
DURATION_OF_ONE_CLIP = "0:00:01.999"
DURATION_OF_TWO_CLIPS = "0:00:03.999"


class TimelineTest(HelpFunc):
    def setUp(self):
        super(TimelineTest, self).setUp()
        self.goToEnd_button = self.viewer.child(name="goToEnd_button")

    def insertTwoClipsAndSeekToEnd(self):
        # Just a small helper method to facilitate timeline setup
        sample = self.import_media()
        self.insert_clip(sample, 2)
        self.goToEnd_button.click()

    def test_drag_clip(self):
        sample = self.import_media()
        seektime = self.viewer.child(name="timecode_entry").child(roleName="text")
        self.assertIsNotNone(seektime)

        center = lambda obj: (obj.position[0] + obj.size[0] / 2, obj.position[1] + obj.size[1] / 2)
        self.improved_drag(center(sample), center(self.timeline))
        self.goToEnd_button.click()
        self.assertNotEqual(seektime.text, "0:00:00.000")

    def test_multiple_drag(self):
        sample = self.import_media()
        seektime = self.viewer.child(name="timecode_entry").child(roleName="text")
        timeline = self.timeline
        self.assertIsNotNone(seektime)
        oldseek = seektime.text
        center = lambda obj: (obj.position[0] + obj.size[0] / 2, obj.position[1] + obj.size[1] / 2)
        endpos = []
        endpos.append((timeline.position[0] + timeline.size[0] - 30, timeline.position[1] + 30))
        endpos.append((timeline.position[0] + timeline.size[0] - 30, timeline.position[1] + 120))
        endpos.append((timeline.position[0] + timeline.size[0] - 30, timeline.position[1] + 80))
        for i in range(20):
            if (i % 4 == 0):
                # Drag to center, next layer, out, and then back in
                self.improved_drag(center(sample), endpos[i % 3], middle=[center(timeline), endpos[(i + 1) % 2], center(sample)])
            else:
                # Simple drag
                self.improved_drag(center(sample), endpos[i % 3])
            # Give time to insert object
            sleep(0.5)
            self.goToEnd_button.click()
            self.assertNotEqual(oldseek, seektime.text)
            oldseek = seektime.text

    def test_split(self):
        self.insertTwoClipsAndSeekToEnd()
        seektime = self.viewer.child(name="timecode_entry").child(roleName="text")
        self.assertEqual(seektime.text, DURATION_OF_TWO_CLIPS)
        timeline = self.timeline
        #Adjust to different screen sizes
        adj = (float)(timeline.size[0]) / 883

        dogtail.rawinput.click(timeline.position[0] + 500 * adj, timeline.position[1] + 50)
        self.timeline_toolbar.child(name="Split", roleName="push button").click()
        dogtail.rawinput.click(timeline.position[0] + 450 * adj, timeline.position[1] + 50)
        self.timeline_toolbar.child(name="Delete", roleName="push button").click()

        self.goToEnd_button.click()
        self.assertEqual(seektime.text, DURATION_OF_TWO_CLIPS)

        dogtail.rawinput.click(timeline.position[0] + 550 * adj, timeline.position[1] + 50)
        dogtail.rawinput.pressKey("Del")
        #self.timeline_toolbar.child(name="Delete", roleName="push button").click()

        self.goToEnd_button.click()
        self.assertEqual(seektime.text, DURATION_OF_ONE_CLIP)

    def test_multiple_split(self):
        self.insertTwoClipsAndSeekToEnd()
        seektime = self.viewer.child(name="timecode_entry").child(roleName="text")
        self.assertEqual(seektime.text, DURATION_OF_TWO_CLIPS)
        #Adjust to different screen sizes
        adj = (float)(self.timeline.size[0]) / 883
        tpos = self.timeline.position
        pos = [50, 480, 170, 240, 350, 610, 410, 510]
        #Sleeps needed for atspi
        for k in pos:
            for p in pos:
                dogtail.rawinput.click(tpos[0] + (p + k / 10) * adj, tpos[1] + 50)
                sleep(0.1)
                dogtail.rawinput.pressKey("s")
                #Just search some object to look if it still alive
                self.pitivi.child(roleName="icon")

    def test_transition(self):
        self.insertTwoClipsAndSeekToEnd()
        seektime = self.viewer.child(name="timecode_entry").child(roleName="text")
        self.assertEqual(seektime.text, DURATION_OF_TWO_CLIPS)
        tpos = self.timeline.position

        #Adjust to different screen sizes
        adj = (float)(self.timeline.size[0]) / 883

        dogtail.rawinput.press(tpos[0] + 500 * adj, tpos[1] + 50)
        #Drag in, drag out, drag in and release
        dogtail.rawinput.relativeMotion(-200 * adj, 10)
        sleep(1)
        dogtail.rawinput.relativeMotion(300 * adj, -10)
        sleep(1)
        dogtail.rawinput.absoluteMotion(tpos[0] + 300 * adj, tpos[1] + 50)
        sleep(1)
        dogtail.rawinput.release(tpos[0] + 300 * adj, tpos[1] + 50)
        sleep(1)
        dogtail.rawinput.click(tpos[0] + 250 * adj, tpos[1] + 50)
        #Check if we selected transition
        iconlist = self.transitions.child(roleName="layered pane")
        self.assertTrue(iconlist.sensitive)
        iconlist.children[-2].select()
        self.assertTrue(self.transitions.child(roleName="slider").sensitive)
        self.transitions.child(roleName="slider").value = 50

    def search_clip_end(self, y, seek, timeline):
        minx = timeline.position[0] + 10.
        maxx = timeline.position[0] + timeline.size[0] - 10.
        minx = (minx + maxx) / 2
        y += timeline.position[1]
        dogtail.rawinput.click(maxx, y)
        maxseek = seek.text
        print maxseek
        while maxx - minx > 2:
            middle = (maxx + minx) / 2
            dogtail.rawinput.click(middle, y)
            sleep(0.1)
            if seek.text == maxseek:
                maxx = middle
            else:
                minx = middle
        #+5 due to handle size
        return maxx - timeline.position[0] + 5

    def test_riple_roll(self):
        self.insertTwoClipsAndSeekToEnd()
        seektime = self.viewer.child(name="timecode_entry").child(roleName="text")
        self.assertEqual(seektime.text, DURATION_OF_TWO_CLIPS)
        tpos = self.timeline.position
        end = self.search_clip_end(30, seektime, self.timeline)

        dogtail.rawinput.absoluteMotion(tpos[0] + end / 2 - 2, tpos[1] + 30)
        registry.generateKeyboardEvent(dogtail.rawinput.keyNameToKeyCode("Control_L"), None, KEY_PRESS)
        dogtail.rawinput.press(tpos[0] + end / 2 - 2, tpos[1] + 30)
        sleep(0.5)
        dogtail.rawinput.absoluteMotion(tpos[0] + end / 2 - 100, tpos[1] + 30)
        sleep(0.5)
        dogtail.rawinput.release(tpos[0] + end / 2 - 100, tpos[1] + 30)
        registry.generateKeyboardEvent(dogtail.rawinput.keyNameToKeyCode("Control_L"), None, KEY_RELEASE)
        self.goToEnd_button.click()
        self.assertNotEqual(seektime.text, DURATION_OF_TWO_CLIPS, "Not rippled, but trimmed")

        #Regresion test of adding effect
        #Add effect
        self.effectslibrary.click()
        self.clipproperties.click()
        center = lambda obj: (obj.position[0] + obj.size[0] / 2, obj.position[1] + obj.size[1] / 2)
        table = self.clipproperties.child(roleName="table")
        effect_from_library = self.search_by_text("Agingtv", self.effectslibrary, roleName="table cell", exactMatchOnly=False)
        self.improved_drag(center(effect_from_library), center(table))
        self.goToEnd_button.click()
        seekbefore = seektime.text
        #Try riple and roll
        dogtail.rawinput.absoluteMotion(tpos[0] + end / 2 - 102, tpos[1] + 30)
        registry.generateKeyboardEvent(dogtail.rawinput.keyNameToKeyCode("Control_L"), None, KEY_PRESS)
        dogtail.rawinput.press(tpos[0] + end / 2 - 102, tpos[1] + 30)
        sleep(0.5)
        dogtail.rawinput.absoluteMotion(tpos[0] + end / 2 - 200, tpos[1] + 30)
        sleep(0.5)
        dogtail.rawinput.release(tpos[0] + end / 2 - 200, tpos[1] + 30)
        registry.generateKeyboardEvent(dogtail.rawinput.keyNameToKeyCode("Control_L"), None, KEY_RELEASE)
        self.goToEnd_button.click()
        self.assertNotEqual(seektime.text, seekbefore, "Not ripled affter adding effect")

    def test_image_video_mix(self):
        files = ["tears of steel.webm", "flat_colour2_640x480.png",
                 "flat_colour4_1600x1200.jpg", "flat_colour1_640x480.png",
                 "flat_colour3_320x180.png", "flat_colour5_1600x1200.jpg"]
        samples = self.import_media_multiple(files)
        seektime = self.viewer.child(name="timecode_entry").child(roleName="text")
        tpos = self.timeline.position

        #One video, one image
        for sample in samples[1:]:
            self.insert_clip(sample)
            self.insert_clip(samples[0])

        end = self.search_clip_end(30, seektime, self.timeline)
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
        self.assertNotEqual(seektime.text, "0:00:11.139")

        #TODO: do something more with clips
