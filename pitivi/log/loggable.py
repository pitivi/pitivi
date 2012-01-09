# PiTiVi , Non-linear video editor
#
#       pitivi/log/loggable.py
#
# Copyright (c) 2009, Alessandro Decina <alessandro.decina@collabora.co.uk>
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

from pitivi.log.log import _canShortcutLogging, doLog, ERROR
from pitivi.log import log


class Loggable(log.Loggable):
    def __init__(self, logCategory=None):
        if logCategory:
            self.logCategory = logCategory
        elif not hasattr(self, 'logCategory'):
            self.logCategory = self.__class__.__name__.lower()

    def logObjectName(self):
        res = log.Loggable.logObjectName(self)
        if not res:
            return "<%s at 0x%x>" % (self.__class__.__name__, id(self))
        return res

    def error(self, format, *args):
        if _canShortcutLogging(self.logCategory, ERROR):
            return
        doLog(ERROR, self.logObjectName(), self.logCategory,
            format, self.logFunction(*args), where=-2)
