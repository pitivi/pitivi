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
import os
import subprocess
from gettext import gettext as _
from hashlib import md5
from time import time
from urllib.parse import unquote

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gio
from gi.repository import Gst
from gi.repository import GstPbutils
from gi.repository import Gtk

from pitivi.clipproperties import ClipProperties
from pitivi.configure import APPNAME
from pitivi.configure import APPURL
from pitivi.configure import get_pixmap_dir
from pitivi.configure import get_ui_dir
from pitivi.configure import GITVERSION
from pitivi.configure import in_devel
from pitivi.dialogs.prefs import PreferencesDialog
from pitivi.effects import EffectListWidget
from pitivi.mediafilespreviewer import PreviewWidget
from pitivi.medialibrary import MediaLibraryWidget
from pitivi.project import ProjectSettingsDialog
from pitivi.settings import GlobalSettings
from pitivi.shortcuts import ShortcutsWindow
from pitivi.tabsmanager import BaseTabs
from pitivi.timeline.timeline import TimelineContainer
from pitivi.titleeditor import TitleEditor
from pitivi.transitions import TransitionsListWidget
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import path_from_uri
from pitivi.utils.misc import show_user_manual
from pitivi.utils.ui import beautify_length
from pitivi.utils.ui import beautify_time_delta
from pitivi.utils.ui import clear_styles
from pitivi.utils.ui import info_name
from pitivi.utils.ui import SPACING
from pitivi.utils.ui import TIMELINE_CSS
from pitivi.viewer.viewer import ViewerContainer


GlobalSettings.addConfigSection("main-window")
GlobalSettings.addConfigOption('mainWindowHPanePosition',
                               section="main-window",
                               key="hpane-position",
                               type_=int)
GlobalSettings.addConfigOption('mainWindowMainHPanePosition',
                               section="main-window",
                               key="main-hpane-position",
                               type_=int)
GlobalSettings.addConfigOption('mainWindowVPanePosition',
                               section="main-window",
                               key="vpane-position",
                               type_=int)
GlobalSettings.addConfigOption('mainWindowX',
                               section="main-window",
                               key="X", default=0, type_=int)
GlobalSettings.addConfigOption('mainWindowY',
                               section="main-window",
                               key="Y", default=0, type_=int)
GlobalSettings.addConfigOption('mainWindowWidth',
                               section="main-window",
                               key="width", default=-1, type_=int)
GlobalSettings.addConfigOption('mainWindowHeight',
                               section="main-window",
                               key="height", default=-1, type_=int)
GlobalSettings.addConfigOption('lastProjectFolder',
                               section="main-window",
                               key="last-folder",
                               environment="PITIVI_PROJECT_FOLDER",
                               default=os.path.expanduser("~"))
GlobalSettings.addConfigSection('export')
GlobalSettings.addConfigOption('lastExportFolder',
                               section='export',
                               key="last-export-folder",
                               environment="PITIVI_EXPORT_FOLDER",
                               default=os.path.expanduser("~"))
GlobalSettings.addConfigSection("version")
GlobalSettings.addConfigOption('displayCounter',
                               section='version',
                               key='info-displayed-counter',
                               default=0)
GlobalSettings.addConfigOption('lastCurrentVersion',
                               section='version',
                               key='last-current-version',
                               default='')
GlobalSettings.addConfigOption('timelineAutoRipple',
                               section='user-interface',
                               key='timeline-autoripple',
                               default=False)


