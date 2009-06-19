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

import gst
from pitivi.factories.base import ObjectFactory, SourceFactory
from pitivi.signalinterface import Signallable
from pitivi.log.loggable import Loggable

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

class DeviceProbe(Signallable, Loggable):
    """
    Allows listing of the various devices available.

    It can also signal devices (dis)appearing.

    This should be subclassed
    """

    def __init__(self):
        Loggable.__init__(self)

    __signals__ = {
        "device-added" : ["device"],
        "device-removed" : ["device"]
        }

    def getSourceDevices(self, media_type):
        """ Returns a list of available SourceDeviceFactory for
        the given mediatype
        """
        raise NotImplementedError

    def getAudioSourceDevices(self):
        """
        Returns a list of available SourceDeviceFactory of
        type AUDIO_DEVICE
        """
        return self.getSourceDevices(media_type=AUDIO_DEVICE)

    def getVideoSourceDevices(self):
        """
        Returns a list of available SourceDeviceFactory of
        type VIDEO_DEVICE
        """
        return self.getSourceDevices(media_type=VIDEO_DEVICE)

    def getSinkDevices(self, media_type):
        """ Returns a list of available SinkDeviceFactory for
        the given mediatype
        """
        raise NotImplementedError

    def getAudioSinkDevices(self):
        """
        Returns a list of available SinkDeviceFactory of
        type AUDIO_DEVICE
        """
        return self.getSinkDevices(media_type=AUDIO_DEVICE)

    def getVideoSinkDevices(self):
        """
        Returns a list of available SinkDeviceFactory of
        type VIDEO_DEVICE
        """
        return self.getSinkDevices(media_type=VIDEO_DEVICE)


class HalDeviceProbe(DeviceProbe):
    """
    Probes for devices using HAL
    """

    def __init__(self):
        DeviceProbe.__init__(self)
        # UDI : DeviceFactory
        self._sources = {'video': {}, 'audio': {}}
        self._sinks = {'video': {}, 'audio': {}}

        self.bus = dbus.SystemBus()
        self.managerobj = self.bus.get_object('org.freedesktop.Hal',
                                              '/org/freedesktop/Hal/Manager')
        self.manager = dbus.Interface(self.managerobj,
                                      'org.freedesktop.Hal.Manager')

        # we want to be warned when devices are added and removed
        self.manager.connect_to_signal("DeviceAdded",
                                       self._deviceAddedCb)
        self.manager.connect_to_signal("DeviceRemoved",
                                       self._deviceRemovedCb)

        # Find v4l ...
        for dev in self.manager.FindDeviceByCapability("video4linux"):
            self._processUDI(dev)
        # ... and alsa devices
        for dev in self.manager.FindDeviceByCapability("alsa"):
            self._processUDI(dev)

    def release(self):
        self.debug("release")
        self._sources = {'video': {}, 'audio': {}}
        self._sinks = {'video': {}, 'audio': {}}

    def getSourceDevices(self, media_type):
        return self._getDevs(media_type, self._sources)

    def getSinkDevices(self, media_type):
        return self._getDevs(media_type, self._sinks)

    # PRIVATE

    def _getDevs(self, media_type, sr):
        if media_type == AUDIO_DEVICE:
            return sr['audio'].values()
        elif media_type == VIDEO_DEVICE:
            return sr['video'].values()

    def _processUDI(self, device_udi):
        if device_udi in self._sources.keys() or device_udi in self._sinks.keys():
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
            self.debug("Valid source %r", dev)
            self._sources['video'][device_udi] = srcdev
            self.emit("device-added", srcdev)
        elif devobject.QueryCapability("alsa"):
            alsatype = devobject.GetProperty("alsa.type")
            if alsatype in ["capture", "playback"]:
                card = devobject.GetProperty("alsa.card")
                device = devobject.GetProperty("alsa.device")
                info = devobject.GetProperty("alsa.card_id")
                if alsatype == "capture":
                    self.debug("Valid source %r", dev)
                    self._sources['audio'][device_udi] = AlsaSourceDeviceFactory(card=card,
                                                                  device=device,
                                                                  displayname=info)
                    self.emit("device-added", self._sources['audio'][device_udi])
                elif alsatype == "playback":
                    self.debug("Valid sink %r", dev)
                    self._sinks[device_udi] = AlsaSinkDeviceFactory(card=card,
                                                              device=device,
                                                              displayname=info)
                    self.emit("device-added", self._sinks[device_udi])

    def _deviceAddedCb(self, device_udi, *unused_args):
        self.debug("udi:%r", device_udi)
        self._processUDI(device_udi)

    def _deviceRemovedCb(self, device_udi, *unused_args):
        self.debug("udi:%r", device_udi)
        for k in ('audio', 'video'):
            if self._sources[k].has_key(device_udi):
                dev = self._sources[k][device_udi]
                del self._sources[k][device_udi]
                self.emit("device-removed", dev)
                break
            elif self._sinks.has_key(device_udi):
                dev = self._sinks[k][device_udi]
                del self._sinks[k][device_udi]
                self.emit("device-removed", dev)
                break

