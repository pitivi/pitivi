# -*- coding: utf-8 -*-
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import Pango
import os

from gettext import gettext as _
from gi.repository.GstPbutils import Discoverer

from pitivi.configure import get_pixmap_dir
from pitivi.settings import GlobalSettings

from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import uri_is_valid
from pitivi.utils.ui import beautify_length, beautify_stream,\
    SPACING

from pitivi.viewer import ViewerWidget

DEFAULT_AUDIO_IMAGE = os.path.join(get_pixmap_dir(), "pitivi-sound.png")

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

acceptable_tags = [Gst.TAG_ALBUM_ARTIST,
                    Gst.TAG_ARTIST,
                    Gst.TAG_TITLE,
                    Gst.TAG_ALBUM,
                    Gst.TAG_BITRATE,
                    Gst.TAG_COMPOSER,
                    Gst.TAG_GENRE,
                    Gst.TAG_PERFORMER,
                    Gst.TAG_DATE]


class PreviewWidget(Gtk.VBox, Loggable):

    def __init__(self, instance):
        GObject.GObject.__init__(self)
        Loggable.__init__(self)

        self.log("Init PreviewWidget")
        self.connect('destroy', self._destroy_cb)

        self.settings = instance.settings
        self.preview_cache = {}
        self.preview_cache_errors = {}

        self.discoverer = Discoverer.new(Gst.SECOND)

        #playbin for play pics
        self.player = Gst.ElementFactory.make("playbin", "preview-player")
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self._bus_message_cb)
        bus.enable_sync_message_emission()
        bus.connect('sync-message::element', self._sync_message_cb)
        bus.connect('message::tag', self._tag_found_cb)
        self.__videosink = self.player.get_property("video-sink")
        self.__fakesink = Gst.ElementFactory.make("fakesink", "fakesink")

        #some global variables for preview handling
        self.is_playing = False
        self.time_format = Gst.Format(Gst.FORMAT_TIME)
        self.original_dims = (PREVIEW_WIDTH, PREVIEW_HEIGHT)
        self.countinuous_seek = False
        self.current_selected_uri = ""
        self.current_preview_type = ""
        self.description = ""
        self.tags = {}

        # Gui elements:
        # Drawing area for video output
        self.preview_video = ViewerWidget()
        self.preview_video.modify_bg(Gtk.StateType.NORMAL, self.preview_video.style.black)
        self.pack_start(self.preview_video, False, True, 0)

        # An image for images and audio
        self.preview_image = Gtk.Image()
        self.preview_image.set_size_request(self.settings.FCpreviewWidth, self.settings.FCpreviewHeight)
        self.preview_image.show()
        self.pack_start(self.preview_image, False, True, 0)

        # Play button
        self.bbox = Gtk.HBox()
        self.play_button = Gtk.ToolButton(Gtk.STOCK_MEDIA_PLAY)
        self.play_button.connect("clicked", self._on_start_stop_clicked_cb)
        self.bbox.pack_start(self.play_button, False, True, 0)

        #Scale for position handling
        self.pos_adj = Gtk.Adjustment()
        self.seeker = Gtk.HScale(self.pos_adj)
        self.seeker.connect('button-press-event', self._on_seeker_press_cb)
        self.seeker.connect('button-release-event', self._on_seeker_press_cb)
        self.seeker.connect('motion-notify-event', self._on_motion_notify_cb)
        self.seeker.set_draw_value(False)
        self.seeker.show()
        self.bbox.pack_start(self.seeker, True, True, 0)

        # Zoom buttons
        self.b_zoom_in = Gtk.ToolButton(Gtk.STOCK_ZOOM_IN)
        self.b_zoom_in.connect("clicked", self._on_zoom_clicked_cb, 1)
        self.b_zoom_out = Gtk.ToolButton(Gtk.STOCK_ZOOM_OUT)
        self.b_zoom_out.connect("clicked", self._on_zoom_clicked_cb, -1)
        self.bbox.pack_start(self.b_zoom_in, False, True, 0)
        self.bbox.pack_start(self.b_zoom_out, False, True, 0)
        self.bbox.show_all()
        self.pack_start(self.bbox, False, False, 0)

        # Label for metadata tags
        self.l_tags = Gtk.Label()
        self.l_tags.set_justify(Gtk.Justification.LEFT)
        self.l_tags.set_ellipsize(Pango.EllipsizeMode.END)
        self.l_tags.show()
        self.pack_start(self.l_tags, False, False, 0)

        # Error handling
        vbox = Gtk.VBox()
        vbox.set_spacing(SPACING)
        self.l_error = Gtk.Label(label=_("PiTiVi can not preview this file."))
        self.b_details = Gtk.Button(_("More info"))
        self.b_details.connect('clicked', self._on_b_details_clicked_cb)
        vbox.pack_start(self.l_error, True, True, 0)
        vbox.pack_start(self.b_details, False, False, 0)
        vbox.show()
        self.pack_start(vbox, False, False, 0)

    def setMinimal(self):
        self.remove(self.l_tags)
        self.b_zoom_in.hide()
        self.b_zoom_out.hide()
        # Allow expanding/filling and pack the video preview below the controls
        self.set_child_packing(self.preview_video, True, True, 0, Gtk.PACK_END)

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
            try:
                info = self.discoverer.discover_uri(uri)
            except Exception, e:
                if e is not None:
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
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(Gst.uri_get_location(uri))
                pixbuf_w = pixbuf.get_width()
                pixbuf_h = pixbuf.get_height()
                w, h = self.__get_best_size(pixbuf_w, pixbuf_h)
                pixbuf = pixbuf.scale_simple(w, h, GdkPixbuf.InterpType.NEAREST)
                self.preview_image.set_from_pixbuf(pixbuf)
                self.preview_image.set_size_request(self.settings.FCpreviewWidth, self.settings.FCpreviewHeight)
                self.preview_image.show()
                self.bbox.show()
                self.play_button.hide()
                self.seeker.hide()
                self.b_zoom_in.show()
                self.b_zoom_out.show()
            else:
                self.current_preview_type = 'video'
                self.preview_image.hide()
                self.player.set_property("video-sink", self.__videosink)
                self.player.set_property("uri", self.current_selected_uri)
                self.player.set_state(Gst.State.PAUSED)
                self.pos_adj.props.upper = duration
                w, h = self.__get_best_size((video.get_par_num() / video.get_par_denom()) * video.get_width(),
                    video.get_height())
                self.preview_video.set_size_request(w, h)
                self.preview_video.show()
                self.bbox.show()
                self.play_button.show()
                self.seeker.show()
                self.b_zoom_in.show()
                self.b_zoom_out.show()
                self.description = _(u"<b>Resolution</b>: %d×%d") % \
                    ((video.get_par_num() / video.get_par_denom()) * video.get_width(), video.get_height()) +\
                     "\n" + _("<b>Duration</b>: %s") % pretty_duration + "\n"
        else:
            self.current_preview_type = 'audio'
            self.preview_video.hide()
            audio = info.get_audio_streams()

            if not audio:
                return

            audio = audio[0]
            self.pos_adj.props.upper = duration
            self.preview_image.set_from_file(DEFAULT_AUDIO_IMAGE)
            self.preview_image.show()
            self.preview_image.set_size_request(PREVIEW_WIDTH, PREVIEW_HEIGHT)
            self.description = beautify_stream(audio) + "\n" + \
                _("<b>Duration</b>: %s") % pretty_duration + "\n"
            self.player.set_state(Gst.State.NULL)
            self.player.set_property("uri", self.current_selected_uri)
            self.player.set_property("video-sink", self.__fakesink)
            self.player.set_state(Gst.State.PAUSED)
            self.play_button.show()
            self.seeker.show()
            self.b_zoom_in.hide()
            self.b_zoom_out.hide()
            self.bbox.show()

    def show_error(self, uri):
        self.l_error.show()
        self.b_details.show()

    def play(self):
        self.player.set_state(Gst.State.PLAYING)
        self.is_playing = True
        self.play_button.set_stock_id(Gtk.STOCK_MEDIA_PAUSE)
        #Make sure position is updated regularly
        GObject.timeout_add(500, self._update_position)
        self.debug("Preview started")

    def pause(self):
        self.player.set_state(Gst.State.PAUSED)
        self.is_playing = False
        self.play_button.set_stock_id(Gtk.STOCK_MEDIA_PLAY)
        self.log("Preview paused")

    def clear_preview(self):
        self.log("Reset PreviewWidget ")
        self.seeker.set_value(0)
        self.bbox.hide()
        self.l_error.hide()
        self.b_details.hide()
        self.description = ""
        self.l_tags.set_markup("")
        self.play_button.set_stock_id(Gtk.STOCK_MEDIA_PLAY)
        self.player.set_state(Gst.State.NULL)
        self.is_playing = False
        self.tags = {}
        self.current_selected_uri = ""
        self.current_preview_type = ""
        self.preview_image.hide()
        self.preview_video.hide()

    def _on_seeker_press_cb(self, widget, event):
        event.button = 2
        if event.type == Gdk.EventType.BUTTON_PRESS:
            self.countinuous_seek = True
            if self.is_playing:
                self.player.set_state(Gst.State.PAUSED)
        elif event.type == Gdk.BUTTON_RELEASE:
            self.countinuous_seek = False
            value = long(widget.get_value())
            self.player.seek_simple(self.time_format, Gst.SeekFlags.FLUSH, value)
            if self.is_playing:
                self.player.set_state(Gst.State.PLAYING)

    def _on_motion_notify_cb(self, widget, event):
        if self.countinuous_seek:
            value = widget.get_value()
            self.player.seek_simple(self.time_format, Gst.SeekFlags.FLUSH, value)

    def _bus_message_cb(self, bus, message):
        if message.type == Gst.MESSAGE_EOS:
            self.player.set_state(Gst.State.NULL)
            self.is_playing = False
            self.play_button.set_stock_id(Gtk.STOCK_MEDIA_PLAY)
            self.pos_adj.set_value(0)
        elif message.type == Gst.MESSAGE_ERROR:
            self.player.set_state(Gst.State.NULL)
            self.is_playing = False
            err, dbg = message.parse_error()
            self.error("Error: %s " % err, dbg)

    def _update_position(self, *args):
        if self.is_playing:
            curr_pos = self.player.query_position(self.time_format)[1]
            self.pos_adj.set_value(long(curr_pos))
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
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(Gst.uri_get_location(self.current_selected_uri))
            pixbuf = pixbuf.scale_simple(int(w), int(h), GdkPixbuf.InterpType.BILINEAR)

            w = max(w, self.settings.FCpreviewWidth)
            h = max(h, self.settings.FCpreviewHeight)
            self.preview_image.set_size_request(int(w), int(h))
            self.preview_image.set_from_pixbuf(pixbuf)
            self.preview_image.show()
            self.settings.FCpreviewWidth = int(w)
            self.settings.FCpreviewHeight = int(h)

    def _sync_message_cb(self, bus, mess):
        if mess.type == Gst.MESSAGE_ELEMENT:
            if mess.has_name('prepare-window-handle'):
                sink = mess.src

                # We need to set force-aspect-ratio and handle-expose properties
                # to the real videosink. Depending on how the pipeline was
                # configured and the version of gstreamer, the source of this
                # message could be the videosink itself or playsink. If it's
                # playsink, we need to get the videosink that is inside it.
                # Even better, the sink inside playsink could be autovideosink,
                # which isn't a real sink, therefore we get the sink inside it.
                try:
                    if sink.get_factory().get_name() == 'playsink':
                        realsink = sink.get_property('video-sink')
                    else:
                        realsink = sink
                    if realsink.get_factory().get_name() == 'autovideosink':
                        realsink = realsink.iterate_sinks().next()[1]

                    realsink.set_property('force-aspect-ratio', True)
                    realsink.set_property("handle-expose", True)
                finally:
                    Gdk.threads_enter()
                    sink.set_window_handle(self.preview_video.window_xid)
                    sink.expose()
                    Gdk.threads_leave()
        return Gst.BUS_PASS

    def _appendTag(self, taglist, tag, unused_udata):
            if tag in acceptable_tags and Gst.tag_get_type(tag) in (GObject.TYPE_STRING,
                                   GObject.TYPE_DOUBLE,
                                   GObject.TYPE_FLOAT,
                                   GObject.TYPE_INT,
                                   GObject.TYPE_UINT):
                name = Gst.tag_get_nick(tag)
                value = unicode(taglist.get_string(tag)[1]).replace('<', ' ').replace('>', ' ')
                self.tags[name] = value

    def _tag_found_cb(self, abus, mess):
        tag_list = mess.parse_tag()
        tag_list.foreach(self._appendTag, None)
        keys = self.tags.keys()
        keys.sort()
        text = self.description + "\n"
        for key in keys:
            text = text + "<b>" + key.capitalize() + "</b>: " + self.tags[key] + "\n"
        self.l_tags.set_markup(text)

    def _on_b_details_clicked_cb(self, unused_button):
        mess = self.preview_cache_errors.get(self.current_selected_uri, None)
        if mess is not None:
            dialog = Gtk.MessageDialog(None,
                Gtk.DialogFlags.MODAL,
                Gtk.MessageType.WARNING,
                Gtk.ButtonsType.OK,
                str(mess))
            dialog.set_icon_name("pitivi")
            dialog.set_title(_("Error while analyzing a file"))
            dialog.run()
            dialog.destroy()

    def _destroy_cb(self, widget):
        self.player.set_state(Gst.State.NULL)
        self.is_playing = False
        #FIXME: are the following lines really needed?
        del self.player
        del self.preview_cache

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
