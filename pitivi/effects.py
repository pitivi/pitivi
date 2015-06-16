# Pitivi video editor
#
#       pitivi/effects.py
#
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

"""
Effects global handling
 Note: Some effects are available through the frei0r
 library and the libavfilter0 library

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

from gi.repository import GLib
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Pango
from gi.repository import GdkPixbuf

from gettext import gettext as _

from pitivi.configure import get_ui_dir, get_pixmap_dir
from pitivi.settings import GlobalSettings

from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import EFFECT_TARGET_ENTRY, SPACING

from pitivi.utils.widgets import GstElementSettingsWidget, FractionWidget


(VIDEO_EFFECT, AUDIO_EFFECT) = list(range(1, 3))

AUDIO_EFFECTS_CATEGORIES = ()

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
                       "navigationtest", "videoanalyse"]

# FIXME Check if this is still true with GES
# We should unblacklist it when #650985 is solved
BLACKLISTED_PLUGINS = ["ldaspa"]

ICON_WIDTH = 48 + 2 * 6  # 48 pixels, plus a margin on each side


class EffectFactory(object):
    """
    Factories that applies an effect on a stream
    """
    def __init__(self, effect_name, media_type, categories,
                 human_name, description):
        object.__init__(self)
        self.effect_name = effect_name
        self.media_type = media_type
        self.categories = categories
        self.description = description
        self.human_name = human_name


class EffectsManager(object):

    """
    Groups effects.
    """

    def __init__(self):
        object.__init__(self)
        self._pixdir = os.path.join(get_pixmap_dir(), "effects")
        self.video_effects = []
        self.audio_effects = []
        self._effect_factories_dict = {}
        self._setAllEffects()

    def _setAllEffects(self):
        """
        go trough the list of element factories and
        add them to the correct list filtering if necessary
        """
        factories = Gst.Registry.get().get_feature_list(Gst.ElementFactory)
        for element_factory in factories:
            klass = element_factory.get_klass()
            name = element_factory.get_name()

            if ("Effect" in klass and name not in BLACKLISTED_EFFECTS and not
                    [bplug for bplug in BLACKLISTED_PLUGINS if bplug in name]):
                media_type = None

                if "Audio" in klass:
                    self.audio_effects.append(element_factory)
                    media_type = AUDIO_EFFECT
                elif "Video" in klass:
                    self.video_effects.append(element_factory)
                    media_type = VIDEO_EFFECT

                if not media_type:
                    HIDDEN_EFFECTS.append(name)
                    continue

                effect = EffectFactory(name,
                                       media_type,
                                       categories=self._getEffectCategories(
                                           name),
                                       human_name=self._getEffectName(
                                           element_factory),
                                       description=self._getEffectDescripton(element_factory))
                self._addEffectToDic(name, effect)

    def getAllAudioEffects(self):
        """
        @return: the list of available audio effects elements
        """
        return self.audio_effects

    def getAllVideoEffects(self):
        """
        @return: the list of available video effects elements
        """
        return self.video_effects

    def _addEffectToDic(self, name, factory):
        self._effect_factories_dict[name] = factory

    def getFactoryFromName(self, name):
        """
        @param name: The bin_description of the effect.
        @type name: C{str}
        @return: The l{EffectFactory} corresponding to the name or None
        """
        return self._effect_factories_dict.get(name)

    def _getEffectDescripton(self, element_factory):
        """
        @param element_factory: The element factory
        @type element_factory: L{Gst.ElementFactory}
        @return: A human description C{str} for the effect
        """
        return element_factory.get_description()

    def _getEffectCategories(self, effect_name):
        """
        @param effect_name: the name of the effect for wich we want the category
        @type effect_name: L{str}
        @return: A C{list} of name C{str} of categories corresponding the effect
        """
        categories = []
        for category_name, effects in AUDIO_EFFECTS_CATEGORIES:
            if effect_name in effects:
                categories.append(category_name)
        for category_name, effects in VIDEO_EFFECTS_CATEGORIES:
            if effect_name in effects:
                categories.append(category_name)
        if not categories:
            uncategorized = _("Uncategorized")
            categories.append(uncategorized)
        categories.insert(0, _("All effects"))
        return categories

    def _getEffectName(self, element_factory):
        """
        @param element_factory: The element factory
        @type element_factory: L{Gst.ElementFactory}
        @return: A human readable name C{str} for the effect
        """
        video = _("Video")
        audio = _("Audio")
        effect = _("effect")
        uselessWords = re.compile(" |".join([video, audio, audio.lower(), effect]))
        return uselessWords.sub("", element_factory.get_longname()).title()

    def getVideoCategories(self):
        """
        Get all video effect categories names.
        """
        return EffectsManager._getCategoriesNames(VIDEO_EFFECTS_CATEGORIES)

    video_categories = property(getVideoCategories)

    def getAudioCategories(self):
        """
        Get all audio effect categories names.
        """
        return EffectsManager._getCategoriesNames(AUDIO_EFFECTS_CATEGORIES)

    audio_categories = property(getAudioCategories)

    @staticmethod
    def _getCategoriesNames(categories):
        ret = [category_name for category_name, unused_effects in categories]
        ret.sort()
        ret.insert(0, _("All effects"))
        if categories:
            # Add Uncategorized only if there are other categories defined.
            ret.append(_("Uncategorized"))
        return ret

    def getEffectIcon(self, effect_name):
        icon = None
        try:
            # We can afford to scale the images here, the impact is negligible
            icon = GdkPixbuf.Pixbuf.new_from_file_at_size(
                os.path.join(self._pixdir, effect_name + ".png"),
                ICON_WIDTH, ICON_WIDTH)
        # An empty except clause is bad, but "gi._glib.GError" is not helpful.
        except:
            icon = GdkPixbuf.Pixbuf.new_from_file(
                os.path.join(self._pixdir, "defaultthumbnail.svg"))
        return icon


# ----------------------- UI classes to manage effects -------------------------#
HIDDEN_EFFECTS = ["frei0r-filter-scale0tilt"]

GlobalSettings.addConfigSection('effect-library')

(COL_NAME_TEXT,
 COL_DESC_TEXT,
 COL_EFFECT_TYPE,
 COL_EFFECT_CATEGORIES,
 COL_FACTORY,
 COL_ELEMENT_NAME,
 COL_ICON) = list(range(7))


class EffectListWidget(Gtk.Box, Loggable):

    """ Widget for listing effects """

    def __init__(self, instance, unused_uiman):
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
            str, str, int, object, object, str, GdkPixbuf.Pixbuf)

        self.view = Gtk.TreeView(model=self.storemodel)
        self.view.props.headers_visible = False
        self.view.get_selection().set_mode(Gtk.SelectionMode.SINGLE)

        # Create the filterModel for searching the storemodel
        self.modelFilter = self.storemodel.filter_new()
        self.modelFilter.set_visible_func(self._setRowVisible, data=None)
        self.view.set_model(self.modelFilter)

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
            text_cell, self.view_description_cell_data_func, None)

        self.view.append_column(icon_col)
        self.view.append_column(text_col)

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

    @staticmethod
    def view_description_cell_data_func(unused_column, cell, model, iter_, unused_data):
        name, desc = model.get(iter_, COL_NAME_TEXT, COL_DESC_TEXT)
        escape = GLib.markup_escape_text
        cell.props.markup = "<b>%s</b>\n%s" % (escape(name),
                                               escape(desc),)

    def _loadAvailableEffectsCb(self):
        self._addFactories(self.app.effects.getAllVideoEffects(), VIDEO_EFFECT)
        self._addFactories(self.app.effects.getAllAudioEffects(), AUDIO_EFFECT)
        return False

    def _addFactories(self, elements, effectType):
        for element in elements:
            name = element.get_name()
            if name not in HIDDEN_EFFECTS:
                effect_factory = self.app.effects.getFactoryFromName(name)
                self.storemodel.append([effect_factory.human_name,
                                        effect_factory.description,
                                        effectType,
                                        effect_factory.categories,
                                        effect_factory,
                                        name,
                                        self.app.effects.getEffectIcon(name)])
        self.storemodel.set_sort_column_id(
            COL_NAME_TEXT, Gtk.SortType.ASCENDING)

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
        factory_name = bytes(self.getSelectedEffectFactoryName(), "UTF-8")
        selection_data.set(drag_context.list_targets()[0], 0, factory_name)
        return True

    def _rowUnderMouseSelected(self, view, event):
        result = view.get_path_at_pos(int(event.x), int(event.y))
        if result:
            path = result[0]
            selection = view.get_selection()
            return selection.path_is_selected(path) and\
                selection.count_selected_rows() > 0
        return False

    def _enterPressEventCb(self, unused_view, unused_event=None):
        factory_name = self.getSelectedEffectFactoryName()
        if factory_name is not None:
            self.app.gui.clipconfig.effect_expander.addEffectToCurrentSelection(
                factory_name)

    def _buttonPressEventCb(self, view, event):
        chain_up = True

        if event.button == 3:
            chain_up = False
        elif event.type == getattr(Gdk.EventType, '2BUTTON_PRESS'):
            factory_name = self.getSelectedEffectFactoryName()
            if factory_name is not None:
                self.app.gui.clipconfig.effect_expander.addEffectToCurrentSelection(
                    factory_name)
        else:
            chain_up = not self._rowUnderMouseSelected(view, event)

        if chain_up:
            self._draggedItems = None
        else:
            self._draggedItems = self.getSelectedEffectFactoryName()

        Gtk.TreeView.do_button_press_event(view, event)
        return True

    def getSelectedEffectFactoryName(self):
        if self._draggedItems:
            return self._draggedItems
        model, rows = self.view.get_selection().get_selected_rows()
        path = self.modelFilter.convert_path_to_child_path(rows[0])
        return self.storemodel[path][COL_ELEMENT_NAME]

    def _toggleViewTypeCb(self, widget):
        """
        Handle the switching of the view mode between video and audio.
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
        self.modelFilter.refilter()

    def _categoryChangedCb(self, unused_combobox):
        self.modelFilter.refilter()

    def _searchEntryChangedCb(self, unused_entry):
        self.modelFilter.refilter()

    def _searchEntryIconClickedCb(self, entry, unused, unused1):
        entry.set_text("")

    def _setRowVisible(self, model, iter, unused_data):
        if self._effectType == model.get_value(iter, COL_EFFECT_TYPE):
            if model.get_value(iter, COL_EFFECT_CATEGORIES) is None:
                return False
            if self.categoriesWidget.get_active_text() in model.get_value(iter, COL_EFFECT_CATEGORIES):
                text = self.searchEntry.get_text().lower()
                return text in model.get_value(iter, COL_DESC_TEXT).lower() or\
                    text in model.get_value(iter, COL_NAME_TEXT).lower()
            else:
                return False
        else:
            return False


