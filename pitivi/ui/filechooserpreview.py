import os

import gobject
import gtk
import pango
import gst

from pitivi.discoverer import Discoverer
from pitivi.ui.common import factory_name, beautify_stream
from pitivi.stream import match_stream_groups_map, AudioStream, VideoStream
from pitivi.utils import beautify_length, uri_is_valid
from pitivi.configure import get_pixmap_dir

DEFAULT_AUDIO_IMAGE = os.path.join(get_pixmap_dir(), "pitivi-sound.png")

PREVIEW_WIDTH = 250
PREVIEW_HEIGHT = 100


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
        self.player = gst.element_factory_make("playbin", "preview-player")
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self._on_bus_message)
        bus.enable_sync_message_emission()
        bus.connect('sync-message::element', self._on_sync_message)
        self.__videosink = self.player.get_property("video-sink")
        self.__fakesink = gst.element_factory_make("fakesink", "fakesink")

        #some global variables for preview handling
        self.is_playng = False 
        self.time_format = gst.Format(gst.FORMAT_TIME)

        #gui elements:
        #a title label
        self.title = gtk.Label('')
        self.title.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        self.title.set_use_markup(True)
        self.title.show()
        self.pack_start(self.title, expand=False)
        
        # a drawing area for video output
        self.preview_video = gtk.DrawingArea()
        self.preview_video.set_size_request(PREVIEW_WIDTH, PREVIEW_HEIGHT)
        self.preview_video.hide()
        self.pack_start(self.preview_video, expand=False)

        #an image for images and audio
        self.preview_image = gtk.Image()
        self.preview_image.set_size_request(PREVIEW_WIDTH, PREVIEW_HEIGHT)
        self.preview_image.show()
        self.pack_start(self.preview_image)

        #Scale for position handling
        adj = gtk.Adjustment(0.0, 0.00, 100.0, 0.1, 10.0, 10.0)
        self.seeker = gtk.HScale(adj)
        self.seeker.set_update_policy(gtk.UPDATE_DISCONTINUOUS)
        self.seeker.connect('button-release-event', self._on_seeker_press)
        self.seeker.set_draw_value(False)
        self.seeker.show()
        self.pack_start(self.seeker, expand=False)

        #buttons for play, seeks ecc
        self.bbox = gtk.HBox()
        self.b_action = gtk.ToolButton(gtk.STOCK_MEDIA_PLAY)
        self.b_action.connect("clicked", self._on_start_stop_clicked)
        self.bbox.pack_start(self.b_action)
        self.bbox.show_all()
        self.pack_start(self.bbox, expand=False)

        #another label for general info on file
        self.description = gtk.Label('') 
        self.description.set_use_markup(True)
        self.description.set_justify(gtk.JUSTIFY_CENTER)
        self.description.show()
        self.pack_start(self.description, expand=False)



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
                desc = "<b>Image</b> <i>%dx%d pixel</i>"
                desc = desc % (pixbuf_w, pixbuf_h)
                self.description.set_markup(desc)                
            else:
                self.preview_image.hide()
                self.player.set_property("video-sink", self.__videosink)
                self.player.set_property("uri", self.current_selected_uri) 
                self.clip_duration = factory.duration
                w, h = self.__get_best_size(video.par*video.width, video.height)
                self.preview_video.set_size_request(w, h)
                self.preview_video.show()
                self.seeker.show()                
                self.bbox.show()
                desc = "<b>Video</b> <i>%dx%d</i>\n%s"
                desc = desc % (video.par*video.width, video.height, duration)
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
            desc = "<b>Audio:</b> %d channels at %d <i>Hz</i> \n%s"
            desc = desc % (audio.channels, audio.rate, duration)
            self.description.set_markup(desc)
            self.player.set_state(gst.STATE_NULL)
            self.player.set_property("uri", self.current_selected_uri) 
            self.player.set_property("video-sink", self.__fakesink)
            self.seeker.show()                
            self.bbox.show()

            
    def clear_preview(self):
        self.seeker.hide()
        self.bbox.hide()
        self.title.set_markup("<i>No preview</i>")
        self.description.set_markup("")
        self.b_action.set_stock_id(gtk.STOCK_MEDIA_PLAY)
        self.player.set_state(gst.STATE_NULL)
        self.is_playing = False
        self.preview_image.set_from_stock(gtk.STOCK_MISSING_IMAGE,
                                        gtk.ICON_SIZE_DIALOG)
        self.preview_image.show()
        self.preview_video.hide()

    def _on_seeker_press(self, widget, event): 
        value = widget.get_value() 
        if self.is_playing == True:
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

    def _on_sync_message(self, bus, mess):
        if mess.structure is None:
            return

        if mess.structure.get_name() == 'prepare-xwindow-id':
            imagesink = mess.src
            imagesink.set_property('force-aspect-ratio', True)
            gtk.gdk.threads_enter()
            imagesink.set_xwindow_id(self.preview_video.window.xid)
            gtk.gdk.threads_leave()



    def _free_all(self, widget):
        self.player.set_state(gst.STATE_NULL)
        self.is_playing = False
        #FIXME: the followig line are really needed?
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

                
    

gtk.gdk.threads_init()
