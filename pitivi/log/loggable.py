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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

from pitivi.log.log import _canShortcutLogging, doLog, ERROR
from pitivi.log import log

def _errorObject(object, cat, format, *args):
    """
    Log a fatal error message in the given category.
    This will also raise a L{SystemExit}.
    """
    doLog(ERROR, object, cat, format, args)

class Loggable(log.Loggable):
    def __init__(self):
        if not hasattr(self, 'logCategory'):
            self.logCategory = self.__class__.__name__.lower()

    def logObjectName(self):
        res = log.Loggable.logObjectName(self)
        if not res:
            return "<%s at 0x%x>" % (self.__class__.__name__, id(self))
        return res

    def error(self, *args):
        if _canShortcutLogging(self.logCategory, ERROR):
            return
        _errorObject(self.logObjectName(), self.logCategory,
            *self.logFunction(*args))
