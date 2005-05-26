#!/usr/bin/python
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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import os
import gobject
import gst
import gnome.vfs
from timeline import Timeline
from sourcelist import SourceList
from bin import SmartTimelineBin

class Project(gobject.GObject):
    """ The base class for PiTiVi projects """

    name = ""
    settings = None
    description = ""
    uri = None
    sources = None
    settings = None
    timeline = None
    timelinebin = None

    def __init__(self, name="", uri=None):
        """
        name : the name of the project
        uri : the uri of the project
        """
        gobject.GObject.__init__(self)
        self.name = name
        self.uri = uri
        self.sources = SourceList(self)
        self.settings = ProjectSettings(self)
        self._load()

    def _load(self):
        """ loads the project from a file """
        if self.timeline:
            return
        self.timeline = Timeline(self)
        if self.uri:
            if not gnome.vfs.exists(uri):
                # given uri doesn't exist !!!
                # TODO raise exception
                return
            # TODO fill the timeline from the uri
            pass

    def get_bin(self):
        """ returns the SmartTimelineBin of the project """
        if not self.timeline:
            return None
        if not self.timelinebin:
            self.timelinebin = SmartTimelineBin(self)
        return self.timelinebin

    def _save(self, filename):
        """ internal save function """
        # TODO
        pass

    def save(self):
        """ Saves the project to the project's current file """
        self._save(self, self.filename)

    def save_as(self, filename):
        """ Saves the project to the given file name """
        self._save(self, filename)
        
gobject.type_register(Project)

class ProjectSettings(gobject.GObject):
    __gsignals__ = {
        "settings-changed" : ( gobject.SIGNAL_RUN_LAST,
                              gobject.TYPE_NONE,
                              (  )),
        "encoders-changed" : ( gobject.SIGNAL_RUN_LAST,
                               gobject.TYPE_NONE,
                               ( ))
        }

    # TODO
    # Audio/Video settings for the project

    def __init__(self, project):
        gobject.GObject.__init__(self)
        self.project = project
        self.videowidth = 720
        self.videoheight = 576
        self.videorate = 25.0
        self.audiochannels = 2
        self.audiorate = 44100
        self.audiodepth = 16
        self.vencoder = "theoraenc"
        self.aencoder = "rawvorbisenc"
        self.muxer = "oggmux"
        self.muxers = available_muxers()
        self.vencoders = available_video_encoders()
        self.aencoders = available_audio_encoders()

    def set_video_properties(self, width=-1, height=-1, framerate=-1):
        print "set_video_props", width, height, framerate
        changed = False
        if not width == -1 and not width == self.videowidth:
            self.videowidth = width
            changed = True
        if not height == -1 and not height == self.videoheight:
            self.videoheight = height
            changed = True
        if not framerate == -1 and not framerate == self.videorate:
            self.videorate = framerate
            changed = True
        if changed:
            self.emit("settings-changed")

    def set_audio_properties(self, nbchanns=-1, rate=-1, depth=-1):
        print "set_audio_props", nbchanns, rate, depth
        changed = False
        if not nbchanns == -1 and not nbchanns == self.audiochannels:
            self.audiochannels = nbchanns
            changed = True
        if not rate == -1 and not rate == self.audiorate:
            self.audiorate = rate
            changed = True
        if not depth == -1 and not depth == self.audiodepth:
            self.audiodepth = depth
            changed = True
        if changed:
            self.emit("settings-changed")

    def set_encoders(self, muxer="", vencoder="", aencoder=""):
        changed = False
        if not muxer == "" and not muxer == self.muxer:
            self.muxer = muxer
            changed = True
        if not vencoder == "" and not vencoder == self.vencoder:
            self.vencoder = vencoder
            changed = True
        if not aencoder == "" and not aencoder == self.aencoder:
            self.aencoder = aencoder
            changed = True
        if changed:
            self.emit("encoders-changed")

gobject.type_register(ProjectSettings)

def file_is_project(uri):
    """ returns True if the given uri is a PitiviProject file"""
    # TODO
    return gnome.vfs.exists(uri)

def available_muxers():
    """ return all available muxers """
    flist = gst.registry_pool_feature_list(gst.ElementFactory)
    res = []
    for fact in flist:
        if "Codec/Muxer" == fact.get_klass():
            res.append(fact)
    return res

def available_video_encoders():
    """ returns all available video encoders """
    flist = gst.registry_pool_feature_list(gst.ElementFactory)
    res = []
    for fact in flist:
        if "Codec/Encoder/Video" in fact.get_klass():
            res.append(fact)
    return res

def available_audio_encoders():
    """ returns all available audio encoders """
    flist = gst.registry_pool_feature_list(gst.ElementFactory)
    res = []
    for fact in flist:
        if "Codec/Encoder/Audio" in fact.get_klass():
            res.append(fact)
    return res

def encoders_muxer_compatible(encoders, muxer):
    """ returns the list of encoders compatible with the given muxer """
    res = []
    for encoder in encoders:
        for caps in [x.get_caps() for x in encoder.get_pad_templates() if x.direction == gst.PAD_SRC]:
            if muxer.can_sink_caps(caps):
                res.append(encoder)
                break
    return res
