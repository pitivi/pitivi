#!/usr/bin/env python
from helper_functions import HelpFunc
import dogtail.rawinput


# FIXME: cleanup the weird use of variable names for tabs here
class EffectLibraryTest(HelpFunc):
    def test_effect_library(self):
        #Load sample
        self.import_media()
        tab = self.effectslibrary
        tab.click()
        search = tab.textentry("")
        view = tab.child(roleName="table")
        combotypes = tab.child(name="All effects", roleName="combo box")
        # Some test of video effects and search. The two column headers are
        # also children and are always present, and each row has two children:
        search.text = "Crop"
        self.assertEqual(len(view.children), 2 + 2 * 3)
        combotypes.click()
        tab.menuItem("Colors").click()
        self.assertEqual(len(view.children), 2 + 2 * 0)
        combotypes.click()
        tab.menuItem("Geometry").click()
        self.assertEqual(len(view.children), 2 + 2 * 3)

        #Audio effects
        tab.child(name="Video effects", roleName="combo box").click()
        tab.menuItem("Audio effects").click()
        search.text = "Equa"
        #Titles plus 3 plugins, two collumns = 8
        self.assertEqual(len(tab.child(roleName="table").children), 8)

    def help_test_effect_drag(self):
        sample = self.import_media()
        self.insert_clip(sample)
        clippos = (self.timeline.position[0] + 20, self.timeline.position[1] + 20)

        tab = self.effectslibrary
        tab.click()
        conftab = self.clipproperties
        conftab.click()
        table = conftab.child(roleName="table")

        dogtail.rawinput.click(clippos[0], clippos[1])
        self.assertTrue(table.sensitive)
        #No effects added
        self.assertEqual(len(table.children), 3)

        center = lambda obj: (obj.position[0] + obj.size[0] / 2, obj.position[1] + obj.size[1] / 2)
        icon = self.search_by_regex("^Agingtv", tab, roleName="table cell")

        #Drag video effect on the clip
        self.improved_drag(center(icon), clippos)
        self.assertEqual(len(table.children), 6)
        #Drag video effect to the table
        icon = self.search_by_regex("^3Dflippo", tab, roleName="table cell")
        self.improved_drag(center(icon), center(table))
        self.assertEqual(len(table.children), 9)

        #Drag audio effect on the clip
        tab.child(name="Video effects", roleName="combo box").click()
        tab.menuItem("Audio effects").click()
        effect = self.search_by_regex("^Amplifier", tab, roleName="table cell")
        self.improved_drag(center(effect), clippos)
        self.assertEqual(len(table.children), 12)

        #Drag audio effect on the table
        effect = self.search_by_regex("^Audiokaraoke", tab, roleName="table cell")
        self.improved_drag(center(effect), center(table))
        self.assertEqual(len(table.children), 15)

    def test_change_effect_settings(self):
        self.help_test_effect_drag()
        self.clipproperties.child(roleName="table").child(name="audioamplify").click()
        fx_expander = self.clipproperties.child(name="Effects", roleName="toggle button")
        fx_expander.child(name="Normal clipping (default)", roleName="combo box")
        fx_expander.child(roleName="spin button").text = "2"
