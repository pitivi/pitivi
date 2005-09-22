# PiTiVi , Non-linear video editor
#
#       pitivi/pitivi.py
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
import gtk
import gst
import sys
from ui import mainwindow
from discoverer import Discoverer
from playground import PlayGround
from project import Project, file_is_project
from effects import Magician

class Pitivi(gobject.GObject):
    """
    Pitivi's main class

    Signals:
      new-project : A new project has been loaded, the Project object is given
      closing-project : Pitivi wishes to close the project, callbacks return False
                if they don't want the project to be closed, True otherwise
      not-project : The given uri is not a project file

    """
    __gsignals__ = {
        "new-project" : ( gobject.SIGNAL_RUN_LAST,
                          gobject.TYPE_NONE,
                          (gobject.TYPE_PYOBJECT, )),
        "closing-project" : ( gobject.SIGNAL_RUN_LAST,
                              gobject.TYPE_BOOLEAN,
                              (gobject.TYPE_PYOBJECT, )),
        "not-project" : ( gobject.SIGNAL_RUN_LAST,
                          gobject.TYPE_NONE,
                          (gobject.TYPE_STRING, ))
        }

    project = None

    def __init__(self, *args):
        """
        initialize pitivi with the command line arguments
        """
        gst.info("starting up pitivi...")
        gobject.GObject.__init__(self)
        # TODO parse cmd line arguments
        self.playground = PlayGround()
        self.current = Project("New Project")
        self.effects = Magician(self)
        
        # we're starting a GUI for the time being
        self.gui = mainwindow.PitiviMainWindow(self)
        self.gui.show()

    def load_project(self, uri=None, filepath=None):
        """ Load the given file through it's uri or filepath """
        gst.info("uri:%s, filepath:%s" % (uri, filepath))
        if not uri and not filepath:
            self.emit("not-project", "")
            return
        if filepath:
            uri = "file://" + filepath
        # is the given filepath a valid pitivi project
        if not file_is_project(uri):
            self.emit("not-project", uri)
            return
        # if current project, try to close it
        if self._close_running_project():
            self.current = Project(uri)
            self.emit("new-project", self.current)

    def _close_running_project(self):
        """ close the current project """
        gst.info("closing running project")
        if self.current:
            if not self.emit("closing-project", self.current):
                return False
            self.playground.pause()
            self.current = None
        return True
        
    def new_blank_project(self):
        """ start up a new blank project """
        # if there's a running project we must close it
        if self._close_running_project():
            self.playground.pause()
            self.current = Project("New Project")
            self.emit("new-project", self.current)
        
gobject.type_register(Pitivi)

def main(argv):
    ptv = Pitivi(argv)
    gtk.main()
