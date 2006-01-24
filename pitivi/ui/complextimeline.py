# PiTiVi , Non-linear video editor
#
#       pitivi/ui/complextimeline.py
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

import gtk
import gst
from complexstack import ComplexTimelineInfoStack, ComplexTimelineTrackStack

class ComplexTimelineWidget(gtk.HBox):
    __gsignals__ = {
        "size-request":"override"
        }
    _minheight = 200

    def __init__(self, pitivi, hadj, vadj):
        gst.debug("creating")
        gtk.HBox.__init__(self)
        self.pitivi = pitivi
        self.set_spacing(5)
        self.hadj = hadj
        self.vadj = vadj
        
        self.leftstack = ComplexTimelineInfoStack()
        self.rightstack = ComplexTimelineTrackStack()

        self.pack_start(self.leftstack, expand=False, fill=True)
        self.pack_start(self.rightstack, fill=True)

        self.leftstack.set_vadjustment(self.vadj)
        self.rightstack.set_vadjustment(self.vadj)
        self.rightstack.set_hadjustment(self.hadj)

        if self.pitivi.current:
            self._load_timeline(self.pitivi.current.timeline)

    def _load_timeline(self, timeline):
        self.append(timeline.videocomp)
        self.append(timeline.audiocomp)

    def append(self, composition):
        gst.debug("Appending composition %s" % composition)
        self.leftstack.append(composition)
        self.rightstack.append(composition)

    def __delitem__(self, pos):
        self.leftstack.__delitem__(pos)
        self.rightstack.__delitem__(pos)

    def do_size_request(self, requisition):
        gst.debug("timeline requisition %s" % list(requisition))
        ret = gtk.HBox.do_size_request(self, requisition)
        requisition.height = max(requisition.height, self._minheight)

    def insert(self, pos, composition):
        self.leftstack.insert(pos, composition)
        self.rightstack.insert(pos, composition)
        
