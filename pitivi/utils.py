#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       utils.py
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

# set of utility functions

import gst, bisect

def time_to_string(value):
    """ Converts the given time in nanoseconds to a human readable string """
    if value == gst.CLOCK_TIME_NONE:
        return "--:--:--.---"
    ms = value / gst.MSECOND
    sec = ms / 1000
    ms = ms % 1000
    mins = sec / 60
    sec = sec % 60
    hours = mins / 60
    mins = mins % 60
    return "%02d:%02d:%02d.%03d" % (hours, mins, sec, ms)

def bin_contains(bin, element):
    """ Returns True if the bin contains the given element, the search is recursive """
    if not isinstance(bin, gst.Bin):
        return False
    if not isinstance(element, gst.Element):
        return False
    for elt in bin:
        if element is elt:
            return True
        if isinstance(elt, gst.Bin) and bin_contains(elt, element):
            return True
    return False

# Python re-implementation of binary search algorithm found here:
# http://en.wikipedia.org/wiki/Binary_search
#
# This is the iterative version without the early termination branch, which
# also tells us the element of A that are nearest to Value, if the element we
# want is not found. This is useful for implementing edge snaping in the UI,
# where we repeatedly search through a list of control points for the one
# closes to the cursor. Because we don't care whether the cursor position
# matches the list, this function returns the index of the lement closest to
# value in the array.

def binary_search(col, value):
    low = 0
    high = len(col)
    while (low < high):
        mid = (low + high)/2
        if (col[mid] < value):
            low = mid + 1
        else:
            #can't be high = mid-1: here col[mid] >= value,
            #so high can't be < mid if col[mid] == value
            high = mid;
    return low

# Returns the element of seq nearest to item, and the difference between them

def closest_item(seq, item):
    index = bisect.bisect(seq, item)
    if index >= len(seq):
        index = len(seq) - 1
    res = seq[index]
    diff = abs(res - item)

    # binary_search returns largest element closest to item.
    # if there is a smaller element...
    if index - 1 >= 0:
        res_a = seq[index - 1]
        # ...and it is closer to the pointer...
        diff_a = abs(res_a - item)
        if diff_a < diff:
            # ...use it instead.
            res = res_a
            diff = diff_a
    return res, diff

def argmax(func, seq):
    """return the element of seq that gives max(map(func, seq))"""
    def compare(a1, b1):
        if a1[0] > b1[0]:
            return a1
        return b1
    # using a generator expression here should save memory
    objs = ((func(val), val) for val in seq)
    return reduce(compare, objs)[1]