class MainWindow(Gtk.ApplicationWindow, Loggable):
    """Pitivi's main window.

    Attributes:
        app (Pitivi): The app.
    """

    def __init__(self, app):
        gtksettings = Gtk.Settings.get_default()
        gtksettings.set_property("gtk-application-prefer-dark-theme", True)
        theme = gtksettings.get_property("gtk-theme-name")
        os.environ["GTK_THEME"] = theme + ":dark"

        # Pulseaudio "role"
        # (http://0pointer.de/blog/projects/tagging-audio.htm)
        os.environ["PULSE_PROP_media.role"] = "production"
        os.environ["PULSE_PROP_application.icon_name"] = "pitivi"

        Gtk.ApplicationWindow.__init__(self)
        Loggable.__init__(self)
        self.app = app
        self.log("Creating MainWindow")
        self.settings = app.settings

        Gtk.IconTheme.get_default().append_search_path(get_pixmap_dir())

        self.connect("destroy", self._destroyedCb)

        self.setupCss()
        self.builder_handler_ids = []
        self.builder = Gtk.Builder()

        self._createUi()
        self.recent_manager = Gtk.RecentManager()

        pm = self.app.project_manager
        pm.connect("new-project-loading",
                   self._projectManagerNewProjectLoadingCb)
        pm.connect("new-project-loaded",
                   self._projectManagerNewProjectLoadedCb)
        pm.connect("new-project-failed",
                   self._projectManagerNewProjectFailedCb)
        pm.connect("save-project-failed",
                   self._projectManagerSaveProjectFailedCb)
        pm.connect("project-saved", self._projectManagerProjectSavedCb)
        pm.connect("closing-project", self._projectManagerClosingProjectCb)
        pm.connect("reverting-to-saved",
                   self._projectManagerRevertingToSavedCb)
        pm.connect("project-closed", self._projectManagerProjectClosedCb)
        pm.connect("missing-uri", self._projectManagerMissingUriCb)

    def setupCss(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(TIMELINE_CSS.encode('UTF-8'))
        screen = Gdk.Screen.get_default()
        style_context = self.get_style_context()
        style_context.add_provider_for_screen(screen, css_provider,
                                              Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def showRenderDialog(self):
        """Shows the RenderDialog for the current project."""
        from pitivi.render import RenderDialog

        project = self.app.project_manager.current_project
        dialog = RenderDialog(self.app, project)
        dialog.window.connect("destroy", self._renderDialogDestroyCb)
        self.set_sensitive(False)
        self.timeline_ui.disableKeyboardAndMouseEvents()
        dialog.window.show()

    def _destroyedCb(self, unused_self):
        self.render_button.disconnect_by_func(self._renderCb)
        pm = self.app.project_manager
        pm.disconnect_by_func(self._projectManagerNewProjectLoadingCb)
        pm.disconnect_by_func(self._projectManagerNewProjectLoadedCb)
        pm.disconnect_by_func(self._projectManagerNewProjectFailedCb)
        pm.disconnect_by_func(self._projectManagerSaveProjectFailedCb)
        pm.disconnect_by_func(self._projectManagerProjectSavedCb)
        pm.disconnect_by_func(self._projectManagerClosingProjectCb)
        pm.disconnect_by_func(self._projectManagerRevertingToSavedCb)
        pm.disconnect_by_func(self._projectManagerProjectClosedCb)
        pm.disconnect_by_func(self._projectManagerMissingUriCb)
        self.save_action.disconnect_by_func(self._saveProjectCb)
        self.new_project_action.disconnect_by_func(self._newProjectMenuCb)
        self.open_project_action.disconnect_by_func(self._openProjectCb)
        self.save_as_action.disconnect_by_func(self._saveProjectAsCb)
        self.help_action.disconnect_by_func(self._userManualCb)
        self.menu_button_action.disconnect_by_func(self._menuCb)
        self.disconnect_by_func(self._destroyedCb)
        self.disconnect_by_func(self._configureCb)
        for gobject, id_ in self.builder_handler_ids:
            gobject.disconnect(id_)
        self.builder_handler_ids = None
        self.vpaned.remove(self.timeline_ui)
        self.timeline_ui.destroy()

    def _renderDialogDestroyCb(self, unused_dialog):
        self.set_sensitive(True)
        self.timeline_ui.enableKeyboardAndMouseEvents()

    def _renderCb(self, unused_button):
        self.showRenderDialog()

    def _createUi(self):
        """Creates the graphical interface.

        The rough hierarchy is:
        vpaned:
        - mainhpaned(secondhpaned(main_tabs, context_tabs), viewer)
        - timeline_ui

        The full hierarchy can be admired by starting the GTK+ Inspector
        with Ctrl+Shift+I.
        """
        self.set_icon_name("pitivi")

        # Main "toolbar" (using client-side window decorations with HeaderBar)
        self._headerbar = Gtk.HeaderBar()
        self._create_headerbar_buttons()
        self.builder.add_from_file(
            os.path.join(get_ui_dir(), "mainmenubutton.ui"))

        # FIXME : see https://bugzilla.gnome.org/show_bug.cgi?id=729263
        self.builder.connect_signals_full(self._builderConnectCb, self)

        self._menubutton = self.builder.get_object("menubutton")

        if Gtk.get_major_version() == 3 and Gtk.get_minor_version() < 13:
            open_menu_image = self.builder.get_object("open_menu_image")
            open_menu_image.set_property("icon_name", "emblem-system-symbolic")

        self._menubutton_items = {}
        for widget in self.builder.get_object("menu").get_children():
            self._menubutton_items[Gtk.Buildable.get_name(widget)] = widget

        self._headerbar.pack_end(self._menubutton)
        self._headerbar.set_show_close_button(True)
        self._headerbar.show_all()
        self.set_titlebar(self._headerbar)

        # Set up our main containers, in the order documented above
        self.vpaned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)  # Separates the tabs+viewer from the timeline
        self.mainhpaned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)  # Separates the tabs from the viewer
        self.secondhpaned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)  # Separates the two sets of tabs
        self.vpaned.pack1(self.mainhpaned, resize=False, shrink=False)
        self.mainhpaned.pack1(self.secondhpaned, resize=True, shrink=False)
        self.add(self.vpaned)
        self.vpaned.show()
        self.secondhpaned.show()
        self.mainhpaned.show()

        # First set of tabs
        self.main_tabs = BaseTabs(self.app)
        self.medialibrary = MediaLibraryWidget(self.app)
        self.effectlist = EffectListWidget(self.app)
        self.main_tabs.append_page(
            self.medialibrary, Gtk.Label(label=_("Media Library")))
        self.main_tabs.append_page(
            self.effectlist, Gtk.Label(label=_("Effect Library")))
        self.medialibrary.connect('play', self._mediaLibraryPlayCb)
        self.medialibrary.show()
        self.effectlist.show()

        # Second set of tabs
        self.context_tabs = BaseTabs(self.app)
        self.clipconfig = ClipProperties(self.app)
        self.trans_list = TransitionsListWidget(self.app)
        self.title_editor = TitleEditor(self.app)
        self.context_tabs.append_page(
            self.clipconfig, Gtk.Label(label=_("Clip")))
        self.context_tabs.append_page(
            self.trans_list, Gtk.Label(label=_("Transition")))
        self.context_tabs.append_page(
            self.title_editor.widget, Gtk.Label(label=_("Title")))
        # Show by default the Title tab, as the Clip and Transition tabs
        # are useful only when a clip or transition is selected, but
        # the Title tab allows adding titles.
        self.context_tabs.set_current_page(2)

        self.secondhpaned.pack1(self.main_tabs, resize=False, shrink=False)
        self.secondhpaned.pack2(self.context_tabs, resize=False, shrink=False)
        self.main_tabs.show()
        self.context_tabs.show()

        # Viewer
        self.viewer = ViewerContainer(self.app)
        self.mainhpaned.pack2(self.viewer, resize=True, shrink=False)

        # Now, the lower part: the timeline
        self.timeline_ui = TimelineContainer(self.app)
        self.vpaned.pack2(self.timeline_ui, resize=True, shrink=False)

        # Enable our shortcuts for HeaderBar buttons and menu items:
        self._set_keyboard_shortcuts()

        # Identify widgets for AT-SPI, making our test suite easier to develop
        # These will show up in sniff, accerciser, etc.
        self.get_accessible().set_name("main window")
        self._headerbar.get_accessible().set_name("headerbar")
        self._menubutton.get_accessible().set_name("main menu button")
        self.vpaned.get_accessible().set_name("contents")
        self.mainhpaned.get_accessible().set_name("upper half")
        self.secondhpaned.get_accessible().set_name("tabs")
        self.main_tabs.get_accessible().set_name("primary tabs")
        self.context_tabs.get_accessible().set_name("secondary tabs")
        self.viewer.get_accessible().set_name("viewer")
        self.timeline_ui.get_accessible().set_name("timeline area")

        # Restore settings for position and visibility.
        if self.settings.mainWindowHPanePosition is None:
            self._setDefaultPositions()
        width = self.settings.mainWindowWidth
        height = self.settings.mainWindowHeight
        if height == -1 and width == -1:
            self.maximize()
        else:
            self.set_default_size(width, height)
            self.move(self.settings.mainWindowX, self.settings.mainWindowY)
        self.secondhpaned.set_position(self.settings.mainWindowHPanePosition)
        self.mainhpaned.set_position(self.settings.mainWindowMainHPanePosition)
        self.vpaned.set_position(self.settings.mainWindowVPanePosition)

        # Connect the main window's signals at the end, to avoid messing around
        # with the restoration of settings above.
        self.connect("delete-event", self._deleteCb)
        self.connect("configure-event", self._configureCb)

        # Focus the timeline by default!
        self.focusTimeline()
        self.updateTitle()

    def _setDefaultPositions(self):
        window_width = self.get_size()[0]
        if self.settings.mainWindowHPanePosition is None:
            self.settings.mainWindowHPanePosition = window_width / 3
        if self.settings.mainWindowMainHPanePosition is None:
            self.settings.mainWindowMainHPanePosition = 2 * window_width / 3
        if self.settings.mainWindowVPanePosition is None:
            screen_width = float(self.get_screen().get_width())
            screen_height = float(self.get_screen().get_height())
            req = self.vpaned.get_preferred_size()[0]
            if screen_width / screen_height < 0.75:
                # Tall screen, give some more vertical space the the tabs.
                value = req.height / 3
            else:
                value = req.height / 2
            self.settings.mainWindowVPanePosition = value

    def checkScreenConstraints(self):
        """Measures the approximate minimum size required by the main window.

        Shrinks some widgets to fit better on smaller screen resolutions.
        """
        # This code works, but keep in mind get_preferred_size's output
        # is only an approximation. As of 2015, GTK still does not have
        # a way, even with client-side decorations, to tell us the exact
        # minimum required dimensions of a window.
        min_size, natural_size = self.get_preferred_size()
        screen_width = self.get_screen().get_width()
        screen_height = self.get_screen().get_height()
        self.debug("Minimum UI size is %sx%s", min_size.width, min_size.height)
        self.debug("Screen size is %sx%s", screen_width, screen_height)
        if min_size.width >= 0.9 * screen_width:
            self.medialibrary.activateCompactMode()
            self.viewer.activateCompactMode()
            min_size, natural_size = self.get_preferred_size()
            self.info("Minimum UI size has been reduced to %sx%s",
                      min_size.width, min_size.height)

    def switchContextTab(self, ges_clip):
        """Activates the appropriate tab on the second set of tabs.

        Args:
            ges_clip (GES.SourceClip): The clip which has been focused.
        """
        if isinstance(ges_clip, GES.TitleClip):
            page = 2
        elif isinstance(ges_clip, GES.SourceClip):
            page = 0
        elif isinstance(ges_clip, GES.TransitionClip):
            page = 1
        else:
            self.warning("Unknown clip type: %s", ges_clip)
            return
        self.context_tabs.set_current_page(page)

    def focusTimeline(self):
        layers_representation = self.timeline_ui.timeline.layout
        # Check whether it has focus already, grab_focus always emits an event.
        if not layers_representation.props.is_focus:
            layers_representation.grab_focus()

    def _create_headerbar_buttons(self):
        undo_button = Gtk.Button.new_from_icon_name(
            "edit-undo-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        undo_button.set_always_show_image(True)
        undo_button.set_label(_("Undo"))
        undo_button.set_action_name("app.undo")
        undo_button.set_use_underline(True)

        redo_button = Gtk.Button.new_from_icon_name(
            "edit-redo-symbolic", Gtk.IconSize.LARGE_TOOLBAR)
        redo_button.set_always_show_image(True)
        redo_button.set_label(_("Redo"))
        redo_button.set_action_name("app.redo")
        redo_button.set_use_underline(True)

        separator = Gtk.Separator()

        self.save_button = Gtk.Button.new_from_icon_name(
            "document-save", Gtk.IconSize.LARGE_TOOLBAR)
        self.save_button.set_always_show_image(True)
        self.save_button.set_label(_("Save"))
        self.save_button.set_focus_on_click(False)

        render_icon = Gtk.Image.new_from_file(
            os.path.join(get_pixmap_dir(), "pitivi-render-24.png"))
        self.render_button = Gtk.Button()
        self.render_button.set_image(render_icon)
        self.render_button.set_always_show_image(True)
        self.render_button.set_label(_("Render"))
        self.render_button.set_tooltip_text(
            _("Export your project as a finished movie"))
        self.render_button.set_sensitive(False)  # The only one we have to set.
        self.render_button.connect("clicked", self._renderCb)

        self._headerbar.pack_start(undo_button)
        self._headerbar.pack_start(redo_button)
        self._headerbar.pack_start(separator)
        self._headerbar.pack_start(self.save_button)
        self._headerbar.pack_start(self.render_button)

    def _set_keyboard_shortcuts(self):
        self.app.shortcuts.register_group("win", _("Project"))
        self.save_action = Gio.SimpleAction.new("save", None)
        self.save_action.connect("activate", self._saveProjectCb)
        self.add_action(self.save_action)
        self.save_button.set_action_name("win.save")
        self.app.shortcuts.add("win.save", ["<Control>s"],
                               _("Save the current project"))

        self.new_project_action = Gio.SimpleAction.new("new-project", None)
        self.new_project_action.connect("activate", self._newProjectMenuCb)
        self.add_action(self.new_project_action)
        self.app.shortcuts.add("win.new-project", ["<Control>n"],
                               _("Create a new project"))

        self.open_project_action = Gio.SimpleAction.new("open-project", None)
        self.open_project_action.connect("activate", self._openProjectCb)
        self.add_action(self.open_project_action)
        self.app.shortcuts.add("win.open-project", ["<Control>o"],
                               _("Open a project"))

        self.save_as_action = Gio.SimpleAction.new("save-as", None)
        self.save_as_action.connect("activate", self._saveProjectAsCb)
        self.add_action(self.save_as_action)
        self.app.shortcuts.add("win.save-as", ["<Control><Shift>s"],
                               _("Save the current project as"))

        self.help_action = Gio.SimpleAction.new("help", None)
        self.help_action.connect("activate", self._userManualCb)
        self.add_action(self.help_action)
        self.app.shortcuts.add("win.help", ["F1"], _("Help"), group="app")

        self.menu_button_action = Gio.SimpleAction.new("menu-button", None)
        self.menu_button_action.connect("activate", self._menuCb)
        self.add_action(self.menu_button_action)
        self.app.shortcuts.add("win.menu-button", ["F10"],
                               _("Show the menu button content"),
                               group="app")

        import_asset_action = Gio.SimpleAction.new("import-asset", None)
        import_asset_action.connect("activate", self.__import_asset_cb)
        self.add_action(import_asset_action)
        self.app.shortcuts.add("win.import-asset", ["<Control>i"],
                               _("Add media files to your project"))

    def __import_asset_cb(self, unusdaction, unusedparam):
        self.medialibrary.show_import_assets_dialog()

    def showProjectStatus(self):
        project = self.app.project_manager.current_project
        dirty = project.hasUnsavedModifications()
        self.save_action.set_enabled(dirty)
        if project.uri:
            self._menubutton_items["menu_revert_to_saved"].set_sensitive(dirty)
        self.updateTitle()

# UI Callbacks

    def _configureCb(self, unused_widget, unused_event):
        """Saves the main window position and size."""
        # Takes window manager decorations into account.
        position = self.get_position()
        self.settings.mainWindowX = position.root_x
        self.settings.mainWindowY = position.root_y

        # Does not include the size of the window manager decorations.
        size = self.get_size()
        self.settings.mainWindowWidth = size.width
        self.settings.mainWindowHeight = size.height

    def _deleteCb(self, unused_widget, unused_data=None):
        self._saveWindowSettings()
        if not self.app.shutdown():
            return True

        return False

    def _saveWindowSettings(self):
        self.settings.mainWindowHPanePosition = self.secondhpaned.get_position(
        )
        self.settings.mainWindowMainHPanePosition = self.mainhpaned.get_position(
        )
        self.settings.mainWindowVPanePosition = self.vpaned.get_position()

    def _mediaLibraryPlayCb(self, unused_medialibrary, asset):
        """Previews the specified asset.

        If the media library item to preview is an image, show it in the user's
        favorite image viewer. Else, preview the video/sound in Pitivi.
        """
        # Technically, our preview widget can show images, but it's never going
        # to do a better job (sizing, zooming, metadata, editing, etc.)
        # than the user's favorite image viewer.
        if asset.is_image():
            subprocess.call(['xdg-open', str(path_from_uri(asset.get_id()))])
        else:
            preview_window = PreviewAssetWindow(asset, self)
            preview_window.preview()

    def _projectChangedCb(self, unused_project):
        self.save_action.set_enabled(True)
        self.updateTitle()

    def _builderConnectCb(self, builder, gobject, signal_name, handler_name,
                          connect_object, flags, user_data):
        id_ = gobject.connect(signal_name, getattr(self, handler_name))
        self.builder_handler_ids.append((gobject, id_))

# Toolbar/Menu actions callback

    def _newProjectMenuCb(self, unused_action, unused_param):
        self.app.project_manager.newBlankProject()

    def _openProjectCb(self, unused_action, unused_param):
        self.openProject()

    def _saveProjectCb(self, action, unused_param):
        if not self.app.project_manager.current_project.uri or self.app.project_manager.disable_save:
            self.saveProjectAs()
        else:
            self.app.project_manager.saveProject()

    def _saveProjectAsCb(self, unused_action, unused_param):
        self.saveProjectAs()

    def saveProject(self):
        self._saveProjectCb(None, None)

    def saveProjectAsDialog(self):
        self._saveProjectAsCb(None, None)

    def _revertToSavedProjectCb(self, unused_action):
        return self.app.project_manager.revertToSavedProject()

    def _exportProjectAsTarCb(self, unused_action):
        uri = self._showExportDialog(self.app.project_manager.current_project)
        result = None
        if uri:
            result = self.app.project_manager.exportProject(
                self.app.project_manager.current_project, uri)

        if not result:
            self.log("Project couldn't be exported")
        return result

    def _projectSettingsCb(self, unused_action):
        self.showProjectSettingsDialog()

    def showProjectSettingsDialog(self):
        project = self.app.project_manager.current_project
        dialog = ProjectSettingsDialog(self, project, self.app)
        dialog.window.run()
        self.updateTitle()

    def _menuCb(self, unused_action, unused_param):
        self._menubutton.set_active(not self._menubutton.get_active())

    def _userManualCb(self, unused_action, unused_param):
        show_user_manual()

    def _aboutResponseCb(self, dialog, unused_response):
        dialog.destroy()

    def _aboutCb(self, unused_action):
        abt = Gtk.AboutDialog()
        abt.set_program_name(APPNAME)
        abt.set_website(APPURL)

        if in_devel():
            version_str = _("Development version: %s" % GITVERSION)
        elif not self.app.isLatest():
            version_str = _("Version %(cur_ver)s — %(new_ver)s is available" %
                            {"cur_ver": GITVERSION,
                             "new_ver": self.app.getLatest()})
        else:
            version_str = _("Version %s" % GITVERSION)
        abt.set_version(version_str)

        comments = ["",
                    "GES %s" % ".".join(map(str, GES.version())),
                    "Gtk %s" % ".".join(map(str, (Gtk.MAJOR_VERSION, Gtk.MINOR_VERSION))),
                    "GStreamer %s" % ".".join(map(str, Gst.version()))]
        abt.set_comments("\n".join(comments))

        authors = [_("Current maintainers:"),
                   "Jean-François Fortin Tam <nekohayo@gmail.com>",
                   "Thibault Saunier <tsaunier@gnome.org>",
                   "Mathieu Duponchelle <mduponchelle1@gmail.com>",
                   "Alexandru Băluț <alexandru.balut@gmail.com>",
                   "",
                   _("Past maintainers:"),
                   "Edward Hervey <bilboed@bilboed.com>",
                   "Alessandro Decina <alessandro.decina@collabora.co.uk>",
                   "Brandon Lewis <brandon_lewis@berkeley.edu>",
                   "",
                   # Translators: this paragraph is to be translated, the list
                   # of contributors is shown dynamically as a clickable link
                   # below it
                   _("Contributors:\n" +
                     "A handwritten list here would...\n" +
                     "• be too long,\n" +
                     "• be frequently outdated,\n" +
                     "• not show their relative merit.\n\n" +
                     "Out of respect for our contributors, we point you instead to:\n"),
                   # Translators: keep the %s at the end of the 1st line
                   _("The list of contributors on Ohloh %s\n" +
                     "Or you can run: git shortlog -s -n")
                   % "http://ohloh.net/p/pitivi/contributors", ]
        abt.set_authors(authors)
        translators = _("translator-credits")
        if translators != "translator-credits":
            abt.set_translator_credits(translators)
        documenters = ["Jean-François Fortin Tam <nekohayo@gmail.com>", ]
        abt.set_documenters(documenters)
        abt.set_license_type(Gtk.License.LGPL_2_1)
        abt.set_icon_name("pitivi")
        abt.set_logo_icon_name("pitivi")
        abt.connect("response", self._aboutResponseCb)
        abt.set_transient_for(self)
        abt.show()

    def openProject(self):
        # Requesting project closure at this point in time prompts users about
        # unsaved changes (if any); much better than having ProjectManager
        # trigger this *after* the user already chose a new project to load...
        if not self.app.project_manager.closeRunningProject():
            return  # The user has not made a decision, don't do anything

        chooser = Gtk.FileChooserDialog(title=_("Open File..."),
                                        transient_for=self,
                                        action=Gtk.FileChooserAction.OPEN)
        chooser.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL,
                            _("Open"), Gtk.ResponseType.OK)
        chooser.set_default_response(Gtk.ResponseType.OK)
        chooser.set_select_multiple(False)
        # TODO: Remove this set_current_folder call when GTK bug 683999 is
        # fixed
        chooser.set_current_folder(self.settings.lastProjectFolder)
        formatter_assets = GES.list_assets(GES.Formatter)
        formatter_assets.sort(
            key=lambda x: - x.get_meta(GES.META_FORMATTER_RANK))
        for format_ in formatter_assets:
            filt = Gtk.FileFilter()
            filt.set_name(format_.get_meta(GES.META_DESCRIPTION))
            filt.add_pattern("*%s" %
                             format_.get_meta(GES.META_FORMATTER_EXTENSION))
            chooser.add_filter(filt)
        default = Gtk.FileFilter()
        default.set_name(_("All supported formats"))
        default.add_custom(Gtk.FileFilterFlags.URI, self._canLoadUri, None)
        chooser.add_filter(default)

        response = chooser.run()
        uri = chooser.get_uri()
        chooser.destroy()
        if response == Gtk.ResponseType.OK:
            self.app.project_manager.loadProject(uri)
        else:
            self.info("User cancelled loading a new project")
            self.app.welcome_wizard.show()

    def _canLoadUri(self, filterinfo, unused_uri):
        try:
            return GES.Formatter.can_load_uri(filterinfo.uri)
        except:
            return False

    def _prefsCb(self, unused_action):
        PreferencesDialog(self.app).run()

