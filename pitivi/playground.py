#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       playground.py
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
import gst
from bin import SmartBin, SmartDefaultBin, SmartFileBin, SmartTempUriBin

class PlayGround(gobject.GObject):
    """
    Holds all the applications pipelines in a GstThread.
    They all share the same (audio,video) sink threads.
    Only one pipeline uses those sinks at any given time, but other pipelines
    can be in a PLAYED state (because they can be encoding).

    Only SmartBin can be added to the PlayGround
    """

    __gsignals__ = {
        "current-changed" : ( gobject.SIGNAL_RUN_LAST,
                              gobject.TYPE_NONE,
                              (gobject.TYPE_PYOBJECT, )),
        }
    
    def __init__(self):
        gobject.GObject.__init__(self)
        self.pipelines = []
        self.playthread = gst.Thread("playground")
        self.vsinkthread = None
        self.asinkthread = None
        self.default = SmartDefaultBin()
        self.current = self.default
        self.playthread.add(self.default)
        self.currentstart = 0
        self.currentlength = 0
        self.currentpos = 0
        self.tempsmartbin = None
        self.state = gst.STATE_READY

    def add_pipeline(self, pipeline):
        """ add a pipeline to the playground """
        print "adding pipeline to playground"
        if not isinstance(pipeline, SmartBin):
            return
        self.playthread.add(pipeline)
        self.pipelines.append(pipeline)

    def remove_pipeline(self, pipeline):
        """ removes a pipeline from the playground """
        print "removing pipeline from playground"
        if not pipeline in self.pipelines:
            return
        pipeline.set_state(gst.STATE_READY)
        if self.current == pipeline:
            self.switch_to_default()
        self.playthread.remove(pipeline)
        self.pipelines.remove(pipeline)

    def switch_to_pipeline(self, pipeline):
        """ switch to the given pipeline for play output """
        # remove the tempsmartbin if it's the current
        print "switching to another pipeline"
        if self.current == pipeline:
            return
        if not pipeline in self.pipelines and not pipeline == self.default:
            return
        self.current.set_state(gst.STATE_READY)
        self.current.remove_audio_sink_thread()
        self.current.remove_video_sink_thread()
        if self.current and self.current == self.tempsmartbin:
            self.playthread.remove(self.current)
            self.tempsmartbin = None
        self.current = pipeline
        self.current.set_state(gst.STATE_READY)
        self.current.set_video_sink_thread(self.vsinkthread)
        self.current.set_audio_sink_thread(self.asinkthread)
        self.emit("current-changed", self.current)
        self.current.set_state(gst.STATE_PAUSED)

    def switch_to_default(self):
        """ switch to the default pipeline """
        print "switching to default"
        self.switch_to_pipeline(self.default)
        self.default.set_state(gst.STATE_PLAYING)

    def set_video_sink_thread(self, vsinkthread):
        """ sets the video sink thread """
        print "set video sink thread"
        if self.vsinkthread and self.current:
            self.current.set_state(gst.STATE_READY)
            self.current.remove_video_sink_thread()
        self.vsinkthread = vsinkthread
        if self.current:
            self.current.set_video_sink_thread(self.vsinkthread)

    def set_audio_sink_thread(self, asinkthread):
        """ sets the audio sink thread """
        print "set audio sink thread"
        if self.asinkthread and self.current:
            self.current.set_state(gst.STATE_READY)
            self.current.remove_audio_sink_thread()
        self.asinkthread = asinkthread
        if self.current:
            self.current.set_audio_sink_thread(self.asinkthread)
        print "finished setting audio sink thread"

    def _play_temporary_bin(self, tempbin):
        """ temporarely play a smartbin """
        self.pause()
        self.add_pipeline(tempbin)
        self.switch_to_pipeline(tempbin)
        if self.tempsmartbin:
            self.remove_pipeline(self.tempsmartbin)
        self.tempsmartbin = tempbin
        self.play()        

    def play_temporary_uri(self, uri):
        """ plays a uri """
        tempbin = SmartTempUriBin(uri)
        self._play_temporary_bin(tempbin)
        pass

    def play_temporary_filesourcefactory(self, factory):
        """ temporarely play a FileSourceFactory """
        if isinstance(self.current, SmartFileBin) and self.current.factory == factory:
            return
        tempbin = SmartFileBin(factory)
        self._play_temporary_bin(tempbin)

    def set_video_output_window_id(self, windowid):
        """ sets the X window id where to output the video """
        pass

    #
    # playing proxy functions
    #

    def play(self):
        """ play the current pipeline """
        print "setting playground to play"
        if not self.current:
            return
        if not self.state == gst.STATE_PLAYING:
            self.current.set_state(gst.STATE_PLAYING)
            self.state = gst.STATE_PLAYING

    def pause(self):
        """ pause the current pipeline """
        print "setting playground to pause"
        if not self.current:
            return
        if not self.state == gst.STATE_PAUSED:
            self.current.set_state(gst.STATE_PAUSED)
            self.state = gst.STATE_PAUSED

    def fast_forward(self):
        """ fast forward the current pipeline """
        pass

    def rewind(self):
        """ play the current pipeline backwards """
        pass

    def forward_one(self):
        """ forward the current pipeline by one video frame """
        pass

    def backward_one(self):
        """ rewind the current pipeline by one video frame """
        pass

    def seek(self, time):
        """ seek in the current pipeline """
        pass

gobject.type_register(PlayGround)
