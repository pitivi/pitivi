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

import gobject
from objectfactory import ObjectFactory, SourceFactory

try:
    import dbus
    import dbus.glib
    HAVE_DBUS = True
except:
    HAVE_DBUS = False

(AUDIO_DEVICE,
 VIDEO_DEVICE,
 UNKNOWN_DEVICE_MEDIA_TYPE) = range(3)

(SOURCE_DEVICE,
 SINK_DEVICE,
 UNKNOWN_DEVICE_DIRECTION) = range(3)

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

def get_probe():
    """
    Returns the default DeviceProbe for the current system.

    If no suitable DeviceProbe implementation is available, returns None.
    """
    if HAVE_DBUS:
        return HalDeviceProbe()
    return None

class DeviceProbe(gobject.GObject):
    """
    Allows listing of the various devices available.

    It can also signal devices (dis)appearing.

    This should be subclassed
    """

    __gsignals__ = {
        "device-added" : (gobject.SIGNAL_RUN_LAST,
                          gobject.TYPE_NONE,
                          (gobject.TYPE_PYOBJECT, )),
        "device-removed" : (gobject.SIGNAL_RUN_LAST,
                            gobject.TYPE_NONE,
                            (gobject.TYPE_PYOBJECT, ))
        }

    def __init__(self):
        gobject.GObject.__init__(self)

    def getSourceDevices(self, media_type):
        """ Returns a list of available SourceDeviceFactory for
        the given mediatype
        """
        raise NotImplementedError

    def getAudioSourceDevices(self):
        return self.getSourceDevices(media_type=AUDIO_DEVICE)

    def getVideoSourceDevices(self):
        return self.getSourceDevices(media_type=VIDEO_DEVICE)

    def getSinkDevices(self, media_type):
        """ Returns a list of available SinkDeviceFactory for
        the given mediatype
        """
        raise NotImplementedError

    def getAudioSinkDevices(self):
        return self.getSinkDevices(media_type=AUDIO_DEVICE)

    def getVideoSinkDevices(self):
        return self.getSinkDevices(media_type=VIDEO_DEVICE)


class HalDeviceProbe(DeviceProbe):
    """
    Probes for devices using HAL
    """

    def __init__(self):
        DeviceProbe.__init__(self)
        # UDI : DeviceFactory
        self.__sources = {}
        self.__sinks = {}

        self.bus = dbus.SystemBus()
        self.managerobj = self.bus.get_object('org.freedesktop.Hal',
                                              '/org/freedesktop/Hal/Manager')
        self.manager = dbus.Interface(self.managerobj,
                                      'org.freedesktop.Hal.Manager')

        # we want to be warned when devices are added and removed
        self.manager.connect_to_signal("DeviceAdded",
                                       self.__deviceAddedCb)
        self.manager.connect_to_signal("DeviceRemoved",
                                       self.__deviceRemovedCb)

        # Find v4l ...
        for dev in self.manager.FindDeviceByCapability("video4linux"):
            self.__processUDI(dev)
        # ... and alsa devices
        for dev in self.manager.FindDeviceByCapability("alsa"):
            self.__processUDI(dev)


    def getSourceDevices(self, media_type):
        return self.__getDevs(media_type, self.__sources)

    def getSinkDevices(self, media_type):
        return self.__getDevs(media_type, self.__sinks)

    # PRIVATE

    def __getDevs(self, media_type, sr):
        if media_type == AUDIO_DEVICE:
            return [sr[x] for x in sr.keys() if sr[x].is_audio]
        elif media_type == VIDEO_DEVICE:
            return [sr[x] for x in sr.keys() if sr[x].is_video]

    def __processUDI(self, device_udi):
        if device_udi in self.__sources.keys() or device_udi in self.__sinks.keys():
            # we already have this device
            return

        # Get the object
        # FIXME : Notify !
        dev = self.bus.get_object("org.freedesktop.Hal",
                                        device_udi)
        devobject = dbus.Interface(dev, 'org.freedesktop.Hal.Device')
        if devobject.QueryCapability("video4linux"):
            location = devobject.GetProperty("video4linux.device")
            info = devobject.GetProperty("info.product")
            srcdev = V4LSourceDeviceFactory(device=location,
                                            displayname=info)
            self.__sources[dev] = srcdev
            self.emit("device-added", srcdev)
        elif devobject.QueryCapability("alsa"):
            alsatype = devobject.GetProperty("alsa.type")
            if alsatype in ["capture", "playback"]:
                card = devobject.GetProperty("alsa.card")
                device = devobject.GetProperty("alsa.device")
                info = devobject.GetProperty("alsa.card_id")
                if alsatype == "capture":
                    self.__sources[dev] = AlsaSourceDeviceFactory(card=card,
                                                                  device=device,
                                                                  displayname=info)
                    self.emit("device-added", self.__sources[dev])
                elif alsatype == "playback":
                    self.__sinks[dev] = AlsaSinkDeviceFactory(card=card,
                                                              device=device,
                                                              displayname=info)
                    self.emit("device-added", self.__sinks[dev])

    def __deviceAddedCb(self, device_udi, *args):
        self.__processUDI(device_udi)

    def __deviceRemovedCb(self, device_udi, *args):
        # FIXME : Notify !
        if self.__sources.has_key(device_udi):
            self.emit("device-removed", self.__sources[device_udi])
            del self.__sources[device_udi]
        elif self.__sinks.has_key(device_udi):
            self.emit("device-removed", self.__sinks[device_udi])
            del self.__sinks[device_udi]



class SourceDeviceFactory(SourceFactory):
    pass

class SinkDeviceFactory(ObjectFactory):
    pass

class AlsaSourceDeviceFactory(SourceDeviceFactory):

    def __init__(self, card, device, *args, **kwargs):
        SourceDeviceFactory.__init__(self, *args, **kwargs)
        self.is_audio = True
        self._card = card
        self._device = device

    def makeAudioBin(self):
        alsa = gst.element_factory_make("alsasrc")
        alsa.set_property("device", "hw:%d,%d" % (self._card, self._device))
        return alsa

    def __repr__(self):
        return "<%s: %s [hw:%s,%s]>" % (self.__class__.__name__,
                                        self.displayname or self.name,
                                        self._card, self._device)

class AlsaSinkDeviceFactory(SinkDeviceFactory):
    def __init__(self, card, device, *args, **kwargs):
        SinkDeviceFactory.__init__(self, *args, **kwargs)
        self.is_audio = True
        self._card = card
        self._device = device

    def makeAudioBin(self):
        alsa = gst.element_factory_make("alsasink")
        alsa.set_property("device", "hw:%d,%d" % (self._card, self._device))
        return alsa

    def __repr__(self):
        return "<%s: %s [hw:%s,%s]>" % (self.__class__.__name__,
                                        self.displayname or self.name,
                                        self._card, self._device)



class V4LSourceDeviceFactory(SourceDeviceFactory):

    def __init__(self, device, *args, **kwargs):
        SourceDeviceFactory.__init__(self, *args, **kwargs)
        self.is_video = True
        self._device = device

    def makeVideoBin(self):
        # FIXME : we need to do some probbing to figure out if we should use
        # v4l or v4l2
        v4l = gst.element_factory_make("v4lsrc")
        v4l.set_property("device", self._device)
        return v4l