# Project management callbacks

    def _projectManagerNewProjectLoadedCb(self, project_manager, project):
        """Starts connecting the UI to the specified project.

        Args:
            project_manager (ProjectManager): The project manager.
            project (Project): The project which has been loaded.
        """
        self.log("A new project has been loaded")
        self._connectToProject(project)
        project.pipeline.activatePositionListener()
        self._setProject(project)

        self.updateTitle()

        if project_manager.disable_save is True:
            # Special case: we enforce "Save as", but the normal "Save" button
            # redirects to it if needed, so we still want it to be enabled:
            self.save_action.set_enabled(True)

        if project.ges_timeline.props.duration != 0:
            self.render_button.set_sensitive(True)

    def _projectManagerNewProjectLoadingCb(self, unused_project_manager, project):
        uri = project.get_uri()
        if uri:
            self.recent_manager.add_item(uri)
        self.log("A NEW project is loading, deactivate UI")

    def _projectManagerSaveProjectFailedCb(self, unused_project_manager, uri, exception=None):
        project_filename = unquote(uri.split("/")[-1])
        dialog = Gtk.MessageDialog(transient_for=self,
                                   modal=True,
                                   message_type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.OK,
                                   text=_('Unable to save project "%s"') % project_filename)
        if exception:
            dialog.set_property("secondary-use-markup", True)
            dialog.set_property("secondary-text", unquote(str(exception)))
        dialog.set_transient_for(self)
        dialog.run()
        dialog.destroy()
        self.error("failed to save project")

    def _projectManagerProjectSavedCb(self, unused_project_manager, project, uri):
        # FIXME GES: Reimplement Undo/Redo
        # self.app.action_log.checkpoint()
        self.updateTitle()

        self.save_action.set_enabled(False)
        if uri:
            self.recent_manager.add_item(uri)

        if project.uri is None:
            project.uri = uri

    def _projectManagerClosingProjectCb(self, project_manager, project):
        """Investigates whether it's possible to close the specified project.

        Args:
            project_manager (ProjectManager): The project manager.
            project (Project): The project which has been closed.

        Returns:
            bool: True when it's OK to close it, False when the user chooses
                to cancel the closing operation.
        """
        if not project.hasUnsavedModifications():
            return True

        if project.uri and not project_manager.disable_save:
            save = _("Save")
        else:
            save = _("Save as...")

        dialog = Gtk.Dialog(title="", transient_for=self, modal=True)
        dialog.add_buttons(_("Close without saving"), Gtk.ResponseType.REJECT,
                           _("Cancel"), Gtk.ResponseType.CANCEL,
                           save, Gtk.ResponseType.YES)
        # Even though we set the title to an empty string when creating dialog,
        # seems we really have to do it once more so it doesn't show
        # "pitivi"...
        dialog.set_resizable(False)
        dialog.set_default_response(Gtk.ResponseType.CANCEL)
        dialog.get_accessible().set_name("unsaved changes dialog")

        primary = Gtk.Label()
        primary.set_line_wrap(True)
        primary.set_use_markup(True)
        primary.set_alignment(0, 0.5)

        message = _("Save changes to the current project before closing?")
        primary.set_markup("<span weight=\"bold\">" + message + "</span>")

        secondary = Gtk.Label()
        secondary.set_line_wrap(True)
        secondary.set_use_markup(True)
        secondary.set_alignment(0, 0.5)

        if project.uri:
            path = unquote(project.uri).split("file://")[1]
            last_saved = max(
                os.path.getmtime(path), project_manager.time_loaded)
            time_delta = time() - last_saved
            secondary.props.label = _("If you don't save, "
                                      "the changes from the last %s will be lost."
                                      % beautify_time_delta(time_delta))
        else:
            secondary.props.label = _("If you don't save, "
                                      "your changes will be lost.")

        # put the text in a vbox
        vbox = Gtk.Box(homogeneous=False, spacing=SPACING * 2)
        vbox.set_orientation(Gtk.Orientation.VERTICAL)
        vbox.pack_start(primary, True, True, 0)
        vbox.pack_start(secondary, True, True, 0)

        # make the [[image] text] hbox
        image = Gtk.Image.new_from_icon_name(
            "dialog-question", Gtk.IconSize.DIALOG)
        hbox = Gtk.Box(homogeneous=False, spacing=SPACING * 2)
        hbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        hbox.pack_start(image, False, False, 0)
        hbox.pack_start(vbox, True, True, 0)
        hbox.set_border_width(SPACING)

        # stuff the hbox in the dialog
        content_area = dialog.get_content_area()
        content_area.pack_start(hbox, True, True, 0)
        content_area.set_spacing(SPACING * 2)
        hbox.show_all()

        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            if project.uri is not None and project_manager.disable_save is False:
                res = self.app.project_manager.saveProject()
            else:
                res = self.saveProjectAs()
        elif response == Gtk.ResponseType.REJECT:
            res = True
        else:
            res = False

        return res

    def _projectManagerProjectClosedCb(self, unused_project_manager, project):
        """Starts disconnecting the UI from the specified project.

        This happens when the user closes the app or asks to load another
        project, immediately after the user confirmed that unsaved changes,
        if any, can be discarded but before the filechooser to pick the next
        project to load appears.

        Args:
            project (Project): The project which has been closed.
        """

        # We must disconnect from the project pipeline before it is released:
        if project.pipeline is not None:
            project.pipeline.deactivatePositionListener()

        self.info("Project closed")
        self.updateTitle()
        if project.loaded:
            self._disconnectFromProject(project)
        self.timeline_ui.setProject(None)
        self.render_button.set_sensitive(False)
        return False

    def _projectManagerRevertingToSavedCb(self, unused_project_manager, unused_project):
        if self.app.project_manager.current_project.hasUnsavedModifications():
            dialog = Gtk.MessageDialog(transient_for=self,
                                       modal=True,
                                       message_type=Gtk.MessageType.WARNING,
                                       buttons=Gtk.ButtonsType.NONE,
                                       text=_("Revert to saved project version?"))
            dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.NO,
                               Gtk.STOCK_REVERT_TO_SAVED, Gtk.ResponseType.YES)
            dialog.set_resizable(False)
            dialog.set_property("secondary-text",
                                _("This will reload the current project. All unsaved changes will be lost."))
            dialog.set_default_response(Gtk.ResponseType.NO)
            dialog.set_transient_for(self)
            response = dialog.run()
            dialog.destroy()
            if response != Gtk.ResponseType.YES:
                return False
        return True

    def _projectManagerNewProjectFailedCb(self, unused_project_manager, uri, reason):
        project_filename = unquote(uri.split("/")[-1])
        dialog = Gtk.MessageDialog(transient_for=self,
                                   modal=True,
                                   message_type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.OK,
                                   text=_('Unable to load project "%s"') % project_filename)
        dialog.set_property("secondary-use-markup", True)
        dialog.set_property("secondary-text", unquote(str(reason)))
        dialog.set_transient_for(self)
        dialog.run()
        dialog.destroy()
        self.app.welcome_wizard.show()

    def _projectManagerMissingUriCb(self, project_manager, project, unused_error, asset):
        if project.at_least_one_asset_missing:
            # One asset is already missing so no point in spamming the user
            # with more file-missing dialogs, as we need all of them.
            return None

        uri = asset.get_id()
        dialog = Gtk.Dialog(title=_("Locate missing file..."),
                            transient_for=self,
                            modal=True)

        dialog.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL,
                           _("Open"), Gtk.ResponseType.OK)
        dialog.set_border_width(SPACING * 2)
        dialog.get_content_area().set_spacing(SPACING)
        dialog.set_transient_for(self)
        dialog.set_default_response(Gtk.ResponseType.OK)

        # This box will contain the label and optionally a thumbnail
        hbox = Gtk.Box()
        hbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        hbox.set_spacing(SPACING)

        # Check if we have a thumbnail available.
        # This can happen if the file was moved or deleted by an application
        # that does not manage Freedesktop thumbnails. The user is in luck!
        # This is based on medialibrary's addDiscovererInfo method.
        thumbnail_hash = md5(uri.encode()).hexdigest()
        thumb_dir = os.path.expanduser("~/.thumbnails/normal/")
        thumb_path_normal = thumb_dir + thumbnail_hash + ".png"
        if os.path.exists(thumb_path_normal):
            self.debug("A thumbnail file was found for %s", uri)
            thumbnail = Gtk.Image.new_from_file(thumb_path_normal)
            thumbnail.set_padding(0, SPACING)
            hbox.pack_start(thumbnail, False, False, 0)

        # TODO: display the filesize to help the user identify the file
        if asset.get_duration() == Gst.CLOCK_TIME_NONE:
            # The file is probably an image, not video or audio.
            text = _('The following file has moved: "<b>%s</b>"'
                     '\nPlease specify its new location:'
                     % info_name(asset))
        else:
            length = beautify_length(asset.get_duration())
            text = _('The following file has moved: "<b>%s</b>" (duration: %s)'
                     '\nPlease specify its new location:'
                     % (info_name(asset), length))

        label = Gtk.Label()
        label.set_markup(text)
        hbox.pack_start(label, False, False, 0)
        dialog.get_content_area().pack_start(hbox, False, False, 0)
        hbox.show_all()

        chooser = Gtk.FileChooserWidget(action=Gtk.FileChooserAction.OPEN)
        chooser.set_select_multiple(False)
        previewer = PreviewWidget(self.settings)
        chooser.set_preview_widget(previewer)
        chooser.set_use_preview_label(False)
        chooser.connect('update-preview', previewer.update_preview_cb)
        chooser.set_current_folder(self.settings.lastProjectFolder)
        # Use a Gtk FileFilter to only show files with the same extension
        # Note that splitext gives us the extension with the ".", no need to
        # add it inside the filter string.
        unused_filename, extension = os.path.splitext(uri)
        filter_ = Gtk.FileFilter()
        # Translators: this is a format filter in a filechooser. Ex: "AVI
        # files"
        filter_.set_name(_("%s files" % extension))
        filter_.add_pattern("*%s" % extension.lower())
        filter_.add_pattern("*%s" % extension.upper())
        default = Gtk.FileFilter()
        default.set_name(_("All files"))
        default.add_pattern("*")
        chooser.add_filter(filter_)
        chooser.add_filter(default)
        dialog.get_content_area().pack_start(chooser, True, True, 0)
        chooser.show()

        # If the window is too big, the window manager will resize it so that
        # it fits on the screen.
        dialog.set_default_size(1024, 1000)
        response = dialog.run()

        new_uri = None
        if response == Gtk.ResponseType.OK:
            self.log("User chose a new URI for the missing file")
            new_uri = chooser.get_uri()
        else:
            dialog.hide()

            if not self.app.proxy_manager.checkProxyLoadingSucceeded(asset):
                # Reset the project manager and disconnect all the signals.
                project_manager.closeRunningProject()
                # Signal the project loading failure.
                # You have to do this *after* successfully creating a blank project,
                # or the startupwizard will still be connected to that signal too.
                reason = _('No replacement file was provided for "<i>%s</i>".\n\n'
                           'Pitivi does not currently support partial projects.'
                           % info_name(asset))
                project_manager.emit("new-project-failed", project.uri, reason)

        dialog.destroy()
        return new_uri

    def _connectToProject(self, project):
        # FIXME GES we should re-enable this when possible
        # medialibrary.connect("missing-plugins", self._sourceListMissingPluginsCb)
        project.connect("project-changed", self._projectChangedCb)
        project.connect(
            "rendering-settings-changed", self._renderingSettingsChangedCb)
        project.ges_timeline.connect("notify::duration",
                                     self._timelineDurationChangedCb)

