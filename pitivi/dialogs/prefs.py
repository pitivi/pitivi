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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
"""User preferences."""
import os
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gtk

from pitivi.configure import get_ui_dir
from pitivi.settings import GlobalSettings
from pitivi.utils import widgets
from pitivi.utils.loggable import Loggable
from pitivi.utils.ui import PADDING
from pitivi.utils.ui import SPACING


GlobalSettings.addConfigSection("user-interface")

GlobalSettings.addConfigOption('prefsDialogWidth',
                               section="user-interface",
                               key="prefs-dialog-width",
                               default=600)

GlobalSettings.addConfigOption('prefsDialogHeight',
                               section="user-interface",
                               key="prefs-dialog-height",
                               default=400)


class PreferencesDialog(Loggable):
    """Preferences for how the app works."""
    prefs = {}
    section_names = {"timeline": _("Timeline")}

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

        self.__add_settings_sections()
        self.__add_shortcuts_section()
        self.dialog.set_transient_for(app.gui)

    def run(self):
        """Runs the dialog."""
        self.dialog.run()

# Public API

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
        if section not in cls.prefs:
            cls.prefs[section] = {}
        cls.prefs[section][attrname] = (label, description, widget_class, args)

    @classmethod
    def addPathPreference(cls, attrname, label, description, section=None):
        """Adds a user preference for a file path."""
        cls._add_preference(attrname, label, description, section,
                            widgets.PathWidget)

    @classmethod
    def addNumericPreference(cls, attrname, label, description, section=None,
                             upper=None, lower=None):
        """Adds a user preference for a number.

        Show up as either a Gtk.SpinButton or a horizontal Gtk.Scale, depending
        whether both the upper and lower limits are set.
        """
        cls._add_preference(attrname, label, description, section,
                            widgets.NumericWidget, upper=upper, lower=lower)

    @classmethod
    def addTextPreference(cls, attrname, label, description, section=None, matches=None):
        """Adds a user preference for text."""
        cls._add_preference(attrname, label, description, section,
                            widgets.TextWidget, matches=matches)

    @classmethod
    def addChoicePreference(cls, attrname, label, description, choices, section=None):
        """Adds a user preference for text options."""
        cls._add_preference(attrname, label, description, section,
                            widgets.ChoiceWidget, choices=choices)

    @classmethod
    def addTogglePreference(cls, attrname, label, description, section=None):
        """Adds a user preference for an on/off option."""
        cls._add_preference(attrname, label, description, section,
                            widgets.ToggleWidget)

    @classmethod
    def addColorPreference(cls, attrname, label, description, section=None, value_type=int):
        """Adds a user preference for a color."""
        cls._add_preference(attrname, label, description, section,
                            widgets.ColorWidget, value_type=value_type)

    @classmethod
    def addFontPreference(cls, attrname, label, description, section=None):
        """Adds a user preference for a font."""
        cls._add_preference(attrname, label, description, section,
                            widgets.FontWidget)

    def __add_settings_sections(self):
        """Adds sections for the preferences which have been registered."""
        for section_id, options in sorted(self.prefs.items()):
            grid = Gtk.Grid()
            grid.set_border_width(SPACING)
            grid.props.column_spacing = SPACING
            grid.props.row_spacing = SPACING / 2

            prefs = []
            for attrname in options:
                label, description, widget_class, args = options[attrname]
                widget = widget_class(**args)
                widget.setWidgetValue(getattr(self.settings, attrname))
                widget.connectValueChanged(
                    self._valueChangedCb, widget, attrname)
                widget.set_tooltip_text(description)
                self.widgets[attrname] = widget
                # Add a semicolon, except for checkbuttons.
                if isinstance(widget, widgets.ToggleWidget):
                    widget.set_label(label)
                    label_widget = None
                else:
                    # Translators: This adds a semicolon to an already
                    # translated name of a preference.
                    label = _("%(preference_label)s:") % {"preference_label": label}
                    label_widget = Gtk.Label(label=label)
                    label_widget.set_tooltip_text(description)
                    label_widget.set_alignment(1.0, 0.5)
                    label_widget.show()
                icon = Gtk.Image()
                icon.set_from_icon_name(
                    "edit-clear-all-symbolic", Gtk.IconSize.MENU)
                revert = Gtk.Button()
                revert.add(icon)
                revert.set_tooltip_text(_("Reset to default value"))
                revert.set_relief(Gtk.ReliefStyle.NONE)
                revert.set_sensitive(not self.settings.isDefault(attrname))
                revert.connect("clicked", self._resetOptionCb, attrname)
                revert.show_all()
                self.resets[attrname] = revert
                row_widgets = (label_widget, widget, revert)
                # Construct the prefs list so that it can be sorted.
                # Make sure the L{ToggleWidget}s appear at the end.
                prefs.append((label_widget is None, label, row_widgets))

            # Sort widgets: I think we only want to sort by the non-localized
            # names, so options appear in the same place across locales ...
            # but then I may be wrong
            for y, (_1, _2, row_widgets) in enumerate(sorted(prefs)):
                label, widget, revert = row_widgets
                if not label:
                    grid.attach(widget, 0, y, 2, 1)
                    grid.attach(revert, 2, y, 1, 1)
                else:
                    grid.attach(label, 0, y, 1, 1)
                    grid.attach(widget, 1, y, 1, 1)
                    grid.attach(revert, 2, y, 1, 1)
                widget.show()
                revert.show()
            grid.show()
            self.stack.add_titled(grid, section_id, self.section_names[section_id])
        self.factory_settings.set_sensitive(self._canReset())

    def __add_shortcuts_section(self):
        """Adds a section with keyboard shortcuts."""
        shortcuts_manager = self.app.shortcuts
        self.description_size_group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        self.accel_size_group = Gtk.SizeGroup(Gtk.SizeGroupMode.HORIZONTAL)
        self.content_box = Gtk.ListBox()
        self.list_store = Gio.ListStore.new(ModelItem)
        index = 0
        for group in shortcuts_manager.groups:
            actions = shortcuts_manager.group_actions[group]
            for action, title in actions:
                item = ModelItem(self.app, action, title, group)
                self.list_store.append(item)
                self.action_ids[action] = index
                index += 1
        self.content_box.bind_model(self.list_store, self._create_widget_func, None)
        self.content_box.set_header_func(self._add_header_func, None)
        self.content_box.connect("row_activated", self.__row_activated_cb)
        self.content_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.content_box.props.margin = PADDING * 3
        viewport = Gtk.Viewport()
        viewport.add(self.content_box)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.add_with_viewport(viewport)
        scrolled_window.set_min_content_height(500)
        scrolled_window.set_min_content_width(600)

        outside_box = Gtk.Box()
        outside_box.add(scrolled_window)
        outside_box.show_all()

        self.stack.add_titled(outside_box, "shortcuts", _("Shortcuts"))

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
        title_label.props.margin_left = PADDING * 2
        title_label.props.margin_right = PADDING * 2
        self.description_size_group.add_widget(title_label)
        accel_label.props.xalign = 0
        accel_label.props.margin_left = PADDING * 2
        accel_label.props.margin_right = PADDING * 2
        self.accel_size_group.add_widget(accel_label)

        # Add the third column with the reset button.
        button = Gtk.Button.new_from_icon_name("edit-clear-all-symbolic",
                                               Gtk.IconSize.MENU)
        button.set_tooltip_text(_("Reset the shortcut to the default accelerator"))
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
            header = Gtk.Label()
            header.set_use_markup(True)
            group_title = self.app.shortcuts.group_titles[group]
            header.set_markup("<b>%s</b>" % group_title)
            header_box = Gtk.Box()
            header_box.add(header)
            header_box.props.margin_top = PADDING
            header_box.props.margin_bottom = PADDING
            header_box.props.margin_left = PADDING * 2
            header_box.props.margin_right = PADDING * 2
            # COMMENTED OUT UNTIL I FIND OUT HOW TO DO IT:
            # header_box.override_background_color(Gtk.StateType.NORMAL,
            #                                      Gdk.RGBA(.4, .4, .4, .4))
            header_box.show_all()
            row.set_header(header_box)
        else:
            row.set_header(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

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

    def _factorySettingsButtonCb(self, unused_button):
        """Resets all settings to the defaults."""
        for section in self.prefs.values():
            for attrname in section:
                self._resetOptionCb(self.resets[attrname], attrname)
        self.app.shortcuts.reset_accels()

    def _revertButtonCb(self, unused_button):
        """Resets all settings to the values when the dialog was opened."""
        for attrname, value in self.original_values.items():
            self.widgets[attrname].setWidgetValue(value)
            setattr(self.settings, attrname, value)
        self.original_values = {}
        self.revert_button.set_sensitive(False)
        self.factory_settings.set_sensitive(self._canReset())

    def _resetOptionCb(self, button, attrname):
        """Resets a particular setting to the factory default."""
        if not self.settings.isDefault(attrname):
            self.settings.setDefault(attrname)
        self.widgets[attrname].setWidgetValue(getattr(self.settings, attrname))
        button.set_sensitive(False)
        self.factory_settings.set_sensitive(self._canReset())

    def _response_cb(self, unused_button, unused_response_id):
        # Disable missing docstring
        # pylint: disable=C0111
        self.dialog.destroy()

    def _valueChangedCb(self, unused_fake_widget, real_widget, attrname):
        # Disable missing docstring
        # pylint: disable=C0111
        value = getattr(self.settings, attrname)
        if attrname not in self.original_values:
            self.original_values[attrname] = value
            if not GlobalSettings.notifiesConfigOption(attrname):
                self.restart_warning.show()
            self.revert_button.set_sensitive(True)

        # convert the value of the widget to whatever type it is currently
        if value is not None:
            value = type(value)(real_widget.getWidgetValue())
        setattr(self.settings, attrname, value)

        # adjust controls as appropriate
        self.resets[attrname].set_sensitive(
            not self.settings.isDefault(attrname))
        self.factory_settings.set_sensitive(True)

    def _configureCb(self, unused_widget, event):
        # Disable missing docstring
        # pylint: disable=C0111
        self.settings.prefsDialogWidth = event.width
        self.settings.prefsDialogHeight = event.height

    def _canReset(self):
        # Disable missing docstring
        # pylint: disable=C0111
        for section in self.prefs.values():
            for attrname in section:
                if not self.settings.isDefault(attrname):
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
