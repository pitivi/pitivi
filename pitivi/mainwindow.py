# -*- coding: utf-8 -*-
# PiTiVi , Non-linear video editor
#
#       ui/mainwindow.py
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
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

"""
Main GTK+ window
"""

import os

from time import time
from urllib import unquote
from gettext import gettext as _
from hashlib import md5

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Gst
from gi.repository import GES
from gi.repository import GObject
from gi.repository import GdkPixbuf
from gi.repository.GstPbutils import InstallPluginsContext, install_plugins_async

from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import in_devel
from pitivi.settings import GlobalSettings
from pitivi.effects import EffectListWidget
from pitivi.transitions import TransitionsListWidget
from pitivi.medialibrary import MediaLibraryWidget, MediaLibraryError
from pitivi.titleeditor import TitleEditor
from pitivi.utils.misc import show_user_manual, path_from_uri
from pitivi.utils.ui import info_name, beautify_time_delta, SPACING,\
        FILESOURCE_TARGET_ENTRY, URI_TARGET_ENTRY, TYPE_URI_LIST, \
        TYPE_PITIVI_FILESOURCE
from pitivi.timeline.timeline import Timeline
from pitivi.viewer import PitiviViewer
from pitivi.tabsmanager import BaseTabs
from pitivi.mediafilespreviewer import PreviewWidget
from pitivi.clipproperties import ClipProperties
from pitivi.configure import pitivi_version, APPNAME, APPURL, \
     get_pixmap_dir, get_ui_dir


GlobalSettings.addConfigOption("fileSupportEnabled",
    environment="PITIVI_FILE_SUPPORT",
    default=False)

GlobalSettings.addConfigSection("main-window")
GlobalSettings.addConfigOption('mainWindowFullScreen',
    section="main-window",
    key="full-screen",
    default=False)
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
    default=200)
GlobalSettings.addConfigOption('mainWindowWidth',
    section="main-window",
    key="width",
    type_=int)
GlobalSettings.addConfigOption('mainWindowHeight',
    section="main-window",
    key="height",
    type_=int)
GlobalSettings.addConfigOption('lastProjectFolder',
    section="main-window",
    key="last-folder",
    environment="PITIVI_PROJECT_FOLDER",
    default=os.path.expanduser("~"))
GlobalSettings.addConfigOption('mainWindowShowMainToolbar',
    section="main-window",
    key="show-main-toolbar",
    default=True)
GlobalSettings.addConfigOption('mainWindowShowTimelineToolbar',
    section="main-window",
    key="show-timeline-toolbar",
    default=True)
GlobalSettings.addConfigSection('export')
GlobalSettings.addConfigOption('lastExportFolder',
                                section='export',
                                key="last-export-folder",
                                environment="PITIVI_EXPORT_FOLDER",
                                default=os.path.expanduser("~"))
GlobalSettings.addConfigOption('elementSettingsDialogWidth',
    section='export',
    key='element-settings-dialog-width',
    default=620)
GlobalSettings.addConfigOption('elementSettingsDialogHeight',
    section='export',
    key='element-settings-dialog-height',
    default=460)
GlobalSettings.addConfigSection("effect-configuration")
GlobalSettings.addConfigOption('effectVPanedPosition',
    section='effect-configuration',
    key='effect-vpaned-position',
    type_=int)
GlobalSettings.addConfigSection("version")
GlobalSettings.addConfigOption('displayCounter',
    section='version',
    key='info-displayed-counter',
    default=0)
GlobalSettings.addConfigOption('lastCurrentVersion',
    section='version',
    key='last-current-version',
    default='')


#FIXME Hacky, reimplement when avalaible in GES
formats = [(None, _("PiTiVi native (XML)"), ('xptv',))]

# FIXME PyGi to get stock_add working
Gtk.stock_add = lambda items: None


def create_stock_icons():
    """ Creates the pitivi-only stock icons """
    Gtk.stock_add([
            ('pitivi-render', _('Render'), 0, 0, 'pitivi'),
            ('pitivi-split', _('Split'), 0, 0, 'pitivi'),
            ('pitivi-keyframe', _('Keyframe'), 0, 0, 'pitivi'),
            ('pitivi-unlink', _('Unlink'), 0, 0, 'pitivi'),
            # Translators: This is an action, the title of a button
            ('pitivi-link', _('Link'), 0, 0, 'pitivi'),
            ('pitivi-ungroup', _('Ungroup'), 0, 0, 'pitivi'),
            # Translators: This is an action, the title of a button
            ('pitivi-group', _('Group'), 0, 0, 'pitivi'),
            ('pitivi-align', _('Align'), 0, 0, 'pitivi'),
            ])
    pixmaps = {
        "pitivi-render": "pitivi-render-24.png",
        "pitivi-split": "pitivi-split-24.svg",
        "pitivi-keyframe": "pitivi-keyframe-24.svg",
        "pitivi-unlink": "pitivi-unlink-24.svg",
        "pitivi-link": "pitivi-relink-24.svg",
        "pitivi-ungroup": "pitivi-ungroup-24.svg",
        "pitivi-group": "pitivi-group-24.svg",
        "pitivi-align": "pitivi-align-24.svg",
    }
    factory = Gtk.IconFactory()
    pmdir = get_pixmap_dir()
    for stockid, path in pixmaps.iteritems():
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(os.path.join(pmdir, path))
        iconset = Gtk.IconSet(pixbuf)
        factory.add(stockid, iconset)
        factory.add_default()


