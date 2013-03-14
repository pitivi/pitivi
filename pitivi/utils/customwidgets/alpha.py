# PiTiVi , Non-linear video editor
#
# Copyright (c) 2013, Thibault Saunier <thibault.saunier@collabora.com>
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

import os

from gi.repository import Gtk

import pitivi.configure as configure


def create_widget(element_setting_widget, element):
    ui = element_setting_widget
    builder = Gtk.Builder()
    builder.add_from_file(os.path.join(configure.get_ui_dir(), "effect-alpha.ui"))
    ui.mapBuilder(builder)

    table = builder.get_object("base_table")
    window = builder.get_object("window1")

    window.remove(table)

    return table
