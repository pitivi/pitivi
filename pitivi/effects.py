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
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GES
from gi.repository import GLib
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import Pango

from pitivi.configure import get_pixmap_dir
from pitivi.configure import get_ui_dir
from pitivi.settings import GlobalSettings
from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import EFFECT_TARGET_ENTRY
from pitivi.utils.ui import SPACING
from pitivi.utils.widgets import FractionWidget
from pitivi.utils.widgets import GstElementSettingsWidget


(VIDEO_EFFECT, AUDIO_EFFECT) = list(range(1, 3))

AUDIO_EFFECTS_CATEGORIES = ()

ALLOWED_ONLY_ONCE_EFFECTS = ['videoflip']

VIDEO_EFFECTS_CATEGORIES = (
    (_("Colors"), (
        # Mostly "serious" stuff that relates to correction/adjustments
        # Fancier stuff goes into the "fancy" category
        "cogcolorspace", "videobalance", "chromahold", "gamma",
        "coloreffects", "exclusion", "burn", "dodge", "videomedian",
        "frei0r-filter-color-distance", "frei0r-filter-threshold0r",
        "frei0r-filter-contrast0r", "frei0r-filter-saturat0r",
        "frei0r-filter-white-balance", "frei0r-filter-brightness",
        "frei0r-filter-gamma", "frei0r-filter-invert0r",
        "frei0r-filter-hueshift0r", "frei0r-filter-equaliz0r",
        "frei0r-filter-bw0r", "frei0r-filter-glow",
        "frei0r-filter-twolay0r", "frei0r-filter-3-point-color-balance",
        "frei0r-filter-coloradj-rgb", "frei0r-filter-curves",
        "frei0r-filter-levels", "frei0r-filter-primaries",
        "frei0r-filter-sop-sat", "frei0r-filter-threelay0r",
        "frei0r-filter-tint0r",
    )),
    (_("Compositing"), (
        "alpha", "alphacolor", "gdkpixbufoverlay",
        "frei0r-filter-transparency", "frei0r-filter-mask0mate",
        "frei0r-filter-alpha0ps", "frei0r-filter-alphagrad",
        "frei0r-filter-alphaspot", "frei0r-filter-bluescreen0r",
        "frei0r-filter-select0r",
    )),
    (_("Noise & blur"), (
        "gaussianblur", "diffuse", "dilate", "marble", "smooth",
        "frei0r-filter-hqdn3d", "frei0r-filter-squareblur",
        "frei0r-filter-sharpness", "frei0r-filter-edgeglow",
        "frei0r-filter-facebl0r",
    )),
    (_("Analysis"), (
        "videoanalyse", "videodetect", "videomark", "revtv",
        "navigationtest", "frei0r-filter-rgb-parade",
        "frei0r-filter-r", "frei0r-filter-g", "frei0r-filter-b",
        "frei0r-filter-vectorscope", "frei0r-filter-luminance",
        "frei0r-filter-opencvfacedetect", "frei0r-filter-pr0be",
        "frei0r-filter-pr0file",
    )),
    (_("Geometry"), (
        "cogscale", "aspectratiocrop", "cogdownsample", "videoscale",
        "videocrop", "videoflip", "videobox", "gdkpixbufscale",
        "kaleidoscope", "mirror", "pinch", "sphere", "square", "fisheye",
        "stretch", "twirl", "waterriple", "rotate", "bulge", "circle",
        "frei0r-filter-letterb0xed", "frei0r-filter-k-means-clustering",
        "frei0r-filter-lens-correction", "frei0r-filter-defish0r",
        "frei0r-filter-perspective", "frei0r-filter-c0rners",
        "frei0r-filter-scale0tilt", "frei0r-filter-pixeliz0r",
        "frei0r-filter-flippo", "frei0r-filter-3dflippo",
    )),
    (_("Fancy"), (
        "rippletv", "streaktv", "radioactv", "optv", "solarize",
        "quarktv", "vertigotv", "shagadelictv", "warptv", "dicetv",
        "agingtv", "edgetv", "bulge", "circle", "fisheye", "tunnel",
        "kaleidoscope", "mirror", "pinch", "sphere", "square",
        "stretch", "twirl", "waterripple", "glfiltersobel", "chromium",
        "frei0r-filter-sobel", "frei0r-filter-cartoon",
        "frei0r-filter-water", "frei0r-filter-nosync0r",
        "frei0r-filter-k-means-clustering", "frei0r-filter-delay0r",
        "frei0r-filter-distort0r", "frei0r-filter-light-graffiti",
        "frei0r-filter-tehroxx0r", "frei0r-filter-vertigo",
    )),
    (_("Time"), (
        "videorate", "frei0r-filter-delay0r", "frei0r-filter-baltan",
        "frei0r-filter-nervous",
    )),
)

