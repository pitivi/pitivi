# -*- coding: utf-8 -*-
# Pitivi video editor
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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
"""User preferences."""
import os
from gettext import gettext as _
from threading import Timer
from typing import Optional

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from pitivi.configure import get_ui_dir
from pitivi.configure import get_user_plugins_dir
from pitivi.pluginmanager import PluginManager
from pitivi.settings import GlobalSettings
from pitivi.utils import widgets
from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import alter_style_class
from pitivi.utils.ui import fix_infobar
from pitivi.utils.ui import PADDING
from pitivi.utils.ui import PREFERENCES_CSS
from pitivi.utils.ui import SPACING


GlobalSettings.add_config_section("user-interface")

GlobalSettings.add_config_option('prefsDialogWidth',
                                 section="user-interface",
                                 key="prefs-dialog-width",
                                 default=600)

GlobalSettings.add_config_option('prefsDialogHeight',
                                 section="user-interface",
                                 key="prefs-dialog-height",
                                 default=400)


class PreferencesDialog(Loggable):
    """Preferences for how the app works."""

    _instance = None
    prefs = {}
    section_names = {
        "timeline": _("Timeline"),
        "__plugins": _("Plugins"),
        "__shortcuts": _("Shortcuts"),
        "_proxies": _("Proxies"),
        "other": _("Other"),
    }

    def __init__(self, app):
        Loggable.__init__(self)

        self.app = app

        self.app.shortcuts.connect("accel-changed", self.__accel_changed_cb)

        self.settings = app.settings
        self.widgets = {}
        self.resets = {}
        self.original_values = {}
        self.action_ids = {}

        # Identify the widgets we'll need
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "preferences.ui"))
        builder.connect_signals(self)
        self.dialog = builder.get_object("dialog1")
        self.sidebar = builder.get_object("sidebar")
        self.stack = builder.get_object("stack")
        self.revert_button = builder.get_object("revertButton")
        self.factory_settings = builder.get_object("resetButton")
        self.restart_warning = builder.get_object("restartWarning")

        self.factory_settings.set_sensitive(self._can_reset())

        self.add_settings_page('timeline')
        self.__add_proxies_section()
        self.__add_shortcuts_section()
        self.__add_plugin_manager_section()
        self.add_settings_page('other')
        self.__setup_css()
        self.dialog.set_transient_for(app.gui)

    def run(self):
        """Runs the dialog."""
        PreferencesDialog._instance = self
        self.dialog.run()
        PreferencesDialog._instance = None

    def __setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(PREFERENCES_CSS.encode('UTF-8'))
        screen = Gdk.Screen.get_default()
        style_context = self.app.gui.get_style_context()
        style_context.add_provider_for_screen(screen, css_provider,
                                              Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

# Public API

    @classmethod
    def add_section(cls, section, title):
        """Adds a new valid section.

        Args:
            section (str): The id of a preferences category.
            title (str): The title of the new `section`.
        """
        cls.section_names[section] = title

    @classmethod
    def remove_section(cls, section):
        if cls._instance is not None:
            cls._instance.remove_page(section)
        try:
            del cls.section_names[section]
            del cls.prefs[section]
        except KeyError:
            pass

    @classmethod
    def _add_preference(cls, attrname, label, description, section,
                        widget_class, **args):
        """Adds a user preference.

        Args:
            attrname (str): The id of the setting holding the preference.
            label (str): The user-visible name for this option.
            description (str): The user-visible description explaining this
                option. Ignored unless `label` is non-None.
            section (str): The id of a preferences category.
                See `PreferencesDialog.section_names` for valid ids.
            widget_class (type): The class of the widget for displaying the
                option.
        """
        if section not in cls.section_names:
            raise Exception("%s is not a valid section id" % section)
        if section.startswith("__"):
            raise Exception("Cannot add preferences to reserved sections")
        if section not in cls.prefs:
            cls.prefs[section] = {}
        cls.prefs[section][attrname] = (label, description, widget_class, args)
        if cls._instance is not None:
            cls._instance.remove_page(section)
            cls._instance.add_settings_page(section)

    @classmethod
    def add_path_preference(cls, attrname, label, description, section=None):
        """Adds a user preference for a file path."""
        cls._add_preference(attrname, label, description, section,
                            widgets.PathWidget)

    @classmethod
    def add_numeric_preference(cls, attrname, label, description, section=None,
                               upper=None, lower=None):
        """Adds a user preference for a number.

        Show up as either a Gtk.SpinButton or a horizontal Gtk.Scale, depending
        whether both the upper and lower limits are set.
        """
        cls._add_preference(attrname, label, description, section,
                            widgets.NumericWidget, upper=upper, lower=lower)

    @classmethod
    def add_text_preference(cls, attrname, label, description, section=None, matches=None):
        """Adds a user preference for text."""
        cls._add_preference(attrname, label, description, section,
                            widgets.TextWidget, matches=matches)

    @classmethod
    def add_choice_preference(cls, attrname, label, description, choices, section=None):
        """Adds a user preference for text options."""
        cls._add_preference(attrname, label, description, section,
                            widgets.ChoiceWidget, choices=choices)

    @classmethod
    def add_toggle_preference(cls, attrname, label, description, section=None):
        """Adds a user preference for an on/off option."""
        cls._add_preference(attrname, label, description, section,
                            widgets.ToggleWidget)

    @classmethod
    def add_color_preference(cls, attrname, label, description, section=None):
        """Adds a user preference for a color."""
        cls._add_preference(attrname, label, description, section,
                            widgets.ColorWidget)

    @classmethod
    def add_font_preference(cls, attrname, label, description, section=None):
        """Adds a user preference for a font."""
        cls._add_preference(attrname, label, description, section,
                            widgets.FontWidget)

    def _add_page(self, section, widget):
        """Adds a widget to the internal stack."""
        if section not in self.section_names:
            raise Exception("%s is not a valid section id" % section)
        self.stack.add_titled(widget, section, self.section_names[section])

    def remove_page(self, section):
        if section in self.section_names:
            widget = self.stack.get_child_by_name(section)
            if widget is not None:
                self.stack.remove(widget)
                widget.destroy()
        else:
            self.log("No widget associated to section '%s' found", section)

    def add_settings_page(self, section_id):
        """Adds a page for the preferences in the specified section."""
        prefs = self._prepare_prefs_widgets(self.prefs[section_id])
        container = self._create_props_container(prefs)
        self._add_page(section_id, container)

    def _create_props_container(self, prefs):
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        container.set_border_width(SPACING)

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.props.margin = PADDING * 2
        listbox.get_style_context().add_class('prefs_list')

        container.pack_start(listbox, False, False, 0)

        label_size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        prop_size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)

        for y, (label, widget, revert_widget, extra_widget) in enumerate(prefs):
            box = Gtk.Box()

            label_widget = Gtk.Label(label=label)
            label_widget.set_alignment(0.0, 0.5)
            label_widget.props.margin_end = PADDING * 3
            label_widget.props.margin_top = PADDING * 2
            label_widget.props.margin_bottom = PADDING * 2
            label_size_group.add_widget(label_widget)

            widget.props.margin_end = PADDING * 3
            widget.props.margin_top = PADDING * 2
            widget.props.margin_bottom = PADDING * 2
            prop_size_group.add_widget(widget)

            box.pack_start(label_widget, True, True, 0)
            box.pack_start(widget, False, False, 0)
            if revert_widget:
                box.pack_start(revert_widget, False, False, 0)

            if extra_widget:
                box1 = box
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                box.pack_start(box1, False, False, 0)
                box.pack_start(extra_widget, False, False, SPACING)

            box.props.margin_start = PADDING * 3

            row = Gtk.ListBoxRow()
            row.set_activatable(False)
            row.add(box)
            if y == 0:
                row.get_style_context().add_class('first')
            listbox.add(row)

        container.show_all()
        return container

    def _create_revert_button(self):
        revert = Gtk.Button.new_from_icon_name("edit-clear-all-symbolic", Gtk.IconSize.MENU)
        revert.set_tooltip_text(_("Reset to default value"))
        revert.set_relief(Gtk.ReliefStyle.NONE)
        revert.props.valign = Gtk.Align.CENTER
        return revert

    def _prepare_prefs_widgets(self, options):
        prefs = []
        for attrname in options:
            label, description, widget_class, args = options[attrname]
            widget = widget_class(**args)
            widget.set_widget_value(getattr(self.settings, attrname))
            widget.connect_value_changed(self._value_changed_cb, widget, attrname)
            widget.set_tooltip_text(description)
            self.widgets[attrname] = widget

            revert = self._create_revert_button()
            revert.set_sensitive(not self.settings.is_default(attrname))
            revert.connect("clicked", self.__reset_option_cb, attrname)
            self.resets[attrname] = revert

            # Construct the prefs list so that it can be sorted.
            prefs.append((label, widget, revert, None))

        # TODO: We need to know exactly where each preference appears,
        #   currently they are sorted by the translated label.
        return sorted(prefs)

    def __add_plugin_manager_section(self):
        page = PluginPreferencesPage(self.app, self)
        page.show_all()
        self._add_page("__plugins", page)

    def __add_proxies_section(self):
        """Adds a section for proxy settings."""
        prefs = self._prepare_prefs_widgets(self.prefs["_proxies"])

        self.proxy_width_widget = widgets.NumericWidget(lower=1, width_chars=4)
        self.proxy_width_widget.set_widget_value(self.app.settings.default_scaled_proxy_width)
        self.widgets["default_scaled_proxy_width"] = self.proxy_width_widget
        self.proxy_height_widget = widgets.NumericWidget(lower=1, width_chars=4)
        self.proxy_height_widget.set_widget_value(self.app.settings.default_scaled_proxy_height)
        self.widgets["default_scaled_proxy_height"] = self.proxy_height_widget
        size_box = Gtk.Box(spacing=SPACING)
        size_box.pack_start(self.proxy_width_widget, False, False, 0)
        size_box.pack_start(Gtk.Label("×"), False, False, 0)
        size_box.pack_start(self.proxy_height_widget, False, False, 0)
        size_box.set_tooltip_text(_("This resolution will be used as the"
                                    " default target resolution for new projects and projects missing"
                                    " scaled proxy meta-data."))
        self.scaled_proxy_size_revert_button = self._create_revert_button()

        self.proxy_infobar = Gtk.InfoBar.new()
        fix_infobar(self.proxy_infobar)
        self.proxy_infobar.set_message_type(Gtk.MessageType.WARNING)
        self.proxy_infobar.add_button(_("Project Settings"), Gtk.ResponseType.OK)
        self.scaled_proxies_infobar_label = Gtk.Label.new()
        self.proxy_infobar.get_content_area().add(self.scaled_proxies_infobar_label)
        self.proxy_infobar.show_all()

        prefs.append((_("Initial proxy size for new projects"), size_box, self.scaled_proxy_size_revert_button, None))

        container = self._create_props_container(prefs)

        container.pack_start(self.proxy_infobar, False, False, 0)

        self._add_page("_proxies", container)

        self.__update_scaled_proxies_infobar()
        self.__update_proxy_size_revert_button()

        self.proxy_width_widget.connect_value_changed(self.__scaled_proxy_size_change_cb)
        self.proxy_height_widget.connect_value_changed(self.__scaled_proxy_size_change_cb)
        self.scaled_proxy_size_revert_button.connect("clicked", self.__reset_option_cb, "default_scaled_proxy_width", "default_scaled_proxy_height")
        self.proxy_infobar.connect("response", self.__proxy_infobar_cb)

    def __scaled_proxy_size_change_cb(self, unused_widget):
        self.app.settings.default_scaled_proxy_width = self.proxy_width_widget.get_widget_value()
        self.app.settings.default_scaled_proxy_height = self.proxy_height_widget.get_widget_value()
        self.__update_scaled_proxies_infobar()
        self.__update_proxy_size_revert_button()

    def __update_proxy_size_revert_button(self):
        default = all(self.settings.is_default(setting)
                      for setting in ("default_scaled_proxy_width", "default_scaled_proxy_height"))
        self.scaled_proxy_size_revert_button.set_sensitive(not default)

    def __update_scaled_proxies_infobar(self):
        project = self.app.project_manager.current_project
        different = project and \
            (project.scaled_proxy_width != self.app.settings.default_scaled_proxy_width or
             project.scaled_proxy_height != self.app.settings.default_scaled_proxy_height)
        self.proxy_infobar.set_visible(different)
        if different:
            self.scaled_proxies_infobar_label.set_text(
                _("Proxy resolution for the current project is %d×%d px") %
                (project.scaled_proxy_width, project.scaled_proxy_height))

    def __proxy_infobar_cb(self, unused_infobar, unused_response_id):
        self.app.gui.editor.show_project_settings_dialog()
        self.__update_scaled_proxies_infobar()

    def __add_shortcuts_section(self):
        """Adds a section with keyboard shortcuts."""
        shortcuts_manager = self.app.shortcuts
        self.description_size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        self.accel_size_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        self.content_box = Gtk.ListBox()
        self.list_store = Gio.ListStore.new(ModelItem)
        index = 0
        for group in shortcuts_manager.groups:
            actions = shortcuts_manager.group_actions[group]
            for action, title, _unused in actions:
                item = ModelItem(self.app, action, title, group)
                self.list_store.append(item)
                self.action_ids[action] = index
                index += 1

        self.content_box.bind_model(self.list_store, self._create_widget_func, None)
        self.content_box.set_header_func(self._add_header_func, None)
        self.content_box.connect("row-activated", self.__row_activated_cb)
        self.content_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.content_box.props.margin = PADDING * 3
        self.content_box.props.halign = Gtk.Align.CENTER
        self.content_box.get_style_context().add_class('prefs_list')

        viewport = Gtk.Viewport()
        viewport.add(self.content_box)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.props.hexpand = True
        scrolled_window.props.min_content_height = 500
        scrolled_window.props.min_content_width = 600
        scrolled_window.add_with_viewport(viewport)

        outside_box = Gtk.Box()
        outside_box.add(scrolled_window)
        outside_box.show_all()

        self._add_page("__shortcuts", outside_box)

    def __row_activated_cb(self, list_box, row):
        index = row.get_index()
        item = self.list_store.get_item(index)
        customsation_dialog = CustomShortcutDialog(self.app, self.dialog, item)
        customsation_dialog.show()

    def _create_widget_func(self, item, user_data):
        """Generates and fills up the contents for the model."""
        accel_changed = self.app.shortcuts.is_changed(item.action_name)

        title_label = Gtk.Label()
        accel_label = Gtk.Label()
        title_label.set_text(item.title)
        accel_label.set_text(item.get_accel())

        if not accel_changed:
            accel_label.set_state_flags(Gtk.StateFlags.INSENSITIVE, True)

        title_label.props.xalign = 0
        title_label.props.margin_start = PADDING * 3
        title_label.props.margin_end = PADDING * 3
        title_label.props.margin_top = PADDING * 2
        title_label.props.margin_bottom = PADDING * 2
        self.description_size_group.add_widget(title_label)

        accel_label.props.xalign = 0
        accel_label.props.margin_start = PADDING * 3
        accel_label.props.margin_end = PADDING * 2
        self.accel_size_group.add_widget(accel_label)

        # Add the third column with the reset button.
        button = Gtk.Button.new_from_icon_name("edit-clear-all-symbolic",
                                               Gtk.IconSize.MENU)
        button.set_tooltip_text(_("Reset the shortcut to the default accelerator"))
        button.props.margin_end = PADDING / 2
        button.set_relief(Gtk.ReliefStyle.NONE)
        button.connect("clicked", self.__reset_accelerator_cb, item)
        button.set_sensitive(accel_changed)

        title_label.show()
        accel_label.show()
        button.show()

        # Pack the three widgets above into a row and add to parent_box.
        contents_box = Gtk.Box()
        contents_box.pack_start(title_label, True, True, 0)
        contents_box.pack_start(accel_label, True, False, 0)
        contents_box.pack_start(button, False, False, 0)

        return contents_box

    def _add_header_func(self, row, before, unused_user_data):
        """Adds a header for a new section in the model."""
        group = self.list_store.get_item(row.get_index()).group
        try:
            prev_group = self.list_store.get_item(row.get_index() - 1).group
        except OverflowError:
            prev_group = None

        if prev_group != group:
            if before is not None:
                before.get_style_context().add_class("last")

            header = Gtk.Label()
            header.set_use_markup(True)
            group_title = self.app.shortcuts.group_titles[group]
            header.set_markup("<b>%s</b>" % group_title)
            header.props.margin_top = PADDING if not prev_group else PADDING * 8
            header.props.margin_bottom = PADDING * 2
            header.props.margin_start = 1
            header.props.margin_end = PADDING * 2
            header.props.xalign = 0
            alter_style_class("group_title", header, "font-size: small;")
            header.get_style_context().add_class("group_title")
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            box.add(header)
            box.get_style_context().add_class("background")
            box.show_all()
            row.set_header(box)
            row.get_style_context().add_class("first")

    def __reset_accelerator_cb(self, unused_button, item):
        """Resets the accelerator to the default value."""
        self.app.shortcuts.reset_accels(item.action_name)

    def __accel_changed_cb(self, shortcuts_manager, action_name):
        """Handles the changing of a shortcut's accelerator."""
        if action_name:
            index = self.action_ids[action_name]
            count = 1
        else:
            # All items changed.
            index = 0
            count = self.list_store.get_n_items()
        self.list_store.emit("items-changed", index, count, count)

    def _factory_settings_button_cb(self, unused_button):
        """Resets all settings to the defaults."""
        for section in self.prefs.values():
            for attrname in section:
                self.__reset_option(self.resets[attrname], attrname)
        self.app.shortcuts.reset_accels()

    def _revert_button_cb(self, unused_button):
        """Resets all settings to the values when the dialog was opened."""
        for attrname, value in self.original_values.items():
            self.widgets[attrname].set_widget_value(value)
            setattr(self.settings, attrname, value)
        self.original_values = {}
        self.revert_button.set_sensitive(False)
        self.factory_settings.set_sensitive(self._can_reset())

    def __reset_option_cb(self, button, *attrnames):
        for attrname in attrnames:
            self.__reset_option(button, attrname)

    def __reset_option(self, button, attrname):
        """Resets a particular setting to the factory default."""
        if not self.settings.is_default(attrname):
            self.settings.set_default(attrname)
        self.widgets[attrname].set_widget_value(getattr(self.settings, attrname))
        button.set_sensitive(False)
        self.factory_settings.set_sensitive(self._can_reset())

    def _response_cb(self, unused_button, unused_response_id):
        self.dialog.destroy()

    def _value_changed_cb(self, unused_fake_widget, real_widget, attrname):
        value = getattr(self.settings, attrname)
        if attrname not in self.original_values:
            self.original_values[attrname] = value
            if not GlobalSettings.notifies_config_option(attrname):
                self.restart_warning.show()
            self.revert_button.set_sensitive(True)

        value = real_widget.get_widget_value()
        setattr(self.settings, attrname, value)

        # adjust controls as appropriate
        self.resets[attrname].set_sensitive(
            not self.settings.is_default(attrname))
        self.factory_settings.set_sensitive(True)

    def _configure_cb(self, unused_widget, event):
        self.settings.prefsDialogWidth = event.width
        self.settings.prefsDialogHeight = event.height

    def _can_reset(self):
        for section in self.prefs.values():
            for attrname in section:
                if not self.settings.is_default(attrname):
                    return True
        return False


