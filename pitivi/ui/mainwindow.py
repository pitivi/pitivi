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
import gst
import gst.pbutils

try:
    import gconf
except:
    HAVE_GCONF = False
else:
    HAVE_GCONF = True

from pitivi.projectsaver import ProjectSaver

from gettext import gettext as _

from timeline import Timeline
from projecttabs import ProjectTabs
from viewer import PitiviViewer
from pitivi.bin import SmartTimelineBin
from projectsettings import ProjectSettingsDialog
from pluginmanagerdialog import PluginManagerDialog
from webcam_managerdialog import WebcamManagerDialog
from netstream_managerdialog import NetstreamManagerDialog
from screencast_managerdialog import ScreencastManagerDialog
from encodingdialog import EncodingDialog
from pitivi.configure import pitivi_version, APPNAME, get_pixmap_dir, \
     get_global_pixmap_dir
from pitivi.ui import dnd
from pitivi.pipeline import Pipeline
from pitivi.action import ViewAction
from pitivi.factories.timeline import TimelineSourceFactory
from pitivi.settings import GlobalSettings

if HAVE_GCONF:
    D_G_INTERFACE = "/desktop/gnome/interface"

    for gconf_dir in (D_G_INTERFACE, ):
        gconf.client_get_default ().add_dir (gconf_dir, gconf.CLIENT_PRELOAD_NONE)

GlobalSettings.addConfigOption("fileSupportEnabled",
    environment="PITIVI_FILE_SUPPORT",
    default=True)

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