class PitiviMainWindow(Gtk.Window, Loggable):
    """
    Pitivi's main window.

    @cvar app: The application object
    @type app: L{Application}
    @cvar project: The current project
    @type project: L{Project}
    """
    def __init__(self, instance, allow_full_screen=True):
        """ initialize with the Pitivi object """
        gtksettings = Gtk.Settings.get_default()
        gtksettings.set_property("gtk-application-prefer-dark-theme", True)
        # Pulseaudio "role" (http://0pointer.de/blog/projects/tagging-audio.htm)
        os.environ["PULSE_PROP_media.role"] = "production"
        os.environ["PULSE_PROP_application.icon_name"] = "pitivi"

        Gtk.Window.__init__(self)
        Loggable.__init__(self, "mainwindow")
        self.app = instance
        self.log("Creating MainWindow")
        self.settings = instance.settings
        self.is_fullscreen = False
        self.prefsdialog = None
        create_stock_icons()
        self._setActions(instance)
        self._createUi(instance, allow_full_screen)
        self.recent_manager = Gtk.RecentManager()
        self._zoom_duration_changed = False
        self._missingUriOnLoading = False

        self.app.projectManager.connect("new-project-loading",
                self._projectManagerNewProjectLoadingCb)
        self.app.projectManager.connect("new-project-loaded",
                self._projectManagerNewProjectLoadedCb)
        self.app.projectManager.connect("new-project-failed",
                self._projectManagerNewProjectFailedCb)
        self.app.projectManager.connect("save-project-failed",
                self._projectManagerSaveProjectFailedCb)
        self.app.projectManager.connect("project-saved",
                self._projectManagerProjectSavedCb)
        self.app.projectManager.connect("closing-project",
                self._projectManagerClosingProjectCb)
        self.app.projectManager.connect("reverting-to-saved",
                self._projectManagerRevertingToSavedCb)
        self.app.projectManager.connect("project-closed",
                self._projectManagerProjectClosedCb)
        self.app.projectManager.connect("missing-uri",
                self._projectManagerMissingUriCb)

        self.app.action_log.connect("commit", self._actionLogCommit)
        self.app.action_log.connect("undo", self._actionLogUndo)
        self.app.action_log.connect("redo", self._actionLogRedo)
        self.app.action_log.connect("cleaned", self._actionLogCleaned)

    def showRenderDialog(self, project):
        """
        Shows the L{RenderDialog} for the given project Timeline.

        @param project: The project
        @type project: L{Project}
        """
        from pitivi.render import RenderDialog

        dialog = RenderDialog(self.app, project)
        dialog.window.connect("destroy", self._renderDialogDestroyCb)
        self.set_sensitive(False)
        dialog.window.show()

    def _renderDialogDestroyCb(self, unused_dialog):
        self.set_sensitive(True)

    def _renderCb(self, unused_button):
        self.showRenderDialog(self.app.current)

    def _setActions(self, instance):
        """
        Sets up the GtkActions. This allows managing the sensitivity of widgets
        to the mouse and keyboard shortcuts.
        """
        # Action list items can vary in size (1-6 items). The first one is the
        # name, and it is the only mandatory option. All the other options are
        # optional, and if omitted will default to None.
        #
        # name (required), stock ID, translatable label,
        # keyboard shortcut, translatable tooltip, callback function
        actions = [
            # In some cases we manually specify the translatable label,
            # because we want to have the "..." at the end, indicating
            # an action that requires "further interaction" from the user.
            ("NewProject", Gtk.STOCK_NEW, None,
            None, _("Create a new project"), self._newProjectMenuCb),

            ("OpenProject", Gtk.STOCK_OPEN, _("_Open..."),
            None, _("Open an existing project"), self._openProjectCb),

            ("SaveProject", Gtk.STOCK_SAVE, None,
            None, _("Save the current project"), self._saveProjectCb),

            ("SaveProjectAs", Gtk.STOCK_SAVE_AS, _("Save _As..."),
            None, _("Save the current project"), self._saveProjectAsCb),

            ("RevertToSavedProject", Gtk.STOCK_REVERT_TO_SAVED, None,
            None, _("Reload the current project"), self._revertToSavedProjectCb),

            ("ExportProject", Gtk.STOCK_HARDDISK, _("Export as Archive..."),
            None, _("Export the current project"), self._exportProjectAsTarCb),

            ("ProjectSettings", Gtk.STOCK_PROPERTIES, _("Project Settings"),
            None, _("Edit the project settings"), self._projectSettingsCb),

            ("RenderProject", 'pitivi-render', _("_Render..."),
            None, _("Export your project as a finished movie"), self._renderCb),

            ("Undo", Gtk.STOCK_UNDO, None,
            "<Ctrl>Z", _("Undo the last operation"), self._undoCb),

            ("Redo", Gtk.STOCK_REDO, None,
            "<Ctrl>Y", _("Redo the last operation that was undone"), self._redoCb),

            ("Preferences", Gtk.STOCK_PREFERENCES, None,
            None, None, self._prefsCb),

            ("RemoveLayer", Gtk.STOCK_REMOVE, _("Remove layer"),
             None, _("Remove the selected layer from the project"), self._removeLayerCb),

            ("Quit", Gtk.STOCK_QUIT, None, None, None, self._quitCb),

            ("About", Gtk.STOCK_ABOUT, None,
            None, _("Information about %s") % APPNAME, self._aboutCb),

            ("UserManual", Gtk.STOCK_HELP, _("User Manual"),
             "F1", None, self._userManualCb),

            # Set up the toplevel menu items for translation
            ("File", None, _("_Project")),
            ("Edit", None, _("_Edit")),
            ("View", None, _("_View")),
            ("Library", None, _("_Library")),
            ("Timeline", None, _("_Timeline")),
            ("Viewer", None, _("Previe_w")),
            ("Help", None, _("_Help")),
        ]

        toggleactions = [
            ("FullScreen", Gtk.STOCK_FULLSCREEN, None,
            "F11", _("View the main window on the whole screen"), self._fullScreenCb),

            ("ShowHideMainToolbar", None, _("Main Toolbar"),
            None, None, self._showHideMainToolBar,
                self.settings.mainWindowShowMainToolbar),
            ("ShowHideTimelineToolbar", None, _("Timeline Toolbar"),
            None, None, self._showHideTimelineToolbar,
                self.settings.mainWindowShowTimelineToolbar),
        ]

        self.main_actions = Gtk.ActionGroup("mainwindow")
        self.main_actions.add_actions(actions)
        self.undock_action = Gtk.Action("WindowizeViewer", _("Undock Viewer"),
            _("Put the viewer in a separate window"), None)
        self.main_actions.add_action(self.undock_action)
        self.toggle_actions = Gtk.ActionGroup("mainwindowtoggles")
        self.toggle_actions.add_toggle_actions(toggleactions)

        important_actions = ("Undo", "SaveProject", "RenderProject")
        for action in self.main_actions.list_actions():
            action_name = action.get_name()
            if action_name in important_actions:
                # Force showing a label alongside the action's toolbar button
                action.props.is_important = True
            if action_name == "RenderProject":
                # the button is set sensitive when the timeline duration changes
                action.set_sensitive(False)
                self.render_button = action
            elif action_name in ["NewProject", "SaveProject", "SaveProjectAs", "OpenProject"]:
                if instance.settings.fileSupportEnabled:
                    action.set_sensitive(True)
            elif action_name in [
                "File", "Edit", "View", "Help",
                "UserManual", "About", "Quit", "ImportSourcesFolder",
                "Preferences", "Project", "ProjectSettings",
                "Library", "Timeline", "Viewer", "WindowizeViewer"]:
                action.set_sensitive(True)
            else:
                action.set_sensitive(False)
                self.log("%s has been made insensitive" % action_name)

        self.uimanager = Gtk.UIManager()
        self.add_accel_group(self.uimanager.get_accel_group())
        self.uimanager.insert_action_group(self.main_actions, 0)
        self.uimanager.insert_action_group(self.toggle_actions, -1)
        self.uimanager.add_ui_from_file(os.path.join(get_ui_dir(), "mainwindow.xml"))

    def _createUi(self, instance, allow_full_screen):
        """
        Create the graphical interface with the following hierarchy in a vbox:
        -- Menubar
        -- Main toolbar
        -- self.vpaned
        ---- self.mainhpaned (upper half)
        ------ self.secondaryhpaned (upper-left)
        -------- Primary tabs
        -------- Context tabs
        ------ Viewer (upper-right)
        ---- Timeline (bottom half)
        """
        self.set_title("%s" % (APPNAME))
        self.set_icon_name("pitivi")
        self.connect("delete-event", self._deleteCb)
        self.connect("configure-event", self._configureCb)
        vbox = Gtk.VBox(False)
        self.add(vbox)
        vbox.show()

        # Main menu & toolbar
        self.menu = self.uimanager.get_widget("/MainMenuBar")
        self.toolbar = self.uimanager.get_widget("/MainToolBar")
        self.toolbar.get_style_context().add_class("primary-toolbar")
        vbox.pack_start(self.menu, False, True, 0)
        vbox.pack_start(self.toolbar, False, True, 0)
        self.menu.show()
        self.toolbar.show()

        # Set up our main containers, in the order documented above
        self.vpaned = Gtk.VPaned()  # Separates the timeline from tabs+viewer
        self.mainhpaned = Gtk.HPaned()  # Separates the viewer from tabs
        self.secondhpaned = Gtk.HPaned()  # Separates the two sets of tabs
        self.vpaned.pack1(self.mainhpaned, resize=True, shrink=False)
        self.mainhpaned.pack1(self.secondhpaned, resize=True, shrink=False)
        vbox.pack_start(self.vpaned, True, True, 0)
        self.vpaned.show()
        self.secondhpaned.show()
        self.mainhpaned.show()

        # First set of tabs
        self.main_tabs = BaseTabs(instance)
        self.medialibrary = MediaLibraryWidget(instance, self.uimanager)
        self.effectlist = EffectListWidget(instance, self.uimanager)
        self.main_tabs.append_page(self.medialibrary, Gtk.Label(label=_("Media Library")))
        self.main_tabs.append_page(self.effectlist, Gtk.Label(label=_("Effect Library")))
        self.medialibrary.connect('play', self._mediaLibraryPlayCb)
        self.medialibrary.show()
        self.effectlist.show()

        # Second set of tabs
        self.context_tabs = BaseTabs(instance)
        self.clipconfig = ClipProperties(instance, self.uimanager)
        self.trans_list = TransitionsListWidget(instance, self.uimanager)
        self.title_editor = TitleEditor(instance, self.uimanager)
        self.context_tabs.append_page(self.clipconfig, Gtk.Label(label=_("Clip configuration")))
        self.context_tabs.append_page(self.trans_list, Gtk.Label(label=_("Transitions")))
        self.context_tabs.append_page(self.title_editor.widget, Gtk.Label(_("Title editor")))
        self.context_tabs.connect("switch-page", self.title_editor.tab_switched)
        self.clipconfig.show()
        self.trans_list.show()

        self.secondhpaned.pack1(self.main_tabs, resize=True, shrink=False)
        self.secondhpaned.pack2(self.context_tabs, resize=True, shrink=False)
        self.main_tabs.show()
        self.context_tabs.show()

        # Viewer
        self.viewer = PitiviViewer(instance, undock_action=self.undock_action)
        self.viewer.drag_dest_set(Gtk.DestDefaults.DROP | Gtk.DestDefaults.MOTION,
                           [FILESOURCE_TARGET_ENTRY, URI_TARGET_ENTRY],
                           Gdk.DragAction.COPY)
        self.viewer.connect("drag_data_received", self._viewerDndDataReceivedCb)
        self.mainhpaned.pack2(self.viewer, resize=False, shrink=False)

        # Now, the lower part: the timeline
        timeline_area = Gtk.HBox()
        self.timeline_ui = Timeline(instance, self.uimanager)
        self.timeline_ui.setProjectManager(self.app.projectManager)
        self.timeline_ui.controls.connect("selection-changed", self._selectedLayerChangedCb)
        ttb = self.uimanager.get_widget("/TimelineToolBar")
        ttb.get_style_context().add_class("inline-toolbar")
        ttb.set_orientation(Gtk.Orientation.VERTICAL)
        ttb.set_style(Gtk.ToolbarStyle.ICONS)

        self.vpaned.pack2(timeline_area, resize=True, shrink=False)
        timeline_area.pack_start(self.timeline_ui, expand=True, fill=True, padding=0)
        timeline_area.pack_start(ttb, expand=False, fill=True, padding=0)
        timeline_area.show()
        self.timeline_ui.show()
        ttb.show()

        # Restore settings (or set defaults) for position and visibility
        height = -1
        width = -1
        if self.settings.mainWindowHPanePosition:
            self.secondhpaned.set_position(self.settings.mainWindowHPanePosition)
        if self.settings.mainWindowMainHPanePosition:
            self.mainhpaned.set_position(self.settings.mainWindowMainHPanePosition)
        if self.settings.mainWindowVPanePosition:
            self.vpaned.set_position(self.settings.mainWindowVPanePosition)
        if self.settings.mainWindowWidth:
            width = self.settings.mainWindowWidth
        if self.settings.mainWindowHeight:
            height = self.settings.mainWindowHeight
        self.set_default_size(width, height)
        if height == -1 and width == -1:
            self.maximize()
        if allow_full_screen and self.settings.mainWindowFullScreen:
            self.setFullScreen(True)
        if not self.settings.mainWindowShowMainToolbar:
            self.toolbar.props.visible = False
        if not self.settings.mainWindowShowTimelineToolbar:
            ttb.props.visible = False

    def switchContextTab(self, tab=None):
        """
        Switch the tab being displayed on the second set of tabs,
        depending on the context.

        @param the name of the tab to switch to, or None to reset
        """
        if not tab:
            page = 0
        else:
            tab = tab.lower()
            if tab == "clip configuration":
                page = 0
            elif tab == "transitions":
                page = 1
            elif tab == "title editor":
                page = 2
            else:
                self.debug("Invalid context tab switch requested")
                return False
        self.context_tabs.set_current_page(page)

    def setFullScreen(self, fullscreen):
        """ Toggle the fullscreen mode of the application """
        if fullscreen:
            self.fullscreen()
        else:
            self.unfullscreen()
        self.is_fullscreen = fullscreen

    def setActionsSensitive(self, sensitive):
        """
        Grab (or release) keyboard letter keys focus/sensitivity
        for operations such as typing text in an entry.

        This toggles the sensitivity of all actiongroups that might interfere.
        This means mostly the timeline's actions.

        This method does not need to be called when creating a separate window.
        """
        self.log("Setting actions sensitivity to %s" % sensitive)
        # The mainwindow's actions don't prevent typing into entry widgets;
        # Only timeline actions (ex: deleting and play/pause) are dangerous.
        if self.timeline_ui:
            # Don't loop in self.timeline_ui.ui_manager.get_action_groups()
            # otherwise you'll get all the action groups of the application.
            self.timeline_ui.playhead_actions.set_sensitive(sensitive)
            selected = self.timeline_ui.timeline.selection.getSelectedTrackObjs()
            if not sensitive or (sensitive and selected):
                self.log("Setting timeline selection actions sensitivity to %s" % sensitive)
                self.timeline_ui.selection_actions.set_sensitive(sensitive)

