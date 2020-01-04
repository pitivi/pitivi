# -*- coding: utf-8 -*-
# Tested with Pitivi 0.98-827-gdd262c24
# Pitivi video editor
# Copyright (c) 2019 Pitivi project
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
# Boston, MA 02110-1301, USA.from gi.repository import GObject
import os
import pickle

import cairo
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GES
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GstController
from gi.repository import Gtk
from gi.repository import Peas

from pitivi.configure import get_pixmap_dir
from pitivi.configure import get_ui_dir
from pitivi.undo.timeline import CommitTimelineFinalizingAction
from pitivi.utils.timeline import SELECT
from pitivi.utils.ui import argb_to_gdk_rgba
from pitivi.utils.ui import gdk_rgba_to_argb
from pitivi.utils.user_utils import Alert
#gi.require_version('Gtk', '3.0')
#from gi.repository import Gio
#from gi.repository import Pango
#from gi.repository import PangoCairo
#from pitivi.utils.user_utils import ChoiceWin
#from pitivi.utils.ui import set_cairo_color
#from pitivi.utils.ui import hex_to_rgb
#from pitivi.utils.ui import unpack_color #def dans le programme à supprimer
#from pitivi.utils.ui import unpack_color_64
#import shutil
#import sys

SEC_1 = Gst.SECOND  # 1000000000  # 1 second in nano seconds

RADIUS = 150
N_WORDS = 10
FONT = "Sans Bold 20"

class TitlerRT(GObject.Object, Peas.Activatable):
    """Create a title .

    Print is used for debugging goal
    In this version, all titles are kept to prevent the remove
    in the different versions of xxxx.xges
    """

    object = GObject.Property(type=GObject.Object)

    def do_activate(self):
        # pylint: disable=attribute-defined-outside-init
        self.app = self.object.app
        self.project = self.app.project_manager.current_project
        dir_img = os.path.join(get_pixmap_dir(), "pitivi-alin.svg")
        image = Gtk.Image.new_from_file(dir_img)
        self.button = Gtk.ToolButton.new(icon_widget=image)
#        print("im", self.button.get_icon_widget())
        self.button.set_tooltip_text("Titler")
        self.button.show_all()

        toolbar = self.app.gui.editor.timeline_ui.toolbar
        toolbar.add(self.button)
        self.button.connect("clicked", self.__titler_cb)

    def __titler_cb(self, unused_button):
        """ """
#            Si une image est sélectionnée, son nom commence-t-il par Titol_
#                si oui ouvrir le titre (dossier, image, texte, buffer_letters, position du titre)
#                si non : message d'alerte terminer
#            Sinon
#                si recherche d'un titre existant
#                    charger texte, buffer_letters, position
#                    le placer sur la timeline à la position de la headplay sur le 1er layout
#                si création d'un nouveau titre
#                    rechercher le titre dont le nom commence par titol_
#                    choisir le nombre le plus élevé + 1
#                    créer un nouveau titre (dossier, texte = "Titre")
#                    se placer sur la timeline à la position de la headplay

        # pylint: disable=attribute-defined-outside-init
        #  Undoing action :
        # http://developer.pitivi.org/Advanced_plugin.html#making-it-shine
        with self.app.action_log.started("titler_rt", toplevel=True):
            self.starting()
            self.tlc = self.app.gui.editor.timeline_ui  # timeline container
            self.timeline = self.tlc.timeline  # timeline
            clips = sorted(self.timeline.selection, key=lambda x: x.get_start())
            print("87 Clips selected = ", clips)
            # create the directory of the titles if it does not exist
            self.titoloj_dirs_create()
            if len(clips) == 1:
                # Copy or update a clip without background
                clip = clips[0]
                uri = os.path.basename(clip.get_uri()[7:])  #remove "file://"
                print("94", clip.get_uri(), uri, uri[:7], uri[7:len(uri) - 4]) # , clip.get_uri()
                name_start = uri[:7]
                print("96 name_start", name_start)
                clip_name = clip.get_asset().props.id
                print("98 clip name", clip_name)
                if name_start == "Titolo_":
                    # effacer et écrire
                    self.entry_title.set_opacity(1)
                    self.title_name = name_start + uri[7:len(uri) - 4]
                    self.entry_title.set_text(self.title_name)
#                    self.titoloj_dirs_create()
                    print("105 dstart ", os.path.dirname(clip.get_uri()[7:]),
                          "102 stname ", self.title_name)
                    self.button_new.set_sensitive(False)
                    self.button_load.set_sensitive(False)
                    self.button_modif.set_sensitive(True)
                    print("108 buttons ", self.button_new, self.button_load)
                    self.load = os.path.dirname(clip.get_uri()[7:])
                    self.load_title(os.path.dirname(clip.get_uri()[7:]))
            elif len(clips) == 2:
                # Copy or update a clip with background
                # The clip name is linked to the img.png not to the img_bg.png
                clip = clips[0]
                uri = os.path.basename(clip.get_uri()[7:])  #remove "file://"
                if uri[len(uri) - 6:len(uri) - 4] == "bg":
                    clip1 = clips[0]
                    clip = clips[1]
                else:
                    clip1 = clips[1]
                uri = os.path.basename(clip.get_uri()[7:])  #remove "file://"
                uri1 = os.path.basename(clip1.get_uri()[7:])  #remove "file://"
                print("118", clip.get_uri(), uri, uri[:7], uri[7:len(uri) - 4]) # , clip.get_uri()
                name_start = uri[:7]
                name_start1 = uri1[:7]
                print("121 name_start", name_start, name_start1)
#                clip_name = clip.get_asset().props.id
#                clip_name1 = clip1.get_asset().props.id
#                print("98 clip name", clip_name)
                if name_start == "Titolo_" and name_start1 == "Titolo_":
                    # effacer et écrire
                    self.entry_title.set_opacity(1)
                    self.title_name = name_start + uri[7:len(uri) - 4]
                    self.entry_title.set_text(self.title_name)
#                    self.titoloj_dirs_create()
                    print("131 dstart ", os.path.dirname(clip.get_uri()[7:]),
                          "102 stname ", self.title_name)
                    self.button_new.set_sensitive(False)
                    self.button_load.set_sensitive(False)
                    self.button_modif.set_sensitive(True)
                    print("135 buttons ", self.button_new, self.button_load)
                    self.load = os.path.dirname(clip.get_uri()[7:])
                    self.load_title(os.path.dirname(clip.get_uri()[7:]))
                else:
                    Alert("No title", "You have to select a title clip \
                          (Titolo_xxx).", "service-logout.oga")
                    self.win.destroy()
            elif len(clips) == 0:
                # Create a title
                # Give a default name to the title
                dirs = os.listdir(self.titoloj_dirs)
                add_name = 0
                self.parcours(dirs, add_name)
                print("117 stname ", self.title_name, self.title_name[7:])
                self.entry_title.set_text(self.title_name[7:])
                self.button_new.set_sensitive(True)
                self.button_load.set_sensitive(True)
                self.button_modif.set_sensitive(False)
            else:
                Alert("Too clips", "You have to select only one clip.", "service-logout.oga")


    def starting(self):
        # pylint: disable=attribute-defined-outside-init
        self.video_width = self.app.project_manager.current_project.videowidth
        self.video_height = self.app.project_manager.current_project.videoheight
        self.width = 900
        self.width_title_box = self.width - 200
        self.height = int((self.width_title_box/self.video_width)*self.video_height)
        self.mult = self.video_width/self.width_title_box
        self.x = 100
        self.y = 100
        self.load = ""
        self.first = True
        cairo_color = [1.0, 1.0, 1.0, 1.0]
        self.cairo_background = []  # Display background  of the title [red, green, blue, alpha]
        self.background_rgba = None  # Background of the title in the saved file (type Gdk.RGBA(red, green, blue, alpha))

        self.title_text = ""
        self.stock_text = ""
        self.buffer_letters = []
        self.letter_format = {"color":[], "bg":[], "font":FONT}
        self.context = None
        tag0 = "color_0"
        self.title_list_tags = [{"tag":tag0, "start":0, "end":len(self.title_text),
                                 "color":cairo_color, "bg":self.cairo_background, "font":FONT}]
        self.title_name = "Titolo_0"
        self.project_dir = self.app.settings.lastProjectFolder # in editorperspective.py _showSaveAsDialog()

        self.center_h = False
        self.center_v = False
        self.center_hv = False
        self.credits_up = False
        self.credits_down = False
        self.fade_in = False
        self.fade_in_out = True
        self.fade_out = False

        # Window description
        self.win = Gtk.Window()
        self.win.set_default_size(self.width, self.height)
        title = "Titler"
        self.win.set_title(title)
        self.win.connect("destroy", self.on_clicked_close)

        # Box h for title_box (DrawingArea) and widget
        box = Gtk.HBox()

        self.title_box = Gtk.HBox()

        self.event_box = Gtk.EventBox()
        self.event_box.connect("button-press-event", self.bouton_press_event)
        self.event_box.connect("button-release-event", self.bouton_release_event)
        self.event_box.connect("motion-notify-event", self.motion_notify_event)

        self.s_title = Gtk.DrawingArea()
        self.s_title.set_size_request(self.width_title_box, self.height)
        self.s_title.connect('draw', self.draw_event)