# Missing Plugins Support

    def _sourceListMissingPluginsCb(
        self, unused_project, unused_uri, unused_factory,
            details, unused_descriptions, missingPluginsCallback):
        res = self._installPlugins(details, missingPluginsCallback)
        return res

    def _installPlugins(self, details, missingPluginsCallback):
        context = GstPbutils.InstallPluginsContext()
        if self.app.system.has_x11():
            context.set_xid(self.window.xid)

        res = GstPbutils.install_plugins_async(details, context,
                                               missingPluginsCallback)
        return res

# Pitivi current project callbacks

    def _setProject(self, project):
        """Disconnects and then reconnects callbacks to the specified project.

        Args:
            project (Project): The new current project.
        """
        if not project:
            self.warning("Current project instance does not exist")
            return False

        self.viewer.setPipeline(project.pipeline)
        self._renderingSettingsChangedCb(project)
        self.clipconfig.project = project

        # When creating a blank project there's no project URI yet.
        if project.uri:
            folder_path = os.path.dirname(path_from_uri(project.uri))
            self.settings.lastProjectFolder = folder_path

    def _disconnectFromProject(self, project):
        project.disconnect_by_func(self._projectChangedCb)
        project.disconnect_by_func(self._renderingSettingsChangedCb)
        project.ges_timeline.disconnect_by_func(self._timelineDurationChangedCb)

