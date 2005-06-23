# PiTiVi , Non-linear video editor
#
#       pitivi/debug.py
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
import gst

def debug_element(bin, space=0):
    print 5*space*" ", bin.get_name()
    for pad in bin.get_pad_list():
        print (5*space+2)*" ", pad.get_name(),
        if pad.get_peer():
            print "->", pad.get_peer().get_parent().get_name(), ":", pad.get_peer().get_name()
        else:
            print "X"
        print "%s%050s" % ((5*space+3)*" ", pad.get_caps().to_string())
    if isinstance(bin, gst.Bin):
        print 5*space*" ", "Childs:"
        for element in bin.get_list():
            debug_element(element, space + 1)
    print "\n"
