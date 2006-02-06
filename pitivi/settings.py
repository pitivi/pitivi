#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       settings.py
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


class ExportSettings(gobject.GObject):
    __gsignals__ = {
        "settings-changed" : ( gobject.SIGNAL_RUN_LAST,
                              gobject.TYPE_NONE,
                              (  )),
        "encoders-changed" : ( gobject.SIGNAL_RUN_LAST,
                               gobject.TYPE_NONE,
                               ( ))
        }

    # Audio/Video settings for processing/export

    def __init__(self):
        gobject.GObject.__init__(self)
        self.videowidth = 720
        self.videoheight = 576
        self.videorate = 25.0
        self.audiochannels = 2
        self.audiorate = 44100
        self.audiodepth = 16
        self.vencoder = "theoraenc"
        self.aencoder = "vorbisenc"
        self.muxer = "oggmux"
        self.containersettings = {}
        self.acodecsettings = {}
        self.vcodecsettings = {}
        self.muxers = available_muxers()
        self.vencoders = available_video_encoders()
        self.aencoders = available_audio_encoders()

    def __str__(self):
        msg = "Export Settings\n"
        msg += "Video :" + str(self.videowidth) + " " + str(self.videoheight) + " " + str(self.videorate)
        msg += "\n\t" + str(self.vencoder) + " " +str(self.vcodecsettings)
        msg += "\nAudio :" + str(self.audiochannels) + " " + str(self.audiorate) + " " + str(self.audiodepth)
        msg += "\n\t" + str(self.aencoder) + " " + str(self.acodecsettings)
        msg += "\nMuxer :" + str(self.muxer) + " " + str(self.containersettings)
        return msg

    def set_video_properties(self, width=-1, height=-1, framerate=-1):
        gst.info("set_video_props %d x %d @ %f fps" % (width, height, framerate))
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
        gst.info("%d x %dHz %dbits" % (nbchanns, rate, depth))
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


def available_muxers():
    """ return all available muxers """
    flist = gst.registry_get_default().get_feature_list(gst.ElementFactory)
    res = []
    for fact in flist:
        if "Codec/Muxer" == fact.get_klass():
            res.append(fact)
    gst.log(str(res))
    return res

def available_video_encoders():
    """ returns all available video encoders """
    flist = gst.registry_get_default().get_feature_list(gst.ElementFactory)
    res = []
    for fact in flist:
        if "Codec/Encoder/Video" in fact.get_klass():
            res.append(fact)
    gst.log(str(res))
    return res

def available_audio_encoders():
    """ returns all available audio encoders """
    flist = gst.registry_get_default().get_feature_list(gst.ElementFactory)
    res = []
    for fact in flist:
        if "Codec/Encoder/Audio" in fact.get_klass():
            res.append(fact)
    gst.log(str(res))
    return res

def encoders_muxer_compatible(encoders, muxer):
    """ returns the list of encoders compatible with the given muxer """
    gst.info("")
    res = []
    for encoder in encoders:
        for caps in [x.get_caps() for x in encoder.get_static_pad_templates() if x.direction == gst.PAD_SRC]:
            if muxer.can_sink_caps(caps):
                res.append(encoder)
                break
    return res
