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
        #self.set_size_request(PREVIEW_WIDTH, PREVIEW_HEIGHT)
        self.connect('destroy', self.stop)
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
        self.pack_start(self.title, expand=False)
        
        # a drawing area for video output
        self.preview_image = gtk.DrawingArea()
        self.preview_image.set_size_request(PREVIEW_WIDTH, PREVIEW_HEIGHT)
        self.pack_start(self.preview_image)

        #slider for position handling
        adj = gtk.Adjustment(0.0, 0.00, 100.0, 0.1, 10.0, 10.0)
        self.slider = gtk.HScale(adj)
        self.slider.set_update_policy(gtk.UPDATE_DISCONTINUOUS)
        self.slider.set_draw_value(False)
        self.pack_start(self.slider, expand=False)

        #buttons for play, seeks ecc
        self.bbox = gtk.HBox()
        self.bbox.pack_start(gtk.ToolButton(gtk.STOCK_MEDIA_PREVIOUS))
        self.b_action = gtk.ToolButton(gtk.STOCK_MEDIA_PLAY)
        self.b_action.connect("clicked", self._on_start_stop_clicked)
        self.bbox.pack_start(self.b_action)
        self.bbox.pack_start(gtk.ToolButton(gtk.STOCK_MEDIA_NEXT))
        self.pack_start(self.bbox, expand=False)

        #another label for general info on file
        self.description = gtk.Label('') 
        self.description.set_use_markup(True)
        self.description.set_justify(gtk.JUSTIFY_CENTER)
        self.pack_start(self.description, expand=False)

        self.show_all()


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
                pixbuf = gtk.gdk.pixbuf_new_from_file(gst.uri_get_location(uri))
                pixbuf_w = pixbuf.get_width()
                pixbuf_h = pixbuf.get_height()
                if pixbuf_w > pixbuf_h:
                    if PREVIEW_WIDTH < pixbuf_w :
                        w = PREVIEW_WIDTH
                        h = pixbuf_h * w / pixbuf_w        
                        pixbuf = pixbuf.scale_simple(w, h, gtk.gdk.INTERP_NEAREST)
                else:
                    if PREVIEW_HEIGHT < pixbuf_h: 
                        h = PREVIEW_HEIGHT
                        w = pixbuf_w * h / pixbuf_h
                        pixbuf = pixbuf.scale_simple(w, h, gtk.gdk.INTERP_NEAREST)
                self.preview_image.set_from_pixbuf(pixbuf)
                desc = "<b>Image</b> <i>%dx%d pixel</i>"
                desc = desc % (pixbuf_w, pixbuf_h)
                self.description.set_markup(desc)                
            elif video.thumbnail:
                self.player.set_property("video-sink", self.__videosink)
                thumbnail_file = video.thumbnail
                self.clip_duration = factory.duration
                try:
                    self.player.set_property("uri", self.current_selected_uri) 
                    pixbuf = gtk.gdk.pixbuf_new_from_file(thumbnail_file)
                    self.preview_image.set_from_pixbuf(pixbuf)
                    self.slider.show()                
                    self.bbox.show()
                except:
                    thumbnail = self.videofilepixbuf
                    thumbnail_large = self.videofilepixbuf
                else:
                    desiredheight = int(96 / float(video.dar))
                    thumbnail_large = pixbuf.scale_simple(96,
                            desiredheight, gtk.gdk.INTERP_BILINEAR)
            else:
                thumbnail_large = self.videofilepixbuf
            #self.description.set_markup(beautify_stream(video))
        else:
            audio = factory.getOutputStreams(AudioStream)
            audio = audio[0]
            self.clip_duration = factory.duration
            adj = gtk.Adjustment(0, 0, 100, gst.SECOND, 0, 0)
            self.slider.set_adjustment(adj)
            self.preview_image.set_from_file(DEFAULT_AUDIO_IMAGE)
            desc = "<b>Audio:</b> %d channels \nat %d <i>Hz</i> (%d <i>bits</i>)"
            desc = desc % (audio.channels, audio.rate, audio.width)
            self.description.set_markup(desc)
            self.player.set_state(gst.STATE_NULL)
            self.player.set_property("uri", self.current_selected_uri) 
            self.player.set_property("video-sink", self.__fakesink)
            self.slider.show()                
            self.bbox.show()

            
    def clear_preview(self):
        self.slider.hide()
        self.bbox.hide()
        self.title.set_markup("<i>No preview</i>")
        self.description.set_markup("")
        self.b_action.set_stock_id(gtk.STOCK_MEDIA_PLAY)
        self.player.set_state(gst.STATE_NULL)
        self.is_playing = False
        self.preview_image.set_from_stock(gtk.STOCK_MISSING_IMAGE,
                                        gtk.ICON_SIZE_DIALOG)

    def _on_bus_message(self, bus, message):
        if message.type == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
            self.is_playing = False
            self.b_action.set_stock_id(gtk.STOCK_MEDIA_PLAY)
            adj = gtk.Adjustment(0, 0.00, 100.0, 0.1, 10.0, 10.0)
            self.slider.set_adjustment(adj)   
        elif message.type == gst.MESSAGE_ERROR:
            self.player.set_state(gst.STATE_NULL)
            self.is_playing = False
            err, dbg = message.parse_error()
            print err
            print dbg
            #print "Error " + err + ": " + dbg

    def _update_position(self, *args):
        if self.is_playing:
            curr_pos = self.player.query_position(self.time_format, None)[0]
            perc = (float(curr_pos)/float(self.clip_duration))*100.0
            adj = gtk.Adjustment(perc, 0.00, 100.0, 0.1, 10.0, 10.0)
            self.slider.set_adjustment(adj)   
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


    def stop(self, widget):
        self.player.set_state(gst.STATE_NULL)
        self.is_playing = False