class ModelItem(GObject.Object):
    """Holds the data of a keyboard shortcut for a Gio.ListStore."""

    def __init__(self, app, action_name, title, group):
        GObject.Object.__init__(self)
        self.app = app
        self.action_name = action_name
        self.title = title
        self.group = group

    def get_accel(self):
        """Returns the corresponding accelerator in a viewable format."""
        try:
            accels = self.app.get_accels_for_action(self.action_name)[0]
        except IndexError:
            accels = ""

        keyval, mods = Gtk.accelerator_parse(accels)
        return Gtk.accelerator_get_label(keyval, mods)


class CustomShortcutDialog(Gtk.Dialog):
    """Dialog for customising accelerator invoked by activating a row in preferences."""

    FORBIDDEN_KEYVALS = [Gdk.KEY_Escape]

    def __init__(self, app, pref_dialog, customised_item):
        Gtk.Dialog.__init__(self, use_header_bar=True, flags=Gtk.DialogFlags.MODAL)
        self.app = app
        self.preferences = pref_dialog
        self.customised_item = customised_item

        # The keyboard shortcut typed by the user.
        self.accelerator = None

        self.set_title(_("Set Shortcut"))
        # Set a minimum size.
        self.set_size_request(500, 300)
        # Set a maximum size.
        geometry = Gdk.Geometry()
        geometry.max_width = self.get_size_request()[0]
        geometry.max_height = -1
        self.set_geometry_hints(None, geometry, Gdk.WindowHints.MAX_SIZE)
        self.set_transient_for(self.preferences)
        self.get_titlebar().set_decoration_layout('close:')
        self.add_events(Gdk.EventMask.KEY_PRESS_MASK)

        self.conflicting_action = None

        # Setup the widgets used in the dialog.
        self.apply_button = self.add_button(_("Apply"), Gtk.ResponseType.OK)
        self.apply_button.get_style_context()\
            .add_class(Gtk.STYLE_CLASS_SUGGESTED_ACTION)
        self.apply_button.set_tooltip_text(_("Apply the accelerator to this"
                                             " shortcut."))
        self.apply_button.hide()
        self.replace_button = self.add_button(_("Replace"), Gtk.ResponseType.OK)
        self.replace_button.get_style_context().\
            add_class(Gtk.STYLE_CLASS_SUGGESTED_ACTION)
        self.replace_button.set_tooltip_text(_("Remove this accelerator from where "
                                               "it was used previously and set it for "
                                               "this shortcut."))
        self.replace_button.hide()

        prompt_label = Gtk.Label()
        prompt_label.set_markup(
            _("Enter new shortcut for <b>%s</b>, or press Esc to cancel.")
            % customised_item.title)
        prompt_label.props.wrap = True
        prompt_label.props.margin_bottom = PADDING * 3
        prompt_label.show()
        self.accelerator_label = Gtk.Label()
        self.accelerator_label.props.margin_bottom = PADDING
        self.invalid_label = Gtk.Label()
        self.invalid_label.set_text(
            _("The accelerator you are trying to set might interfere with typing."
              " Try using Control, Shift or Alt with some other key, please."))
        self.invalid_label.props.wrap = True
        self.conflict_label = Gtk.Label()
        self.conflict_label.props.wrap = True

        content_area = self.get_content_area()
        content_area.props.margin = PADDING * 3
        content_area.add(prompt_label)
        content_area.add(self.accelerator_label)
        content_area.add(self.conflict_label)
        content_area.add(self.invalid_label)

    def do_key_press_event(self, event):
        """Handles key press events and detects valid accelerators."""
        keyval = event.keyval
        mask = event.state

        if keyval == Gdk.KEY_Escape:
            self.destroy()
            return

        self.accelerator = Gtk.accelerator_name(keyval, mask)

        accelerator = Gtk.accelerator_get_label(keyval, mask)
        self.accelerator_label.set_markup("<span size='20000'><b>%s</b></span>"
                                          % accelerator)
        valid = Gtk.accelerator_valid(keyval, mask)

        self.conflicting_action = self.app.shortcuts.get_conflicting_action(
            self.customised_item.action_name, keyval, mask)
        if valid and self.conflicting_action:
            title = self.app.shortcuts.titles[self.conflicting_action]
            self.conflict_label.set_markup(
                _("This key combination is already used by <b>%s</b>."
                  " Press Replace to use it for <b>%s</b> instead.")
                % (title, self.customised_item.title))

        # Set visibility according to the booleans set above.
        self.apply_button.set_visible(valid and not bool(self.conflicting_action))
        self.accelerator_label.set_visible(valid)
        self.conflict_label.set_visible(valid and bool(self.conflicting_action))
        self.replace_button.set_visible(valid and bool(self.conflicting_action))
        self.invalid_label.set_visible(not valid)

    def do_response(self, response):
        """Handles the user's response."""
        if response == Gtk.ResponseType.OK:
            assert self.accelerator
            if self.conflicting_action:
                # Disable the accelerator in its previous use, set for this action.
                accels = self.app.get_accels_for_action(self.conflicting_action)
                accels.remove(self.accelerator)
                self.app.shortcuts.set(self.conflicting_action, accels)

            # Apply the custom accelerator to the shortcut.
            action = self.customised_item.action_name
            self.app.shortcuts.set(action, [self.accelerator])
            self.app.shortcuts.save()
        self.destroy()


