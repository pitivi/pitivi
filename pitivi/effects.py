# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2010, Thibault Saunier <tsaunier@gnome.org>
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
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
"""Effects categorization and management.

 There are different types of effects available:
  _ Simple Audio/Video Effects
     GStreamer elements that only apply to audio OR video
     Only take the elements who have a straightforward meaning/action
  _ Expanded Audio/Video Effects
     These are the Gstreamer elements that don't have a easy meaning/action or
     that are too cumbersome to use as such
  _ Complex Audio/Video Effects
"""
import os
import re
import subprocess
import sys
import threading
from gettext import gettext as _

import cairo
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GES
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import Pango

from pitivi.configure import get_pixmap_dir
from pitivi.configure import get_ui_dir
from pitivi.settings import GlobalSettings
from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import EFFECT_TARGET_ENTRY
from pitivi.utils.ui import PADDING
from pitivi.utils.ui import SPACING
from pitivi.utils.widgets import FractionWidget
from pitivi.utils.widgets import GstElementSettingsWidget

(VIDEO_EFFECT, AUDIO_EFFECT) = list(range(1, 3))

ALLOWED_ONLY_ONCE_EFFECTS = ['videoflip']

EFFECTS_CATEGORIES = (
    (_("Colors"), (
        # Mostly "serious" stuff that relates to correction/adjustments
        # Fancier stuff goes into the "fancy" category
        'burn', 'chromahold', 'cogcolorspace', 'coloreffects', 'dodge',
        'exclusion', 'frei0r-filter-3-point-color-balance',
        'frei0r-filter-brightness', 'frei0r-filter-bw0r',
        'frei0r-filter-color-distance', 'frei0r-filter-coloradj-rgb',
        'frei0r-filter-contrast0r', 'frei0r-filter-curves',
        'frei0r-filter-equaliz0r', 'frei0r-filter-gamma', 'frei0r-filter-glow',
        'frei0r-filter-hueshift0r', 'frei0r-filter-invert0r',
        'frei0r-filter-levels', 'frei0r-filter-primaries',
        'frei0r-filter-saturat0r', 'frei0r-filter-sop-sat',
        'frei0r-filter-threelay0r', 'frei0r-filter-threshold0r',
        'frei0r-filter-tint0r', 'frei0r-filter-twolay0r',
        'frei0r-filter-white-balance', 'gamma', 'videobalance', 'videomedian',
    )),
    (_("Compositing"), (
        'alpha', 'alphacolor', 'frei0r-filter-alpha0ps',
        'frei0r-filter-alphagrad', 'frei0r-filter-alphaspot',
        'frei0r-filter-bluescreen0r', 'frei0r-filter-mask0mate',
        'frei0r-filter-select0r', 'frei0r-filter-transparency',
        'gdkpixbufoverlay',
    )),
    (_("Noise & blur"), (
        'diffuse', 'dilate', 'frei0r-filter-edgeglow', 'frei0r-filter-facebl0r',
        'frei0r-filter-hqdn3d', 'frei0r-filter-sharpness',
        'frei0r-filter-squareblur', 'gaussianblur', 'marble', 'smooth',
    )),
    (_("Analysis"), (
        'frei0r-filter-b', 'frei0r-filter-g', 'frei0r-filter-luminance',
        'frei0r-filter-opencvfacedetect', 'frei0r-filter-pr0be',
        'frei0r-filter-pr0file', 'frei0r-filter-r', 'frei0r-filter-rgb-parade',
        'frei0r-filter-vectorscope', 'navigationtest', 'revtv', 'videoanalyse',
        'videodetect', 'videomark',
    )),
    (_("Geometry"), (
        'aspectratiocrop', 'bulge', 'circle', 'cogdownsample', 'cogscale',
        'fisheye', 'frei0r-filter-3dflippo', 'frei0r-filter-c0rners',
        'frei0r-filter-defish0r', 'frei0r-filter-flippo',
        'frei0r-filter-k-means-clustering', 'frei0r-filter-lens-correction',
        'frei0r-filter-letterb0xed', 'frei0r-filter-perspective',
        'frei0r-filter-pixeliz0r', 'frei0r-filter-scale0tilt', 'gdkpixbufscale',
        'kaleidoscope', 'mirror', 'pinch', 'rotate', 'sphere', 'square',
        'stretch', 'twirl', 'videobox', 'videocrop', 'videoflip', 'videoscale',
        'waterriple',
    )),
    (_("Fancy"), (
        'agingtv', 'bulge', 'chromium', 'circle', 'dicetv', 'edgetv', 'fisheye',
        'frei0r-filter-cartoon', 'frei0r-filter-delay0r',
        'frei0r-filter-distort0r', 'frei0r-filter-k-means-clustering',
        'frei0r-filter-light-graffiti', 'frei0r-filter-nosync0r',
        'frei0r-filter-sobel', 'frei0r-filter-tehroxx0r',
        'frei0r-filter-vertigo', 'frei0r-filter-water', 'glfiltersobel',
        'kaleidoscope', 'mirror', 'optv', 'pinch', 'quarktv', 'radioactv',
        'rippletv', 'shagadelictv', 'solarize', 'sphere', 'square', 'streaktv',
        'stretch', 'tunnel', 'twirl', 'vertigotv', 'warptv', 'waterripple',
    )),
    (_("Time"), (
        'frei0r-filter-baltan', 'frei0r-filter-delay0r',
        'frei0r-filter-nervous', 'videorate',
    )),
    (_("Audio"), (
        "pitch", "freeverb", "removesilence", "festival", "speed",
        "audiorate", "volume", "equalizer-nbands", "equalizer-3bands",
        "equalizer-10bands", "rglimiter", "rgvolume", "audiopanorama",
        "audioinvert", "audiokaraoke", "audioamplify", "audiodynamic",
        "audiocheblimit", "audiochebband", "audioiirfilter", "audiowsinclimit",
        "audiowsincband", "audiofirfilter", "audioecho", "scaletempo", "stereo",

        'audioamplify', 'audiochebband', 'audiocheblimit', 'audiodynamic',
        'audioecho', 'audiofirfilter', 'audioiirfilter', 'audioinvert',
        'audiokaraoke', 'audiopanorama', 'audiorate', 'audiowsincband',
        'audiowsinclimit', 'equalizer-10bands', 'equalizer-3bands',
        'equalizer-nbands', 'festival', 'freeverb', 'pitch', 'removesilence',
        'rglimiter', 'rgvolume', 'scaletempo', 'speed', 'stereo', 'volume',
    )),
)

