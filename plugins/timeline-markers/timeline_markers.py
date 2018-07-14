# -*- coding: utf-8 -*-
# Copyright (c) 2017, Fabian Orccon <cfoch.fabian@gmail.com>
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
"""Timeline markers that are addded to the timeline."""
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Peas

from pitivi.dialogs.prefs import PreferencesDialog
from pitivi.settings import ConfigError
from pitivi.utils.ui import PLAYHEAD_WIDTH
from pitivi.utils.ui import set_cairo_color


class TimelineMarkers(GObject.Object, Peas.Activatable):
    """Plugin to add markers every N seconds in the Pitivi timeline."""
    __gtype_name__ = 'TimelineMarkers'
    object = GObject.Property(type=GObject.Object)

    DEFAULT_TIMESPAN = 5
    DEFAULT_TIMELINE_MARKER_COLOR = (175, 235, 240)

    def __init__(self):
        GObject.Object.__init__(self)
        self.app = None
        self.timeline = None
        self.markers_positions = []
        self.timespan = Gst.SECOND * 5

    def draw_vertical_bar(self, cr, xpos, width, color):
        """Draws a vertical in the Pitivi timeline."""
        if xpos < 0:
            return

        # Add 0.5 so the line is sharp, xpos represents the center of the line.
        xpos += 0.5
        height = self.timeline.layout.get_allocated_height()
        cr.set_line_width(width)
        cr.move_to(xpos, 0)
        set_cairo_color(cr, color)
        cr.line_to(xpos, height)
        cr.stroke()

    def __draw_cb(self, layout, cr):
        layout_width = self.timeline.layout.props.width
        timespan_px = layout.nsToPixel(self.timespan)
        n_markers = int(layout_width / timespan_px)
        cr.set_dash([2, 4])
        for i in range(1, n_markers + 1):
            offset = layout.get_hadjustment().get_value()
            position = Gst.SECOND * self.app.settings.timespan * i
            x = layout.nsToPixel(position) - offset
            self.draw_vertical_bar(cr, x, PLAYHEAD_WIDTH,
                                   self.DEFAULT_TIMELINE_MARKER_COLOR)

    def do_activate(self):
        api = self.object
        self.app = api.app

        try:
            self.app.settings.addConfigSection("timeline")
            self.app.settings.addConfigOption(attrname="timespan",
                                              section="timeline",
                                              key="timespan",
                                              notify=True,
                                              default=TimelineMarkers.DEFAULT_TIMESPAN)
        except ConfigError:
            pass
        self.app.settings.reload_attribute_from_file("timeline", "timespan")
        PreferencesDialog.addNumericPreference(attrname="timespan",
                                               label=_("Markers span"),
                                               description=_("Sets the timespan (in seconds) between markers"),
                                               section="timeline",
                                               lower=0)

        self.timeline = self.app.gui.editor.timeline_ui.timeline
        self.timeline.layout.connect_after("draw", self.__draw_cb)

    def do_deactivate(self):
        print("Deactivating Timeline Markers")
        self.app.gui.editor.timeline_ui.timeline.layout.disconnect_by_func(self.__draw_cb)
        self.app = None
        self.timeline = None
