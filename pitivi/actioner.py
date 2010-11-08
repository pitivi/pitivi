# PiTiVi , Non-linear video editor
#
#       render.py
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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""
Rendering helpers
"""

import time
import gst

from pitivi.signalinterface import Signallable
from pitivi.log.loggable import Loggable
from pitivi.action import render_action_for_uri, ViewAction
from pitivi.factories.base import SourceFactory
from pitivi.factories.timeline import TimelineSourceFactory
from pitivi.settings import export_settings_to_render_settings
from pitivi.stream import VideoStream, AudioStream
from pitivi.utils import beautify_length

class Actioner(Loggable, Signallable):
    """ Previewer/Renderer helper methods """

    __signals__ = {
        "eos" : None,
        "error" : None
        }

    RENDERER = 0
    PREVIEWER = 1

    def __init__(self, project, pipeline=None):
        Loggable.__init__(self)
        # grab the Pipeline and settings
        self.project = project
        if pipeline != None:
            self.pipeline = pipeline
        else:
            self.pipeline = self.project.pipeline
        self.acting = False
        self.action = None
        self.settings = project.getSettings()

    def _eosCb(self, unused_pipeline):
        self.debug("eos !")
        if self.actioner != self.PREVIEWER:
            self.shutdown()
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
        if self.action == None:
            if self.actioner == self.RENDERER:
                self.pipeline.connect('position', self._positionCb)
            self.pipeline.connect('eos', self._eosCb)
            self.pipeline.connect('error', self._errorCb)
            self.debug("Setting pipeline to STOP")
            self.pipeline.stop()
            self.debug("Creating action")
            if len(self.pipeline.factories) == 0:
                sources = [self.project.factory]
            else:
                sources = [factory for factory in self.pipeline.factories
                        if isinstance(factory, SourceFactory)]
            if self.actioner == self.PREVIEWER:
                self.action = ViewAction()
                self.action.addProducers(*sources)
                self.ui.setAction(self.action)
                self.ui.setPipeline(self.pipeline)
            elif self.actioner == self.RENDERER:
                settings = export_settings_to_render_settings(self.settings,
                        self.have_video, self.have_audio)
                self.action = render_action_for_uri(self.outfile,
                        settings, *sources)
            #else:
                # BIG FAT ERROR HERE

            self.debug("setting action on pipeline")
            self.pipeline.addAction(self.action)
            self.debug("Activating action")
            self.action.activate()
            if self.actioner == self.RENDERER:
                self.debug("Setting all active ViewAction to sync=False")
                for ac in self.pipeline.actions:
                    if isinstance(ac, ViewAction) and ac.isActive():
                        ac.setSync(False)
            self.debug("Updating all sources to render settings")
            self._changeSourceSettings(self.settings)
            self.debug("setting pipeline to PAUSE")
            self.pipeline.pause()
            self.debug("done")


    def removeAction(self):
        self.debug("action %r", self.action)
        if self.action:
            self.pipeline.stop()
            self.action.deactivate()
            self.pipeline.removeAction(self.action)
            self.debug("putting all active ViewActions back to sync=True")
            for ac in self.pipeline.actions:
                if isinstance(ac, ViewAction) and ac.isActive():
                    ac.setSync(True)
            self._changeSourceSettings(self.project.getSettings())
            self.pipeline.pause()
            if self.actioner == self.RENDERER:
                self.pipeline.disconnect_by_function(self._positionCb)
            self.pipeline.disconnect_by_function(self._eosCb)
            self.pipeline.disconnect_by_function(self._errorCb)
            self.action = None

    def _startAction(self):
        self.addAction()
        self.pipeline.play()
        self.timestarted = time.time()
        self.acting = True

class Renderer(Actioner):
    """ Rendering helper methods """

    def __init__(self, project, pipeline=None, outfile=None):
        self.actioner = self.RENDERER
        Actioner.__init__(self, project, pipeline)
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
        fraction = None
        text = None
        timediff = time.time() - self.timestarted
        length = self.project.timeline.duration
        fraction = float(min(position, length)) / float(length)
        if timediff > 5.0 and position:
            # only display ETA after 5s in order to have enough averaging and
            # if the position is non-null
            totaltime = (timediff * float(length) / float(position)) - timediff
            text = beautify_length(int(totaltime * gst.SECOND))
        self.updatePosition(fraction, text)

    def updatePosition(self, fraction, text):
        pass

    def startAction(self):
        self.debug("Rendering")
        if not self.acting and self.outfile:
            self._startAction()

class Previewer(Actioner):
    """ Previewing helper methods """

    def __init__(self, project, pipeline=None, ui=None):
        self.actioner = self.PREVIEWER
        Actioner.__init__(self, project, pipeline)
        self.ui = ui

    def startAction(self):
        self.debug("Previewing")
        if not self.acting and self.ui:
            self._startAction()
