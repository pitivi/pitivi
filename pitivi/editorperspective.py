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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
import os
from gettext import gettext as _
from time import time
from urllib.parse import unquote

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gio
from gi.repository import Gtk

from pitivi.clipproperties import ClipProperties
from pitivi.configure import APPNAME
from pitivi.configure import get_ui_dir
from pitivi.dialogs.missingasset import MissingAssetDialog
from pitivi.dialogs.projectsettings import ProjectSettingsDialog
from pitivi.editorstate import EditorState
from pitivi.effects import EffectListWidget
from pitivi.interactiveintro import InteractiveIntro
from pitivi.mediafilespreviewer import PreviewWidget
from pitivi.medialibrary import MediaLibraryWidget
from pitivi.perspective import Perspective
from pitivi.settings import GlobalSettings
from pitivi.tabsmanager import BaseTabs
from pitivi.timeline.previewers import ThumbnailCache
from pitivi.timeline.timeline import TimelineContainer
from pitivi.transitions import TransitionsListWidget
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import path_from_uri
from pitivi.utils.ui import beautify_time_delta
from pitivi.utils.ui import EDITOR_PERSPECTIVE_CSS
from pitivi.utils.ui import info_name
from pitivi.viewer.viewer import ViewerContainer


GlobalSettings.add_config_section("main-window")
GlobalSettings.add_config_option('mainWindowHPanePosition',
                                 section="main-window",
                                 key="hpane-position",
                                 type_=int)
GlobalSettings.add_config_option('mainWindowMainHPanePosition',
                                 section="main-window",
                                 key="main-hpane-position",
                                 type_=int)
GlobalSettings.add_config_option('mainWindowVPanePosition',
                                 section="main-window",
                                 key="vpane-position",
                                 type_=int)
