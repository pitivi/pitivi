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
import gtk
import gst
import ges
import webbrowser

from urllib import unquote
from gettext import gettext as _
from gtk import RecentManager


from pitivi.utils.loggable import Loggable
from pitivi.settings import GlobalSettings
from pitivi.effects import EffectListWidget
from pitivi.medialibrary import MediaLibraryWidget, MediaLibraryError

from pitivi.utils.misc import show_user_manual
from pitivi.utils.ui import SPACING, info_name, FILESOURCE_TUPLE, URI_TUPLE, \
         TYPE_URI_LIST, TYPE_PITIVI_FILESOURCE
from pitivi.utils.timeline import Zoomable

from pitivi.timeline.timeline import Timeline

from pitivi.ui.viewer import PitiviViewer

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


#FIXME Hacky, reimplement when avalaible in GES
formats = [(None, _("PiTiVi Native (XML)"), ('xptv',))]


def create_stock_icons():
    """ Creates the pitivi-only stock icons """
    gtk.stock_add([
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
    factory = gtk.IconFactory()
    pmdir = get_pixmap_dir()
    for stockid, path in pixmaps.iteritems():
        pixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(pmdir, path))
        iconset = gtk.IconSet(pixbuf)
        factory.add(stockid, iconset)
        factory.add_default()


class PitiviMainWindow(gtk.Window, Loggable):
    """
    Pitivi's main window.

    @cvar app: The application object
    @type app: L{Application}
    @cvar project: The current project
    @type project: L{Project}
    """
    def __init__(self, instance, allow_full_screen=True):
        """ initialize with the Pitivi object """
        gtk.Window.__init__(self)
        Loggable.__init__(self, "mainwindow")
        self.log("Creating MainWindow")
        self.actions = None
        self.toggleactions = None
        self.actiongroup = None
        self.settings = instance.settings
        self.is_fullscreen = False
        self.timelinepos = 0
        self.prefsdialog = None
        create_stock_icons()
        self._setActions(instance)
        self._createUi(instance, allow_full_screen)

        self.app = instance
        self.manager = RecentManager()
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

    def showEncodingDialog(self, project, pause=True):
        """
        Shows the L{EncodingDialog} for the given project Timeline.

        @param project: The project
        @type project: L{Project}
        @param pause: If C{True}, pause the timeline before displaying the dialog.
        @type pause: C{bool}
        """
        from pitivi.render import EncodingDialog

        dialog = EncodingDialog(self, project)
        dialog.window.connect("destroy", self._renderingDialogDestroyCb)
        self.set_sensitive(False)
        dialog.window.show()

    def _renderingDialogDestroyCb(self, unused_dialog):
        self.set_sensitive(True)

    def _recordCb(self, unused_button):
        self.showEncodingDialog(self.project)

    def _setActions(self, instance):
        PLAY = _("Start Playback")
        LOOP = _("Loop over selected area")

        """ sets up the GtkActions """
        self.actions = [
            ("NewProject", gtk.STOCK_NEW, None,
             None, _("Create a new project"), self._newProjectMenuCb),
            ("OpenProject", gtk.STOCK_OPEN, _("_Open..."),
             None, _("Open an existing project"), self._openProjectCb),
            ("SaveProject", gtk.STOCK_SAVE, None,
             None, _("Save the current project"), self._saveProjectCb),
            ("SaveProjectAs", gtk.STOCK_SAVE_AS, _("Save _As..."),
             None, _("Save the current project"), self._saveProjectAsCb),
            ("RevertToSavedProject", gtk.STOCK_REVERT_TO_SAVED, None,
             None, _("Reload the current project"), self._revertToSavedProjectCb),
            ("ProjectSettings", gtk.STOCK_PROPERTIES, _("Project Settings"),
             None, _("Edit the project settings"), self._projectSettingsCb),
            ("RenderProject", 'pitivi-render', _("_Render..."),
             None, _("Export your project as a finished movie"), self._recordCb),
            ("Undo", gtk.STOCK_UNDO,
             _("_Undo"),
             "<Ctrl>Z", _("Undo the last operation"), self._undoCb),
            ("Redo", gtk.STOCK_REDO,
             _("_Redo"),
             "<Ctrl>Y", _("Redo the last operation that was undone"), self._redoCb),
            ("Preferences", gtk.STOCK_PREFERENCES, _("_Preferences"),
              None, None, self._prefsCb),
            ("Quit", gtk.STOCK_QUIT, None, None, None, self._quitCb),
            ("About", gtk.STOCK_ABOUT, None, None,
             _("Information about %s") % APPNAME, self._aboutCb),
            ("UserManual", gtk.STOCK_HELP, _("User Manual"),
             None, None, self._userManualCb),
            ("File", None, _("_Project")),
            ("Edit", None, _("_Edit")),
            ("View", None, _("_View")),
            ("Library", None, _("_Library")),
            ("Timeline", None, _("_Timeline")),
            ("Viewer", None, _("Previe_w")),
            ("PlayPause", gtk.STOCK_MEDIA_PLAY, None, "space", PLAY,
                self.playPause),
            ("Loop", gtk.STOCK_REFRESH, _("Loop"), None, LOOP,
                self.loop),
            ("Help", None, _("_Help")),
        ]

        self.toggleactions = [
            ("FullScreen", gtk.STOCK_FULLSCREEN, None, "f",
             _("View the main window on the whole screen"),
                 self._fullScreenCb),
            ("FullScreenAlternate", gtk.STOCK_FULLSCREEN, None, "F11", None,
                self._fullScreenAlternateCb),
            ("ShowHideMainToolbar", None, _("Main Toolbar"), None, None,
                self._showHideMainToolBar,
                self.settings.mainWindowShowMainToolbar),
            ("ShowHideTimelineToolbar", None, _("Timeline Toolbar"), None,
                None, self._showHideTimelineToolbar,
                self.settings.mainWindowShowTimelineToolbar),
        ]

        self.actiongroup = gtk.ActionGroup("mainwindow")
        self.actiongroup.add_actions(self.actions)
        self.actiongroup.add_toggle_actions(self.toggleactions)
        self.undock_action = gtk.Action("WindowizeViewer", _("Undock Viewer"),
            _("Put the viewer in a separate window"), None)
        self.actiongroup.add_action(self.undock_action)

        # deactivating non-functional actions
        # FIXME : reactivate them
        save_action = self.actiongroup.get_action("SaveProject")
        save_action.set_sensitive(False)

        for action in self.actiongroup.list_actions():
            action_name = action.get_name()
            if action_name == "RenderProject":
                self.render_button = action
                # this will be set sensitive when the timeline duration changes
                action.props.is_important = True
            elif action_name in [
                "ProjectSettings", "Quit", "File", "Edit", "Help", "About",
                "View", "FullScreen", "FullScreenAlternate", "UserManual",
                "ImportSourcesFolder", "PlayPause",
                "Project", "FrameForward", "FrameBackward",
                "ShowHideMainToolbar", "ShowHideTimelineToolbar", "Library",
                "Timeline", "Viewer", "FrameForward", "FrameBackward",
                "SecondForward", "SecondBackward", "EdgeForward",
                "EdgeBackward", "Preferences", "WindowizeViewer"]:
                action.set_sensitive(True)
            elif action_name in ["NewProject", "SaveProjectAs", "OpenProject"]:
                if instance.settings.fileSupportEnabled:
                    action.set_sensitive(True)
            elif action_name == "SaveProject":
                if instance.settings.fileSupportEnabled:
                    action.set_sensitive(True)
                action.props.is_important = True
            elif action_name == "Undo":
                action.set_sensitive(True)
                action.props.is_important = True
            else:
                action.set_sensitive(False)

        self.uimanager = gtk.UIManager()
        self.add_accel_group(self.uimanager.get_accel_group())
        self.uimanager.insert_action_group(self.actiongroup, 0)
        self.uimanager.add_ui_from_file(os.path.join(get_ui_dir(), "mainwindow.xml"))

    def _createUi(self, instance, allow_full_screen):
        """ Create the graphical interface """
        self.set_title("%s" % (APPNAME))
        self.connect("delete-event", self._deleteCb)
        self.connect("configure-event", self._configureCb)

        # main menu & toolbar
        vbox = gtk.VBox(False)
        self.add(vbox)
        vbox.show()
        self.menu = self.uimanager.get_widget("/MainMenuBar")
        vbox.pack_start(self.menu, expand=False)
        self.menu.show()
        self.toolbar = self.uimanager.get_widget("/MainToolBar")
        vbox.pack_start(self.toolbar, expand=False)
        self.toolbar.show()
        # timeline and project tabs
        vpaned = gtk.VPaned()
        vbox.pack_start(vpaned)
        vpaned.show()

        self.timeline = Timeline(instance, self.uimanager)
        self.timeline.connect("duration-changed",
                self._timelineDurationChangedCb)
        self.project = None

        vpaned.pack2(self.timeline, resize=True, shrink=False)
        self.timeline.show()
        self.mainhpaned = gtk.HPaned()
        vpaned.pack1(self.mainhpaned, resize=True, shrink=False)

        self.secondhpaned = gtk.HPaned()
        self.mainhpaned.pack1(self.secondhpaned, resize=True, shrink=False)
        self.secondhpaned.show()
        self.mainhpaned.show()

        self.projecttabs = BaseTabs(instance)

        self.medialibrary = MediaLibraryWidget(instance, self.uimanager)
        self.projecttabs.append_page(self.medialibrary, gtk.Label(_("Media Library")))
        self._connectToMediaLibrary()
        self.medialibrary.show()

        self.effectlist = EffectListWidget(instance, self.uimanager)
        self.projecttabs.append_page(self.effectlist, gtk.Label(_("Effect Library")))
        self.effectlist.show()

        self.secondhpaned.pack1(self.projecttabs, resize=True, shrink=False)
        self.projecttabs.show()

        # Actions with key accelerators that will be made unsensitive while
        # a gtk entry box is used to avoid conflicts.
        self.sensitive_actions = []
        for action in self.timeline.playhead_actions:
            self.sensitive_actions.append(action[0])
        for action in self.toggleactions:
            self.sensitive_actions.append(action[0])

        #Clips properties
        self.propertiestabs = BaseTabs(instance, True)
        self.clipconfig = ClipProperties(instance, self.uimanager)
        self.propertiestabs.append_page(self.clipconfig,
                                        gtk.Label(_("Clip configuration")))
        self.clipconfig.show()

        self.secondhpaned.pack2(self.propertiestabs, resize=True, shrink=False)
        self.propertiestabs.show()

        # Viewer
        self.viewer = PitiviViewer(instance, undock_action=self.undock_action)
        # drag and drop
        self.viewer.drag_dest_set(gtk.DEST_DEFAULT_DROP | gtk.DEST_DEFAULT_MOTION,
                           [FILESOURCE_TUPLE, URI_TUPLE],
                           gtk.gdk.ACTION_COPY)
        self.viewer.connect("drag_data_received", self._viewerDndDataReceivedCb)
        self.mainhpaned.pack2(self.viewer, resize=False, shrink=False)

        # window and pane position defaults
        self.hpaned = self.secondhpaned
        self.vpaned = vpaned
        height = -1
        width = -1
        if self.settings.mainWindowHPanePosition:
            self.hpaned.set_position(self.settings.mainWindowHPanePosition)
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
        # timeline toolbar
        # FIXME: remove toolbar padding and shadow. In fullscreen mode, the
        # toolbar buttons should be clickable with the mouse cursor at the
        # very bottom of the screen.
        ttb = self.uimanager.get_widget("/TimelineToolBar")
        vbox.pack_start(ttb, expand=False)
        ttb.show()

        if not self.settings.mainWindowShowMainToolbar:
            self.toolbar.props.visible = False

        if not self.settings.mainWindowShowTimelineToolbar:
            ttb.props.visible = False

        #application icon
        self.set_icon_name("pitivi")

        #pulseaudio 'role' (http://0pointer.de/blog/projects/tagging-audio.htm
        os.environ["PULSE_PROP_media.role"] = "production"
        os.environ["PULSE_PROP_application.icon_name"] = "pitivi"

    def _connectToMediaLibrary(self):
        self.medialibrary.connect('play', self._sourceListPlayCb)

    def setFullScreen(self, fullscreen):
        """ Toggle the fullscreen mode of the application """
        if fullscreen:
            self.fullscreen()
        else:
            self.unfullscreen()
        self.is_fullscreen = fullscreen

    #TODO check if it is the way to go
    def setActionsSensitive(self, action_names, sensitive):
        """
        Grab (or release) keyboard letter keys focus/sensitivity
        for operations such as typing text in an entry.
        @param action_names: The name of actions we
                             want to set to sensitive or not, if set to "default"
                             we use the default actions.
        @type action_names: A {list} of action names
        @param sensitive: %True if actions must be sensitive False otherwise
        @type action_names: C{Bool}
        """
        if action_names == "default":
            action_names = self.sensitive_actions

        for action in self.actiongroup.list_actions():
            if action.get_name() in action_names:
                action.set_sensitive(sensitive)

        if self.timeline:
            for action_group in self.timeline.ui_manager.get_action_groups():
                for action in action_group.list_actions():
                    if action.get_name() in action_names:
                        action.set_sensitive(sensitive)

## Missing Plugin Support

    def _installPlugins(self, details, missingPluginsCallback):
        context = gst.pbutils.InstallPluginsContext()
        context.set_xid(self.window.xid)

        res = gst.pbutils.install_plugins_async(details, context,
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
        self.settings.mainWindowHPanePosition = self.hpaned.get_position()
        self.settings.mainWindowMainHPanePosition = self.mainhpaned.get_position()
        self.settings.mainWindowVPanePosition = self.vpaned.get_position()
        mtb = self.actiongroup.get_action("ShowHideMainToolbar")
        ttb = self.actiongroup.get_action("ShowHideTimelineToolbar")
        self.settings.mainWindowShowMainToolbar = mtb.props.active
        self.settings.mainWindowShowTimelineToolbar = ttb.props.active

    def _sourceListPlayCb(self, medialibrary, uri):
        self._viewUri(uri)

## Toolbar/Menu actions callback

    def _newProjectMenuCb(self, unused_action):
        self.app.projectManager.newBlankProject()
        self.app.gui.showProjectSettingsDialog()

    def _openProjectCb(self, unused_action):
        self.openProject()

    def _saveProjectCb(self, unused_action):
        if not self.project.uri:
            self._saveProjectAsCb(unused_action)
        else:
            self.app.projectManager.saveProject(self.project, overwrite=True)

    def _saveProjectAsCb(self, unused_action):
        uri = self._showSaveAsDialog(self.app.current)
        if uri is not None:
            return self.app.projectManager.saveProject(self.project, uri, overwrite=True)

        return False

    def _revertToSavedProjectCb(self, unused_action):
        return self.app.projectManager.revertToSavedProject()

    def _projectSettingsCb(self, unused_action):
        self.showProjectSettingsDialog()

    def showProjectSettingsDialog(self):
        from pitivi.project import ProjectSettingsDialog
        ProjectSettingsDialog(self, self.app.current).window.run()
        self.updateTitle()

    def _quitCb(self, unused_action):
        self._saveWindowSettings()
        self.app.shutdown()

    def _fullScreenCb(self, unused_action):
        self.setFullScreen(not self.is_fullscreen)

    def _fullScreenAlternateCb(self, unused_action):
        # Nothing more, nothing less.
        self.actiongroup.get_action("FullScreen").activate()

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

    def _showWebsiteCb(self, dialog, uri):
        webbrowser.open_new(uri)

    def _aboutCb(self, unused_action):
        abt = gtk.AboutDialog()
        abt.set_name(APPNAME)
        abt.set_version(pitivi_version)
        gtk.about_dialog_set_url_hook(self._showWebsiteCb)
        abt.set_website(APPURL)
        authors = ["Edward Hervey <bilboed@bilboed.com>",
                   "Alessandro Decina <alessandro.decina@collabora.co.uk>",
                   "Brandon Lewis <brandon_lewis@berkeley.edu> (UI)",
                   "Jean-François Fortin Tam <nekohayo@gmail.com> (UI)",
                   "Thibault Saunier <thibault.saunier@collabora.com>",
                   "",
                   _("Contributors:"),
                   "Christophe Sauthier <christophe.sauthier@gmail.com> (i18n)",
                   "Laszlo Pandy <laszlok2@gmail.com> (UI)",
                   "Ernst Persson  <ernstp@gmail.com>",
                   "Richard Boulton <richard@tartarus.org>",
                   "Thibaut Girka <thibaut.girka@free.fr> (UI)",
                   "Johan Dahlin <jdahlin@async.com.br> (UI)",
                   "Luca Della Santina <dellasantina@farm.unipi.it>",
                   "Thijs Vermeir <thijsvermeir@gmail.com>",
                   "Sarath Lakshman <sarathlakshman@slynux.org>",
                   "Alex Balut <alexandru.balut@gmail.com>"]
        abt.set_authors(authors)
        translators = _("translator-credits")
        if translators != "translator-credits":
            abt.set_translator_credits(translators)
        abt.set_license(_("GNU Lesser General Public License\n"
                          "See http://www.gnu.org/copyleft/lesser.html for more details"))
        abt.set_icon_name("pitivi")
        abt.set_logo_icon_name("pitivi")
        abt.connect("response", self._aboutResponseCb)
        abt.show()

    def openProject(self):
        chooser = gtk.FileChooserDialog(_("Open File..."),
            self,
            action=gtk.FILE_CHOOSER_ACTION_OPEN,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        chooser.set_icon_name("pitivi")
        chooser.set_select_multiple(False)
        chooser.set_current_folder(self.settings.lastProjectFolder)
        for format in formats:
            filt = gtk.FileFilter()
            filt.set_name(format[1])
            for ext in format[2]:
                filt.add_pattern("*%s" % ext)
            chooser.add_filter(filt)
        default = gtk.FileFilter()
        default.set_name(_("All Supported Formats"))
        default.add_custom(gtk.FILE_FILTER_URI, ges.formatter_can_load_uri)
        chooser.add_filter(default)

        response = chooser.run()
        self.settings.lastProjectFolder = chooser.get_current_folder()
        if response == gtk.RESPONSE_OK:
            uri = chooser.get_uri()
            uri = unquote(uri)
            self.app.projectManager.loadProject(uri)

        chooser.destroy()
        return True

    def _undoCb(self, action):
        self.app.action_log.undo()

    def _redoCb(self, action):
        self.app.action_log.redo()

    def _prefsCb(self, unused_action):
        if not self.prefsdialog:
            from pitivi.ui.prefs import PreferencesDialog
            self.prefsdialog = PreferencesDialog(self.app)
            self.prefsdialog.dialog.set_transient_for(self)
        self.prefsdialog.run()

    def rewind(self, unused_action):
        pass

    def playPause(self, unused_action):
        self.viewer.togglePlayback()

    def pause(self, unused_action):
        self.viewer.pause()

    def fastForward(self, unused_action):
        pass

    def loop(self, unused_action):
        pass

    def _projectManagerNewProjectLoadedCb(self, projectManager, project):
        self.log("A NEW project is loaded, update the UI!")
        self._setProject(project)

        #FIXME we should reanable it when possible with GES
        #self._connectToProjectSources(project.sources)
        #self._syncDoUndo(self.app.action_log)

        #FIXME GES reimplement me
        if self._missingUriOnLoading:
            self.app.current.setModificationState(True)
            self.actiongroup.get_action("SaveProject").set_sensitive(True)
            self._missingUriOnLoading = False

        if self.timeline.duration != 0:
            self.setBestZoomRatio()
        else:
            self._zoom_duration_changed = True

        self._seeker = self.project.seeker
        self._seeker.connect("seek", self._timelineSeekCb)
        self._seeker.connect("seek-relative", self._timelineSeekRelativeCb)
        self._seeker.connect("flush", self._timelineSeekFlushCb)

        # preliminary seek to ensure the project pipeline is configured
        self._seeker.seek(0)

    def setBestZoomRatio(self, p=0):
        """Set the zoom level so that the entire timeline is in view."""
        ruler_width = self.timeline.ruler.get_allocation()[2]
        # Add gst.SECOND - 1 to the timeline duration to make sure the
        # last second of the timeline will be in view.
        duration = self.timeline.duration
        timeline_duration = duration + gst.SECOND - 1
        timeline_duration_s = int(timeline_duration / gst.SECOND)

        ideal_zoom_ratio = float(ruler_width) / timeline_duration_s
        nearest_zoom_level = Zoomable.computeZoomLevel(ideal_zoom_ratio)
        Zoomable.setZoomLevel(nearest_zoom_level)

    def _projectManagerNewProjectLoadingCb(self, projectManager, uri):
        if uri != None:
            self.manager.add_item(uri)
        self.log("A NEW project is being loading, deactivate UI")

    def _projectManagerSaveProjectFailedCb(self, projectManager,
            project, uri):
        # FIXME: do something here
        self.error("failed to save project")

    def _projectManagerProjectSavedCb(self, projectManager, project, uri):
        self.app.action_log.checkpoint()
        self._syncDoUndo(self.app.action_log)
        if project.uri is None:
            project.uri = uri

    def _projectManagerClosingProjectCb(self, projectManager, project):
        if not project.hasUnsavedModifications():
            return True

        if project.uri:
            save = gtk.STOCK_SAVE
        else:
            save = gtk.STOCK_SAVE_AS

        dialog = gtk.Dialog("",
            self, gtk.DIALOG_MODAL | gtk.DIALOG_NO_SEPARATOR,
            (_("Close without saving"), gtk.RESPONSE_REJECT,
                    gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                    save, gtk.RESPONSE_YES))
        dialog.set_icon_name("pitivi")
        dialog.set_resizable(False)
        dialog.set_has_separator(False)
        dialog.set_default_response(gtk.RESPONSE_YES)
        dialog.set_transient_for(self)

        primary = gtk.Label()
        primary.set_line_wrap(True)
        primary.set_use_markup(True)
        primary.set_alignment(0, 0.5)

        message = _("Save changes to the current project before closing?")
        primary.set_markup("<span weight=\"bold\">" + message + "</span>")

        secondary = gtk.Label()
        secondary.set_line_wrap(True)
        secondary.set_use_markup(True)
        secondary.set_alignment(0, 0.5)
        secondary.props.label = _("If you don't save some of your "
                "changes will be lost")

        # put the text in a vbox
        vbox = gtk.VBox(False, SPACING * 2)
        vbox.pack_start(primary, expand=True, fill=True)
        vbox.pack_start(secondary, expand=True, fill=True)

        # make the [[image] text] hbox
        image = gtk.image_new_from_stock(gtk.STOCK_DIALOG_WARNING,
               gtk.ICON_SIZE_DIALOG)
        hbox = gtk.HBox(False, SPACING * 2)
        hbox.pack_start(image, expand=False)
        hbox.pack_start(vbox, expand=True, fill=True)
        hbox.set_border_width(SPACING)

        # stuff the hbox in the dialog
        content_area = dialog.get_content_area()
        content_area.pack_start(hbox, expand=True, fill=True)
        content_area.set_spacing(SPACING * 2)
        hbox.show_all()

        response = dialog.run()
        dialog.destroy()
        if response == gtk.RESPONSE_YES:
            if project.uri is not None:
                res = self.app.projectManager.saveProject(project, overwrite=True)
            else:
                res = self._saveProjectAsCb(None)
        elif response == gtk.RESPONSE_REJECT:
            res = True
        else:
            res = False

        return res

    def _projectManagerProjectClosedCb(self, projectManager, project):
        # we must disconnect from the project pipeline before it is released
        return False

    def _projectManagerRevertingToSavedCb(self, projectManager, project):
        if project.hasUnsavedModifications():
            dialog = gtk.MessageDialog(self,
                    gtk.DIALOG_MODAL,
                    gtk.MESSAGE_WARNING,
                    gtk.BUTTONS_NONE,
                    _("Do you want to reload current project?"))
            dialog.set_icon_name("pitivi")
            dialog.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_NO,
                    gtk.STOCK_REVERT_TO_SAVED, gtk.RESPONSE_YES)
            dialog.set_title(_("Revert to saved project"))
            dialog.set_resizable(False)
            dialog.set_property("secondary-text",
                    _("All unsaved changes will be lost."))
            dialog.set_default_response(gtk.RESPONSE_NO)
            dialog.set_transient_for(self)
            response = dialog.run()
            dialog.destroy()
            if response != gtk.RESPONSE_YES:
                return False
        return True

    def _projectManagerNewProjectFailedCb(self, projectManager, uri, exception):
        project_filename = unquote(uri.split("/")[-1])
        dialog = gtk.MessageDialog(self,
            gtk.DIALOG_MODAL,
            gtk.MESSAGE_ERROR,
            gtk.BUTTONS_OK,
            _('Unable to load project "%s"') % project_filename)
        dialog.set_icon_name("pitivi")
        dialog.set_title(_("Error Loading Project"))
        dialog.set_property("secondary-text", unquote(str(exception)))
        dialog.set_transient_for(self)
        dialog.run()
        dialog.destroy()
        self.set_sensitive(True)

    def _projectManagerMissingUriCb(self, instance, formatter, tfs):
        dialog = gtk.Dialog(_("Locate missing file..."),
            self,
            gtk.DIALOG_MODAL,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
            gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_icon_name("pitivi")
        dialog.set_border_width(SPACING * 2)
        dialog.get_content_area().set_spacing(SPACING)
        dialog.set_transient_for(self)

        # FIXME GES port, help user identify files with more information
        # need work to be done in GES directly
        # TODO: display the filesize to help the user identify the file
        #if info.get_duration() == gst.CLOCK_TIME_NONE:
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

        label = gtk.Label()
        label.set_markup(text)
        dialog.get_content_area().pack_start(label, False, False)
        label.show()

        chooser = gtk.FileChooserWidget(action=gtk.FILE_CHOOSER_ACTION_OPEN)
        chooser.set_select_multiple(False)
        pw = PreviewWidget(self.app)
        chooser.set_preview_widget(pw)
        chooser.set_use_preview_label(False)
        chooser.connect('update-preview', pw.add_preview_request)
        chooser.set_current_folder(self.settings.lastProjectFolder)
        dialog.get_content_area().pack_start(chooser, True, True)
        chooser.show()

        # If the window is too big, the window manager will resize it so that
        # it fits on the screen.
        dialog.set_default_size(1024, 1000)
        response = dialog.run()

        if response == gtk.RESPONSE_OK:
            self.log("User chose a new URI for the missing file")
            new_uri = chooser.get_uri()
            if new_uri:
                self.project.sources.addUri(new_uri)
                formatter.update_source_uri(tfs, new_uri)
                self._missingUriOnLoading = True
        else:
            self.log("User didn't choose a URI for the missing file")
            # FIXME: not calling addMapping doesn't keep the formatter from
            # re-emitting the same signal. How do we get out of this
            # situation?
            pass

        dialog.destroy()

    def _connectToProjectSources(self, medialibrary):
        medialibrary.connect("missing-plugins", self._sourceListMissingPluginsCb)

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
        undo_action = self.actiongroup.get_action("Undo")
        can_undo = bool(action_log.undo_stacks)
        undo_action.set_sensitive(can_undo)

        dirty = action_log.dirty()
        save_action = self.actiongroup.get_action("SaveProject")
        save_action.set_sensitive(dirty)
        if self.app.current.uri is not None:
            revert_action = self.actiongroup.get_action("RevertToSavedProject")
            revert_action.set_sensitive(dirty)
        self.app.current.setModificationState(dirty)

        redo_action = self.actiongroup.get_action("Redo")
        can_redo = bool(action_log.redo_stacks)
        redo_action.set_sensitive(can_redo)
        self.updateTitle()

## PiTiVi current project callbacks

    def _setProject(self, project):
        if self.project:
            self.project.disconnect_by_func(self._settingsChangedCb)

        if project:
            self.project = project
            self.project_pipeline = self.project.pipeline
            self.project_timeline = self.project.timeline
            self.viewer.setPipeline(project.pipeline)
            self._settingsChangedCb(project, None, project.settings)
            if self.timeline:
                self.timeline.setProject(self.project)
                self.clipconfig.project = self.project
                #FIXME GES port undo/redo
                #self.app.timelineLogObserver.pipeline = self.project.pipeline
            self.project.connect("settings-changed", self._settingsChangedCb)

    def _settingsChangedCb(self, project, old, new):
        self.viewer.setDisplayAspectRatio(float(new.videopar * new.videowidth) /\
                float(new.videoheight))

    def _sourceListMissingPluginsCb(self, project, uri, factory,
            details, descriptions, missingPluginsCallback):
        res = self._installPlugins(details, missingPluginsCallback)
        return res

## Current Project Pipeline
# We handle the pipeline here

    def setProjectPipeline(self, pipeline):
        self._project_pipeline = pipeline
        if self._project_pipeline:
            bus = self._project_pipeline.get_bus()
            bus.add_signal_watch()
            bus.connect('message', self._busMessageCb)

    def getProjectPipeline(self):
        return self._project_pipeline

    project_pipeline = property(getProjectPipeline, setProjectPipeline, None, "The Gst.Pipeline of the project")

    def _timelinePipelineStateChanged(self, pipeline, state):
        self.timeline.stateChanged(state)

## Project Timeline (not to be confused with UI timeline)

    def _timelineDurationChangedCb(self, timeline, duration):
        if timeline.duration > 0:
            sensitive = True
            if self._zoom_duration_changed:
                self.setBestZoomRatio()
                self._zoom_duration_changed = False
            else:
                self.timeline.updateScrollAdjustments()
        else:
            sensitive = False
        self.render_button.set_sensitive(sensitive)

#Pipeline messages
    def _busMessageCb(self, unused_bus, message):
        if message.type == gst.MESSAGE_EOS:
            self.warning("eos")
        elif message.type == gst.MESSAGE_STATE_CHANGED:
            prev, new, pending = message.parse_state_changed()

            if message.src == self._project_pipeline:
                self.debug("Pipeline change state prev:%r, new:%r, pending:%r", prev, new, pending)

                state_change = pending == gst.STATE_VOID_PENDING

                if state_change:
                    self._timelinePipelineStateChanged(self, new)
## other

    def _showSaveAsDialog(self, project):
        self.log("Save URI requested")
        chooser = gtk.FileChooserDialog(_("Save As..."),
            self,
            action=gtk.FILE_CHOOSER_ACTION_SAVE,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
            gtk.STOCK_SAVE, gtk.RESPONSE_OK))

        chooser.set_icon_name("pitivi")
        chooser.set_select_multiple(False)
        chooser.set_current_name(_("Untitled") + ".xptv")
        chooser.set_current_folder(self.settings.lastProjectFolder)
        chooser.props.do_overwrite_confirmation = True
        for format in formats:
            filt = gtk.FileFilter()
            filt.set_name(format[1])
            for ext in format[2]:
                filt.add_pattern("*.%s" % ext)
            chooser.add_filter(filt)
        default = gtk.FileFilter()
        default.set_name(_("Detect Automatically"))
        default.add_pattern("*")
        chooser.add_filter(default)

        response = chooser.run()
        current_folder = chooser.get_current_folder()
        if current_folder:
            self.settings.lastProjectFolder = current_folder

        if response == gtk.RESPONSE_OK:
            self.log("User chose a URI to save project to")
            # need to do this to work around bug in gst.uri_construct
            # which escapes all /'s in path!
            uri = "file://" + chooser.get_filename()
            format = chooser.get_filter().get_name()
            if format == _("Detect Automatically"):
                format = None
            self.log("uri:%s , format:%s", uri, format)
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
            info = self.project.sources.getInfoFromUri(uri)
        except MediaLibraryError:
            self.project.sources.addUri(uri)
            # FIXME Add a delay/catch signal when we start doing the discovering
            # async
            info = self.project.sources.getInfoFromUri(uri)
        self._viewUri(info.get_uri())
        context.finish(True, False, ctime)

    def _leavePreviewCb(self, window, unused):
        window.destroy()

    def _viewUri(self, path):
        """ Preview a media file from the media library """
        preview_window = gtk.Window()
        preview_window.set_title(_("Preview - click outside to close"))
        preview_window.set_transient_for(self)
        preview_window.connect("focus-out-event", self._leavePreviewCb)
        previewer = PreviewWidget(self)
        preview_window.add(previewer)

        preview_window.show_all()  # Needed for PreviewWidget to do its magic
        preview_window.hide()  # Hack to allow setting the window position
        previewer.previewUri(path)
        previewer.setMinimal()
        info = self.project.sources.getInfoFromUri(path)
        try:
            # For videos and images, automatically resize the window
            # Try to keep it 1:1 if it can fit within 85% of the parent window
            img_width = info.get_video_streams()[0].get_width()
            img_height = info.get_video_streams()[0].get_height()
            controls_height = previewer.bbox.size_request()[1]
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
        preview_window.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        preview_window.show()

        previewer.play()

    def _timelineSeekRelativeCb(self, unused_seeker, time):
        try:
            position = self.project_pipeline.query_position(gst.FORMAT_TIME)[0]
            position += time

            self.project_pipeline.seek(1.0, gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH,
                    gst.SEEK_TYPE_SET, position, gst.SEEK_TYPE_NONE, -1)
            self._seeker.setPosition(position)

        except Exception, e:
            self.error("seek failed %s %s %s", gst.TIME_ARGS(position), format, e)

    def _timelineSeekFlushCb(self, unused_seeker):
        try:
            position = self.project_pipeline.query_position(gst.FORMAT_TIME)[0]
            self.project_pipeline.seek(1.0, gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH,
                    gst.SEEK_TYPE_SET, position, gst.SEEK_TYPE_NONE, -1)
            self._seeker.setPosition(position)

        except Exception, e:
            self.error("seek failed %s %s %s", gst.TIME_ARGS(position), format, e)

    def _timelineSeekCb(self, ruler, position, format):
        try:
            # CLAMP (0, position, self.timeline.getDuration())
            position = sorted((0, position, self.timeline.getDuration()))[1]

            if not self.project_pipeline.seek(1.0, format, gst.SEEK_FLAG_FLUSH,
                    gst.SEEK_TYPE_SET, position, gst.SEEK_TYPE_NONE, -1):
                self.warning("Could not seek to %s", gst.TIME_ARGS(position))
            else:
                self._seeker.setPosition(position)

        except Exception, e:
            self.error("seek failed %s %s %s", gst.TIME_ARGS(position), format, e)

    def updateTitle(self):
        name = touched = ""
        if self.project:
            if self.project.name:
                name = self.project.name
            else:
                name = _("Untitled")
            if self.project.hasUnsavedModifications():
                touched = "*"
        title = u"%s%s \u2014 %s" % (touched, name, APPNAME)
        self.set_title(title)