## Missing Plugin Support

    def _installPlugins(self, details, missingPluginsCallback):
        context = InstallPluginsContext()
        context.set_xid(self.window.xid)

        res = install_plugins_async(details, context,
                missingPluginsCallback)
        return res

## UI Callbacks

    def _configureCb(self, unused_widget, event):
        if not self.is_fullscreen:
            self.settings.mainWindowWidth = event.width
            self.settings.mainWindowHeight = event.height

    def _deleteCb(self, unused_widget, unused_data=None):
        self._saveWindowSettings()
        if not self.app.shutdown():
            return True

        return False

    def _saveWindowSettings(self):
        self.settings.mainWindowFullScreen = self.is_fullscreen
        self.settings.mainWindowHPanePosition = self.secondhpaned.get_position()
        self.settings.mainWindowMainHPanePosition = self.mainhpaned.get_position()
        self.settings.mainWindowVPanePosition = self.vpaned.get_position()
        mtb = self.toggle_actions.get_action("ShowHideMainToolbar")
        ttb = self.toggle_actions.get_action("ShowHideTimelineToolbar")
        self.settings.mainWindowShowMainToolbar = mtb.props.active
        self.settings.mainWindowShowTimelineToolbar = ttb.props.active

    def _mediaLibraryPlayCb(self, medialibrary, uri):
        self._viewUri(uri)

    def _mediaLibrarySourceRemovedCb(self, medialibrary, uri, unused_info):
        """When a clip is removed from the Media Library, tell the timeline
        to remove all instances of that clip."""
        self.timeline_ui.purgeObject(uri)

    def _selectedLayerChangedCb(self, widget, layer):
        self.main_actions.get_action("RemoveLayer").set_sensitive(layer != None)

