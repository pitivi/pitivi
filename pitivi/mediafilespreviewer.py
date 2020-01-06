# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2011, Pier Carteri <pier.carteri@gmail.com>
# Copyright (c) 2012, Thibault Saunier <tsaunier@gnome.org>
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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
import html
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GES
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import Pango

from pitivi.settings import GlobalSettings
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import uri_is_valid
from pitivi.utils.pipeline import AssetPipeline
from pitivi.utils.ui import beautify_length
from pitivi.utils.ui import beautify_stream
from pitivi.utils.ui import SPACING
from pitivi.viewer.viewer import ViewerWidget

PREVIEW_WIDTH = 250
PREVIEW_HEIGHT = 100

GlobalSettings.add_config_section('filechooser-preview')
GlobalSettings.add_config_option('FCEnablePreview',
                                 section='filechooser-preview',
                                 key='do-preview-on-clip-import',
                                 default=True)
GlobalSettings.add_config_option('FCpreviewWidth',
                                 section='filechooser-preview',
                                 key='video-preview-width',
                                 default=PREVIEW_WIDTH)
GlobalSettings.add_config_option('FCpreviewHeight',
                                 section='filechooser-preview',
                                 key='video-preview-height',
                                 default=PREVIEW_HEIGHT)

ACCEPTABLE_TAGS = [
    Gst.TAG_ALBUM_ARTIST,
    Gst.TAG_ARTIST,
    Gst.TAG_TITLE,
    Gst.TAG_ALBUM,
    Gst.TAG_BITRATE,
    Gst.TAG_COMPOSER,
    Gst.TAG_GENRE,
    Gst.TAG_PERFORMER,
    Gst.TAG_DATE,
    Gst.TAG_COPYRIGHT]


