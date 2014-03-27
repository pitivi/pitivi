#!/usr/bin/env python2
from common import PitiviTestCase
from dogtail.tree import SearchError
import dogtail.rawinput


class DialogsPreferencesTest(PitiviTestCase):

    def test_pref_dialog(self):
        dogtail.rawinput.pressKey("Esc")
        self.menubar.menu("Edit").click()
        self.menubar.menuItem("Preferences").click()
        dialog = self.pitivi.child(name="Preferences", roleName="dialog", recursive=False)
        dialog.child("Reset to Factory Settings", roleName="push button").click()

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
        dialog = self.pitivi.child(name="Preferences", roleName="dialog", recursive=False)

        # Check if the previous values were correctly saved
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
        self.assertEqual(dialog.child(roleName="spin button").text, "5", "Resetting to factory defaults failed")
