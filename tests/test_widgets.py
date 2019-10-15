# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2013, Alex Băluț <alexandru.balut@gmail.com>
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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
from gi.repository import Gdk
from gi.repository import Gst

from pitivi.utils.widgets import ChoiceWidget
from pitivi.utils.widgets import ColorWidget
from pitivi.utils.widgets import FontWidget
from pitivi.utils.widgets import FractionWidget
from pitivi.utils.widgets import NumericWidget
from pitivi.utils.widgets import PathWidget
from pitivi.utils.widgets import TextWidget
from pitivi.utils.widgets import ToggleWidget
from pitivi.utils.widgets import GstElementSettingsDialog
from tests import common


class TestWidgets(common.TestCase):

    def testConstruction(self):
        widgets = (
            (PathWidget, "file:///home/", ()),
            (TextWidget, "banana", ()),
            (NumericWidget, 42, (100, 1)),
            (ToggleWidget, True, ()),
            (ChoiceWidget, "banana", ((
                ("banana", "banana"),
                ("apple", "apple"),
                ("pear", "pear")),)),
            (ColorWidget, Gdk.RGBA(0.5, 0.5, 0.3, 0.8), ()),
            (FontWidget, "Sans 9", ()))

        for widget_class, default, args in widgets:
            widget = widget_class(*args, default=default)
            self.assertEqual(default, widget.getWidgetDefault())
            widget.setWidgetToDefault()
            self.assertEqual(default, widget.getWidgetValue())
            widget.setWidgetValue(default)
            self.assertEqual(default, widget.getWidgetValue())

    def testValidation(self):
        widget = TextWidget("^([a-zA-Z]+\s*)+$")
        bad_value = "1"
        self.assertNotEqual(bad_value, widget.getWidgetValue())

        widget = TextWidget("^\d+$", ("12", "14"))
        bad_value = "non-digits"
        self.assertNotEqual(bad_value, widget.getWidgetValue())


class TestFractionWidget(common.TestCase):

    def test_widget_text(self):
        widget = FractionWidget()
        widget.setWidgetValue(Gst.Fraction(1000000, 1))
        self.assertEqual(widget.text.get_text(), "1000000:1")
        widget.setWidgetValue(Gst.Fraction(7504120000000001, 4503600000000002))
        self.assertEqual(widget.text.get_text(), "7504120000000001:4503600000000002")

    def test_widget_text_magic_M(self):
        widget = FractionWidget()
        widget.setWidgetValue(Gst.Fraction(1000000000, 1001))
        self.assertEqual(widget.text.get_text(), "1000000M")


class TestGstElementSettingsDialog(common.TestCase):

    def test_reusing_properties(self):
        """Check that passing values to be used on element to be configured works."""

        dialog = GstElementSettingsDialog(Gst.ElementFactory.find("identity"), {"datarate": 12})
        v, = [v for (k, v) in dialog.elementsettings.properties.items() if k.name == "datarate"]
        self.assertEqual(v.getWidgetValue(), 12)