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

import gtk
import gst
from pitivi.log.loggable import Loggable
from pitivi.encode import encoders_muxer_compatible, muxer_can_sink_raw_audio, muxer_can_sink_raw_video
from glade import GladeWidget
from gstwidget import GstElementSettingsDialog
import gobject
from gettext import gettext as _

class ExportSettingsWidget(GladeWidget, Loggable):
    glade_file = "exportsettingswidget.glade"
    video_presets = ((_("576p (PAL DV/DVD)"), 720, 576, 25.0, 1.0),
                    (_("480p (NTSC DV/DVD)"), 720, 480, 30000.0, 1001.0),
                    (_("720p HD"), 1280, 720, 30000.0, 1001.0),
                    (_("1080p full HD"), 1920, 1080, 30000.0, 1001.0),
                    (_("QVGA (320x240)"), 320, 240, 30.0, 1.0),
                    (_("VGA (640x480)"), 640, 480, 30.0, 1.0),
                    (_("SVGA (800x600)"), 800, 600, 30.0, 1.0),
                    (_("XGA (1024x768)"), 1024, 768, 30.0, 1.0),
                    )
    video_rates = ( ("12 fps",      12.0, 1.0),
                    ("24 fps",      24.0, 1.0),
                    ("23,97 fps",   24000.0, 1001.0),
                    ("25 fps",      25.0, 1.0),
                    ("29,97 fps",   30000.0, 1001.0),
                    ("30 fps",      30.0, 1.0),
                    ("60 fps",      60.0, 1.0) )
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


    def __init__(self, app):
        GladeWidget.__init__(self)
        Loggable.__init__(self)
        self.settings = None
        self.validaencoders = []
        self.validvencoders = []
        # cached values
        self.containersettings = {}
        self.vcodecsettings = {}
        self.acodecsettings = {}
        self.muxer = None
        self.vencoder = None
        self.aencoder = None
        self.app = app
        self._loading = False

    def setSettings(self, settings):
        self.debug("settings:%s", settings)
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
            if rate[1] == self.settings.videorate.num and rate[2] == self.settings.videorate.denom:
                value = idx
            idx = idx + 1
        self.videoratecbox.set_active(value)

        videolist = self.videocombobox.get_model()
        videolist.clear()
        fps_map = dict(((num, denom), desc)
                for desc, num, denom in self.video_rates)
        for preset in self.video_presets:
            fps = preset[3:5]
            videolist.append(["%s - %s" % (preset[0], fps_map[fps])])

        # i18n: string for custom video width/height/framerate settings
        videolist.append([_("Custom")])

        # find out from the project settings which combo to take
        idx = 0
        for preset in self.video_presets:
            if (self.settings.videowidth,
                self.settings.videoheight,
                self.settings.videorate.num,
                self.settings.videorate.denom) == preset[1:]:
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
        # i18n: string for custom audio rate/depth/channels settings
        audiolist.append([_("Custom")])

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
        self._loading = True
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
        self._loading = False
        self.muxercombobox.set_active(selected)

        # Encoder/Muxer settings
        self.muxer = self.settings.muxer
        self.vencoder = self.settings.vencoder
        self.aencoder = self.settings.aencoder
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
        if idx == -1 or idx == len(self.video_presets):
            # not a preset
            activate = True
        else:
            # valid preset
            activate = False
            self.videowidthspin.set_value(self.video_presets[idx][1])
            self.videoheightspin.set_value(self.video_presets[idx][2])
            self._putGoodVideorate(self.video_presets[idx][3])
        self.videowidthspin.set_sensitive(activate)
        self.videoheightspin.set_sensitive(activate)
        self.videoratecbox.set_sensitive(activate)

    def _audioComboboxChangedCb(self, widget):
        idx = widget.get_active()
        if idx == -1 or idx == len(self.audio_presets):
            # not a preset
            activate = True
        else:
            # valid preset
            activate = False
            self.audiochanncbox.set_active(self.audio_presets[idx][1] - 1)
            self._putGoodAudiorate(self.audio_presets[idx][2])
            self._putGoodAudiodepth(self.audio_presets[idx][3])
        self.audiochanncbox.set_sensitive(activate)
        self.audioratecbox.set_sensitive(activate)
        self.audiodepthcbox.set_sensitive(activate)

    def _muxerComboboxChangedCb(self, widget):
        if self._loading:
            return
        # get previous video encoder name
        if self.validvencoders:
            vidx = self.vcodeccbox.get_active()
            if vidx < len(self.validvencoders):
                prevvenc = self.validvencoders[vidx].get_name()
            elif vidx == len(self.validvencoders):
                prevvenc = None
        else:
            prevvenc = self.settings.vencoder

        # get previous audio encoder name
        if self.validaencoders:
            aidx = self.acodeccbox.get_active()
            if aidx < len(self.validaencoders):
                prevaenc = self.validaencoders[aidx].get_name()
            elif aidx == len(self.validaencoders):
                prevaenc = None
        else:
            prevaenc = self.settings.aencoder
        # find the valid audio/video codec with the given muxer
        muxer = self.muxers[widget.get_active()]
        self.validaencoders = encoders_muxer_compatible(self.settings.aencoders,
                                                        muxer)
        self.validvencoders = encoders_muxer_compatible(self.settings.vencoders,
                                                        muxer)

        venclist = self.vcodeccbox.get_model()
        venclist.clear()
        idx = 0
        selected = 0
        for enc in self.validvencoders:
            venclist.append(["%s [%s]" % (enc.get_longname(), enc.get_name())])
            if enc.get_name() == prevvenc:
                selected = idx
            idx = idx + 1
        if muxer_can_sink_raw_video(muxer):
            venclist.append([_("Raw Video")])
            if prevvenc == None:
                selected = idx
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
        if muxer_can_sink_raw_audio(muxer):
            aenclist.append([_("Raw Audio")])
            if prevaenc == None:
                selected = idx
        self.acodeccbox.set_active(selected)

    def runSettingsDialog(self, factory, settings={}):
        def configureEventCb(window, event):
            self.app.settings.elementSettingsDialogWidth = event.width
            self.app.settings.elementSettingsDialogHeight = event.height

        def mapEventCb(window, event):
            def reallySetWindowSize():
                dialog.window.resize(self.app.settings.elementSettingsDialogWidth,
                    self.app.settings.elementSettingsDialogHeight)
                dialog.window.disconnect(mapEventId)
                window.connect("configure-event", configureEventCb)
                return False
            gobject.idle_add(reallySetWindowSize)

        dialog = GstElementSettingsDialog(factory, settings)
        mapEventId = dialog.window.connect("map-event", mapEventCb)

        if dialog.run() == gtk.RESPONSE_OK:
            dialog.hide()
            settings = dialog.getSettings()
        else:
            settings = None
        dialog.destroy()
        return settings

    def _muxerSettingsButtonClickedCb(self, button):
        factory = self.settings.muxers[self.muxercombobox.get_active()]
        if not factory:
            return
        if factory.get_name() == self.settings.muxer:
            set = self.runSettingsDialog(factory, self.containersettings)
        else:
            set = self.runSettingsDialog(factory)
        if set:
            self.containersettings = set
            self.muxer = factory.get_name()

    def _acodecSettingsButtonClickedCb(self, button):
        factory = self.validaencoders[self.acodeccbox.get_active()]
        if not factory:
            return
        if factory.get_name() == self.aencoder:
            set = self.runSettingsDialog(factory, self.acodecsettings)
        else:
            set = self.runSettingsDialog(factory)
        if set:
            self.acodecsettings = set
            self.aencoder = factory.get_name()

    def _vcodecSettingsButtonClickedCb(self, button):
        factory = self.validvencoders[self.vcodeccbox.get_active()]
        if not factory:
            return
        if factory.get_name() == self.vencoder:
            settings = self.runSettingsDialog(factory, self.vcodecsettings)
        else:
            settings = self.runSettingsDialog(factory)
        if settings:
            self.vcodecsettings = settings
            self.vencoder = factory.get_name()


    def updateSettings(self):
        """ Updates and returns the ExportSettings configured in the widget """
        # Video Settings
        width = self.videowidthspin.get_value()
        height = self.videoheightspin.get_value()
        rate = gst.Fraction(*self.video_rates[self.videoratecbox.get_active()][1:])
        self.settings.setVideoProperties(width, height, rate)

        # Audio Settings
        nbchanns = self.audiochanncbox.get_active() + 1
        rate = self.audio_rates[self.audioratecbox.get_active()][1]
        depth = self.audio_depths[self.audiodepthcbox.get_active()][1]
        self.settings.setAudioProperties(nbchanns, rate, depth)

        # Encoders
        muxer = self.settings.muxers[self.muxercombobox.get_active()].get_name()
        vidx = self.vcodeccbox.get_active()
        if vidx < len(self.validvencoders):
            vencoder = self.validvencoders[vidx].get_name()
        elif vidx == len(self.validvencoders):
            vencoder = None
        else:
            self.warning("we don't want any video stream")
        aidx = self.acodeccbox.get_active()
        if aidx < len(self.validaencoders):
            aencoder = self.validaencoders[aidx].get_name()
        elif aidx == len(self.validaencoders):
            aencoder = None
        else:
            self.warning("we don't want any audio stream")
        self.settings.setEncoders(muxer, vencoder, aencoder)

        # encoder/muxer settings
        # only store cached values if no different factory was chosen.
        if muxer == self.muxer:
            self.settings.containersettings = self.containersettings
        else:
            self.settings.containersettings = {}
        if aencoder == self.aencoder:
            self.settings.acodecsettings = self.acodecsettings
        else:
            self.settings.acodecsettings = {}
        if vencoder == self.vencoder:
            self.settings.vcodecsettings = self.vcodecsettings
        else:
            self.settings.vcodecsettings = {}

        self.debug("Returning %s", self.settings)

        return self.settings


class ExportSettingsDialog(gtk.Dialog):

    def __init__(self, app, settings):
        gtk.Dialog.__init__(self, parent=None,
                            title=_("Export settings"),
                            flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
                                     gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        self.set_icon_name("pitivi")
        self.setwidget = ExportSettingsWidget(app)
        self.vbox.pack_start(self.setwidget)
        self.setwidget.setSettings(settings)
        self.setwidget.show_all()

    def getSettings(self):
        return self.setwidget.updateSettings()