BLACKLISTED_EFFECTS = [
    "alphacolor",
    "cogcolorspace",
    "coglogoinsert",
    "colorconvert",
    "festival",
    "navigationtest",
    "videoanalyse",
    # We prefer to use videocrop, see https://gitlab.gnome.org/GNOME/pitivi/issues/2150
    "videobox",
    "videodetect",
    "volume",
]

BLACKLISTED_PLUGINS = []

HIDDEN_EFFECTS = [
    # Overlaying an image onto a video stream can already be done.
    "gdkpixbufoverlay"]

GlobalSettings.addConfigSection('effect-library')
GlobalSettings.addConfigOption('favourite_effects',
                               section='effect-library',
                               key='favourite-effects',
                               default=[])

ICON_WIDTH = 80
ICON_HEIGHT = 45


class EffectInfo(object):
    """Info for displaying and using an effect.

    Attributes:
        effect_name (str): The bin_description identifying the effect.
    """

    def __init__(self, effect_name, media_type, categories,
                 human_name, description):
        object.__init__(self)
        self.effect_name = effect_name
        self.media_type = media_type
        self.categories = categories
        self.description = description
        self.human_name = human_name

    @property
    def icon(self):
        pixdir = os.path.join(get_pixmap_dir(), "effects")
        try:
            # We can afford to scale the images here, the impact is negligible
            icon = GdkPixbuf.Pixbuf.new_from_file_at_size(
                os.path.join(pixdir, self.effect_name + ".png"),
                ICON_WIDTH, ICON_HEIGHT)
        # An empty except clause is bad, but "gi._glib.GError" is not helpful.
        except:
            icon = GdkPixbuf.Pixbuf.new_from_file_at_size(
                os.path.join(pixdir, "defaultthumbnail.svg"), ICON_WIDTH, ICON_HEIGHT)

        return icon

    @property
    def bin_description(self):
        """Gets the bin description which defines this effect."""
        if self.effect_name.startswith("gl"):
            return "glupload ! %s ! gldownload" % self.effect_name
        else:
            return self.effect_name

    @staticmethod
    def name_from_bin_description(bin_description):
        """Gets the name of the effect defined by the `bin_description`."""
        if bin_description.startswith("glupload"):
            return bin_description.split("!")[1].strip()
        else:
            return bin_description

    def good_for_track_element(self, track_element):
        """Checks the effect is compatible with the specified track element.

        Args:
            track_element (GES.TrackElement): The track element to check against.

        Returns:
            bool: Whether it makes sense to apply the effect to the track element.
        """
        track_type = track_element.get_track_type()
        if track_type == GES.TrackType.AUDIO:
            return self.media_type == AUDIO_EFFECT
        elif track_type == GES.TrackType.VIDEO:
            return self.media_type == VIDEO_EFFECT
        else:
            return False


