#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       device.py
#
# Copyright (c) 2008, Edward Hervey <bilboed@bilboed.com>
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
Classes and Methods for Device handling and usage
"""

from objectfactory import SourceFactory

(AUDIO_DEVICE,
 VIDEO_DEVICE,
 UNKNOWN_MEDIA_DEVICE) = range(3)

(SOURCE_DEVICE,
 SINK_DEVICE,
 UNKNOWN_DIRECTION_DEVICE) = range(3)

# A device can be categorized as follows:
# Media type handled:
# * audio
# * video
# * unkown ?
#
# Direction:
# * source : produces data
# * sink : consumes data
#

class DeviceProbe(object):
    """
    Allows listing of the various devices available.

    It can also signal devices (dis)appearing.

    This should be subclassed
    """

    def __init__(self):
        pass

    def getSourceDevices(self, media_type):
        """ Returns a list of available SourceDeviceFactory for
        the given mediatype
        """
        raise NotImplementedError

    def getSinkDevices(self, media_type):
        """ Returns a list of available SinkDeviceFactory for
        the given mediatype
        """
        raise NotImplementedError

class HalDeviceProbe(DeviceProbe):
    """
    Probes for devices using HAL
    """

    def __init__(self):
        DeviceProbe.__init__(self)
        # install dbus listener
        # FIXME: Finish implementing

class SourceDeviceFactory(SourceFactory):
    pass

class AlsaSourceDeviceFactory(SourceDeviceFactory):

    def __init__(self, card, device):
        SourceDeviceFactory.__init__(self)
        self.setAudio(True)
        self._card = card
        self._device = device

    def makeAudioBin(self):
        alsa = gst.element_factory_make("alsasrc")
        alsa.set_property("device", "hw:%d,%d" % (self._card, self._device))
        return alsa

class V4LSourceDeviceFactory(SourceDeviceFactory):

    def __init__(self, device):
        SourceDeviceFactory.__init__(self)
        self.setAudio(True)
        self._device = device

    def makeVideoBin(self):
        v4l = gst.element_factory_make("v4lsrc")
        v4l.set_property("device", self._device)
        return v4l

class V4L2SourceDeviceFactory(SourceDeviceFactory):

    def __init__(self, device):
        SourceDeviceFactory.__init__(self)
        self.setAudio(True)
        self._device = device

    def makeVideoBin(self):
        v4l2 = gst.element_factory_make("v4l2src")
        v4l2.set_property("device", self._device)
        return v4l2