#            print("201 style ", self.s_title.get_style_context())

        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "titleeditor_rt.ui"))
        builder.connect_signals(self)
        self.widget1 = builder.get_object("box1")

        self.textarea = builder.get_object("textview")
        self.textbuffer = self.textarea.props.buffer
        self.textbuffer.connect("changed", self._text_changed_cb)

        self.button_new = builder.get_object("button_create")
        self.button_modif = builder.get_object("button_modif")
        self.button_load = builder.get_object("button_load")

        self.h_center_button = builder.get_object("tbutton_h_center")
        self.v_center_button = builder.get_object("tbutton_v_center")
        self.hv_center_button = builder.get_object("tbutton_hv_center")
        self.center_align_label = builder.get_object("label_alignement")
        self.center_v_label = builder.get_object("label_vertical")
        self.center_h_label = builder.get_object("label_horizontal")
        self.center_hv_label = builder.get_object("label_middle")
        self.label_credits = builder.get_object("label_credits")
        self.up_button = builder.get_object("tup_button")
        self.down_button = builder.get_object("tdown_button")
        self.info_label = builder.get_object("info_label")
        self.label_fade = builder.get_object("label_fade")
        self.fade_in_label = builder.get_object("label_fade_in")
        self.fade_out_label = builder.get_object("label_fade_out")
        self.fade_in_out_label = builder.get_object("label_fade_inout")
        self.fade_in_button = builder.get_object("fade_in_tbutton")
        self.fade_out_button = builder.get_object("fade_out_tbutton")
        self.fade_in_out_button = builder.get_object("fade_in_out_tbutton")
        self.fade_in_out_label.set_markup('<span foreground="#8dfb85" font_weight="bold">Fade in and out</span>')
        self.fade_in_out_button.set_active(True)

#            self.enter = False

        self.entry_title = builder.get_object("entry_titolo")
        self.entry_duration = builder.get_object("duration")
        self.duration = int(self.app.settings.titleClipLength * Gst.MSECOND / 1000000000)
        self.entry_duration.set_text(str(self.duration))

        self.win.add(box)
        box.add(self.title_box)
        self.title_box.add(self.event_box)
        self.event_box.add(self.s_title)
        box.add(self.widget1)

        self.win.show_all()

        # Image of the first background image of the title
        dir_img = self.background_image()
        im = GdkPixbuf.Pixbuf.new_from_file(dir_img)
        # 2 = Gtk.GDK_INTERP_BILINEAR  GdkPixbuf.InterpType.NEAREST
        pixbuf_im = im.scale_simple(self.width_title_box, self.height, 2)
        self.pixbuf = pixbuf_im

    def background_image(self):
        """Exports a snapshot of the current frame as an image file."""
        # from editorperspective def  __save_frame_cb():
        path = "/home/jpf/Images/Sans titre1.png"
        mime = 'image/png'
        self.app.project_manager.current_project.pipeline.save_thumbnail(
            -1, -1, mime, path)
        return path

    def titoloj_dirs_create(self):
        # pylint: disable=attribute-defined-outside-init
        """Create the directory of all the titles."""
        print("Dir Titoloj", self.project_dir)
        self.titoloj_dirs = os.path.join(self.project_dir, "Titoloj")
        if not os.path.isdir(self.titoloj_dirs):
            os.mkdir(self.titoloj_dirs)
            print("251 ", self.titoloj_dirs)

# pylint: disable=unused-argument
    def on_clicked_close(self, widget):
        """If exist, remove the titles non used by the project."""
        # pylint: disable=attribute-defined-outside-init
        print("282 clicked")
#        list_clip=[]
#        # Remove all titles of directory out of the project
#        dirs = os.listdir(self.titoloj_dirs)
#        print("dirs ", dirs)
#        layers = self.timeline.ges_timeline.get_layers()
#        for dir_clip in layers[0].get_clips():
#            dl_name = dir_clip.get_asset().props.id
#            dl_name = os.path.basename(dl_name)
#            dl_name = dl_name[:len(dl_name) - 4]
#            list_clip.append(dl_name)
#        print("list ", list_clip)
#        for dlc in dirs:
#            dl_path = os.path.join(self.titoloj_dirs, dlc)
#            if not dlc in list_clip and os.path.isdir(dl_path):
#                print("rm tr ", dlc, dl_path)
#                shutil.rmtree(dl_path)
        self.cairo_background = []
        print("self.cairo_background 288", self.cairo_background)
        self.win.destroy()

    def _create_cb(self, widget):
        # pylint: disable=attribute-defined-outside-init
        rgba = None
        im_bg = ""
        self.button_new.set_sensitive(True)

        # Create a surface for saving the image of the title
        save_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.video_width, self.video_height)
        save_context = cairo.Context(save_surface)
        save_context.scale(self.mult, self.mult)
        # Create a surface for saving the background of the title
        save_surface_bg = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                             self.video_width, self.video_height)
        save_context_bg = cairo.Context(save_surface_bg)
        save_context_bg.scale(self.mult, self.mult)
        print("316 scb ", self.cairo_background)
        if self.cairo_background == []:
            print("318 cb []")
        else:
            if self.cairo_background[3] >= 0.0:
                rgba = self.background_rgba
            print("rgba 317", rgba)
            Gdk.cairo_set_source_rgba(save_context_bg, rgba)
            save_context_bg.paint()
        self.show_buffer_bl(self.context)
        # The text is pushed in the new surface without background
        h = self.show_buffer_bl(save_context)
#        print("hhhhhhh ", h)

        if self.title_name == "":
            self.title_name = "Titolo_0"
        print("stn 330 ", self.title_name)
        self.dir_of_title = os.path.join(self.titoloj_dirs, self.title_name)
        if not os.path.isdir(self.dir_of_title):
            os.mkdir(self.dir_of_title)
            print("334 ok ", self.dir_of_title)
#        else:
#            print("336 pas ok ", self.dir_of_title)
#            # Test if the title is a modified title = has a copy
#            self.remove_copy_title(self.dir_of_title)
#            dirs = os.listdir(self.titoloj_dirs)
#            add_name = 0
#            self.parcours(dirs, add_name)
#            self.dir_of_title = os.path.join(self.titoloj_dirs, self.title_name)
#            os.mkdir(self.dir_of_title)
        im_file = os.path.join(self.titoloj_dirs, self.dir_of_title, self.title_name + ".png")
        txt_file = os.path.join(self.titoloj_dirs, self.dir_of_title, "titol.txt")
        buf_file = os.path.join(self.titoloj_dirs, self.title_name, "titol.buf")
        pos_file = os.path.join(self.titoloj_dirs, self.dir_of_title, "titol.pos")
        bg_file = os.path.join(self.titoloj_dirs, self.dir_of_title, "titol.bg")
        mocefa_file = os.path.join(self.titoloj_dirs, self.dir_of_title, "titol.mcf")
        # create the directory of the title (dossier, image,
        # texte, buffer_letters, position du titre)
        print("351 ", self.buffer_letters)
        with open(buf_file, "wb") as buffer_file:
            pickle.dump(self.buffer_letters, buffer_file)
        with open(im_file, "wb") as image_file:
            save_surface.write_to_png(image_file)
        if rgba is not None:
            im_bg = os.path.join(self.titoloj_dirs, self.dir_of_title, self.title_name + "_bg.png")
            with open(im_bg, "wb") as image_file_bg:
                save_surface_bg.write_to_png(image_file_bg)
        with open(txt_file, "wb") as text_file:
            pickle.dump(self.textbuffer.props.text, text_file)
        with open(pos_file, "wb") as position_file:
            pickle.dump([self.x, self.y], position_file)
        with open(bg_file, "wb") as backg_file:
            pickle.dump(self.cairo_background, backg_file)
        with open(mocefa_file, "wb") as mcf_file:
            pickle.dump(self.move_center_fade_file(), mcf_file)
        image_file.close()
        if rgba is not None:
            image_file_bg.close()
        buffer_file.close()
        text_file.close()
        position_file.close()
        backg_file.close()
        mcf_file.close()
        self.title_name = ""
