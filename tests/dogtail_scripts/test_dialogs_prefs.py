#!/usr/bin/env python
from helper_functions import HelpFunc
from dogtail.tree import SearchError
import dogtail.rawinput


class DialogsPreferencesTest(HelpFunc):

    def test_pref_dialog(self):
        dogtail.rawinput.pressKey("Esc")
        self.menubar.menu("Edit").click()
        self.menubar.menuItem("Preferences").click()
        dialog = self.pitivi.child(name="Preferences", roleName="dialog")
        dialog.child("Reset to Factory Settings", roleName="push button").click()

        # Set a different font
        dialog.child(name="Sans", roleName="push button").click()
        fontchooser = self.pitivi.child(name="Pick a Font", roleName="dialog")
        # Perf hack: do a search to reduce the amount of table cells displayed,
        # otherwise dogtail will take ages to search for it.
        # But even if the search entry is focused by default, you can't do
        # dogtail.rawinput.typeText("cantarell bold")
        # Because it types randomized letters (in dogtail 0.8.1).
        # So here's a positional hack:
        search_entry = fontchooser.children[0].children[0].children[0].children[4]
        # Search for a very specific font, to avoid scrolling, which would
        # make it impossible to click the first item in the search results
        search_entry.text = "cantarell bold"
        # Ideally I'd search the child table cells, but this is way too slow,
        # so let's just pick the first item in the search results:
        fontchooser.child(roleName="table cell").click()
        fontchooser.child(name="Select", roleName="push button").click()

        # Set the thumbnail gap setting (or whatever the first spinbutton is)
        foo = dialog.child(roleName="spin button")
        # The following is quite silly. You *need* to focus the widget
        # before changing its text, otherwise GTK won't fire "changed" signals
        # when you click somewhere else (ex: the Close button) and it won't be
        # saved. Since grabFocus() doesn't work here, just click it.
        foo.click()
        foo.text = "12"

        # Close the preferences, restart the app...
        dialog.button("Close").click()
        self.tearDown(kill=False)  # Pitivi only saves prefs on a normal exit
        self.setUp()
        dogtail.rawinput.pressKey("Esc")
        self.menubar.menu("Edit").click()
        self.menubar.menuItem("Preferences").click()
        dialog = self.pitivi.child(name="Preferences", roleName="dialog")

        # Check if the previous values were correctly saved
        # In the case of the font, just search if such an item exists:
        try:
            dialog.child(name="Cantarell Bold", roleName="push button")
        except SearchError:
            self.fail("Font was not saved")
        self.assertEqual(dialog.child(roleName="spin button").text, "12")

        # Check the "revert to last user values" feature
        foo = dialog.child(roleName="spin button")
        foo.click()
        foo.text = ""  # Clear the text so we can type into it
        # Finish typeText with a \n so that the "changed" signals get fired
        # Otherwise the Revert button will not be made sensitive
        foo.typeText("888\n")
        dialog.child("Revert", roleName="push button").click()
        self.assertEqual(dialog.child(roleName="spin button").text, "12", "Spacing setting was not reverted")

        # Check resetting to factory settings
        dialog.child("Reset to Factory Settings", roleName="push button").click()
        dialog.child(name="Sans", roleName="push button")
        self.assertEqual(dialog.child(roleName="spin button").text, "5", "Resetting to factory defaults failed")