class EffectsManager(Loggable):
    """Keeps info about effects and their categories.

    Attributes:
        video_effects (List[Gst.ElementFactory]): The available video effects.
        audio_effects (List[Gst.ElementFactory]): The available audio effects.
    """

    def __init__(self):
        Loggable.__init__(self)
        self.video_effects = []
        self.audio_effects = []
        self.gl_effects = []
        self._effects = {}

        useless_words = ["Video", "Audio", "audio", "effect",
                         _("Video"), _("Audio"), _("Audio").lower(), _("effect")]
        uselessRe = re.compile(" |".join(useless_words))

        registry = Gst.Registry.get()
        factories = registry.get_feature_list(Gst.ElementFactory)
        longnames = set()
        duplicate_longnames = set()
        for factory in factories:
            longname = factory.get_longname()
            if longname in longnames:
                duplicate_longnames.add(longname)
            else:
                longnames.add(longname)
        for factory in factories:
            klass = factory.get_klass()
            name = factory.get_name()
            if ("Effect" not in klass or
                    any(black in name for black in BLACKLISTED_PLUGINS)):
                continue

            media_type = None
            if "Audio" in klass:
                self.audio_effects.append(factory)
                media_type = AUDIO_EFFECT
            elif "Video" in klass:
                self.video_effects.append(factory)
                media_type = VIDEO_EFFECT
            if not media_type:
                HIDDEN_EFFECTS.append(name)
                continue

            longname = factory.get_longname()
            if longname in duplicate_longnames:
                # Workaround https://bugzilla.gnome.org/show_bug.cgi?id=760566
                # Add name which identifies the element and is unique.
                longname = "%s %s" % (longname, name)
            human_name = uselessRe.sub("", longname).title()
            effect = EffectInfo(name,
                                media_type,
                                categories=self._getEffectCategories(name),
                                human_name=human_name,
                                description=factory.get_description())
            self._effects[name] = effect

        gl_element_factories = registry.get_feature_list_by_plugin("opengl")
        self.gl_effects = [element_factory.get_name()
                           for element_factory in gl_element_factories]
        if self.gl_effects:
            if "gleffects" in os.environ.get("PITIVI_UNSTABLE_FEATURES", ""):
                thread = threading.Thread(target=self._check_gleffects)
                thread.start()
            else:
                HIDDEN_EFFECTS.extend(self.gl_effects)

    def _check_gleffects(self):
        try:
            res = subprocess.check_output([sys.executable,
                os.path.join(os.path.dirname(__file__), "utils",
                "check_pipeline.py"),
                "videotestsrc ! glupload ! gleffects ! fakesink"])
            self.debug(res)
        except subprocess.CalledProcessError as e:
            self.error("Can not use GL effects: %s", e)
            HIDDEN_EFFECTS.extend(self.gl_effects)

    def getInfo(self, bin_description):
        """Gets the info for an effect which can be applied.

        Args:
            bin_description (str): The bin_description defining the effect.

        Returns:
            EffectInfo: The info corresponding to the name, or None.
        """
        name = EffectInfo.name_from_bin_description(bin_description)
        return self._effects.get(name)

    def _getEffectCategories(self, effect_name):
        """Gets the categories to which the specified effect belongs.

        Args:
            effect_name (str): The bin_description identifying the effect.

        Returns:
            List[str]: The categories which contain the effect.
        """
        categories = []
        for category_name, effects in EFFECTS_CATEGORIES:
            if effect_name in effects:
                categories.append(category_name)
        if not categories:
            categories.append(_("Uncategorized"))
        return categories

    @property
    def categories(self):
        """Gets the name of all effect categories."""
        return EffectsManager._getCategoriesNames(EFFECTS_CATEGORIES)

    @staticmethod
    def _getCategoriesNames(categories):
        ret = [category_name for category_name, unused_effects in categories]
        ret.sort()
        if categories:
            # Add Uncategorized only if there are other categories defined.
            ret.append(_("Uncategorized"))
        return ret


