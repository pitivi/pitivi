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

class DetachLabel(gtk.HBox):

    def __init__(self, parent, child, label, *args, **kwargs):
        gtk.HBox.__init__(self, *args, **kwargs)

        self.label = gtk.Label(label)
        self.child = child
        self.button = gtk.Button()
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_LEAVE_FULLSCREEN,
            gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.button.set_image(image)
        self.button.connect("clicked", self._windowize)
        self.pack_start(self.button, False, False)
        self.pack_start(self.label)
        self.show_all()

    def select(self):
        self.button.set_sensitive(True)

    def deselect(self):
        self.button.set_sensitive(False)

    def _windowize(self, unused_button):
        self.parent.windowizeComponent(self.child, self)

class ProjectTabs(gtk.Notebook):
    """
    Widget for the various source factories (files, effects, live,...)
    """

    __DEFAULT_COMPONENTS__ = (
        (SourceList, _("Clip Library")),
        # (AudioFxList, _("Audio Effects")),
        # (VideoFxList, _("Video Effects")),
        # FIXME : Property editor disabled for 0.11.3 release, re-enable after
        # (PropertyEditor, _("Properties")),
    )

    def __init__(self, instance, uiman):
        """ initialize """
        gtk.Notebook.__init__(self)
        self.app = instance
        self.uiman = uiman
        self._full_list = []
        self.connect("switch-page", self._switchPage)
        self._createUi()

    def _createUi(self):
        """ set up the gui """
        self.set_tab_pos(gtk.POS_TOP)
        for component, label in self.__DEFAULT_COMPONENTS__:
            self.addComponent(component(self.app, self.uiman), label)

    def addComponent(self, component, label):
        self.append_page(component, DetachLabel(self, component, label))
        self._full_list.append(component)

    def windowizeComponent(self, component, label):
        self.remove_page(self.page_num(component))
        window = gtk.Window()
        window.add(component)
        window.show_all()
        window.connect("destroy", self._replaceComponent, component, label)
        window.resize(200, 200)
        if not self.get_n_pages():
            self.hide()

    def _replaceComponent(self, window, component, label):
        window.remove(component)
        self.set_current_page(self.insert_page(component, label,
            self._full_list.index(component)))
        self.show()

    def _switchPage(self, unused_widget, unused_page, num):
        for child in (self.get_nth_page(i) for i in xrange(self.get_n_pages())):
            self.get_tab_label(child).deselect()
        cur = self.get_tab_label(self.get_nth_page(num))
        cur.select()
