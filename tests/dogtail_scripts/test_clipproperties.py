#!/usr/bin/env python
from helper_functions import HelpFunc
from dogtail.predicate import GenericPredicate
import dogtail.rawinput
from time import sleep


class ClipTransforamtionTest(HelpFunc):
    def test_transformation_options(self):
        #Load sample
        sample = self.import_media()
        self.insert_clip(sample)

        clippos = []
        clippos.append((self.timeline.position[0] + 20, self.timeline.position[1] + 20))
        clippos.append((self.timeline.position[0] + self.timeline.size[0] / 2, self.timeline.position[1] + 20))
        dogtail.rawinput.click(clippos[0][0], clippos[0][1])

        tab = self.clipproperties
        tab.click()
        tab.child(name="Transformation", roleName="toggle button").click()
        #Just try changing values
        #Test slider
        slider = tab.child(roleName="slider")
        self.assertEqual(slider.value, 1.0)
        slider.click()
        # Clicking in the middle of the slider will set it backwards to 0.9
        self.assertNotEqual(slider.value, 1.0)

        #Test position
        spinb = tab.child(roleName="panel", name="Position").findChildren(GenericPredicate(roleName="spin button"))
        self.assertEqual(len(spinb), 2)
        spinb[0].text = "0.3"
        spinb[1].text = "0.2"

        #Test size
        spinb = tab.child(roleName="panel", name="Size").findChildren(GenericPredicate(roleName="spin button"))
        self.assertEqual(len(spinb), 2)
        spinb[0].text = "0.4"
        spinb[1].text = "0.1"

        #Test crop
        spinb = tab.child(roleName="panel", name="Crop").findChildren(GenericPredicate(roleName="spin button"))
        self.assertEqual(len(spinb), 4)
        spinb[0].text = "0.05"
        spinb[1].text = "0.12"
        spinb[2].text = "0.14"
        spinb[3].text = "0.07"

        #Click second clip, look that settings not changed(not linked)
        dogtail.rawinput.click(clippos[1][0], clippos[1][1])
        self.assertEqual(tab.child(roleName="slider").value, 1.0)

        #Click back, look if settings saved
        dogtail.rawinput.click(clippos[0][0], clippos[0][1])
        self.assertNotEqual(tab.child(roleName="slider").value, 1.0)

        self.assertNotNone(self.search_by_text("0.3", tab.child(roleName="panel", name="Position")))
        self.assertNotNone(self.search_by_text("0.2", tab.child(roleName="panel", name="Position")))

        self.assertNotNone(self.search_by_text("0.4", tab.child(roleName="panel", name="Size")))
        self.assertNotNone(self.search_by_text("0.1", tab.child(roleName="panel", name="Size")))

        self.assertNotNone(self.search_by_text("0.05", tab.child(roleName="panel", name="Crop")))
        self.assertNotNone(self.search_by_text("0.12", tab.child(roleName="panel", name="Crop")))
        self.assertNotNone(self.search_by_text("0.14", tab.child(roleName="panel", name="Crop")))
        self.assertNotNone(self.search_by_text("0.07", tab.child(roleName="panel", name="Crop")))

        #Push clear
        tab.child(roleName="scroll bar").value = 140
        tab.button("Clear")

        self.assertEqual(tab.child(roleName="slider").value, 1.0)

        self.assertNone(self.search_by_text("0.3", tab.child(roleName="panel", name="Position")))
        self.assertNone(self.search_by_text("0.2", tab.child(roleName="panel", name="Position")))

        self.assertNone(self.search_by_text("0.4", tab.child(roleName="panel", name="Size")))
        self.assertNone(self.search_by_text("0.1", tab.child(roleName="panel", name="Size")))

        self.assertNone(self.search_by_text("0.05", tab.child(roleName="panel", name="Crop")))
        self.assertNone(self.search_by_text("0.12", tab.child(roleName="panel", name="Crop")))
        self.assertNone(self.search_by_text("0.14", tab.child(roleName="panel", name="Crop")))
        self.assertNone(self.search_by_text("0.07", tab.child(roleName="panel", name="Crop")))
