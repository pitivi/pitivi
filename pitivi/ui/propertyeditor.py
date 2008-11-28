# PiTiVi , Non-linear video editor
#
#       ui/propertyeditor.py
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
Editor for aribtrary properties of timeline objects
"""

import gtk
import pitivi.instance as instance
from gettext import gettext as _
from pitivi.receiver import receiver, handler

class PropertyEditor(gtk.VBox):

    def __init__(self, *args, **kwargs):
        gtk.VBox.__init__(self, *args, **kwargs)
        self.instance = instance.PiTiVi
        self.timeline = instance.PiTiVi.current.timeline
        self.__createUi()

    def __createUi(self):
        # basic initialization
        self.set_border_width(5)
        self.set_spacing(6)

        # scrolled window
        scrolled = gtk.ScrolledWindow()
        scrolled.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.label = gtk.Label()
        scrolled.add_with_viewport(self.label)
        self.add(scrolled)
        self.__selectionChangedCb(self.timeline)

## Instance Callbacks

    instance = receiver()

    @handler(instance, "new-project-loading")
    def __newProjectLoading(self, unused_inst, project):
        self.timeline = project.timeline

    @handler(instance, "new-project-failed")
    def __newProjectFailed(self, unused_inst, unused_reason, unused_uri):
        self.timeline = None

## Timeline Callbacks

    timeline = receiver()

    @handler(timeline, "selection-changed")
    def __selectionChangedCb(self, timeline):
        if not self.timeline:
            return

        objs = self.timeline.getSelection()
        if objs:
            text = "Properties For: "
            for obj in self.timeline.getSelection():
                text += "\n" + obj.factory.name
        else:
            text = "No Objects Selected"
        self.label.set_text(text)
