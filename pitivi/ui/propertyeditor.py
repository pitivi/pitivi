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
from pitivi.utils import same
from defaultpropertyeditor import DefaultPropertyEditor

class PropertyEditor(gtk.ScrolledWindow):

    __MODULES__ = {
        
    }

    def __init__(self, *args, **kwargs):
        gtk.ScrolledWindow.__init__(self, *args, **kwargs)
        self.instance = instance.PiTiVi
        self.timeline = instance.PiTiVi.current.timeline
        self.__createUi()
        self.__selectionChangedCb(self.timeline)
        self.__module_instances = {}
        self.__default_editor = DefaultPropertyEditor()

    def __createUi(self):
        # basic initialization
        self.set_border_width(5)

        # scrolled window
        self.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.__no_objs = gtk.Viewport()
        self.__no_objs.add(gtk.Label(_("No Objects Selected")))
        self.__contents = self.__no_objs
        self.add(self.__no_objs)

## Public API

    @classmethod
    def addModule(cls, core_class, widget_class):
        cls.__MODULES__[core_class] = widget_class

    @classmethod
    def delModule(cls, core_class):
        del cls.__MODULES__[core_class]

## Internal Methods

    def __get_widget_for_type(self, t):
        w = self.__default_editor
        if t in self.__module_instances:
            w = self.__module_instances[t]
        elif t in self.__MODULES__:
            w = self.__MODULES[t]()
            self.__module_instances[t] = w
        return w

    def __set_contents(self, widget):
        if widget != self.__contents:
            self.remove(self.__contents)
            self.__contents = widget
            self.add(widget)
            self.show_all()

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
            t = same(map(type, objs))
            if t:
                widget = self.__get_widget_for_type(t)
            else:
                widget = DefaultPropertyEditor(objs)
            widget.setObjects(objs)
        else:
            widget = self.__no_objs
        self.__set_contents(widget)