#        self.entry_title.set_opacity(1)
#        self.entry_title.set_text("")
        save_context.scale(1, 1)
        save_context_bg.scale(1, 1)
        self.clip_create(im_file, im_bg, h, rgba)
        self.cairo_background = []
        print("self.cairo_background 405", self.cairo_background)
        self.win.destroy()

    def parcours(self, dirs, add_name):
        # pylint: disable=attribute-defined-outside-init
        print("stname 390", self.title_name)
        for d_r in dirs:
            index_t = d_r[7:]
            print("index 393 = ", index_t, add_name)
            if index_t == self.title_name[7:]:
                add_name += 1
                self.title_name = self.title_name[:7] + str(add_name)
                self.parcours(dirs, add_name)
            else:
                continue
        add_name = 0

    def clip_create(self, im_file, im_bg, h, rgba):
        print("403 Clip create")
#        print("bl 351 ", self.buffer_letters)
#        list_clips = []
        uri_img = "file://" + im_file
        asset = GES.UriClipAsset.request_sync(uri_img)
        print("408 asset", asset)
        if asset.is_image():
            dur = int(self.entry_duration.get_text())
            print("409 dur", dur)
            if dur > 120:
                # The title has a duration max of 120 s
                dur = 120
            clip_duration = dur * Gst.SECOND
        print("413 asset ", asset, asset.get_id(), asset.get_supported_formats())
        if len(im_bg) > 0:
            print("415 im_bg", im_bg)
            uri_bg = "file://" + im_bg
            asset_bg = GES.UriClipAsset.request_sync(uri_bg)
#        if asset_bg.is_image():
##            Gio.AppInfo.launch_default_for_uri(asset.get_id(), None)
#            clip_duration = self.app.settings.titleClipLength * Gst.MSECOND
        offset_t = self.timeline.layout.playhead_position
        print("421 off dur ", offset_t, offset_t + clip_duration)
        with self.app.action_log.started("add layer 0 1",
                                         finalizing_action=CommitTimelineFinalizingAction(self.app.project_manager.current_project.pipeline)):
            layers = self.timeline.ges_timeline.get_layers()
            intersecting_clips_0 = layers[0].get_clips_in_interval(
                offset_t, offset_t + clip_duration)
            if intersecting_clips_0:
                nl = self.timeline.create_layer(0)
                print("428 nl layer", nl)
            else:
                nl = layers[0]
                print("431 nl layer")
            if len(im_bg) > 0:
                intersecting_clips_1 = layers[1].get_clips_in_interval(
                    offset_t, offset_t + clip_duration)
                if intersecting_clips_1:
                    nl_bg = self.timeline.create_layer(1)
                    print("436 nl_bg layer", nl_bg)
                else:
                    nl_bg = layers[1]
                    print("439 nl_bg layer", nl_bg)
        with self.app.action_log.started("add asset",
                                         finalizing_action=CommitTimelineFinalizingAction(self.app.project_manager.current_project.pipeline)):
            ges_clip = nl.add_asset(asset, offset_t, 0, clip_duration,
                                    track_types=asset.get_supported_formats())
            if len(im_bg) > 0:
                ges_clip_bg = nl_bg.add_asset(asset_bg, offset_t, 0,
                                              clip_duration, track_types=asset.get_supported_formats())
            print("443 ges_clip --------", ges_clip, ges_clip.get_uri())
#        list_clips.append(ges_clip)
#        self.tlc.insert_clips_on_first_layer(list_clips, position=offset_t)
#        self.app.gui.editor.timeline_ui.insert_clips_on_first_layer
#                           (list_clips, position=offset_t)  # [title_clip]
        if self.credits_up:
            self.title_vup_move(ges_clip, h)
        if self.credits_down:
            self.title_vdown_move(ges_clip, h)
        if self.fade_in:
            self.title_fade_in(ges_clip)
        if self.fade_out:
            self.title_fade_out(ges_clip)
        if self.fade_in_out:
            self.title_fade_inout(ges_clip)
        if len(im_bg) > 0:
            self.timeline.selection.setSelection([ges_clip, ges_clip_bg], SELECT)
            # group the two clips : from timeline.py  def _group_selected_cb
            with self.app.action_log.started("group",
                                             finalizing_action=CommitTimelineFinalizingAction(self.app.project_manager.current_project.pipeline),
                                             toplevel=True):
                toplevels = self.timeline.selection.toplevels
                if toplevels:
                    GES.Container.group(list(toplevels))

                # timeline.selection doesn't change during grouping,
                # we need to manually update group actions.
                self.timeline.selection.set_can_group_ungroup()
                self.tlc.update_actions()
        # Verify
        self.app.gui.editor.focus_timeline()
        self.timeline.selection.set_selection([], SELECT)

    def move_center_fade_file(self):
        mo_ce_fa = []
        mo_ce_fa.append(self.center_h)
        mo_ce_fa.append(self.center_v)
        mo_ce_fa.append(self.center_hv)

        mo_ce_fa.append(self.credits_up)
        mo_ce_fa.append(self.credits_down)

        mo_ce_fa.append(self.fade_in)
        mo_ce_fa.append(self.fade_in_out)
        mo_ce_fa.append(self.fade_out)
        return mo_ce_fa

    def _title_name_cb(self, widget, event):
        """Name of the title directory."""
        # pylint: disable=unused-variable
        # pylint: disable=attribute-defined-outside-init
        res, key = event.get_keyval()
        print(key)
        if self.entry_title.get_text() == "":
            self.entry_title.set_opacity(1)

        if key == Gdk.KEY_Return: # 65293 https://lazka.github.io/pgi-docs/#Gdk-3.0/constants.html#details
            self.title_name = "Titolo_" + self.entry_title.get_text()
            self.enter = True
            print("dot ", self.title_name)
            self.entry_title.set_opacity(0.5)

    def _load_cb(self, widget):
        clips = sorted(self.timeline.selection, key=lambda x: x.get_start())
        if len(clips) == 0:
            message = "Title to load"
            dialog = Gtk.FileChooserDialog(message, self.win,
                                           Gtk.FileChooserAction.SELECT_FOLDER,
                                           (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                            "Select", Gtk.ResponseType.OK))
    #        print(dir(dialog.props))
            dialog.set_size_request(-1, -1)
            response = dialog.run()
            # On choisit un dossier déjà existant
            if response == Gtk.ResponseType.OK:
                print("Select clicked")
                print("526 Dossier selectionné : " + dialog.get_filename())
                # (dossier, image, texte, buffer_letters, position du titre)
                dir_l = dialog.get_filename()
                self.load_title(dir_l)
            elif response == Gtk.ResponseType.CANCEL:
                print("Cancel clicked")
            dialog.destroy()
        else:
            Alert("Too clips", "You cannot select a clip in this case.", "service-logout.oga")
            self.win.destroy()

    def load_title(self, dir_l):
        # pylint: disable=attribute-defined-outside-init
        print("context 539", self.context, dir)
        self.load = dir_l
        self.load_buffer = []
        # load the directory of the title (image, texte, buffer_letters,
        # position du titre, fond du titre, annexes)
        txt_file = os.path.join(dir_l, "titol.txt")
        buf_file = os.path.join(dir_l, "titol.buf")
        pos_file = os.path.join(dir_l, "titol.pos")
        bg_file = os.path.join(dir_l, "titol.bg")
        mocefa_file = os.path.join(dir_l, "titol.mcf")
        with open(buf_file, "rb") as buffer_file:
            self.load_buffer = pickle.load(buffer_file)
            print("\nsbl 582", self.buffer_letters, "\n582 ", self.load_buffer)
        print("583 stb ", self.textbuffer.props.text)
