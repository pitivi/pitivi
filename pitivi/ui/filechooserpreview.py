
import gobject
gobject.threads_init()
import gst
import gtk
gtk.gdk.threads_init()
import pango

import os

from pitivi.discoverer import Discoverer
from pitivi.ui.common import factory_name, beautify_stream
from pitivi.stream import match_stream_groups_map, AudioStream, VideoStream
from pitivi.utils import beautify_length, uri_is_valid
from pitivi.configure import get_pixmap_dir

DEFAULT_AUDIO_IMAGE = os.path.join(get_pixmap_dir(), "pitivi-sound.png")

PREVIEW_WIDTH = 250
PREVIEW_HEIGHT = 100

def get_playbin():
    try:
        return gst.element_factory_make("playbin2", "preview-player")
    except:
        return gst.element_factory_make("playbin", "preview-player")


class PreviewWidget(gtk.VBox):

    def __init__(self):
        gtk.VBox.__init__(self)
        self.connect('destroy', self._free_all)
        #a dictionary for caching factories
        self.preview_cache = {}
        
        #discoverer for analyze file
        self.discoverer = Discoverer()
        self.discoverer.connect('discovery-done', self._update_preview)

        #playbin for play pics
        self.player = get_playbin()
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self._on_bus_message)
        bus.enable_sync_message_emission()
        bus.connect('sync-message::element', self._on_sync_message)
        bus.connect('message::tag', self._on_tag_found)
        self.__videosink = self.player.get_property("video-sink")
        self.__fakesink = gst.element_factory_make("fakesink", "fakesink")

        #some global variables for preview handling
        self.is_playng = False 
        self.time_format = gst.Format(gst.FORMAT_TIME)
        self.original_dims = None
        self.countinuous_seek = False
        self.tag_text = ""
        
        #gui elements:
        #a title label
        self.title = gtk.Label('')
        self.title.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        self.title.set_use_markup(True)
        self.title.show()
        self.pack_start(self.title, expand=False)
        
        # a drawing area for video output
        self.preview_video = gtk.DrawingArea()
        self.preview_video.modify_bg(gtk.STATE_NORMAL, self.preview_video.style.black)
        self.preview_video.set_size_request(PREVIEW_WIDTH, PREVIEW_HEIGHT)
        self.preview_video.hide()
        self.pack_start(self.preview_video, expand=False)

        #an image for images and audio
        self.preview_image = gtk.Image()
        self.preview_image.set_size_request(PREVIEW_WIDTH, PREVIEW_HEIGHT)
        self.preview_image.show()
        self.pack_start(self.preview_image, expand=False)


        #button play
        self.bbox = gtk.HBox()
        self.b_action = gtk.ToolButton(gtk.STOCK_MEDIA_PLAY)
        self.b_action.connect("clicked", self._on_start_stop_clicked)
        self.bbox.pack_start(self.b_action, expand=False)
        
        #Scale for position handling
        adj = gtk.Adjustment(0.0, 0.00, 100.0, 0.1, 10.0, 10.0)
        self.seeker = gtk.HScale(adj)
        self.seeker.set_update_policy(gtk.UPDATE_DISCONTINUOUS)
        self.seeker.connect('button-press-event', self._on_seeker_press)
        self.seeker.connect('button-release-event', self._on_seeker_press)
        self.seeker.connect('motion-notify-event', self._on_motion_notify)
        self.seeker.set_draw_value(False)
        self.seeker.show()
        self.bbox.pack_start(self.seeker)

        #button zoom in
        self.b_zoom_in = gtk.ToolButton(gtk.STOCK_ZOOM_IN)
        self.b_zoom_in.connect("clicked", self._on_zoom_clicked, 1)
        self.bbox.pack_start(self.b_zoom_in, expand=False)
        #button zoom out
        self.b_zoom_out = gtk.ToolButton(gtk.STOCK_ZOOM_OUT)
        self.b_zoom_out.connect("clicked", self._on_zoom_clicked, -1)
        self.bbox.pack_start(self.b_zoom_out, expand=False)
        
        self.bbox.show_all()

        self.pack_start(self.bbox, expand=False)

        #another label for general info on file
        self.description = gtk.Label('') 
        self.description.set_use_markup(True)
        self.description.set_justify(gtk.JUSTIFY_LEFT)
        self.description.show()
        self.pack_start(self.description, expand=False)
        #a filler
        self.pack_start( gtk.Label(''))


    def add_preview_request(self, dialogbox):
        """add a preview request """ 
        uri = dialogbox.get_preview_uri()
        if uri is None or not uri_is_valid(uri):
            return
        self.clear_preview()
        self.current_selected_uri = uri
        if self.preview_cache.has_key(uri):
            #already discovered
            self.show_preview(uri)
        else:
            self.discoverer.addUri(uri)

    def _update_preview(self, dscvr, uri, factory):
        #add to cache
        self.preview_cache[uri] = factory
        #show uri only if is the selected one
        if self.current_selected_uri == uri:
            self.show_preview(uri)

    def show_preview(self, uri):
        factory = self.preview_cache.get(uri, None)
        if factory is None:
            return
    
        if not factory.duration or factory.duration == gst.CLOCK_TIME_NONE:
            duration = ''
        else:
            duration = beautify_length(factory.duration)
        self.title.set_markup('<b>'+ factory_name(factory) + '</b>') 
        self.b_action.set_stock_id(gtk.STOCK_MEDIA_PLAY)
        video = factory.getOutputStreams(VideoStream)
        if video:
            video = video[0]
            if video.is_image:
                self.preview_video.hide()
                pixbuf = gtk.gdk.pixbuf_new_from_file(gst.uri_get_location(uri))
                pixbuf_w = pixbuf.get_width()
                pixbuf_h = pixbuf.get_height()
                w, h = self.__get_best_size(pixbuf_w, pixbuf_h)
                pixbuf = pixbuf.scale_simple(w, h, gtk.gdk.INTERP_NEAREST)
                self.preview_image.set_from_pixbuf(pixbuf)
                self.preview_image.show()
                self.bbox.show()
                self.b_action.set_sensitive(False)
                self.seeker.set_sensitive(False)
                self.b_zoom_in.set_sensitive(True)
                self.b_zoom_out.set_sensitive(True)
                desc = "<b>Image</b> <i>%dx%d pixel</i>"
                desc = desc % (pixbuf_w, pixbuf_h)
                self.description.set_markup(desc)                
            else:
                self.preview_image.hide()
                self.player.set_property("video-sink", self.__videosink)
                self.player.set_property("uri", self.current_selected_uri) 
                self.player.set_state(gst.STATE_PAUSED)
                self.clip_duration = factory.duration
                w, h = self.__get_best_size(video.par*video.width, video.height)
                self.original_dims = (w, h)
                self.preview_video.set_size_request(w, h)
                self.preview_video.show()
                self.bbox.show()
                self.b_action.set_sensitive(True)
                self.seeker.set_sensitive(True)
                self.b_zoom_in.set_sensitive(True)
                self.b_zoom_out.set_sensitive(True)
                desc = "<b>Width/Height</b> <i>%dx%d</i>\n" + "<b>Duration</b> %s \n"
                self.tag_text = desc % (video.par*video.width, video.height, duration) 
                self.description.set_markup(desc) 
        else:
            self.preview_video.hide()
            audio = factory.getOutputStreams(AudioStream)
            audio = audio[0]
            self.clip_duration = factory.duration
            adj = gtk.Adjustment(0, 0, 100, gst.SECOND, 0, 0)
            self.seeker.set_adjustment(adj)
            self.preview_image.set_from_file(DEFAULT_AUDIO_IMAGE)
            self.preview_image.show()
            desc = "<b>Channels:</b> %d  at %d <i>Hz</i> \n" + "<b>Duration</b> %s \n" 
            self.tag_text = desc % (audio.channels, audio.rate, duration) 
            self.description.set_markup(desc)
            self.player.set_state(gst.STATE_NULL)
            self.player.set_property("uri", self.current_selected_uri) 
            self.player.set_property("video-sink", self.__fakesink)
            self.player.set_state(gst.STATE_PAUSED)
            self.b_action.set_sensitive(True)
            self.b_zoom_in.set_sensitive(False)
            self.b_zoom_out.set_sensitive(False)
            self.bbox.show()

            
    def clear_preview(self):
        self.seeker.set_value(0)
        self.bbox.hide()
        self.title.set_markup("<i>No preview</i>")
        self.description.set_markup("")
        self.b_action.set_stock_id(gtk.STOCK_MEDIA_PLAY)
        self.player.set_state(gst.STATE_NULL)
        self.is_playing = False
        self.tag_text = ""
        self.preview_image.set_from_stock(gtk.STOCK_MISSING_IMAGE,
                                        gtk.ICON_SIZE_DIALOG)
        self.preview_image.show()
        self.preview_video.hide()

    def _on_seeker_press(self, widget, event): 
        event.button = 2
        if event.type == gtk.gdk.BUTTON_PRESS:
            self.countinuous_seek = True
            if self.is_playing:
                self.player.set_state(gst.STATE_PAUSED)
                
        elif event.type == gtk.gdk.BUTTON_RELEASE:
            self.countinuous_seek = False
            value = widget.get_value() 
            time = value * (self.clip_duration / 100) 
            self.player.seek_simple(self.time_format, gst.SEEK_FLAG_FLUSH, time)
            if self.is_playing:
                self.player.set_state(gst.STATE_PLAYING)

    def _on_motion_notify(self, widget, event):
        if self.countinuous_seek:
            value = widget.get_value() 
            time = value * (self.clip_duration / 100) 
            self.player.seek_simple(self.time_format, gst.SEEK_FLAG_FLUSH, time)
            

    def _on_bus_message(self, bus, message):
        if message.type == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
            self.is_playing = False
            self.b_action.set_stock_id(gtk.STOCK_MEDIA_PLAY)
            adj = gtk.Adjustment(0, 0.00, 100.0, 0.1, 10.0, 10.0)
            self.seeker.set_adjustment(adj)   
        elif message.type == gst.MESSAGE_ERROR:
            self.player.set_state(gst.STATE_NULL)
            self.is_playing = False
            err, dbg = message.parse_error()
            print "Error: %s " % err, dbg


    def _update_position(self, *args):
        if self.is_playing:
            curr_pos = self.player.query_position(self.time_format, None)[0]
            perc = (float(curr_pos)/float(self.clip_duration))*100.0
            adj = gtk.Adjustment(perc, 0.00, 100.0, 0.1, 10.0, 10.0)
            self.seeker.set_adjustment(adj)   
        return self.is_playing


    def _on_start_stop_clicked(self, button):
        if button.get_stock_id() == gtk.STOCK_MEDIA_PLAY:
            self.player.set_state(gst.STATE_PLAYING)
            gobject.timeout_add(1000, self._update_position)
            self.is_playing = True
            button.set_stock_id(gtk.STOCK_MEDIA_PAUSE)
        else:
            self.player.set_state(gst.STATE_PAUSED)
            self.is_playing = False
            button.set_stock_id(gtk.STOCK_MEDIA_PLAY)


    def _on_zoom_clicked(self, button, increment):
        if increment > 0 :
            w, h = self.preview_video.get_size_request()
            w *= 1.2
            h *= 1.2
        else:
            w, h = self.preview_video.get_size_request()
            w *= 0.8
            h *= 0.8
            if (w, h) < self.original_dims:
                (w, h) = self.original_dims
        self.preview_video.set_size_request(int(w), int(h))


    def _on_sync_message(self, bus, mess):
        if mess.type == gst.MESSAGE_ELEMENT:
            if mess.structure.get_name() == 'prepare-xwindow-id':
                sink = mess.src
                sink.set_property('force-aspect-ratio', True)
                sink.set_property("handle-expose", True)
                gtk.gdk.threads_enter()
                sink.set_xwindow_id(self.preview_video.window.xid)
                sink.expose()
                gtk.gdk.threads_leave()
        return gst.BUS_PASS


    def _on_tag_found(self, abus, mess):
        tag_list = mess.parse_tag()
        keys = tag_list.keys()
        keys.sort()
        for tag in keys:
            tag_type = gst.tag_get_tag_type(tag)
            if tag_type in (gobject.TYPE_STRING, 
                                   gobject.TYPE_DOUBLE,
                                   gobject.TYPE_FLOAT,
                                   gobject.TYPE_INT,
                                   gobject.TYPE_UINT):
                value = unicode(tag_list[tag]).replace('<', ' ').replace('>', ' ')
                name = gst.tag_get_nick(tag)
                self.tag_text = self.tag_text + '<b>' + name + '</b> ' \
                                    + value \
                                    + '\n'
        self.description.set_markup(self.tag_text)


    def _free_all(self, widget):
        self.player.set_state(gst.STATE_NULL)
        self.is_playing = False
        #FIXME: the followig lines are really needed?
        del self.player
        del self.preview_cache


    def __get_best_size(self, width_in, height_in):
        if width_in > height_in:
            if PREVIEW_WIDTH < width_in :
                w = PREVIEW_WIDTH
                h = height_in * w / width_in
                return (w, h)        
        else:
            if PREVIEW_HEIGHT < height_in: 
                h = PREVIEW_HEIGHT
                w = width_in * h / height_in
                return (w, h)
        return (width_in, height_in)