GlobalSettings.add_config_option('lastProjectFolder',
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

        self.builder = Gtk.Builder()
        self.editor_state = EditorState(app.project_manager)

        pm = self.app.project_manager
        pm.connect("new-project-loaded",
                   self._project_manager_new_project_loaded_cb)
        pm.connect("save-project-failed",
                   self._project_manager_save_project_failed_cb)
        pm.connect("project-saved", self._project_manager_project_saved_cb)
        pm.connect("closing-project", self._project_manager_closing_project_cb)
        pm.connect("reverting-to-saved",
                   self._project_manager_reverting_to_saved_cb)
        pm.connect("project-closed", self._project_manager_project_closed_cb)
        pm.connect("missing-uri", self._project_manager_missing_uri_cb)

    def setup_ui(self):
        """Sets up the UI."""
        self.__setup_css()
        self._create_ui()
        self.app.gui.connect("focus-in-event", self.__focus_in_event_cb)
        self.app.gui.connect("destroy", self._destroyed_cb)

    def activate_compact_mode(self):
        """Shrinks widgets to suit better a small screen."""
        self.medialibrary.activate_compact_mode()
        self.viewer.activate_compact_mode()

    def refresh(self):
        """Refreshes the perspective."""
        self.timeline_ui.restore_state()
        self.focus_timeline()

    def __setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(EDITOR_PERSPECTIVE_CSS.encode("UTF-8"))
        screen = Gdk.Screen.get_default()
        style_context = self.app.gui.get_style_context()
        style_context.add_provider_for_screen(screen, css_provider,
                                              Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def __focus_in_event_cb(self, unused_widget, unused_event):
        ges_timeline = self.timeline_ui.timeline.ges_timeline
        if not ges_timeline:
            # Nothing to work with, Pitivi is starting up.
            return

        if self.app.project_manager.current_project.pipeline.rendering():
            return

        # Commit the timeline so its nested timelines assets are refreshed.
        ges_timeline.commit()

        # We need to track the changed assets ourselves.
        changed_files_uris = ThumbnailCache.update_caches()
        if changed_files_uris:
            self.medialibrary.update_asset_thumbs(changed_files_uris)

            for ges_layer in ges_timeline.get_layers():
                for ges_clip in ges_layer.get_clips():
                    if ges_clip.get_asset().props.id in changed_files_uris:
                        if ges_clip.ui.audio_widget:
                            ges_clip.ui.audio_widget.update_previewer()
                        if ges_clip.ui.video_widget:
                            ges_clip.ui.video_widget.update_previewer()

    def _destroyed_cb(self, unused_main_window):
        """Cleanup before destroying this window."""
        pm = self.app.project_manager
        pm.disconnect_by_func(self._project_manager_new_project_loaded_cb)
        pm.disconnect_by_func(self._project_manager_save_project_failed_cb)
        pm.disconnect_by_func(self._project_manager_project_saved_cb)
        pm.disconnect_by_func(self._project_manager_closing_project_cb)
        pm.disconnect_by_func(self._project_manager_reverting_to_saved_cb)
        pm.disconnect_by_func(self._project_manager_project_closed_cb)
        pm.disconnect_by_func(self._project_manager_missing_uri_cb)
        self.toplevel_widget.remove(self.timeline_ui)
        self.timeline_ui.destroy()

    def _render_cb(self, unused_button):
        """Shows the RenderDialog for the current project."""
        from pitivi.render import RenderDialog

        project = self.app.project_manager.current_project
        dialog = RenderDialog(self.app, project)
        dialog.window.show()

    def _create_ui(self):
        """Creates the graphical interface.

        The rough hierarchy is:
        vpaned:
        - mainhpaned(secondhpaned(main_tabs, context_tabs), viewer)
        - timeline_ui

        The full hierarchy can be admired by starting the GTK+ Inspector
        with Ctrl+Shift+I.
        """
        # pylint: disable=attribute-defined-outside-init
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
        self.medialibrary.connect('play', self._media_library_play_cb)
        self.medialibrary.show()
        self.effectlist.show()

        # Second set of tabs
        self.context_tabs = BaseTabs(self.app)
        self.clipconfig = ClipProperties(self.app)
        self.trans_list = TransitionsListWidget(self.app)
        self.context_tabs.append_page("Clip",
                                      self.clipconfig, Gtk.Label(label=_("Clip")))
        self.context_tabs.append_page("Transition",
                                      self.trans_list, Gtk.Label(label=_("Transition")))
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
        self.timelinepaned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)

        self.timeline_ui = TimelineContainer(self.app, self.editor_state)
        self.mini_timeline_ui = self.timeline_ui.timeline.mini_layout_container

        self.timelinepaned.pack1(self.mini_timeline_ui, resize=False, shrink=False)
        self.timelinepaned.pack2(self.timeline_ui, resize=False, shrink=False)
        self.timelinepaned.show_all()

        self.toplevel_widget.pack2(self.timelinepaned, resize=True, shrink=False)

        self.intro = InteractiveIntro(self.app)
        self.headerbar.pack_end(self.intro.intro_button)

        # Setup shortcuts for HeaderBar buttons and menu items.
        self._create_actions()

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
            self._set_default_positions()
        self.secondhpaned.set_position(self.settings.mainWindowHPanePosition)
        self.mainhpaned.set_position(self.settings.mainWindowMainHPanePosition)
        self.toplevel_widget.set_position(self.settings.mainWindowVPanePosition)

    def _set_default_positions(self):
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

    def switch_context_tab(self, ges_clip):
        """Activates the appropriate tab on the second set of tabs.

        Args:
            ges_clip (GES.SourceClip): The clip which has been focused.
        """
        if isinstance(ges_clip, GES.TitleClip):
            page = 0
        elif isinstance(ges_clip, GES.SourceClip):
            page = 0
        elif isinstance(ges_clip, GES.TransitionClip):
            page = 1
        elif isinstance(ges_clip, GES.TestClip):
            page = 0
        else:
            self.warning("Unknown clip type: %s", ges_clip)
            return
        self.context_tabs.set_current_page(page)

    def focus_timeline(self):
        layers_representation = self.timeline_ui.timeline.layout
        # Check whether it has focus already, grab_focus always emits an event.
        if not layers_representation.props.is_focus:
            layers_representation.grab_focus()

    def __create_headerbar(self):
        headerbar = Gtk.HeaderBar()
        headerbar.set_show_close_button(True)

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

        # pylint: disable=attribute-defined-outside-init
        self.save_button = Gtk.Button.new_with_label(_("Save"))
        self.save_button.set_focus_on_click(False)

        self.render_button = Gtk.Button.new_from_icon_name(
            "system-run-symbolic", Gtk.IconSize.SMALL_TOOLBAR)
        self.render_button.set_always_show_image(True)
        self.render_button.set_label(_("Render"))
        self.render_button.set_tooltip_text(
            _("Export your project as a finished movie"))
        self.render_button.set_sensitive(False)  # The only one we have to set.
        self.render_button.connect("clicked", self._render_cb)

        undo_redo_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        undo_redo_box.get_style_context().add_class("linked")
        undo_redo_box.pack_start(undo_button, expand=False, fill=False, padding=0)
        undo_redo_box.pack_start(redo_button, expand=False, fill=False, padding=0)
        headerbar.pack_start(undo_redo_box)

        self.builder.add_from_file(
            os.path.join(get_ui_dir(), "mainmenubutton.ui"))

        self.menu_button = self.builder.get_object("menubutton")
        self.keyboard_shortcuts_button = self.builder.get_object("menu_shortcuts")

        headerbar.pack_end(self.menu_button)
        headerbar.pack_end(self.save_button)
        headerbar.pack_end(self.render_button)
        headerbar.show_all()

        return headerbar

    def _create_actions(self):
        group = Gio.SimpleActionGroup()
        self.toplevel_widget.insert_action_group("editor", group)
        self.headerbar.insert_action_group("editor", group)

        # pylint: disable=attribute-defined-outside-init
        self.save_action = Gio.SimpleAction.new("save", None)
        self.save_action.connect("activate", self.__save_project_cb)
        group.add_action(self.save_action)
        self.app.shortcuts.add("editor.save", ["<Primary>s"], self.save_action,
                               _("Save the current project"), group="win")
        self.save_button.set_action_name("editor.save")

        self.save_as_action = Gio.SimpleAction.new("save-as", None)
        self.save_as_action.connect("activate", self.__save_project_as_cb)
        group.add_action(self.save_as_action)
        self.app.shortcuts.add("editor.save-as", ["<Primary><Shift>s"],
                               self.save_as_action,
                               _("Save the current project as"), group="win")

        self.revert_to_saved_action = Gio.SimpleAction.new("revert-to-saved", None)
        self.revert_to_saved_action.connect("activate", self.__revert_to_saved_cb)
        group.add_action(self.revert_to_saved_action)

        self.export_project_action = Gio.SimpleAction.new("export-project", None)
        self.export_project_action.connect("activate", self.__export_project_cb)
        group.add_action(self.export_project_action)

        self.save_frame_action = Gio.SimpleAction.new("save-frame", None)
        self.save_frame_action.connect("activate", self.__save_frame_cb)
        group.add_action(self.save_frame_action)

        self.project_settings_action = Gio.SimpleAction.new("project-settings", None)
        self.project_settings_action.connect("activate", self.__project_settings_cb)
        group.add_action(self.project_settings_action)

        group.add_action(self.intro.intro_action)
        self.app.shortcuts.add("editor.interactive-intro", [], self.intro.intro_action,
                               _("Quick intros to Pitivi"), group="win")

        self.import_asset_action = Gio.SimpleAction.new("import-asset", None)
        self.import_asset_action.connect("activate", self.__import_asset_cb)
        group.add_action(self.import_asset_action)
        self.app.shortcuts.add("editor.import-asset", ["<Primary>i"],
                               self.import_asset_action,
                               _("Add media files to your project"), group="win")

    def __import_asset_cb(self, unused_action, unused_param):
        self.medialibrary.show_import_assets_dialog()

    def show_project_status(self):
        project = self.app.project_manager.current_project
        dirty = project.has_unsaved_modifications()
        self.save_action.set_enabled(dirty)
        self.revert_to_saved_action.set_enabled(bool(project.uri) and dirty)
        self.update_title()

# UI Callbacks

    def _media_library_play_cb(self, unused_medialibrary, asset):
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

    def _project_changed_cb(self, unused_project):
        self.save_action.set_enabled(True)
        self.update_title()

# Toolbar/Menu actions callback

    def __save_project_cb(self, unused_action, unused_param):
        self.save_project()

    def __save_project_as_cb(self, unused_action, unused_param):
        self.save_project_as()

    def save_project(self):
        if not self.app.project_manager.current_project.uri or self.app.project_manager.disable_save:
            self.save_project_as()
        else:
            self.app.project_manager.save_project()

    def __revert_to_saved_cb(self, unused_action, unused_param):
        self.app.project_manager.revert_to_saved_project()

    def __export_project_cb(self, unused_action, unused_param):
        uri = self._show_export_dialog(self.app.project_manager.current_project)
        result = None
        if uri:
            result = self.app.project_manager.export_project(
                self.app.project_manager.current_project, uri)

        if not result:
            self.log("Project couldn't be exported")
        return result

    def __project_settings_cb(self, unused_action, unused_param):
        self.show_project_settings_dialog()

    def show_project_settings_dialog(self):
        project = self.app.project_manager.current_project
        dialog = ProjectSettingsDialog(self.app.gui, project, self.app)
        dialog.window.run()
        self.update_title()

# Project management callbacks

    def _project_manager_new_project_loaded_cb(self, project_manager, project):
        """Connects the UI to the specified project.

        Args:
            project_manager (ProjectManager): The project manager.
            project (Project): The project which has been loaded.
        """
        self.log("A new project has been loaded")

        self._connect_to_project(project)
        project.pipeline.activate_position_listener()

        self.viewer.set_project(project)
        self.clipconfig.set_project(project, self.timeline_ui)
        self.timeline_ui.set_project(project)

        # When creating a blank project there's no project URI yet.
        if project.uri:
            folder_path = os.path.dirname(path_from_uri(project.uri))
            self.settings.lastProjectFolder = folder_path

        self.update_title()

        if project_manager.disable_save is True:
            # Special case: we enforce "Save as", but the normal "Save" button
            # redirects to it if needed, so we still want it to be enabled:
            self.save_action.set_enabled(True)

        if project.ges_timeline.props.duration != 0:
            self.render_button.set_sensitive(True)

    def _project_manager_save_project_failed_cb(self, unused_project_manager, uri, exception=None):
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

    def _project_manager_project_saved_cb(self, unused_project_manager, unused_project, unused_uri):
        self.update_title()
        self.save_action.set_enabled(False)

    def _project_manager_closing_project_cb(self, project_manager, project):
        """Investigates whether it's possible to close the specified project.

        Args:
            project_manager (ProjectManager): The project manager.
            project (Project): The project which has been closed.

        Returns:
            bool: True when it's OK to close it, False when the user chooses
                to cancel the closing operation.
        """
        if not project.has_unsaved_modifications():
            return True

        if project.uri and not project_manager.disable_save:
            save = _("Save")
        else:
            save = _("Save as...")

        dialog = Gtk.MessageDialog(transient_for=self.app.gui, modal=True)
        reject_btn = dialog.add_button(_("Close without saving"),
                                       Gtk.ResponseType.REJECT)

        dialog.add_buttons(_("Cancel"), Gtk.ResponseType.CANCEL,
                           save, Gtk.ResponseType.YES)

        dialog.set_default_response(Gtk.ResponseType.CANCEL)
        dialog.get_accessible().set_name("unsaved changes dialog")
        reject_btn.get_style_context().add_class("destructive-action")

        primary = _("Save changes to the current project before closing?")
        dialog.props.use_markup = True
        dialog.props.text = "<span weight=\"bold\">" + primary + "</span>"

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

        dialog.props.secondary_text = message

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            if project.uri is not None and project_manager.disable_save is False:
                res = self.app.project_manager.save_project()
            else:
                res = self.save_project_as()
        elif response == Gtk.ResponseType.REJECT:
            res = True
        else:
            res = False

        return res

    def _project_manager_project_closed_cb(self, project_manager, project):
        """Starts disconnecting the UI from the specified project.

        This happens when the user closes the app or asks to load another
        project, immediately after the user confirmed that unsaved changes,
        if any, can be discarded but before the filechooser to pick the next
        project to load appears.
        """
        # We must disconnect from the project pipeline before it is released:
        if project.pipeline is not None:
            project.pipeline.deactivate_position_listener()

        self.info("Project closed")
        if project.loaded:
            self._disconnect_from_project(project)

        self.timeline_ui.set_project(None)
        self.clipconfig.set_project(None, None)

        self.render_button.set_sensitive(False)
        return False

    def _project_manager_reverting_to_saved_cb(self, unused_project_manager, unused_project):
        if self.app.project_manager.current_project.has_unsaved_modifications():
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

    def _project_manager_missing_uri_cb(self, project_manager, project, unused_error, asset):
        if project.at_least_one_asset_missing:
            # One asset is already missing so no point in spamming the user
            # with more file-missing dialogs, as we need all of them.
            return None

        if self.app.proxy_manager.is_proxy_asset(asset):
            uri = self.app.proxy_manager.get_target_uri(asset)
        else:
            uri = asset.get_id()

        dialog = MissingAssetDialog(self.app, asset, uri)
        new_uri = dialog.get_new_uri()

        if not new_uri:
            dialog.hide()
            if not self.app.proxy_manager.check_proxy_loading_succeeded(asset):
                # Reset the project manager and disconnect all the signals.
                project_manager.close_running_project()
                # Signal the project loading failure.
                # You have to do this *after* successfully creating a blank project,
                # or the startupwizard will still be connected to that signal too.
                reason = _("No replacement file was provided for \"<i>%s</i>\".\n\n"
                           "Pitivi does not currently support partial projects.") % \
                    info_name(asset)
                project_manager.emit("new-project-failed", project.uri, reason)

        dialog.destroy()
        return new_uri

    def _connect_to_project(self, project):
        project.connect("project-changed", self._project_changed_cb)
        project.ges_timeline.connect("notify::duration",
                                     self._timeline_duration_changed_cb)

    def _disconnect_from_project(self, project):
        project.disconnect_by_func(self._project_changed_cb)
        project.ges_timeline.disconnect_by_func(self._timeline_duration_changed_cb)

    def _timeline_duration_changed_cb(self, timeline, unused_duration):
        """Updates the render button.

        This covers the case when a clip is inserted into a blank timeline.
        This callback is not triggered by loading a project.
        """
        duration = timeline.get_duration()
        self.debug("Timeline duration changed to %s", duration)
        self.render_button.set_sensitive(duration > 0)

    def _show_export_dialog(self, project):
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

    def save_project_as(self):
        uri = self._show_save_as_dialog()
        if uri is None:
            return False
        return self.app.project_manager.save_project(uri)

    def _show_save_as_dialog(self):
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

    def __save_frame_cb(self, unused_action, unused_param):
        """Exports a snapshot of the current frame as an image file."""
        res = self._show_save_screenshot_dialog()
        if res:
            path, mime = res[0], res[1]
            self.app.project_manager.current_project.pipeline.save_thumbnail(
                -1, -1, mime, path)

    def _show_save_screenshot_dialog(self):
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
        for image_format in formats:
            filt = Gtk.FileFilter()
            filt.set_name(image_format)
            filt.add_mime_type(formats.get(image_format)[0])
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

    def update_title(self):
        project = self.app.project_manager.current_project
        unsaved_mark = ""
        if project.has_unsaved_modifications():
            unsaved_mark = "*"
        title = "%s%s — %s" % (unsaved_mark, project.name, APPNAME)
        self.headerbar.set_title(title)


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

        self.connect("key-press-event", self._key_press_event_cb)

    def preview(self):
        """Shows the window and starts the playback."""
        width, height = self._calculate_preview_window_size()
        self.resize(width, height)
        # Setting the position of the window only works if it's currently hidden
        # otherwise, after the resize the position will not be readjusted
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.show()

        self._previewer.play()
        # Hack so that we really really force the "utility" window to be
        # focused
        self.present()

    def _calculate_preview_window_size(self):
        info = self._asset.get_info()
        video_streams = info.get_video_streams()
        if not video_streams:
            # There is no video/image stream. This is an audio file.
            # Resize to the minimum and let the window manager deal with it.
            return 1, 1
        # For videos and images, automatically resize the window
        # Try to keep it 1:1 if it can fit within 85% of the parent window
        video = video_streams[0]
        img_width = video.get_natural_width()
        img_height = video.get_natural_height()
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

    def _key_press_event_cb(self, unused_widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
        return True
