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

class PreferencesDialog(gtk.Window):

    prefs = {}
    original_values = {}
    widgets = {}

    def __init__(self, instance):
        gtk.Window.__init__(self)
        self.app = instance
        self.settings = instance.settings
        self._current = None
        self._createUi()
        self._fillContents()


    def _createUi(self):
        self.set_title(_("Preferences"))
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.set_border_width(12)

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
        factory_settings = gtk.Button(label=_("Restore Factory Settings"))
        factory_settings.connect("clicked", self._factorySettingsButtonCb)
        factory_settings.set_sensitive(False)
        factory_settings.show()
        self.revert_button = gtk.Button(_("Revert"))
        self.revert_button.connect("clicked", self._revertButtonCb)
        self.revert_button.show()
        self.revert_button.set_sensitive(False)
        accept_button = gtk.Button(stock=gtk.STOCK_CLOSE)
        accept_button.connect("clicked", self._acceptButtonCb)
        accept_button.show()
        button_box.pack_start(factory_settings, False, True)
        button_box.pack_end(accept_button, False, True)
        button_box.pack_end(self.revert_button, False, True)
        button_box.show()

        # restart warning
        self.restart_warning = gtk.Label()
        self.restart_warning.set_markup(
            _("<b>Some changes will not take effect until you restart "
            "PiTiVi</b>"))
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

## Implementation

    def _fillContents(self):
        self.sections = {}
        for section, options in self.prefs.iteritems():
            self.model.append((_(section), section))
            widgets = gtk.Table()
            widgets.set_border_width(6)
            widgets.props.column_spacing = 6
            widgets.props.row_spacing = 3
            self.sections[section] = widgets
            for y, (attrname, (label, description, klass, args)) in enumerate(
                options.iteritems()):
                label = gtk.Label(_(label))
                label.set_justify(gtk.JUSTIFY_RIGHT)
                widget = klass(**args)
                widgets.attach(label, 0, 1, y, y + 1, xoptions=0, yoptions=0)
                widgets.attach(widget, 1, 2, y, y + 1, yoptions=0)
                widget.setWidgetValue(getattr(self.settings, attrname))
                widget.connectValueChanged(self._valueChanged, widget,
                    attrname)
                self.widgets[attrname] = widget
                label.show()
                widget.show()
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
        pass

    def _revertButtonCb(self, unused_button):
        for attrname, value in self.original_values.iteritems():
            self.widgets[attrname].setWidgetValue(value)
        self._clearHistory()

    def _acceptButtonCb(self, unused_button):
        self._clearHistory()
        self.hide()

    def _valueChanged(self, fake_widget, real_widget, attrname):
        if attrname not in self.original_values:
            self.original_values[attrname] = getattr(self.settings, attrname)
            if attrname + "Changed" not in GlobalSettings.get_signals():
                self.restart_warning.show()
            self.revert_button.set_sensitive(True)
        setattr(self.settings, attrname, real_widget.getWidgetValue())

## Preference Test Cases

if True:

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
