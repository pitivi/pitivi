# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2010, Stephen Griffiths <scgmk5@gmail.com>
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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
"""Logic for checking the system features availability."""
import datetime
import multiprocessing
import os
import resource
import sys

from gi.repository import GObject

from pitivi.check import MISSING_SOFT_DEPS
from pitivi.configure import APPNAME
from pitivi.utils.loggable import Loggable


class System(GObject.Object, Loggable):
    """A base class for systems in which Pitivi runs."""

    def __init__(self):
        GObject.Object.__init__(self)
        Loggable.__init__(self)
        self.log("new object %s", self)

        self._x11 = False
        try:
            # pylint: disable=unused-import
            from gi.repository import GdkX11
            self._x11 = True
        except ImportError:
            pass

    def has_x11(self):
        return self._x11

    def desktop_message(self, title, message, icon=None):
        """Sends a message to the desktop to be displayed to the user.

        Args:
            title (str): The title of the message.
            message (str): The body of the message.
            icon (str): The icon to be shown with the message
        """
        self.debug("%s, %s, %s", title, message, icon)

    def get_unique_filename(self, string):
        """Gets a filename which can only be obtained from the specified string.

        Args:
            string (str): The string identifying the filename.

        Returns:
            str: A filename which looks like the specified string.
        """
        return string.replace("%", "%37").replace("/", "%47")


class FreedesktopOrgSystem(System):
    """Provides messaging capabilities for desktops that implement fd.o specs."""

    def __init__(self):
        System.__init__(self)
        if "Notify" not in MISSING_SOFT_DEPS:
            from gi.repository import Notify
            Notify.init(APPNAME)

    def desktop_message(self, title, message, icon="pitivi"):
        # call super method for consistent logging
        System.desktop_message(self, title, message, icon)

        if "Notify" not in MISSING_SOFT_DEPS:
            from gi.repository import Notify
            notification = Notify.Notification.new(title, message, icon=icon)
            try:
                notification.show()
            except RuntimeError as e:
                # This can happen if the system is not properly configured.
                # See for example
                # https://bugzilla.gnome.org/show_bug.cgi?id=719627.
                self.error(
                    "Failed displaying notification: %s", e.message)
                return None
            return notification
        return None


class GnomeSystem(FreedesktopOrgSystem):
    """GNOME."""

    def __init__(self):
        FreedesktopOrgSystem.__init__(self)


class DarwinSystem(System):
    """Apple OS X."""

    def __init__(self):
        System.__init__(self)


class WindowsSystem(System):
    """Microsoft Windows."""

    def __init__(self):
        System.__init__(self)


def get_system():
    """Creates a System object.

    Returns:
        System: A System object.
    """
    if os.name == 'posix':
        if sys.platform == 'darwin':
            return DarwinSystem()

        if 'GNOME_DESKTOP_SESSION_ID' in os.environ:
            return GnomeSystem()
        return FreedesktopOrgSystem()
    if os.name == 'nt':
        return WindowsSystem()
    return System()


class CPUUsageTracker:

    def __init__(self):
        self.reset()

    def usage(self):
        delta_time = (datetime.datetime.now() - self.last_moment).total_seconds()
        delta_usage = resource.getrusage(
            resource.RUSAGE_SELF).ru_utime - self.last_usage.ru_utime
        usage = float(delta_usage) / delta_time * 100
        return usage / multiprocessing.cpu_count()

    def reset(self):
        self.last_moment = datetime.datetime.now()
        self.last_usage = resource.getrusage(resource.RUSAGE_SELF)
