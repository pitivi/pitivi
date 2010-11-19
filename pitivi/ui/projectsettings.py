# PiTiVi , Non-linear video editor
#
#       ui/projectsettings.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
# Copyright (c) 2010, Brandon Lewis <brandon.lewis@collabora.co.uk>
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
from pitivi.ui.ripple_update_group import RippleUpdateGroup
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

        self.settings = project.getSettings()
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

        # behavior

        self.wg = RippleUpdateGroup(
            (self.frame_rate_combo, self._updateCombo, "changed",
                self.frame_rate_fraction_widget),
            (self.frame_rate_fraction_widget, self._updateFraction, 
                "value-changed", self.frame_rate_combo),
            (self.dar_combo, None, "changed"),
            (self.dar_fraction_widget, None, "value-changed"),
            (self.par_combo, None, "changed"),
            (self.par_fraction_widget, None, "value-changed"),
            (self.width_spinbutton, None, "value-changed"),
            (self.height_spinbutton, None, "value-changed"),
        )

        # constrain width and height IFF constrain_sar_button is active
        self.wg.add_edge(self.width_spinbutton, self.height_spinbutton,
            self.constrained, self.updateHeight)
        self.wg.add_edge(self.height_spinbutton, self.width_spinbutton,
            self.constrained, self.updateWidth)

        # keep framereate text field and combo in sync
        self.wg.add_bi_edge(self.frame_rate_combo,
           self.frame_rate_fraction_widget)

        # keep dar text field and combo in sync
        self.wg.add_edge(self.dar_combo, self.dar_fraction_widget,
            edge_func=self.updateDarFromCombo)
        self.wg.add_edge(self.dar_fraction_widget, self.dar_combo,
            edge_func=self.updateDarFromFractionWidget)

        # keep par text field and combo in sync
        self.wg.add_edge(self.par_combo, self.par_fraction_widget,
            edge_func=self.updateParFromCombo)
        self.wg.add_edge(self.par_fraction_widget, self.par_combo,
            edge_func=self.updateParFromFractionWidget)

        # constrain DAR and PAR values. because the combo boxes are already
        # linked, we only have to link the fraction widgets together.
        self.wg.add_edge(self.par_fraction_widget, self.dar_fraction_widget,
            edge_func=self.updateDarFromPar)
        self.wg.add_edge(self.dar_fraction_widget, self.par_fraction_widget,
            edge_func=self.updateParFromDar)

        # update PAR when width/height change and the DAR checkbutton is
        # selected
        self.wg.add_edge(self.width_spinbutton, self.par_fraction_widget,
            predicate=self.darSelected, edge_func=self.updateParFromDar)
        self.wg.add_edge(self.height_spinbutton, self.par_fraction_widget,
            predicate=self.darSelected, edge_func=self.updateParFromDar)

        # update DAR when width/height change and the PAR checkbutton is
        # selected
        self.wg.add_edge(self.width_spinbutton, self.dar_fraction_widget,
            predicate=self.parSelected, edge_func=self.updateDarFromPar)
        self.wg.add_edge(self.height_spinbutton, self.dar_fraction_widget,
            predicate=self.parSelected, edge_func=self.updateDarFromPar)

        self.updateUI()

    def constrained(self):
        return self.constrain_sar_button.props.active

    def _updateFraction(self, unused, fraction, combo):
        fraction.setWidgetValue(get_combo_value(combo))

    def _updateCombo(self, unused, combo, fraction):
        set_combo_value(combo, fraction.getWidgetValue())

    def getSAR(self):
        width = int(self.width_spinbutton.get_value())
        height = int(self.height_spinbutton.get_value())
        return gst.Fraction(width, height)

    def _constrainSarButtonToggledCb(self, button):
        if button.props.active:
            self.sar = self.getSAR()

    def _selectDarRadiobuttonToggledCb(self, button):
        state = button.props.active
        self.dar_fraction_widget.set_sensitive(state)
        self.dar_combo.set_sensitive(state)
        self.par_fraction_widget.set_sensitive(not state)
        self.par_combo.set_sensitive(not state)

    def darSelected(self):
        return self.select_dar_radiobutton.props.active

    def parSelected(self):
        return not self.darSelected()

    def updateWidth(self):
        height = int(self.height_spinbutton.get_value())
        self.width_spinbutton.set_value(height * self.sar)

    def updateHeight(self):
        width = int(self.width_spinbutton.get_value())
        self.height_spinbutton.set_value(width * (1 / self.sar))

    def updateDarFromPar(self):
        par = self.par_fraction_widget.getWidgetValue()
        sar = self.getSAR()
        self.dar_fraction_widget.setWidgetValue(sar * par)

    def updateParFromDar(self):
        dar = self.dar_fraction_widget.getWidgetValue()
        sar = self.getSAR()
        self.par_fraction_widget.setWidgetValue(dar * (1 / sar))

    def updateDarFromCombo(self):
        self.dar_fraction_widget.setWidgetValue(get_combo_value(
            self.dar_combo))

    def updateDarFromFractionWidget(self):
        set_combo_value(self.dar_combo, 
            self.dar_fraction_widget.getWidgetValue())

    def updateParFromCombo(self):
        self.par_fraction_widget.setWidgetValue(get_combo_value(
            self.par_combo))

    def updateParFromFractionWidget(self):
        set_combo_value(self.par_combo, 
            self.par_fraction_widget.getWidgetValue())

    def updateUI(self):

        self.width_spinbutton.set_value(self.settings.videowidth)
        self.height_spinbutton.set_value(self.settings.videoheight)

        # video
        self.frame_rate_fraction_widget.setWidgetValue(self.settings.videorate)
        self.par_fraction_widget.setWidgetValue(self.settings.videopar)

        # audio
        set_combo_value(self.channels_combo, self.settings.audiochannels)
        set_combo_value(self.sample_rate_combo, self.settings.audiorate)
        set_combo_value(self.sample_depth_combo, self.settings.audiodepth)

        self._selectDarRadiobuttonToggledCb(self.select_dar_radiobutton)

    def updateSettings(self):
        width = int(self.width_spinbutton.get_value())
        height = int(self.height_spinbutton.get_value())
        par = self.par_fraction_widget.getWidgetValue()
        frame_rate = self.frame_rate_fraction_widget.getWidgetValue()

        channels = get_combo_value(self.channels_combo)
        sample_rate = get_combo_value(self.sample_rate_combo)
        sample_depth = get_combo_value(self.sample_depth_combo)

        self.settings.setVideoProperties(width, height, frame_rate, par)
        self.settings.setAudioProperties(channels, sample_rate, sample_depth)

        self.project.setSettings(self.settings)

    def _responseCb(self, unused_widget, response):
        if response == gtk.RESPONSE_OK:
            self.updateSettings()
        self.destroy()
