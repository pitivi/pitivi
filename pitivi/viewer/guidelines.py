# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2020, Jaden Goter <jadengoter@huskers.unl.edu>
# Copyright (c) 2020, Jessie Guo <jessie.guo@huskers.unl.edu>
# Copyright (c) 2020, Daniel Rudebusch <daniel.rudebusch@huskers.unl.edu>
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
from enum import Enum
from gettext import gettext as _

from gi.repository import Gtk

from pitivi.utils.misc import round05
from pitivi.utils.ui import SPACING


class Guideline(Enum):
    """Guideline types."""

    @staticmethod
    def __three_by_three_draw_func(cr, width, height):
        for i in range(1, 3):
            x = round05(i * width / 3)
            cr.move_to(x, 0)
            cr.line_to(x, height)

            y = round05(i * height / 3)
            cr.move_to(0, y)
            cr.line_to(width, y)

    @staticmethod
    def __vertical_horizontal_center_draw_func(cr, width, height):
        x = round05(width / 2)
        cr.move_to(x, 0)
        cr.line_to(x, height)

        y = round05(height / 2)
        cr.move_to(0, y)
        cr.line_to(width, y)

    @staticmethod
    def __diagonals_draw_func(cr, width, height):
        cr.move_to(0, 0)
        cr.line_to(width, height)
        cr.move_to(width, 0)
        cr.line_to(0, height)

    THREE_BY_THREE = (_("3 by 3"), __three_by_three_draw_func)
    VERTICAL_HORIZONTAL_CENTER = (_("Vertical/Horizontal"), __vertical_horizontal_center_draw_func)
    DIAGONALS = (_("Diagonals"), __diagonals_draw_func)

    def __init__(self, label, func):
        self.label = label
        self.draw_func = func.__func__


class GuidelinesPopover(Gtk.Popover):
    """A popover for controlling the visible composition guidelines.

    Attributes:
        overlay (GuidelinesOverlay): The managed overlay showing the guidelines.
        switches (dict): Maps the Guideline types to Gtk.Switch widgets.
    """

    def __init__(self):
        Gtk.Popover.__init__(self)

        self.switches = {}

        self.overlay = GuidelinesOverlay()
        self._create_ui()

        self._last_guidelines = {Guideline.THREE_BY_THREE}

    def _create_ui(self):
        grid = Gtk.Grid()
        grid.props.row_spacing = SPACING
        grid.props.column_spacing = SPACING
        grid.props.margin = SPACING * 2

        label = Gtk.Label(_("Composition Guidelines"))
        label.props.wrap = True
        grid.attach(label, 0, 0, 2, 1)

        grid.attach(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), 0, 1, 2, 1)

        row = 1
        for guideline in Guideline:
            row += 1

            label = Gtk.Label(guideline.label)
            label.props.halign = Gtk.Align.START
            label.props.wrap = True
            label.props.xalign = 0
            grid.attach(label, 0, row, 1, 1)

            switch = Gtk.Switch()
            switch.connect("state-set", self.__guideline_switch_state_set_cb, guideline)
            grid.attach(switch, 1, row, 1, 1)

            self.switches[guideline] = switch

        grid.show_all()
        self.add(grid)

    def toggle(self):
        """Toggle the visible guidelines on the managed overlay."""
        # Keep a copy and restore it since the last active guidelines
        # can be changed when the switches are toggled.
        last_guidelines_copy = self._last_guidelines.copy()
        try:
            for guideline in last_guidelines_copy:
                switch = self.switches[guideline]
                switch.set_active(not switch.get_active())
        finally:
            self._last_guidelines = last_guidelines_copy

    def __guideline_switch_state_set_cb(self, switch_widget, unused_parameter, guideline):
        last_guidelines = {guideline
                           for guideline in Guideline
                           if self.switches[guideline].get_active()}
        if last_guidelines:
            self._last_guidelines = last_guidelines
        if switch_widget.get_active():
            self.overlay.add_guideline(guideline)
        else:
            self.overlay.remove_guideline(guideline)


class GuidelinesOverlay(Gtk.DrawingArea):
    """Overlay which draws the composition guidelines.

    Attributes:
        active_guidelines (set[Guideline]): The guidelines to be drawn.
    """

    def __init__(self):
        Gtk.DrawingArea.__init__(self)

        self.active_guidelines = set()

        self.hide()
        self.props.no_show_all = True

    def add_guideline(self, guideline):
        if guideline not in self.active_guidelines:
            if not self.active_guidelines:
                self.set_visible(True)
            self.active_guidelines.add(guideline)
            self.queue_draw()

    def remove_guideline(self, guideline):
        if guideline in self.active_guidelines:
            self.active_guidelines.remove(guideline)
            if not self.active_guidelines:
                self.set_visible(False)
            self.queue_draw()

    def do_draw(self, cr):
        width = self.get_allocated_width()
        height = self.get_allocated_height()

        # Draw black border.
        cr.set_source_rgb(0, 0, 0)
        cr.set_line_width(2)
        for guideline in self.active_guidelines:
            guideline.draw_func(cr, width, height)
        cr.stroke()

        # Draw blue line in middle.
        cr.set_source_rgb(0.75, 1.0, 1.0)
        cr.set_line_width(1)
        for guideline in self.active_guidelines:
            guideline.draw_func(cr, width, height)
        cr.stroke()