@Gtk.Template(filename=os.path.join(get_ui_dir(), "pluginpreferencesrow.ui"))
class PluginPreferencesRow(Gtk.ListBoxRow):
    """A row in the plugins list allowing activating and deactivating a plugin."""

    __gtype_name__ = "PluginPreferencesRow"

    _title_label = Gtk.Template.Child()
    _description_label = Gtk.Template.Child()
    switch = Gtk.Template.Child()

    def __init__(self, item):
        Gtk.ListBoxRow.__init__(self)
        self.plugin_info = item.plugin_info
        self.switch_handler_id: Optional[int] = None

        self._title_label.set_text(self.plugin_info.get_name())

        description = self.plugin_info.get_description()
        if not description:
            description = _("No description available.")
            self._description_label.set_markup(
                "<span style=\"italic\">%s</span>" % description)
        else:
            self._description_label.set_text(description)


class PluginItem(GObject.Object):
    """Holds the data of a plugin info for a Gio.ListStore."""

    def __init__(self, plugin_info):
        GObject.Object.__init__(self)
        self.plugin_info = plugin_info


class PluginManagerStore(Gio.ListStore):
    """Stores the models for available plugins."""

    def __init__(self):
        Gio.ListStore.__init__(self, item_type=PluginItem)
        self.app = None
        self.preferences_dialog = None

    @classmethod
    def new(cls, app, preferences_dialog):
        store = PluginManagerStore()
        store.app = app
        store.preferences_dialog = preferences_dialog
        store.reload()
        return store

    def reload(self):
        self.remove_all()
        plugins = self.app.plugin_manager.engine.get_plugin_list()
        # Firstly, sort the plugins according the number assigned to the
        # pluginmanager.PluginType object. Secondly, sort alphabetically.
        for plugin_info in sorted(plugins,
                                  key=lambda x: (PluginManager.get_plugin_type(x), x.get_name())):
            self.append(PluginItem(plugin_info))


