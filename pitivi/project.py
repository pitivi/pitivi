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

from pitivi.log.loggable import Loggable
from pitivi.timeline.timeline import Timeline
from pitivi.pipeline import Pipeline
from pitivi.factories.timeline import TimelineSourceFactory
from pitivi.sourcelist import SourceList
from pitivi.settings import ExportSettings
from pitivi.signalinterface import Signallable
from pitivi.action import ViewAction
from pitivi.utils import Seeker
import gst


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
    @type timeline: L{Timeline}
    @ivar pipeline: The timeline's pipeline
    @type pipeline: L{Pipeline}
    @ivar factory: The timeline factory
    @type factory: L{TimelineSourceFactory}
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
        self.sources.connect("source-added", self._sourceAddedCb)
        self.sources.connect("source-removed", self._sourceRemovedCb)

        self._dirty = False

        self.timeline = Timeline()

        self.factory = TimelineSourceFactory(self.timeline)
        self.pipeline = Pipeline()
        self.view_action = ViewAction()
        self.view_action.addProducers(self.factory)
        self.seeker = Seeker(80)

        self.settings = ExportSettings()
        self._videocaps = self.settings.getVideoCaps()

    def release(self):
        self.pipeline.release()
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
        if self.timeline:
            self.timeline.updateVideoCaps(self._videocaps)

        for fact in self.sources.getSources():
            fact.setFilterCaps(self._videocaps)
        if self.pipeline.getState() != gst.STATE_NULL:
            self.pipeline.stop()
            self.pipeline.pause()

    def _sourceAddedCb(self, sourcelist, factory):
        factory.setFilterCaps(self._videocaps)

    def _sourceRemovedCb(self, sourclist, uri, factory):
        self.timeline.removeFactory(factory)
