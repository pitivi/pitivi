#!/usr/bin/env python
from test_help_func import HelpFunc
from dogtail.predicate import GenericPredicate
from helper_functions import improved_drag
import dogtail.rawinput
from time import sleep
from pyatspi import Registry as registry
from pyatspi import (KEY_SYM, KEY_PRESS, KEY_PRESSRELEASE, KEY_RELEASE)


class TimelineTest(HelpFunc):
    def setUp(self):
        super(TimelineTest, self).setUp()
        self.nextb = self.pitivi.child(name="Next", roleName="push button")

    def help_test_insertEnd(self):
        sample = self.import_media()
        #Right click
        seektime = self.search_by_text("0:00:00.000", self.pitivi, roleName="text")

        self.assertIsNotNone(seektime)

        sample.click(3)
        buttons = self.pitivi.findChildren(
            GenericPredicate(name="Insert at End of Timeline"))
        buttons[1].click()
        self.nextb.click()
        self.assertEqual(seektime.text, "0:00:01.227")

        #Add one more
        sample.click(3)
        buttons = self.pitivi.findChildren(
            GenericPredicate(name="Insert at End of Timeline"))
        buttons[1].click()
        self.nextb.click()

        self.assertEqual(seektime.text, "0:00:02.455")

    def help_test_insertEndFast(self):
        sample = self.import_media()
        self.insert_clip(sample, 2)
        self.nextb.click()

    def test_drag_clip(self):
        sample = self.import_media()
        seektime = self.search_by_text("0:00:00.000", self.pitivi, roleName="text")
        self.assertIsNotNone(seektime)

        timeline = self.get_timeline()

        center = lambda obj: (obj.position[0] + obj.size[0] / 2, obj.position[1] + obj.size[1] / 2)
        improved_drag(center(sample), center(timeline))
        self.nextb.click()
        self.assertNotEqual(seektime.text, "0:00:00.000")

    def test_multiple_drag(self):
        sample = self.import_media()
        seektime = self.search_by_text("0:00:00.000", self.pitivi, roleName="text")
        timeline = self.get_timeline()
        self.assertIsNotNone(seektime)
        oldseek = seektime.text
        center = lambda obj: (obj.position[0] + obj.size[0] / 2, obj.position[1] + obj.size[1] / 2)
        endpos = []
        endpos.append((timeline.position[0] + timeline.size[0] - 30, timeline.position[1] + 30))
        endpos.append((timeline.position[0] + timeline.size[0] - 30, timeline.position[1] + 120))
        endpos.append((timeline.position[0] + timeline.size[0] - 30, timeline.position[1] + 80))
        for i in range(20):
            if (i % 4 == 0):
                #Drag to center, next layer, out, and then back in
                improved_drag(center(sample), endpos[i % 3], middle=[center(timeline), endpos[(i + 1) % 2], center(sample)])
            else:
                #Simple drag
                improved_drag(center(sample), endpos[i % 3])
            #Give time to insert object
            sleep(0.5)
            self.nextb.click()
            self.assertNotEqual(oldseek, seektime.text)
            oldseek = seektime.text

    def test_split(self):
        self.help_test_insertEnd()
        seektime = self.search_by_text("0:00:02.455", self.pitivi, roleName="text")
        timeline = self.get_timeline()
        #Adjust to different screen sizes
        adj = (float)(timeline.size[0]) / 883

        dogtail.rawinput.click(timeline.position[0] + 500 * adj, timeline.position[1] + 50)
        self.pitivi.child(name="Split", roleName="push button").click()
        dogtail.rawinput.click(timeline.position[0] + 450 * adj, timeline.position[1] + 50)
        self.pitivi.child(name="Delete", roleName="push button").click()

        self.nextb.click()
        self.assertEqual(seektime.text, "0:00:02.455")

        dogtail.rawinput.click(timeline.position[0] + 550 * adj, timeline.position[1] + 50)
        dogtail.rawinput.pressKey("Del")
        #self.pitivi.child(name="Delete", roleName="push button").click()

        self.nextb.click()
        self.assertEqual(seektime.text, "0:00:01.227")

    def test_multiple_split(self):
        self.help_test_insertEndFast()
        seektime = self.search_by_text("0:00:02.455", self.pitivi, roleName="text")
        timeline = self.get_timeline()
        #Adjust to different screen sizes
        adj = (float)(timeline.size[0]) / 883
        tpos = timeline.position
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
        self.help_test_insertEndFast()
        seektime = self.search_by_text("0:00:02.455", self.pitivi, roleName="text")
        timeline = self.get_timeline()
        tpos = timeline.position

        #Adjust to different screen sizes
        adj = (float)(timeline.size[0]) / 883

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
        transitions = self.pitivi.child(name="Transitions", roleName="page tab")
        iconlist = transitions.child(roleName="layered pane")
        self.assertTrue(iconlist.sensitive)
        iconlist.children[-2].select()
        self.assertTrue(transitions.child(roleName="slider").sensitive)
        transitions.child(roleName="slider").value = 50

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
        self.help_test_insertEndFast()
        seektime = self.search_by_text("0:00:02.455", self.pitivi, roleName="text")
        timeline = self.get_timeline()
        tpos = timeline.position
        end = self.search_clip_end(30, seektime, timeline)

        dogtail.rawinput.absoluteMotion(tpos[0] + end / 2 - 2, tpos[1] + 30)
        registry.generateKeyboardEvent(dogtail.rawinput.keyNameToKeyCode("Control_L"), None, KEY_PRESS)
        dogtail.rawinput.press(tpos[0] + end / 2 - 2, tpos[1] + 30)
        sleep(0.5)
        dogtail.rawinput.absoluteMotion(tpos[0] + end / 2 - 100, tpos[1] + 30)
        sleep(0.5)
        dogtail.rawinput.release(tpos[0] + end / 2 - 100, tpos[1] + 30)
        registry.generateKeyboardEvent(dogtail.rawinput.keyNameToKeyCode("Control_L"), None, KEY_RELEASE)
        self.nextb.click()
        self.assertNotEqual(seektime.text, "0:00:02.455", "Not ripled, but trimed")

        #Regresion test of adding effect
        #Add effect
        tab = self.pitivi.tab("Effect Library")
        tab.click()
        conftab = self.pitivi.tab("Clip configuration")
        conftab.click()
        center = lambda obj: (obj.position[0] + obj.size[0] / 2, obj.position[1] + obj.size[1] / 2)
        table = conftab.child(roleName="table")
        icon = self.search_by_text("Agingtv ", tab, roleName="icon")
        improved_drag(center(icon), center(table))
        self.nextb.click()
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
        self.nextb.click()
        self.assertNotEqual(seektime.text, seekbefore, "Not ripled affter adding effect")

    def test_image_video_mix(self):
        files = ["1sec_simpsons_trailer.mp4", "flat_colour2_640x480.png",
                 "flat_colour4_1600x1200.jpg", "flat_colour1_640x480.png",
                 "flat_colour3_320x180.png", "flat_colour5_1600x1200.jpg"]
        samples = self.import_media_multiple(files)
        seektime = self.search_by_text("0:00:00.000", self.pitivi, roleName="text")
        timeline = self.get_timeline()
        tpos = timeline.position

        #One video, one image
        for sample in samples[1:]:
            self.insert_clip(sample)
            self.insert_clip(samples[0])

        end = self.search_clip_end(30, seektime, timeline)
        cend = end / 11.139
        dogtail.rawinput.absoluteMotion(tpos[0] + cend - 2, tpos[1] + 30)
        registry.generateKeyboardEvent(dogtail.rawinput.keyNameToKeyCode("Shift_L"), None, KEY_PRESS)
        dogtail.rawinput.press(tpos[0] + cend - 2, tpos[1] + 30)
        sleep(0.5)
        dogtail.rawinput.absoluteMotion(tpos[0] + cend - 40, tpos[1] + 30)
        sleep(0.5)
        dogtail.rawinput.release(tpos[0] + cend - 40, tpos[1] + 30)
        registry.generateKeyboardEvent(dogtail.rawinput.keyNameToKeyCode("Shift_L"), None, KEY_RELEASE)
        self.nextb.click()
        self.assertNotEqual(seektime.text, "0:00:11.139")

        #TODO: do something more with clips
