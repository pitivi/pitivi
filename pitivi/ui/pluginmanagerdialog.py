# PiTiVi , Non-linear video editor
#
#       pitivi/ui/pluginmanagerdialog.py
#
# Copyright (c) 2007, Luca Della Santina <dellasantina@farm.unipi.it>
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

import os
import gtk
import gtk.glade
import pango
import gobject
from gettext import gettext as _

import pitivi.plugincore as plugincore
import pitivi.pluginmanager as pluginmanager

(COL_ENABLED, COL_INFO, COL_CATEGORY, COL_PLUGIN) = range(4)
(RESPONSE_ABOUT, RESPONSE_CONFIGURE, RESPONSE_DELETE) = range(3)

class PluginManagerDialog(object):
    """ This dialog is the main way user can interact with the plugin manager.
        It allows to install,remove,update,configure and enable plugins. """

    def __init__(self, plugin_manager):
        self.pm = plugin_manager

        # load user interface items
        glade_dir = os.path.dirname(os.path.abspath(__file__))
        self.wTree = gtk.glade.XML(os.path.join(glade_dir, 'pluginmanagerdialog.glade'))
        self.window = self.wTree.get_widget('pluginmanager_dlg')
        self.search_entry = self.wTree.get_widget('search_entry')
        self.category_cmb = self.wTree.get_widget('category_cmb')
        self.about_btn = self.wTree.get_widget('about_btn')
        self.configure_btn = self.wTree.get_widget('configure_btn')
        self.delete_btn = self.wTree.get_widget('delete_btn')
        self.plugin_tree = self.wTree.get_widget('plugin_tree')
        self.search_entry = self.wTree.get_widget('search_entry')

        # connect signals
        self.wTree.signal_autoconnect(self)

        # intialize plugin list
        self._initialize_plugin_tree(self.plugin_tree)
        self._initialize_category_cmb(self.category_cmb)
        self.refresh_category()
        self.refresh_tree()

        # show the window
        self.search_entry.grab_focus()
        self.window.show()

    def _initialize_plugin_tree(self, tree):
        """ Perform treeview initialization """

        self.model = gtk.ListStore(gobject.TYPE_BOOLEAN,
                                    gobject.TYPE_STRING,
                                    gobject.TYPE_STRING,
                                    object)

        # init tree view
        tree.set_model(self.model)
        tree.get_selection().set_mode(gtk.SELECTION_MULTIPLE)

        # Enable Drag&Drop
        tree.enable_model_drag_dest([("text/uri-list", 0, 1)], \
                                    gtk.gdk.ACTION_DEFAULT)
        tree.connect("drag-data-received", self.drag_data_received_cb)

        # plugin enabled status
        cell = gtk.CellRendererToggle()
        cell.set_property('activatable', True)
        cell.connect('toggled', self.plugin_enabled_cb, self.model)

        column = gtk.TreeViewColumn(_("Enabled"))
        tree.append_column(column)
        column.pack_start(cell, True)
        column.add_attribute(cell, 'active', COL_ENABLED)
        column.set_sort_column_id(COL_ENABLED)

        # plugin name
        cell = gtk.CellRendererText()
        cell.set_property("ellipsize", pango.ELLIPSIZE_END)

        column = gtk.TreeViewColumn(_("Plugin"))
        tree.append_column(column)
        column.pack_start(cell, True)
        column.set_min_width(300)
        column.add_attribute(cell, "markup", COL_INFO)
        column.set_sort_column_id(COL_INFO)

        # plugin category
        cell = gtk.CellRendererText()

        column = gtk.TreeViewColumn(_("Category"))
        tree.append_column(column)
        column.pack_start(cell, False)
        column.add_attribute(cell, 'text', COL_CATEGORY)
        column.set_sort_column_id(COL_CATEGORY)

    def _initialize_category_cmb(self, combo):
        """ perform category combobox initialization """

        self.model_category = gtk.ListStore(gobject.TYPE_STRING)
        combo.set_model(self.model_category)

    def search_entry_changed_cb(self, widget):
        """ filter the plugin list according to searched text """

        self.refresh_tree(self.search_entry.get_text())

        if self.search_entry.get_text():
            self.search_entry.modify_base(gtk.STATE_NORMAL,\
                                            gtk.gdk.color_parse("#FBFAD6"))
        else:
            self.search_entry.modify_base(gtk.STATE_NORMAL, None)

    def category_cmb_changed_cb(self, widget):
        """ Catch changes in category combobox triggered by the user """

        self.refresh_tree(self.search_entry.get_text())

    def refresh_tree(self, filter_text = None):
        """
        Refresh the list of plugins according to filter_text

        @param filter_text: plugin name must have this substring (case insensitive)
        """

        def _get_active_category():
            """ return the active category the chosen from the combobox """
            if self.category_cmb.get_active() > 0:
                return self.model_category[self.category_cmb.get_active()][0]
            else:
                return None

        self.model.clear()

        for plugin in self.pm.getPlugins(category=_get_active_category()):
            if filter_text and (plugin.name.lower().find(filter_text.lower()) < 0):
                continue

            rowiter = self.model.append()
            self.model.set_value(rowiter, COL_ENABLED, plugin.enabled)
            self.model.set_value(rowiter, COL_INFO, "<b>%s</b>\n%s"\
                                            %(plugin.name, plugin.description))
            self.model.set_value(rowiter, COL_CATEGORY, plugin.category)
            self.model.set_value(rowiter, COL_PLUGIN, plugin)

        # refresh available operations according to the new visualized list
        self.plugin_tree_button_release_cb(self.plugin_tree, None)

    def refresh_category(self):
        """ Refresh the list of plugin categories """
        self._initialize_category_cmb(self.category_cmb)

        # The first entry is always "All categories"
        rowiter = self.model_category.append()
        self.model_category.set_value(rowiter, 0, _("All categories"))

        categories = []
        # populate categories
        for plugin in self.pm.getPlugins():
            if not plugin.category in categories:
                categories.append(plugin.category)

        #populate combo model with categories
        for category in categories:
            rowiter = self.model_category.append()
            self.model_category.set_value(rowiter, 0, category)

        self.category_cmb.set_active(0)

    def response_cb(self, widget, response):
        """ Catch signal emitted by user-pressed buttons in the main bar """
        if response == gtk.RESPONSE_DELETE_EVENT:
            self.window.destroy()
        elif response == gtk.RESPONSE_CLOSE:
            self.window.destroy()
        elif response == RESPONSE_ABOUT:
            self.show_plugin_info()
        elif response == RESPONSE_CONFIGURE:
            for plugin in self._get_selected_plugins():
                plugin.configure()
        elif response == RESPONSE_DELETE:
            self.uninstall_selected_plugins()

    def plugin_enabled_cb(self, cell, path, model):
        """ Toggle loaded status for selected plugin"""

        model[path][COL_ENABLED] = model[path][COL_PLUGIN].enabled = not model[path][COL_PLUGIN].enabled

    def plugin_tree_button_release_cb(self, widget, event):
        """ Select plugins from the list """

        selection = widget.get_selection()
        if not selection:
            return

        if selection.count_selected_rows() == 1:
            self.about_btn.set_sensitive(True)

            (model, pathlist) = selection.get_selected_rows()
            row = model.get_iter(pathlist[0])
            plugin = model[row][COL_PLUGIN]
            self.configure_btn.set_sensitive(plugincore.IConfigurable.providedBy(plugin))
            self.delete_btn.set_sensitive(self.pm.canUninstall(plugin))
        elif selection.count_selected_rows() > 1:
            self.about_btn.set_sensitive(False)
            self.configure_btn.set_sensitive(False)
            self.delete_btn.set_sensitive(True)
        else:
            self.about_btn.set_sensitive(False)
            self.configure_btn.set_sensitive(False)
            self.delete_btn.set_sensitive(False)

    def _get_selected_plugins(self):
        """
        Retrieve from treeview widget those plugins selected by the use

        @return: the list of plugins selected by the user
        """

        selection = self.plugin_tree.get_selection()
        if not selection:
            return []

        (model, pathlist) = selection.get_selected_rows()
        sel_plugins = []
        for path in pathlist:
            row = model.get_iter(path)
            sel_plugins.append(model[row][COL_PLUGIN])

        return sel_plugins

    def show_plugin_info(self):
        """ Show the about dialog for selected plugins """

        for plugin in self._get_selected_plugins():
            dialog = gtk.AboutDialog()
            dialog.connect("response", lambda x, y: dialog.destroy())
            dialog.set_name(plugin.name)
            dialog.set_version(plugin.version)
            dialog.set_authors(plugin.authors.split(","))
            dialog.set_comments(plugin.description)
            dialog.show()

    def uninstall_selected_plugins(self):
        """ Uninstall plugins selected by the user """

        # ensure the user really wants this operation to be performed
        dialog = gtk.MessageDialog(
            parent = self.window,
            flags = gtk.DIALOG_MODAL,
            type = gtk.MESSAGE_WARNING,
            buttons = gtk.BUTTONS_OK_CANCEL,
            message_format = _("Are you sure you want to remove the selected plugins?"))
        dialog.set_title(_("Confirm remove operation"))
        try:
            if dialog.run() == gtk.RESPONSE_CANCEL:
                return
        finally:
            dialog.destroy()

        # remove selected plugins
        for plugin in self._get_selected_plugins():
            try:
                self.pm.uninstall(plugin)
            except Exception, e:
                error_dialog = gtk.MessageDialog(
                    parent = self.window,
                    flags = gtk.DIALOG_MODAL,
                    type = gtk.MESSAGE_ERROR,
                    buttons = gtk.BUTTONS_CLOSE,
                    message_format = _("Cannot remove %s") % (plugin.name))
                error_dialog.run()
                error_dialog.destroy()

        # refresh the plugin list
        self.pm.collect()
        self.refresh_tree()
        self.refresh_category()

    def drag_data_received_cb(self, widget, context, x, y, selection,
                            targetType, time):
        """ handle drag&drop of new plugins into the list by installing them"""

        uri_list = selection.data.strip().split()
        installed = False

        for uri in uri_list:
            # ensure a file is dragged
            if not (uri.startswith("file://") and os.path.isfile(uri[7:])):
                continue

            filename = uri[7:]
            try:
                self.pm.install(filename, self.pm.local_plugin_path)
                installed = True
            except plugincore.DuplicatePluginError, e:
                # Plugin already exists, ask the user if he wants to update
                dialog = gtk.MessageDialog(
                    parent = self.window,
                    flags = gtk.DIALOG_MODAL,
                    type = gtk.MESSAGE_WARNING,
                    buttons = gtk.BUTTONS_OK_CANCEL,
                    message_format = _("Update the existing plugin?"))

                dialog.format_secondary_text(
                    _("This plugin is already installed in your system.\nIf you agree, version %(v1)s will be replaced with version %(v2)s")\
                    %{'v1': e.old_plugin.version, 'v2': e.new_plugin.version})

                dialog.set_title(_("Duplicate plugin found"))
                try:
                    if dialog.run() == gtk.RESPONSE_OK:
                        self.pm.update(filename, self.pm.local_plugin_path)
                        installed = True
                finally:
                    dialog.destroy()
            except plugincore.InvalidPluginError, e:
                # The file user is trying to install is not a valid plugin
                error_dialog = gtk.MessageDialog(
                    parent = self.window,
                    flags = gtk.DIALOG_MODAL,
                    type = gtk.MESSAGE_ERROR,
                    buttons = gtk.BUTTONS_CLOSE,
                    message_format = _("Cannot install %s\nThe file is not a valid plugin") % e.filename)
                error_dialog.run()
                error_dialog.destroy()

        if installed:
            # refresh plugin list if the operation succedded
            self.pm.collect()
            self.refresh_tree()
            self.refresh_category()
            # Tell the drag source that operation succedded
            context.finish(success=True, del_=False, time=time)

if __name__ == "__main__":
    pm = pluginmanager.PluginManager("./plugins", "./plugins-settings")
    PluginManagerDialog(pm)
    gtk.main()
