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

        timeline = self.get_timeline()
        clippos = []
        clippos.append((timeline.position[0] + 20, timeline.position[1] + 20))
        clippos.append((timeline.position[0] + timeline.size[0] / 2, timeline.position[1] + 20))
        dogtail.rawinput.click(clippos[0][0], clippos[0][1])

        conftab = self.pitivi.tab("Clip configuration")
        conftab.click()
        conftab.get_child()(name="Transformation", roleName="toggle button").click()
        #Just try changing values
        #Test slider
        slider = conftab.get_child()(roleName="slider")
        self.assertEqual(slider.value, 1.0)
        slider.click()
        # Clicking in the middle of the slider will set it backwards to 0.9
        self.assertNotEqual(slider.value, 1.0)

        #Test position
        spinb = conftab.get_child()(roleName="panel", name="Position").findChildren(GenericPredicate(roleName="spin button"))
        self.assertEqual(len(spinb), 2)
        spinb[0].text = "0.3"
        spinb[1].text = "0.2"

        #Test size
        spinb = conftab.get_child()(roleName="panel", name="Size").findChildren(GenericPredicate(roleName="spin button"))
        self.assertEqual(len(spinb), 2)
        spinb[0].text = "0.4"
        spinb[1].text = "0.1"

        #Test crop
        spinb = conftab.get_child()(roleName="panel", name="Crop").findChildren(GenericPredicate(roleName="spin button"))
        self.assertEqual(len(spinb), 4)
        spinb[0].text = "0.05"
        spinb[1].text = "0.12"
        spinb[2].text = "0.14"
        spinb[3].text = "0.07"

        #Click second clip, look that settings not changed(not linked)
        dogtail.rawinput.click(clippos[1][0], clippos[1][1])
        self.assertEqual(conftab.get_child()(roleName="slider").value, 1.0)

        #Click back, look if settings saved
        dogtail.rawinput.click(clippos[0][0], clippos[0][1])
        self.assertNotEqual(conftab.get_child()(roleName="slider").value, 1.0)

        self.assertNotNone(self.search_by_text("0.3", conftab.get_child()(roleName="panel", name="Position")))
        self.assertNotNone(self.search_by_text("0.2", conftab.get_child()(roleName="panel", name="Position")))

        self.assertNotNone(self.search_by_text("0.4", conftab.get_child()(roleName="panel", name="Size")))
        self.assertNotNone(self.search_by_text("0.1", conftab.get_child()(roleName="panel", name="Size")))

        self.assertNotNone(self.search_by_text("0.05", conftab.get_child()(roleName="panel", name="Crop")))
        self.assertNotNone(self.search_by_text("0.12", conftab.get_child()(roleName="panel", name="Crop")))
        self.assertNotNone(self.search_by_text("0.14", conftab.get_child()(roleName="panel", name="Crop")))
        self.assertNotNone(self.search_by_text("0.07", conftab.get_child()(roleName="panel", name="Crop")))

        #Push clear
        conftab.get_child()(roleName="scroll bar").value = 140
        conftab.button("Clear")

        self.assertEqual(conftab.get_child()(roleName="slider").value, 1.0)

        self.assertNone(self.search_by_text("0.3", conftab.get_child()(roleName="panel", name="Position")))
        self.assertNone(self.search_by_text("0.2", conftab.get_child()(roleName="panel", name="Position")))

        self.assertNone(self.search_by_text("0.4", conftab.get_child()(roleName="panel", name="Size")))
        self.assertNone(self.search_by_text("0.1", conftab.get_child()(roleName="panel", name="Size")))

        self.assertNone(self.search_by_text("0.05", conftab.get_child()(roleName="panel", name="Crop")))
        self.assertNone(self.search_by_text("0.12", conftab.get_child()(roleName="panel", name="Crop")))
        self.assertNone(self.search_by_text("0.14", conftab.get_child()(roleName="panel", name="Crop")))
        self.assertNone(self.search_by_text("0.07", conftab.get_child()(roleName="panel", name="Crop")))
