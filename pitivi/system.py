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


from pitivi.log.loggable import Loggable
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

    def desktopMessage(title, message, icon=None):
        """send a message to the desktop to be displayed to the user
        @arg title: C{str} the title of the message
        @arg message: C{str} the body of the message
        @arg icon: C{gtk.gdk.Pixbuf} icon to be shown with the message
        """
        self.debug("desktopMessage(): %s, %s" \
            % key % message)
        pass

    def desktopIsMessageable():
        return False

