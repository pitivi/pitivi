# PiTiVi , Non-linear video editor
#
#       pitivi/ui/infolayer.py
#
# Copyright (c) 2006, Edward Hervey <bilboed@bilboed.com>
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

import gtk
import gst


class InfoLayer(gtk.Expander):

    __gsignals__ = {
        "activate":"override",
        "size-request":"override"
        }

    def __init__(self, layerInfo):
        gtk.Expander.__init__(self, "Track")
        self.layerInfo = layerInfo
        self.set_border_width(5)
        self.set_expanded(self.layerInfo.expanded)
        self.add(gtk.Label("Track Info"))

        # TODO :
        # . react on 'expand' virtual method
        # . put content

    def do_activate(self):
        gst.debug("do activate")
        self.layerInfo.expanded = not self.get_expanded()
        gtk.Expander.do_activate(self)

    def do_size_request(self, requisition):
        # setting the requested height of the whole layer should be done here.
        gtk.Expander.do_size_request(self, requisition)
        requisition.height = max(requisition.height, self.getNeededHeight())
        gst.debug("%r expanded:%d returning %s" % (self, self.layerInfo.expanded, list(requisition)))
