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
from gettext import gettext as _
from time import time
from urllib.parse import unquote

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gio
from gi.repository import GstPbutils
from gi.repository import Gtk

from pitivi.clipproperties import ClipProperties
from pitivi.configure import APPNAME
from pitivi.configure import get_ui_dir
from pitivi.dialogs.prefs import PreferencesDialog
from pitivi.effects import EffectListWidget
from pitivi.mediafilespreviewer import PreviewWidget
from pitivi.medialibrary import AssetThumbnail
from pitivi.medialibrary import MediaLibraryWidget
from pitivi.perspective import Perspective
from pitivi.project import ProjectSettingsDialog
from pitivi.settings import GlobalSettings
from pitivi.tabsmanager import BaseTabs
from pitivi.timeline.timeline import TimelineContainer
from pitivi.titleeditor import TitleEditor
from pitivi.transitions import TransitionsListWidget
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import path_from_uri
from pitivi.utils.ui import beautify_missing_asset
from pitivi.utils.ui import beautify_time_delta
from pitivi.utils.ui import clear_styles
from pitivi.utils.ui import info_name
from pitivi.utils.ui import PADDING
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
GlobalSettings.addConfigOption('lastProjectFolder',
                               section="main-window",
                               key="last-folder",
                               environment="PITIVI_PROJECT_FOLDER",
                               default=os.path.expanduser("~"))