#        self.title_text = self.textbuffer.props.text
        with open(pos_file, "rb") as position_file:
            pos = pickle.load(position_file)
            self.x = pos[0]
            self.y = pos[1]
        with open(bg_file, "rb") as backg_file:
            self.cairo_background = pickle.load(backg_file)
        with open(mocefa_file, "rb") as mcf_file:
            list_l = pickle.load(mcf_file)
            self.move_center_fade_values(list_l)
        with open(txt_file, "rb") as text_file:
            self.title_text = pickle.load(text_file)
        buffer_file.close()
        text_file.close()
        position_file.close()
        backg_file.close()
        mcf_file.close()
        self.entry_title.set_text(self.title_name[7:])
        self.entry_title.set_opacity(0.5)
        print("context 595", self.context)
        print("\604 bl + tb + stt", self.buffer_letters,
              self.textbuffer.props.text, self.title_text, self.stock_text)
        print("605 scb ", self.cairo_background)
        if self.cairo_background == []:
            print("607 cb []")
        else:
            if self.cairo_background[3] >= 0.0:
                self.background_rgba = Gdk.RGBA()
                self.background_rgba.red = self.cairo_background[0]
                self.background_rgba.green = self.cairo_background[1]
                self.background_rgba.blue = self.cairo_background[2]
                self.background_rgba.alpha = self.cairo_background[3]
            print("rgba 612", self.background_rgba.red)

    def _modif_cb(self, widget):
        """Update the initial title."""
        # pylint: disable=attribute-defined-outside-init
        print("600 Modif")
        self.button_new.set_sensitive(True)
        self.button_load.set_sensitive(True)

        if self.timeline.selection is None:
            return
        rgba = None
        im_bg = ""
        self.button_new.set_sensitive(True)
        self.button_load.set_sensitive(True)

        # Create a surface for saving the image of the title
        save_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.video_width, self.video_height)
        save_context = cairo.Context(save_surface)
        save_context.scale(self.mult, self.mult)
        # Create a surface for saving the background of the title
        save_surface_bg = cairo.ImageSurface(cairo.FORMAT_ARGB32,
                                             self.video_width, self.video_height)
        save_context_bg = cairo.Context(save_surface_bg)
        save_context_bg.scale(self.mult, self.mult)
        print("619 scb ", self.cairo_background)
        if self.cairo_background == []:
            print("621 cb []")
        else:
            if self.cairo_background[3] >= 0.0:
                rgba = self.background_rgba
            print("rgba 625", rgba)
            Gdk.cairo_set_source_rgba(save_context_bg, rgba)
            save_context_bg.paint()
        self.show_buffer_bl(self.context)
        # The text is pushed in the new surface without background
        h = self.show_buffer_bl(save_context)
#        print("hhhhhhh ", h)

        # The directory of the title is flushed
        self.dir_of_title = self.title_name
        files = os.listdir(os.path.join(self.titoloj_dirs, self.dir_of_title))
        print("617  Files ", files)
        for f_f in files:
            print("619 File ", f_f)
            os.remove(os.path.join(self.titoloj_dirs, self.dir_of_title, f_f))
        # The  directory of the title is updated
        im_file = os.path.join(self.titoloj_dirs, self.dir_of_title, self.title_name + ".png")
        txt_file = os.path.join(self.titoloj_dirs, self.dir_of_title, "titol.txt")
        buf_file = os.path.join(self.titoloj_dirs, self.title_name, "titol.buf")
        pos_file = os.path.join(self.titoloj_dirs, self.dir_of_title, "titol.pos")
        bg_file = os.path.join(self.titoloj_dirs, self.dir_of_title, "titol.bg")
        mocefa_file = os.path.join(self.titoloj_dirs, self.dir_of_title, "titol.mcf")
        # create the directory of the title (dossier,
        # image, texte, buffer_letters, position du titre)
        print("351 ", self.buffer_letters)
        with open(buf_file, "wb") as buffer_file:
            pickle.dump(self.buffer_letters, buffer_file)
#        with open(buf_file, "rb") as buffer_file:
#            self.load_buffer = pickle.load(buffer_file)
#            print("sbl 356", self.load_buffer)
        with open(im_file, "wb") as image_file:
            save_surface.write_to_png(image_file)
        if rgba is not None:
            im_bg = os.path.join(self.titoloj_dirs, self.dir_of_title, self.title_name + "_bg.png")
            with open(im_bg, "wb") as image_file_bg:
                save_surface_bg.write_to_png(image_file_bg)
        with open(txt_file, "wb") as text_file:
            pickle.dump(self.textbuffer.props.text, text_file)
        with open(pos_file, "wb") as position_file:
            pickle.dump([self.x, self.y], position_file)
        with open(bg_file, "wb") as backg_file:
            pickle.dump(self.cairo_background, backg_file)
        with open(mocefa_file, "wb") as mcf_file:
            pickle.dump(self.move_center_fade_file(), mcf_file)
        image_file.close()
        if rgba is not None:
            image_file_bg.close()
        buffer_file.close()
        text_file.close()
        position_file.close()
        backg_file.close()
        mcf_file.close()
        self.clip_replace(im_file, h, rgba, im_bg)
        self.win.destroy()

    def clip_replace(self, im_file, h, rgba=None, im_bg=""):
        print("663 Clip replace")
        clips = sorted(self.timeline.selection, key=lambda x: x.get_start())
        if len(clips) == 1:
            clip = clips[0]
            position = clip.start
            uri_img = "file://" + im_file
        asset = GES.UriClipAsset.request_sync(uri_img)
        print("669 asset", asset)
        if asset.is_image():
            dur = int(self.entry_duration.get_text())
            print("672 dur", dur)
            if dur > 120:
                # The title has a duration max of 120 s
                dur = 120
            clip_duration = dur * Gst.SECOND
        print("413 asset ", asset, asset.get_id(), asset.get_supported_formats())
        if len(im_bg) > 0:
            print("679 im_bg", im_bg)
            uri_bg = "file://" + im_bg
            asset_bg = GES.UriClipAsset.request_sync(uri_bg)
#        if asset_bg.is_image():
##            Gio.AppInfo.launch_default_for_uri(asset.get_id(), None)
#            clip_duration = self.app.settings.titleClipLength * Gst.MSECOND
        # The image of the title is removed out the timeline
        #pylint: disable=protected-access
        self.tlc._deleteSelected(unused_action=None, unused_parameter=None)
        # Anew image is put on the timeline
        offset_t = position
        print("421 off dur ", offset_t, offset_t + clip_duration)
        with self.app.action_log.started("add layer 0 1",
                                         finalizing_action=CommitTimelineFinalizingAction(self.app.project_manager.current_project.pipeline)):
            layers = self.timeline.ges_timeline.get_layers()
            intersecting_clips_0 = layers[0].get_clips_in_interval(offset_t,
                                                                   offset_t + clip_duration)
            if intersecting_clips_0:
                nl = self.timeline.create_layer(0)
                print("696 nl layer", nl)
            else:
                nl = layers[0]
                print("699 nl layer")
            if len(im_bg) > 0:
                intersecting_clips_1 = layers[1].get_clips_in_interval(offset_t,
                                                                       offset_t + clip_duration)
                if intersecting_clips_1:
                    nl_bg = self.timeline.create_layer(1)
                    print("704 nl_bg layer", nl_bg)
                else:
                    nl_bg = layers[1]
                    print("707 nl_bg layer", nl_bg)
        with self.app.action_log.started("add asset",
                                         finalizing_action=CommitTimelineFinalizingAction(self.app.project_manager.current_project.pipeline)):
            ges_clip = nl.add_asset(asset, offset_t, 0, clip_duration,
                                    track_types=asset.get_supported_formats())
            if len(im_bg) > 0:
                ges_clip_bg = nl_bg.add_asset(asset_bg, offset_t, 0,
                                              clip_duration, track_types=asset.get_supported_formats())
            print("713 ges_clip --------", ges_clip, ges_clip.get_uri())
        if self.credits_up:
            self.title_vup_move(ges_clip, h)
        if self.credits_down:
            self.title_vdown_move(ges_clip, h)
        if self.fade_in:
            self.title_fade_in(ges_clip)
        if self.fade_out:
            self.title_fade_out(ges_clip)
        if self.fade_in_out:
            self.title_fade_inout(ges_clip)
        if len(im_bg) > 0:
            self.timeline.selection.set_selection([ges_clip, ges_clip_bg], SELECT)
            # group the two clips : from timeline.py  def _group_selected_cb
            with self.app.action_log.started("group",
                                             finalizing_action=CommitTimelineFinalizingAction(self.app.project_manager.current_project.pipeline),
                                             toplevel=True):
                toplevels = self.timeline.selection.toplevels
                if toplevels:
                    GES.Container.group(list(toplevels))

                # timeline.selection doesn't change during grouping,
                # we need to manually update group actions.
                self.timeline.selection.set_can_group_ungroup()
                self.tlc.update_actions()
        self.timeline.selection.set_selection([], SELECT)

    def move_center_fade_values(self, liste):
        # pylint: disable=attribute-defined-outside-init
        for mo_ce_fav in liste:
            self.center_h = mo_ce_fav
            self.center_v = mo_ce_fav
            self.center_hv = mo_ce_fav

            self.credits_up = mo_ce_fav
            self.credits_down = mo_ce_fav

            self.fade_in = mo_ce_fav
            self.fade_in_out = mo_ce_fav
            self.fade_out = mo_ce_fav


    def bouton_press_event(self, widget, event):
        # pylint: disable=attribute-defined-outside-init
        res, button = event.get_button()
        return res and button
