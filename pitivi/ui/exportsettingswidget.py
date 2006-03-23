# PiTiVi , Non-linear video editor
#
#       ui/exportsettingswidget.py
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

"""
Widget for the output settings
"""

import gobject
import gtk
from glade import GladeWidget
from pitivi.settings import encoders_muxer_compatible
from gstwidget import GstElementSettingsDialog

class ExportSettingsWidget(GladeWidget):
    glade_file = "exportsettingswidget.glade"
    video_presets = ( ("DVD PAL",  720,    576,    25.0),
                      ("320x240x30", 320,  240,    30.0) )
    video_rates = ( ("12 fps",      12.0),
                    ("24 fps",      24.0),
                    ("23,97 fps",   2400.0/1001.0),
                    ("25 fps",      25.0),
                    ("29,97 fps",   3000.0/1001.0),
                    ("30 fps",      30.0),
                    ("60 fps",      60.0) )
    audio_presets = ( ("CD",  2,      44100,  16), )
    audio_rates = ( ("8 KHz",   8000),
                    ("11 KHz",  11025),
                    ("22 KHz",  22050),
                    ("44.1 KHz", 44100),
                    ("48 KHz",  48000),
                    ("96 KHz",  96000) )
    audio_depths = ( ("8 bit",  8),
                     ("16 bit", 16),
                     ("24 bit", 24),
                     ("32 bit", 32) )
    

    def __init__(self):
        GladeWidget.__init__(self)
        self.settings = None
        self.validaencoders = []
        self.validvencoders = []
        self.containersettings = {}
        self.vcodecsettings = {}
        self.acodecsettings = {}

    def setSettings(self, settings):
        self.settings = settings
        self._fillSettings()

    def _fillSettings(self):
        # Video settings
        self.videowidthspin.set_value(self.settings.videowidth)
        self.videoheightspin.set_value(self.settings.videoheight)

        videolist = self.videoratecbox.get_model()
        videolist.clear()
        idx = 0
        value = -1
        for rate in self.video_rates:
            videolist.append([rate[0]])
            if rate[1] == self.settings.videorate:
                value = idx
            idx = idx + 1
        self.videoratecbox.set_active(value)

        videolist = self.videocombobox.get_model()
        videolist.clear()
        for preset in self.video_presets:
            videolist.append([preset[0]])
        videolist.append(["Custom"])

        # find out from the project settings which combo to take
        idx = 0
        for preset in self.video_presets:
            if (self.settings.videowidth,
                self.settings.videoheight,
                self.settings.videorate) == preset[1:]:
                break
            idx = idx + 1
        self.videocombobox.set_active(idx)

        # Audio settings

        self.audiochanncbox.set_active(self.settings.audiochannels - 1)
        # fill audio rate/depth combobox
        audiolist = self.audioratecbox.get_model()
        audiolist.clear()
        for rate in self.audio_rates:
            audiolist.append([rate[0]])
        self._putGoodAudiorate(self.settings.audiorate)

        audiolist = self.audiodepthcbox.get_model()
        audiolist.clear()
        for depth in self.audio_depths:
            audiolist.append([depth[0]])
        self._putGoodAudiodepth(self.settings.audiodepth)
        
        audiolist = self.audiocombobox.get_model()
        audiolist.clear()
        for preset in self.audio_presets:
            audiolist.append([preset[0]])
        audiolist.append(["Custom"])

        idx = 0
        for preset in self.audio_presets:
            if (self.settings.audiochannels,
                self.settings.audiorate,
                self.settings.audiodepth) == preset[1:]:
                break
            idx = idx + 1
        self.audiocombobox.set_active(idx)


        # Encoder settings
        venclist = self.vcodeccbox.get_model()
        venclist.clear()
        idx = 0
        selected = 0
        for factory in self.settings.vencoders:
            venclist.append(["%s [%s]" % (factory.get_longname(), factory.get_name())])
            if factory.get_name() == self.settings.vencoder:
                selected = idx
            idx = idx + 1
        self.vcodeccbox.set_active(selected)
        
        aenclist = self.acodeccbox.get_model()
        aenclist.clear()
        idx = 0
        selected = 0
        for factory in self.settings.aencoders:
            aenclist.append(["%s [%s]" % (factory.get_longname(), factory.get_name())])
            if factory.get_name() == self.settings.aencoder:
                selected = idx
            idx = idx + 1
        self.acodeccbox.set_active(selected)
        
        # Muxer
        self.muxers = self.settings.muxers
        muxs = self.muxercombobox.get_model()
        muxs.clear()
        idx = 0
        selected = 0
        for mux in self.muxers:
            muxs.append(["%s [%s]" % (mux.get_longname(), mux.get_name())])
            if mux.get_name() == self.settings.muxer:
                selected = idx
            idx = idx + 1
        self.muxercombobox.set_active(selected)

        # Encoder/Muxer settings
        self.containersettings = self.settings.containersettings
        self.acodecsettings = self.settings.acodecsettings
        self.vcodecsettings = self.settings.vcodecsettings

    def _putGoodVideorate(self, value):
        idx = 0
        for rate in self.video_rates:
            if value == rate[1]:
                self.videoratecbox.set_active(idx)
                return
            idx = idx + 1

    def _putGoodAudiorate(self, value):
        idx = 0
        for rate in self.audio_rates:
            if value == rate[1]:
                self.audioratecbox.set_active(idx)
                return
            idx = idx + 1

    def _putGoodAudiodepth(self, value):
        idx = 0
        for depth in self.audio_depths:
            if value == depth[1]:
                self.audiodepthcbox.set_active(idx)
                return
            idx = idx + 1

    def _videoComboboxChangedCb(self, widget):
        idx = widget.get_active()
        if idx == len(self.video_presets):
            activate = True
        else:
            activate = False
            self.videowidthspin.set_value(self.video_presets[idx][1])
            self.videoheightspin.set_value(self.video_presets[idx][2])
            self._putGoodVideorate(self.video_presets[idx][3])
        self.videowidthspin.set_sensitive(activate)
        self.videoheightspin.set_sensitive(activate)
        self.videoratecbox.set_sensitive(activate)

    def _audioComboboxChangedCb(self, widget):
        idx = widget.get_active()
        if idx == len(self.audio_presets):
            activate = True
        else:
            activate = False
            self.audiochanncbox.set_active(self.audio_presets[idx][1] - 1)
            self._putGoodAudiorate(self.audio_presets[idx][2])
            self._putGoodAudiodepth(self.audio_presets[idx][3])
        self.audiochanncbox.set_sensitive(activate)
        self.audioratecbox.set_sensitive(activate)
        self.audiodepthcbox.set_sensitive(activate)

    def _muxerComboboxChangedCb(self, widget):
        if self.validvencoders:
            prevvenc = self.validvencoders[self.vcodeccbox.get_active()].get_name()
        else:
            prevvenc = self.settings.vencoder
        if self.validaencoders:
            prevaenc = self.validaencoders[self.acodeccbox.get_active()].get_name()
        else:
            prevaenc = self.settings.aencoder
        # find the valid audio/video codec with the given muxer
        self.validaencoders = encoders_muxer_compatible(self.settings.aencoders,
                                                        self.muxers[widget.get_active()])
        self.validvencoders = encoders_muxer_compatible(self.settings.vencoders,
                                                        self.muxers[widget.get_active()])

        venclist = self.vcodeccbox.get_model()
        venclist.clear()
        idx = 0
        selected = 0
        for enc in self.validvencoders:
            venclist.append(["%s [%s]" % (enc.get_longname(), enc.get_name())])
            if enc.get_name() == prevvenc:
                selected = idx
            idx = idx + 1
        self.vcodeccbox.set_active(selected)

        aenclist = self.acodeccbox.get_model()
        aenclist.clear()
        idx = 0
        selected = 0
        for enc in self.validaencoders:
            aenclist.append(["%s [%s]" % (enc.get_longname(), enc.get_name())])
            if enc.get_name() == prevaenc:
                selected = idx
            idx = idx + 1
        self.acodeccbox.set_active(selected)

    def runSettingsDialog(self, factory, settings):
        dialog = GstElementSettingsDialog(factory, settings)
        if dialog.run() == gtk.RESPONSE_OK:
            dialog.hide()
            settings = dialog.get_settings()
        else:
            settings = None
        dialog.destroy()
        return settings        

    def _muxerSettingsButtonClickedCb(self, button):
        factory = self.settings.muxers[self.muxercombobox.get_active()]
        if not factory:
            return
        set = self.runSettingsDialog(factory, self.containersettings)
        if set:
            self.containersettings = set

    def _acodecSettingsButtonClickedCb(self, button):
        factory = self.validaencoders[self.acodeccbox.get_active()]
        if not factory:
            return
        set = self.runSettingsDialog(factory, self.acodecsettings)
        if set:
            self.acodecsettings = set

    def _vcodecSettingsButtonClickedCb(self, button):
        factory = self.validvencoders[self.vcodeccbox.get_active()]
        if not factory:
            return
        settings = self.runSettingsDialog(factory, self.vcodecsettings)
        if settings:
            self.vcodecsettings = settings
        
        
    def updateSettings(self):
        # Video Settings
        width = self.videowidthspin.get_value()
        height = self.videoheightspin.get_value()
        rate = self.video_rates[self.videoratecbox.get_active()][1]
        self.settings.setVideoProperties(width, height, rate)

        # Audio Settings
        nbchanns = self.audiochanncbox.get_active() + 1
        rate = self.audio_rates[self.audioratecbox.get_active()][1]
        depth = self.audio_depths[self.audiodepthcbox.get_active()][1]
        self.settings.setAudioProperties(nbchanns, rate, depth)

        # Encoders
        muxer = self.settings.muxers[self.muxercombobox.get_active()].get_name()
        vencoder = self.validvencoders[self.vcodeccbox.get_active()].get_name()
        aencoder = self.validaencoders[self.acodeccbox.get_active()].get_name()
        self.settings.setEncoders(muxer, vencoder, aencoder)

        # encoder/muxer settings
        self.settings.containersettings = self.containersettings
        self.settings.acodecsettings = self.acodecsettings
        self.settings.vcodecsettings = self.vcodecsettings
        

class ExportSettingsDialog(gtk.Dialog):

    def __init__(self, settings):
        gtk.Dialog.__init__(self, parent=None,
                            title="Export Settings",
                            flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                            buttons=(gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                     gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
        self.setwidget = ExportSettingsWidget()
        self.vbox.pack_start(self.setwidget)
        self.setwidget.setSettings(settings)
        self.setwidget.show_all()

    def getSettings(self):
        self.setwidget.updateSettings()
        return self.setwidget.settings

