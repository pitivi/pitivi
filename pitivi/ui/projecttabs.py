# PiTiVi , Non-linear video editor
#
#       ui/projecttabs.py
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
Source and effects list widgets
"""

import gtk
from gettext import gettext as _
from sourcelist import SourceList
from audiofxlist import AudioFxList
from videofxlist import VideoFxList
from propertyeditor import PropertyEditor

class ProjectTabs(gtk.Notebook):
    """
    Widget for the various source factories (files, effects, live,...)
    """

    __DEFAULT_COMPONENTS__ = (
        (SourceList, _("Clip Library")),
        # (AudioFxList, _("Audio Effects")),
        # (VideoFxList, _("Video Effects")),
        (PropertyEditor, _("Properties")),
    )

    def __init__(self):
        """ initialize """
        gtk.Notebook.__init__(self)
        self._createUi()

    def _createUi(self):
        """ set up the gui """
        self.set_tab_pos(gtk.POS_TOP)
        for component, label in self.__DEFAULT_COMPONENTS__:
            self.addComponent(component, label)

    def addComponent(self, component, label):
        # TODO: detachability
        self.append_page(component(), gtk.Label(label))
