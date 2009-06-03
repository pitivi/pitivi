# PiTiVi , Non-linear video editor
#
#       pitivi/projectmanager.py
#
# Copyright (c) 2009, Alessandro Decina <alessandro.d@gmail.com>
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

from gettext import gettext as _
import gobject
gobject.threads_init()
import gst

from pitivi.project import Project
from pitivi.formatters.format import get_formatter_for_uri
from pitivi.signalinterface import Signallable
from pitivi.log.loggable import Loggable
from pitivi.stream import AudioStream, VideoStream
from pitivi.timeline.track import Track


class ProjectManager(Signallable, Loggable):
    __signals__ = {
        "new-project-loading": ["project"],
        "new-project-loaded": ["project"],
        "new-project-failed": ["uri", "exception"],
        "closing-project": ["project"],
        "project-closed": ["project"],
    }

    def __init__(self):
        Signallable.__init__(self)
        Loggable.__init__(self)

        self.current = None

    def loadProject(self, uri):
        """ Load the given project file"""
        formatter = get_formatter_for_uri(uri)
        if not formatter:
            self.emit("new-project-failed", uri,
                    Exception(_("Not a valid project file.")))
            return

        if not self.closeRunningProject():
            self.emit("new-project-failed", uri,
                    Exception(_("Couldn't close current project")))
            return

        project = formatter.newProject()
        self._connectToFormatter(formatter)
        # start loading the project, from now on everything is async
        formatter.loadProject(uri, project)

    def closeRunningProject(self):
        """ close the current project """
        self.info("closing running project")

        if self.current.hasUnsavedModifications():
            if not self.current.save():
                return False

        if self.emit("closing-project", self.current) == False:
            return False

        self.emit("project-closed", self.current)
        self.current.release()
        self.current = None

        return True

    def newBlankProject(self):
        """ start up a new blank project """
        # if there's a running project we must close it
        if self.current is not None and not self.closeRunningProject():
            return

        project = Project(_("New Project"))
        self.emit("new-project-loading", project)
        self.current = project

        # FIXME: this should not be hard-coded
        # add default tracks for a new project
        video = VideoStream(gst.Caps('video/x-raw-rgb; video/x-raw-yuv'))
        track = Track(video)
        project.timeline.addTrack(track)
        audio = AudioStream(gst.Caps('audio/x-raw-int; audio/x-raw-float'))
        track = Track(audio)
        project.timeline.addTrack(track)

        self.emit("new-project-loaded", self.current)


    def _connectToFormatter(self, formatter):
        formatter.connect("missing-uri", self._formatterMissingURICb)
        formatter.connect("new-project-loading",
                self._formatterNewProjectLoading)
        formatter.connect("new-project-loaded",
                self._formatterNewProjectLoaded)
        formatter.connect("new-project-failed",
                self._formatterNewProjectFailed)

    def _disconnectFromFormatter(self, formatter):
        formatter.disconnect_by_function(self._formatterMissingURICb)
        formatter.disconnect_by_function(self._formatterNewProjectLoading)
        formatter.disconnect_by_function(self._formatterNewProjectLoaded)
        formatter.disconnect_by_function(self._formatterNewProjectFailed)

    def _formatterNewProjectLoading(self, formatter, project):
        self.emit("new-project-loading", project)

    def _formatterNewProjectLoaded(self, formatter, project):
        self._disconnectFromFormatter(formatter)

        self.current = project
        self.emit("new-project-loaded", project)

    def _formatterNewProjectFailed(self, formatter, uri, exception):
        self._disconnectFromFormatter(formatter)

        self.handleException(exception)
        self.warning("error loading the project")
        self.current = None
        self.emit("new-project-failed", uri, exception)

    def _formatterMissingURICb(self, formatter, uri):
        self.emit("missing-uri", formatter, uri)
