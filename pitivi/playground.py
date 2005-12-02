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
from bin import SmartBin, SmartDefaultBin, SmartFileBin#, SmartTempUriBin

class PlayGround(gobject.GObject):
    """
    Holds all the applications pipelines in a GstThread.
    They all share the same (audio,video) sink threads.
    Only one pipeline uses those sinks at any given time, but other pipelines
    can be in a PLAYED state (because they can be encoding).

    Only SmartBin can be added to the PlayGround

    Signals:
      current-changed : There's a new bin playing
      current-state : The state of the current bin has changed
    """

    __gsignals__ = {
        "current-changed" : ( gobject.SIGNAL_RUN_LAST,
                              gobject.TYPE_NONE,
                              (gobject.TYPE_PYOBJECT, )),
        "current-state" : ( gobject.SIGNAL_RUN_LAST,
                            gobject.TYPE_NONE,
                            (gobject.TYPE_PYOBJECT, )),
        "bin-added" : ( gobject.SIGNAL_RUN_LAST,
                       gobject.TYPE_NONE,
                       ( gobject.TYPE_PYOBJECT, )),
        "bin-removed" : ( gobject.SIGNAL_RUN_LAST,
                          gobject.TYPE_NONE,
                          ( gobject.TYPE_PYOBJECT, ))
        }

    # TODO
    #
    # * Only put in the thread what is being played/rendered
    #   The rest should only be remembered in the playground itself
    
    def __init__(self):
        gst.info("Starting up playground")
        gobject.GObject.__init__(self)
        # List of used pipelines
        self.pipelines = []
        
        self.vsinkthread = None
        self.asinkthread = None
        
        # Defaut pipeline if no other pipeline is playing
        self.default = SmartDefaultBin()

        # Current playing pipeline
        self.current = None
        self.currentstart = 0
        self.currentlength = 0
        self.currentpos = 0
        self.tempsmartbin = None
        self.cur_state_signal = None
        self.cur_eos_signal = None
        
        self.switch_to_default()
        self.state = gst.STATE_READY
        self.current.set_state(self.state)
        #self.playthread.set_state(self.state)

    def add_pipeline(self, pipeline):
        """ add a pipeline to the playground """
        gst.debug("pipeline : %s" % pipeline)
        if not isinstance(pipeline, SmartBin):
            return

        self.pipelines.append(pipeline)
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._bus_message_cb, pipeline)
        self.emit("bin-added", pipeline)

    def remove_pipeline(self, pipeline):
        """ removes a pipeline from the playground """
        gst.debug("pipeline : %s" % pipeline)
        if not pipeline in self.pipelines:
            return

        bus = pipeline.get_bus()
        bus.remove_signal_watch()

        pipeline.set_state(gst.STATE_READY)
        if self.current == pipeline:
            self.switch_to_default()
        self.pipelines.remove(pipeline)
        self.emit("bin-removed", pipeline)

    def switch_to_pipeline(self, pipeline):
        """
        switch to the given pipeline for play output
        """
        pipeline.debug("BEGINNING")
        if self.current == pipeline:
            return
        if not pipeline in self.pipelines and not pipeline == self.default:
            return
        if self.current:
            self.current.info("setting to READY")
            self.current.set_state(gst.STATE_READY)
            self.current.remove_audio_sink_thread()
            self.current.remove_video_sink_thread()
            if self.cur_state_signal:
                self.current.disconnect(self.cur_state_signal)
            if self.cur_eos_signal:
                self.current.disconnect(self.cur_eos_signal)
            #self.playthread.remove(self.current)
            # remove the tempsmartbin if it's the current
            if self.current == self.tempsmartbin:
                self.tempsmartbin = None

        self.current = pipeline
        self.current.set_state(gst.STATE_READY)
        if self.current.has_video and self.vsinkthread:
            #self.vsinkthread.set_state(gst.STATE_READY)
            self.current.set_video_sink_thread(self.vsinkthread)
        if self.current.has_audio and self.asinkthread:
            #self.asinkthread.set_state(gst.STATE_READY)
            self.current.set_audio_sink_thread(self.asinkthread)
        self.emit("current-changed", self.current)

        pipeline.debug("END")

    def switch_to_default(self):
        """ switch to the default pipeline """
        gst.debug("switching to default")
        self.switch_to_pipeline(self.default)

    def set_video_sink_thread(self, vsinkthread):
        """ sets the video sink thread """
        gst.debug("video sink thread : %s" % vsinkthread)
        if self.vsinkthread and self.current.has_video:
            self.current.set_state(gst.STATE_READY)
            self.current.remove_video_sink_thread()
        self.vsinkthread = vsinkthread
        if self.current and self.current.has_video:
            self.current.set_video_sink_thread(self.vsinkthread)

    def set_audio_sink_thread(self, asinkthread):
        """ sets the audio sink thread """
        gst.debug("set audio sink thread : %s" % asinkthread)
        if self.asinkthread and self.current.asinkthread:
            self.current.set_state(gst.STATE_READY)
            self.current.remove_audio_sink_thread()
        self.asinkthread = asinkthread
        if self.current and self.current.has_audio:
            self.current.set_audio_sink_thread(self.asinkthread)

    def _play_temporary_bin(self, tempbin):
        """ temporarely play a smartbin """
        gst.debug("BEGINNING tempbin : %s" % tempbin)
        self.pause()
        self.add_pipeline(tempbin)
        res = self.switch_to_pipeline(tempbin)
        if self.tempsmartbin:
            self.remove_pipeline(self.tempsmartbin)
        self.tempsmartbin = tempbin
        self.play()
        gst.debug("END tempbin : %s" % tempbin)

    def play_temporary_uri(self, uri):
        """ plays a uri """
        gst.debug("uri : %s" % uri)
        tempbin = SmartTempUriBin(uri)
        self._play_temporary_bin(tempbin)
        pass

    def play_temporary_filesourcefactory(self, factory):
        """ temporarely play a FileSourceFactory """
        gst.debug("factory : %s" % factory)
        if isinstance(self.current, SmartFileBin) and self.current.factory == factory:
            gst.info("Already playing factory : %s" % factory)
            return
        tempbin = SmartFileBin(factory)
        self._play_temporary_bin(tempbin)

    def seek_in_current(self, value, format=gst.FORMAT_TIME):
        """ seek to the given position in the current playing bin """
        gst.debug("value : %s , format : %s" % (value, format))
        if not self.current:
            return
        target = self.current

        # actual seeking
        res = target.seek(1.0, format, gst.SEEK_FLAG_FLUSH,
                          gst.SEEK_TYPE_SET, value,
                          gst.SEEK_TYPE_NONE, -1)
        if not res:
            gst.warning ("Seeking in current failed !");

        # bring back current to previous state

    #
    # Bus handler
    #
    def _bus_message_cb(self, bus, message, pipeline):
        """ handler for messages from the pipelines' buses """
        gst.info("%s [%s]" % (message.type, message.src))
        if message.src == self.current:
            if message.type == gst.MESSAGE_STATE_CHANGED:
                oldstate, newstate, pending = message.parse_state_changed()
                self.current.info("old:%s, new:%s, pending:%s" %
                                  (oldstate, newstate, pending))
                if pending == gst.STATE_VOID_PENDING:
                    self.emit("current-state", newstate)


    #
    # playing proxy functions
    #

    def play(self):
        """ play the current pipeline """
        gst.debug("play")
        if not self.current or not self.asinkthread or not self.vsinkthread:
            gst.warning("returning ???")
            return
        gst.debug("setting to play")
        self.state = gst.STATE_PLAYING
        gst.info("%s" % self.current.set_state(self.state))
##        gst.debug("set_state() done, getting state now")
##         value = self.current.get_state(None)
##        gst.debug("got_state : %s" % str(value))
 
    def pause(self):
        """ pause the current pipeline """
        gst.debug("pause")
        if not self.current or self.current == self.default:
            return
        self.state = gst.STATE_PAUSED
        self.current.set_state(self.state)

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

