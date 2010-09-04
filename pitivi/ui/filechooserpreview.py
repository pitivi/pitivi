
import gobject
gobject.threads_init()
import gst
import gtk
gtk.gdk.threads_init()
import pango

import os

from pitivi.log.loggable import Loggable
from pitivi.discoverer import Discoverer
from pitivi.ui.common import factory_name, beautify_stream
from pitivi.stream import match_stream_groups_map, AudioStream, VideoStream
from pitivi.utils import beautify_length, uri_is_valid
from pitivi.configure import get_pixmap_dir
from pitivi.factories.file import PictureFileSourceFactory
from pitivi.settings import GlobalSettings
from gettext import gettext as _


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


def get_playbin():
    try:
        return gst.element_factory_make("playbin2", "preview-player")
    except:
        return gst.element_factory_make("playbin", "preview-player")


class PreviewWidget(gtk.VBox, Loggable):

    def __init__(self, instance):
        gtk.VBox.__init__(self)
        Loggable.__init__(self)
        
        self.log("Init PreviewWidget")
        self.connect('destroy', self._free_all)
        
        #settings obj 
        self.settings = instance.settings
        
        #a dictionary for caching factories
        self.preview_cache = {}
        
        #a dictionary for caching errors
        self.preview_cache_errors = {}
        
        #discoverer for analyze file
        self.discoverer = Discoverer()
        self.discoverer.connect('discovery-done', self._update_preview)
        self.discoverer.connect('discovery-error', self._error_detected)

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
        self.original_dims = (PREVIEW_WIDTH, PREVIEW_HEIGHT)
        self.countinuous_seek = False
        self.current_selected_uri = ""
        self.current_preview_type = ""
        self.description = ""
        self.tags = {}
        
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
        self.preview_video.set_size_request(self.settings.FCpreviewWidth, self.settings.FCpreviewHeight)
        self.preview_video.hide()
        self.pack_start(self.preview_video, expand=False)

        #an image for images and audio
        self.preview_image = gtk.Image()
        self.preview_image.set_size_request(self.settings.FCpreviewWidth, self.settings.FCpreviewHeight)
        self.preview_image.show()
        self.pack_start(self.preview_image, expand=False)


        #button play
        self.bbox = gtk.HBox()
        self.b_action = gtk.ToolButton(gtk.STOCK_MEDIA_PLAY)
        self.b_action.connect("clicked", self._on_start_stop_clicked)
        self.bbox.pack_start(self.b_action, expand=False)
        
        #Scale for position handling
        self.pos_adj = gtk.Adjustment()
        self.seeker = gtk.HScale(self.pos_adj)
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

        #another label for tag
        self.l_tags = gtk.Label('')
        self.l_tags.set_justify(gtk.JUSTIFY_LEFT)
        self.l_tags.show()
        self.pack_start(self.l_tags, expand=False)
        
        #error handling
        #a label
        hbox = gtk.HBox()
        hbox.set_spacing(5)
        self.l_error = gtk.Label('')
        self.l_error.set_markup( _("<i>PiTiVi can not preview this file</i>"))        
        hbox.pack_start(self.l_error)
        #button for detail
        self.b_details = gtk.Button('More')
        self.b_details.connect('clicked', self._on_b_details_clicked)
        hbox.pack_start(self.b_details, expand=False, fill=False)
        hbox.show()
        self.pack_start(hbox, expand=False, fill=False)
        #a filler
        self.pack_start( gtk.Label(''))


    def add_preview_request(self, dialogbox):
        """add a preview request """ 
        uri = dialogbox.get_preview_uri()
        if uri is None or not uri_is_valid(uri):
            return
        self.log("Preview request for " + uri)
        self.clear_preview()
        self.current_selected_uri = uri
        if self.preview_cache.has_key(uri):
            #already discovered
            self.log(uri + " already in cache")
            self.show_preview(uri)
        elif  self.preview_cache_errors.has_key(uri):
            self.log(uri + " already in error cache")
            self.show_error(uri)
        else:
            self.log("Call discoverer for " + uri )
            self.discoverer.addUri(uri)

    def _update_preview(self, dscvr, uri, factory):
        if factory is None:
            self.error("Discoverer does not handle " + uri)
        #add to cache
        self.preview_cache[uri] = factory
        #show uri only if is the selected one
        if self.current_selected_uri == uri:
            self.show_preview(uri)

    def _error_detected(self, discoverer, uri, mess, details):
        if details is not None:
            self.preview_cache_errors[uri] = (mess, details)
            if self.current_selected_uri == uri:
                self.show_error(uri)

    def show_preview(self, uri):
        self.log("Show preview for " + uri )
        factory = self.preview_cache.get(uri, None)
        if factory is None:
            self.log("No preview for " + uri )
            return
    
        if not factory.duration or factory.duration == gst.CLOCK_TIME_NONE:
            duration = ''
        else:
            duration = beautify_length(factory.duration)
        self.title.set_markup('<b>'+ factory_name(factory) + '</b>') 
        video = factory.getOutputStreams(VideoStream)
        if video:
            video = video[0]
            if type(factory) == PictureFileSourceFactory:
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
                self.b_action.set_sensitive(False)
                self.seeker.set_sensitive(False)
                self.b_zoom_in.set_sensitive(True)
                self.b_zoom_out.set_sensitive(True)
                desc = "<b>Image</b> <i>%dx%d pixel</i>"
                desc = desc % (pixbuf_w, pixbuf_h)
                self.description = desc            
            else:
                self.current_preview_type = 'video'
                self.preview_image.hide()
                self.player.set_property("video-sink", self.__videosink)
                self.player.set_property("uri", self.current_selected_uri) 
                self.player.set_state(gst.STATE_PAUSED)
                self.clip_duration = factory.duration
                self.pos_adj.upper = self.clip_duration
                w, h = self.__get_best_size(video.par*video.width, video.height)
                self.preview_video.set_size_request(w, h)
                self.preview_video.show()
                self.bbox.show()
                self.b_action.set_sensitive(True)
                self.seeker.set_sensitive(True)
                self.b_zoom_in.set_sensitive(True)
                self.b_zoom_out.set_sensitive(True)
                desc = "<b>Width/Height</b>: <i>%dx%d</i>\n" + "<b>Duration</b>: %s \n"
                desc = desc % (video.par*video.width, video.height, duration) 
                self.description = desc
        else:
            self.current_preview_type = 'audio'
            self.preview_video.hide()
            audio = factory.getOutputStreams(AudioStream)
            audio = audio[0]
            self.clip_duration = factory.duration
            self.pos_adj.upper = self.clip_duration
            self.preview_image.set_from_file(DEFAULT_AUDIO_IMAGE)
            self.preview_image.show()
            self.preview_image.set_size_request(PREVIEW_WIDTH, PREVIEW_HEIGHT)
            desc = "<b>Channels:</b> %d  at %d <i>Hz</i> \n" + "<b>Duration</b>: %s \n" 
            desc = desc % (audio.channels, audio.rate, duration) 
            self.description = desc
            self.player.set_state(gst.STATE_NULL)
            self.player.set_property("uri", self.current_selected_uri) 
            self.player.set_property("video-sink", self.__fakesink)
            self.player.set_state(gst.STATE_PAUSED)
            self.b_action.set_sensitive(True)
            self.b_zoom_in.set_sensitive(False)
            self.b_zoom_out.set_sensitive(False)
            self.bbox.show()


    def show_error(self, uri):
            self.l_error.show()
            self.b_details.show()

    def clear_preview(self):
        self.log("Reset PreviewWidget ")
        self.seeker.set_value(0)
        self.bbox.hide()
        self.l_error.hide()
        self.b_details.hide()
        self.title.set_markup("<i>No preview</i>")
        self.description = ""
        self.l_tags.set_markup("")
        self.b_action.set_stock_id(gtk.STOCK_MEDIA_PLAY)
        self.player.set_state(gst.STATE_NULL)
        self.is_playing = False
        self.tags = {}
        self.current_selected_uri = ""
        self.current_preview_type = ''
        self.preview_image.set_from_stock(gtk.STOCK_MISSING_IMAGE,
                                        gtk.ICON_SIZE_DIALOG)
        self.preview_image.set_size_request(PREVIEW_WIDTH, PREVIEW_HEIGHT)
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
            value = long(widget.get_value()) 
            self.player.seek_simple(self.time_format, gst.SEEK_FLAG_FLUSH, value)
            if self.is_playing:
                self.player.set_state(gst.STATE_PLAYING)

    def _on_motion_notify(self, widget, event):
        if self.countinuous_seek:
            value = widget.get_value() 
            self.player.seek_simple(self.time_format, gst.SEEK_FLAG_FLUSH, value)
            

    def _on_bus_message(self, bus, message):
        if message.type == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
            self.is_playing = False
            self.b_action.set_stock_id(gtk.STOCK_MEDIA_PLAY)
            self.pos_adj.set_value(0)
        elif message.type == gst.MESSAGE_ERROR:
            self.player.set_state(gst.STATE_NULL)
            self.is_playing = False
            err, dbg = message.parse_error()
            self.error( "Error: %s " % err, dbg)


    def _update_position(self, *args):
        if self.is_playing:
            curr_pos = self.player.query_position(self.time_format, None)[0]
            self.pos_adj.set_value(long(curr_pos))
        return self.is_playing



    def _on_start_stop_clicked(self, button):
        if button.get_stock_id() == gtk.STOCK_MEDIA_PLAY:
            self.player.set_state(gst.STATE_PLAYING)
            gobject.timeout_add(1000, self._update_position)
            self.is_playing = True
            button.set_stock_id(gtk.STOCK_MEDIA_PAUSE)
            self.log("Preview started" )
        else:
            self.player.set_state(gst.STATE_PAUSED)
            self.is_playing = False
            button.set_stock_id(gtk.STOCK_MEDIA_PLAY)
            self.log("Preview paused" )


    def _on_zoom_clicked(self, button, increment):
        if self.current_preview_type == 'video':
            w, h = self.preview_video.get_size_request()
            if increment > 0 :
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
            if increment > 0 :
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
        self.log("Tag found" )
        tag_list = mess.parse_tag()
        for tag in tag_list.keys():
            tag_type = gst.tag_get_tag_type(tag)
            if tag_type in (gobject.TYPE_STRING, 
                                   gobject.TYPE_DOUBLE,
                                   gobject.TYPE_FLOAT,
                                   gobject.TYPE_INT,
                                   gobject.TYPE_UINT):
                value = unicode(tag_list[tag]).replace('<', ' ').replace('>', ' ')
                name = gst.tag_get_nick(tag)
                self.tags['<b>' + name + '</b>: '] = value
        keys = self.tags.keys()
        keys.sort()
        text = self.description + "\n"
        for key in keys:
            text = text + key + self.tags[key] + "\n"
        self.l_tags.set_markup(text)


    def _on_b_details_clicked(self, unused_button):
        mess, detail = self.preview_cache_errors.get(self.current_selected_uri, (None, None))
        if mess is not None:
            dialog = gtk.MessageDialog(None,
                gtk.DIALOG_MODAL,
                gtk.MESSAGE_WARNING,
                gtk.BUTTONS_OK,
                mess)
            dialog.set_icon_name("pitivi")
            dialog.set_title(_("Error Previewing File"))
            dialog.set_property("secondary-text", detail)
            dialog.run()
            dialog.destroy()

    def _free_all(self, widget):
        self.player.set_state(gst.STATE_NULL)
        self.is_playing = False
        
        #FIXME: the followig lines are really needed?
        del self.player
        del self.preview_cache


    def __get_best_size(self, width_in, height_in):
        if width_in > height_in:
            if  self.settings.FCpreviewWidth < width_in :
                w = self.settings.FCpreviewWidth
                h = height_in * w / width_in
                return (w, h)        
        else:
            if self.settings.FCpreviewHeight < height_in: 
                h = self.settings.FCpreviewHeight
                w = width_in * h / height_in
                return (w, h)
        return (width_in, height_in)

