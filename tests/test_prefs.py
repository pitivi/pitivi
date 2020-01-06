# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2009, Brandon Lewis <brandon_lewis@berkeley.edu>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
from unittest import mock

from gi.repository import Gtk

from pitivi.dialogs.prefs import PreferencesDialog
from tests import common


class PreferencesDialogTest(common.TestCase):

    def test_dialog_creation(self):
        """Exercises the dialog creation."""
        app = common.create_pitivi()
        with mock.patch.object(Gtk.Dialog, "set_transient_for"):
            PreferencesDialog(app)

        app.project_manager.new_blank_project()
        with mock.patch.object(Gtk.Dialog, "set_transient_for"):
            PreferencesDialog(app)

    def test_numeric(self):
        PreferencesDialog.add_numeric_preference('numericPreference1',
                                                 label="Open Range",
                                                 section="timeline",
                                                 description="This option has no upper bound",
                                                 lower=-10)
        self.assertTrue(
            'numericPreference1' in PreferencesDialog.prefs["timeline"])

        PreferencesDialog.add_numeric_preference('numericPreference2',
                                                 label="Closed Range",
                                                 section="timeline",
                                                 description="This option has both upper and lower bounds",
                                                 lower=-10,
                                                 upper=10000)

    def test_text(self):
        PreferencesDialog.add_text_preference('textPreference1',
                                              label="Unfiltered",
                                              section="timeline",
                                              description="Anything can go in this box")

        PreferencesDialog.add_text_preference('textPreference2',
                                              label="Numbers only",
                                              section="timeline",
                                              description="This input validates its input with a regex",
                                              matches=r"^-?\d+(\.\d+)?$")

    def test_other(self):
        PreferencesDialog.add_path_preference('aPathPreference',
                                              label="Test Path",
                                              section="timeline",
                                              description="Test the path widget")

        PreferencesDialog.add_choice_preference('aChoicePreference',
                                                label="Swallow Velocity",
                                                section="timeline",
                                                description="What is the airspeed velocity of a coconut-laden swallow?",
                                                choices=(
                                                    ("42 Knots", 32),
                                                    ("9 furlongs per fortnight", 42),
                                                    ("I don't know that!", None)))

        PreferencesDialog.add_choice_preference('aLongChoicePreference',
                                                label="Favorite Color",
                                                section="timeline",
                                                description="What is the color of the parrot's plumage?",
                                                choices=(
                                                    ("Mauve", "Mauve"),
                                                    ("Chartreuse", "Chartreuse"),
                                                    ("Magenta", "Magenta"),
                                                    ("Pink", "Pink"),
                                                    ("Norwegian Blue", "Norwegian Blue"),
                                                    ("Yellow Ochre", "Yellow Ochre")))

        PreferencesDialog.add_toggle_preference('aTogglePreference',
                                                label="Test Toggle",
                                                section="timeline",
                                                description="Test the toggle widget")

        PreferencesDialog.add_font_preference('aFontPreference',
                                              label="Foo Font",
                                              section="timeline",
                                              description="Test the font widget")
