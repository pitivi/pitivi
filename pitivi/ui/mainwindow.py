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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""
Main GTK+ window
"""

import os
import gtk
import gobject
gobject.threads_init()
import gst
import gst.pbutils
from urllib import unquote

try:
    import gconf
except:
    HAVE_GCONF = False
else:
    HAVE_GCONF = True

from gettext import gettext as _

from pitivi.log.loggable import Loggable

from pitivi.ui.timeline import Timeline
from pitivi.ui.projecttabs import ProjectTabs
from pitivi.ui.viewer import PitiviViewer
from pitivi.configure import pitivi_version, APPNAME, get_pixmap_dir, \
     get_global_pixmap_dir
from pitivi.ui import dnd
from pitivi.pipeline import Pipeline
from pitivi.action import ViewAction
from pitivi.settings import GlobalSettings
from pitivi.receiver import receiver, handler
import pitivi.formatters.format as formatter
from pitivi.sourcelist import SourceListError
from pitivi.ui.sourcelist import SourceList
from pitivi.ui.common import beautify_factory
from pitivi.utils import beautify_length
from pitivi.ui.zoominterface import Zoomable

if HAVE_GCONF:
    D_G_INTERFACE = "/desktop/gnome/interface"

    for gconf_dir in (D_G_INTERFACE, ):
        gconf.client_get_default ().add_dir (gconf_dir, gconf.CLIENT_PRELOAD_NONE)

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
    default = 620)
GlobalSettings.addConfigOption('elementSettingsDialogHeight',
    section='export',
    key='element-settings-dialog-height',
    default = 460)

def supported(info):
    return formatter.can_handle_location(info[1])

def create_stock_icons():
    """ Creates the pitivi-only stock icons """
    gtk.stock_add([
            ('pitivi-render', _('Render'), 0, 0, 'pitivi'),
            ('pitivi-split', _('Split'), 0, 0, 'pitivi'),
            ('pitivi-unlink', _('Unlink'), 0, 0, 'pitivi'),
            # Translators: This is an action, the title of a button
            ('pitivi-link', _('Link'), 0, 0, 'pitivi'),
            ('pitivi-ungroup', _('Ungroup'), 0, 0, 'pitivi'),
            # Translators: This is an action, the title of a button
            ('pitivi-group', _('Group'), 0, 0, 'pitivi'),
            ])
    pixmaps = {
        "pitivi-render" : "pitivi-render-24.png",
        "pitivi-split" : "pitivi-split-24.svg",
        "pitivi-unlink" : "pitivi-unlink-24.svg",
        "pitivi-link" : "pitivi-relink-24.svg",
        "pitivi-ungroup" : "pitivi-unlink-24.svg",
        "pitivi-group" : "pitivi-relink-24.svg",
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


    def __init__(self, instance):
        """ initialize with the Pitivi object """
        gtk.Window.__init__(self)
        Loggable.__init__(self)
        self.log("Creating MainWindow")
        self.actions = None
        self.toggleactions = None
        self.actiongroup = None
        self.error_dialogbox = None
        self.settings = instance.settings
        self.is_fullscreen = self.settings.mainWindowFullScreen
        self.timelinepos = 0
        self.prefsdialog = None
        create_stock_icons()
        self._setActions(instance)
        self._createUi(instance)
        self.app = instance

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
        self.app.projectManager.connect("project-closed",
                self._projectManagerProjectClosedCb)
        self.app.projectManager.connect("missing-uri",
                self._projectManagerMissingUriCb)

        self.app.action_log.connect("commit", self._actionLogCommit)
        self.app.action_log.connect("undo", self._actionLogUndo)
        self.app.action_log.connect("redo", self._actionLogRedo)
        self.app.action_log.connect("cleaned", self._actionLogCleaned)

        # if no webcams available, hide the webcam action
        self.app.deviceprobe.connect("device-added", self._deviceChangeCb)
        self.app.deviceprobe.connect("device-removed", self._deviceChangeCb)
        if len(self.app.deviceprobe.getVideoSourceDevices()) < 1:
            self.webcam_button.set_sensitive(False)

        self.show()

    def showEncodingDialog(self, project, pause=True):
        """
        Shows the L{EncodingDialog} for the given project Timeline.

        @param project: The project
        @type project: L{Project}
        @param pause: If C{True}, pause the timeline before displaying the dialog.
        @type pause: C{bool}
        """
        from encodingdialog import EncodingDialog

        if pause:
            project.pipeline.pause()
        win = EncodingDialog(self, project)
        win.window.connect("destroy", self._encodingDialogDestroyCb)
        self.set_sensitive(False)
        win.show()

    def _encodingDialogDestroyCb(self, unused_dialog):
        self.set_sensitive(True)

    def _recordCb(self, unused_button):
        self.showEncodingDialog(self.project)

    def _setActions(self, instance):
        PLAY = _("Start Playback")
        PAUSE = _("Stop Playback")
        LOOP = _("Loop over selected area")

        """ sets up the GtkActions """
        self.actions = [
            ("NewProject", gtk.STOCK_NEW, None,
             None, _("Create a new project"), self._newProjectMenuCb),
            ("OpenProject", gtk.STOCK_OPEN, None,
             None, _("Open an existing project"), self._openProjectCb),
            ("SaveProject", gtk.STOCK_SAVE, None,
             None, _("Save the current project"), self._saveProjectCb),
            ("SaveProjectAs", gtk.STOCK_SAVE_AS, None,
             None, _("Save the current project"), self._saveProjectAsCb),
            ("ProjectSettings", gtk.STOCK_PROPERTIES, _("Project Settings"),
             None, _("Edit the project settings"), self._projectSettingsCb),
            ("RenderProject", 'pitivi-render' , _("_Render project"),
             None, _("Render project"), self._recordCb),
            ("Undo", gtk.STOCK_UNDO,
             _("_Undo"),
             "<Ctrl>Z", _("Undo the last operation"), self._undoCb),
            ("Redo", gtk.STOCK_REDO,
             _("_Redo"),
             "<Ctrl>Y", _("Redo the last operation that was undone"), self._redoCb),
            ("PluginManager", gtk.STOCK_PREFERENCES ,
             _("_Plugins..."),
             None, _("Manage plugins"), self._pluginManagerCb),
            ("Preferences", gtk.STOCK_PREFERENCES, _("_Preferences"),
              None, None, self._prefsCb),
            ("ImportfromCam", gtk.STOCK_ADD ,
             _("Import from _Webcam..."),
             None, _("Import Camera stream"), self._ImportWebcam),
            ("Screencast", gtk.STOCK_ADD ,
             _("_Make screencast..."),
             None, _("Capture the desktop"), self._Screencast),
            ("NetstreamCapture", gtk.STOCK_ADD ,
             _("_Capture Network Stream..."),
             None, _("Capture Network Stream"), self._ImportNetstream),
            ("Quit", gtk.STOCK_QUIT, None, None, None, self._quitCb),
            ("About", gtk.STOCK_ABOUT, None, None,
             _("Information about %s") % APPNAME, self._aboutCb),
            ("File", None, _("_File")),
            ("Edit", None, _("_Edit")),
            ("View", None, _("_View")),
            ("Library", None, _("_Project")),
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

        # deactivating non-functional actions
        # FIXME : reactivate them
        save_action = self.actiongroup.get_action("SaveProject")
        save_action.set_sensitive(False)

        for action in self.actiongroup.list_actions():
            action_name = action.get_name()
            if action_name == "RenderProject":
                self.render_button = action
                # this will be set sensitive when the timeline duration changes
                action.set_sensitive(False)
                action.props.is_important = True
            elif action_name == "ImportfromCam":
                self.webcam_button = action
                action.set_sensitive(False)
            elif action_name == "Screencast":
                # FIXME : re-enable this action once istanbul integration is complete
                # and upstream istanbul has applied packages for proper interaction.
                action.set_sensitive(False)
                action.set_visible(False)
            elif action_name in [
                "ProjectSettings", "Quit", "File", "Edit", "Help", "About",
                "View", "FullScreen", "FullScreenAlternate",
                "ImportSourcesFolder", "PluginManager", "PlayPause",
                "Project", "FrameForward", "FrameBackward",
                "ShowHideMainToolbar", "ShowHideTimelineToolbar", "Library",
                "Timeline", "Viewer", "FrameForward", "FrameBackward",
                "SecondForward", "SecondBackward", "EdgeForward",
                "EdgeBackward", "Preferences"]:
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
        self.uimanager.add_ui_from_file(os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "mainwindow.xml"))

    def _createUi(self, instance):
        """ Create the graphical interface """
        self.set_title("%s v%s" % (APPNAME, pitivi_version))
        self.connect("delete-event", self._deleteCb)
        self.connect("configure-event", self._configureCb)

        # main menu & toolbar
        vbox = gtk.VBox(False)
        self.add(vbox)
        self.menu = self.uimanager.get_widget("/MainMenuBar")
        vbox.pack_start(self.menu, expand=False)
        self.toolbar = self.uimanager.get_widget("/MainToolBar")
        vbox.pack_start(self.toolbar, expand=False)
        # timeline and project tabs
        vpaned = gtk.VPaned()
        vbox.pack_start(vpaned)

        self.timeline = Timeline(instance, self.uimanager)
        self.timeline.project = self.project

        vpaned.pack2(self.timeline, resize=False, shrink=False)
        hpaned = gtk.HPaned()
        vpaned.pack1(hpaned, resize=True, shrink=False)
        self.projecttabs = ProjectTabs()

        self.sourcelist = SourceList(instance, self.uimanager)
        self.projecttabs.append_page(self.sourcelist, gtk.Label(_("Clip Library")))
        self._connectToSourceList()

        hpaned.pack1(self.projecttabs, resize=True, shrink=False)

        self.timeline.ruler.connect('seek', self._timelineRulerSeekCb)

        # Viewer
        self.viewer = PitiviViewer()
        # drag and drop
        self.viewer.drag_dest_set(gtk.DEST_DEFAULT_DROP | gtk.DEST_DEFAULT_MOTION,
                           [dnd.FILESOURCE_TUPLE, dnd.URI_TUPLE],
                           gtk.gdk.ACTION_COPY)
        self.viewer.connect("drag_data_received", self._viewerDndDataReceivedCb)
        hpaned.pack2(self.viewer, resize=False, shrink=False)
        self.viewer.connect("expose-event", self._exposeEventCb)

        # window and pane position defaults
        self.hpaned = hpaned
        self.vpaned = vpaned
        height = -1
        width = -1
        if self.settings.mainWindowHPanePosition:
            self.hpaned.set_position(self.settings.mainWindowHPanePosition)
        if self.settings.mainWindowVPanePosition:
            self.vpaned.set_position(self.settings.mainWindowVPanePosition)
        if self.settings.mainWindowWidth:
            width = self.settings.mainWindowWidth
        if self.settings.mainWindowHeight:
            height = self.settings.mainWindowHeight
        self.set_default_size(width, height)
        if height == -1 and width == -1:
            self.maximize()
        self._do_pending_fullscreen = False
        # FIXME: don't know why this doesn't work
        #if self.settings.mainWindowFullScreen:
        #    self._do_pending_fullscreen = True

        # timeline toolbar
        # FIXME: remove toolbar padding and shadow. In fullscreen mode, the
        # toolbar buttons should be clickable with the mouse cursor at the
        # very bottom of the screen.
        ttb = self.uimanager.get_widget("/TimelineToolBar")
        vbox.pack_start(ttb, expand=False)

        self.show_all()

        if not self.settings.mainWindowShowMainToolbar:
            self.toolbar.props.visible = False

        if not self.settings.mainWindowShowTimelineToolbar:
            ttb.props.visible = False

        #application icon
        self.set_icon_name("pitivi")

    def _connectToSourceList(self):
        # FIXME: projecttabs creates the "components" but then has no API to get
        # them back
        self.sourcelist.connect('play', self._sourceListPlayCb)

    def toggleFullScreen(self):
        """ Toggle the fullscreen mode of the application """
        if not self.is_fullscreen:
            self.viewer.window.fullscreen()
            self.is_fullscreen = True
        else:
            self.viewer.window.unfullscreen()
            self.is_fullscreen = False

## PlayGround callback

    def _windowizeViewer(self, button, pane):
        # FIXME: the viewer can't seem to handle being unparented/reparented
        pane.remove(self.viewer)
        window = gtk.Window()
        window.add(self.viewer)
        window.connect("destroy", self._reparentViewer, pane)
        window.resize(200, 200)
        window.show_all()

    def _reparentViewer(self, window, pane):
        window.remove(self.viewer)
        pane.pack2(self.viewer, resize=False, shrink=False)
        self.viewer.show()

    def _errorMessageResponseCb(self, dialogbox, unused_response):
        dialogbox.hide()
        dialogbox.destroy()
        self.error_dialogbox = None

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

    def _exposeEventCb(self, unused_widget, event):
        if self._do_pending_fullscreen:
            self._fullScreenAlternateCb(None)
            self._do_pending_fullscreen = False

    def _saveWindowSettings(self):
        self.settings.mainWindowFullScreen = self.is_fullscreen
        self.settings.mainWindowHPanePosition = self.hpaned.get_position()
        self.settings.mainWindowVPanePosition = self.vpaned.get_position()
        mtb = self.actiongroup.get_action("ShowHideMainToolbar")
        ttb = self.actiongroup.get_action("ShowHideTimelineToolbar")
        self.settings.mainWindowShowMainToolbar = mtb.props.active
        self.settings.mainWindowShowTimelineToolbar = ttb.props.active


    def _sourceListPlayCb(self, sourcelist, factory):
        self._viewFactory(factory)

## Toolbar/Menu actions callback

    def _newProjectMenuCb(self, unused_action):
        self.app.projectManager.newBlankProject()

    def _openProjectCb(self, unused_action):

        chooser = gtk.FileChooserDialog(_("Open File..."),
            self,
            action=gtk.FILE_CHOOSER_ACTION_OPEN,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        chooser.set_icon_name("pitivi")
        chooser.set_select_multiple(False)
        chooser.set_current_folder(self.settings.lastProjectFolder)
        formats = formatter.list_formats()
        for format in formats:
            filt = gtk.FileFilter()
            filt.set_name(format[1])
            for ext in format[2]:
                filt.add_pattern("*%s" % ext)
            chooser.add_filter(filt)
        default = gtk.FileFilter()
        default.set_name(_("All Supported Formats"))
        default.add_custom(gtk.FILE_FILTER_URI, supported)
        chooser.add_filter(default)

        response = chooser.run()
        self.settings.lastProjectFolder = chooser.get_current_folder()
        if response == gtk.RESPONSE_OK:
            uri = chooser.get_uri()
            uri = unquote(uri)
            self.app.projectManager.loadProject(uri)

        chooser.destroy()
        return True

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

    def _projectSettingsCb(self, unused_action):
        from projectsettings import ProjectSettingsDialog
        ProjectSettingsDialog(self, self.app.current).show()

    def _quitCb(self, unused_action):
        self._saveWindowSettings()
        self.app.shutdown()

    def _fullScreenCb(self, unused_action):
        self.toggleFullScreen()

    def _fullScreenAlternateCb(self, unused_action):
        self.actiongroup.get_action("FullScreen").activate()

    def _showHideMainToolBar(self, action):
        self.uimanager.get_widget("/MainToolBar").props.visible = \
            action.props.active

    def _showHideTimelineToolbar(self, action):
        self.uimanager.get_widget("/TimelineToolBar").props.visible = \
            action.props.active

    def _aboutResponseCb(self, dialog, unused_response):
        dialog.destroy()

    def _showWebsiteCb(self, dialog, uri):
        import webbrowser
        webbrowser.open_new(uri)

    def _aboutCb(self, unused_action):
        abt = gtk.AboutDialog()
        abt.set_name(APPNAME)
        abt.set_version("v%s" % pitivi_version)
        gtk.about_dialog_set_url_hook(self._showWebsiteCb)
        abt.set_website("http://www.pitivi.org/")
        authors = ["Edward Hervey <bilboed@bilboed.com>",
                   "Alessandro Decina <alessandro.decina@collabora.co.uk>",
                   "Brandon Lewis <brandon_lewis@berkeley.edu> (UI)",
                   "",
                   _("Contributors:"),
                   "Christophe Sauthier <christophe.sauthier@gmail.com> (i18n)",
                   "Laszlo Pandy <laszlok2@gmail.com> (UI)",
                   "Ernst Persson  <ernstp@gmail.com>",
                   "Richard Boulton <richard@tartarus.org>",
                   "Thibaut Girka <thibaut.girka@free.fr> (UI)",
                   "Jeff Fortin <nekohayo@gmail.com> (UI)",
                   "Johan Dahlin <jdahlin@async.com.br> (UI)",
                   "Luca Della Santina <dellasantina@farm.unipi.it>",
                   "Thijs Vermeir <thijsvermeir@gmail.com>",
                   "Sarath Lakshman <sarathlakshman@slynux.org>"]
        abt.set_authors(authors)
        abt.set_license(_("GNU Lesser General Public License\n"
                          "See http://www.gnu.org/copyleft/lesser.html for more details"))
        abt.set_icon_name("pitivi")
        abt.set_logo_icon_name("pitivi")
        abt.connect("response", self._aboutResponseCb)
        abt.show()

    def _undoCb(self, action):
        self.app.action_log.undo()

    def _redoCb(self, action):
        self.app.action_log.redo()

    def _pluginManagerCb(self, unused_action):
        from pluginmanagerdialog import PluginManagerDialog
        PluginManagerDialog(self.app.plugin_manager)

    # Import from Webcam callback
    def _ImportWebcam(self,unused_action):
        from webcam_managerdialog import WebcamManagerDialog
        w = WebcamManagerDialog(self.app)
        w.show()

    # Capture network stream callback
    def _ImportNetstream(self,unused_action):
        from netstream_managerdialog import NetstreamManagerDialog
        NetstreamManagerDialog()

    # screencast callback
    def _Screencast(self,unused_action):
        from screencast_managerdialog import ScreencastManagerDialog
        ScreencastManagerDialog(self.app)

    ## Devices changed
    def _deviceChangeCb(self, probe, unused_device):
        if len(probe.getVideoSourceDevices()) < 1:
            self.webcam_button.set_sensitive(False)
        else:
            self.webcam_button.set_sensitive(True)

    def _hideChildWindow(self, window, event):
        window.hide()
        return True

    def _prefsCb(self, unused_action):
        if not self.prefsdialog:
            from pitivi.ui.prefs import PreferencesDialog
            self.prefsdialog = PreferencesDialog(self.app)
            self.prefsdialog.set_transient_for(self)
            self.prefsdialog.connect("delete-event", self._hideChildWindow)
        self.prefsdialog.show()

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
        self.project = project
        self._connectToProjectSources(project.sources)
        can_render = project.timeline.duration > 0
        self.render_button.set_sensitive(can_render)
        self._syncDoUndo(self.app.action_log)

        if project.timeline.duration != 0:
            self._setBestZoomRatio()

    def _setBestZoomRatio(self):
        ruler_width = self.timeline.ruler.get_allocation()[2]
        timeline_duration = self.project.timeline.duration

        ideal_zoom_ratio = ruler_width / float(timeline_duration / gst.SECOND)
        nearest_zoom_level = Zoomable.computeZoomLevel(ideal_zoom_ratio)
        Zoomable.setZoomLevel(nearest_zoom_level)

    def _projectManagerNewProjectLoadingCb(self, projectManager, uri):
        self.log("A NEW project is being loaded, deactivate UI")

    def _projectManagerSaveProjectFailedCb(self, projectManager,
            project, uri, exception):
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
        vbox = gtk.VBox(False, 12)
        vbox.pack_start(primary, expand=True, fill=True)
        vbox.pack_start(secondary, expand=True, fill=True)

        # make the [[image] text] hbox
        image = gtk.image_new_from_stock(gtk.STOCK_DIALOG_WARNING,
               gtk.ICON_SIZE_DIALOG)
        hbox = gtk.HBox(False, 12)
        hbox.pack_start(image, expand=False)
        hbox.pack_start(vbox, expand=True, fill=True)
        action_area = dialog.get_action_area()
        # FIXME: find out where this "6" comes from. It's needed to align our
        # hbox with the action area button box
        hbox.set_border_width(6)

        # stuff the hbox in the dialog
        content_area = dialog.get_content_area()
        content_area.pack_start(hbox, expand=True, fill=True)
        content_area.set_spacing(14)
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
        self._disconnectFromProjectSources(project.sources)
        self.viewer.setAction(None)
        self.viewer.setPipeline(None)
        return False

    def _projectManagerNewProjectFailedCb(self, projectManager, uri, exception):
        # ungrey UI
        dialog = gtk.MessageDialog(self,
            gtk.DIALOG_MODAL,
            gtk.MESSAGE_ERROR,
            gtk.BUTTONS_OK,
            _("PiTiVi is unable to load file \"%s\"") %
                uri)
        dialog.set_icon_name("pitivi")
        dialog.set_title(_("Error Loading File"))
        dialog.set_property("secondary-text", str(exception))
        dialog.run()
        dialog.destroy()
        self.set_sensitive(True)

    def _projectManagerMissingUriCb(self, instance, formatter, uri, factory):
        dialog = gtk.Dialog(_("Locate missing file..."),
            self,
            gtk.DIALOG_MODAL,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
            gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_icon_name("pitivi")
        dialog.set_border_width(12)
        dialog.get_content_area().set_spacing(6)

        text = _("The following file has moved," +
            " please tell PiTiVi where to find it.") + "\n\n" + \
            beautify_factory(factory) + "\n" +\
            _("<b>Duration:</b>") + beautify_length(factory.duration)

        label = gtk.Label()
        label.set_markup(text)
        label.set_justify(gtk.JUSTIFY_CENTER)
        dialog.get_content_area().pack_start(label, False, False)
        label.show()

        chooser = gtk.FileChooserWidget(action=gtk.FILE_CHOOSER_ACTION_OPEN)
        chooser.set_select_multiple(False)
        chooser.set_current_folder(self.settings.lastProjectFolder)
        dialog.get_content_area().pack_start(chooser, True, True)
        chooser.show()

        dialog.set_size_request(640, 480)
        response = dialog.run()

        if response == gtk.RESPONSE_OK:
            self.log("User chose a URI to save project to")
            new = chooser.get_uri()
            if new:
                formatter.addMapping(uri, unquote(new))
        else:
            self.log("User didn't choose a URI to save project to")
            # FIXME: not calling addMapping doesn't keep the formatter from
            # re-emitting the same signal. How do we get out of this
            # situation?
            pass

        dialog.destroy()

    def _connectToProjectSources(self, sourcelist):
        sourcelist.connect("missing-plugins", self._sourceListMissingPluginsCb)

    def _disconnectFromProjectSources(self, sourcelist):
        sourcelist.disconnect_by_func(self._sourceListMissingPluginsCb)

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
        self.app.current.setModificationState(dirty)

        redo_action = self.actiongroup.get_action("Redo")
        can_redo = bool(action_log.redo_stacks)
        redo_action.set_sensitive(can_redo)

        if self.project is not None:
            app_name = "%s %s" % (APPNAME, pitivi_version)
            title = u"%s \u2014 %s" % (self.project.name, app_name)
            if dirty:
                title = "*" + title
            title = title.encode("utf8")
            self.set_title(title)

## PiTiVi current project callbacks

    def _setProject(self):
        if self.project:
            self.project_pipeline = self.project.pipeline
            self.project_timeline = self.project.timeline
            if self.timeline:
                self.timeline.project = self.project

    project = receiver(_setProject)

    @handler(project, "settings-changed")
    def _settingsChangedCb(self, project):
        if self.viewer.action == self.project.view_action:
            sett = self.project.getSettings()
            self.viewer.setDisplayAspectRatio(float(sett.videopar * sett.videowidth) / float(sett.videoheight))

    def _sourceListMissingPluginsCb(self, project, uri, factory,
            details, descriptions, missingPluginsCallback):
        res = self._installPlugins(details, missingPluginsCallback)
        return res

## Current Project Pipeline

    def _setProjectPipeline(self):
        if self.project_pipeline:
            # connect to timeline
            self.project_pipeline.activatePositionListener()
            self._timelinePipelinePositionChangedCb(self.project_pipeline, 0)

    project_pipeline = receiver()

    @handler(project_pipeline, "error")
    def _pipelineErrorCb(self, unused_pipeline, error, detail):
        # FIXME FIXME FIXME:
        # _need_ an onobtrusive way to present gstreamer errors,
        # one that doesn't steel mouse/keyboard focus, one that
        # makes some kind of sense to the user, and one that presents
        # some ways of actually _dealing_ with the underlying problem:
        # install a plugin, re-conform source to some other format, or
        # maybe even disable playback of a problematic file.
        if self.error_dialogbox:
            return
        self.error_dialogbox = gtk.MessageDialog(None, gtk.DIALOG_MODAL,
            gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, None)
        self.error_dialogbox.set_markup("<b>%s</b>" % error)
        self.error_dialogbox.connect("response", self._errorMessageResponseCb)
        if detail:
            self.error_dialogbox.format_secondary_text(detail)
        self.error_dialogbox.show()

    @handler(project_pipeline, "position")
    def _timelinePipelinePositionChangedCb(self, pipeline, position):
        self.timeline.timelinePositionChanged(position)
        self.timelinepos = position

    @handler(project_pipeline, "state-changed")
    def _timelinePipelineStateChangedCb(self, pipeline, state):
        self.timeline.stateChanged(state)

## Project Timeline (not to be confused with UI timeline)

    project_timeline = receiver()

    @handler(project_timeline, "duration-changed")
    def _timelineDurationChangedCb(self, timeline, duration):
        if duration > 0:
            sensitive = True
        else:
            sensitive = False
        self.render_button.set_sensitive(sensitive)

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
        chooser.set_current_name(_("Untitled.xptv"))
        chooser.set_current_folder(self.settings.lastProjectFolder)
        chooser.props.do_overwrite_confirmation = True
        formats = formatter.list_formats()
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
        self.settings.lastProjectFolder = chooser.get_current_folder()

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
        if targetType == dnd.TYPE_URI_LIST:
            uri = selection.data.strip().split("\n")[0].strip()
        elif targetType == dnd.TYPE_PITIVI_FILESOURCE:
            uri = selection.data
        else:
            context.finish(False, False, ctime)
            return

        # Use factory from our source list if we have the given uri
        try:
            fact = self.project.sources.getUri(uri)
        except SourceListError:
            from pitivi.factories.file import FileSourceFactory
            fact = FileSourceFactory(uri)
        self._viewFactory(fact)
        context.finish(True, False, ctime)

    def _viewFactory(self, factory):
        # FIXME: we change the viewer pipeline unconditionally for now
        # we need a pipeline for playback
        pipeline = Pipeline()
        action = ViewAction()
        action.addProducers(factory)
        self.viewer.setPipeline(None)
        # FIXME: why do I have to call viewer.setAction ?
        self.viewer.setAction(action)
        self.viewer.setPipeline(pipeline)
        self.viewer.play()

    def _timelineRulerSeekCb(self, ruler, position):
        self.debug("position:%s", gst.TIME_ARGS (position))
        if self.viewer.action != self.project.view_action:
            self.viewer.setPipeline(None)
            self.viewer.setAction(self.project.view_action)
            self.viewer.setPipeline(self.project.pipeline)
            # get the pipeline settings and set the DAR of the viewer
            sett = self.project.getSettings()
            self.viewer.setDisplayAspectRatio(float(sett.videopar * sett.videowidth) / float(sett.videoheight))
        # everything above only needs to be done if the viewer isn't already
        # set to the pipeline.
        self.project.pipeline.pause()
        try:
            self.project.pipeline.seek(position)
        except:
            self.debug("Seeking failed")