# ----------------------- UI classes to manage effects -------------------------#


class EffectListWidget(Gtk.Box, Loggable):
    """Widget for listing effects."""

    def __init__(self, instance):
        Gtk.Box.__init__(self)
        Loggable.__init__(self)

        self.app = instance

        self._drag_icon = GdkPixbuf.Pixbuf.new_from_file_at_size(
            os.path.join(get_pixmap_dir(), "effects", "defaultthumbnail.svg"),
            ICON_WIDTH, ICON_HEIGHT)
        self._star_icon_regular = GdkPixbuf.Pixbuf.new_from_file_at_size(
            os.path.join(get_pixmap_dir(), "star-regular.svg"), 15, 15)
        self._star_icon_solid = GdkPixbuf.Pixbuf.new_from_file_at_size(
            os.path.join(get_pixmap_dir(), "star-solid.svg"), 15, 15)

        self.set_orientation(Gtk.Orientation.VERTICAL)
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "effectslibrary.ui"))
        builder.connect_signals(self)
        toolbar = builder.get_object("effectslibrary_toolbar")
        toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_INLINE_TOOLBAR)
        self.search_entry = builder.get_object("search_entry")
        self.fav_view_toggle = builder.get_object("favourites_toggle")
        self.fav_view_toggle.set_image(Gtk.Image.new_from_pixbuf(self._star_icon_solid))

        self.main_view = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.category_view = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Used for showing search results and favourites
        self.search_view = Gtk.ListBox(activate_on_single_click=False)
        self.search_view.connect("row-activated", self.apply_selected_effect)

        placeholder_text = Gtk.Label(_("No effects"))
        placeholder_text.props.visible = True
        self.search_view.set_placeholder(placeholder_text)

        self.main_view.pack_start(self.category_view, True, True, 0)
        self.main_view.pack_start(self.search_view, True, True, 0)

        scrollwin = Gtk.ScrolledWindow()
        scrollwin.props.hscrollbar_policy = Gtk.PolicyType.NEVER
        scrollwin.props.vscrollbar_policy = Gtk.PolicyType.AUTOMATIC
        scrollwin.add(self.main_view)

        self.pack_start(toolbar, False, False, 0)
        self.pack_start(scrollwin, True, True, 0)

        # Delay the loading of the available effects so the application
        # starts faster.
        GLib.idle_add(self._load_available_effects_cb)

        scrollwin.show_all()
        toolbar.show_all()
        self.search_view.hide()

    def _load_available_effects_cb(self):
        self._set_up_category_view()
        self.add_effects_to_listbox(self.search_view)

    def _set_up_category_view(self):
        """Adds expanders and effects to the category view."""
        # Add category expanders
        for category in self.app.effects.categories:
            widget = self._create_category_widget(category)
            self.category_view.add(widget)

        # Add effects to category expanders
        for expander in self.category_view.get_children():
            listbox = expander.get_child()
            category_name = expander.get_label()

            self.add_effects_to_listbox(listbox, category_name)

        self.category_view.show_all()

    def add_effects_to_listbox(self, listbox, category=None, only_text=False):
        """Adds effect rows to the given listbox."""
        effects = self.app.effects.video_effects + self.app.effects.audio_effects
        for effect in effects:
            name = effect.get_name()

            if name in HIDDEN_EFFECTS:
                continue

            effect_info = self.app.effects.getInfo(name)

            if not category or category in effect_info.categories:
                widget = self._create_effect_widget(name, only_text)
                listbox.add(widget)

    def _create_category_widget(self, category):
        """Creates an expander for the given category."""
        expander = Gtk.Expander(label=category, margin=SPACING)

        listbox = Gtk.ListBox(activate_on_single_click=False)
        listbox.connect("row-activated", self.apply_selected_effect)

        expander.add(listbox)

        return expander

    def _create_effect_widget(self, effect_name, only_text):
        """Creates list box row for the given effect."""
        effect_info = self.app.effects.getInfo(effect_name)

        effect_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, margin=SPACING / 2)
        effect_box.effect_name = effect_name
        effect_box.set_tooltip_text(effect_info.description)
        label = Gtk.Label(effect_info.human_name, xalign=0)

        if not only_text:
            # Show effect thumbnail
            icon = Gtk.Image.new_from_pixbuf(effect_info.icon)
            effect_box.pack_start(icon, False, True, SPACING / 2)

            # Set up favourite button
            fav_button = Gtk.Button()
            fav_button.props.relief = Gtk.ReliefStyle.NONE
            fav_button.props.halign = Gtk.Align.CENTER
            fav_button.props.valign = Gtk.Align.CENTER
            fav_button.set_tooltip_text(_("Add to Favourites"))

            starred = effect_name in self.app.settings.favourite_effects
            self._set_fav_button_state(fav_button, starred)
            fav_button.connect("clicked", self._fav_button_cb, effect_box.effect_name)
            effect_box.pack_end(fav_button, False, True, SPACING / 2)

        effect_box.pack_start(label, True, True, 0)

        # Set up drag behavoir
        eventbox = Gtk.EventBox(visible_window=False)
        eventbox.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, [EFFECT_TARGET_ENTRY], Gdk.DragAction.COPY)
        eventbox.connect("drag-data-get", self._drag_data_get_cb)
        eventbox.connect("drag-begin", self._drag_begin_cb)
        eventbox.add(effect_box)

        row = Gtk.ListBoxRow(selectable=False)
        row.add(eventbox)

        return row

    def _drag_data_get_cb(self, eventbox, drag_context, selection_data, unused_info, unused_timestamp):
        effect_box = eventbox.get_child()
        data = bytes(effect_box.effect_name, "UTF-8")
        selection_data.set(drag_context.list_targets()[0], 0, data)

    def _drag_begin_cb(self, eventbox, context):
        # Draw drag-icon
        icon = self._drag_icon
        icon_height = icon.get_height()
        icon_width = icon.get_width()

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, icon_width, icon_height)
        ctx = cairo.Context(surface)
        # Center the icon around the cursor.
        ctx.translate(icon_width / 2, icon_height / 2)
        surface.set_device_offset(-icon_width / 2, -icon_height / 2)

        Gdk.cairo_set_source_pixbuf(ctx, icon, 0, 0)
        ctx.paint_with_alpha(0.35)

        Gtk.drag_set_icon_surface(context, surface)

    def apply_selected_effect(self, unused_listbox, row):
        """Adds the selected effect to the single selected clip, if any."""

        effect_box = row.get_child().get_child()
        effect_info = self.app.effects.getInfo(effect_box.effect_name)

        if not effect_info:
            return
        timeline = self.app.gui.editor.timeline_ui.timeline
        clip = timeline.selection.getSingleClip()
        if not clip:
            return
        pipeline = timeline.ges_timeline.get_parent()
        from pitivi.undo.timeline import CommitTimelineFinalizingAction
        with self.app.action_log.started("add effect",
                                         finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                         toplevel=True):
            clip.ui.add_effect(effect_info)

    def _set_fav_button_state(self, button, is_active):
        """Manages the state of the favourite button."""
        button.active = is_active

        if button.active:
            image = Gtk.Image.new_from_pixbuf(self._star_icon_solid)
        else:
            image = Gtk.Image.new_from_pixbuf(self._star_icon_regular)

        button.props.image = image

    def _fav_button_cb(self, clicked_button, effect):
        """Adds effect to favourites and syncs the state of favourite button."""
        # Toggle the state of clicked button
        self._set_fav_button_state(clicked_button, not clicked_button.active)

        # Get all listboxes which contain the effect
        effect_info = self.app.effects.getInfo(effect)
        all_effect_listboxes = [category_expander.get_child()
            for category_expander in self.category_view.get_children()
            if category_expander.get_label() in effect_info.categories]
        all_effect_listboxes.append(self.search_view)

        # Find and sync state in other listboxes
        for listbox in all_effect_listboxes:
            for row in listbox.get_children():
                effect_box = row.get_child().get_child()
                if effect == effect_box.effect_name:
                    fav_button = effect_box.get_children()[2]
                    # Sync the state with the clicked button
                    self._set_fav_button_state(fav_button, clicked_button.active)

        # Update the favourites list
        if clicked_button.active:
            self.app.settings.favourite_effects.append(effect)
        else:
            self.app.settings.favourite_effects = \
                [fav for fav in self.app.settings.favourite_effects if fav != effect]
        self.search_view.invalidate_filter()

    def _favourites_filter(self, row):
        """Filters search_view to show favourites."""
        effect_box = row.get_child().get_child()
        effect_name = effect_box.effect_name

        return effect_name in self.app.settings.favourite_effects

    def _favourites_toggle_cb(self, toggle):
        """Manages the visiblity and filtering of Favourites in search_view."""
        if toggle.get_active():
            self.search_entry.set_text("")
            self.search_view.set_filter_func(self._favourites_filter)
            self.search_view.invalidate_filter()
            self._switch_to_view(self.search_view)
        else:
            self._switch_to_view(self.category_view)

    def _search_filter(self, row):
        """Filters search_view to show search results."""
        effect_box = row.get_child().get_child()
        label = effect_box.get_children()[1]

        label_text = label.get_text().lower()
        search_key = self.search_entry.get_text().lower()

        return search_key in label_text

    def _search_entry_changed_cb(self, search_entry):
        """Manages the visiblity and filtering search results in search_view."""
        if search_entry.get_text():
            self.fav_view_toggle.props.active = False
            self.search_view.set_filter_func(self._search_filter)
            self.search_view.invalidate_filter()
            self._switch_to_view(self.search_view)
        else:
            self._switch_to_view(self.category_view)

    def _search_entry_icon_clicked_cb(self, entry, unused, unused1):
        entry.set_text("")

    def _switch_to_view(self, next_view):
        """Shows next_view and hides all other views."""
        if not next_view.props.visible:
            for child_view in self.main_view.get_children():
                if child_view == next_view:
                    next_view.show_all()
                else:
                    child_view.hide()


