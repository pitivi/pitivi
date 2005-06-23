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

import gobject
import gtk
from glade import GladeWindow

class ProjectSettingsDialog(GladeWindow):
    glade_file = "projectsettings.glade"

    def __init__(self, parent, project):
        GladeWindow.__init__(self, parent)
        self.project = project
        self.widgets["exportwidget"].set_settings(self.project.settings)
        self._fill_settings()

    def _fill_settings(self):
        w = self.widgets
        w["nameentry"].set_text(self.project.name)
        w["descriptiontextview"].get_buffer().set_text(self.project.description)
        

    def _update_settings(self):
        # apply selected settings to project
        w = self.widgets
        
        # Name/Description
        self.project.name = w["nameentry"].get_text()
        txtbuffer = w["descriptiontextview"].get_buffer()
        self.project.description = txtbuffer.get_text(txtbuffer.get_start_iter(),
                                                      txtbuffer.get_end_iter())
        w["exportwidget"]._update_settings()

    def response_cb(self, widget, response):
        # if the response is gtk.RESPONSE_OK update the settings
        # else destroy yourself !
        self.hide()
        if response == gtk.RESPONSE_OK:
            print "settings updated"
            self._update_settings()
        else:
            print "settings NOT updated!"
        self.destroy()
