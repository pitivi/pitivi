# PiTiVi , Non-linear video editor
#
#       ui/clipmediaprops.py
#
# Copyright (c) 2011, Parthasarathi Susarla <partha@collabora.co.uk>
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
Dialog box displaying the properties of a clip from media library, allowing
to set those properties as the project settings.
"""

import gtk
import gst
import os

from gettext import gettext as _
from pitivi.configure import get_ui_dir
from pitivi.utils.ui import frame_rates, audio_rates, audio_depths,\
    audio_channels, pixel_aspect_ratios, get_value_from_model


class clipmediapropsDialog():

    def __init__(self, project, audio_streams, video_streams):
        self.project = project
        self.settings = self.project.getSettings()
        self.audio_streams = audio_streams
        self.video_streams = video_streams
        self.has_audio = self.has_video = self.is_image = False
        self._createUi()

    def run(self):
        # TODO: in "onApplyButtonClicked", we only use the first stream...
        # If we have multiple audio or video streams, we should reflect that
        # in the UI, instead of acting as if there was only one. But that means
        # dynamically creating checkboxes and labels in a table and such.
        for stream in self.audio_streams:
            self.channels.set_text(
                get_value_from_model(audio_channels, stream.get_channels()))
            self.sample_rate.set_text(
                get_value_from_model(audio_rates, stream.get_sample_rate()))
            self.sample_depth.set_text(
                get_value_from_model(audio_depths, stream.get_depth()))
            self.has_audio = True
            break

        for stream in self.video_streams:
            self.size_width.set_text(str(stream.get_width()))
            self.size_height.set_text(str(stream.get_height()))
            self.is_image = stream.is_image()
            if not self.is_image:
                self.frame_rate.set_text(
                    get_value_from_model(frame_rates, gst.Fraction(
                                                stream.get_framerate_num(),
                                                stream.get_framerate_denom())))
                self.aspect_ratio.set_text(
                    get_value_from_model(pixel_aspect_ratios, gst.Fraction(
                                                    stream.get_par_num(),
                                                    stream.get_par_denom())))
            self.has_video = True
            break

        if not self.has_video:
            self.frame1.hide()
        if not self.has_audio:
            self.frame2.hide()
        if self.is_image:
            self.hbox2.hide()
            self.hbox3.hide()
            self.label2.set_markup("<b>" + _("Image:") + "</b>")
        self.dialog.run()

    def _createUi(self):
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "clipmediaprops.ui"))
        builder.connect_signals(self)
        self.dialog = builder.get_object("Import Settings")
        self.channels = builder.get_object("channels")
        self.size_height = builder.get_object("size_height")
        self.size_width = builder.get_object("size_width")
        self.frame_rate = builder.get_object("frame_rate")
        self.aspect_ratio = builder.get_object("aspect_ratio")
        self.sample_depth = builder.get_object("sample_depth")
        self.sample_rate = builder.get_object("sample_rate")
        self.frame1 = builder.get_object("frame1")
        self.frame2 = builder.get_object("frame2")
        self.hbox2 = builder.get_object("hbox2")
        self.hbox3 = builder.get_object("hbox3")
        self.label2 = builder.get_object("label2")
        self.checkbutton1 = builder.get_object("checkbutton1")
        self.checkbutton2 = builder.get_object("checkbutton2")
        self.checkbutton3 = builder.get_object("checkbutton3")
        self.checkbutton4 = builder.get_object("checkbutton4")
        self.checkbutton5 = builder.get_object("checkbutton5")
        self.checkbutton6 = builder.get_object("checkbutton6")

    def _applyButtonCb(self, unused_button):
        _width = _height = _framerate = _par = -1
        _channels = _rate = _depth = -1

        if self.has_video:
            # This also handles the case where the video is a still image
            video = self.video_streams[0]
            if self.checkbutton1.get_active():
                _width = video.get_width()
                _height = video.get_height()
            if (self.checkbutton2.get_active() and not self.is_image):
                _framerate = gst.Fraction(video.get_framerate_num(),
                                          video.get_framerate_denom())
            if (self.checkbutton3.get_active() and not self.is_image):
                _par = gst.Fraction(video.get_par_num(),
                                    video.get_par_denom())
            self.settings.setVideoProperties(_width, _height, _framerate, _par)

        if self.has_audio:
            audio = self.audio_streams[0]
            if self.checkbutton4.get_active():
                _channels = audio.get_channels()
            if self.checkbutton5.get_active():
                _rate = audio.get_sample_rate()
            if self.checkbutton6.get_active():
                _depth = audio.get_depth()
            self.settings.setAudioProperties(_channels, _rate, _depth)

        if self.has_video or self.has_audio:
            self.project.setSettings(self.settings)

        self.dialog.destroy()

    def _cancelButtonCb(self, unused_button):
        self.dialog.destroy()