#        if res and button == 1:
##            print("Coord = ", event.x, event.y)
#            return True
#        else:
#            return False

    def motion_notify_event(self, widget, event):
        # pylint: disable=unused-variable
        # pylint: disable=attribute-defined-outside-init
        if event.is_hint:
            x, y, etat = event.window.get_pointer()
        else:
            self.x = event.x
            self.y = event.y
            self.draw_event(self.s_title, self.context)
            self.title_box.hide()
            self.title_box.show_all()

    def bouton_release_event(self, widget, event):
#        print("ctx = ", self.context)
        # pylint: disable=attribute-defined-outside-init
        res, button = event.get_button()
        if res and button == 1:
#            print("Coord R = ", event.x, event.y)
            self.x = event.x
            self.y = event.y
            self.draw_event(self.s_title, self.context)
#            self.s_title.queue_draw()
            self.title_box.hide()
            self.title_box.show_all()
            return True
        else:
            return False

    def draw_event(self, widget, ctx):
        # pylint: disable=attribute-defined-outside-init
        self.context = ctx
        print("867 s context ", self.context)
        if self.cairo_background == []:  # Image background
            Gdk.cairo_set_source_pixbuf(ctx, self.pixbuf, 0, 0)
        else: #  Color background
            rgba = self.background_rgba
            Gdk.cairo_set_source_rgba(self.context, rgba)
        ctx.paint()
        self.show_buffer_bl(self.context)
#        self.fade_in_out_button.set_active(True)

    def _text_changed_cb(self, unused_updated_obj):
        print("text changed")
        print("719 self.textbuffer.get_char_count",
              self.textbuffer.get_char_count(), "stb ", self.textbuffer.props.text)
        self.analyze_text()
        print("text analyzed")
        self.draw_event(self.s_title, self.context)
        print("draw_event passed")
        self.title_box.hide()
        self.title_box.show_all()

    def analyze_text(self):
        """Search to fill the buffer."""
        # pylint: disable=attribute-defined-outside-init
        print("851 self.textbuffer.get_char_count",\
              self.textbuffer.get_char_count(), "stb ", self.textbuffer.props.text)
        if self.title_text == "Titre":
            self.buffer_letters = []
            self.show_buffer_bl(self.context)
            self.title_text = ""
        if len(self.stock_text) < self.textbuffer.get_char_count():
            print("857 Add")
            # add
            # search the letter name in the text buffer
            index_text = self.textbuffer.props.text.find(self.stock_text)
            if index_text == 0:
                print("862 Add end")
                # The add is at the end
                letter_names = self.textbuffer.props.text[len(self.stock_text):]
                print("\n 865 letter ", letter_names)
                if self.buffer_letters == []:
                    color = self.letter_format["color"]
                    bg = self.letter_format["color"]
                    font = self.letter_format["font"]
                else:  # Take the caracteristics of the last character ef self.stock_text
                    print("871 len(self.stock_text)", len(self.stock_text))
                    color = self.buffer_letters[len(self.stock_text) - 1]["color"]
                    bg = self.buffer_letters[len(self.stock_text) - 1]["bg"]
                    font = self.buffer_letters[len(self.stock_text) - 1]["font"]
                # add the letters to the letter buffer
                i_slb = 0
                for l_n in letter_names:
                    if self.load == "":  # Take the caracteristics of the last character
                        letter = {"letter_name":l_n, "color":color, "bg":bg, "font":font}
                    else:  # Load from an existant title
#                        print("881 slb ", self.load_buffer, "i", i_slb)
                        color = self.load_buffer[i_slb]["color"]
                        print("Color ", color)
                        bg = self.load_buffer[i_slb]["bg"]
                        font = self.load_buffer[i_slb]["font"]
                        letter = {"letter_name":l_n, "color":color, "bg":bg, "font":font}
                        print("\n 887 letter ", letter)
                        i_slb += 1
                        # pylint: disable=anomalous-backslash-in-string
                        print("\889 i", i_slb)
                    print("\n 890 letter ", letter)
                    self.buffer_letters.append(letter)
                if self.load != "":
                    self.load = ""
                self.title_text = self.textbuffer.props.text
                self.stock_text = self.textbuffer.props.text
                print("896 stt", self.stock_text)
                self.show_buffer_bl(self.context)
            elif index_text > 0:
                # The add is at the start
                print("900 Add start")
                len_s = len(self.textbuffer.props.text) -len(self.stock_text)
                print("902 len", len_s)
                letter_names = self.textbuffer.props.text[:len_s]
#                letter_name = self.textbuffer.props.text[0]
                color = self.buffer_letters[1]["color"]
                bg = self.buffer_letters[1]["color"]
                font = self.buffer_letters[1]["font"]
                # add the letters to the letter buffer
                for nl in range(len(letter_names)-1, -1, -1):
                    letter = {"letter_name":letter_names[nl], "color":color, "bg":bg, "font":font}
                    print("letter 911", letter)
                    self.buffer_letters.insert(0, letter)
                self.title_text = self.textbuffer.props.text
                self.stock_text = self.textbuffer.props.text
                self.show_buffer_bl(self.context)
            elif index_text == -1:
                # The add is at the middle
                print("918 Add middle")
                i = 0
                while self.stock_text[i] == self.textbuffer.props.text[i]:
                    i += 1
#                letter_name = self.textbuffer.props.text[i]
                j = len(self.textbuffer.props.text) - 1
                k = len(self.stock_text) - 1
                while self.stock_text[k] == self.textbuffer.props.text[j]:
                    j -= 1
                    k -= 1
                color = self.buffer_letters[i]["color"]
                bg = self.buffer_letters[i]["color"]
                font = self.buffer_letters[i]["font"]
                # add the letters to the letter buffer
                for nl in range(i, j + 1):
                    letter = {"letter_name":self.textbuffer.props.text[nl],
                              "color":color, "bg":bg, "font":font}
                    print("letter 934", letter)
                    self.buffer_letters.insert(nl, letter)
                self.title_text = self.textbuffer.props.text
                self.stock_text = self.textbuffer.props.text
                self.show_buffer_bl(self.context)
        elif self.textbuffer.get_char_count() == 0:
            print("\n937 Vide ")
            self.buffer_letters = []
            self.title_text = ""
            self.show_buffer_bl(self.context)
            print("941 title_text", self.title_text)
#            self.title_text = self.textbuffer.props.text
#            self.stock_text = self.textbuffer.props.text
#            self.show_buffer_bl(self.context)
        elif len(self.stock_text) == self.textbuffer.get_char_count():
            # Replace
            print("947 Replace")
            i = 0
            while self.stock_text[i] == self.textbuffer.props.text[i]:
                i += 1
#                letter_name = self.textbuffer.props.text[i]
            j = len(self.textbuffer.props.text) - 1
            k = len(self.stock_text) - 1
            while self.stock_text[k] == self.textbuffer.props.text[j]:
                j -= 1
                k -= 1
            color = self.buffer_letters[i]["color"]
            bg = self.buffer_letters[i]["color"]
            font = self.buffer_letters[i]["font"]
            # add the letters to the letter buffer
            for nl in range(i, j + 1):
                letter = {"letter_name":self.textbuffer.props.text[nl],
                          "color":color, "bg":bg, "font":font}
                print("letter 797", letter)
                self.buffer_letters.insert(nl, letter)
            self.title_text = self.textbuffer.props.text
            self.stock_text = self.textbuffer.props.text
            self.show_buffer_bl(self.context)
        else:
            # substract
            #  = if len(self.stock_text) > self.textbuffer.get_char_count()
            print("971 substract")
            index_end_of_start, index_start_of_end = 0, 0

            # Part to remove
#            print("lettres buffer 377 = ", self.buffer_letters)
            index_end_of_start, index_start_of_end = self.part_to_remove()
#            print("lettres buffer 459 = ", self.buffer_letters)

            # Remove
            if index_end_of_start == index_start_of_end:
                print("981 index_end_of_start", index_start_of_end)
                del self.buffer_letters[index_end_of_start]
            else:
                del self.buffer_letters[index_end_of_start:index_start_of_end + 1]
