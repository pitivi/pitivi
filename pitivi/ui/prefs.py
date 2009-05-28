# PiTiVi , Non-linear video editor
#
#       ui/prefs.py
#
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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""
Dialog box for user preferences.
"""

import gtk
from gettext import gettext as _
import pitivi.ui.dynamic as dynamic
from pitivi.settings import GlobalSettings

GlobalSettings.addConfigOption('prefsDialogWidth',
    section = "user-interface",
    key = "prefs-dialog-width",
    default = 400)

GlobalSettings.addConfigOption('prefsDialogHeight',
    section = "user-interface",
    key = "prefs-dialog-height",
    default = 300)

class PreferencesDialog(gtk.Window):

    prefs = {}
    original_values = {}

    def __init__(self, instance):
        gtk.Window.__init__(self)
        self.app = instance
        self.settings = instance.settings
        self.widgets = {}
        self.resets = {}
        self._current = None
        self._createUi()
        self._fillContents()
    
    def _createUi(self):
        self.set_title(_("Preferences"))
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.set_border_width(12)
        self.connect("configure-event", self._configureCb)
        self.set_default_size(self.settings.prefsDialogWidth,
            self.settings.prefsDialogHeight)

        # basic layout
        vbox = gtk.VBox()
        vbox.set_spacing(6)
        button_box = gtk.HBox()
        button_box.set_spacing(5)
        button_box.set_homogeneous(False)
        pane = gtk.HPaned()
        vbox.pack_start(pane, True, True)
        vbox.pack_end(button_box, False, False)
        pane.show()
        self.add(vbox)
        vbox.show()

        # left-side list view
        self.model = gtk.ListStore(str, str)
        self.treeview = gtk.TreeView(self.model)
        self.treeview.get_selection().connect("changed",
            self._treeSelectionChangedCb)
        ren = gtk.CellRendererText()
        col = gtk.TreeViewColumn(_("Section"), ren, text=0)
        self.treeview.append_column(col)
        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        scrolled.add(self.treeview)
        scrolled.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.treeview.props.headers_visible = False
        self.treeview.show()
        pane.pack1(scrolled)
        scrolled.show()

        # preferences content region
        self.contents = gtk.VBox()
        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolled.add_with_viewport(self.contents)
        pane.pack2(scrolled)
        scrolled.show()
        self.contents.show()

        # revert, close buttons
        self.factory_settings = gtk.Button(label=_("Reset to Factory Settings"))
        self.factory_settings.connect("clicked", self._factorySettingsButtonCb)
        self.factory_settings.set_sensitive(self._canReset())
        self.factory_settings.show()
        self.revert_button = gtk.Button(_("Revert"))
        self.revert_button.connect("clicked", self._revertButtonCb)
        self.revert_button.show()
        self.revert_button.set_sensitive(False)
        accept_button = gtk.Button(stock=gtk.STOCK_CLOSE)
        accept_button.connect("clicked", self._acceptButtonCb)
        accept_button.show()
        button_box.pack_start(self.factory_settings, False, True)
        button_box.pack_end(accept_button, False, True)
        button_box.pack_end(self.revert_button, False, True)
        button_box.show()

        # restart warning
        self.restart_warning = gtk.Label()
        self.restart_warning.set_markup(
            "<b>%s</b>" % _("Some changes will not take effect until you "
            "restart PiTiVi"))
        vbox.pack_end(self.restart_warning, False, False)

## Public API

    @classmethod
    def addPreference(cls, attrname, label, description, section=None, 
        widget_klass=None, **args):
        """
        Add a user preference. The preferences dialog will try
        to guess the appropriate widget to use based on the type of the
        option, but you can override this by specifying a ustom class.

        @param label: user-visible name for this option
        @type label: C{str}
        @param desc: a user-visible description documenting this option
        (ignored unless prefs_label is non-null)
        @type desc: C{str}
        @param : user-visible category to which this option
        belongs (ignored unless prefs_label is non-null)
        @type section: C{str}
        @param widget_klass: overrides auto-detected widget
        @type widget_klass: C{class}
        """
        if not section:
            section = "General"
        if not section in cls.prefs:
            cls.prefs[section] = {}
        cls.prefs[section][attrname] = (label, description, widget_klass, args)

    @classmethod
    def addPathPreference(cls, attrname, label, description, section=None):
        """
        Add an auto-generated user preference that will show up as a
        gtk.FileChooserButton.

        @param label: user-visible name for this option
        @type label: C{str}
        @param desc: a user-visible description documenting this option
        (ignored unless prefs_label is non-null)
        @type desc: C{str}
        @param section: user-visible category to which this option
        belongs (ignored unless prefs_label is non-null)
        @type section: C{str}
        """
        cls.addPreference(attrname, label, description, section,
            dynamic.PathWidget)

    @classmethod
    def addNumericPreference(cls, attrname, label, description, section=None,
        upper = None, lower = None):
        """
        Add an auto-generated user preference that will show up as either a
        gtk.SpinButton or a gtk.HScale, depending whether both the upper and lower
        limits are set.

        @param label: user-visible name for this option
        @type label: C{str}
        @param desc: a user-visible description documenting this option
        (ignored unless prefs_label is non-null)
        @type desc: C{str}
        @param section: user-visible category to which this option
        belongs (ignored unless prefs_label is non-null)
        @type section: C{str}
        @param upper: upper limit for this widget, or None
        @type upper: C{number}
        @param lower: lower limit for this widget, or None
        @type lower: C{number}
        """
        cls.addPreference(attrname, label, description, section,
            dynamic.NumericWidget, upper=upper, lower=lower)

    @classmethod
    def addTextPreference(cls, attrname, label, description, section=None,
        matches = None):
        """
        Add an auto-generated user preference that will show up as either a
        gtk.SpinButton or a gtk.HScale, depending on the upper and lower
        limits

        @param label: user-visible name for this option
        @type label: C{str}
        @param desc: a user-visible description documenting this option
        (ignored unless prefs_label is non-null)
        @type desc: C{str}
        @param section: user-visible category to which this option
        belongs (ignored unless prefs_label is non-null)
        @type section: C{str}
        """
        cls.addPreference(attrname, label, description, section,
            dynamic.TextWidget, matches=matches)

    @classmethod
    def addChoicePreference(cls, attrname, label, description, choices,
        section=None):
        """
        Add an auto-generated user preference that will show up as either a
        gtk.ComboBox or a group of radio buttons, depending on the number of
        choices.

        @param label: user-visible name for this option
        @type label: C{str}
        @param desc: a user-visible description documenting this option
        (ignored unless prefs_label is non-null)
        @type desc: C{str}
        @param choices: a sequence of (<label>, <value>) pairs
        @type choices: C{[(str, pyobject), ...]}
        @param section: user-visible category to which this option
        belongs (ignored unless prefs_label is non-null)
        @type section: C{str}
        """
        cls.addPreference(attrname, label, description, section,
            dynamic.ChoiceWidget, choices=choices)

    @classmethod
    def addTogglePreference(cls, attrname, label, description, section=None):
        """
        Add an auto-generated user preference that will show up as a
        gtk.CheckButton.

        @param label: user-visible name for this option
        @type label: C{str}
        @param desc: a user-visible description documenting this option
        (ignored unless prefs_label is non-null)
        @type desc: C{str}
        @param section: user-visible category to which this option
        belongs (ignored unless prefs_label is non-null)
        @type section: C{str}
        """
        cls.addPreference(attrname, label, description, section,
            dynamic.ToggleWidget)

    @classmethod
    def addColorPreference(cls, attrname, label, description, section=None,
        value_type=int):
        """
        Add an auto-generated user preference for specifying colors. The
        colors can be returned as either int, a string colorspec, or a
        gtk.gdk.Color object. See the gtk.gdk.color_parse() function for info
        on colorspecs.

        @param label: user-visible name for this option
        @type label: C{str}
        @param desc: a user-visible description documenting this option
        (ignored unless prefs_label is non-null)
        @type desc: C{str}
        @param section: user-visible category to which this option
        belongs (ignored unless prefs_label is non-null)
        @type section: C{str}
        """
        cls.addPreference(attrname, label, description, section,
            dynamic.ColorWidget, value_type=value_type)

    @classmethod
    def addFontPreference(cls, attrname, label, description, section=None):
        """
        Add an auto-generated user preference that will show up as a
        font selector.

        @param label: user-visible name for this option
        @type label: C{str}
        @param desc: a user-visible description documenting this option
        (ignored unless prefs_label is non-null)
        @type desc: C{str}
        @param section: user-visible category to which this option
        belongs (ignored unless prefs_label is non-null)
        @type section: C{str}
        """
        cls.addPreference(attrname, label, description, section,
            dynamic.FontWidget)


## Implementation

    def _fillContents(self):
        self.sections = {}
        for section in sorted(self.prefs):
            options = self.prefs[section]
            self.model.append((_(section), section))
            widgets = gtk.Table()
            widgets.set_border_width(6)
            widgets.props.column_spacing = 6
            widgets.props.row_spacing = 3
            self.sections[section] = widgets

            prefs = {}
            for attrname in options:
                label, description, klass, args = options[attrname]
                label_widget = gtk.Label(_(label) + ":")
                widget = klass(**args)
                widget.setWidgetValue(getattr(self.settings, attrname))
                widget.connectValueChanged(self._valueChanged, widget,
                    attrname)
                self.widgets[attrname] = widget
                revert = gtk.Button(_("Reset"))
                revert.set_sensitive(not self.settings.isDefault(attrname))
                revert.connect("clicked",  self._resetOptionCb, attrname)
                self.resets[attrname] = revert
                prefs[label] = (label_widget, widget, revert)

            # Sort widgets: I think we only want to sort by the non-localized
            # names, so options appear in the same place across locales ...
            # but then I may be wrong

            for y, unlocalized in enumerate(sorted(prefs)):
                label, widget, revert = prefs[unlocalized]
                label.set_alignment(1.0, 0.5)
                widgets.attach(label, 0, 1, y, y + 1, xoptions=gtk.FILL, yoptions=0)
                widgets.attach(widget, 1, 2, y, y + 1, yoptions=0)
                widgets.attach(revert, 2, 3, y, y + 1, xoptions=0, yoptions=0)
                label.show()
                widget.show()
                revert.show()

            self.contents.pack_start(widgets, True, True)

        self.treeview.get_selection().select_path((0,))

    def _treeSelectionChangedCb(self, selection):
        model, iter = selection.get_selected()
        new = self.sections[model[iter][1]]
        if self._current != new:
            if self._current:
                self._current.hide()
            new.show()
            self._current = new

    def _clearHistory(self):
        self.original_values = {}
        self.revert_button.set_sensitive(False)

    def _factorySettingsButtonCb(self, unused_button):
        for section in self.prefs.itervalues():
            for attrname in section:
                self._resetOptionCb(self.resets[attrname], attrname)

    def _revertButtonCb(self, unused_button):
        for attrname, value in self.original_values.iteritems():
            self.widgets[attrname].setWidgetValue(value)
            setattr(self.settings, attrname, value)
        self._clearHistory()
        self.factory_settings.set_sensitive(self._canReset())

    def _resetOptionCb(self, button, attrname):
        if not self.settings.isDefault(attrname):
            self.settings.setDefault(attrname)
        self.widgets[attrname].setWidgetValue(getattr(self.settings,
            attrname))
        button.set_sensitive(False)
        self.factory_settings.set_sensitive(self._canReset())

    def _acceptButtonCb(self, unused_button):
        self._clearHistory()
        self.hide()

    def _valueChanged(self, fake_widget, real_widget, attrname):
        value = getattr(self.settings, attrname)
        if attrname not in self.original_values:
            self.original_values[attrname] = value
            if attrname + "Changed" not in GlobalSettings.get_signals():
                self.restart_warning.show()
            self.revert_button.set_sensitive(True)

        # convert the value of the widget to whatever type it is currently
        if value is not None:
            value = type(value)(real_widget.getWidgetValue())
        setattr(self.settings, attrname, value)

        # adjust controls as appropriate
        self.resets[attrname].set_sensitive(not self.settings.isDefault(
            attrname))
        self.factory_settings.set_sensitive(True)

    def _configureCb(self, unused_widget, event):
        self.settings.prefsDialogWidth = event.width
        self.settings.prefsDialogHeight = event.height

    def _canReset(self):
        for section in self.prefs.itervalues():
            for attrname in section:
                if not self.settings.isDefault(attrname):
                    return True
        return False

## Preference Test Cases

if False:

    from pitivi.settings import GlobalSettings

    options = (
        ('numericPreference1', 10),
        ('numericPreference2', 2.4),
        ('textPreference1', "banana"),
        ('textPreference2', "42"),
        ('aPathPreference', "file:///etc/"),
        ('aChoicePreference', 42),
        ('aLongChoicePreference', "Mauve"),
        ('aTogglePreference', True),
        ('aFontPreference', "Sans 9"),
    )

    for attrname, default in options:
        GlobalSettings.addConfigOption(attrname, default=default)

## Numeric

    PreferencesDialog.addNumericPreference('numericPreference1',
        label = "Open Range",
        section = "Test",
        description = "This option has no upper bound",
        lower = -10)

    PreferencesDialog.addNumericPreference('numericPreference2',
        label = "Closed Range",
        section = "Test",
        description = "This option has both upper and lower bounds",
        lower = -10,
        upper = 10000)

## Text

    PreferencesDialog.addTextPreference('textPreference1',
        label = "Unfiltered",
        section = "Test",
        description = "Anything can go in this box")

    PreferencesDialog.addTextPreference('textPreference2',
        label = "Numbers only",
        section = "Test",
        description = "This input validates its input with a regex",
        matches = "^-?\d+(\.\d+)?$")

## other

    PreferencesDialog.addPathPreference('aPathPreference',
        label = "Test Path",
        section = "Test",
        description = "Test the path widget")

    PreferencesDialog.addChoicePreference('aChoicePreference',
        label = "Swallow Velocity",
        section = "Test",
        description = "What is the velocity of an african swollow laden " \
            "a coconut?",
        choices = (
            ("42 Knots", 32),
            ("9 furlongs per fortnight", 42),
            ("I don't know that!", None)))

    PreferencesDialog.addChoicePreference('aLongChoicePreference',
        label = "Favorite Color",
        section = "Test",
        description = "What is the velocity of an african swollow laden " \
            "a coconut?",
        choices = (
            ("Mauve", "Mauve"),
            ("Chartreuse", "Chartreuse"),
            ("Magenta", "Magenta"),
            ("Pink", "Pink"),
            ("Orange", "Orange"),
            ("Yellow Ochre", "Yellow Ochre")))

    PreferencesDialog.addTogglePreference('aTogglePreference',
        label = "Test Toggle",
        section = "Test",
        description = "Test the toggle widget")

    PreferencesDialog.addFontPreference('aFontPreference',
        label = "Foo Font",
        section = "Test",
        description = "Test the font widget")