class PluginsBox(Gtk.ListBox):
    """A ListBox for showing plugins grouped by type."""

    def __init__(self, list_store):
        Gtk.ListBox.__init__(self)
        self.app = list_store.app
        self.list_store = list_store
        self.title_size_group = None
        self.switch_size_group = None

        self.set_selection_mode(Gtk.SelectionMode.NONE)
        self.set_header_func(self._add_header_func, None)
        self.bind_model(self.list_store, self._create_widget_func, None)

        self.props.margin = PADDING * 3
        self.props.margin_top = 0

        self.get_style_context().add_class('prefs_list')

        # Activate the plugins' switches for plugins that are already loaded.
        loaded_plugins = self.app.plugin_manager.engine.get_loaded_plugins()
        for row in self.get_children():
            if row.plugin_info.get_module_name() in loaded_plugins:
                row.switch.set_active(True)

        self.app.plugin_manager.engine.connect_after("load-plugin",
                                                     self.__load_plugin_cb)
        self.app.plugin_manager.engine.connect_after("unload-plugin",
                                                     self.__unload_plugin_cb)

    def get_row(self, module_name):
        """Gets the PluginPreferencesRow linked to a given module name."""
        for row in self.get_children():
            if row.plugin_info.get_module_name() == module_name:
                return row
        return None

    def _create_widget_func(self, item, unused_user_data):
        row = PluginPreferencesRow(item)
        row.switch_handler_id = row.switch.connect("notify::active",
                                                   self.__switch_active_cb,
                                                   row.plugin_info)
        return row

    def __switch_active_cb(self, switch, unused_pspec, plugin_info):
        engine = self.app.plugin_manager.engine
        if switch.get_active():
            if not engine.load_plugin(plugin_info):
                stack = self.list_store.preferences_dialog.stack
                preferences_page = stack.get_child_by_name("_plugins")
                msg = _("Unable to load the plugin '{module_name}'").format(
                    module_name=plugin_info.get_module_name())
                preferences_page.show_infobar(msg, Gtk.MessageType.WARNING)
                switch.set_active(False)
        else:
            self.app.plugin_manager.engine.unload_plugin(plugin_info)

    def __load_plugin_cb(self, engine, plugin_info):
        """Handles the activation of one of the available plugins."""
        row = self.get_row(plugin_info.get_module_name())
        if row is not None and row.switch_handler_id is not None:
            with row.switch.handler_block(row.switch_handler_id):
                row.switch.set_active(True)

    def __unload_plugin_cb(self, engine, plugin_info):
        """Handles the deactivation of one of the available plugins."""
        row = self.get_row(plugin_info.get_module_name())
        if row is not None and row.switch_handler_id is not None:
            with row.switch.handler_block(row.switch_handler_id):
                row.switch.set_active(False)

    def _add_header_func(self, row, before, unused_user_data):
        """Adds a header for a new section in the model."""
        current_type = PluginManager.get_plugin_type(row.plugin_info)
        if before is not None:
            previous_type = PluginManager.get_plugin_type(before.plugin_info)
        else:
            previous_type = None
        if previous_type != current_type:
            self._set_header(row, current_type)
            if before is not None:
                before.get_style_context().add_class("last")

    def _set_header(self, row, group):
        group_title = str(group)
        header = Gtk.Label()
        header.set_use_markup(True)

        header.set_markup("<b>%s</b>" % group_title)
        header.props.valign = Gtk.Align.CENTER
        header.props.halign = Gtk.Align.START
        alter_style_class("group_title", header, "font-size: small;")
        header.get_style_context().add_class("group_title")

        button = Gtk.Button.new()
        button.props.valign = Gtk.Align.CENTER
        button.props.relief = Gtk.ReliefStyle.NONE
        button.add(Gtk.Image.new_from_icon_name("folder-open-symbolic", Gtk.IconSize.MENU))
        button.connect("clicked", self.__location_clicked_cb, group.get_dir())

        inner_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        inner_box.set_halign(Gtk.Align.FILL)
        inner_box.props.margin_top = PADDING * 3
        inner_box.props.margin_bottom = PADDING
        inner_box.props.margin_end = PADDING * 2
        inner_box.pack_start(header, True, True, 0)
        inner_box.pack_start(button, False, False, 0)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.add(inner_box)
        box.get_style_context().add_class("background")
        box.show_all()
        row.set_header(box)
        row.get_style_context().add_class("first")

    def __location_clicked_cb(self, unused_button, directory):
        uri = GLib.filename_to_uri(directory, None)
        Gio.AppInfo.launch_default_for_uri(uri, None)


