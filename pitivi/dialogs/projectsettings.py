# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2013, 2014, 2015, Thibault Saunier <tsaunier@gnome.org>
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
"""Project settings dialog."""
import datetime
import os

from gi.repository import Gst
from gi.repository import Gtk

from pitivi.configure import get_ui_dir
from pitivi.dialogs.prefs import PreferencesDialog
from pitivi.preset import VideoPresetManager
from pitivi.utils.ripple_update_group import RippleUpdateGroup
from pitivi.utils.ui import create_frame_rates_model
from pitivi.utils.ui import get_combo_value
from pitivi.utils.ui import set_combo_value
from pitivi.utils.widgets import FractionWidget


class ProjectSettingsDialog:
    """Manager of a dialog for viewing and changing the project settings.

    Attributes:
        project (Project): The project who's settings are displayed.
        app (Pitivi): The current app.
    """

    def __init__(self, parent_window, project, app):
        self.app = app
        self.project = project
        self.video_presets = VideoPresetManager(app.system)

        self.sar = 0
        self.proxy_aspect_ratio = Gst.Fraction(1, 0)

        self._create_ui()
        self.window.set_transient_for(parent_window)
        self._setup_ui_constraints()
        self.update_ui()

    def _create_ui(self):
        """Initializes the static parts of the UI."""
        self.builder = Gtk.Builder()
        self.builder.add_from_file(
            os.path.join(get_ui_dir(), "projectsettings.ui"))
        self.builder.connect_signals(self)

        self.window = self.builder.get_object("project-settings-dialog")
        self.frame_rate_combo = self.builder.get_object("frame_rate_combo")
        self.year_spinbutton = self.builder.get_object("year_spinbutton")
        self.author_entry = self.builder.get_object("author_entry")
        self.width_spinbutton = self.builder.get_object("width_spinbutton")
        self.height_spinbutton = self.builder.get_object("height_spinbutton")
        self.video_presets_combo = self.builder.get_object("video_presets_combo")
        self.constrain_sar_button = self.builder.get_object("constrain_sar_button")
        self.select_dar_radiobutton = self.builder.get_object("select_dar_radiobutton")
        self.year_spinbutton = self.builder.get_object("year_spinbutton")

        self.video_preset_menubutton = self.builder.get_object("video_preset_menubutton")
        self.video_presets.setup_ui(self.video_presets_combo,
                                    self.video_preset_menubutton)
        self.video_presets.connect("preset-loaded", self.__video_preset_loaded_cb)

        self.scaled_proxy_width_spin = self.builder.get_object("scaled_proxy_width")
        self.scaled_proxy_height_spin = self.builder.get_object("scaled_proxy_height")
        self.proxy_res_linked_check = self.builder.get_object("proxy_res_linked")

        self.title_horizontal_spinbutton = self.builder.get_object("title_safe_area_horizontal")
        self.title_vertical_spinbutton = self.builder.get_object("title_safe_area_vertical")
        self.action_horizontal_spinbutton = self.builder.get_object("action_safe_area_horizontal")
        self.action_vertical_spinbutton = self.builder.get_object("action_safe_area_vertical")

    def _setup_ui_constraints(self):
        """Creates the dynamic widgets and connects other widgets."""
        # Add custom framerate fraction widget.
        frame_rate_box = self.builder.get_object("frame_rate_box")
        self.frame_rate_fraction_widget = FractionWidget()
        frame_rate_box.pack_end(self.frame_rate_fraction_widget, True, True, 0)
        self.frame_rate_fraction_widget.show()

        # Behavior.
        self.widgets_group = RippleUpdateGroup()
        self.widgets_group.add_vertex(self.frame_rate_combo,
                                      signal="changed",
                                      update_func=self._update_frame_rate_combo_func,
                                      update_func_args=(self.frame_rate_fraction_widget,))
        self.widgets_group.add_vertex(self.frame_rate_fraction_widget,
                                      signal="value-changed",
                                      update_func=self._update_frame_rate_fraction_func,
                                      update_func_args=(self.frame_rate_combo,))
        self.widgets_group.add_vertex(self.width_spinbutton, signal="value-changed")
        self.widgets_group.add_vertex(self.height_spinbutton, signal="value-changed")
        self.widgets_group.add_vertex(self.video_preset_menubutton,
                                      update_func=self._update_preset_menu_button_func,
                                      update_func_args=(self.video_presets,))
        self.widgets_group.add_vertex(self.scaled_proxy_width_spin, signal="value-changed")
        self.widgets_group.add_vertex(self.scaled_proxy_height_spin, signal="value-changed")

        # Constrain width and height IFF the Constrain checkbox is checked.
        # Video
        self.widgets_group.add_edge(self.width_spinbutton, self.height_spinbutton,
                                    predicate=self.width_height_linked,
                                    edge_func=self.update_height)
        self.widgets_group.add_edge(self.height_spinbutton, self.width_spinbutton,
                                    predicate=self.width_height_linked,
                                    edge_func=self.update_width)
        # Proxy
        self.widgets_group.add_edge(self.scaled_proxy_width_spin,
                                    self.scaled_proxy_height_spin,
                                    predicate=self.proxy_res_linked,
                                    edge_func=self.update_scaled_proxy_height)
        self.widgets_group.add_edge(self.scaled_proxy_height_spin,
                                    self.scaled_proxy_width_spin,
                                    predicate=self.proxy_res_linked,
                                    edge_func=self.update_scaled_proxy_width)

        # Keep the framerate combo and fraction widgets in sync.
        self.widgets_group.add_bi_edge(
            self.frame_rate_combo, self.frame_rate_fraction_widget)

        # Presets.
        self.video_presets.load_all()

        # Bind the widgets in the Video tab to the Video Presets Manager.
        self.bind_spinbutton(self.video_presets, "width", self.width_spinbutton)
        self.bind_spinbutton(self.video_presets, "height", self.height_spinbutton)
        self.bind_fraction_widget(
            self.video_presets, "frame-rate", self.frame_rate_fraction_widget)

        self.widgets_group.add_edge(
            self.frame_rate_fraction_widget, self.video_preset_menubutton)
        self.widgets_group.add_edge(self.width_spinbutton, self.video_preset_menubutton)
        self.widgets_group.add_edge(self.height_spinbutton, self.video_preset_menubutton)

    def bind_fraction_widget(self, mgr, name, widget):
        mgr.bind_widget(name, widget.set_widget_value, widget.get_widget_value)

    def bind_combo(self, mgr, name, widget):
        def setter(value):
            res = set_combo_value(widget, value)
            assert res, value
        mgr.bind_widget(name, setter, lambda: get_combo_value(widget))

    def bind_spinbutton(self, mgr, name, widget):
        mgr.bind_widget(name,
                        lambda x: widget.set_value(float(x)),
                        lambda: int(widget.get_value()))

    def width_height_linked(self):
        return self.constrain_sar_button.props.active and not self.video_presets.ignore_update_requests

    def proxy_res_linked(self):
        return self.proxy_res_linked_check.props.active

    def _update_frame_rate_fraction_func(self, unused, fraction_widget, combo_widget):
        """Updates the fraction_widget to match the combo_widget."""
        fraction_widget.set_widget_value(get_combo_value(combo_widget))

    def _update_frame_rate_combo_func(self, unused, combo_widget, fraction_widget):
        """Updates the combo_widget to match the fraction_widget."""
        widget_value = fraction_widget.get_widget_value()
        fr_datum = (widget_value.num, widget_value.denom)
        model = create_frame_rates_model(fr_datum)
        self.frame_rate_combo.set_model(model)
        res = set_combo_value(combo_widget, widget_value)
        assert res, widget_value

    def __video_preset_loaded_cb(self, unused_mgr):
        self.sar = self.get_sar()

    def get_sar(self):
        width = int(self.width_spinbutton.get_value())
        height = int(self.height_spinbutton.get_value())
        return Gst.Fraction(width, height)

    def _constrain_sar_button_toggled_cb(self, unused_button):
        self.sar = self.get_sar()

    def _update_preset_menu_button_func(self, unused_source, unused_target, mgr):
        mgr.update_menu_actions()

    def update_width(self):
        height = int(self.height_spinbutton.get_value())
        fraction = height * self.sar
        width = int(fraction.num / fraction.denom)
        self.width_spinbutton.set_value(width)

    def update_height(self):
        width = int(self.width_spinbutton.get_value())
        fraction = width / self.sar
        height = int(fraction.num / fraction.denom)
        self.height_spinbutton.set_value(height)

    def _proxy_res_linked_toggle_cb(self, unused_button):
        width = int(self.scaled_proxy_width_spin.get_value())
        height = int(self.scaled_proxy_height_spin.get_value())
        self.proxy_aspect_ratio = Gst.Fraction(width, height)

    def _proxy_settings_label_cb(self, unused_widget, unused_parm):
        prefs_dialog = PreferencesDialog(self.app)
        prefs_dialog.stack.set_visible_child_name("_proxies")
        prefs_dialog.run()

    def update_scaled_proxy_width(self):
        height = int(self.scaled_proxy_height_spin.get_value())
        fraction = height * self.proxy_aspect_ratio
        width = int(fraction.num / fraction.denom)
        self.scaled_proxy_width_spin.set_value(width)

    def update_scaled_proxy_height(self):
        width = int(self.scaled_proxy_width_spin.get_value())
        fraction = width / self.proxy_aspect_ratio
        height = int(fraction.num / fraction.denom)
        self.scaled_proxy_height_spin.set_value(height)

    def update_ui(self):
        # Video
        self.width_spinbutton.set_value(self.project.videowidth)
        self.height_spinbutton.set_value(self.project.videoheight)
        self.frame_rate_fraction_widget.set_widget_value(self.project.videorate)

        matching_video_preset = self.video_presets.matching_preset(self.project)
        if matching_video_preset:
            self.video_presets_combo.set_active_id(matching_video_preset)

        # Safe Areas
        self.title_vertical_spinbutton.set_value(self.project.title_safe_area_vertical * 100)
        self.title_horizontal_spinbutton.set_value(self.project.title_safe_area_horizontal * 100)
        self.action_vertical_spinbutton.set_value(self.project.action_safe_area_vertical * 100)
        self.action_horizontal_spinbutton.set_value(self.project.action_safe_area_horizontal * 100)

        # Metadata
        self.author_entry.set_text(self.project.author)
        if self.project.year:
            year = int(self.project.year)
        else:
            year = datetime.datetime.now().year
        self.year_spinbutton.get_adjustment().set_value(year)

        self.scaled_proxy_width_spin.set_value(self.project.scaled_proxy_width)
        self.scaled_proxy_height_spin.set_value(self.project.scaled_proxy_height)

    def update_project(self):
        with self.app.action_log.started("change project settings",
                                         toplevel=True):
            self.project.author = self.author_entry.get_text()
            self.project.year = str(self.year_spinbutton.get_value_as_int())

            self.project.set_video_properties(
                int(self.width_spinbutton.get_value()),
                int(self.height_spinbutton.get_value()),
                self.frame_rate_fraction_widget.get_widget_value())

            # Store values as a decimal value
            self.project.set_safe_areas_sizes(int(self.title_horizontal_spinbutton.get_value()) / 100,
                                              int(self.title_vertical_spinbutton.get_value()) / 100,
                                              int(self.action_horizontal_spinbutton.get_value()) / 100,
                                              int(self.action_vertical_spinbutton.get_value()) / 100)

            proxy_width = int(self.scaled_proxy_width_spin.get_value())
            proxy_height = int(self.scaled_proxy_height_spin.get_value())
            # Update scaled proxy meta-data and trigger proxy regen
            if not self.project.has_scaled_proxy_size() or \
                    self.project.scaled_proxy_width != proxy_width or \
                    self.project.scaled_proxy_height != proxy_height:
                self.project.scaled_proxy_width = proxy_width
                self.project.scaled_proxy_height = proxy_height

                self.project.regenerate_scaled_proxies()

    def _response_cb(self, unused_widget, response):
        """Handles the dialog being closed."""
        if response == Gtk.ResponseType.OK:
            self.update_project()
        self.window.destroy()