class EffectsPopover(Gtk.Popover, Loggable):
    """Popover for adding effects."""

    def __init__(self, app):
        Gtk.Popover.__init__(self)
        Loggable.__init__(self)

        self.app = app

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin=PADDING)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.connect("search-changed", self._search_entry_cb)

        scroll_window = Gtk.ScrolledWindow()
        scroll_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll_window.props.max_content_height = 350
        scroll_window.props.propagate_natural_height = True

        self.listbox = Gtk.ListBox()
        self.listbox.connect("row-activated", self._effect_row_activate_cb)
        self.listbox.set_filter_func(self._search_filter)
        placeholder_text = Gtk.Label(_("No effects"))
        placeholder_text.props.visible = True
        self.listbox.set_placeholder(placeholder_text)

        self.app.gui.editor.effectlist.add_effects_to_listbox(self.listbox, only_text=True)
        scroll_window.add(self.listbox)

        vbox.pack_start(self.search_entry, False, False, 0)
        vbox.pack_end(scroll_window, True, True, 0)
        vbox.show_all()

        self.add(vbox)

    def _effect_row_activate_cb(self, listbox, row):
        self.app.gui.editor.effectlist.apply_selected_effect(listbox, row)
        self.hide()

    def _search_entry_cb(self, search_entry):
        self.listbox.invalidate_filter()

    def _search_filter(self, row):
        effect_box = row.get_child().get_child()
        label = effect_box.get_children()[0]

        label_text = label.get_text().lower()
        search_key = self.search_entry.get_text().lower()

        return search_key in label_text

    def popup(self):
        self.search_entry.set_text("")
        Gtk.Popover.popup(self)