class SourceDeviceFactory(SourceFactory):
    """
    Base class for ObjectFactory to control source devices
    """
    pass

class SinkDeviceFactory(ObjectFactory):
    """
    Base class for ObjectFactory to control sink devices
    """
    pass

class AlsaSourceDeviceFactory(SourceDeviceFactory):
    """ObjectFactory for Alsa source devices"""

    def __init__(self, card, device, *args, **kwargs):
        SourceDeviceFactory.__init__(self, *args, **kwargs)
        self.is_audio = True
        self._card = card
        self._device = device

    def makeAudioBin(self):
        alsa = gst.element_factory_make("alsasrc")
        alsa.set_property("device", "hw:%d,%d" % (self._card, self._device))
        return alsa

    def __str__(self):
        return "<%s: %s [hw:%s,%s]>" % (self.__class__.__name__,
                                        self.displayname or self.name,
                                        self._card, self._device)

class AlsaSinkDeviceFactory(SinkDeviceFactory):
    """ObjectFactory for Alsa sink devices"""

    def __init__(self, card, device, *args, **kwargs):
        SinkDeviceFactory.__init__(self, *args, **kwargs)
        self.is_audio = True
        self._card = card
        self._device = device

    def makeAudioBin(self):
        alsa = gst.element_factory_make("alsasink")
        alsa.set_property("device", "hw:%d,%d" % (self._card, self._device))
        return alsa

    def __str__(self):
        return "<%s: %s [hw:%s,%s]>" % (self.__class__.__name__,
                                        self.displayname or self.name,
                                        self._card, self._device)



class V4LSourceDeviceFactory(SourceDeviceFactory):
    """ObjectFactory for Video4Linux source devices"""

    def __init__(self, device, *args, **kwargs):
        SourceDeviceFactory.__init__(self, *args, **kwargs)
        self.is_video = True
        self._device = device
        self.__probed = False
        self.__isv4l2 = True

    def makeVideoBin(self):
        # FIXME : we need to do some probbing to figure out if we should use
        # v4l or v4l2
        if not self.__probed:
            self.__probe()
        v4l = gst.element_factory_make(self.__isv4l2 and "v4l2src" or "v4lsrc")
        v4l.set_property("device", self._device)
        return v4l

    def __probe(self):
        """Probes the device to figure out which v4l source to use"""
        # first v4l
        v = gst.Pipeline()
        vsrc = gst.element_factory_make("v4lsrc")
        vsrc.props.device = self._device
        fsink = gst.element_factory_make("fakesink")
        v.add(vsrc, fsink)
        vsrc.link(fsink)
        if v.set_state(gst.STATE_PAUSED) != gst.STATE_CHANGE_FAILURE:
            self.__isv4l2 = False
            self.__probed = True
            v.set_state(gst.STATE_NULL)
            return
        v.set_state(gst.STATE_NULL)

        v = gst.Pipeline()
        vsrc = gst.element_factory_make("v4l2src")
        vsrc.props.device = self._device
        fsink = gst.element_factory_make("fakesink")
        v.add(vsrc, fsink)
        # let's still make sure that it's a v4l2 device :)
        if v.set_state(gst.STATE_PAUSED) != gst.STATE_CHANGE_FAILURE:
            self.__isv4l2 = True
            self.__probed = True
            v.set_state(gst.STATE_NULL)
            return
        v.set_state(gst.STATE_NULL)
        self.warning("Could not probe %s", self._device)
