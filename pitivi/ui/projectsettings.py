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
from pitivi.ui.glade import GladeWindow

class ProjectSettingsDialog(GladeWindow):
    glade_file = "projectsettings.glade"

    def __init__(self, parent, project):
        GladeWindow.__init__(self, parent)
        self.project = project


    def updateSettings(self):


    def _responseCb(self, unused_widget, response):
        if response == gtk.RESPONSE_OK:
            self.updateSettings()
        self.destroy()
