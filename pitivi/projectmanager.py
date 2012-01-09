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

import gobject
import os
import ges
import gio

from gettext import gettext as _
from urlparse import urlparse
from pwd import getpwuid

from pitivi.project import Project
from pitivi.signalinterface import Signallable
from pitivi.log.loggable import Loggable
from pitivi.undo.undo import UndoableAction


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
        self.formatter = None

    def loadProject(self, uri):

        """ Load the given project file"""
        self.emit("new-project-loading", uri)

        self.current = Project(uri=uri)

        self.timeline = self.current.timeline
        self.formatter = ges.PitiviFormatter()

        self.formatter.connect("source-moved", self._formatterMissingURICb)
        self.formatter.connect("loaded", self._projectLoadedCb)
        if self.formatter.load_from_uri(self.timeline, uri):
            self.current.connect("project-changed", self._projectChangedCb)

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
            formatter = ges.PitiviFormatter()

        if uri is None:
            uri = project.uri

        if uri is None or not ges.formatter_can_save_uri(uri):
            self.emit("save-project-failed", project, uri)
            return

        # FIXME Using query_exist is not the best thing to do, but makes
        # the trick for now
        file = gio.File(uri)
        if overwrite or not file.query_exist():
            formatter.set_sources(project.sources.getSources())
            return formatter.save_to_uri(project.timeline, uri)

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

    def newBlankProject(self, emission=True):
        """ start up a new blank project """
        # if there's a running project we must close it
        if self.current is not None and not self.closeRunningProject():
            return False

        # we don't have an URI here, None means we're loading a new project
        if emission:
            self.emit("new-project-loading", None)
        project = Project(_("New Project"))

        # setting default values for project metadata
        project.author = getpwuid(os.getuid()).pw_gecos.split(",")[0]

        self.emit("new-project-created", project)
        self.current = project

        # Add default tracks to the timeline of the new project.
        # The tracks of the timeline determine what tracks
        # the rendered content will have. Pitivi currently supports
        # projects with exactly one video track and one audio track.
        settings = project.getSettings()
        project.connect("project-changed", self._projectChangedCb)
        if emission:
            self.current.disconnect = False
        else:
            self.current.disconnect = True
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
            return name + ext + "~"
        return None

    def _formatterMissingURICb(self, formatter, tfs):
        return self.emit("missing-uri", formatter, tfs)

    def _projectLoadedCb(self, formatter, timeline):
        self.debug("Project Loaded")
        self.emit("new-project-loaded", self.current)
        self.current.sources.addUris(self.formatter.get_sources())
