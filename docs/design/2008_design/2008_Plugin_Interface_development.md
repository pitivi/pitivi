## 2008 Plugin Interface

### About

Pitivi's current interface, whist having a solid base is a little
lackluster with regards to API compatibility and formality, I
(--[Gord](User:Gord.md) 16:06, 4 August 2008 (BST)) am currently
developing a branch that aims to counter that.

### Development

Current development is happening on a launchpad branch (simply for ease
of development for me) located here:
[https://code.edge.launchpad.net/\~gordallott/+junk/pitivi-plugininterface
pitivi-plugininterface](https://code.edge.launchpad.net/~gordallott/+junk/pitivi-plugininterface_pitivi-plugininterface.md)

## Concept

A plugin needs to communicate in two ways, the main application needs to
be able to talk to plugin code (call methods and such) and plugin code
needs to be able to communicate back via some sort of API, currently
pitivi handles the first problem with zope interfaces which works
nicely, the second problem is ignored, plugins must query pitivi's
internal code via pitivi.instance.PiTiVi which contains the programs
instance.

The problem with this direction is that any internal code changes will
break plugin compatibility and further more it increases the difficulty
of the casual user writing plugins as they are required to be intimately
knowledgeable of pitivi's internal code.

The tried and tested solution to this problem is to develop a plugin
API, the API will handle any communication from the plugin to pitivi by
abstracting pitivi.instance.PiTiVi with a stable API. The plugin can
then make simple calls such as api.gui.add\_menu\_item(...) and be
confident that the API will not change from version to version.

## API

### Design considerations

The api has a slight problem in that it may be initialised before pitivi
is ready to be modified, This is solved at the moment by 'locking' the
api (via decorators for ease of use..) until the main pitivi codebase
emits a 'ready' signal, the api will raise an InterfaceNotReadyError
exception if its called before then

### Current implementation

The current API uses epydoc for its documentation and is structured as
follows:

-   `pitivi`
    -   `PluginInterface`
        -   `gui`
            -   `show_gui(self, *args, **kwargs)` shows or hides the
                main application window depending on the value of
                'visible'
            -   `add_menu_item(self, *args, **kwargs)` Adds a menu
                item to the appropriate main window menu
            -   `remove_menu_item(self, name)` removes the given menu
                item from the user interface
            -   `remove_ui(self)` removes all changes this instance of
                the plugininterface has made to the user interface
        -   `Project`
            -   `add_source`

## Settings

The current api simply requires that plugin.settings exists and
(un)pickles that data to save/load settings, there is a problem there
with human readabity and maybe even security, also its not that kind to
version upgrades.

### Current implementation

The current implementation is inspired by Django's model setup,
essentially the plugin authors create a class, in that class are Fields
(special pitivi python objects that can handle validation and such) that
describe settings.

for example the Field for a setting that must be a single line string
would be

    mySetting = pluginsettings.CharField('a_string', default='hello world!')

At the moment plugin.settings must be a
pitivi.pluginsettings.SettingsStore object, this object can then create
xml data to store and retrieve the settings as needed.

a further example for the entire settings store is:

    class ConfigureTest_Settings(pluginsettings.SettingsStore):
        """ Our plugins settings """

        variable1 = pluginsettings.CharField('astring', default='hello world!')
        variable2 = pluginsettings.FloatField('float_field', default=10)

#### Fields

This is a list of the current fields available:

-   BooleanField
-   CharField
-   FloatField
-   IntegerField
-   TextField
-   NullField

## Configuration

The current api only makes one consideration regarding configuration,
that is that the plugin class object must be IConfigurable zope
interface compatible, which essentially means must provide the
configure() method - this requires plugins to create their own
configuration dialogs and such, which is a pain for plugin developers
and a pain for anyone that likes consistency in their applications To
solve this I am proposing an interface that will be able to take
settings defined by a plugin and turn that into a sensible gtk
configuration dialog.

### Current implementation

The current implementation is a mix-in object that replaces the
configure() method with our own gui-builder code (plugin authors that
need more flexibility can create their own configure() method)

the gui-builder code simply parses the current settings object and is
able to build a gui from the fields provided, for example it will
provide a text entry for CharField objects. what 'widget' is used to
draw each settings can be further customised by providing the setting
with a widget argument, for example:

    pw_string = CharField('a password string', default='', max_length=32,
                          widget=pluginsettings.charField_widget_passworded)

this code will provide an input widget where the characters are starred
out which is appropriate for a password field. plugins can even provide
their own widgets by subclassing FieldWidget but this is absolutely not
nessasserry

#### custom configuration widget example

this will check to see if the current screen is composited and emit a
warning

    composite_warning = _('Warning: you seem to have compositing enabled, this may \
    result in a severe slowdown when recording your screencast.')
    class composite_check(pluginsettings.FieldWidget):

        def __init__(self, field=None):
            pluginsettings.FieldWidget.__init__(self, field)

            self.container = gtk.HBox(False, 6)

            self.icon = gtk.Image()
            self.icon.set_from_stock(gtk.STOCK_DIALOG_WARNING, 6)
            self.container.pack_start(self.icon, False, True, 0)
            self.icon.show()

            self.label = gtk.Label(composite_warning)
            self.label.set_line_wrap(True)
            self.container.pack_start(self.label, True, True, 0)
            self.label.show()


            self.add(self.container)
            self.container.show()

            if not self.is_composited():
                #we check for a composited desktop with this
                self.container.hide()

        def get_value(self):

            return None


    class Settings(pluginsettings.SettingsStore):

        warning = NullField('', widget=composite_check, draw_label=False)

        ... more settings go here ...

##### custom configuration widget example - preview

The above example produces the following image

![](images/Config-custom-widget.png "Config-custom-widget.png")

## Plugin Examples

### Plugin that demonstrates the configuration dialog builder

    #!/usr/bin/env python
    #       configure_test.py
    #


    from zope.interface import Interface, Attribute
    import zope.interface as interface
    from pitivi import plugininterface
    from pitivi import plugincore
    from pitivi import pluginsettings
    from pitivi.pluginsettings import *
    from random import random

    class Interface_Settings(pluginsettings.SettingsStore):

        # this is a CharField setting, a charfield is used to store simple strings
        # we set its priority to 0 to make sure that its right at the top of our
        # settings dialog (lower values = drawn first)
        astring = CharField('a string', default='hello world!',
                            max_length=32, priority=0)

        # this is similar to the previous setting apart from that we use a different
        # 'widget' to draw the settings value, specifically one that will hide the
        # password from view
        pw_string = CharField('a password string', default='apassword', max_length=32,
                              widget=pluginsettings.charField_widget_passworded)

        # this is a FloatField setting, it will store floating point numbers,
        # by default this uses a 'spinner' widget in the settings dialog
        afloat = FloatField('put a number in here', default=10.0, priority=200,
                            min_value=0.0, max_value=20.0)

        # this is similar to the previous setting but instead will only store
        # integer values
        anint = IntegerField('put an int in here', default=5, priority=100)

        # this is another floating point setting but we use a different widget
        # to draw it, the scaleField widget will allow people to configure the
        # setting by dragging a handlebar around
        arange = FloatField('push this widget around', default=10.0, priority=500,
                            max_value=100.0, min_value=0.0,
                            widget=pluginsettings.scaleField_widget)

        airange = IntegerField('integer based range', default=10, priority=499,
                               max_value=100, min_value=0,
                               widget=pluginsettings.scaleField_widget)

        # this is a boolean value, it will store True/False values, we set draw_label
        # to false because the checkbutton that's used to draw this setting already
        # contains a label inside it
        truth = BooleanField('this is a truth value', default=True, draw_label=False)

        # second tag here - this is a 'realworld' example,
        # we pass each item two tags, the first tag indicates a 'major' tag and
        # the second indicates a 'minor' tag, if there is more than one major tag
        # given then the settings dialog will use a notebook to draw the settings,

        username = CharField('username', default='Simon', max_length=64,
                             priority=0, tags=('Realworld', 'user info'))
        password = CharField('password', default='', max_length=32,
                              widget=pluginsettings.charField_widget_passworded,
                              tags=('Realworld', 'user info'))

        fish_size = FloatField('Fish Size', default=15, priority=35,
                               max_value=100, min_value=1,
                               tags=('Realworld', 'Fish Configuration'),
                               widget=pluginsettings.scaleField_widget)

        fish_number = IntegerField('Number of fish', default=15, priority=1,
                                   max_value=1000, min_value=0,
                                   tags=('Realworld', 'Fish Configuration'),
                                   widget=pluginsettings.scaleField_widget)


    # this is our main plugin class that's called by pitivi, we subclass it from
    # ConfigureBuilder so that we can have a settings dialog built for us
    class Configure_Test(pluginsettings.ConfigureBuilder):

        interface.implements(plugincore.IPlugin, plugincore.IConfigurable)

        name = 'configure test plugin'
        category = 'test'
        description = 'a test plugin, just gets the configure test going'
        version = '1.0'
        authors = 'Gordon Allott'
        enabled = True

        # for our settings we must create an instance of our custom settings object
        settings = Interface_Settings()

        def __init__(self):
            pass


        def __call__(self, manager):
            """ called when the plugin is loaded """
            pluginsettings.ConfigureBuilder.__init__(self, manager)
            self.manager = manager

            # load our saved settings
            self.manager.loadSettings(self)

            # connect up the 'enabled changed' signal, its a signal that's emitted
            # when the plugin.enabled state is changed somehow, obviously our
            # plugin has to take note of that and disable/enable its functionality
            # accordingly
            self.manager.connect('plugin-enabled-changed', self._enabled_changed_cb)


        def cleanup(self):
            """ used to remove any items and stuff we have added """
            self.manager.saveSettings(self)


        def initialize(self, ref):
            """ called when the interface is ready to be manipulated """
            pass


        # -- callbacks --
        def _enabled_changed_cb(self, manager, plugins):
            """ called when some plugins state has changed, maybe this one """
            if self.name in plugins:
                if self.enabled:
                    self.initialize(None)
                else:
                    self.cleanup()

#### Preview of the previous example

![](images/Config-example.png "Config-example.png")
