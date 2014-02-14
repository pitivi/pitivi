#!/usr/bin/env python2
from helper_functions import HelpFunc
import dogtail.rawinput


# FIXME: cleanup the weird use of variable names for tabs here
class EffectLibraryTest(HelpFunc):
    def test_effect_library(self):
        self.import_media()
        tab = self.effectslibrary
        tab.click()
        search = tab.child(name="effects library search entry")
        view = tab.child(roleName="table")
        combotypes = tab.child(name="effect category combobox", roleName="combo box")
        # Some test of video effects and search. The two column headers are
        # also children and are always present, and each row has two children:
        search.text = "Crop"
        self.assertEqual(len(view.children), 2 + 2 * 3)
        combotypes.click()
        combotypes.menuItem("Colors").click()
        self.assertEqual(len(view.children), 2 + 2 * 0)
        combotypes.click()
        combotypes.menuItem("Geometry").click()
        self.assertEqual(len(view.children), 2 + 2 * 3)

        # Switch to audio effects view
        tab.child(name="effects library audio togglebutton").click()
        search.text = "Equa"
        # The effects library listview doesn't show the header row, but
        # it is still one of the children. So when we're looking for the 3
        # rows matching "Equa", we need to add one child (1 header + 3 rows).
        self.assertEqual(len(tab.child(roleName="table").children), 4)

    def help_test_effect_drag(self):
        self.force_medialibrary_iconview_mode()

        sample = self.import_media()
        self.insert_clip(sample)
        # Assume that the layer controls are roughly 260 pixels wide,
        # so the clip position should be x + 300, y + 30
        clippos = (self.timeline.position[0] + 300, self.timeline.position[1] + 30)

        tab = self.effectslibrary
        tab.click()
        conftab = self.clipproperties
        conftab.click()
        clip_effects_table = conftab.child(roleName="table")

        dogtail.rawinput.click(clippos[0], clippos[1])
        self.assertTrue(clip_effects_table.sensitive)
        # No effects added. The listview has 3 columns, so it starts at 3.
        # Each time you add an effect, it adds a row, so +3 children.
        self.assertEqual(len(clip_effects_table.children), 3)

        icon = self.search_by_regex("^Agingtv", tab, roleName="table cell")

        #Drag video effect on the clip
        self.improved_drag(self.center(icon), clippos)
        self.assertEqual(len(clip_effects_table.children), 6)
        #Drag video effect to the table
        icon = self.search_by_regex("^3Dflippo", tab, roleName="table cell")
        self.improved_drag(self.center(icon), self.center(clip_effects_table))
        self.assertEqual(len(clip_effects_table.children), 9)

        #Drag audio effect on the clip
        tab.child(name="effects library audio togglebutton").click()
        effect = self.search_by_regex("^Amplifier", tab, roleName="table cell")
        self.improved_drag(self.center(effect), clippos)
        self.assertEqual(len(clip_effects_table.children), 12)

        #Drag audio effect on the table
        effect = self.search_by_regex("^Audiokaraoke", tab, roleName="table cell")
        self.improved_drag(self.center(effect), self.center(clip_effects_table))
        self.assertEqual(len(clip_effects_table.children), 15)

    def test_change_effect_settings(self):
        self.help_test_effect_drag()
        self.clipproperties.child(roleName="table").child(name="audioamplify").click()
        fx_expander = self.clipproperties.child(name="Effects", roleName="toggle button")
        fx_expander.child(name="Normal clipping (default)", roleName="combo box")
        fx_expander.child(roleName="spin button").text = "2"
