# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2010 Mathieu Duponchelle <seeed@laposte.net>
# Copyright (c) 2018 Harish Fulara <harishfulara1996@gmail.com>
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
"""Pitivi's Welcome/Greeter perspective."""
import os
from gettext import gettext as _

from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import Gtk

from pitivi.check import MISSING_SOFT_DEPS
from pitivi.configure import get_ui_dir
from pitivi.dialogs.browseprojects import BrowseProjectsDialog
from pitivi.perspective import Perspective
from pitivi.project import Project
from pitivi.utils.ui import beautify_last_updated_timestamp
from pitivi.utils.ui import beautify_project_path
from pitivi.utils.ui import BinWithNaturalWidth
from pitivi.utils.ui import fix_infobar
from pitivi.utils.ui import GREETER_PERSPECTIVE_CSS
from pitivi.utils.ui import PADDING
from pitivi.utils.ui import SPACING
from pitivi.utils.ui import URI_TARGET_ENTRY

MAX_RECENT_PROJECTS = 10


class ProjectInfoRow(Gtk.ListBoxRow):
    """Displays a project's info.

    Attributes:
        recent_project_item (Gtk.RecentInfo): Recent project's meta-data.
    """

    def __init__(self, recent_project_item):
        Gtk.ListBoxRow.__init__(self)
        self.uri = recent_project_item.get_uri()
        self.name = os.path.splitext(recent_project_item.get_display_name())[0]

        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "project_info.ui"))
        self.add(builder.get_object("project_info_tophbox"))

        self.select_button = builder.get_object("project_select_button")
        # Hide the select button as we only want to
        # show it during projects removal screen.
        self.select_button.hide()

        self.__thumb = builder.get_object("project_thumbnail")
        # Defer loading of thumbnail.
        GLib.idle_add(self.__load_thumb_cb)

        builder.get_object("project_name_label").set_text(self.name)
        builder.get_object("project_uri_label").set_text(
            beautify_project_path(recent_project_item.get_uri_display()))
        builder.get_object("project_last_updated_label").set_text(
            beautify_last_updated_timestamp(recent_project_item.get_modified()))

    def __load_thumb_cb(self):
        self.__thumb.set_from_pixbuf(Project.get_thumb(self.uri))
        return False


