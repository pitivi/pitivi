#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       thumbnailcache.py
#
# Copyright (c) 2009, Brandon Lewis (brandon_lewis@berkeley.edu)
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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

"""
Dictionary-Like object for caching of thumbnails.
"""

import collections

class ThumbnailCache(object):

    """Caches thumbnails by key using LRU policy, implemented with heapq"""

    def __init__(self, size=100):
        object.__init__(self)
        self.queue = collections.deque()
        self.cache = {}
        self.hits = 0
        self.misses = 0
        self.size = size

    def __contains__(self, key):
        if key in self.cache:
            self.hits += 1
            return True
        self.misses += 1
        return False

    def __getitem__(self, key):
        if key in self.cache:
            # I guess this is why LRU is considered expensive
            self.queue.remove(key)
            self.queue.append(key)
            return self.cache[key]
        raise KeyError(key)

    def __setitem__(self, key, value):
        self.cache[key] = value
        self.queue.append(key)
        if len(self.cache) > self.size:
            self.ejectLRU()

    def ejectLRU(self):
        key = self.queue.popleft()
        del self.cache[key]
