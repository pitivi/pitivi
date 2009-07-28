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
from pitivi.formatters.base import FormatterLoadError, FormatterSaveError

from pitivi.signalinterface import Signallable
from pitivi.log.loggable import Loggable
from pitivi.stream import AudioStream, VideoStream
from pitivi.timeline.track import Track

class ProjectManager(Signallable, Loggable):
    __signals__ = {
        "new-project-loading": ["uri"],
        "new-project-created": ["project"],
        "new-project-failed": ["uri", "exception"],
        "new-project-loaded": ["project"],
        "save-project-failed": ["project", "uri", "exception"],
        "project-saved": ["project", "uri"],
        "closing-project": ["project"],
        "project-closed": ["project"],
        "missing-uri": ["formatter", "uri", "factory"],
    }

    def __init__(self):
        Signallable.__init__(self)
        Loggable.__init__(self)

        self.current = None

    def loadProject(self, uri):
        """ Load the given project file"""
        self.emit("new-project-loading", uri)

        formatter = self._getFormatterForUri(uri)
        if not formatter:
            self.emit("new-project-failed", uri,
                    FormatterLoadError(_("Not a valid project file.")))
            return

        if not self.closeRunningProject():
            self.emit("new-project-failed", uri,
                    FormatterLoadError(_("Couldn't close current project")))
            return

        self._connectToFormatter(formatter)
        # start loading the project, from now on everything is async
        formatter.loadProject(uri)

    def saveProject(self, project, uri=None, overwrite=False, formatter=None):
        """
        Save the L{Project} to the given location.

        If specified, use the given formatter.

        @type project: L{Project}
        @param project: The L{Project} to save.
        @type uri: L{str}
        @param uri: The location to store the project to. Needs to
        be an absolute URI.
        @type formatter: L{Formatter}
        @param formatter: The L{Formatter} to use to store the project if specified.
        If it is not specified, then it will be saved at its original format.
        @param overwrite: Whether to overwrite existing location.
        @type overwrite: C{bool}
        @raise FormatterSaveError: If the file couldn't be properly stored.

        @see: L{Formatter.saveProject}
        """
        if formatter is None:
            if project.format:
                formatter == project.format
            else:
                from pitivi.formatters.etree import ElementTreeFormatter
                formatter = ElementTreeFormatter()

        if uri is None:
            if project.uri is None:
                self.emit("save-project-failed", project, uri,
                        FormatterSaveError(_("No URI specified.")))
                return

            uri = project.uri

        self._connectToFormatter(formatter)
        return formatter.saveProject(project, uri, overwrite)

    def closeRunningProject(self):
        """ close the current project """
        self.info("closing running project")

        if self.current is None:
            return True

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
            return False

        # we don't have an URI here, None means we're loading a new project
        self.emit("new-project-loading", None)
        project = Project(_("New Project"))
        self.emit("new-project-created", project)
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

        return True


    def _getFormatterForUri(self, uri):
        return get_formatter_for_uri(uri)

    def _connectToFormatter(self, formatter):
        formatter.connect("missing-uri", self._formatterMissingURICb)
        formatter.connect("new-project-created",
                self._formatterNewProjectCreated)
        formatter.connect("new-project-loaded",
                self._formatterNewProjectLoaded)
        formatter.connect("new-project-failed",
                self._formatterNewProjectFailed)
        formatter.connect("save-project-failed",
                self._formatterSaveProjectFailed)
        formatter.connect("project-saved",
                self._formatterProjectSaved)

    def _disconnectFromFormatter(self, formatter):
        formatter.disconnect_by_function(self._formatterMissingURICb)
        formatter.disconnect_by_function(self._formatterNewProjectCreated)
        formatter.disconnect_by_function(self._formatterNewProjectLoaded)
        formatter.disconnect_by_function(self._formatterNewProjectFailed)
        formatter.disconnect_by_function(self._formatterSaveProjectFailed)
        formatter.disconnect_by_function(self._formatterProjectSaved)

    def _formatterNewProjectCreated(self, formatter, project):
        self.emit("new-project-created", project)

    def _formatterNewProjectLoaded(self, formatter, project):
        self._disconnectFromFormatter(formatter)

        self.current = project
        self.emit("new-project-loaded", project)

    def _formatterNewProjectFailed(self, formatter, uri, exception):
        self._disconnectFromFormatter(formatter)
        self.current = None
        self.emit("new-project-failed", uri, exception)

    def _formatterMissingURICb(self, formatter, uri, factory):
        return self.emit("missing-uri", formatter, uri, factory)

    def _formatterSaveProjectFailed(self, formatter, project, uri, exception):
        self._disconnectFromFormatter(formatter)
        self.emit("save-project-failed", project, uri, exception)

    def _formatterProjectSaved(self, formatter, project, uri):
        self._disconnectFromFormatter(formatter)
        self.emit("project-saved", project, uri)
