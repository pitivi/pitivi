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
Project class
"""

import gst
import ges

from pitivi.utils import Seeker
from pitivi.log.loggable import Loggable
from pitivi.sourcelist import SourceList
from pitivi.settings import ExportSettings
from pitivi.signalinterface import Signallable
from pitivi.timeline.timeline import Selection


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
    @type sources: L{SourceList}
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
        self.sources = SourceList()

        self._dirty = False

        self.timeline = ges.timeline_new_audio_video()

        # We add a Selection to the timeline as there is currently
        # no such feature in GES
        self.timeline.selection = Selection()

        self.pipeline = ges.TimelinePipeline()
        self.pipeline._setUp = False
        self.pipeline.add_timeline(self.timeline)
        self.seeker = Seeker(80)

        self.settings = ExportSettings()
        self._videocaps = self.settings.getVideoCaps()

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
        @type settings: ExportSettings
        """
        assert settings
        self.log("Setting %s as the project's settings", settings)
        oldsettings = self.settings
        self.settings = settings
        self._projectSettingsChanged()
        self.emit('settings-changed', oldsettings, settings)

    #}

    #{ Save and Load features

    def setModificationState(self, state):
        self._dirty = state
        if state:
            self.emit('project-changed')

    def hasUnsavedModifications(self):
        return self._dirty

    def _projectSettingsChanged(self):
        settings = self.getSettings()
        self._videocaps = settings.getVideoCaps()

        if self.pipeline.get_state() != gst.STATE_NULL:
            self.pipeline.set_state(gst.STATE_READY)
            self.pipeline.set_state(gst.STATE_PAUSED)

    def loadSources(self):
        for layer in self.timeline.get_layers():
            for obj in layer.get_objects():
                self.sources.addUri(obj.get_uri())