#            print("lettre buffer 386= ", self.buffer_letters)
            self.title_text = self.textbuffer.props.text
            self.stock_text = self.textbuffer.props.text
            self.show_buffer_bl(self.context)


    def part_to_remove(self):
        str_buff = ""
        str_text = ""
        # Two strings for comparison
        for i in self.buffer_letters:
            str_buff += i["letter_name"]
        str_text = self.textbuffer.props.text
        diff_str = self.diff_str(str_buff, str_text)
        print("1081 diff_str", diff_str)
        index_start = diff_str[0]
        index_end = diff_str[1]
        return index_start, index_end

    def diff_str(self, str1, str2):
        # E
        ec = len(str1) - len(str2)
        for i in range(len(str2)):
            print(i, str1[i], str1[:i + 1])
            if str2.startswith(str1[:i + 1]) is False:
                start = i
                break
#            if str2.startswith(str1[:i + 1]) is True:
#                continue
#            else:
#                start = i
#                break
        else:
            # Last characters are removed
            start = i + 1

        print("\n===========")
        for i in range(len(str2) - 1, -1, -1):
            print(str(i), str2[i])
            print(str1[i+ ec])
            print(str1[i+ ec:], " -- ")

            if str2.endswith(str1[i+ ec:]) is False:
                end = i + ec
                break
#            if str2.endswith(str1[i+ ec:]) is True:
#                continue
#            else:
#                end = i + ec
#                break
        else:
            # First characters are removed
            end = i + ec - 1
        return start, end

    # pylint: disable=inconsistent-return-statements
    def show_buffer_bl(self, cr):
        """Show the title on screen."""
        # pylint: disable=attribute-defined-outside-init
        x_adv, y_adv = 0, 0
        line_number = 0
        x_cr, y_cr = self.x- 3, self.y -10
#        line_width = 0
        fheight = 0
        fdescent = 0

        if self.load != "":
            self.buffer_letters = []
            self.load_title(self.load)
            self.textbuffer.props.text = self.title_text
            return

        if self.title_text == "":
            self.title_text = "Titre"
            white_c = [1.0, 1.0, 1.0, 1.0]
            bg_ground = []
            self.buffer_letters = []
            self.letter_format = {"color":white_c, "bg":bg_ground, "font":FONT}
            for lett in self.title_text:
                letter = {}
                letter["letter_name"] = lett
                letter["color"] = self.letter_format["color"]
                letter["bg"] = self.letter_format["bg"]
                letter["font"] = self.letter_format["font"]
                self.buffer_letters.append(letter)
            self.stock_text = self.textbuffer.props.text
            self.show_buffer_bl(self.context)
            print("880 b_l ", self.buffer_letters)
            # pylint: disable=inconsistent-return-statements
            return

        if self.center_h is True:
            list_x_cr = self.parcours_h_center(cr)
        if self.center_v is True:
            list_y_cr = self.parcours_v_center(cr)
        if self.center_hv is True:
            list_x_cr = self.parcours_h_center(cr)
            list_y_cr = self.parcours_v_center(cr)
        for letter_b in self.buffer_letters:
#            print("rd 247 ", self.buffer_letters)
#            print("col ", letter_b["color"])
            cr.set_source_rgba(letter_b["color"][0], letter_b["color"][1],
                               letter_b["color"][2], letter_b["color"][3])
            text_font = letter_b["font"].split(" ")
#            print("tf ", text_font)
            if "Bold" in text_font:
                weight = cairo.FONT_WEIGHT_BOLD
            else:
                weight = cairo.FONT_WEIGHT_NORMAL
            if "Italic" in text_font:
                slant = cairo.FONT_SLANT_ITALIC
            elif "Oblique" in text_font:
                slant = cairo.FONT_SLANT_OBLIQUE
            else:
                slant = cairo.FONT_SLANT_NORMAL
            cr.select_font_face(text_font[0], slant, weight)
            cr.set_font_size(int(text_font[-1]))
            # pylint: disable=unused-variable
            fascent, fdescent, fheight, fxadvance, fyadvance = cr.font_extents()
            xbearing, ybearing, width, height, xadvance, yadvance = (
                cr.text_extents(letter_b["letter_name"]))
            if letter_b["letter_name"].encode("utf-8") == b'\n': # new line
                line_number += 1

                x_adv = 0
                y_adv = line_number * fheight #+ (-ybearing - yadvance)
            else:
                if self.center_h is True:
#                    print("xcr xadvance --", int(x_cr), x_adv, (xbearing + xadvance)/2)
                    x_cr = list_x_cr[line_number]
                if self.center_v is True:
                    print("line number ", line_number)
#                    print("xcr xadvance ---", int(x_cr), x_adv, (xbearing + xadvance)/2)
                    y_cr = self.height/2 - list_y_cr * fheight/2 #list_y_cr[line_number]
#                    y_adv = 0
                    print("ycr ", y_cr, list_y_cr, y_cr + y_adv + 0.5 - fdescent + fheight / 2)
                if self.center_hv is True:
                    x_cr = list_x_cr[line_number]
                    print("line number ", line_number)
                    y_cr = self.height/2 - list_y_cr * fheight/2 #list_y_cr[line_number]
                coord_x, coord_y = x_cr + x_adv, y_cr + y_adv + 0.5 - fdescent + fheight / 2
                cr.move_to(coord_x, coord_y)
                cr.show_text(letter_b["letter_name"])
                x_adv += xbearing + xadvance
        # pylint: disable=inconsistent-return-statements
        return (line_number + 2) * fheight, y_cr + y_adv + 0.5 - fdescent + fheight / 2

    def parcours_h_center(self, cr):
        x_adv = 0
        x_cr_middle = []  # list of lines start
        for letter_b in self.buffer_letters:
            cr.set_source_rgba(letter_b["color"][0], letter_b["color"][1],
                               letter_b["color"][2], letter_b["color"][3])
            text_font = letter_b["font"].split(" ")
            if "Bold" in text_font:
                weight = cairo.FONT_WEIGHT_BOLD
            else:
                weight = cairo.FONT_WEIGHT_NORMAL
            if "Italic" in text_font:
                slant = cairo.FONT_SLANT_ITALIC
            elif "Oblique" in text_font:
                slant = cairo.FONT_SLANT_OBLIQUE
            else:
                slant = cairo.FONT_SLANT_NORMAL
            cr.select_font_face(text_font[0], slant, weight)
            cr.set_font_size(int(text_font[-1]))
#            fascent, fdescent, fheight, fxadvance, fyadvance = cr.font_extents()
            # pylint: disable=unused-variable
            xbearing, ybearing, width, height, xadvance, yadvance = (
                cr.text_extents(letter_b["letter_name"]))
            if letter_b["letter_name"].encode("utf-8") == b'\n': # new line
                x_cr_middle.append((self.width_title_box - x_adv) / 2)
                x_adv = 0
            else:
                x_adv += xbearing + xadvance
        x_cr_middle.append((self.width_title_box - x_adv) / 2)
#        print("x_cr_middle x_adv+++++++++++++++++", x_cr_middle, x_adv)
        return x_cr_middle

    def parcours_v_center(self, cr):
        print("sh ", self.height/2)
        line_number = 0

        for letter_b in self.buffer_letters:
#            print("letter ", letter_b["letter_name"])
           # pylint: disable=unused-variable
            fascent, fdescent, fheight, fxadvance, fyadvance = self.context.font_extents()
            xbearing, ybearing, width, height, xadvance, yadvance = (
                cr.text_extents(letter_b["letter_name"]))
            if letter_b["letter_name"].encode("utf-8") == b'\n': # new line
                print("new line")
                line_number += 1
            else:
                continue
        return line_number

# ################ Modif font, color, background
    def _font_button_cb(self, widget):
        """Create the font."""
        # pylint: disable=attribute-defined-outside-init
        print("nt font button = ", self.title_list_tags)
#        found = False
        font_desc = widget.get_font_desc().to_string()
        print(font_desc)
#        pango_font =  Pango.font_description_from_string (font_desc)
#        print("pango ", pango_font)
        tag_name = "font"
        text_font = font_desc.split(" ")
        for t_f in text_font:
            tag_name += "_" + t_f
        print("tag name = ", tag_name)
        table_buffer = self.textbuffer.get_tag_table()
        tag_look = table_buffer.lookup(tag_name)
        if tag_look is None:
            self.tag_new = self.textbuffer.create_tag(tag_name)  # , weight=Pango.Weight.BOLD
            print("tag new ", self.tag_new)
        else:
            self.tag_new = tag_look
        self.font_modif(self.tag_new, tag_name, font_desc)

    def font_modif(self, new_tag, tag_name, font_desc):
        """Create the tag of the font in the selected text."""
