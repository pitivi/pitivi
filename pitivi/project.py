# PiTiVi , Non-linear video editor
#
#       project.py
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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

"""
Project related classes
"""

import ges
import gst

from pitivi.utils.playback import Seeker
from pitivi.utils.loggable import Loggable
from pitivi.medialibrary import MediaLibrary
from pitivi.settings import MultimediaSettings
from pitivi.utils.signal import Signallable
from pitivi.utils.timeline import Selection

import gobject
import os
import gio

from gettext import gettext as _
from urlparse import urlparse
from pwd import getpwuid

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


class ProjectError(Exception):
    """Project error"""
    pass


class Project(Signallable, Loggable):
    """The base class for PiTiVi projects

    @ivar name: The name of the project
    @type name: C{str}
    @ivar description: A description of the project
    @type description: C{str}
    @ivar sources: The sources used by this project
    @type sources: L{MediaLibrary}
    @ivar timeline: The timeline
    @type timeline: L{ges.Timeline}
    @ivar pipeline: The timeline's pipeline
    @type pipeline: L{ges.Pipeline}
    @ivar format: The format under which the project is currently stored.
    @type format: L{FormatterClass}
    @ivar loaded: Whether the project is fully loaded or not.
    @type loaded: C{bool}

    Signals:
     - C{loaded} : The project is now fully loaded.
    """

    __signals__ = {
        "settings-changed": ['old', 'new'],
        "project-changed": [],
        "selected-changed": ['element']
        }

    def __init__(self, name="", uri=None, **kwargs):
        """
        @param name: the name of the project
        @param uri: the uri of the project
        """
        Loggable.__init__(self)
        self.log("name:%s, uri:%s", name, uri)
        self.name = name
        self.author = ""
        self.year = ""
        self.settings = None
        self.description = ""
        self.uri = uri
        self.urichanged = False
        self.format = None
        self.sources = MediaLibrary()

        self._dirty = False

        self.timeline = ges.timeline_new_audio_video()

        # We add a Selection to the timeline as there is currently
        # no such feature in GES
        self.timeline.selection = Selection()

        self.pipeline = ges.TimelinePipeline()
        self.pipeline.add_timeline(self.timeline)
        self.seeker = Seeker(80)

        self.settings = MultimediaSettings()

    def getUri(self):
        return self._uri

    def setUri(self, uri):
        # FIXME support not local project
        if uri and not gst.uri_has_protocol(uri, "file"):
            self._uri = gst.uri_construct("file", uri)
        else:
            self._uri = uri

    uri = property(getUri, setUri)

    def release(self):
        self.pipeline = None

    #{ Settings methods

    def getSettings(self):
        """
        return the currently configured settings.
        """
        self.debug("self.settings %s", self.settings)
        return self.settings

    def setSettings(self, settings):
        """
        Sets the given settings as the project's settings.
        @param settings: The new settings for the project.
        @type settings: MultimediaSettings
        """
        assert settings
        self.log("Setting %s as the project's settings", settings)
        oldsettings = self.settings
        self.settings = settings
        self.emit('settings-changed', oldsettings, settings)
        self.seeker.flush()

    #}

    #{ Save and Load features

    def setModificationState(self, state):
        self._dirty = state
        if state:
            self.emit('project-changed')

    def hasUnsavedModifications(self):
        return self._dirty
