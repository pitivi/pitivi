# -*- coding: utf-8 -*-
#
# Copyright (c) 2013, Alexandru Băluț <alexandru.balut@gmail.com>
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

from unittest import TestCase

from pitivi.utils.widgets import PathWidget, TextWidget, NumericWidget, ToggleWidget, ChoiceWidget, ColorWidget, FontWidget


class TestWidgets(TestCase):

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
            (ColorWidget, 0x336699FF, (int,)),
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
