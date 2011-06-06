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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

from gettext import gettext as _
import gobject
gobject.threads_init()
import gst
import os

from urlparse import urlparse

from pitivi.project import Project
from pitivi.formatters.format import get_formatter_for_uri
from pitivi.formatters.base import FormatterLoadError, FormatterSaveError

from pitivi.signalinterface import Signallable
from pitivi.log.loggable import Loggable
from pitivi.stream import AudioStream, VideoStream
from pitivi.timeline.track import Track
from pitivi.undo import UndoableAction


class ProjectSettingsChanged(UndoableAction):

    def __init__(self, project, old, new):
        self.project = project
        self.oldsettings = old
        self.newsettings = new

    def do(self):
        self.project.setSettings(self.newsettings)
        self._done()

    def undo(self):
        self.project.setSettings(self.oldsettings)
        self._undone()


class ProjectLogObserver(UndoableAction):

    def __init__(self, log):
        self.log = log

    def startObserving(self, project):
        project.connect("settings-changed", self._settingsChangedCb)

    def stopObserving(self, project):
        project.disconnect_by_function(self._settingsChangedCb)

    def _settingsChangedCb(self, project, old, new):
        action = ProjectSettingsChanged(project, old, new)
        self.log.begin("change project settings")
        self.log.push(action)
        self.log.commit()


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
        "reverting-to-saved": ["project"],
    }

    def __init__(self, avalaible_effects={}):
        Signallable.__init__(self)
        Loggable.__init__(self)

        self.current = None
        self.backup_lock = 0
        self.avalaible_effects = avalaible_effects

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

    def saveProject(self, project, uri=None, overwrite=False, formatter=None, backup=False):
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
                formatter = ElementTreeFormatter(self.avalaible_effects)

        if uri is None:
            if project.uri is None:
                self.emit("save-project-failed", project, uri,
                        FormatterSaveError(_("No URI specified.")))
                return

            uri = project.uri

        self._connectToFormatter(formatter)
        return formatter.saveProject(project, uri, overwrite, backup)

    def closeRunningProject(self):
        """ close the current project """
        self.info("closing running project")

        if self.current is None:
            return True

        if not self.emit("closing-project", self.current):
            return False

        self.emit("project-closed", self.current)
        self.current.disconnect_by_function(self._projectChangedCb)
        self._cleanBackup(self.current.uri)
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
        settings = project.getSettings()
        video = VideoStream(gst.Caps(settings.getVideoCaps()))
        track = Track(video)
        project.timeline.addTrack(track)
        audio = AudioStream(gst.Caps(settings.getAudioCaps()))
        track = Track(audio)
        project.timeline.addTrack(track)
        project.connect("project-changed", self._projectChangedCb)

        self.emit("new-project-loaded", self.current)

        return True

    def revertToSavedProject(self):
        """ discard all unsaved changes and reload current open project """
        #no running project or
        #project has not been modified
        if self.current.uri is None \
           or not self.current.hasUnsavedModifications():
            return True

        if not self.emit("reverting-to-saved", self.current):
            return False
        uri = self.current.uri
        self.current.setModificationState(False)
        self.closeRunningProject()
        self.loadProject(uri)

    def _projectChangedCb(self, project):
        # The backup_lock is a timer, when a change in the project is done it is
        # set to 10 seconds. If before those 10 seconds pass an other change is done
        # 5 seconds are added in the timeout callback instead of saving the backup
        # file. The limit is 60 seconds.
        uri = project.uri
        if uri is None:
            return

        if self.backup_lock == 0:
            self.backup_lock = 10
            gobject.timeout_add_seconds(self.backup_lock,
                    self._saveBackupCb, project, uri)
        else:
            if self.backup_lock < 60:
                self.backup_lock += 5

    def _saveBackupCb(self, project, uri):
        backup_uri = self._makeBackupURI(uri)

        if self.backup_lock > 10:
            self.backup_lock -= 5
            return True
        else:
            self.saveProject(project, backup_uri, overwrite=True, backup=True)
            self.backup_lock = 0
        return False

    def _cleanBackup(self, uri):
        if uri is None:
            return

        location = self._makeBackupURI(uri)
        path = urlparse(location).path
        if os.path.exists(path):
            os.remove(path)

    def _makeBackupURI(self, uri):
        name, ext = os.path.splitext(uri)
        if ext == '.xptv':
            return name + "~" + ext
        return None

    def _getFormatterForUri(self, uri):
        return get_formatter_for_uri(uri, self.avalaible_effects)

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
        project.connect("project-changed", self._projectChangedCb)
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