class PluginPreferencesPage(Gtk.ScrolledWindow):
    """The page that displays the list of available plugins."""

    INFOBAR_TIMEOUT_SECONDS = 5

    def __init__(self, app, preferences_dialog):
        Gtk.ScrolledWindow.__init__(self)

        list_store = PluginManagerStore.new(app, preferences_dialog)
        if list_store.get_n_items():
            plugins_box = PluginsBox(list_store)
        else:
            # We could use Gtk.ListBox.set_placeholder, but it
            # appears bad inside the list widget.
            placeholder_label = Gtk.Label.new(_("No plugins available"))
            placeholder_label.props.margin = 4 * PADDING
            placeholder_label.props.margin_top = 10 * PADDING
            placeholder_label.show()
            plugins_box = placeholder_label

        self._infobar_revealer = Gtk.Revealer()
        self._infobar = Gtk.InfoBar()
        fix_infobar(self._infobar)
        self._infobar_label = Gtk.Label()
        self._setup_infobar()

        note_label = Gtk.Label.new()
        note_label.set_markup(_("You can create <a href='{doc_url}'>plugins</a> into your <a href='{dir_url}'>plugins directory</a>.").format(
            doc_url="http://developer.pitivi.org/Plugins.html",
            dir_url=GLib.filename_to_uri(get_user_plugins_dir(), None)))
        note_label.props.margin_top = PADDING * 4
        note_label.props.margin_bottom = PADDING * 2

        wrapper_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(wrapper_box)
        self.set_min_content_height(500)
        self.set_min_content_width(600)

        wrapper_box.pack_start(self._infobar_revealer, expand=False, fill=False, padding=0)
        wrapper_box.pack_start(plugins_box, expand=False, fill=False, padding=0)
        wrapper_box.pack_start(note_label, expand=False, fill=False, padding=0)

        # Helpers
        self._infobar_timer = None

    def _setup_infobar(self):
        self._infobar_revealer.add(self._infobar)
        self._infobar_label.set_line_wrap(True)
        self._infobar.get_content_area().add(self._infobar_label)

    def show_infobar(self, text, message_type, auto_hide=True):
        """Sets a text and a message type to the infobar to display it."""
        self._infobar.set_message_type(message_type)
        self._infobar_label.set_text(text)
        self._infobar_revealer.set_reveal_child(True)
        if auto_hide:
            if self._infobar_timer is not None:
                self._infobar_timer.cancel()
            self._infobar_timer = Timer(self.INFOBAR_TIMEOUT_SECONDS,
                                        self.hide_infobar)
            self._infobar_timer.start()

    def hide_infobar(self):
        """Hides the info bar."""
        self._infobar_revealer.set_reveal_child(False)
        self._infobar_timer = None
