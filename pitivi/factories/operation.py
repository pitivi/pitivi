# PiTiVi , Non-linear video editor
#
#       operation.py
#
# Copyright (c) 2009, Edward Hervey <bilboed@bilboed.com>
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

from gettext import gettext as _


class Effect():
    """
    Factories that applies an effect on a stream
    """
    def __init__(self, effect, name='', categories=[_("Uncategorized")],
                  human_name="", description="", icon=None):
        self.effectname = effect
        self.categories = categories
        self.description = description
        self.human_name = human_name
        self._icon = icon

    def getHumanName(self):
        return self.human_name

    def getDescription(self):
        return self.description

    def getCategories(self):
        return self.categories