#        exist = False
        print("sbuf %= ", self.textbuffer.props.text)
        bounds = self.textbuffer.get_selection_bounds()
        if len(bounds) != 0:
            start, end = bounds
            print("start - end ", start.get_offset(), end.get_offset())
            self.textbuffer.apply_tag(new_tag, start, end)
            for i in range(len(self.buffer_letters)):
                # pylint: disable=chained-comparison
                if i >= start.get_offset() and i < end.get_offset():
                    self.buffer_letters[i]["font"] = font_desc
            print("bl ", self.buffer_letters)
        else:
            self.letter_format["font"] = font_desc
            print("self.letter_format ", self.letter_format)

    def _front_text_color_button_cb(self, widget):
        """Create the color."""
        # pylint: disable=attribute-defined-outside-init
        print("nt color button = ", self.title_list_tags)
        tag_name = ""
        cairo_color = []
#        found = False

#        color = self.gdk_rgba_to_argb(widget.get_rgba())# ##_ à supprimer
#        rgba = self.argb_to_gdk_rgba(color) # ##  à supprimer
#        col = self.unpack_color(color) # ##  à supprimer # alpha, red, green, blue
        color = gdk_rgba_to_argb(widget.get_rgba())
        rgba = argb_to_gdk_rgba(color)  # à rétablir
#        col = unpack_color(color)  # alpha, red, green, blue
        hex_c = self.argb_to_hex(color)  # 0x, alpha, red, green, blue
        hex_6bytes = "#" + hex_c[4:]
        cairo_color.append(float(rgba.red))  # [0]
        cairo_color.append(float(rgba.green))  # [1]
        cairo_color.append(float(rgba.blue))  # [2]
        cairo_color.append(float(rgba.alpha))  #[3]
        print("color = ", color, rgba, cairo_color, hex_c, hex_6bytes)  # , col
        tag_name = "color_" + hex_c
        print("tag name = ", tag_name)
        table_buffer = self.textbuffer.get_tag_table()
        tag_look = table_buffer.lookup(tag_name)
        if tag_look is None:
            self.tag_new = self.textbuffer.create_tag(tag_name)  # , weight=Pango.Weight.BOLD
            print("tag new ", self.tag_new)
        else:
            self.tag_new = tag_look
        self.color_modif(self.tag_new, tag_name, cairo_color)

    def color_modif(self, new_tag, tag_name, col):
        """Create the tag of the color in the selected text."""
#        exist = False
        print("sbuf %= ", self.textbuffer.props.text)
        bounds = self.textbuffer.get_selection_bounds()
        if len(bounds) != 0:
            start, end = bounds
            print("start - end ", start.get_offset(), end.get_offset())
            if self.tag_new is not None:
                self.textbuffer.apply_tag(new_tag, start, end)
            for i in range(len(self.buffer_letters)):
                # pylint: disable=chained-comparison
                if i >= start.get_offset() and i < end.get_offset():
                    self.buffer_letters[i]["color"] = col
        else:
            self.letter_format["color"] = col

    def _background_color_button_cb(self, widget):
        """Create the color of the background of the title.

        Create the tag of the color
        """
        # pylint: disable=attribute-defined-outside-init
        print("nt color button = ", self.title_list_tags)
        tag_name = ""
        cairo_color = []
        color = gdk_rgba_to_argb(widget.get_rgba())
#        rgba = argb_to_gdk_rgba(color)
        rgba = widget.get_rgba()
#        col = unpack_color(color)  # alpha, red, green, blue  à rétablir
        hex_c = self.argb_to_hex(color)  # 0x, alpha, red, green, blue
        hex_6bytes = "#" + hex_c[4:]
        cairo_color.append(float(rgba.red))  # [0]
        cairo_color.append(float(rgba.green))  # [1]
        cairo_color.append(float(rgba.blue))  # [2]
        cairo_color.append(float(rgba.alpha))  #[3]
        print("color = ", color, rgba, cairo_color, hex_c, hex_6bytes)  # , col
        tag_name = "color_" + hex_c
        print("tag name = ", tag_name)
        table_buffer = self.textbuffer.get_tag_table()
        tag_look = table_buffer.lookup(tag_name)
        if tag_look is None:
            self.tag_new = self.textbuffer.create_tag(tag_name)  # , weight=Pango.Weight.BOLD
            print("tag new ", self.tag_new)
        else:
            self.tag_new = tag_look
        self.background_modif(self.tag_new, tag_name, rgba, cairo_color)

    def background_modif(self, new_tag, tag_name, rgba, cairo_color):
        """Create the background."""
        # pylint: disable=attribute-defined-outside-init
        print("sbuf %= ", self.textbuffer.props.text)
        self.cairo_background = cairo_color
        if self.cairo_background[3] == 0:
            self.cairo_background = []  # No color background, image background
        else:
            self.background_rgba = rgba
        print("rgba", self.background_rgba)
#        Gdk.cairo_set_source_rgba(save_context_bg, rgba)
#        save_context_bg.paint()
        self.context.rectangle(0, 0, self.width_title_box, self.height) # 50, 50)  #
        self.context.fill()
        self.context.paint()
        self.show_buffer_bl(self.context)

# ################ End of Modif font, color, background

# ################ Center move and fade

    def _center_h_text_cb(self, widget):
        # pylint: disable=attribute-defined-outside-init
        if self.h_center_button.get_active():
            self.h_center_button.set_label("Center")
            self.center_align_label.set_markup(
                '<span foreground="#8dfb85" font_weight="bold">Center</span>')
            self.center_h_label.set_markup(
                '<span foreground="#8dfb85" font_weight="bold">Horizontal</span>')
            self.center_h = True
            self.show_buffer_bl(self.context)
#            self.title_box.hide()
#            self.title_box.show_all()
        else:
            self.h_center_button.set_label("Off")
            self.center_align_label.set_markup('Center')
            self.center_h_label.set_markup("Horizontal")
            self.center_h = False
            self.show_buffer_bl(self.context)
        self.title_box.hide()
        self.title_box.show_all()

    def _center_v_text_cb(self, widget):
        # pylint: disable=attribute-defined-outside-init
        if self.v_center_button.get_active():
            self.v_center_button.set_label("Middle")
            self.center_align_label.set_markup(
                '<span foreground="#8dfb85" font_weight="bold">Center</span>')
            self.center_v_label.set_markup(
                '<span foreground="#8dfb85" font_weight="bold">Vertical</span>')
            self.center_v = True
            self.show_buffer_bl(self.context)
        else:
            self.v_center_button.set_label("Off")
            self.center_align_label.set_markup('Center')
            self.center_v_label.set_markup("Vertical")
            self.center_v = False
            self.show_buffer_bl(self.context)
        self.title_box.hide()
        self.title_box.show_all()

    def _center_hv_text_cb(self, widget):
        # pylint: disable=attribute-defined-outside-init
        if self.hv_center_button.get_active():
            self.hv_center_button.set_label("Center-Middle")
            self.center_align_label.set_markup(
                '<span foreground="#8dfb85" font_weight="bold">Center</span>')
            self.center_hv_label.set_markup(
                '<span foreground="#8dfb85" font_weight="bold">Center-Middle</span>')
            self.center_hv = True
            self.show_buffer_bl(self.context)
            self.title_box.hide()
            self.title_box.show_all()
        else:
            self.hv_center_button.set_label("Off")
            self.center_align_label.set_markup('Center')
            self.center_hv_label.set_markup("Both")
            self.center_hv = False
            self.show_buffer_bl(self.context)
            self.title_box.hide()
            self.title_box.show_all()
        self.title_box.hide()
        self.title_box.show_all()

    def _credits_down(self, widget):
#        self.credits_down = True
#        self.source.set_child_property(prop, value)
        # pylint: disable=attribute-defined-outside-init
        if self.down_button.get_active():
            self.up_button.set_active(False)
            self.down_button.set_label("Down")
            self.label_credits.set_markup(
                '<span foreground="#8dfb85" font_weight="bold">Move</span>')
            self.credits_down = True
            print("down True", self.credits_up)
#            self.show_buffer_bl(self.context)
        else:
            self.down_button.set_label("Off")
            self.label_credits.set_markup("Move")
            self.credits_down = False
            print("up False ", self.credits_down)
        self.show_buffer_bl(self.context)
        self.title_box.hide()
        self.title_box.show_all()

    def _credits_up(self, widget):
        # pylint: disable=attribute-defined-outside-init
        if self.up_button.get_active():
            self.down_button.set_active(False)
            self.up_button.set_label("Up")
            self.label_credits.set_markup(
                '<span foreground="#8dfb85" font_weight="bold">Move</span>')
            self.credits_up = True
            print("up True")
        else:
            self.up_button.set_label("Off")
            self.label_credits.set_markup("Move")
            self.credits_up = False
            print("up False")
        self.show_buffer_bl(self.context)
        self.title_box.hide()
        self.title_box.show_all()

    def _fadein_cb(self, widget):
        # pylint: disable=attribute-defined-outside-init
        if self.fade_in_button.get_active():
            self.fade_in_button.set_label("In")
            self.label_fade.set_markup('<span foreground="#8dfb85" font_weight="bold">Fade</span>')
            self.fade_in_label.set_markup(
                '<span foreground="#8dfb85" font_weight="bold">Fade in</span>')
            self.fade_in = True
            print("fade_in True")
            self.fade_in_out_button.set_active(False)
            self.fade_in_out_button.set_label("Off")
            self.fade_in_out_label.set_markup("Fade in and out")
            self.fade_in_out = False
