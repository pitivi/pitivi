#!/usr/bin/env python
from helper_functions import HelpFunc
from dogtail.tree import SearchError
import dogtail.rawinput


class DialogsPreferencesTest(HelpFunc):

    def test_pref_dialog(self):
        dogtail.rawinput.pressKey("Esc")
        self.menubar.menu("Edit").click()
        self.menubar.menuItem("Preferences").click()
        dialog = self.pitivi.get_child()(name="Preferences", roleName="dialog")
        dialog.get_child()("Reset to Factory Settings", roleName="push button").click()

        # Set a different font
        dialog.get_child()(name="Sans", roleName="label").click()
        fontchooser = self.pitivi.get_child()(name="Pick a Font", roleName="fontchooser")
        fontchooser.get_child()(name="Serif").click()
        fontchooser.get_child()(name="OK", roleName="push button").click()

        # Set the thumbnail gap setting (or whatever the first spinbutton is)
        foo = dialog.get_child()(roleName="spin button")
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
        dialog = self.pitivi.get_child()(name="Preferences", roleName="dialog")

        # Check if the previous values were correctly saved
        # In the case of the font, just search if such an item exists:
        try:
            dialog.get_child()(name="Serif", roleName="label")
        except SearchError:
            self.fail("Font was not saved")
        self.assertEqual(dialog.get_child()(roleName="spin button").text, "12")

        # Check the "revert to last user values" feature
        foo = dialog.get_child()(roleName="spin button")
        foo.click()
        foo.text = ""  # Clear the text so we can type into it
        # Finish typeText with a \n so that the "changed" signals get fired
        # Otherwise the Revert button will not be made sensitive
        foo.typeText("888\n")
        dialog.get_child()("Revert", roleName="push button").click()
        self.assertEqual(dialog.get_child()(roleName="spin button").text, "12", "Spacing setting was not reverted")

        # Check resetting to factory settings
        dialog.get_child()("Reset to Factory Settings", roleName="push button").click()
        dialog.get_child()(name="Sans", roleName="label")
        self.assertEqual(dialog.get_child()(roleName="spin button").text, "5", "Resetting to factory defaults failed")
