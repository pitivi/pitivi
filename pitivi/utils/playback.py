#!/usr/bin/env python
#
#       seek.py
#
# Copyright (C) 2012 Thibault Saunier <thibaul.saunier@collabora.com>
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
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.


import gst
import gobject

import pitivi.utils.loggable as log

from pitivi.signalinterface import Signallable


class Seeker(Signallable):
    """
    The Seeker is a singleton helper class to do various seeking
    operations in the pipeline.
    """

    __signals__ = {
        'seek': ['position', 'format'],
        'flush': [],
        'seek-relative': ['time'],
        'position-changed': ['position']
    }
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Seeker, cls).__new__(
                                cls, *args, **kwargs)
        return cls._instance

    def __init__(self, timeout):
        self.timeout = timeout
        self.pending_seek_id = None
        self.position = None
        self.format = None
        self._time = None

    def seek(self, position, format=gst.FORMAT_TIME, on_idle=False):
        self.format = format
        self.position = position

        if self.pending_seek_id is None:
            if on_idle:
                gobject.idle_add(self._seekTimeoutCb)
            else:
                self._seekTimeoutCb()
            self.pending_seek_id = self._scheduleSeek(self.timeout,
                    self._seekTimeoutCb)

    def seekRelative(self, time, on_idle=False):
        if self.pending_seek_id is None:
            self._time = time
            if on_idle:
                gobject.idle_add(self._seekRelativeTimeoutCb)
            else:
                self._seekTimeoutCb()
            self.pending_seek_id = self._scheduleSeek(self.timeout,
                    self._seekTimeoutCb, True)

    def flush(self):
        try:
            self.emit('flush')
        except:
            log.doLog(log.ERROR, None, "seeker", "Error while flushing", None)

    def _scheduleSeek(self, timeout, callback, relative=False):
        return gobject.timeout_add(timeout, callback, relative)

    def _seekTimeoutCb(self, relative=False):
        self.pending_seek_id = None
        if relative:
            try:
                self.emit('seek-relative', self._time)
            except:
                log.doLog(log.ERROR, None, "seeker", "Error while seeking %s relative",
                        self._time)
                # if an exception happened while seeking, properly
                # reset ourselves
                return False

            self._time = None
        elif self.position != None and self.format != None:
            position, self.position = self.position, None
            format, self.format = self.format, None
            try:
                self.emit('seek', position, format)
            except:
                log.doLog(log.ERROR, None, "seeker", "Error while seeking to position:%s format:%r",
                          (gst.TIME_ARGS(position), format))
                # if an exception happened while seeking, properly
                # reset ourselves
                return False
        return False

    def setPosition(self, position):
        self.emit("position-changed", position)