class PreviewWidget(Gtk.Grid, Loggable):
    """Widget for displaying a GStreamer sink with playback controls.

    Args:
        settings (GlobalSettings): The settings of the app.
    """

    def __init__(self, settings, minimal=False, discover_sync=False):
        Gtk.Grid.__init__(self)
        Loggable.__init__(self)

        self.log("Init PreviewWidget")
        self.settings = settings
        self.error_message = None

        # playbin for play pics
        self.player = AssetPipeline(name="preview-player")
        self.player.connect('eos', self._pipeline_eos_cb)
        self.player.connect('error', self._pipeline_error_cb)
        self.player._bus.connect('message::tag', self._tag_found_cb)

        # some global variables for preview handling
        self.is_playing = False
        self.at_eos = False
        self.original_dims = (PREVIEW_WIDTH, PREVIEW_HEIGHT)
        self.countinuous_seek = False
        self.slider_being_used = False
        self.current_selected_uri = ""
        self.current_preview_type = ""
        self.play_on_discover = False
        self.description = ""

        # Gui elements:
        # Drawing area for video output
        unused_sink, sink_widget = self.player.create_sink()
        self.preview_video = ViewerWidget(sink_widget)
        self.preview_video.props.hexpand = minimal
        self.preview_video.props.vexpand = minimal
        self.preview_video.show_all()
        self.attach(self.preview_video, 0, 0, 1, 1)

        # An image for images and audio
        self.preview_image = Gtk.Image()
        self.preview_image.set_size_request(
            self.settings.FCpreviewWidth, self.settings.FCpreviewHeight)
        self.preview_image.show()
        self.attach(self.preview_image, 0, 1, 1, 1)

        # Play button
        self.bbox = Gtk.Box()
        self.bbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.play_button = Gtk.ToolButton()
        self.play_button.set_icon_name("media-playback-start")
        self.play_button.connect("clicked", self._on_start_stop_clicked_cb)
        self.bbox.pack_start(self.play_button, False, False, 0)

        # Scale for position handling
        self.pos_adj = Gtk.Adjustment()
        self.seeker = Gtk.Scale.new(Gtk.Orientation.HORIZONTAL, self.pos_adj)
        self.seeker.connect('button-press-event', self._on_seeker_press_cb)
        self.seeker.connect('button-release-event', self._on_seeker_press_cb)
        self.seeker.connect('motion-notify-event', self._on_motion_notify_cb)
        self.seeker.set_draw_value(False)
        self.seeker.show()
        self.bbox.pack_start(self.seeker, True, True, 0)

        # Zoom buttons
        self.b_zoom_in = Gtk.ToolButton()
        self.b_zoom_in.set_icon_name("zoom-in")
        self.b_zoom_in.connect("clicked", self._on_zoom_clicked_cb, 1)
        self.b_zoom_out = Gtk.ToolButton()
        self.b_zoom_out.set_icon_name("zoom-out")
        self.b_zoom_out.connect("clicked", self._on_zoom_clicked_cb, -1)
        self.bbox.pack_start(self.b_zoom_in, False, False, 0)
        self.bbox.pack_start(self.b_zoom_out, False, False, 0)
        self.bbox.show_all()
        self.attach(self.bbox, 0, 2, 1, 1)

        # Label for metadata tags
        self.l_tags = Gtk.Label()
        self.l_tags.set_justify(Gtk.Justification.LEFT)
        self.l_tags.set_ellipsize(Pango.EllipsizeMode.END)
        self.l_tags.show()
        self.attach(self.l_tags, 0, 3, 1, 1)

        # Error handling
        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.VERTICAL)
        vbox.set_spacing(SPACING)
        self.l_error = Gtk.Label(label=_("Pitivi can not preview this file."))
        self.b_details = Gtk.Button.new_with_label(_("More info"))
        self.b_details.connect('clicked', self._on_b_details_clicked_cb)
        vbox.pack_start(self.l_error, True, True, 0)
        vbox.pack_start(self.b_details, False, False, 0)
        vbox.show()
        self.attach(vbox, 0, 4, 1, 1)

        if minimal:
            self.remove(self.l_tags)
            self.bbox.remove(self.b_zoom_in)
            self.bbox.remove(self.b_zoom_out)

        self.clear_preview()
        self._discover_sync = discover_sync

    def update_preview_cb(self, file_chooser):
        """Previews the URI of the specified file chooser.

        Args:
            file_chooser (Gtk.FileChooser): The file chooser providing the URI.
        """
        uri = file_chooser.get_preview_uri()
        previewable = uri and uri_is_valid(uri)
        if not previewable:
            self.clear_preview()
            return
        self.preview_uri(uri)

    def preview_uri(self, uri):
        self.log("Preview request for %s", uri)
        self.clear_preview()
        self.current_selected_uri = uri

        if self._discover_sync:
            self._handle_new_asset(uri=uri)
        else:
            GES.UriClipAsset.new(uri, None, self.__asset_loaded_cb)

    def _handle_new_asset(self, async_result=None, uri=None):
        try:
            if uri:
                asset = GES.UriClipAsset.request_sync(uri)
            else:
                asset = GES.Asset.request_finish(async_result)
                uri = asset.get_id()
        except GLib.Error as error:
            self.log("Failed discovering %s: %s", uri, error.message)
            self._show_error(error.message)
            return

        self.log("Discovered %s", uri)
        if not self._show_preview(uri, asset.get_info()):
            return
        if self.play_on_discover:
            self.play_on_discover = False
            self.play()

    def __asset_loaded_cb(self, source, res):
        self._handle_new_asset(async_result=res)

    def _show_preview(self, uri, info):
        self.log("Show preview for %s", uri)
        duration = info.get_duration()
        pretty_duration = beautify_length(duration)

        videos = info.get_video_streams()
        if videos:
            video = videos[0]
            if video.is_image():
                self.current_preview_type = 'image'
                self.preview_video.hide()
                path = Gst.uri_get_location(uri)
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
                except GLib.Error as error:
                    self.debug("Failed loading image because: %s", error)
                    self._show_error(error.message)
                    return False
                pixbuf_w = pixbuf.get_width()
                pixbuf_h = pixbuf.get_height()
                w, h = self.__get_best_size(pixbuf_w, pixbuf_h)
                pixbuf = pixbuf.scale_simple(
                    w, h, GdkPixbuf.InterpType.NEAREST)
                self.preview_image.set_from_pixbuf(pixbuf)
                self.preview_image.set_size_request(
                    self.settings.FCpreviewWidth, self.settings.FCpreviewHeight)
                self.preview_image.show()
                self.bbox.show()
                self.play_button.hide()
                self.seeker.hide()
                self.b_zoom_in.show()
                self.b_zoom_out.show()
            else:
                self.current_preview_type = 'video'
                self.preview_image.hide()
                self.player.uri = self.current_selected_uri
                self.player.set_simple_state(Gst.State.PAUSED)
                self.pos_adj.props.upper = duration
                video_width = video.get_natural_width()
                video_height = video.get_natural_height()
                w, h = self.__get_best_size(video_width, video_height)
                self.preview_video.set_size_request(w, h)
                self.preview_video.props.ratio = video_width / video_height
                self.preview_video.show()
                self.bbox.show()
                self.play_button.show()
                self.seeker.show()
                self.b_zoom_in.show()
                self.b_zoom_out.show()
                self.description = "\n".join([
                    _("<b>Resolution</b>: %d×%d") % (
                        video_width, video_height),
                    _("<b>Duration</b>: %s") % pretty_duration])
        else:
            self.current_preview_type = 'audio'
            self.preview_video.hide()
            audio = info.get_audio_streams()
            if not audio:
                self.debug("Audio has no streams")
                return False

            audio = audio[0]
            self.pos_adj.props.upper = duration
            self.preview_image.set_from_icon_name(
                "audio-x-generic", Gtk.IconSize.DIALOG)
            self.preview_image.show()
            self.preview_image.set_size_request(PREVIEW_WIDTH, PREVIEW_HEIGHT)
            self.description = "\n".join([
                beautify_stream(audio),
                _("<b>Duration</b>: %s") % pretty_duration])
            self.player.set_simple_state(Gst.State.NULL)
            self.player.uri = self.current_selected_uri
            self.player.set_simple_state(Gst.State.PAUSED)
            self.play_button.show()
            self.seeker.show()
            self.b_zoom_in.hide()
            self.b_zoom_out.hide()
            self.bbox.show()
        return True

    def _show_error(self, error_message):
        self.error_message = error_message
        self.l_error.show()
        self.b_details.show()

    def play(self):
        if not self.current_preview_type:
            self.play_on_discover = True
            return
        if self.at_eos:
            # The content played once already and the pipeline is at the end.
            self.at_eos = False
            self.player.simple_seek(0)
        self.player.set_simple_state(Gst.State.PLAYING)
        self.is_playing = True
        self.play_button.set_icon_name("media-playback-pause")
        GLib.timeout_add(250, self._update_position)
        self.debug("Preview started")

    def pause(self, state=Gst.State.PAUSED):
        if state is not None:
            self.player.set_simple_state(state)
        self.is_playing = False
        self.play_button.set_icon_name("media-playback-start")
        self.log("Preview paused")

    def toggle_playback(self):
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def clear_preview(self):
        self.log("Reset PreviewWidget")
        self.seeker.set_value(0)
        self.bbox.hide()
        self.l_error.hide()
        self.b_details.hide()
        self.description = ""
        self.l_tags.set_markup("")
        self.pause(state=Gst.State.NULL)
        self.current_selected_uri = ""
        self.current_preview_type = ""
        self.preview_image.hide()
        self.preview_video.hide()

    def _on_seeker_press_cb(self, widget, event):
        self.slider_being_used = True
        if event.type == Gdk.EventType.BUTTON_PRESS:
            self.countinuous_seek = True
            if self.is_playing:
                self.player.set_simple_state(Gst.State.PAUSED)
        elif event.type == Gdk.EventType.BUTTON_RELEASE:
            self.countinuous_seek = False
            value = int(widget.get_value())
            self.player.simple_seek(value)
            self.at_eos = False
            if self.is_playing:
                self.player.set_simple_state(Gst.State.PLAYING)
            # Now, allow gobject timeout to continue updating the slider pos:
            self.slider_being_used = False

    def _on_motion_notify_cb(self, widget, event):
        if self.countinuous_seek:
            value = int(widget.get_value())
            self.player.simple_seek(value)
            self.at_eos = False

    def _pipeline_eos_cb(self, unused_pipeline):
        self._update_position()
        self.pause()
        # The pipeline is at the end. Leave it like that so the last frame
        # is displayed.
        self.at_eos = True

    def _pipeline_error_cb(self, unused_pipeline, unused_message, unused_detail):
        self.pause(state=Gst.State.NULL)

    def _update_position(self, *unused_args):
        if self.is_playing and not self.slider_being_used:
            curr_pos = self.player.get_position()
            self.pos_adj.set_value(int(curr_pos))
        return self.is_playing

    def _on_start_stop_clicked_cb(self, button):
        self.toggle_playback()

    def _on_zoom_clicked_cb(self, button, increment):
        if self.current_preview_type == 'video':
            w, h = self.preview_video.get_size_request()
            if increment > 0:
                w *= 1.2
                h *= 1.2
            else:
                w *= 0.8
                h *= 0.8
                if (w, h) < self.original_dims:
                    (w, h) = self.original_dims
            self.preview_video.set_size_request(int(w), int(h))
            self.settings.FCpreviewWidth = int(w)
            self.settings.FCpreviewHeight = int(h)
        elif self.current_preview_type == 'image':
            pixbuf = self.preview_image.get_pixbuf()
            w = pixbuf.get_width()
            h = pixbuf.get_height()
            if increment > 0:
                w *= 1.2
                h *= 1.2
            else:
                w *= 0.8
                h *= 0.8
                if (w, h) < self.original_dims:
                    (w, h) = self.original_dims
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(
                Gst.uri_get_location(self.current_selected_uri))
            pixbuf = pixbuf.scale_simple(
                int(w), int(h), GdkPixbuf.InterpType.BILINEAR)

            self.preview_image.set_size_request(int(w), int(h))
            self.preview_image.set_from_pixbuf(pixbuf)
            self.preview_image.show()
            self.settings.FCpreviewWidth = int(w)
            self.settings.FCpreviewHeight = int(h)

    def _append_tag(self, taglist, tag, tags):
        if tag in ACCEPTABLE_TAGS:
            tag_name = Gst.tag_get_nick(tag)
            tag_type = Gst.tag_get_type(tag)
            type_getters = {GObject.TYPE_STRING: 'get_string',
                            GObject.TYPE_DOUBLE: 'get_double',
                            GObject.TYPE_FLOAT: 'get_float',
                            GObject.TYPE_INT: 'get_int',
                            GObject.TYPE_UINT: 'get_uint'}
            if tag_type in type_getters:
                res, value = getattr(taglist, type_getters[tag_type])(tag)
                assert res
                if not tag_type == GObject.TYPE_STRING:
                    value = str(value)
                tags[tag_name] = value

    def _tag_found_cb(self, unused_bus, message):
        tag_list = message.parse_tag()
        tags = {}
        tag_list.foreach(self._append_tag, tags)
        items = list(tags.items())
        items.sort()
        text = self.description + "\n\n"
        for key, value in items:
            escaped = html.escape(value)
            text = text + "<b>%s</b>: %s\n" % (key, escaped)
        self.l_tags.set_markup(text)

    def _on_b_details_clicked_cb(self, unused_button):
        if not self.error_message:
            return

        dialog = Gtk.MessageDialog(transient_for=None,
                                   modal=True,
                                   message_type=Gtk.MessageType.WARNING,
                                   buttons=Gtk.ButtonsType.OK,
                                   text=self.error_message)
        dialog.set_icon_name("pitivi")
        dialog.set_title(_("Error while analyzing a file"))
        dialog.run()
        dialog.destroy()

    def do_destroy(self):
        """Handles the destruction of the widget."""
        self.player.release()
        self.is_playing = False

    def __get_best_size(self, width_in, height_in):
        if width_in > height_in:
            if self.settings.FCpreviewWidth < width_in:
                w = self.settings.FCpreviewWidth
                h = height_in * w / width_in
                return (w, h)
        else:
            if self.settings.FCpreviewHeight < height_in:
                h = self.settings.FCpreviewHeight
                w = width_in * h / height_in
                return (w, h)
        return (width_in, height_in)