BLACKLISTED_EFFECTS = ["colorconvert", "coglogoinsert", "festival",
                       "alphacolor", "cogcolorspace", "videodetect",
                       "navigationtest", "videoanalyse", "volume"]

BLACKLISTED_PLUGINS = []

HIDDEN_EFFECTS = [
    # Overlaying an image onto a video stream can already be done.
    "gdkpixbufoverlay"]

GlobalSettings.addConfigSection('effect-library')

(COL_NAME_TEXT,
 COL_DESC_TEXT,
 COL_EFFECT_TYPE,
 COL_EFFECT_CATEGORIES,
 COL_ELEMENT_NAME,
 COL_ICON) = list(range(6))

ICON_WIDTH = 48 + 2 * 6  # 48 pixels, plus a margin on each side


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
                ICON_WIDTH, ICON_WIDTH)
        # An empty except clause is bad, but "gi._glib.GError" is not helpful.
        except:
            icon = GdkPixbuf.Pixbuf.new_from_file(
                os.path.join(pixdir, "defaultthumbnail.svg"))
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


class EffectsManager(object):
    """Keeps info about effects and their categories.

    Attributes:
        video_effects (List[Gst.ElementFactory]): The available video effects.
        audio_effects (List[Gst.ElementFactory]): The available audio effects.
    """

    def __init__(self):
        object.__init__(self)
        self.video_effects = []
        self.audio_effects = []
        self._effects = {}

        useless_words = ["Video", "Audio", "audio", "effect",
                         _("Video"), _("Audio"), _("Audio").lower(), _("effect")]
        uselessRe = re.compile(" |".join(useless_words))

        factories = Gst.Registry.get().get_feature_list(Gst.ElementFactory)
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
        for category_name, effects in AUDIO_EFFECTS_CATEGORIES:
            if effect_name in effects:
                categories.append(category_name)
        for category_name, effects in VIDEO_EFFECTS_CATEGORIES:
            if effect_name in effects:
                categories.append(category_name)
        if not categories:
            categories.append(_("Uncategorized"))
        categories.insert(0, _("All effects"))
        return categories

    @property
    def video_categories(self):
        """Gets all video effect categories names."""
        return EffectsManager._getCategoriesNames(VIDEO_EFFECTS_CATEGORIES)

    @property
    def audio_categories(self):
        """Gets all audio effect categories names."""
        return EffectsManager._getCategoriesNames(AUDIO_EFFECTS_CATEGORIES)

    @staticmethod
    def _getCategoriesNames(categories):
        ret = [category_name for category_name, unused_effects in categories]
        ret.sort()
        ret.insert(0, _("All effects"))
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

        self._draggedItems = None
        self._effectType = VIDEO_EFFECT

        self.set_orientation(Gtk.Orientation.VERTICAL)
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "effectslibrary.ui"))
        builder.connect_signals(self)
        toolbar = builder.get_object("effectslibrary_toolbar")
        toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_INLINE_TOOLBAR)
        self.video_togglebutton = builder.get_object("video_togglebutton")
        self.audio_togglebutton = builder.get_object("audio_togglebutton")
        self.categoriesWidget = builder.get_object("categories")
        self.searchEntry = builder.get_object("search_entry")

        # Store
        self.storemodel = Gtk.ListStore(
            str, str, int, object, str, GdkPixbuf.Pixbuf)
        self.storemodel.set_sort_column_id(
            COL_NAME_TEXT, Gtk.SortType.ASCENDING)

        # Create the filter for searching the storemodel.
        self.model_filter = self.storemodel.filter_new()
        self.model_filter.set_visible_func(self._setRowVisible, data=None)

        self.view = Gtk.TreeView(model=self.model_filter)
        self.view.props.headers_visible = False
        self.view.get_selection().set_mode(Gtk.SelectionMode.SINGLE)

        icon_col = Gtk.TreeViewColumn()
        icon_col.set_spacing(SPACING)
        icon_col.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        icon_col.props.fixed_width = ICON_WIDTH
        icon_cell = Gtk.CellRendererPixbuf()
        icon_cell.props.xpad = 6
        icon_col.pack_start(icon_cell, True)
        icon_col.add_attribute(icon_cell, "pixbuf", COL_ICON)

        text_col = Gtk.TreeViewColumn()
        text_col.set_expand(True)
        text_col.set_spacing(SPACING)
        text_col.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        text_cell = Gtk.CellRendererText()
        text_cell.props.yalign = 0.0
        text_cell.props.xpad = 6
        text_cell.set_property("ellipsize", Pango.EllipsizeMode.END)
        text_col.pack_start(text_cell, True)
        text_col.set_cell_data_func(
            text_cell, self.viewDescriptionCellDataFunc, None)

        self.view.append_column(icon_col)
        self.view.append_column(text_col)

        self.view.connect("query-tooltip", self._treeViewQueryTooltipCb)
        self.view.props.has_tooltip = True

        # Make the treeview a drag source which provides effects.
        self.view.enable_model_drag_source(
            Gdk.ModifierType.BUTTON1_MASK, [EFFECT_TARGET_ENTRY], Gdk.DragAction.COPY)

        self.view.connect("button-press-event", self._buttonPressEventCb)
        self.view.connect("select-cursor-row", self._enterPressEventCb)
        self.view.connect("drag-data-get", self._dndDragDataGetCb)

        scrollwin = Gtk.ScrolledWindow()
        scrollwin.props.hscrollbar_policy = Gtk.PolicyType.NEVER
        scrollwin.props.vscrollbar_policy = Gtk.PolicyType.AUTOMATIC
        scrollwin.add(self.view)

        self.pack_start(toolbar, False, False, 0)
        self.pack_start(scrollwin, True, True, 0)

        # Delay the loading of the available effects so the application
        # starts faster.
        GLib.idle_add(self._loadAvailableEffectsCb)
        self.populate_categories_widget()

        # Individually show the tab's widgets.
        # If you use self.show_all(), the tab will steal focus on startup.
        scrollwin.show_all()
        toolbar.show_all()

    def _treeViewQueryTooltipCb(self, view, x, y, keyboard_mode, tooltip):
        is_row, x, y, model, path, tree_iter = view.get_tooltip_context(
            x, y, keyboard_mode)
        if not is_row:
            return False

        view.set_tooltip_row(tooltip, path)
        tooltip.set_markup(self.formatDescription(model, tree_iter))
        return True

    def viewDescriptionCellDataFunc(self, unused_column, cell, model, iter_, unused_data):
        cell.props.markup = self.formatDescription(model, iter_)

    def formatDescription(self, model, iter_):
        name, element_name, desc = model.get(iter_, COL_NAME_TEXT, COL_ELEMENT_NAME, COL_DESC_TEXT)
        escape = GLib.markup_escape_text
        return "<b>%s</b>\n%s" % (escape(name), escape(desc))

    def _loadAvailableEffectsCb(self):
        self._addFactories(self.app.effects.video_effects, VIDEO_EFFECT)
        self._addFactories(self.app.effects.audio_effects, AUDIO_EFFECT)
        return False

    def _addFactories(self, elements, effectType):
        for element in elements:
            name = element.get_name()
            if name in HIDDEN_EFFECTS:
                continue
            effect_info = self.app.effects.getInfo(name)
            self.storemodel.append([effect_info.human_name,
                                    effect_info.description,
                                    effectType,
                                    effect_info.categories,
                                    name,
                                    effect_info.icon])

    def populate_categories_widget(self):
        self.categoriesWidget.get_model().clear()
        icon_column = self.view.get_column(0)

        if self._effectType is VIDEO_EFFECT:
            for category in self.app.effects.video_categories:
                self.categoriesWidget.append_text(category)
            icon_column.props.visible = True
        else:
            for category in self.app.effects.audio_categories:
                self.categoriesWidget.append_text(category)
            icon_column.props.visible = False

        self.categoriesWidget.set_active(0)

    def _dndDragDataGetCb(self, unused_view, drag_context, selection_data, unused_info, unused_timestamp):
        data = bytes(self.getSelectedEffect(), "UTF-8")
        selection_data.set(drag_context.list_targets()[0], 0, data)

    def _rowUnderMouseSelected(self, view, event):
        result = view.get_path_at_pos(int(event.x), int(event.y))
        if result:
            path = result[0]
            selection = view.get_selection()
            return selection.path_is_selected(path) and\
                selection.count_selected_rows() > 0
        return False

    def _enterPressEventCb(self, unused_view, unused_event=None):
        self._addSelectedEffect()

    def _buttonPressEventCb(self, view, event):
        chain_up = True

        if event.button == 3:
            chain_up = False
        elif event.type == getattr(Gdk.EventType, '2BUTTON_PRESS'):
            self._addSelectedEffect()
        else:
            chain_up = not self._rowUnderMouseSelected(view, event)

        if chain_up:
            self._draggedItems = None
        else:
            self._draggedItems = self.getSelectedEffect()

        Gtk.TreeView.do_button_press_event(view, event)
        return True

    def _addSelectedEffect(self):
        """Adds the selected effect to the single selected clip, if any."""
        effect = self.getSelectedEffect()
        effect_info = self.app.effects.getInfo(effect)
        if not effect_info:
            return
        timeline = self.app.gui.timeline_ui.timeline
        clip = timeline.selection.getSingleClip()
        if not clip:
            return
        pipeline = timeline.ges_timeline.get_parent()
        from pitivi.undo.timeline import CommitTimelineFinalizingAction
        with self.app.action_log.started("add effect",
                                         finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                         toplevel=True):
            clip.ui.add_effect(effect_info)

    def getSelectedEffect(self):
        if self._draggedItems:
            return self._draggedItems
        model, rows = self.view.get_selection().get_selected_rows()
        path = self.model_filter.convert_path_to_child_path(rows[0])
        return self.storemodel[path][COL_ELEMENT_NAME]

    def _toggleViewTypeCb(self, widget):
        """Switches the view mode between video and audio.

        This makes the two togglebuttons behave like a group of radiobuttons.
        """
        if widget is self.video_togglebutton:
            self.audio_togglebutton.set_active(not widget.get_active())
        else:
            assert widget is self.audio_togglebutton
            self.video_togglebutton.set_active(not widget.get_active())

        if self.video_togglebutton.get_active():
            self._effectType = VIDEO_EFFECT
        else:
            self._effectType = AUDIO_EFFECT
        self.populate_categories_widget()
        self.model_filter.refilter()

    def _categoryChangedCb(self, unused_combobox):
        self.model_filter.refilter()

    def _searchEntryChangedCb(self, unused_entry):
        self.model_filter.refilter()

    def _searchEntryIconClickedCb(self, entry, unused, unused1):
        entry.set_text("")

    def _setRowVisible(self, model, iter, unused_data):
        if not self._effectType == model.get_value(iter, COL_EFFECT_TYPE):
            return False
        if model.get_value(iter, COL_EFFECT_CATEGORIES) is None:
            return False
        if self.categoriesWidget.get_active_text() not in model.get_value(iter, COL_EFFECT_CATEGORIES):
            return False
        text = self.searchEntry.get_text().lower()
        return text in model.get_value(iter, COL_DESC_TEXT).lower() or\
            text in model.get_value(iter, COL_NAME_TEXT).lower()


