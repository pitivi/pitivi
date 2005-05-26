# PiTiVi , Non-linear video editor
#
#       ui/projectsettings.py
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
import gtk
from glade import GladeWindow
from pitivi.project import encoders_muxer_compatible

class ProjectSettingsDialog(GladeWindow):
    glade_file = "projectsettings.glade"
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

    def __init__(self, parent, project):
        GladeWindow.__init__(self, parent)
        self.project = project
        self.validaencoders = []
        self.validvencoders = []
        self._fill_settings()

    def _fill_settings(self):
        w = self.widgets
        w["nameentry"].set_text(self.project.name)
        w["descriptiontextview"].get_buffer().set_text(self.project.description)
        
        # Video settings
        w["videowidthspin"].set_value(self.project.settings.videowidth)
        w["videoheightspin"].set_value(self.project.settings.videoheight)

        videolist = w["videoratecbox"].get_model()
        videolist.clear()
        idx = 0
        value = -1
        for rate in self.video_rates:
            videolist.append([rate[0]])
            if rate[1] == self.project.settings.videorate:
                value = idx
            idx = idx + 1
        w["videoratecbox"].set_active(value)

        videolist = w["videocombobox"].get_model()
        videolist.clear()
        for preset in self.video_presets:
            videolist.append([preset[0]])
        videolist.append(["Custom"])

        # find out from the project settings which combo to take
        idx = 0
        for preset in self.video_presets:
            if (self.project.settings.videowidth,
                self.project.settings.videoheight,
                self.project.settings.videorate) == preset[1:]:
                break
            idx = idx + 1
        w["videocombobox"].set_active(idx)

        # Audio settings

        w["audiochanncbox"].set_active(self.project.settings.audiochannels - 1)
        # fill audio rate/depth combobox
        audiolist = w["audioratecbox"].get_model()
        audiolist.clear()
        for rate in self.audio_rates:
            audiolist.append([rate[0]])
        self._put_good_audiorate(self.project.settings.audiorate)

        audiolist = w["audiodepthcbox"].get_model()
        audiolist.clear()
        for depth in self.audio_depths:
            audiolist.append([depth[0]])
        self._put_good_audiodepth(self.project.settings.audiodepth)
        
        audiolist = w["audiocombobox"].get_model()
        audiolist.clear()
        for preset in self.audio_presets:
            audiolist.append([preset[0]])
        audiolist.append(["Custom"])

        idx = 0
        for preset in self.audio_presets:
            if (self.project.settings.audiochannels,
                self.project.settings.audiorate,
                self.project.settings.audiodepth) == preset[1:]:
                break
            idx = idx + 1
        w["audiocombobox"].set_active(idx)


        # Encoder settings
        venclist = w["vcodeccbox"].get_model()
        venclist.clear()
        idx = 0
        selected = 0
        for factory in self.project.settings.vencoders:
            venclist.append(["%s [%s]" % (factory.get_longname(), factory.get_name())])
            if factory.get_name() == self.project.settings.vencoder:
                selected = idx
            idx = idx + 1
        w["vcodeccbox"].set_active(selected)
        
        aenclist = w["acodeccbox"].get_model()
        aenclist.clear()
        idx = 0
        selected = 0
        for factory in self.project.settings.aencoders:
            aenclist.append(["%s [%s]" % (factory.get_longname(), factory.get_name())])
            if factory.get_name() == self.project.settings.aencoder:
                selected = idx
            idx = idx + 1
        w["acodeccbox"].set_active(selected)
        
        # Muxer
        self.muxers = self.project.settings.muxers
        muxs = w["muxercombobox"].get_model()
        muxs.clear()
        idx = 0
        selected = 0
        for mux in self.muxers:
            muxs.append(["%s [%s]" % (mux.get_longname(), mux.get_name())])
            if mux.get_name() == self.project.settings.muxer:
                selected = idx
            idx = idx + 1
        w["muxercombobox"].set_active(selected)

    def _update_settings(self):
        # apply selected settings to project
        w = self.widgets
        
        # Name/Description
        self.project.name = w["nameentry"].get_text()
        txtbuffer = w["descriptiontextview"].get_buffer()
        self.project.description = txtbuffer.get_text(txtbuffer.get_start_iter(),
                                                      txtbuffer.get_end_iter())

        # Video Settings
        width = w["videowidthspin"].get_value()
        height = w["videoheightspin"].get_value()
        rate = self.video_rates[w["videoratecbox"].get_active()][1]
        self.project.settings.set_video_properties(width, height, rate)

        # Audio Settings
        nbchanns = w["audiochanncbox"].get_active() + 1
        rate = self.audio_rates[w["audioratecbox"].get_active()][1]
        depth = self.audio_depths[w["audiodepthcbox"].get_active()][1]
        self.project.settings.set_audio_properties(nbchanns, rate, depth)

        # Encoders
        muxer = self.project.settings.muxers[w["muxercombobox"].get_active()].get_name()
        vencoder = self.validvencoders[w["vcodeccbox"].get_active()].get_name()
        aencoder = self.validaencoders[w["acodeccbox"].get_active()].get_name()
        self.project.settings.set_encoders(muxer, vencoder, aencoder)

    def _put_good_videorate(self, value):
        idx = 0
        for rate in self.video_rates:
            if value == rate[1]:
                self.widgets["videoratecbox"].set_active(idx)
                return
            idx = idx + 1

    def _put_good_audiorate(self, value):
        print "put good audiorate", value
        idx = 0
        for rate in self.audio_rates:
            if value == rate[1]:
                self.widgets["audioratecbox"].set_active(idx)
                return
            idx = idx + 1

    def _put_good_audiodepth(self, value):
        print "put good audiodepth", value
        idx = 0
        for depth in self.audio_depths:
            if value == depth[1]:
                self.widgets["audiodepthcbox"].set_active(idx)
                return
            idx = idx + 1

    def videocombobox_changed(self, widget):
        print "videocombobox changed"
        idx = widget.get_active()
        if idx == len(self.video_presets):
            activate = True
        else:
            activate = False
            self.widgets["videowidthspin"].set_value(self.video_presets[idx][1])
            self.widgets["videoheightspin"].set_value(self.video_presets[idx][2])
            self._put_good_videorate(self.video_presets[idx][3])
        self.widgets["videowidthspin"].set_sensitive(activate)
        self.widgets["videoheightspin"].set_sensitive(activate)
        self.widgets["videoratecbox"].set_sensitive(activate)

    def audiocombobox_changed(self, widget):
        print "audiocombobox changed"
        idx = widget.get_active()
        if idx == len(self.audio_presets):
            activate = True
        else:
            activate = False
            self.widgets["audiochanncbox"].set_active(self.audio_presets[idx][1] - 1)
            self._put_good_audiorate(self.audio_presets[idx][2])
            self._put_good_audiodepth(self.audio_presets[idx][3])
        self.widgets["audiochanncbox"].set_sensitive(activate)
        self.widgets["audioratecbox"].set_sensitive(activate)
        self.widgets["audiodepthcbox"].set_sensitive(activate)

    def muxercombobox_changed(self, widget):
        print "muxercombobox changed"

        if self.validvencoders:
            prevvenc = self.validvencoders[self.widgets["vcodeccbox"].get_active()].get_name()
        else:
            prevvenc = self.project.settings.vencoder
        if self.validaencoders:
            prevaenc = self.validaencoders[self.widgets["acodeccbox"].get_active()].get_name()
        else:
            prevaenc = self.project.settings.aencoder
        # find the valid audio/video codec with the given muxer
        self.validaencoders = encoders_muxer_compatible(self.project.settings.aencoders, self.muxers[widget.get_active()])
        self.validvencoders = encoders_muxer_compatible(self.project.settings.vencoders, self.muxers[widget.get_active()])
        print "valid vencoder", self.validvencoders
        print "valid aencoder", self.validaencoders

        venclist = self.widgets["vcodeccbox"].get_model()
        venclist.clear()
        idx = 0
        selected = 0
        for enc in self.validvencoders:
            venclist.append(["%s [%s]" % (enc.get_longname(), enc.get_name())])
            if enc.get_name() == prevvenc:
                selected = idx
            idx = idx + 1
        self.widgets["vcodeccbox"].set_active(selected)

        aenclist = self.widgets["acodeccbox"].get_model()
        aenclist.clear()
        idx = 0
        selected = 0
        for enc in self.validaencoders:
            aenclist.append(["%s [%s]" % (enc.get_longname(), enc.get_name())])
            if enc.get_name() == prevaenc:
                selected = idx
            idx = idx + 1
        self.widgets["acodeccbox"].set_active(selected)

    def response_cb(self, widget, response):
        # if the response is gtk.RESPONSE_OK update the settings
        # else destroy yourself !
        self.hide()
        if response == gtk.RESPONSE_OK:
            print "settings updated"
            self._update_settings()
        else:
            print "settings NOT updated!"
        self.destroy()
