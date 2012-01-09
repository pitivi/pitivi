# PiTiVi , Non-linear video editor
#
#       pitivi/ui/system.py
#
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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.


import os

from pitivi.configure import APPNAME
from pitivi.utils.loggable import Loggable
from pitivi.signalinterface import Signallable


class System(Signallable, Loggable):
    """A base class for all *Systems
    implementing methods available in other parts of PiTiVi
    """

    __signals__ = {
        'update-power-inhibition': []
    }

    def __init__(self):
        Loggable.__init__(self)
        self.log("new object" + str(self))
        self._reset()

    def _reset(self):
        self._screensaver_keys = []
        self._sleep_keys = []

    #generic functions
    def _inhibit(self, list_, key):
        is_blocked = self._isInhibited(list_, key)

        if key == None or (not isinstance(key, str)):
            assert False

        if not key in list_:
            list_.append(key)
            self.debug("emitting 'update-power-inhibition'")
            self.emit('update-power-inhibition')

    def _uninhibit(self, list_, key):
        if key == None:
            if self._isInhibited(list_):
                list_ = []
                self.debug("emitting 'update-power-inhibition'")
                self.emit('update-power-inhibition')
        else:
            if not isinstance(key, str):
                assert False

            if key in list_:
                list_.remove(key)
                self.debug("emitting 'update-power-inhibition'")
                self.emit('update-power-inhibition')

    def _listToString(self, list_):
        keys = ""
        for key in list_:
            if keys != "":
                keys += ", "
            keys += key

        return keys

    def _isInhibited(self, list_, key=None):
        if key == None:
            if len(list_) > 0:
                return True
        elif key in list_:
            return True

        return False

    #screensaver
    def inhibitScreensaver(self, key):
        """increase screensaver inhibitor count
        @arg key: C{str} a unique translated string, giving the reason for
            inhibiting sleep
        NOTE: it is safe to call this method with a key that is already
            inhibited
        """
        self.debug("inhibitScreensaver()")
        self._inhibit(self._screensaver_keys, key)

    def uninhibitScreensaver(self, key):
        """decrease screensaver inhibitor count
        @arg key: C{str} a unique translated string, giving the reason for
            inhibiting sleep
        NOTE: it is safe to call this method with a key that is not inhibited.
        """
        self.debug("uninhibitScreensaver()")
        self._uninhibit(self._screensaver_keys, key)

    def screensaverIsInhibited(self, key=None):
        """returns True if inhibited"""
        return self._isInhibited(self._screensaver_keys, key)

    def getScreensaverInhibitors(self):
        """returns a comma seperated string of screensaver inhibitor keys"""
        return self._listToString(self._screensaver_keys)

    def screensaverIsBlockable(self):
        return False

    # sleep
    def inhibitSleep(self, key):
        """increase sleep inhibitor count
        @arg key: C{str} a unique translated string, giving the reason for
            inhibiting sleep
        NOTE: it is safe to call this method with a key that is already
            inhibited
        """
        self.debug("inhibitSleep()")
        self._inhibit(self._sleep_keys, key)

    def uninhibitSleep(self, key):
        """decrease sleep inhibitor count
        @arg key: C{str} a unique translated string, giving the reason for
            inhibiting sleep
        NOTE: it is safe to call this method with a key that is not inhibited.
        """
        self.debug("uninhibitSleep()")
        self._uninhibit(self._sleep_keys, key)

    def sleepIsInhibited(self, key=None):
        """returns true if inhibited"""
        return self._isInhibited(self._sleep_keys, key)

    def getSleepInhibitors(self):
        """returns a comma seperated string of sleep inhibitor keys"""
        return self._listToString(self._sleep_keys)

    def sleepIsBlockable(self):
        return False

    # other
    def uninhibitAll(self):
        self._reset()
        self.emit('update-power-inhibition')
        pass

    def desktopMessage(self, title, message, icon=None):
        """send a message to the desktop to be displayed to the user
        @arg title: C{str} the title of the message
        @arg message: C{str} the body of the message
        @arg icon: C{gtk.gdk.Pixbuf} icon to be shown with the message
        """
        self.debug("desktopMessage(): %s, %s" \
            % title % message)
        pass

    def desktopIsMessageable():
        return False