class GreeterPerspective(Perspective):
    """Pitivi's Welcome/Greeter perspective.

    Allows the user to create a new project or open an existing one.

    Attributes:
        app (Pitivi): The app.
    """

    def __init__(self, app):
        Perspective.__init__(self)

        self.app = app
        self.new_project_action = None
        self.open_project_action = None

        self.__topvbox = None
        self.__welcome_vbox = None
        self.__recent_projects_vbox = None
        self.__search_entry = None
        self.__recent_projects_labelbox = None
        self.__recent_projects_listbox = None
        self.__project_filter = self.__create_project_filter()
        self.__infobar = None
        self.__selection_button = None
        self.__actionbar = None
        self.__remove_projects_button = None
        self.__cancel_button = None
        self.__new_project_button = None
        self.__open_project_button = None
        self.__warnings_button = None

        # Projects selected for removal.
        self.__selected_projects = []

        if app.get_latest():
            self.__show_newer_available_version()
        else:
            app.connect("version-info-received", self.__app_version_info_received_cb)

    def setup_ui(self):
        """Sets up the UI."""
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "greeter.ui"))

        logo = builder.get_object("logo")
        icon_theme = Gtk.IconTheme.get_default()
        pixbuf = icon_theme.load_icon("org.pitivi.Pitivi", 256, Gtk.IconLookupFlags.FORCE_SIZE)
        logo.set_from_pixbuf(pixbuf)

        self.toplevel_widget = builder.get_object("toplevel_vbox")
        self.toplevel_widget.drag_dest_set(
            Gtk.DestDefaults.ALL, [URI_TARGET_ENTRY], Gdk.DragAction.COPY)
        self.toplevel_widget.connect("drag-data-received", self.__drag_data_received_cb)

        self.__topvbox = builder.get_object("topvbox")
        self.__welcome_vbox = builder.get_object("welcome_vbox")
        self.__recent_projects_vbox = builder.get_object("recent_projects_vbox")

        self.__recent_projects_labelbox = builder.get_object("recent_projects_labelbox")

        self.__search_entry = builder.get_object("search_entry")
        self.__search_entry.connect("search-changed", self.__search_changed_cb)

        self.__recent_projects_listbox = builder.get_object("recent_projects_listbox")
        self.__recent_projects_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.__recent_projects_listbox.connect(
            "row-activated", self.__projects_row_activated_cb)
        self.__recent_projects_listbox.connect(
            "button-press-event", self.__projects_button_press_cb)

        self.__infobar = builder.get_object("infobar")
        fix_infobar(self.__infobar)
        self.__infobar.hide()
        self.__infobar.connect("response", self.__infobar_response_cb)

        self.__actionbar = builder.get_object("actionbar")
        self.__remove_projects_button = builder.get_object("remove_projects_button")
        self.__remove_projects_button.get_style_context().add_class("destructive-action")
        self.__remove_projects_button.connect("clicked", self.__remove_projects_clicked_cb)

        self.__setup_css()
        self.headerbar = self.__create_headerbar()
        self._create_actions()

    def refresh(self):
        """Refreshes the perspective."""
        # Hide actionbar because we only want to show it during projects removal screen.
        self.__actionbar.hide()
        self.__remove_projects_button.set_sensitive(False)
        self.__selected_projects = []

        # Clear the currently displayed list of recent projects.
        for child in self.__recent_projects_listbox.get_children():
            self.__recent_projects_listbox.remove(child)

        recent_items = [item for item in self.app.recent_manager.get_items()
                        if item.get_display_name().endswith(self.__project_filter) and item.exists()]

        # If there are recent projects, display them, else display welcome screen.
        if recent_items:
            for item in recent_items[:MAX_RECENT_PROJECTS]:
                recent_project_info = ProjectInfoRow(item)
                recent_project_info.select_button.connect(
                    "toggled", self.__project_selected_cb, recent_project_info)
                self.__recent_projects_listbox.add(recent_project_info)
                recent_project_info.show()

            child = self.__recent_projects_vbox
            self.__update_headerbar(projects=True)
            self.__recent_projects_listbox.show()
        else:
            child = self.__welcome_vbox
            self.__update_headerbar(welcome=True)

        children = self.__topvbox.get_children()
        if children:
            current_child = children[0]
            if current_child == child:
                child = None
            else:
                self.__topvbox.remove(current_child)

        if child:
            self.__topvbox.pack_start(child, False, False, 0)

        if recent_items:
            self.__search_entry.show()
            # We are assuming that the users name their projects meaningfully
            # and are sure of what project they want to search for. Once they
            # find the project and open it they don't want to come back to the
            # previous search results. So, we clear out the search entry before
            # the greeter is shown again.
            self.__search_entry.set_text("")
            self.__search_entry.grab_focus()

    def __setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(GREETER_PERSPECTIVE_CSS.encode('UTF-8'))
        screen = Gdk.Screen.get_default()
        style_context = self.app.gui.get_style_context()
        style_context.add_provider_for_screen(screen, css_provider,
                                              Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def __create_headerbar(self):
        headerbar = Gtk.HeaderBar()

        self.__new_project_button = Gtk.Button.new_with_label(_("New"))
        self.__new_project_button.set_tooltip_text(_("Create a new project"))
        self.__new_project_button.set_action_name("greeter.new-project")

        self.__open_project_button = Gtk.Button.new_with_label(_("Open…"))
        self.__open_project_button.set_tooltip_text(_("Open an existing project"))
        self.__open_project_button.set_action_name("greeter.open-project")

        self.__selection_button = Gtk.Button.new_from_icon_name("object-select-symbolic",
                                                                Gtk.IconSize.BUTTON)
        self.__selection_button.set_tooltip_text(_("Select projects for removal"))
        self.__selection_button.connect("clicked", self.__selection_clicked_cb)

        self.__cancel_button = Gtk.Button.new_with_label(_("Cancel"))
        self.__cancel_button.connect("clicked", self.__cancel_clicked_cb)

        self.__warnings_button = Gtk.MenuButton.new()
        self.__warnings_button.props.image = Gtk.Image.new_from_icon_name("warning-symbolic", Gtk.IconSize.BUTTON)
        self.__warnings_button.set_popover(self.__create_warnings_popover())

        self.menu_button = self.__create_menu()

        headerbar.pack_start(self.__new_project_button)
        headerbar.pack_start(self.__open_project_button)
        headerbar.pack_end(self.menu_button)
        headerbar.pack_end(self.__selection_button)
        headerbar.pack_end(self.__cancel_button)
        headerbar.pack_end(self.__warnings_button)
        headerbar.show()

        return headerbar

    def __update_headerbar(self, welcome=False, projects=False, selection=False):
        """Updates the headerbar depending on the greeter state."""
        self.__new_project_button.set_visible(welcome or projects)
        self.__open_project_button.set_visible(welcome or projects)
        self.__cancel_button.set_visible(selection)
        self.__selection_button.set_visible(projects)
        self.menu_button.set_visible(welcome or projects)
        self.headerbar.set_show_close_button(welcome or projects)
        self.__warnings_button.set_visible((welcome or projects) and MISSING_SOFT_DEPS)

        if selection:
            self.headerbar.get_style_context().add_class("selection-mode")
            self.headerbar.set_title(_("Click an item to select"))
        else:
            self.headerbar.get_style_context().remove_class("selection-mode")
            if projects:
                self.headerbar.set_title(_("Select a Project"))
            else:
                self.headerbar.set_title(_("Pitivi"))

    def _create_actions(self):
        group = Gio.SimpleActionGroup()
        self.toplevel_widget.insert_action_group("greeter", group)
        self.headerbar.insert_action_group("greeter", group)

        self.new_project_action = Gio.SimpleAction.new("new-project", None)
        self.new_project_action.connect("activate", self.__new_project_cb)
        group.add_action(self.new_project_action)
        self.app.shortcuts.add("greeter.new-project", ["<Primary>n"],
                               self.new_project_action,
                               _("Create a new project"), group="win")

        self.open_project_action = Gio.SimpleAction.new("open-project", None)
        self.open_project_action.connect("activate", self.__open_project_cb)
        group.add_action(self.open_project_action)
        self.app.shortcuts.add("greeter.open-project", ["<Primary>o"],
                               self.open_project_action,
                               _("Open a project"), group="win")

    @staticmethod
    def __create_project_filter():
        filter_ = []
        for asset in GES.list_assets(GES.Formatter):
            filter_.append(asset.get_meta(GES.META_FORMATTER_EXTENSION))
        return tuple(filter_)

    @staticmethod
    def __create_menu():
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "mainmenubutton.ui"))
        menu_button = builder.get_object("menubutton")
        # Menu options we want to display.
        visible_options = ["menu_shortcuts", "menu_help", "menu_about"]
        for widget in builder.get_object("menu_box").get_children():
            if Gtk.Buildable.get_name(widget) not in visible_options:
                widget.hide()
            else:
                visible_options.remove(Gtk.Buildable.get_name(widget))
        assert not visible_options
        return menu_button

    def __drag_data_received_cb(self, unused_widget, unused_context, unused_x,
                                unused_y, data, unused_info, unused_time):
        """Opens the project file dragged from Nautilus."""
        uris = data.get_uris()
        if not uris:
            return

        uri = uris[0]
        extension = os.path.splitext(uri)[1][1:]
        if extension in self.__project_filter:
            self.app.project_manager.load_project(uri)

    def __new_project_cb(self, unused_action, unused_param):
        self.app.project_manager.new_blank_project()

    def __open_project_cb(self, unused_action, unused_param):
        dialog = BrowseProjectsDialog(self.app)
        response = dialog.run()
        uri = dialog.get_uri()
        dialog.destroy()
        if response == Gtk.ResponseType.OK:
            self.app.project_manager.load_project(uri)

    def __app_version_info_received_cb(self, app, unused_version_information):
        """Handles new version info."""
        if app.is_latest():
            # current version, don't show message
            return
        self.__show_newer_available_version()

    def __show_newer_available_version(self):
        latest_version = self.app.get_latest()

        if self.app.settings.lastCurrentVersion != latest_version:
            # new latest version, reset counter
            self.app.settings.lastCurrentVersion = latest_version
            self.app.settings.displayCounter = 0

        if self.app.settings.displayCounter >= 5:
            # current version info already showed 5 times, don't show again
            return

        # increment counter, create infobar and show info
        self.app.settings.displayCounter += 1
        text = _("Pitivi %s is available.") % latest_version
        label = Gtk.Label(label=text)
        self.__infobar.get_content_area().add(label)
        self.__infobar.set_message_type(Gtk.MessageType.INFO)
        self.__infobar.show_all()

    def __infobar_response_cb(self, unused_infobar, response_id):
        if response_id == Gtk.ResponseType.CLOSE:
            self.__infobar.hide()

    def __projects_row_activated_cb(self, unused_listbox, row):
        if row.select_button.get_visible():
            row.select_button.set_active(not row.select_button.get_active())
        else:
            self.app.project_manager.load_project(row.uri)

    def __projects_button_press_cb(self, listbox, event):
        if event.button == 3:
            self.__start_selection_mode()
            row = listbox.get_row_at_y(event.y)
            if row:
                row.select_button.set_active(True)

    def __search_changed_cb(self, search_entry):
        search_hit = False
        search_text = search_entry.get_text().lower()
        style_context = search_entry.get_style_context()

        for recent_project_item in self.__recent_projects_listbox.get_children():
            if search_text in recent_project_item.name.lower():
                recent_project_item.show()
                search_hit = True
            else:
                recent_project_item.hide()

        if not search_hit:
            style_context.add_class("error")
        else:
            style_context.remove_class("error")

        self.__recent_projects_labelbox.set_visible(search_hit)
        self.__recent_projects_listbox.set_visible(search_hit)

    def __selection_clicked_cb(self, unused_button):
        self.__start_selection_mode()

    def __start_selection_mode(self):
        if self.__actionbar.get_visible():
            return

        self.__update_headerbar(selection=True)
        self.__search_entry.hide()
        self.__actionbar.show()
        for child in self.__recent_projects_listbox.get_children():
            child.select_button.show()

    def __cancel_clicked_cb(self, unused_button):
        self.refresh()

    def __project_selected_cb(self, check_button, project):
        if check_button.get_active():
            self.__selected_projects.append(project)
        else:
            self.__selected_projects.remove(project)

        self.__remove_projects_button.set_sensitive(bool(self.__selected_projects))

    def __remove_projects_clicked_cb(self, unused_button):
        for project in self.__selected_projects:
            self.app.recent_manager.remove_item(project.uri)
        self.refresh()

    def __create_warnings_popover(self):
        """Creates a popover listing missing soft dependencies."""
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin=PADDING * 3)

        label = Gtk.Label(_("To enable additional features, please install the following packages and restart Pitivi:"))
        label.props.halign = Gtk.Align.START
        label.props.wrap = True
        label.props.xalign = 0
        box.pack_start(label, False, False, 0)

        grid = Gtk.Grid()
        grid.props.row_spacing = SPACING
        grid.props.column_spacing = PADDING
        grid.props.margin_start = SPACING
        grid.props.margin_top = SPACING * 2

        for row_index, dep in enumerate(MISSING_SOFT_DEPS.values()):
            name_label = Gtk.Label(dep.modulename)
            name_label.props.selectable = True
            name_label.props.can_focus = False
            name_label.props.xalign = 0
            name_label.props.valign = Gtk.Align.START
            grid.attach(name_label, 0, row_index, 1, 1)

            mdash_label = Gtk.Label("―")
            mdash_label.props.xalign = 0
            mdash_label.props.valign = Gtk.Align.START
            grid.attach(mdash_label, 1, row_index, 1, 1)

            description_label = Gtk.Label(dep.additional_message)
            description_label.props.wrap = True
            description_label.props.xalign = 0
            description_label.props.yalign = Gtk.Align.START
            grid.attach(description_label, 2, row_index, 1, 1)

        box.pack_start(grid, False, False, 0)

        wrapper_bin = BinWithNaturalWidth(box, width=500)
        wrapper_bin.show_all()
        popover.add(wrapper_bin)
        return popover