## Toolbar/Menu actions callback

    def _newProjectMenuCb(self, unused_action):
        self.app.projectManager.newBlankProject()
        self.app.gui.showProjectSettingsDialog()

    def _openProjectCb(self, unused_action):
        self.openProject()

    def _saveProjectCb(self, unused_action):
        if not self.app.current.uri:
            self._saveProjectAsCb(unused_action)
        else:
            self.app.projectManager.saveProject(self.app.current, overwrite=True)

    def _saveProjectAsCb(self, unused_action):
        uri = self._showSaveAsDialog(self.app.current)
        if uri is not None:
            return self.app.projectManager.saveProject(self.app.current, uri, overwrite=True)

        return False

    def _revertToSavedProjectCb(self, unused_action):
        return self.app.projectManager.revertToSavedProject()

    def _exportProjectAsTarCb(self, unused_action):
        uri = self._showExportDialog(self.app.current)
        result = None
        if uri:
            result = self.app.projectManager.exportProject(self.app.current, uri)

        if not result:
            self.log("Project couldn't be exported")
        return result

    def _projectSettingsCb(self, unused_action):
        self.showProjectSettingsDialog()

    def _removeLayerCb(self, unused_action):
        layer = self.timeline_ui.controls.getSelectedLayer()
        timeline = layer.get_timeline()
        timeline.remove_layer(layer)

    def showProjectSettingsDialog(self):
        from pitivi.project import ProjectSettingsDialog
        ProjectSettingsDialog(self, self.app.current).window.run()
        self.updateTitle()

    def _quitCb(self, unused_action):
        self._saveWindowSettings()
        self.app.shutdown()

    def _fullScreenCb(self, unused_action):
        self.setFullScreen(not self.is_fullscreen)

    def _showHideMainToolBar(self, action):
        self.uimanager.get_widget("/MainToolBar").props.visible = \
            action.props.active

    def _showHideTimelineToolbar(self, action):
        self.uimanager.get_widget("/TimelineToolBar").props.visible = \
            action.props.active

    def _userManualCb(self, unused_action):
        show_user_manual()

    def _aboutResponseCb(self, dialog, unused_response):
        dialog.destroy()

    def _aboutCb(self, unused_action):
        abt = Gtk.AboutDialog()
        abt.set_name(APPNAME)
        if in_devel:
            abt.set_version(_("Development version"))
        else:
            abt.set_version(pitivi_version)
        abt.set_website(APPURL)
        ges_version_str = "GES %i.%i.%i.%i" % (GES.version())
        gst_version_str = "GStreamer %i.%i.%i.%i" % (Gst.version())
        if self.app.version_information and \
           self.app.version_information["status"] != "CURRENT":
            version_str = _("PiTiVi %s is available." %
                (self.app.version_information["current"]))

            abt.set_comments("%s\n\n%s\n\n%s" %
                (ges_version_str, gst_version_str, version_str))
        else:
            abt.set_comments("%s\n%s" % (ges_version_str, gst_version_str))
        authors = [_("Current maintainers:"),
                   "Jean-François Fortin Tam <nekohayo@gmail.com>",
                   "Thibault Saunier <thibault.saunier@collabora.com>",
                   "",
                   _("Past maintainers:"),
                   "Edward Hervey <bilboed@bilboed.com>",
                   "Alessandro Decina <alessandro.decina@collabora.co.uk>",
                   "Brandon Lewis <brandon_lewis@berkeley.edu>",
                   "",
                   _("Contributors:\n" +
                   "A handwritten list here would...\n" +
                   "• be too long,\n" +
                   "• be frequently outdated,\n" +
                   "• not show their relative merit.\n\n" +
                   "Out of respect for our contributors, we point you instead to:\n"),
                   # Translators: keep the %s at the end of the 1st line
                   _("The list of contributors on Ohloh %s\n" +
                   "Or you can run: git shortlog -s -n")\
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
        abt.show()

    def openProject(self):
        chooser = Gtk.FileChooserDialog(_("Open File..."),
            self,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        chooser.set_icon_name("pitivi")
        chooser.set_select_multiple(False)
        # TODO: Remove this set_current_folder call when GTK bug 683999 is fixed
        chooser.set_current_folder(self.settings.lastProjectFolder)
        for format in formats:
            filt = Gtk.FileFilter()
            filt.set_name(format[1])
            for ext in format[2]:
                filt.add_pattern("*%s" % ext)
            chooser.add_filter(filt)
        default = Gtk.FileFilter()
        default.set_name(_("All supported formats"))
        default.add_custom(Gtk.FileFilterFlags.URI, GES.Formatter.can_load_uri, None)
        chooser.add_filter(default)

        response = chooser.run()
        if response == Gtk.ResponseType.OK:
            self.app.projectManager.loadProject(chooser.get_uri())
        chooser.destroy()
        return True

    def _undoCb(self, action):
        self.app.action_log.undo()

    def _redoCb(self, action):
        self.app.action_log.redo()

    def _prefsCb(self, unused_action):
        if not self.prefsdialog:
            from pitivi.dialogs.prefs import PreferencesDialog
            self.prefsdialog = PreferencesDialog(self.app)
            self.prefsdialog.dialog.set_transient_for(self)
        self.prefsdialog.run()

    def _projectManagerNewProjectLoadedCb(self, projectManager, project):
        """
        Once a new project has been loaded, wait for media library's
        "ready" signal to populate the timeline.
        """
        self.log("A new project is loaded, wait for clips")
        self._connectToProjectSources(self.app.current.medialibrary)
        self.app.current.timeline.connect("notify::duration",
                self._timelineDurationChangedCb)
        self.app.current.pipeline.activatePositionListener()

        # This should only be done when loading a project, and disconnected
        # as soon as we receive the signal.
        self.app.current.medialibrary.connect("ready", self._projectClipsReady)

    def _projectClipsReady(self, medialibrary):
        """
        After the project is loaded along with its media files, update the UI.
        """
        self.log("Project clips are ready, update the UI")
        self.app.current.medialibrary.disconnect_by_func(self._projectClipsReady)
        self._setProject()

        #FIXME GES we should re-enable this when possible
        #self._syncDoUndo(self.app.action_log)

        # Enable export functionality
        self.main_actions.get_action("ExportProject").set_sensitive(True)

        if self._missingUriOnLoading:
            self.app.current.setModificationState(True)
            self.main_actions.get_action("SaveProject").set_sensitive(True)
            self._missingUriOnLoading = False

        if self.app.current.timeline.props.duration != 0:
            self.render_button.set_sensitive(True)

    def _projectManagerNewProjectLoadingCb(self, projectManager, uri):
        if uri:
            self.recent_manager.add_item(uri)
        self.log("A NEW project is loading, deactivate UI")

    def _projectManagerSaveProjectFailedCb(self, projectManager, uri, exception=None):
        project_filename = unquote(uri.split("/")[-1])
        dialog = Gtk.MessageDialog(self,
            Gtk.DialogFlags.MODAL,
            Gtk.MessageType.ERROR,
            Gtk.ButtonsType.OK,
            _('Unable to save project "%s"') % project_filename)
        dialog.set_title(_("Error Saving Project"))
        if exception:
            dialog.set_property("secondary-use-markup", True)
            dialog.set_property("secondary-text", unquote(str(exception)))
        dialog.set_transient_for(self)
        dialog.run()
        dialog.destroy()
        self.error("failed to save project")

    def _projectManagerProjectSavedCb(self, projectManager, project, uri):
        self.app.action_log.checkpoint()
        self._syncDoUndo(self.app.action_log)
        if uri:
            self.recent_manager.add_item(uri)
        if project.uri is None:
            project.uri = uri

    def _projectManagerClosingProjectCb(self, projectManager, project):
        if not project.hasUnsavedModifications():
            return True

        if project.uri:
            save = Gtk.STOCK_SAVE
        else:
            save = Gtk.STOCK_SAVE_AS

        dialog = Gtk.Dialog("",
            self, Gtk.DialogFlags.MODAL,
            (_("Close without saving"), Gtk.ResponseType.REJECT,
                    Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                    save, Gtk.ResponseType.YES))
        dialog.set_icon_name("pitivi")
        dialog.set_resizable(False)
        dialog.set_default_response(Gtk.ResponseType.YES)
        dialog.set_transient_for(self)

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
            last_saved = max(os.path.getmtime(path), projectManager.time_loaded)
            time_delta = time() - last_saved
            secondary.props.label = _("If you don't save, "
                "the changes from the last %s will be lost."
                % beautify_time_delta(time_delta))
        else:
            secondary.props.label = _("If you don't save, "
                                    "your changes will be lost.")

        # put the text in a vbox
        vbox = Gtk.VBox(False, SPACING * 2)
        vbox.pack_start(primary, True, True, 0)
        vbox.pack_start(secondary, True, True, 0)

        # make the [[image] text] hbox
        image = Gtk.Image.new_from_stock(Gtk.STOCK_DIALOG_WARNING,
               Gtk.IconSize.DIALOG)
        hbox = Gtk.HBox(False, SPACING * 2)
        hbox.pack_start(image, False, True, 0)
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
            if project.uri is not None:
                res = self.app.projectManager.saveProject(project, overwrite=True)
            else:
                res = self._saveProjectAsCb(None)
        elif response == Gtk.ResponseType.REJECT:
            res = True
        else:
            res = False

        return res

    def _projectManagerProjectClosedCb(self, projectManager, project):
        # we must disconnect from the project pipeline before it is released
        if project.pipeline is not None:
            project.pipeline.deactivatePositionListener()

        self.timeline_ui.timeline = None
        self.clipconfig.timeline = None
        return False

    def _projectManagerRevertingToSavedCb(self, projectManager, unused_project):
        if self.app.current.hasUnsavedModifications():
            dialog = Gtk.MessageDialog(self,
                    Gtk.DialogFlags.MODAL,
                    Gtk.MessageType.WARNING,
                    Gtk.ButtonsType.NONE,
                    _("Do you want to reload current project?"))
            dialog.set_icon_name("pitivi")
            dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.NO,
                    Gtk.STOCK_REVERT_TO_SAVED, Gtk.ResponseType.YES)
            dialog.set_title(_("Revert to saved project"))
            dialog.set_resizable(False)
            dialog.set_property("secondary-text",
                    _("All unsaved changes will be lost."))
            dialog.set_default_response(Gtk.ResponseType.NO)
            dialog.set_transient_for(self)
            response = dialog.run()
            dialog.destroy()
            if response != Gtk.ResponseType.YES:
                return False
        return True

    def _projectManagerNewProjectFailedCb(self, projectManager, uri, exception):
        project_filename = unquote(uri.split("/")[-1])
        dialog = Gtk.MessageDialog(self,
            Gtk.DialogFlags.MODAL,
            Gtk.MessageType.ERROR,
            Gtk.ButtonsType.OK,
            _('Unable to load project "%s"') % project_filename)
        dialog.set_title(_("Error Loading Project"))
        dialog.set_property("secondary-use-markup", True)
        dialog.set_property("secondary-text", unquote(str(exception)))
        dialog.set_transient_for(self)
        dialog.run()
        dialog.destroy()

    def _projectManagerMissingUriCb(self, instance, formatter, tfs):
        dialog = Gtk.Dialog(_("Locate missing file..."),
            self,
            Gtk.DialogFlags.MODAL,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        dialog.set_icon_name("pitivi")
        dialog.set_border_width(SPACING * 2)
        dialog.get_content_area().set_spacing(SPACING)
        dialog.set_transient_for(self)

        # This box will contain the label and optionally a thumbnail
        hbox = Gtk.HBox()
        hbox.set_spacing(SPACING)

        # Check if we have a thumbnail available.
        # This can happen if the file was moved or deleted by an application
        # that does not manage Freedesktop thumbnails. The user is in luck!
        # This is based on medialibrary's addDiscovererInfo method.
        thumbnail_hash = md5(tfs.get_uri()).hexdigest()
        thumb_dir = os.path.expanduser("~/.thumbnails/normal/")
        thumb_path_normal = thumb_dir + thumbnail_hash + ".png"
        if os.path.exists(thumb_path_normal):
            self.debug("A thumbnail file was found for %s" % tfs.get_uri())
            thumbnail = Gtk.Image.new_from_file(thumb_path_normal)
            thumbnail.set_padding(0, SPACING)
            hbox.pack_start(thumbnail, False, False, 0)

        # FIXME GES port, help user identify files with more information
        # need work to be done in GES directly
        # TODO: display the filesize to help the user identify the file
        #if info.get_duration() == Gst.CLOCK_TIME_NONE:
            ## The file is probably an image, not video or audio.
            #text = _('The following file has moved: "<b>%s</b>"'
                     #'\nPlease specify its new location:'
                     #% info_name(info))
        #else:
            #length = beautify_length(info.get_duration())
            #text = _('The following file has moved: "<b>%s</b>" (duration: %s)'
                     #'\nPlease specify its new location:'
                     #% (info_name(info), length))

        text = _('The following file has moved: "<b>%s</b>"'
                 '\nPlease specify its new location:'
                 % info_name(tfs))

        label = Gtk.Label()
        label.set_markup(text)
        hbox.pack_start(label, False, False, 0)
        dialog.get_content_area().pack_start(hbox, False, False, 0)
        hbox.show_all()

        chooser = Gtk.FileChooserWidget(action=Gtk.FileChooserAction.OPEN)
        chooser.set_select_multiple(False)
        pw = PreviewWidget(self.app)
        chooser.set_preview_widget(pw)
        chooser.set_use_preview_label(False)
        chooser.connect('update-preview', pw.add_preview_request)
        chooser.set_current_folder(self.settings.lastProjectFolder)
        # Use a Gtk FileFilter to only show files with the same extension
        # Note that splitext gives us the extension with the ".", no need to
        # add it inside the filter string.
        filename, extension = os.path.splitext(tfs.get_uri())
        filter = Gtk.FileFilter()
        # Translators: this is a format filter in a filechooser. Ex: "AVI files"
        filter.set_name(_("%s files" % extension))
        filter.add_pattern("*" + extension.lower())
        filter.add_pattern("*" + extension.upper())
        default = Gtk.FileFilter()
        default.set_name(_("All files"))
        default.add_pattern("*")
        chooser.add_filter(filter)
        chooser.add_filter(default)
        dialog.get_content_area().pack_start(chooser, True, True, 0)
        chooser.show()

        # If the window is too big, the window manager will resize it so that
        # it fits on the screen.
        dialog.set_default_size(1024, 1000)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            self.log("User chose a new URI for the missing file")
            new_uri = chooser.get_uri()
            if new_uri:
                self.app.current.medialibrary.addUris([new_uri])
                formatter.update_source_uri(tfs, new_uri)
                self._missingUriOnLoading = True
        else:
            # Even if the user clicks Cancel, the discoverer keeps trying to
            # import the rest of the clips...
            # However, since we don't yet have proxy editing, we need to break
            # this async operation, or the filechooser will keep showing up
            # and all sorts of weird things will happen.
            # TODO: bugs #661059, 609136
            attempted_uri = self.app.current.uri
            reason = _('No replacement file was provided for "<i>%s</i>".\n\n'
                        'PiTiVi does not currently support partial projects.'
                        % info_name(tfs))
            # Put an end to the async signals spamming us with dialogs:
            self.app.projectManager.disconnect_by_func(self._projectManagerMissingUriCb)
            # Don't overlap the file chooser with our error dialog
            # The chooser will be destroyed further below, so let's hide it now.
            dialog.hide()
            # Reset projectManager and disconnect all the signals:
            self.app.projectManager.newBlankProject()
            # Force the project load to fail:
            # This will show an error using _projectManagerNewProjectFailedCb
            # You have to do this *after* successfully creating a blank project,
            # or the startupwizard will still be connected to that signal too.
            self.app.projectManager.emit("new-project-failed", attempted_uri, reason)

        dialog.destroy()

    def _connectToProjectSources(self, medialibrary):
        #FIXME GES we should re-enable this when possible
        #medialibrary.connect("missing-plugins", self._sourceListMissingPluginsCb)
        medialibrary.connect("source-removed", self._mediaLibrarySourceRemovedCb)

    def _actionLogCommit(self, action_log, stack, nested):
        if nested:
            return

        self._syncDoUndo(action_log)

    def _actionLogCleaned(self, action_log):
        self._syncDoUndo(action_log)

    def _actionLogUndo(self, action_log, stack):
        self._syncDoUndo(action_log)

    def _actionLogRedo(self, action_log, stack):
        self._syncDoUndo(action_log)

    def _syncDoUndo(self, action_log):
        undo_action = self.main_actions.get_action("Undo")
        can_undo = bool(action_log.undo_stacks)
        undo_action.set_sensitive(can_undo)

        dirty = action_log.dirty()
        save_action = self.main_actions.get_action("SaveProject")
        save_action.set_sensitive(dirty)
        if self.app.current.uri is not None:
            revert_action = self.main_actions.get_action("RevertToSavedProject")
            revert_action.set_sensitive(dirty)
        self.app.current.setModificationState(dirty)

        redo_action = self.main_actions.get_action("Redo")
        can_redo = bool(action_log.redo_stacks)
        redo_action.set_sensitive(can_redo)
        self.updateTitle()

## PiTiVi current project callbacks

    def _setProject(self):
        """
        Disconnect and reconnect callbacks to the new current project
        """
        if not self.app.current:
            self.warning("Current project instance does not exist")
            return False
        try:
            self.app.current.disconnect_by_func(self._settingsChangedCb)
        except:
            # When loading the first project, the signal has never been
            # connected before.
            pass
        self.viewer.setPipeline(self.app.current.pipeline)
        self._settingsChangedCb(self.app.current, None, self.app.current.settings)
        if self.timeline_ui:
            self.timeline_ui.setProject(self.app.current)
            self.clipconfig.project = self.app.current
            #FIXME GES port undo/redo
            #self.app.timelineLogObserver.pipeline = self.app.current.pipeline
        self.app.current.connect("settings-changed", self._settingsChangedCb)
        # When creating a blank project, medialibrary will eventually trigger
        # this _setProject method, but there's no project URI yet.
        if self.app.current.uri:
            folder_path = os.path.dirname(path_from_uri(self.app.current.uri))
            self.settings.lastProjectFolder = folder_path

    def _settingsChangedCb(self, project, unused_old, new):
        # TODO: this method's signature should be changed:
        # project = self.app.current,
        # old is never used, and the new is equal to self.app.current.settings
        self.viewer.setDisplayAspectRatio(
            float(new.videopar.num / new.videopar.denom * new.videowidth) /\
                float(new.videoheight))

    def _sourceListMissingPluginsCb(self, project, uri, factory,
            details, descriptions, missingPluginsCallback):
        res = self._installPlugins(details, missingPluginsCallback)
        return res

    def _timelineDurationChangedCb(self, timeline, unused_duration):
        duration = timeline.get_duration()
        self.debug("Timeline duration changed to %s", duration)
        self.render_button.set_sensitive(duration > 0)

## other
    def _showExportDialog(self, project):
        self.log("Export requested")
        chooser = Gtk.FileChooserDialog(_("Export To..."),
            self,
            action=Gtk.FileChooserAction.SAVE,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK))

        chooser.set_icon_name("pitivi")
        chooser.set_select_multiple(False)
        chooser.props.do_overwrite_confirmation = True

        if not project.name:
            chooser.set_current_name(_("Untitled") + ".tar")
        else:
            chooser.set_current_name(project.name + ".tar")

        filt = Gtk.FileFilter()
        filt.set_name(_("Tar archive"))
        filt.add_pattern("*.tar")
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
            format = chooser.get_filter().get_name()
            if format == _("Detect automatically"):
                format = None
            self.log("uri:%s , format:%s", uri, format)
            ret = uri
        else:
            self.log("User didn't choose a URI to export project to")
            ret = None

        chooser.destroy()
        return ret

    def _showSaveAsDialog(self, project):
        self.log("Save URI requested")
        chooser = Gtk.FileChooserDialog(_("Save As..."),
            self,
            action=Gtk.FileChooserAction.SAVE,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK))

        chooser.set_icon_name("pitivi")
        chooser.set_select_multiple(False)
        chooser.set_current_name(_("Untitled") + ".xptv")
        chooser.set_current_folder(self.settings.lastProjectFolder)
        chooser.props.do_overwrite_confirmation = True
        for format in formats:
            filt = Gtk.FileFilter()
            filt.set_name(format[1])
            for ext in format[2]:
                filt.add_pattern("*.%s" % ext)
            chooser.add_filter(filt)
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
            self.log("uri:%s , format:%s", uri, format)
            format = chooser.get_filter().get_name()
            if format == _("Detect automatically"):
                format = None
            self.settings.lastProjectFolder = chooser.get_current_folder()
            ret = uri
        else:
            self.log("User didn't choose a URI to save project to")
            ret = None

        chooser.destroy()
        return ret

    def _viewerDndDataReceivedCb(self, unused_widget, context, unused_x, unused_y,
                           selection, targetType, ctime):
        # FIXME : This should be handled by the main application who knows how
        # to switch between pipelines.
        self.info("context:%s, targetType:%s", context, targetType)
        if targetType == TYPE_URI_LIST:
            uri = selection.data.strip().split("\n")[0].strip()
        elif targetType == TYPE_PITIVI_FILESOURCE:
            uri = selection.data
        else:
            context.finish(False, False, ctime)
            return

        try:
            info = self.app.current.medialibrary.getInfoFromUri(uri)
        except MediaLibraryError:
            self.app.current.medialibrary.addUris([uri])
            # FIXME Add a delay/catch signal when we start doing the discovering
            # async
            info = self.app.current.medialibrary.getInfoFromUri(uri)
        self._viewUri(info.get_uri())
        context.finish(True, False, ctime)

    def _leavePreviewCb(self, window, unused):
        window.destroy()

    def _viewUri(self, path):
        """ Preview a media file from the media library """
        preview_window = Gtk.Window()
        preview_window.set_title(_("Preview - click outside to close"))
        preview_window.set_transient_for(self)
        preview_window.connect("focus-out-event", self._leavePreviewCb)
        previewer = PreviewWidget(self)
        preview_window.add(previewer)

        preview_window.show_all()  # Needed for PreviewWidget to do its magic
        preview_window.hide()  # Hack to allow setting the window position
        previewer.previewUri(path)
        previewer.setMinimal()
        info = self.app.current.medialibrary.getInfoFromUri(path)
        try:
            # For videos and images, automatically resize the window
            # Try to keep it 1:1 if it can fit within 85% of the parent window
            img_width = info.get_video_streams()[0].get_width()
            img_height = info.get_video_streams()[0].get_height()
            controls_height = previewer.bbox.size_request().height
            mainwindow_width, mainwindow_height = self.get_size()
            max_width = 0.85 * mainwindow_width
            max_height = 0.85 * mainwindow_height
            if img_width < max_width \
                and (img_height + controls_height) < max_height:
                # The video is small enough, keep it 1:1
                preview_window.resize(img_width, img_height + controls_height)
            else:
                # The video is too big, size it down
                # TODO: be smarter, figure out which (width, height) is bigger
                new_height = max_width * img_height / img_width
                preview_window.resize(int(max_width),
                    int(new_height + controls_height))
        except:
            # There is no video/image stream. This is an audio file.
            # Resize to the minimum and let the window manager deal with it
            preview_window.resize(1, 1)
        # Setting the position of the window only works if it's currently hidden
        # otherwise, after the resize the position will not be readjusted
        preview_window.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        preview_window.show()

        previewer.play()

    def updateTitle(self):
        name = touched = ""
        if self.app.current:
            if self.app.current.name:
                name = self.app.current.name
            else:
                name = _("Untitled")
            if self.app.current.hasUnsavedModifications():
                touched = "*"
        title = u"%s%s \u2014 %s" % (touched, name, APPNAME)
        self.set_title(title)
