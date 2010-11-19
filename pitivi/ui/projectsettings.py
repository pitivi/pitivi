# PiTiVi , Non-linear video editor
#
#       ui/projectsettings.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""
Dialog box for project settings
"""

import gtk
import gst
from gettext import gettext as _
from pitivi.ui.glade import GladeWindow
from pitivi.ui.dynamic import FractionWidget
from pitivi.ui.common import\
    model,\
    frame_rates,\
    audio_rates,\
    audio_depths,\
    audio_channels,\
    get_combo_value,\
    set_combo_value

# FIXME: are we sure the following tables correct?

pixel_aspect_ratios = model((str, object), (
    (_("Square"), gst.Fraction(1, 1)),
    (_("480p"), gst.Fraction(10, 11)),
    (_("480i"), gst.Fraction(8, 9)),
    (_("480p Wide"), gst.Fraction(40, 33)),
    (_("480i Wide"), gst.Fraction(32, 27)),
    (_("576p"), gst.Fraction(12, 11)),
    (_("576i"), gst.Fraction(16, 15)),
    (_("576p Wide"), gst.Fraction(16, 11)),
    (_("576i Wide"), gst.Fraction(64, 45)),
))

display_aspect_ratios = model((str, object), (
    (_("Standard (4:3)"), gst.Fraction(4, 3)),
    (_("DV (15:11)"), gst.Fraction(15, 11)),
    (_("DV Widescreen (16:9)"), gst.Fraction(16, 9)),
    (_("Cinema (1.37)"), gst.Fraction(11, 8)),
    (_("Cinema (1.66)"), gst.Fraction(166, 100)),
    (_("Cinema (1.85)"), gst.Fraction(185, 100)),
    (_("Anamorphic (2.35)"), gst.Fraction(235, 100)),
    (_("Anamorphic (2.39)"), gst.Fraction(239, 100)),
    (_("Anamorphic (2.4)"), gst.Fraction(24, 10)),
))

class ProjectSettingsDialog(GladeWindow):
    glade_file = "projectsettings.glade"

    def __init__(self, parent, project):
        GladeWindow.__init__(self, parent)
        self.project = project

        # add custom widgets
        self.dar_fraction_widget = FractionWidget()
        self.video_properties_table.attach(self.dar_fraction_widget, 
            0, 1, 6, 7, xoptions=gtk.EXPAND | gtk.FILL, yoptions=0)
        self.dar_fraction_widget.show()

        # add custom widgets
        self.par_fraction_widget = FractionWidget()
        self.video_properties_table.attach(self.par_fraction_widget, 
            1, 2, 6, 7, xoptions=gtk.EXPAND | gtk.FILL, yoptions=0)
        self.par_fraction_widget.show()

        self.frame_rate_fraction_widget = FractionWidget()
        self.video_properties_table.attach(self.frame_rate_fraction_widget,
            1, 2, 2, 3, xoptions=gtk.EXPAND | gtk.FILL, yoptions=0)
        self.frame_rate_fraction_widget.show()

        # populate coboboxes with appropriate data
        self.frame_rate_combo.set_model(frame_rates)
        self.dar_combo.set_model(display_aspect_ratios)
        self.par_combo.set_model(pixel_aspect_ratios)

        self.channels_combo.set_model(audio_channels)
        self.sample_rate_combo.set_model(audio_rates)
        self.sample_depth_combo.set_model(audio_depths)
    def updateSettings(self):


    def _responseCb(self, unused_widget, response):
        if response == gtk.RESPONSE_OK:
            self.updateSettings()
        self.destroy()
