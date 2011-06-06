# PiTiVi , Non-linear video editor
#
#       pitivi/actioner.py
#
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
# Copyright (c) 2010, Robert Swain <rob@opendot.cl>
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
Rendering helpers
"""

import time
import gst

from pitivi.action import RenderAction, ViewAction
from pitivi.encode import RenderFactory, RenderSinkFactory
from pitivi.factories.base import SourceFactory
from pitivi.factories.file import URISinkFactory
from pitivi.factories.timeline import TimelineSourceFactory
from pitivi.log.loggable import Loggable
from pitivi.settings import export_settings_to_render_settings
from pitivi.signalinterface import Signallable
from pitivi.stream import AudioStream, VideoStream
from pitivi.utils import beautify_ETA


class Actioner(Loggable, Signallable):
    """ Previewer/Renderer helper methods """

    __signals__ = {
        "eos": None,
        "error": None
        }

    def __init__(self, project, pipeline=None, settings=None):
        Loggable.__init__(self)
        # grab the Pipeline and settings
        self.project = project
        if pipeline != None:
            self.pipeline = pipeline
        else:
            self.pipeline = self.project.pipeline
        self.acting = False
        self.action = None
        if settings:
            self.settings = settings
        else:
            self.settings = project.getSettings()
        self.timestarted = 0

    def _eosCb(self, unused_pipeline):
        self.debug("eos !")
        self.emit("eos")

    def shutdown(self):
        self.acting = False
        self.updateUIOnEOS()
        self.removeAction()

    def updateUIOnEOS(self):
        pass

    def _errorCb(self, pipeline, error, detail):
        self.debug("error !")
        self.acting = False
        self.updateUIOnError()
        self.removeAction()
        self.emit("error")

    def updateUIOnError(self):
        pass

    def _changeSourceSettings(self, settings):
        videocaps = settings.getVideoCaps()
        for source in self.project.sources.getSources():
            source.setFilterCaps(videocaps)

    def addAction(self):
        self.debug("action %r", self.action)
        if self.action:
            return
        self._connectFunctions()
        self.debug("Setting pipeline to STOP")
        self.pipeline.stop()
        self.debug("Creating action")
        sources = self._getSources()
        self.action = self._createAction(sources)

        self.debug("Setting action on pipeline")
        self.pipeline.addAction(self.action)
        self.debug("Activating action")
        self._activateAction()
        self.debug("Updating all sources to render settings")
        self._changeSourceSettings(self.settings)
        self.debug("Setting pipeline to PAUSE")
        self.pipeline.pause()
        self.debug("Done")

    def _getSources(self):
        if not self.pipeline.factories:
            return [self.project.factory]
        return [factory
                for factory in self.pipeline.factories
                if isinstance(factory, SourceFactory)]

    def _connectFunctions(self):
        self.pipeline.connect('eos', self._eosCb)
        self.pipeline.connect('error', self._errorCb)

    def _disconnectFunctions(self):
        self.pipeline.disconnect_by_function(self._eosCb)
        self.pipeline.disconnect_by_function(self._errorCb)

    def _activateAction(self):
        self.action.activate()

    def removeAction(self):
        self.debug("action %r", self.action)
        if not self.action:
            return
        self.pipeline.stop()
        self.action.deactivate()
        self.pipeline.removeAction(self.action)
        self.debug("putting all active ViewActions back to sync=True")
        for ac in self.pipeline.actions:
            if isinstance(ac, ViewAction) and ac.isActive():
                ac.setSync(True)
        self._changeSourceSettings(self.project.getSettings())
        self.pipeline.pause()
        self._disconnectFunctions()
        self.action = None

    def startAction(self):
        if not self._isReady():
            return
        self.addAction()
        self.pipeline.play()
        self.timestarted = time.time()
        self.acting = True

    def _isReady(self):
        """ Whether the @action can be started """
        raise NotImplementedError()

    def _createAction(self, sources):
        """ Create the @action for this Actioner

        @param sources: The source factories
        @type sources: L{SourceFactory}
        """
        raise NotImplementedError()


class Renderer(Actioner):
    """ Rendering helper methods """

    def __init__(self, project, pipeline=None, settings=None, outfile=None):
        """
        @param settings: The export settings to be used, or None to use
        the default export settings of the project.
        @type settings: ExportSettings
        @param outfile: The destination URI
        @type outfile: C{URI}
        """
        Actioner.__init__(self, project, pipeline, settings)
        self.detectStreamTypes()
        self.outfile = outfile

    def detectStreamTypes(self):
        self.have_video = False
        self.have_audio = False

        # we can only render TimelineSourceFactory
        if len(self.pipeline.factories) == 0:
            timeline_source = self.project.factory
        else:
            sources = [factory for factory in self.pipeline.factories.keys()
                    if isinstance(factory, SourceFactory)]
            timeline_source = sources[0]
        assert isinstance(timeline_source, TimelineSourceFactory)

        for track in timeline_source.timeline.tracks:
            if isinstance(track.stream, AudioStream) and track.duration > 0:
                self.have_audio = True
            elif isinstance(track.stream, VideoStream) and \
                    track.duration > 0:
                self.have_video = True

    def _positionCb(self, unused_pipeline, position):
        self.debug("%r %r", unused_pipeline, position)
        text = None
        timediff = time.time() - self.timestarted
        length = self.project.timeline.duration
        fraction = float(min(position, length)) / float(length)
        if timediff > 5.0 and position:
            # only display ETA after 5s in order to have enough averaging and
            # if the position is non-null
            totaltime = (timediff * float(length) / float(position)) - timediff
            text = beautify_ETA(int(totaltime * gst.SECOND))
        self.updatePosition(fraction, text)

    def updatePosition(self, fraction, text):
        pass

    def _isReady(self):
        return bool(not self.acting and self.outfile)

    def _eosCb(self, unused_pipeline):
        self.shutdown()
        Actioner._eosCb(self, unused_pipeline)

    def _createAction(self, sources):
        """Creates a L{RenderAction}."""
        settings = export_settings_to_render_settings(self.settings,
                self.have_video, self.have_audio)
        sf = RenderSinkFactory(RenderFactory(settings=settings),
                               URISinkFactory(uri=self.outfile))
        a = RenderAction()
        a.addProducers(*sources)
        a.addConsumers(sf)

        return a

    def _connectFunctions(self):
        self.pipeline.connect('position', self._positionCb)
        Actioner._connectFunctions(self)

    def _disconnectFunctions(self):
        self.pipeline.disconnect_by_function(self._positionCb)
        Actioner._disconnectFunctions(self)

    def _activateAction(self):
        Actioner._activateAction(self)
        self.debug("Setting all active ViewAction to sync=False")
        for action in self.pipeline.actions:
            if isinstance(action, ViewAction) and action.isActive():
                action.setSync(False)


class Previewer(Actioner):
    """ Previewing helper methods """

    def __init__(self, project, pipeline=None, ui=None):
        Actioner.__init__(self, project, pipeline=pipeline)
        self.ui = ui

    def _isReady(self):
        return bool(not self.acting and self.ui)

    def _createAction(self, sources):
        action = ViewAction()
        action.addProducers(*sources)
        self.ui.setAction(action)
        self.ui.setPipeline(self.pipeline)
        return action