class FreedesktopOrgSystem(System):
    """provides messaging capabilites for desktops that implement fd.o specs"""

    def __init__(self):
        System.__init__(self)
        # FIXME Notifications disabled for the time being
        # pynotify.init(APPNAME)

    def desktopIsMesageable(self):
        return True

    def desktopMessage(self, title, message, icon=None):
        #call super method for consistent logging
        System.desktopMessage(title, message, icon)

        # FIXME Notifications disabled for the time being
        #notification = pynotify.Notification(title, message)
        #if icon != None and isinstance(icon, gtk.gdk.Pixbuf):
            #notification.set_icon_from_pixbuf(icon)
        #notification.show()


#org.gnome.SessionManager flags
INHIBIT_LOGOUT = 1
INHIBIT_USER_SWITCHING = 2
INHIBIT_SUSPEND = 4
INHIBIT_SESSION_IDLE = 8

COOKIE_NONE = 0
COOKIE_SCREENSAVER = 1
COOKIE_SLEEP = 2


class GnomeSystem(FreedesktopOrgSystem):
    def __init__(self):
        FreedesktopOrgSystem.__init__(self)
        self.bus = dbus.Bus(dbus.Bus.TYPE_SESSION)

        #connect to gnome sessionmanager
        self.sessionmanager = self.bus.get_object('org.gnome.SessionManager',
            '/org/gnome/SessionManager')
        self.session_iface = dbus.Interface(self.sessionmanager,
            'org.gnome.SessionManager')
        self.cookie = None
        self.cookie_type = COOKIE_NONE

        self.connect('update-power-inhibition', self._updatePowerInhibitionCb)

    def screensaver_is_blockable(self):
        return True

    def sleep_is_blockable(self):
        return True

    def _updatePowerInhibitionCb(self, unused_system):
        #there are two states we want the program to be in, with regards to
        #power saving, the screen saver is inhibited when the viewer is watched.
        #or we inhibit sleep/powersaving when we are processing data
        #we do things the way we do here because the viewer shows the the output
        #of the render pipeline
        self.debug("updating power inhibitors")
        toplevel_id = 0

        #inhibit power saving if we are rendering, maybe downloading a video
        if self.sleepIsInhibited():
            if self.cookie_type != COOKIE_SLEEP:
                new_cookie = self.session_iface.Inhibit(APPNAME, toplevel_id,
                    self.getSleepInhibitors(), INHIBIT_SUSPEND | INHIBIT_LOGOUT)
                if self.cookie != None:
                    self.session_iface.Uninhibit(self.cookie)
                self.cookie = new_cookie
                self.cookie_type = COOKIE_SLEEP
                self.debug("sleep inhibited")
            else:
                self.debug("sleep already inhibited")
        #inhibit screensaver if we are just watching the viewer
        elif self.screensaverIsInhibited():
            if self.cookie_type != COOKIE_SCREENSAVER:
                new_cookie = self.session_iface.Inhibit(APPNAME, toplevel_id,
                    self.getScreensaverInhibitors(), INHIBIT_SESSION_IDLE)
                if self.cookie != None:
                    self.session_iface.Uninhibit(self.cookie)
                self.cookie = new_cookie
                self.cookie_type = COOKIE_SCREENSAVER
                self.debug("screensaver inhibited")
            else:
                self.debug("screensaver already inhibited")
        #unblock everything otherwise
        else:
            if self.cookie != COOKIE_NONE:
                self.session_iface.Uninhibit(self.cookie)
                self.cookie = None
                self.cookie_type = COOKIE_NONE
                self.debug("uninhibited")
            else:
                self.debug("already uninhibited")


system_ = None

#attempts to identify the System, import dependencies and overide system_
if os.name == 'posix':
    if 'GNOME_DESKTOP_SESSION_ID' in os.environ:
        try:
            # FIXME Disable notifications for the time being as it causes
            # various errors and the implementation is not done yet
            #import pynotify
            import dbus
            system_ = GnomeSystem
        except:
            pass

    if  system_ == None:
        try:
            # FIXME Disable notifications for the time being as it causes
            # various errors and the implementation is not done yet
            # import pynotify
            system_ = FreedesktopOrgSystem
        except:
            pass
elif os.name == 'nt':
    pass
elif os.name == 'mac':
    pass


def getSystem():
    system = None
    if system_ != None:
        system = system_()

    if system == None:
        system = System()

    return system
