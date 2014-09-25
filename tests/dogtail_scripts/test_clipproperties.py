#!/usr/bin/env python2
from common import PitiviTestCase
from dogtail.predicate import GenericPredicate
import dogtail.rawinput
from time import sleep


class ClipTransformationTest(PitiviTestCase):

    def test_transformation_options(self):
        # Load a sample file, insert it twice in the timeline and wait for
        # the insertion animation to be complete before we start clicking
        sample = self.import_media()
        self.insert_clip(sample)
        self.insert_clip(sample)
        sleep(0.5)

        # Assume that the layer controls are roughly 260 pixels wide,
        # so the first clip position should be x + 300, y + 30
        _layer1_clips_y = self.timeline.position[1] + 30
        clip1_pos = (self.timeline.position[0] + 300, _layer1_clips_y)
        # The second clip position should be right in the middle of the timeline
        # but we compensate (approximately) for the width of layer controls:
        _middle_x = self.timeline.position[
            0] + 300 + (self.timeline.size[0] - 300) / 2
        clip2_pos = (_middle_x, _layer1_clips_y)
        # For now, only select the first clip on the timeline
        dogtail.rawinput.click(clip1_pos[0], clip1_pos[1])

        tab = self.clipproperties
        tab.click()
        tab.child(name="Transformation", roleName="toggle button").click()
        # Just try changing values
        # Test slider
        slider = tab.child(roleName="slider")
        self.assertEqual(slider.value, 1.0)
        slider.click()
        # Clicking in the middle of the slider will set it backwards to 0.9
        self.assertNotEqual(slider.value, 1.0)

        # Test position
        spinb = tab.child(roleName="panel", name="Position").findChildren(
            GenericPredicate(roleName="spin button"))
        self.assertEqual(len(spinb), 2)
        spinb[0].text = "0.3"
        spinb[1].text = "0.2"

        # Test size
        spinb = tab.child(roleName="panel", name="Size").findChildren(
            GenericPredicate(roleName="spin button"))
        self.assertEqual(len(spinb), 2)
        spinb[0].text = "0.4"
        spinb[1].text = "0.1"

        # Test crop
        spinb = tab.child(roleName="panel", name="Crop").findChildren(
            GenericPredicate(roleName="spin button"))
        self.assertEqual(len(spinb), 4)
        spinb[0].text = "0.05"
        spinb[1].text = "0.12"
        spinb[2].text = "0.14"
        spinb[3].text = "0.07"

        # Click second clip, check that settings have not changed (not linked)
        dogtail.rawinput.click(clip2_pos[0], clip2_pos[1])
        self.assertEqual(tab.child(roleName="slider").value, 1.0)

        # Click back onto the 1st clip, check that settings were saved
        dogtail.rawinput.click(clip1_pos[0], clip1_pos[1])
        self.assertNotEqual(tab.child(roleName="slider").value, 1.0)

        self.assertNotNone(
            self.search_by_text("0.3", tab.child(roleName="panel", name="Position")))
        self.assertNotNone(self.search_by_text(
            "0.2", tab.child(roleName="panel", name="Position")))

        self.assertNotNone(
            self.search_by_text("0.4", tab.child(roleName="panel", name="Size")))
        self.assertNotNone(
            self.search_by_text("0.1", tab.child(roleName="panel", name="Size")))

        self.assertNotNone(self.search_by_text(
            "0.05", tab.child(roleName="panel", name="Crop")))
        self.assertNotNone(self.search_by_text(
            "0.12", tab.child(roleName="panel", name="Crop")))
        self.assertNotNone(
            self.search_by_text("0.14", tab.child(roleName="panel", name="Crop")))
        self.assertNotNone(self.search_by_text(
            "0.07", tab.child(roleName="panel", name="Crop")))

        # Push clear
        tab.child(roleName="scroll bar").value = 140
        tab.button("Clear")

        self.assertEqual(tab.child(roleName="slider").value, 1.0)

        self.assertNone(self.search_by_text(
            "0.3", tab.child(roleName="panel", name="Position")))
        self.assertNone(self.search_by_text(
            "0.2", tab.child(roleName="panel", name="Position")))

        self.assertNone(self.search_by_text(
            "0.4", tab.child(roleName="panel", name="Size")))
        self.assertNone(self.search_by_text(
            "0.1", tab.child(roleName="panel", name="Size")))

        self.assertNone(
            self.search_by_text("0.05", tab.child(roleName="panel", name="Crop")))
        self.assertNone(self.search_by_text(
            "0.12", tab.child(roleName="panel", name="Crop")))
        self.assertNone(
            self.search_by_text("0.14", tab.child(roleName="panel", name="Crop")))
        self.assertNone(self.search_by_text(
            "0.07", tab.child(roleName="panel", name="Crop")))