PROPS_TO_IGNORE = ['name', 'qos', 'silent', 'message']


class EffectsPropertiesManager:

    """
    @type app: L{Pitivi}
    """

    def __init__(self, app):
        self.cache_dict = {}
        self._current_effect_setting_ui = None
        self._current_element_values = {}
        self.action_log = app.action_log
        self.app = app

    def getEffectConfigurationUI(self, effect):
        """Permit to get a configuration GUI for the effect

        @param effect: The effect for which we want the configuration UI
        @type effect: C{Gst.Element}
        """
        if effect not in self.cache_dict:
            # Here we should handle special effects configuration UI
            effect_settings_widget = GstElementSettingsWidget()
            effect_settings_widget.setElement(effect, ignore=PROPS_TO_IGNORE,
                                              default_btn=True, use_element_props=True)
            scrolled_window = Gtk.ScrolledWindow()
            scrolled_window.add_with_viewport(effect_settings_widget)
            scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                       Gtk.PolicyType.AUTOMATIC)
            self.cache_dict[effect] = scrolled_window
            self._connectAllWidgetCallbacks(effect_settings_widget, effect)
            self._postConfiguration(effect, effect_settings_widget)

        self._current_effect_setting_ui = self._getUiToSetEffect(effect)
        element = self._current_effect_setting_ui.element
        for prop in element.list_children_properties():
            self._current_element_values[
                prop.name] = element.get_child_property(prop.name)

        return self.cache_dict[effect]

    def cleanCache(self, effect):
        if effect in self.cache_dict:
            conf_ui = self.cache_dict.get(effect)
            self.cache_dict.pop(effect)
            return conf_ui

    def _postConfiguration(self, effect, effect_set_ui):
        if 'aspectratiocrop' in effect.get_property("bin-description"):
            for widget in effect_set_ui.get_children()[0].get_children():
                if isinstance(widget, FractionWidget):
                    widget.addPresets(["4:3", "5:4", "9:3", "16:9", "16:10"])

    def _getUiToSetEffect(self, effect):
        """ Permit to get the widget to set the effect and not its container """
        if type(self.cache_dict[effect]) is Gtk.ScrolledWindow:
            effect_set_ui = self.cache_dict[
                effect].get_children()[0].get_children()[0]
        else:
            effect_set_ui = self.cache_dict[effect]
        return effect_set_ui

    def _connectAllWidgetCallbacks(self, effect_settings_widget, unused_effect):
        for prop, widget in effect_settings_widget.properties.items():
            widget.connectValueChanged(self._onValueChangedCb, widget, prop)

    def _onSetDefaultCb(self, unused_widget, dynamic):
        dynamic.setWidgetToDefault()

    def _onValueChangedCb(self, unused_widget, dynamic, prop):
        value = dynamic.getWidgetValue()

        # FIXME Workaround in order to make aspectratiocrop working
        if isinstance(value, Gst.Fraction):
            value = Gst.Fraction(int(value.num), int(value.denom))

        if value != self._current_element_values.get(prop.name):
            self.action_log.begin("Effect property change")
            self._current_effect_setting_ui.element.set_child_property(
                prop.name, value)
            self.action_log.commit()

            self.app.project_manager.current_project.pipeline.flushSeek()
            self._current_element_values[prop.name] = value