#            self.fade_out_button.set_label("Off")
#            self.fade_out_label.set_markup("Fade in and out")
#            self.fade_out = False
        else:
            self.fade_in_button.set_label("Off")
            self.label_fade.set_markup("Fade")
            self.fade_in_label.set_markup("Fade in")
            self.fade_in = False
            print("fade_in False")
#        self.show_buffer_bl(self.context)
        self.title_box.hide()
        self.title_box.show_all()

    def _fadeout_cb(self, widget):
        # pylint: disable=attribute-defined-outside-init
        if self.fade_out_button.get_active():
            self.fade_out_button.set_label("Out")
            self.label_fade.set_markup('<span foreground="#8dfb85" font_weight="bold">Fade</span>')
            self.fade_out_label.set_markup(
                '<span foreground="#8dfb85" font_weight="bold">Fade out</span>')
            self.fade_out = True
            print("fade_out True")
            self.fade_in_out_button.set_active(False)
            self.fade_in_out_button.set_label("Off")
            self.fade_in_out_label.set_markup("Fade in and out")
            self.fade_in_out = False
#            self.fade_in_out_button.set_label("Off")
#            self.fade_in_out_label.set_markup("Fade in and out")
#            self.fade_in_out = False
        else:
            self.fade_out_button.set_label("Off")
            self.label_fade.set_markup("Fade")
            self.fade_out_label.set_markup("Fade out")
            self.fade_out = False
            print("fade_out False")
#        self.show_buffer_bl(self.context)
        self.title_box.hide()
        self.title_box.show_all()

    def _fadeinout_cb(self, widget):
        # pylint: disable=attribute-defined-outside-init
        if self.fade_in_out_button.get_active():
            self.fade_in_out_button.set_label("In / out")
            self.label_fade.set_markup(
                '<span foreground="#8dfb85" font_weight="bold">Fade</span>')
            self.fade_in_out_label.set_markup(
                '<span foreground="#8dfb85" font_weight="bold">Fade in and out</span>')
            self.fade_in_out = True
            print("fade_in out True")
            self.fade_in_button.set_active(False)
            self.fade_in = False
            self.fade_in_button.set_label("Off")
            self.fade_in_label.set_markup("Fade in")
            self.fade_in = False
            self.fade_out_button.set_active(False)
            self.fade_out_button.set_label("Off")
            self.fade_out_label.set_markup("Fade out")
            self.fade_out = False
            print("fade out+in False")
        else:
            self.fade_in_out_button.set_label("Off")
            self.label_fade.set_markup("Fade")
            self.fade_in_out_label.set_markup("Fade in and out")
            self.fade_in_out = False
            print("fade_in out False")
#        self.show_buffer_bl(self.context)
        self.title_box.hide()
        self.title_box.show_all()

    def title_vup_move(self, ges_clip, h_t):
#        h_title = int(h[0])
        # pylint: disable=attribute-defined-outside-init
        pos_title = int(h_t[1])
        delta_title = int(h_t[0]) + int(h_t[1])

        source = ges_clip.find_track_element(None, GES.VideoSource)
        print("source", source)
        source.set_child_property("posy", 10)
        print("in point out point", source.props.in_point,
              source.props.in_point + source.props.duration)
        res, val = source.get_child_property("posy")
        print("res, val", res, val)
        control_source = GstController.InterpolationControlSource()
        control_source.props.mode = GstController.InterpolationMode.LINEAR
        source.set_control_source(control_source, "posy", "direct-absolute")
        control_source.set(source.props.in_point, 1080 + self.mult * (pos_title))
        control_source.set(source.props.in_point + source.props.duration, - self.mult * delta_title)
        binding = source.get_control_binding("posy")
        print("binding", binding)

    def title_vdown_move(self, ges_clip, h_t):
#        h_title = int(h[0])
        # pylint: disable=attribute-defined-outside-init
        pos_title = int(h_t[1])
        delta_title = int(h_t[0]) + int(h_t[1])

        source = ges_clip.find_track_element(None, GES.VideoSource)
        print("source", source)
        source.set_child_property("posy", 10)
        res, val = source.get_child_property("posy")
        print("res, val", res, val)
        control_source = GstController.InterpolationControlSource()
        control_source.props.mode = GstController.InterpolationMode.LINEAR
        source.set_control_source(control_source, "posy", "direct-absolute")
        control_source.set(source.props.in_point, - self.mult * delta_title)
        control_source.set(source.props.in_point + source.props.duration,
                           1080 + self.mult * (pos_title))
        binding = source.get_control_binding("posy")
        print("binding", binding)

    #  pylint: disable=no-self-use
    def title_fade_in(self, clip):
        self.timeline.selection.set_selection([clip], SELECT)
        inpoint = clip.get_inpoint()
        start = clip.get_start()
        offset_t = 1 * Gst.SECOND
        print("st in of ", inpoint, start, offset_t)
        ges_track_elements = clip.find_track_elements(None, GES.TrackType.VIDEO, GES.Source)
        print("gtes ", ges_track_elements)
        for ges_track_element in ges_track_elements:
            keyframe_curve_t = ges_track_element.ui.keyframe_curve
            # Reading only a protected object
            # pylint: disable=protected-access
            offsets = keyframe_curve_t._keyframes.get_offsets()
            print("offsets -1 = ", offsets)
        keyframe_curve_t.toggle_keyframe(offset_t)
        #  pylint: disable=protected-access
        keyframe_curve_t._move_keyframe(int(offsets[0][0]), inpoint, 0)

    #  pylint: disable=no-self-use
    def title_fade_out(self, clip):
        self.timeline.selection.set_selection([clip], SELECT)
        start = clip.get_start()
        end = start + clip.duration
        offset_t = clip.duration - 1 * Gst.SECOND
        ges_track_elements = clip.find_track_elements(None, GES.TrackType.VIDEO, GES.Source)
        ges_track_element = ges_track_elements[0]
        keyframe_curve_t = ges_track_element.ui.keyframe_curve
        # pylint: disable=protected-access
        offsets = keyframe_curve_t._keyframes.get_offsets()
        keyframe_curve_t.toggle_keyframe(offset_t)
        offsets = keyframe_curve_t._keyframes.get_offsets()
        offset = offsets[- 1][0]
        offsets[- 1][1] = 0
        print("offsets dur d = ", offset, offsets)
        keyframe_curve_t._move_keyframe(end, int(offset), 0)
        print("offsets -3 = ", offsets)

    def title_fade_inout(self, clip):
        self.timeline.selection.set_selection([clip], SELECT)
        inpoint = clip.get_inpoint()
        start = clip.get_start()
        end = start + clip.duration
        offset_t_s = clip.duration - 1 * Gst.SECOND
        offset_t_e = 1 * Gst.SECOND
        ges_track_elements = clip.find_track_elements(None, GES.TrackType.VIDEO, GES.Source)
        ges_track_element = ges_track_elements[0]
        keyframe_curve_t = ges_track_element.ui.keyframe_curve
        # pylint: disable=protected-access
        keyframe_curve_t.toggle_keyframe(offset_t_s)
        keyframe_curve_t.toggle_keyframe(offset_t_e)
        offsets = keyframe_curve_t._keyframes.get_offsets()
        offset_e = offsets[- 1][0]
        offsets[- 1][1] = 0
        keyframe_curve_t._move_keyframe(end, int(offset_e), 0)
        keyframe_curve_t._move_keyframe(int(offsets[0][0]), inpoint, 0)

# ################ End of Center move and fade



    def _update_source_cb(self, updated_obj):
        """Handles changes in the advanced property widgets at the bottom."""
        if not self.source:
            # Nothing to update.
            return

    def on_clear_clicked(self, widget):
        start = self.textbuffer.get_start_iter()
        end = self.textbuffer.get_end_iter()
        self.textbuffer.remove_all_tags(start, end)

    def argb_to_hex(self, color_int):
        return hex(color_int)


    def do_deactivate(self):
        self.app.gui.editor.timeline_ui.toolbar.remove(self.button)
