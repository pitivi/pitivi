#!/usr/bin/env python
from test_help_func import HelpFunc
from helper_functions import improved_drag
import dogtail.rawinput


class EffectLibraryTest(HelpFunc):
    def test_effect_library(self):
        #Load sample
        self.import_media()
        tab = self.pitivi.tab("Effect Library")
        tab.click()
        search = tab.textentry("")
        iconview = tab.child(roleName="layered pane")
        combotypes = tab.child(name="All effects", roleName="combo box")
        #Some test of video effects and search
        search.text = "Crop"
        self.assertEqual(len(iconview.children), 3)
        combotypes.click()
        tab.menuItem("Colors").click()
        self.assertEqual(len(iconview.children), 0)
        combotypes.click()
        tab.menuItem("Geometry").click()
        self.assertEqual(len(iconview.children), 3)

        #Audio effects
        tab.child(name="Video effects", roleName="combo box").click()
        tab.menuItem("Audio effects").click()
        search.text = "Equa"
        #Titles plus 3 plugins, two collumns = 8
        self.assertEqual(len(tab.child(roleName="table").children), 8)

    def help_test_effect_drag(self):
        sample = self.import_media()
        self.insert_clip(sample)
        timeline = self.get_timeline()
        clippos = (timeline.position[0] + 20, timeline.position[1] + 20)

        tab = self.pitivi.tab("Effect Library")
        tab.click()
        conftab = self.pitivi.tab("Clip configuration")
        conftab.click()
        table = conftab.child(roleName="table")

        dogtail.rawinput.click(clippos[0], clippos[1])
        self.assertTrue(table.sensitive)
        #No effects added
        self.assertEqual(len(table.children), 3)

        center = lambda obj: (obj.position[0] + obj.size[0] / 2, obj.position[1] + obj.size[1] / 2)
        icon = self.search_by_text("Agingtv ", tab, roleName="icon")

        #Drag video effect on the clip
        improved_drag(center(icon), clippos)
        self.assertEqual(len(table.children), 6)
        #Drag video effect to the table
        icon = self.search_by_text("3Dflippo", tab, roleName="icon")
        improved_drag(center(icon), center(table))
        self.assertEqual(len(table.children), 9)

        #Drag audio effect on the clip
        tab.child(name="Video effects", roleName="combo box").click()
        tab.menuItem("Audio effects").click()
        effect = tab.child(name="Amplifier")
        improved_drag(center(effect), clippos)
        self.assertEqual(len(table.children), 12)

        #Drag audio effect on the table
        effect = tab.child(name="Audiokaraoke")
        improved_drag(center(effect), center(table))
        self.assertEqual(len(table.children), 15)

    def test_change_effect_settings(self):
        self.help_test_effect_drag()
        conftab = self.pitivi.tab("Clip configuration")
        conftab.child(roleName="table").child(name="audioamplify").click()
        eftab = conftab.child(name="Effects", roleName="toggle button")
        eftab.child(name="Normal clipping (default)", roleName="combo box")
        eftab.child(roleName="spin button").text = "2"