class EditorPerspective(Perspective, Loggable):
    """Pitivi's Editor perspective.

    Attributes:
        app (Pitivi): The app.
    """

    def __init__(self, app):
        Perspective.__init__(self)
        Loggable.__init__(self)

        self.app = app
        self.settings = app.settings

        self.builder_handler_ids = []
        self.builder = Gtk.Builder()

        pm = self.app.project_manager
        pm.connect("new-project-loaded",
                   self._projectManagerNewProjectLoadedCb)
        pm.connect("save-project-failed",
                   self._projectManagerSaveProjectFailedCb)
        pm.connect("project-saved", self._projectManagerProjectSavedCb)
        pm.connect("closing-project", self._projectManagerClosingProjectCb)
        pm.connect("reverting-to-saved",
                   self._projectManagerRevertingToSavedCb)
        pm.connect("project-closed", self._projectManagerProjectClosedCb)
        pm.connect("missing-uri", self._projectManagerMissingUriCb)

    def setup_ui(self):
        """Sets up the UI."""
        self.__setup_css()
        self._createUi()
        self.app.gui.connect("destroy", self._destroyedCb)

    def refresh(self):
        """Refreshes the perspective."""
        self.main_tabs.grab_focus()

    def __setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(TIMELINE_CSS.encode('UTF-8'))
        screen = Gdk.Screen.get_default()
        style_context = self.app.gui.get_style_context()
        style_context.add_provider_for_screen(screen, css_provider,
                                              Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _destroyedCb(self, unused_main_window):
        """Cleanup before destroying this window."""
        pm = self.app.project_manager
        pm.disconnect_by_func(self._projectManagerNewProjectLoadedCb)
        pm.disconnect_by_func(self._projectManagerSaveProjectFailedCb)
        pm.disconnect_by_func(self._projectManagerProjectSavedCb)
        pm.disconnect_by_func(self._projectManagerClosingProjectCb)
        pm.disconnect_by_func(self._projectManagerRevertingToSavedCb)
        pm.disconnect_by_func(self._projectManagerProjectClosedCb)
        pm.disconnect_by_func(self._projectManagerMissingUriCb)
        self.toplevel_widget.remove(self.timeline_ui)
        self.timeline_ui.destroy()

    def _renderCb(self, unused_button):
        """Shows the RenderDialog for the current project."""
        from pitivi.render import RenderDialog

        project = self.app.project_manager.current_project
        dialog = RenderDialog(self.app, project)
        dialog.window.show()

    def _createUi(self):
        """Creates the graphical interface.

        The rough hierarchy is:
        vpaned:
        - mainhpaned(secondhpaned(main_tabs, context_tabs), viewer)
        - timeline_ui

        The full hierarchy can be admired by starting the GTK+ Inspector
        with Ctrl+Shift+I.
        """
        # Main "toolbar" (using client-side window decorations with HeaderBar)
        self.headerbar = self.__create_headerbar()

        # Set up our main containers, in the order documented above

        # Separates the tabs+viewer from the timeline
        self.toplevel_widget = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        # Separates the tabs from the viewer
        self.mainhpaned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        # Separates the two sets of tabs
        self.secondhpaned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.toplevel_widget.pack1(self.mainhpaned, resize=False, shrink=False)
        self.mainhpaned.pack1(self.secondhpaned, resize=True, shrink=False)
        self.toplevel_widget.show()
        self.secondhpaned.show()
        self.mainhpaned.show()

        # First set of tabs
        self.main_tabs = BaseTabs(self.app)
        self.medialibrary = MediaLibraryWidget(self.app)
        self.effectlist = EffectListWidget(self.app)
        self.main_tabs.append_page("Media Library",
            self.medialibrary, Gtk.Label(label=_("Media Library")))
        self.main_tabs.append_page("Effect Library",
            self.effectlist, Gtk.Label(label=_("Effect Library")))
        self.medialibrary.connect('play', self._mediaLibraryPlayCb)
        self.medialibrary.show()
        self.effectlist.show()

        # Second set of tabs
        self.context_tabs = BaseTabs(self.app)
        self.clipconfig = ClipProperties(self.app)
        self.trans_list = TransitionsListWidget(self.app)
        self.title_editor = TitleEditor(self.app)
        self.context_tabs.append_page("Clip",
            self.clipconfig, Gtk.Label(label=_("Clip")))
        self.context_tabs.append_page("Transition",
            self.trans_list, Gtk.Label(label=_("Transition")))
        self.context_tabs.append_page("Title",
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
        self.toplevel_widget.pack2(self.timeline_ui, resize=True, shrink=False)

        # Setup shortcuts for HeaderBar buttons and menu items.
        self.__set_keyboard_shortcuts()

        # Identify widgets for AT-SPI, making our test suite easier to develop
        # These will show up in sniff, accerciser, etc.
        self.headerbar.get_accessible().set_name("editor_headerbar")
        self.menu_button.get_accessible().set_name("main menu button")
        self.toplevel_widget.get_accessible().set_name("contents")
        self.mainhpaned.get_accessible().set_name("upper half")
        self.secondhpaned.get_accessible().set_name("tabs")
        self.main_tabs.get_accessible().set_name("primary tabs")
        self.context_tabs.get_accessible().set_name("secondary tabs")
        self.viewer.get_accessible().set_name("viewer")
        self.timeline_ui.get_accessible().set_name("timeline area")

        # Restore settings for position and visibility.
        if self.settings.mainWindowHPanePosition is None:
            self._setDefaultPositions()
        self.secondhpaned.set_position(self.settings.mainWindowHPanePosition)
        self.mainhpaned.set_position(self.settings.mainWindowMainHPanePosition)
        self.toplevel_widget.set_position(self.settings.mainWindowVPanePosition)

        # Connect the main window's signals at the end, to avoid messing around
        # with the restoration of settings above.
        self.app.gui.connect("delete-event", self._deleteCb)

        # Focus the timeline by default!
        self.focusTimeline()
        self.updateTitle()

    def _setDefaultPositions(self):
        window_width = self.app.gui.get_size()[0]
        if self.settings.mainWindowHPanePosition is None:
            self.settings.mainWindowHPanePosition = window_width / 3
        if self.settings.mainWindowMainHPanePosition is None:
            self.settings.mainWindowMainHPanePosition = 2 * window_width / 3
        if self.settings.mainWindowVPanePosition is None:
            screen_width = float(self.app.gui.get_screen().get_width())
            screen_height = float(self.app.gui.get_screen().get_height())
            req = self.toplevel_widget.get_preferred_size()[0]
            if screen_width / screen_height < 0.75:
                # Tall screen, give some more vertical space the the tabs.
                value = req.height / 3
            else:
                value = req.height / 2
            self.settings.mainWindowVPanePosition = value

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

    def __create_headerbar(self):
        headerbar = Gtk.HeaderBar()
        headerbar.set_show_close_button(True)

        back_button = Gtk.Button.new_from_icon_name(
            "go-previous-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        back_button.set_always_show_image(True)
        back_button.set_tooltip_text(_("Close project"))
        back_button.connect("clicked", self.__close_project_cb)
        back_button.set_margin_right(4 * PADDING)
        headerbar.pack_start(back_button)

        undo_button = Gtk.Button.new_from_icon_name(
            "edit-undo-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        undo_button.set_always_show_image(True)
        undo_button.set_label(_("Undo"))
        undo_button.set_action_name("app.undo")
        undo_button.set_use_underline(True)

        redo_button = Gtk.Button.new_from_icon_name(
            "edit-redo-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        redo_button.set_always_show_image(True)
        redo_button.set_action_name("app.redo")
        redo_button.set_use_underline(True)

        self.save_button = Gtk.Button.new_with_label(_("Save"))
        self.save_button.set_focus_on_click(False)

        self.render_button = Gtk.Button.new_from_icon_name(
            "system-run-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        self.render_button.set_always_show_image(True)
        self.render_button.set_label(_("Render"))
        self.render_button.set_tooltip_text(
            _("Export your project as a finished movie"))
        self.render_button.set_sensitive(False)  # The only one we have to set.
        self.render_button.connect("clicked", self._renderCb)

        undo_redo_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        undo_redo_box.get_style_context().add_class("linked")
        undo_redo_box.pack_start(undo_button, expand=False, fill=False, padding=0)
        undo_redo_box.pack_start(redo_button, expand=False, fill=False, padding=0)
        headerbar.pack_start(undo_redo_box)

        self.builder.add_from_file(
            os.path.join(get_ui_dir(), "mainmenubutton.ui"))

        # FIXME : see https://bugzilla.gnome.org/show_bug.cgi?id=729263
        self.builder.connect_signals_full(self._builderConnectCb, self)

        self.menu_button = self.builder.get_object("menubutton")

        self._menubutton_items = {}
        for widget in self.builder.get_object("menu").get_children():
            self._menubutton_items[Gtk.Buildable.get_name(widget)] = widget

        headerbar.pack_end(self.menu_button)
        headerbar.pack_end(self.save_button)
        headerbar.pack_end(self.render_button)
        headerbar.show_all()

        return headerbar

    def __set_keyboard_shortcuts(self):
        group = Gio.SimpleActionGroup()
        self.toplevel_widget.insert_action_group("editor", group)
        self.headerbar.insert_action_group("editor", group)

        self.save_action = Gio.SimpleAction.new("save", None)
        self.save_action.connect("activate", self._saveProjectCb)
        group.add_action(self.save_action)
        self.app.shortcuts.add("editor.save", ["<Primary>s"],
                               _("Save the current project"), group="win")
        self.save_button.set_action_name("editor.save")

        self.save_as_action = Gio.SimpleAction.new("save-as", None)
        self.save_as_action.connect("activate", self._saveProjectAsCb)
        group.add_action(self.save_as_action)
        self.app.shortcuts.add("editor.save-as", ["<Primary><Shift>s"],
                               _("Save the current project as"), group="win")

        self.import_asset_action = Gio.SimpleAction.new("import-asset", None)
        self.import_asset_action.connect("activate", self.__import_asset_cb)
        group.add_action(self.import_asset_action)
        self.app.shortcuts.add("editor.import-asset", ["<Primary>i"],
                               _("Add media files to your project"), group="win")

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
        self.settings.mainWindowVPanePosition = self.toplevel_widget.get_position()

    def _mediaLibraryPlayCb(self, unused_medialibrary, asset):
        """Previews the specified asset.

        If the media library item to preview is an image, show it in the user's
        favorite image viewer. Else, preview the video/sound in Pitivi.
        """
        # Technically, our preview widget can show images, but it's never going
        # to do a better job (sizing, zooming, metadata, editing, etc.)
        # than the user's favorite image viewer.
        if asset.is_image():
            Gio.AppInfo.launch_default_for_uri(asset.get_id(), None)
        else:
            preview_window = PreviewAssetWindow(asset, self.app)
            preview_window.preview()

    def _projectChangedCb(self, unused_project):
        self.save_action.set_enabled(True)
        self.updateTitle()

    def _builderConnectCb(self, builder, gobject, signal_name, handler_name,
                          connect_object, flags, user_data):
        id_ = gobject.connect(signal_name, getattr(self, handler_name))
        self.builder_handler_ids.append((gobject, id_))

# Toolbar/Menu actions callback

    def __close_project_cb(self, unused_button):
        """Closes the current project."""
        self.app.project_manager.closeRunningProject()

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
        dialog = ProjectSettingsDialog(self.app.gui, project, self.app)
        dialog.window.run()
        self.updateTitle()

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

    def _projectManagerSaveProjectFailedCb(self, unused_project_manager, uri, exception=None):
        project_filename = unquote(uri.split("/")[-1])
        dialog = Gtk.MessageDialog(transient_for=self.app.gui,
                                   modal=True,
                                   message_type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.OK,
                                   text=_('Unable to save project "%s"') % project_filename)
        if exception:
            dialog.set_property("secondary-use-markup", True)
            dialog.set_property("secondary-text", unquote(str(exception)))
        dialog.set_transient_for(self.app.gui)
        dialog.run()
        dialog.destroy()
        self.error("failed to save project")

    def _projectManagerProjectSavedCb(self, unused_project_manager, project, uri):
        # FIXME GES: Reimplement Undo/Redo
        # self.app.action_log.checkpoint()
        self.updateTitle()

        self.save_action.set_enabled(False)
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

        dialog = Gtk.Dialog(title="", transient_for=self.app.gui, modal=True)
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
            message = _("If you don't save, "
                        "the changes from the last %s will be lost.") % \
                beautify_time_delta(time_delta)
        else:
            message = _("If you don't save, your changes will be lost.")
        secondary.props.label = message

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
            dialog = Gtk.MessageDialog(transient_for=self.app.gui,
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
            dialog.set_transient_for(self.app.gui)
            response = dialog.run()
            dialog.destroy()
            if response != Gtk.ResponseType.YES:
                return False
        return True

    def _projectManagerMissingUriCb(self, project_manager, project, unused_error, asset):
        if project.at_least_one_asset_missing:
            # One asset is already missing so no point in spamming the user
            # with more file-missing dialogs, as we need all of them.
            return None

        if self.app.proxy_manager.is_proxy_asset(asset):
            uri = self.app.proxy_manager.getTargetUri(asset)
        else:
            uri = asset.get_id()
        dialog = Gtk.Dialog(title=_("Locate missing file..."),
                            transient_for=self.app.gui,
                            modal=True)

        dialog.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL,
                           _("Open"), Gtk.ResponseType.OK)
        dialog.set_border_width(SPACING * 2)
        dialog.get_content_area().set_spacing(SPACING)
        dialog.set_transient_for(self.app.gui)
        dialog.set_default_response(Gtk.ResponseType.OK)

        # This box will contain widgets with details about the missing file.
        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.VERTICAL)

        label_start = Gtk.Label()
        label_start.set_markup(_("The following file could not be found:"))
        label_start.set_xalign(0)
        vbox.pack_start(label_start, False, False, 0)

        hbox = Gtk.Box()
        hbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        hbox.set_margin_top(PADDING)
        hbox.set_spacing(PADDING * 2)

        label_asset_info = Gtk.Label()
        label_asset_info.set_markup(beautify_missing_asset(asset))
        label_asset_info.set_xalign(0)
        label_asset_info.set_yalign(0)
        hbox.pack_start(label_asset_info, False, False, 0)

        small_thumb, large_thumb = AssetThumbnail.get_thumbnails_from_xdg_cache(uri)
        if large_thumb:
            self.debug("A thumbnail file was found for %s", uri)
            thumbnail = Gtk.Image.new_from_pixbuf(large_thumb)
            hbox.pack_end(thumbnail, False, False, 0)

        vbox.pack_start(hbox, False, False, 0)

        label_end = Gtk.Label()
        label_end.set_markup(_("Please specify its new location:"))
        label_end.set_xalign(0)
        label_end.set_margin_top(PADDING)
        vbox.pack_start(label_end, False, False, 0)

        dialog.get_content_area().pack_start(vbox, False, False, 0)
        vbox.show_all()

        chooser = Gtk.FileChooserWidget(action=Gtk.FileChooserAction.OPEN)
        chooser.set_select_multiple(False)
        previewer = PreviewWidget(self.settings, discover_sync=True)
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
        filter_.set_name(_("%s files") % extension)
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
                           'Pitivi does not currently support partial projects.') % \
                    info_name(asset)
                project_manager.emit("new-project-failed", project.uri, reason)

        dialog.destroy()
        return new_uri

    def _connectToProject(self, project):
        # FIXME GES we should re-enable this when possible
        # medialibrary.connect("missing-plugins", self._sourceListMissingPluginsCb)
        project.connect("project-changed", self._projectChangedCb)
        project.connect("rendering-settings-changed",
                        self._rendering_settings_changed_cb)
        project.ges_timeline.connect("notify::duration",
                                     self._timelineDurationChangedCb)

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

    def _setProject(self, project):
        """Disconnects and then reconnects callbacks to the specified project.

        Args:
            project (Project): The new current project.
        """
        if not project:
            self.warning("Current project instance does not exist")
            return False

        self.viewer.setPipeline(project.pipeline)
        self._reset_viewer_aspect_ratio(project)
        self.clipconfig.project = project

        # When creating a blank project there's no project URI yet.
        if project.uri:
            folder_path = os.path.dirname(path_from_uri(project.uri))
            self.settings.lastProjectFolder = folder_path

    def _disconnectFromProject(self, project):
        project.disconnect_by_func(self._projectChangedCb)
        project.disconnect_by_func(self._rendering_settings_changed_cb)
        project.ges_timeline.disconnect_by_func(self._timelineDurationChangedCb)

    def _rendering_settings_changed_cb(self, project, unused_item):
        """Handles Project metadata changes."""
        self._reset_viewer_aspect_ratio(project)

    def _reset_viewer_aspect_ratio(self, project):
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

    def _showExportDialog(self, project):
        self.log("Export requested")
        chooser = Gtk.FileChooserDialog(title=_("Export To..."),
                                        transient_for=self.app.gui,
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
                                        transient_for=self.app.gui,
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
            transient_for=self.app.gui, action=Gtk.FileChooserAction.SAVE)
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
        self.headerbar.set_custom_title(event_box)
        self.app.gui.set_title(title)

    def __titleClickCb(self, unused_widget, unused_event, project):
        entry = Gtk.Entry()
        entry.set_width_chars(100)
        entry.set_margin_left(SPACING)
        entry.set_margin_right(SPACING)
        entry.show()
        entry.set_text(project.name)
        self.headerbar.set_custom_title(entry)
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
        app (Pitivi): The app.
    """

    def __init__(self, asset, app):
        Gtk.Window.__init__(self)
        self._asset = asset
        self.app = app

        self.set_title(_("Preview"))
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_transient_for(app.gui)

        self._previewer = PreviewWidget(app.settings, minimal=True)
        self.add(self._previewer)
        self._previewer.preview_uri(self._asset.get_id())
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
        img_width = video.get_square_width()
        img_height = video.get_height()
        mainwindow_width, mainwindow_height = self.app.gui.get_size()
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
