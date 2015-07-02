# -*- coding: utf-8 -*-
# Pitivi video editor
#
#       pitivi/mediafilespreviewer.py
#
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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

from gettext import gettext as _
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Pango
from gi.repository import GstPbutils

from pitivi.settings import GlobalSettings
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import uri_is_valid
from pitivi.utils.pipeline import AssetPipeline
from pitivi.utils.ui import beautify_length, beautify_stream, SPACING
from pitivi.viewer import ViewerWidget

PREVIEW_WIDTH = 250
PREVIEW_HEIGHT = 100

GlobalSettings.addConfigSection('filechooser-preview')
GlobalSettings.addConfigOption('FCEnablePreview',
                               section='filechooser-preview',
                               key='do-preview-on-clip-import',
                               default=True)
GlobalSettings.addConfigOption('FCpreviewWidth',
                               section='filechooser-preview',
                               key='video-preview-width',
                               default=PREVIEW_WIDTH)
GlobalSettings.addConfigOption('FCpreviewHeight',
                               section='filechooser-preview',
                               key='video-preview-height',
                               default=PREVIEW_HEIGHT)

acceptable_tags = [
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

    """
    Widget for displaying a GStreamer sink with playback controls.

    @ivar settings: The settings of the app.
    @type settings: L{GlobalSettings}
    """

    def __init__(self, settings, minimal=False):
        Gtk.Grid.__init__(self)
        Loggable.__init__(self)

        self.log("Init PreviewWidget")
        self.connect('destroy', self._destroy_cb)

        self.settings = settings
        self.preview_cache = {}
        self.preview_cache_errors = {}

        self.discoverer = GstPbutils.Discoverer.new(Gst.SECOND)

        # playbin for play pics
        self.player = AssetPipeline(clip=None, name="preview-player")
        self.player.connect('eos', self._pipelineEosCb)
        self.player.connect('error', self._pipelineErrorCb)
        self.player._bus.connect('message::tag', self._tag_found_cb)

        # some global variables for preview handling
        self.is_playing = False
        self.original_dims = (PREVIEW_WIDTH, PREVIEW_HEIGHT)
        self.countinuous_seek = False
        self.slider_being_used = False
        self.current_selected_uri = ""
        self.current_preview_type = ""
        self.description = ""
        self.tags = {}

        # Gui elements:
        # Drawing area for video output
        self.preview_video = ViewerWidget(self.player.video_sink)
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

    def add_preview_request(self, dialogbox):
        """add a preview request """
        uri = dialogbox.get_preview_uri()
        if uri is None or not uri_is_valid(uri):
            return
        self.previewUri(uri)

    def previewUri(self, uri):
        self.log("Preview request for %s", uri)
        self.clear_preview()
        self.current_selected_uri = uri
        if uri in self.preview_cache:  # Already discovered
            self.log(uri + " already in cache")
            self.show_preview(uri, None)
        elif uri in self.preview_cache_errors:
            self.log(uri + " already in error cache")
            self.show_error(uri)
        else:
            self.log("Call discoverer for " + uri)
            self.fixme("Use a GESAsset here, and discover async with it")
            try:
                info = self.discoverer.discover_uri(uri)
            except Exception as e:
                self.preview_cache_errors[uri] = e
                if self.current_selected_uri == uri:
                    self.show_error(uri)
                return

            if self.current_selected_uri == uri:
                self.show_preview(uri, info)

    def show_preview(self, uri, info):
        if info:
            self.preview_cache[uri] = info
        else:
            self.log("Show preview for " + uri)
            info = self.preview_cache.get(uri, None)

        if info is None:
            self.log("No preview for " + uri)
            return

        duration = info.get_duration()
        pretty_duration = beautify_length(duration)

        videos = info.get_video_streams()
        if videos:
            video = videos[0]
            if video.is_image():
                self.current_preview_type = 'image'
                self.preview_video.hide()
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(
                    Gst.uri_get_location(uri))
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
                self.player.setClipUri(self.current_selected_uri)
                self.player.setState(Gst.State.PAUSED)
                self.pos_adj.props.upper = duration
                video_width = (
                    video.get_par_num() / video.get_par_denom()) * video.get_width()
                video_height = video.get_height()
                w, h = self.__get_best_size(video_width, video_height)
                self.preview_video.set_size_request(w, h)
                self.preview_video.setDisplayAspectRatio(
                    float(video_width) / video_height)
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
                return

            audio = audio[0]
            self.pos_adj.props.upper = duration
            self.preview_image.set_from_icon_name(
                "audio-x-generic", Gtk.IconSize.DIALOG)
            self.preview_image.show()
            self.preview_image.set_size_request(PREVIEW_WIDTH, PREVIEW_HEIGHT)
            self.description = "\n".join([
                beautify_stream(audio),
                _("<b>Duration</b>: %s") % pretty_duration])
            self.player.setState(Gst.State.NULL)
            self.player.setClipUri(self.current_selected_uri)
            self.player.setState(Gst.State.PAUSED)
            self.play_button.show()
            self.seeker.show()
            self.b_zoom_in.hide()
            self.b_zoom_out.hide()
            self.bbox.show()

    def show_error(self, unused_uri):
        self.l_error.show()
        self.b_details.show()

    def play(self):
        self.player.setState(Gst.State.PLAYING)
        self.is_playing = True
        self.play_button.set_stock_id(Gtk.STOCK_MEDIA_PAUSE)
        GLib.timeout_add(250, self._update_position)
        self.debug("Preview started")

    def pause(self):
        self.player.setState(Gst.State.PAUSED)
        self.is_playing = False
        self.play_button.set_stock_id(Gtk.STOCK_MEDIA_PLAY)
        self.log("Preview paused")

    def togglePlayback(self):
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
        self.play_button.set_stock_id(Gtk.STOCK_MEDIA_PLAY)
        self.player.setState(Gst.State.NULL)
        self.is_playing = False
        self.tags = {}
        self.current_selected_uri = ""
        self.current_preview_type = ""
        self.preview_image.hide()
        self.preview_video.hide()

    def _on_seeker_press_cb(self, widget, event):
        self.slider_being_used = True
        if event.type == Gdk.EventType.BUTTON_PRESS:
            self.countinuous_seek = True
            if self.is_playing:
                self.player.setState(Gst.State.PAUSED)
        elif event.type == Gdk.EventType.BUTTON_RELEASE:
            self.countinuous_seek = False
            value = int(widget.get_value())
            self.player.simple_seek(value)
            if self.is_playing:
                self.player.setState(Gst.State.PLAYING)
            # Now, allow gobject timeout to continue updating the slider pos:
            self.slider_being_used = False

    def _on_motion_notify_cb(self, widget, event):
        if self.countinuous_seek:
            value = int(widget.get_value())
            self.player.simple_seek(value)

    def _pipelineEosCb(self, unused_pipeline):
        self.player.setState(Gst.State.NULL)
        self.is_playing = False
        self.play_button.set_stock_id(Gtk.STOCK_MEDIA_PLAY)
        self.pos_adj.set_value(0)

    def _pipelineErrorCb(self, unused_message, unused_detail):
        self.player.setState(Gst.State.NULL)
        self.is_playing = False

    def _update_position(self, *unused_args):
        if self.is_playing and not self.slider_being_used:
            curr_pos = self.player.getPosition()
            self.pos_adj.set_value(int(curr_pos))
        return self.is_playing

    def _on_start_stop_clicked_cb(self, button):
        if self.is_playing:
            self.pause()
        else:
            self.play()

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

            w = max(w, self.settings.FCpreviewWidth)
            h = max(h, self.settings.FCpreviewHeight)
            self.preview_image.set_size_request(int(w), int(h))
            self.preview_image.set_from_pixbuf(pixbuf)
            self.preview_image.show()
            self.settings.FCpreviewWidth = int(w)
            self.settings.FCpreviewHeight = int(h)

    def _appendTag(self, taglist, tag, unused_udata):
        if tag in acceptable_tags:
            name = Gst.tag_get_nick(tag)
            type = Gst.tag_get_type(tag)
            type_getters = {GObject.TYPE_STRING: 'get_string',
                            GObject.TYPE_DOUBLE: 'get_double',
                            GObject.TYPE_FLOAT: 'get_float',
                            GObject.TYPE_INT: 'get_int',
                            GObject.TYPE_UINT: 'get_uint'}
            if type in type_getters:
                if type == GObject.TYPE_STRING:
                    value = getattr(taglist, type_getters[type])(tag)[1]
                    value = value.replace('<', ' ').replace('>', ' ')
                else:
                    value = str(getattr(taglist, type_getters[type])(tag)[1])
                self.tags[name] = value

    def _tag_found_cb(self, abus, mess):
        tag_list = mess.parse_tag()
        tag_list.foreach(self._appendTag, None)
        keys = list(self.tags.keys())
        keys.sort()
        text = self.description + "\n\n"
        for key in keys:
            text = text + "<b>" + \
                key.capitalize() + "</b>: " + self.tags[key] + "\n"
        self.l_tags.set_markup(text)

    def _on_b_details_clicked_cb(self, unused_button):
        mess = self.preview_cache_errors.get(self.current_selected_uri, None)
        if mess is not None:
            dialog = Gtk.MessageDialog(transient_for=None,
                                       modal=True,
                                       message_type=Gtk.MessageType.WARNING,
                                       buttons=Gtk.ButtonsType.OK,
                                       text=str(mess))
            dialog.set_icon_name("pitivi")
            dialog.set_title(_("Error while analyzing a file"))
            dialog.run()
            dialog.destroy()

    def _destroy_cb(self, widget):
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