# Pitivi current project callbacks

    def _renderingSettingsChangedCb(self, project, unused_item=None, unused_value=None):
        """Resets the viewer aspect ratio."""
        self.viewer.setDisplayAspectRatio(project.getDAR())
        self.viewer.timecode_entry.setFramerate(project.videorate)

    def _timelineDurationChangedCb(self, timeline, unused_duration):
        """Updates the render button.

        This covers the case when a clip is inserted into a blank timeline.
        This callback is not triggered by loading a project.
        """
        duration = timeline.get_duration()
        self.debug("Timeline duration changed to %s", duration)
        self.render_button.set_sensitive(duration > 0)

# other

    def _showExportDialog(self, project):
        self.log("Export requested")
        chooser = Gtk.FileChooserDialog(title=_("Export To..."),
                                        transient_for=self,
                                        action=Gtk.FileChooserAction.SAVE)
        chooser.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL,
                            _("Save"), Gtk.ResponseType.OK)
        chooser.set_default_response(Gtk.ResponseType.OK)

        chooser.set_select_multiple(False)
        chooser.props.do_overwrite_confirmation = True

        asset = GES.Formatter.get_default()
        asset_extension = asset.get_meta(GES.META_FORMATTER_EXTENSION)

        if not project.name:
            chooser.set_current_name(
                _("Untitled") + "." + asset_extension + "_tar")
        else:
            chooser.set_current_name(
                project.name + "." + asset_extension + "_tar")

        filt = Gtk.FileFilter()
        filt.set_name(_("Tar archive"))
        filt.add_pattern("*.%s_tar" % asset_extension)
        chooser.add_filter(filt)
        default = Gtk.FileFilter()
        default.set_name(_("Detect automatically"))
        default.add_pattern("*")
        chooser.add_filter(default)

        response = chooser.run()
        if response == Gtk.ResponseType.OK:
            self.log("User chose a URI to export project to")
            # need to do this to work around bug in Gst.uri_construct
            # which escapes all /'s in path!
            uri = "file://" + chooser.get_filename()
            self.log("uri: %s", uri)
            ret = uri
        else:
            self.log("User didn't choose a URI to export project to")
            ret = None

        chooser.destroy()
        return ret

    def saveProjectAs(self):
        uri = self._showSaveAsDialog()
        if uri is None:
            return False
        return self.app.project_manager.saveProject(uri)

    def _showSaveAsDialog(self):
        self.log("Save URI requested")
        chooser = Gtk.FileChooserDialog(title=_("Save As..."),
                                        transient_for=self,
                                        action=Gtk.FileChooserAction.SAVE)
        chooser.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL,
                            _("Save"), Gtk.ResponseType.OK)
        chooser.set_default_response(Gtk.ResponseType.OK)
        asset = GES.Formatter.get_default()
        filt = Gtk.FileFilter()
        filt.set_name(asset.get_meta(GES.META_DESCRIPTION))
        filt.add_pattern("*.%s" % asset.get_meta(GES.META_FORMATTER_EXTENSION))
        chooser.add_filter(filt)

        chooser.set_select_multiple(False)
        chooser.set_current_name(_("Untitled") + "." +
                                 asset.get_meta(GES.META_FORMATTER_EXTENSION))
        chooser.set_current_folder(self.settings.lastProjectFolder)
        chooser.props.do_overwrite_confirmation = True

        default = Gtk.FileFilter()
        default.set_name(_("Detect automatically"))
        default.add_pattern("*")
        chooser.add_filter(default)

        response = chooser.run()
        if response == Gtk.ResponseType.OK:
            self.log("User chose a URI to save project to")
            # need to do this to work around bug in Gst.uri_construct
            # which escapes all /'s in path!
            uri = "file://" + chooser.get_filename()
            file_filter = chooser.get_filter().get_name()
            self.log("uri:%s , filter:%s", uri, file_filter)
            self.settings.lastProjectFolder = chooser.get_current_folder()
            ret = uri
        else:
            self.log("User didn't choose a URI to save project to")
            ret = None

        chooser.destroy()
        return ret

    def _screenshotCb(self, unused_action):
        """Exports a snapshot of the current frame as an image file."""
        foo = self._showSaveScreenshotDialog()
        if foo:
            path, mime = foo[0], foo[1]
            self.app.project_manager.current_project.pipeline.save_thumbnail(
                -1, -1, mime, path)

    def _showSaveScreenshotDialog(self):
        """Asks the user where to save the current frame.

        Returns:
            List[str]: The full path and the mimetype if successful, None otherwise.
        """
        chooser = Gtk.FileChooserDialog(title=_("Save As..."),
                                        transient_for=self, action=Gtk.FileChooserAction.SAVE)
        chooser.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL,
                            _("Save"), Gtk.ResponseType.OK)
        chooser.set_default_response(Gtk.ResponseType.OK)
        chooser.set_select_multiple(False)
        chooser.set_current_name(_("Untitled"))
        chooser.props.do_overwrite_confirmation = True
        formats = {_("PNG image"): ["image/png", ("png",)],
                   _("JPEG image"): ["image/jpeg", ("jpg", "jpeg")]}
        for format in formats:
            filt = Gtk.FileFilter()
            filt.set_name(format)
            filt.add_mime_type(formats.get(format)[0])
            chooser.add_filter(filt)
        response = chooser.run()
        if response == Gtk.ResponseType.OK:
            chosen_format = formats.get(chooser.get_filter().get_name())
            chosen_ext = chosen_format[1][0]
            chosen_mime = chosen_format[0]
            uri = os.path.join(
                chooser.get_current_folder(), chooser.get_filename())
            ret = ["%s.%s" % (uri, chosen_ext), chosen_mime]
        else:
            ret = None
        chooser.destroy()
        return ret

    def updateTitle(self):
        project = self.app.project_manager.current_project
        if project:
            if project.name:
                name = project.name
            else:
                name = _("Untitled")
            unsaved_mark = ""
            if project.hasUnsavedModifications():
                unsaved_mark = "*"
            title = "%s%s — %s" % (unsaved_mark, name, APPNAME)
        else:
            title = APPNAME
        event_box = Gtk.EventBox()
        label = Gtk.Label()
        clear_styles(label)
        label.set_text(title)
        event_box.add(label)
        event_box.show_all()
        event_box.connect("button-press-event", self.__titleClickCb, project)
        self._headerbar.set_custom_title(event_box)
        self.set_title(title)

    def __titleClickCb(self, unused_widget, unused_event, project):
        entry = Gtk.Entry()
        entry.set_width_chars(100)
        entry.set_margin_left(SPACING)
        entry.set_margin_right(SPACING)
        entry.show()
        entry.set_text(project.name)
        self._headerbar.set_custom_title(entry)
        if project.hasDefaultName():
            entry.grab_focus()
        else:
            entry.grab_focus_without_selecting()
        entry.connect("focus-out-event", self.__titleChangedCb, project)
        entry.connect("key_release_event", self.__titleTypeCb, project)

    def __titleChangedCb(self, widget, event, project):
        if not event.window:
            # Workaround https://bugzilla.gnome.org/show_bug.cgi?id=757036
            return
        name = widget.get_text()
        if project.name == name:
            self.updateTitle()
        else:
            project.name = name

    def __titleTypeCb(self, widget, event, project):
        if event.keyval == Gdk.KEY_Return:
            self.focusTimeline()
            return True
        elif event.keyval == Gdk.KEY_Escape:
            widget.set_text(project.name)
            self.focusTimeline()
            return True
        return False