def create_stock_icons():
    """ Creates the pitivi-only stock icons """
    gtk.stock_add([
            ('pitivi-render', 'Render', 0, 0, 'pitivi'),
            ('pitivi-split', 'Split', 0, 0, 'pitivi'),
            ('pitivi-unlink', 'Unlink', 0, 0, 'pitivi'),
            ('pitivi-link', 'Link', 0, 0, 'pitivi'),
            ('pitivi-ungroup', 'Ungroup', 0, 0, 'pitivi'),
            ('pitivi-group', 'Group', 0, 0, 'pitivi'),
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


class PitiviMainWindow(gtk.Window):
    """
    Pitivi's main window
    """


    def __init__(self, instance):
        """ initialize with the Pitivi object """
        gst.log("Creating MainWindow")
        gtk.Window.__init__(self)
        self.actions = None
        self.toggleactions = None
        self.actiongroup = None
        self.error_dialogbox = None
        self.pitivi = instance
        self.settings = instance.settings
        self.is_fullscreen = self.settings.mainWindowFullScreen
        self.missing_plugins = []

    def load(self):
        """ load the user interface """
        create_stock_icons()
        self._setActions()
        self._createUi()
        self.pitivi.connect("new-project-loaded", self._newProjectLoadedCb)
        self.pitivi.connect("new-project-loading", self._newProjectLoadingCb)
        self.pitivi.connect("closing-project", self._closingProjectCb)
        self.pitivi.connect("new-project-failed", self._notProjectCb)
        self.pitivi.current.connect("save-uri-requested", self._saveAsDialogCb)
        self.pitivi.current.connect("confirm-overwrite", self._confirmOverwriteCb)
        self.pitivi.playground.connect("error", self._playGroundErrorCb)
        self.pitivi.current.sources.connect("file_added", self._sourcesFileAddedCb)

        self.pitivi.current.connect('missing-plugins',
                self._projectMissingPluginsCb)

        # if no webcams available, hide the webcam action
        self.pitivi.deviceprobe.connect("device-added", self.__deviceChangeCb)
        self.pitivi.deviceprobe.connect("device-removed", self.__deviceChangeCb)
        if len(self.pitivi.deviceprobe.getVideoSourceDevices()) < 1:
            self.webcam_button.set_sensitive(False)
        self.show_all()

    def _encodingDialogDestroyCb(self, unused_dialog):
        self.pitivi.gui.set_sensitive(True)

    def _recordCb(self, unused_button):
        # pause timeline !
        self.pitivi.playground.pause()

        win = EncodingDialog(self.pitivi.current, self.pitivi)
        win.window.connect("destroy", self._encodingDialogDestroyCb)
        self.pitivi.gui.set_sensitive(False)
        win.show()

    def _timelineDurationChangedCb(self, timeline, duration):
        if not isinstance(self.pitivi.playground.current, SmartTimelineBin):
            return

        self.render_button.set_sensitive((duration > 0) and True or False)

    def _currentPlaygroundChangedCb(self, playground, smartbin):
        if smartbin == playground.default:
            self.render_button.set_sensitive(False)
        else:
            if isinstance(smartbin, SmartTimelineBin):
                gst.info("switching to Timeline, setting duration to %s" %
                         (gst.TIME_ARGS(smartbin.project.timeline.duration)))
                smartbin.project.timeline.connect("duration-changed", 
                        self._timelineDurationChangedCb)
                if smartbin.project.timeline.duration > 0:
                    self.render_button.set_sensitive(True)
                else:
                    self.render_button.set_sensitive(False)
            else:
                self.render_button.set_sensitive(False)

    def _setActions(self):
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
            ("ProjectSettings", gtk.STOCK_PROPERTIES, _("Project settings"),
             None, _("Edit the project settings"), self._projectSettingsCb),
            ("RenderProject", 'pitivi-render' , _("_Render project"),
             None, _("Render project"), self._recordCb),
            ("PluginManager", gtk.STOCK_PREFERENCES ,
             _("_Plugins..."),
             None, _("Manage plugins"), self._pluginManagerCb),
            ("ImportfromCam", gtk.STOCK_ADD ,
             _("_Import from Webcam.."),
             None, _("Import Camera stream"), self._ImportWebcam),   
            ("Screencast", gtk.STOCK_ADD ,
             _("_Make screencast.."),
             None, _("Capture the desktop"), self._Screencast),   
            ("NetstreamCapture", gtk.STOCK_ADD ,
             _("_Capture Network Stream.."),
             None, _("Capture Network Stream"), self._ImportNetstream), 
            ("Quit", gtk.STOCK_QUIT, None, None, None, self._quitCb),
            ("About", gtk.STOCK_ABOUT, None, None,
             _("Information about %s") % APPNAME, self._aboutCb),
            ("File", None, _("_File")),
            ("Edit", None, _("_Edit")),
            ("View", None, _("_View")),
            ("Help", None, _("_Help")),
        ]

        self.toggleactions = [
            ("FullScreen", gtk.STOCK_FULLSCREEN, None, None,
             _("View the main window on the whole screen"), self._fullScreenCb)
        ]

        self.actiongroup = gtk.ActionGroup("mainwindow")
        self.actiongroup.add_actions(self.actions)
        self.actiongroup.add_toggle_actions(self.toggleactions)

        # deactivating non-functional actions
        # FIXME : reactivate them
        for action in self.actiongroup.list_actions():
            if action.get_name() == "RenderProject":
                self.render_button = action
            elif action.get_name() == "ImportfromCam":
                self.webcam_button = action
            elif action.get_name() == "Screencast":
                # FIXME : re-enable this action once istanbul integration is complete
                # and upstream istanbul has applied packages for proper interaction.
                action.set_visible(False)
            elif action.get_name() in [
                "ProjectSettings", "Quit", "File", "Edit", "Help",
                "About", "View", "FullScreen", "ImportSources",
                "ImportSourcesFolder", "PluginManager","ImportfromCam","NetstreamCapture"]:
                action.set_sensitive(True)
            elif action.get_name() in ["SaveProject", "SaveProjectAs",
                    "NewProject", "OpenProject"]:
                if not self.pitivi.settings.fileSupportEnabled:
                    action.set_sensitive(False)
            else:
                action.set_sensitive(False)

        self.uimanager = gtk.UIManager()
        self.add_accel_group(self.uimanager.get_accel_group())
        self.uimanager.insert_action_group(self.actiongroup, 0)
        self.uimanager.add_ui_from_file(os.path.join(os.path.dirname(
            os.path.abspath(__file__)), "actions.xml"))

        self.connect_after("key-press-event", self._keyPressEventCb)

    def _createUi(self):
        """ Create the graphical interface """
        self.set_title("%s v%s" % (APPNAME, pitivi_version))
        self.set_geometry_hints(min_width=800, min_height=480)
        self.connect("destroy", self._destroyCb)
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
        
        self.timeline = Timeline(self.uimanager)
        self.timeline.setProject(self.pitivi.current)
        
        vpaned.pack2(self.timeline, resize=True, shrink=False)
        hpaned = gtk.HPaned()
        vpaned.pack1(hpaned, resize=False, shrink=True)
        self.projecttabs = ProjectTabs()
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
        #self.viewer.detach_button.connect("clicked", self.__windowizeViewer, 
        #    hpaned)

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
            

        # timeline toolbar
        # FIXME: remove toolbar padding and shadow. In fullscreen mode, the
        # toolbar buttons should be clickable with the mouse cursor at the
        # very bottom of the screen.
        vbox.pack_start(self.uimanager.get_widget("/TimelineToolBar"),
            False)

        #application icon
        self.set_icon_from_file(get_global_pixmap_dir() 
            + "/pitivi.png")

    def toggleFullScreen(self):
        """ Toggle the fullscreen mode of the application """
        if not self.is_fullscreen:
            self.viewer.window.fullscreen()
            self.is_fullscreen = True
        else:
            self.viewer.window.unfullscreen()
            self.is_fullscreen = False

## PlayGround callback

    def __windowizeViewer(self, button, pane):
        # FIXME: the viewer can't seem to handle being unparented/reparented
        pane.remove(self.viewer)
        window = gtk.Window()
        window.add(self.viewer)
        window.connect("destroy", self.__reparentViewer, pane)
        window.resize(200, 200)
        window.show_all()

    def __reparentViewer(self, window, pane):
        window.remove(self.viewer)
        pane.pack2(self.viewer, resize=False, shrink=False)
        self.viewer.show()

    def _errorMessageResponseCb(self, dialogbox, unused_response):
        dialogbox.hide()
        dialogbox.destroy()
        self.error_dialogbox = None

    def _playGroundErrorCb(self, unused_playground, error, detail):
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

## Project source list callbacks

    def _sourcesFileAddedCb(self, unused_sources, unused_factory):
        #if (len(self.sourcefactories.sourcelist.storemodel) == 1 
        #    and not len(self.pitivi.current.timeline.videocomp):
        pass
    
    def _projectMissingPluginsCb(self, project, uri, detail, message):
        self.missing_plugins.append(uri)
        return self._installPlugins(detail)

    def _installPlugins(self, details):
        context = gst.pbutils.InstallPluginsContext()
        context.set_xid(self.window.xid)

        res = gst.pbutils.install_plugins_async(details, context,
                self._installPluginsAsyncCb)
        return res

    def _installPluginsAsyncCb(self, result):
        missing_plugins, self.missing_plugins = self.missing_plugins, []
        
        if result != gst.pbutils.INSTALL_PLUGINS_SUCCESS:
            return

        gst.update_registry()
        self.pitivi.current.sources.addUris(missing_plugins)

## UI Callbacks

    def _configureCb(self, unused_widget, event):
        self.settings.mainWindowWidth = event.width
        self.settings.mainWindowHeight = event.height

    def _destroyCb(self, unused_widget, unused_data=None):
        self._saveWindowSettings()
        self.pitivi.shutdown()

    def _saveWindowSettings(self):
        self.settings.mainWindowFullscreen = self.is_fullscreen
        self.settings.mainWindowHPanePosition = self.hpaned.get_position()
        self.settings.mainWindowVPanePosition = self.vpaned.get_position()
        width, height = self.get_size()

    def _keyPressEventCb(self, unused_widget, event):
        if gtk.gdk.keyval_name(event.keyval) in ['f', 'F', 'F11']:
            self.toggleFullScreen()

## Toolbar/Menu actions callback

    def _newProjectMenuCb(self, unused_action):
        self.pitivi.newBlankProject()

    def _openProjectCb(self, unused_action):
        chooser = gtk.FileChooserDialog(_("Open File ..."),
            self,
            action=gtk.FILE_CHOOSER_ACTION_OPEN,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        chooser.set_select_multiple(False)
        chooser.set_current_folder(self.settings.lastProjectFolder)
        formats = ProjectSaver.listFormats()
        for format in formats:
            filt = gtk.FileFilter()
            filt.set_name(format[0])
            for ext in format[1]:
                filt.add_pattern("*%s" % ext)
            chooser.add_filter(filt)
        default = gtk.FileFilter()
        default.set_name("All")
        default.add_pattern("*")
        chooser.add_filter(default)

        response = chooser.run()
        self.settings.lastProjectFolder = chooser.get_current_folder()
        if response == gtk.RESPONSE_OK:
            path = chooser.get_filename()
            self.pitivi.loadProject(filepath = path)

        chooser.destroy()
        return True

    def _saveProjectCb(self, unused_action):
        self.pitivi.current.save()

    def _saveProjectAsCb(self, unused_action):
        self.pitivi.current.saveAs()

    def _projectSettingsCb(self, unused_action):
        ProjectSettingsDialog(self, self.pitivi.current).show()

    def _quitCb(self, unused_action):
        self._saveWindowSettings()
        self.pitivi.shutdown()

    def _fullScreenCb(self, unused_action):
        self.toggleFullScreen()

    def _aboutResponseCb(self, dialog, unused_response):
        dialog.destroy()

    def _aboutCb(self, unused_action):
        abt = gtk.AboutDialog()
        abt.set_name(APPNAME)
        abt.set_version("v%s" % pitivi_version)
        abt.set_website("http://www.pitivi.org/")
        authors = ["Edward Hervey <bilboed@bilboed.com>",
                   "",
                   _("Contributors:"),
                   "Christophe Sauthier <christophe.sauthier@gmail.com> (i18n)",
                   "Laszlo Pandy <laszlok2@gmail.com> (UI)",
                   "Ernst Persson  <ernstp@gmail.com>",
                   "Richard Boulton <richard@tartarus.org>",
                   "Thibaut Girka <thibaut.girka@free.fr> (UI)",
                   "Jeff Fortin <nekohayo@gmail.com> (UI)",
                   "Johan Dahlin <jdahlin@async.com.br> (UI)",
                   "Brandon Lewis <brandon_lewis@berkeley.edu> (UI)",
                   "Luca Della Santina <dellasantina@farm.unipi.it>",
                   "Thijs Vermeir <thijsvermeir@gmail.com>",
                   "Sarath Lakshman <sarathlakshman@slynux.org>"]
        abt.set_authors(authors)
        abt.set_license(_("GNU Lesser General Public License\n"
                          "See http://www.gnu.org/copyleft/lesser.html for more details"))
        abt.set_icon_from_file(get_global_pixmap_dir() + "/pitivi.png")
        abt.connect("response", self._aboutResponseCb)
        abt.show()

    def _pluginManagerCb(self, unused_action):
        PluginManagerDialog(self.pitivi.plugin_manager)

    # Import from Webcam callback
    def _ImportWebcam(self,unused_action):
        w = WebcamManagerDialog(self.pitivi)
        w.show()

    # Capture network stream callback
    def _ImportNetstream(self,unused_action):
        NetstreamManagerDialog()

    # screencast callback
    def _Screencast(self,unused_action):
        ScreencastManagerDialog()

    ## Devices changed
    def __deviceChangeCb(self, probe, unused_device):
        if len(probe.getVideoSourceDevices()) < 1:
            self.webcam_button.set_sensitive(False)
        else:
            self.webcam_button.set_sensitive(True)

    ## PiTiVi main object callbacks

    def _newProjectLoadedCb(self, unused_pitivi, project):
        gst.log("A NEW project is loaded, update the UI!")
        self.timeline.setProject(project)
        # ungrey UI
        self.set_sensitive(True)

    def _newProjectLoadingCb(self, unused_pitivi, unused_project):
        gst.log("A NEW project is being loaded, deactivate UI")
        # grey UI
        self.set_sensitive(False)

    def _closingProjectCb(self, unused_pitivi, project):
        if not project.hasUnsavedModifications():
            return True

        dialog = gtk.MessageDialog(
            self,
            gtk.DIALOG_MODAL,
            gtk.MESSAGE_QUESTION,
            gtk.BUTTONS_YES_NO,
            _("The project has unsaved changes. Do you wish to close the project?"))
        response = dialog.run()
        dialog.destroy()
        if response == gtk.RESPONSE_YES:
            return True
        return False

    def _notProjectCb(self, unused_pitivi, reason, uri):
        # ungrey UI
        dialog = gtk.MessageDialog(self,
            gtk.DIALOG_MODAL,
            gtk.MESSAGE_ERROR,
            gtk.BUTTONS_OK,
            _("PiTiVi is unable to load file \"%s\"") %
                uri)
        dialog.set_title(_("Error Loading File"))
        dialog.set_property("secondary-text", reason)
        dialog.run()
        dialog.destroy()
        self.set_sensitive(True)

## PiTiVi current project callbacks

    def _confirmOverwriteCb(self, unused_project, uri):
        message = _("Do you wish to overwrite existing file \"%s\"?") %\
                 gst.uri_get_location(uri)

        dialog = gtk.MessageDialog(self,
            gtk.DIALOG_MODAL,
            gtk.MESSAGE_WARNING,
            gtk.BUTTONS_YES_NO,
            message)

        dialog.set_title(_("Overwrite Existing File?"))
        response = dialog.run()
        dialog.destroy()
        if response == gtk.RESPONSE_YES:
            return True
        return False

    def _saveAsDialogCb(self, project):
        gst.log("Save URI requested")
        chooser = gtk.FileChooserDialog(_("Save As..."),
            self,
            action=gtk.FILE_CHOOSER_ACTION_SAVE,
            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
            gtk.STOCK_SAVE, gtk.RESPONSE_OK))

        chooser.set_select_multiple(False)
        chooser.set_current_name(_("Untitled.pptv"))
        chooser.set_current_folder(self.settings.lastProjectFolder)
        formats = ProjectSaver.listFormats()
        for format in formats:
            filt = gtk.FileFilter()
            filt.set_name(format[0])
            for ext in format[1]:
                filt.add_pattern("*.%s" % ext)
            chooser.add_filter(filt)
        default = gtk.FileFilter()
        default.set_name(_("Detect Automatically"))
        default.add_pattern("*")
        chooser.add_filter(default)

        response = chooser.run()
        self.settings.lastProjectFolder = chooser.get_current_folder()

        if response == gtk.RESPONSE_OK:
            gst.log("User chose a URI to save project to")
            # need to do this to work around bug in gst.uri_construct
            # which escapes all /'s in path!
            uri = "file://" + chooser.get_filename()
            format = chooser.get_filter().get_name()
            if format == _("Detect Automatically"):
                format = None
            gst.log("uri:%s , format:%s" % (uri, format))
            project.setUri(uri, format)
            ret = True
        else:
            gst.log("User didn't choose a URI to save project to")
            ret = False

        chooser.destroy()
        return ret
    
    def _viewerDndDataReceivedCb(self, unused_widget, context, unused_x, unused_y,
                           selection, targetType, ctime):
        # FIXME : This should be handled by the main application who knows how
        # to switch between pipelines.
        gst.info("context:%s, targetType:%s" % (context, targetType))
        if targetType == dnd.TYPE_URI_LIST:
            uri = selection.data.strip().split("\n")[0].strip()
        elif targetType == dnd.TYPE_PITIVI_FILESOURCE:
            uri = selection.data
        else:
            context.finish(False, False, ctime)
            return

        # FIXME: we change the viewer pipeline unconditionally for now

        from pitivi.factories.file import FileSourceFactory
        # we need a pipeline for playback
        pipeline = Pipeline()
        factory = FileSourceFactory(uri)
        action = ViewAction()
        action.addProducers(factory)
        # FIXME: why do I have to call viewer.setAction ?
        self.viewer.setAction(action)
        self.viewer.setPipeline(pipeline)
        pipeline.pause()

        context.finish(True, False, ctime)
    
    def _timelineDragMotionCb(self, unused_layout, unused_context, x, y, timestamp):
        # FIXME: temporarily add source to timeline, and put it in drag mode
        # so user can see where it will go
        gst.info("SimpleTimeline x:%d , source would go at %d" % (x, 0))

    def _timelineDragDataReceivedCb(self, unused_layout, context, x, y, 
        selection, targetType, timestamp):
        gst.log("SimpleTimeline, targetType:%d, selection.data:%s" % 
            (targetType, selection.data))
        if targetType == dnd.TYPE_PITIVI_FILESOURCE:
            uri = selection.data
        else:
            context.finish(False, False, timestamp)
        factory = self.pitivi.current.sources[uri]

        # FIXME: the UI should be smart here and figure out which track the
        # source was dragged onto
        self.pitivi.current.timeline.addSourceFactory(factory)
        context.finish(True, False, timestamp)


    def _getTimelinePipeline(self):
        # FIXME: the timeline pipeline should probably be moved in project
        if hasattr(self, '_timeline_pipeline') and hasattr(self, '_timeline_view_action'):
            return self._timeline_pipeline, self._timeline_view_action

        timeline = self.pitivi.current.timeline
        factory = TimelineSourceFactory(timeline)
        pipeline = Pipeline()
        pipeline.activatePositionListener()
        pipeline.connect('position', self._timelinePipelinePositionChangedCb)
        action = ViewAction()
        action.addProducers(factory)

        self._timeline_pipeline = pipeline
        self._timeline_view_action = action

        return self._timeline_pipeline, self._timeline_view_action

    def _timelineRulerSeekCb(self, ruler, position):
        pipeline, action = self._getTimelinePipeline()
        self.viewer.setAction(action)
        self.viewer.setPipeline(pipeline)
        pipeline.pause()
        pipeline.seek(position)

    def _timelinePipelinePositionChangedCb(self, pipeline, position):
        self.timeline.ruler.timelinePositionChanged(position)