PROPS_TO_IGNORE = ['name', 'qos', 'silent', 'message', 'parent']


class EffectsPropertiesManager(GObject.Object, Loggable):
    """Provides UIs for editing effects.

    Attributes:
        app (Pitivi): The app.
    """

    def create_widget_accumulator(*args):
        """Aborts `create_widget` emission if we got a widget."""
        handler_return = args[2]
        if handler_return is None:
            return True, handler_return
        return False, handler_return

    __gsignals__ = {
        "create_widget": (GObject.SignalFlags.RUN_LAST, Gtk.Widget, (GstElementSettingsWidget, GES.Effect,),
                          create_widget_accumulator),
        "create_property_widget": (
            GObject.SignalFlags.RUN_LAST, object, (GstElementSettingsWidget, GES.Effect, object, object,),
            create_widget_accumulator),
    }

    def do_create_widget(self, effect_widget, effect):
        """Creates a widget if the `create_widget` handlers did not."""
        effect_name = effect.get_property("bin-description")
        self.log('UI is being auto-generated for "%s"', effect_name)
        effect_widget.add_widgets(create_property_widget=self.create_property_widget, with_reset_button=True)
        self._postConfiguration(effect, effect_widget)
        return None

    def do_create_property_widget(self, effect_widget, effect, prop, prop_value):
        """Creates a widget if the `create_property_widget` handlers did not."""
        widget = effect_widget.make_property_widget(prop, prop_value)
        return widget

    def __init__(self, app):
        GObject.Object.__init__(self)
        Loggable.__init__(self)
        self.app = app

    def getEffectConfigurationUI(self, effect):
        """Gets a configuration UI element for the effect.

        Args:
            effect (Gst.Element): The effect for which we want the UI.

        Returns:
            GstElementSettingsWidget: A container for configuring the effect.
        """
        effect_widget = GstElementSettingsWidget(effect, PROPS_TO_IGNORE)
        widget = self.emit("create_widget", effect_widget, effect)
        # The default handler of `create_widget` handles visibility
        # itself and returns None
        if widget is not None:
            effect_widget.show_widget(widget)
        self._connectAllWidgetCallbacks(effect_widget, effect)

        return effect_widget

    def _postConfiguration(self, effect, effect_set_ui):
        effect_name = effect.get_property("bin-description")
        if 'aspectratiocrop' in effect.get_property("bin-description"):
            for widget in effect_set_ui.get_children()[0].get_children():
                if isinstance(widget, FractionWidget):
                    widget.addPresets(["4:3", "5:4", "9:3", "16:9", "16:10"])
        else:
            self.log('No additional set-up required for "%s"', effect_name)
            return
        self.debug('Additional properties successfully set for "%s"', effect_name)

    def _connectAllWidgetCallbacks(self, effect_widget, effect):
        for prop, widget in effect_widget.properties.items():
            widget.connectValueChanged(self._on_widget_value_changed_cb, widget, prop, effect, effect_widget)

    def _on_widget_value_changed_cb(self, unused_widget, prop_widget, prop, effect, effect_widget):
        if effect_widget.updating_property:
            # The widget is updated as a side-effect of setting one of its
            # properties. Ignore.
            return

        effect_widget.updating_property = True
        try:
            value = prop_widget.getWidgetValue()

            # FIXME Workaround in order to make aspectratiocrop working
            if isinstance(value, Gst.Fraction):
                value = Gst.Fraction(int(value.num), int(value.denom))

            from pitivi.undo.timeline import CommitTimelineFinalizingAction
            pipeline = self.app.project_manager.current_project.pipeline
            with self.app.action_log.started("Effect property change",
                                             finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                             toplevel=True):
                effect.set_child_property(prop.name, value)
        finally:
            effect_widget.updating_property = False

    def create_property_widget(self, element_settings_widget, prop, prop_value):
        prop_widget = self.emit("create_property_widget", element_settings_widget, element_settings_widget.element,
                                prop, prop_value)
        return prop_widget