class PreviewAssetWindow(Gtk.Window):
    """Window for previewing a video or audio asset.

    Args:
        asset (GES.UriClipAsset): The asset to be previewed.
        main_window (MainWindow): The main window.
    """

    def __init__(self, asset, main_window):
        Gtk.Window.__init__(self)
        self._asset = asset
        self._main_window = main_window

        self.set_title(_("Preview"))
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_transient_for(main_window)

        self._previewer = PreviewWidget(main_window.settings, minimal=True)
        self.add(self._previewer)
        self._previewer.previewUri(self._asset.get_id())
        self._previewer.show()

        self.connect("focus-out-event", self._leavePreviewCb)
        self.connect("key-press-event", self._keyPressCb)

    def preview(self):
        """Shows the window and starts the playback."""
        width, height = self._calculatePreviewWindowSize()
        self.resize(width, height)
        # Setting the position of the window only works if it's currently hidden
        # otherwise, after the resize the position will not be readjusted
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.show()

        self._previewer.play()
        # Hack so that we really really force the "utility" window to be
        # focused
        self.present()

    def _calculatePreviewWindowSize(self):
        info = self._asset.get_info()
        video_streams = info.get_video_streams()
        if not video_streams:
            # There is no video/image stream. This is an audio file.
            # Resize to the minimum and let the window manager deal with it.
            return 1, 1
        # For videos and images, automatically resize the window
        # Try to keep it 1:1 if it can fit within 85% of the parent window
        video = video_streams[0]
        img_width = video.get_width()
        img_height = video.get_height()
        mainwindow_width, mainwindow_height = self._main_window.get_size()
        max_width = 0.85 * mainwindow_width
        max_height = 0.85 * mainwindow_height

        controls_height = self._previewer.bbox.get_preferred_size()[0].height
        if img_width < max_width and (img_height + controls_height) < max_height:
            # The video is small enough, keep it 1:1
            return img_width, img_height + controls_height
        else:
            # The video is too big, size it down
            # TODO: be smarter, figure out which (width, height) is bigger
            new_height = max_width * img_height / img_width
            return int(max_width), int(new_height + controls_height)

    def _leavePreviewCb(self, window, unused):
        self.destroy()
        return True

    def _keyPressCb(self, unused_widget, event):
        if event.keyval in (Gdk.KEY_Escape, Gdk.KEY_Q, Gdk.KEY_q):
            self.destroy()
        elif event.keyval == Gdk.KEY_space:
            self._previewer.togglePlayback()
        return True