PROPS_TO_IGNORE = ['name', 'qos', 'silent', 'message', 'parent']


class EffectsPropertiesManager:
    """Provides and caches UIs for editing effects.

    Attributes:
        app (Pitivi): The app.
    """

    def __init__(self, app):
        self.cache_dict = {}
        self._current_element_values = {}
        self.app = app

    def getEffectConfigurationUI(self, effect):
        """Gets a configuration UI element for the effect.

        Args:
            effect (Gst.Element): The effect for which we want the UI.

        Returns:
            GstElementSettingsWidget: A container for configuring the effect.
        """
        if effect not in self.cache_dict:
            # Here we should handle special effects configuration UI
            effect_widget = GstElementSettingsWidget()
            effect_widget.setElement(effect, ignore=PROPS_TO_IGNORE,
                                     with_reset_button=True)
            self.cache_dict[effect] = effect_widget
            self._connectAllWidgetCallbacks(effect_widget, effect)
            self._postConfiguration(effect, effect_widget)

        for prop in effect.list_children_properties():
            value = effect.get_child_property(prop.name)
            self._current_element_values[prop.name] = value

        return self.cache_dict[effect]

    def cleanCache(self, effect):
        if effect in self.cache_dict:
            return self.cache_dict.pop(effect)

    def _postConfiguration(self, effect, effect_set_ui):
        if 'aspectratiocrop' in effect.get_property("bin-description"):
            for widget in effect_set_ui.get_children()[0].get_children():
                if isinstance(widget, FractionWidget):
                    widget.addPresets(["4:3", "5:4", "9:3", "16:9", "16:10"])

    def _connectAllWidgetCallbacks(self, effect_settings_widget, effect):
        for prop, widget in effect_settings_widget.properties.items():
            widget.connectValueChanged(self._onValueChangedCb, widget, prop, effect)

    def _onSetDefaultCb(self, unused_widget, effect_widget):
        effect_widget.setWidgetToDefault()

    def _onValueChangedCb(self, unused_widget, effect_widget, prop, effect):
        value = effect_widget.getWidgetValue()

        # FIXME Workaround in order to make aspectratiocrop working
        if isinstance(value, Gst.Fraction):
            value = Gst.Fraction(int(value.num), int(value.denom))

        if value != self._current_element_values.get(prop.name):
            from pitivi.undo.timeline import CommitTimelineFinalizingAction

            pipeline = self.app.project_manager.current_project.pipeline
            with self.app.action_log.started("Effect property change",
                                             finalizing_action=CommitTimelineFinalizingAction(pipeline),
                                             toplevel=True):
                effect.set_child_property(prop.name, value)
            self._current_element_values[prop.name] = value
