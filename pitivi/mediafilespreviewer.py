# -*- coding: utf-8 -*-
import gobject
import gst
import gtk
import pango
import os

from gettext import gettext as _
from gst.pbutils import Discoverer

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


class PreviewWidget(gtk.VBox, Loggable):

    def __init__(self, instance):
        gtk.VBox.__init__(self)
        Loggable.__init__(self)

        self.log("Init PreviewWidget")
        self.connect('destroy', self._destroy_cb)

        self.settings = instance.settings
        self.preview_cache = {}
        self.preview_cache_errors = {}

        self.discoverer = Discoverer.new(gst.SECOND)

        #playbin for play pics
        self._unsurePlaybin()
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self._bus_message_cb)
        bus.enable_sync_message_emission()
        bus.connect('sync-message::element', self._sync_message_cb)
        bus.connect('message::tag', self._tag_found_cb)
        self.__videosink = self.player.get_property("video-sink")
        self.__fakesink = gst.element_factory_make("fakesink", "fakesink")

        #some global variables for preview handling
        self.is_playing = False
        self.time_format = gst.Format(gst.FORMAT_TIME)
        self.original_dims = (PREVIEW_WIDTH, PREVIEW_HEIGHT)
        self.countinuous_seek = False
        self.current_selected_uri = ""
        self.current_preview_type = ""
        self.description = ""
        self.tags = {}

        # Gui elements:
        # Drawing area for video output
        self.preview_video = ViewerWidget()
        self.preview_video.modify_bg(gtk.STATE_NORMAL, self.preview_video.style.black)
        self.pack_start(self.preview_video, expand=False)

        # An image for images and audio
        self.preview_image = gtk.Image()
        self.preview_image.set_size_request(self.settings.FCpreviewWidth, self.settings.FCpreviewHeight)
        self.preview_image.show()
        self.pack_start(self.preview_image, expand=False)

        # Play button
        self.bbox = gtk.HBox()
        self.play_button = gtk.ToolButton(gtk.STOCK_MEDIA_PLAY)
        self.play_button.connect("clicked", self._on_start_stop_clicked_cb)
        self.bbox.pack_start(self.play_button, expand=False)

        #Scale for position handling
        self.pos_adj = gtk.Adjustment()
        self.seeker = gtk.HScale(self.pos_adj)
        self.seeker.set_update_policy(gtk.UPDATE_DISCONTINUOUS)
        self.seeker.connect('button-press-event', self._on_seeker_press_cb)
        self.seeker.connect('button-release-event', self._on_seeker_press_cb)
        self.seeker.connect('motion-notify-event', self._on_motion_notify_cb)
        self.seeker.set_draw_value(False)
        self.seeker.show()
        self.bbox.pack_start(self.seeker)

        # Zoom buttons
        self.b_zoom_in = gtk.ToolButton(gtk.STOCK_ZOOM_IN)
        self.b_zoom_in.connect("clicked", self._on_zoom_clicked_cb, 1)
        self.b_zoom_out = gtk.ToolButton(gtk.STOCK_ZOOM_OUT)
        self.b_zoom_out.connect("clicked", self._on_zoom_clicked_cb, -1)
        self.bbox.pack_start(self.b_zoom_in, expand=False)
        self.bbox.pack_start(self.b_zoom_out, expand=False)
        self.bbox.show_all()
        self.pack_start(self.bbox, expand=False, fill=False)

        # Label for metadata tags
        self.l_tags = gtk.Label()
        self.l_tags.set_justify(gtk.JUSTIFY_LEFT)
        self.l_tags.set_ellipsize(pango.ELLIPSIZE_END)
        self.l_tags.show()
        self.pack_start(self.l_tags, expand=False, fill=False)

        # Error handling
        vbox = gtk.VBox()
        vbox.set_spacing(SPACING)
        self.l_error = gtk.Label(_("PiTiVi can not preview this file."))
        self.b_details = gtk.Button(_("More info"))
        self.b_details.connect('clicked', self._on_b_details_clicked_cb)
        vbox.pack_start(self.l_error)
        vbox.pack_start(self.b_details, expand=False, fill=False)
        vbox.show()
        self.pack_start(vbox, expand=False, fill=False)

    def _unsurePlaybin(self):
        # FIXME GI, remove that method
        self.player = gst.element_factory_make("playbin", "preview-player")

    def setMinimal(self):
        self.remove(self.l_tags)
        self.b_zoom_in.hide()
        self.b_zoom_out.hide()
        # Allow expanding/filling and pack the video preview below the controls
        self.set_child_packing(self.preview_video, True, True, 0, gtk.PACK_END)

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
                pixbuf = gtk.gdk.pixbuf_new_from_file(gst.uri_get_location(uri))
                pixbuf_w = pixbuf.get_width()
                pixbuf_h = pixbuf.get_height()
                w, h = self.__get_best_size(pixbuf_w, pixbuf_h)
                pixbuf = pixbuf.scale_simple(w, h, gtk.gdk.INTERP_NEAREST)
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
                self.player.set_state(gst.STATE_PAUSED)
                self.pos_adj.upper = duration
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
            self.pos_adj.upper = duration
            self.preview_image.set_from_file(DEFAULT_AUDIO_IMAGE)
            self.preview_image.show()
            self.preview_image.set_size_request(PREVIEW_WIDTH, PREVIEW_HEIGHT)
            self.description = beautify_stream(audio) + "\n" + \
                _("<b>Duration</b>: %s") % pretty_duration + "\n"
            self.player.set_state(gst.STATE_NULL)
            self.player.set_property("uri", self.current_selected_uri)
            self.player.set_property("video-sink", self.__fakesink)
            self.player.set_state(gst.STATE_PAUSED)
            self.play_button.show()
            self.seeker.show()
            self.b_zoom_in.hide()
            self.b_zoom_out.hide()
            self.bbox.show()

    def show_error(self, uri):
        self.l_error.show()
        self.b_details.show()

    def play(self):
        self.player.set_state(gst.STATE_PLAYING)
        self.is_playing = True
        self.play_button.set_stock_id(gtk.STOCK_MEDIA_PAUSE)
        #Make sure position is updated regularly
        gobject.timeout_add(500, self._update_position)
        self.debug("Preview started")

    def pause(self):
        self.player.set_state(gst.STATE_PAUSED)
        self.is_playing = False
        self.play_button.set_stock_id(gtk.STOCK_MEDIA_PLAY)
        self.log("Preview paused")

    def clear_preview(self):
        self.log("Reset PreviewWidget ")
        self.seeker.set_value(0)
        self.bbox.hide()
        self.l_error.hide()
        self.b_details.hide()
        self.description = ""
        self.l_tags.set_markup("")
        self.play_button.set_stock_id(gtk.STOCK_MEDIA_PLAY)
        self.player.set_state(gst.STATE_NULL)
        self.is_playing = False
        self.tags = {}
        self.current_selected_uri = ""
        self.current_preview_type = ""
        self.preview_image.hide()
        self.preview_video.hide()

    def _on_seeker_press_cb(self, widget, event):
        event.button = 2
        if event.type == gtk.gdk.BUTTON_PRESS:
            self.countinuous_seek = True
            if self.is_playing:
                self.player.set_state(gst.STATE_PAUSED)
        elif event.type == gtk.gdk.BUTTON_RELEASE:
            self.countinuous_seek = False
            value = long(widget.get_value())
            self.player.seek_simple(self.time_format, gst.SEEK_FLAG_FLUSH, value)
            if self.is_playing:
                self.player.set_state(gst.STATE_PLAYING)

    def _on_motion_notify_cb(self, widget, event):
        if self.countinuous_seek:
            value = widget.get_value()
            self.player.seek_simple(self.time_format, gst.SEEK_FLAG_FLUSH, value)

    def _bus_message_cb(self, bus, message):
        if message.type == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
            self.is_playing = False
            self.play_button.set_stock_id(gtk.STOCK_MEDIA_PLAY)
            self.pos_adj.set_value(0)
        elif message.type == gst.MESSAGE_ERROR:
            self.player.set_state(gst.STATE_NULL)
            self.is_playing = False
            err, dbg = message.parse_error()
            self.error("Error: %s " % err, dbg)

    def _update_position(self, *args):
        if self.is_playing:
            curr_pos = self.player.query_position(self.time_format, None)[0]
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
            pixbuf = gtk.gdk.pixbuf_new_from_file(gst.uri_get_location(self.current_selected_uri))
            pixbuf = pixbuf.scale_simple(int(w), int(h), gtk.gdk.INTERP_BILINEAR)

            w = max(w, self.settings.FCpreviewWidth)
            h = max(h, self.settings.FCpreviewHeight)
            self.preview_image.set_size_request(int(w), int(h))
            self.preview_image.set_from_pixbuf(pixbuf)
            self.preview_image.show()
            self.settings.FCpreviewWidth = int(w)
            self.settings.FCpreviewHeight = int(h)

    def _sync_message_cb(self, bus, mess):
        if mess.type == gst.MESSAGE_ELEMENT:
            if mess.structure.get_name() == 'prepare-xwindow-id':
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
                        realsink = realsink.sinks().next()

                    realsink.set_property('force-aspect-ratio', True)
                    realsink.set_property("handle-expose", True)
                finally:
                    gtk.gdk.threads_enter()
                    sink.set_xwindow_id(self.preview_video.window_xid)
                    sink.expose()
                    gtk.gdk.threads_leave()
        return gst.BUS_PASS

    def _tag_found_cb(self, abus, mess):
        tag_list = mess.parse_tag()
        acceptable_tags = [gst.TAG_ALBUM_ARTIST,
                            gst.TAG_ARTIST,
                            gst.TAG_TITLE,
                            gst.TAG_ALBUM,
                            gst.TAG_BITRATE,
                            gst.TAG_COMPOSER,
                            gst.TAG_GENRE,
                            gst.TAG_PERFORMER,
                            gst.TAG_DATE]
        for tag in tag_list.keys():
            tag_type = gst.tag_get_tag_type(tag)
            if tag in acceptable_tags and tag_type in (gobject.TYPE_STRING,
                                   gobject.TYPE_DOUBLE,
                                   gobject.TYPE_FLOAT,
                                   gobject.TYPE_INT,
                                   gobject.TYPE_UINT):
                name = gst.tag_get_nick(tag)
                value = unicode(tag_list[tag]).replace('<', ' ').replace('>', ' ')
                self.tags[name] = value
        keys = self.tags.keys()
        keys.sort()
        text = self.description + "\n"
        for key in keys:
            text = text + "<b>" + key.capitalize() + "</b>: " + self.tags[key] + "\n"
        self.l_tags.set_markup(text)

    def _on_b_details_clicked_cb(self, unused_button):
        mess = self.preview_cache_errors.get(self.current_selected_uri, None)
        if mess is not None:
            dialog = gtk.MessageDialog(None,
                gtk.DIALOG_MODAL,
                gtk.MESSAGE_WARNING,
                gtk.BUTTONS_OK,
                str(mess))
            dialog.set_icon_name("pitivi")
            dialog.set_title(_("Error while analyzing a file"))
            dialog.run()
            dialog.destroy()

    def _destroy_cb(self, widget):
        self.player.set_state(gst.STATE_NULL)
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
