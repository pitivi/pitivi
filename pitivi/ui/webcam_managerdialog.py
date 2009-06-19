# PiTiVi , Non-linear video editor
#
#       pitivi/ui/webcam_managerdialog.py
#
# Copyright (c) 2008, Sarath Lakshman <sarathlakshman@slynux.org>
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

import gtk
import gst
import tempfile
from pitivi.settings import ExportSettings
from pitivi.sourcelist import SourceList
from pitivi.bin import SmartCaptureBin, SinkBin
from pitivi.threads import CallbackThread
from pitivi.ui.glade import GladeWindow

class WebcamManagerDialog(GladeWindow):
    """
    Webcan capture dialog box
    """
    glade_file = "cam_capture.glade"

    def __init__(self, pitivi):
        gst.log("Creating new WebcamManager Dialog")
        self.pitivi = pitivi
        GladeWindow.__init__(self)

        # Create gtk widget using glade model
        self.draw_window = self.widgets["draw_window"]
        self.draw_window.unset_flags(gtk.DOUBLE_BUFFERED)
        self.draw_window.unset_flags(gtk.SENSITIVE)
        self.record_btn = self.widgets["record_btn"]
        self.close_btn = self.widgets["close_btn"]

        self.close_btn.connect("clicked", self.close)
        self.record_btn.connect("clicked", self.threaded_recording)
        self.window.connect("destroy", self.close)

        self.record_btn = self.record_btn.get_children()[0]
        self.record_btn = self.record_btn.get_children()[0].get_children()[1]
        self.record_btn.set_label("Start Recording")

        self.sourcefactories = SourceList()

        self._audiodev = None
        self._videodev = None

        self._vdevcombo = self.widgets["videodev_combo"]
        self._vdevcombo.set_active(0)
        self._vdevcombo.set_model(gtk.ListStore(str, object))
        self._vdevcombo.set_attributes(self._vdevcombo.child.get_cell_renderers()[0],
                                       text=0)
        self._adevcombo = self.widgets["audiodev_combo"]
        self._adevcombo.set_active(0)
        self._adevcombo.set_model(gtk.ListStore(str, object))
        self._adevcombo.set_attributes(self._adevcombo.child.get_cell_renderers()[0],
                                       text=0)
        self._updateVideoCombo()
        self._updateAudioCombo()

        self.filepath = None

        self.sink = SinkBin()
        CallbackThread(self._setupPlayer).start()

    def show_all(self):
        self.window.show_all()

    # Perform record in a seperate thread
    def threaded_recording(self, w):
        CallbackThread(self.do_recording, w).start()


    # Record button action callback
    def do_recording(self, w):
        if self.record_btn.get_label() == "Start Recording":
            gst.debug("recording started")
            self.filepath = 'file://'+tempfile.mktemp(suffix=".ogg",
                                                      prefix="pitivi-webcam-capture-")
            self.player.record(self.filepath, ExportSettings())
            self.record_btn.set_label("Stop Recording")
            self.player.set_state(gst.STATE_PLAYING)



        else:
            gst.debug("recording stopped")
            self.player.stopRecording()
            # FIXME : use the generic way for adding a file
            self.sourcefactories.addUris([self.filepath])
            self.player.set_state(gst.STATE_PLAYING)
            self.record_btn.set_label("Start Recording")

    # For Setting up audio,video sinks
    def setSinks(self):
        self.sink.connectSink(self.player, True, True)
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect('sync-message::element', self.on_sync_message)

    # Close the Webcamdialog
    def close(self, w):
        self.window.hide()
        self.player.set_state(gst.STATE_NULL)
        self.window.destroy()

    # For draw_window syncs
    def on_sync_message(self, bus, message):
        if message.structure is None:
            return
        message_name = message.structure.get_name()
        if message_name == 'prepare-xwindow-id':
            # Assign the viewport
            imagesink = message.src
            imagesink.set_property('force-aspect-ratio', True)
            try:
                imagesink.set_xwindow_id(self.draw_window.window.xid)
            except:
                gst.warning("Couldn't set the XID on our video sink !")

    def _setupPlayer(self):
        gst.debug("Creating initial SmartCaptureBin")
        # figure out adev
        probe = self.pitivi.deviceprobe
        if len(probe.getAudioSourceDevices()):
            adev = probe.getAudioSourceDevices()[0]
        else:
            adev = None
        self._changeSelectedAudio(adev)

        if len(probe.getVideoSourceDevices()):
            vdev = probe.getVideoSourceDevices()[0]
        else:
            vdev = None
        self._changeSelectedVideo(vdev)

        probe.connect("device-added", self._deviceAddedCb)
        probe.connect("device-removed", self._deviceRemovedCb)

        if hasattr(self, "player"):
            self.player.set_state(gst.STATE_NULL)
        self.player = SmartCaptureBin(audiodevice=adev,
                                      videodevice=vdev)
        self.setSinks()
        # FIXME : check for state change failures
        self.player.set_state(gst.STATE_PLAYING)

    def _resetPlayer(self):
        ## call me in another thread !
        gst.debug("Setting previous to NULL")
        self.player.set_state(gst.STATE_NULL)
        gst.debug("Creating new SmartCaptureBin(%r,%r)" % (self._audiodev, self._videodev))
        self.player = SmartCaptureBin(audiodevice = self._audiodev,
                                      videodevice = self._videodev)
        gst.debug("Calling setSinks()")
        self.setSinks()
        gst.debug("Finally setting to PLAYING...")
        res = self.player.set_state(gst.STATE_PLAYING)
        gst.debug("... which returned %r" % res)

    def _changeSelectedCombo(self, combo, device):
        gst.debug("device %r" % device)
        model = combo.get_model()
        idx = 0
        for name, dev in model:
            if dev == device:
                break
            idx += 1
        combo.set_active(idx)

    def _changeSelectedAudio(self, device):
        self._audiodev = device
        self._changeSelectedCombo(self._adevcombo, device)

    def _changeSelectedVideo(self, device):
        self._videodev = device
        self._changeSelectedCombo(self._vdevcombo, device)

    def _deviceAddedCb(self, probe, device):
        gst.debug("device %r appeared" % device)
        self._updateAudioCombo()
        self._updateVideoCombo()

    def _deviceRemovedCb(self, probe, device):
        gst.debug("device %r went away" % device)
        if self._audiodev == device:
            devs = self.pitivi.deviceprobe.getAudioSourceDevices()
            if len(devs):
                self._changeSelectedAudio(devs[0])
            else:
                self._audiodev = None
        elif self._videodev == device:
            devs = self.pitivi.deviceprobe.getVideoSourceDevices()
            if len(devs):
                self._changeSelectedVideo(devs[0])
            else:
                self._videodev = None
        self._updateAudioCombo()
        self._updateVideoCombo()

    def _updateCombo(self, combo, devices):
        model = combo.get_model()
        if len(devices) == len(model):
            # nothing changed
            return
        model.clear()
        for dev in devices:
            model.append([dev.name, dev])

    def _updateAudioCombo(self):
        self._updateCombo(self._adevcombo,
                           self.pitivi.deviceprobe.getAudioSourceDevices())
        self._changeSelectedAudio(self._audiodev)

    def _updateVideoCombo(self):
        self._updateCombo(self._vdevcombo,
                           self.pitivi.deviceprobe.getVideoSourceDevices())
        self._changeSelectedVideo(self._videodev)

    def _adevComboChangedCb(self, widget):
        # get the active device
        row = widget.get_model()[widget.get_active()]
        if len(row) < 2:
            return
        dev = row[1]
        gst.debug("device %r" % dev)
        if dev == self._audiodev:
            return
        self._changeSelectedAudio(dev)
        if not hasattr(self, "player"):
            return
        CallbackThread(self._resetPlayer).start()

    def _vdevComboChangedCb(self, widget):
        row = widget.get_model()[widget.get_active()]
        if len(row) < 2:
            return
        dev = row[1]
        gst.debug("device %r" % dev)
        if dev == self._videodev:
            return
        self._changeSelectedVideo(dev)
        if not hasattr(self, "player"):
            return
        CallbackThread(self._resetPlayer).start()
