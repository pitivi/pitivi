# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
# Copyright (c) 2013, 2014, 2015, Thibault Saunier <tsaunier@gnome.org>
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
"""Project related classes."""
import os
import pwd
import shutil
import tarfile
import tempfile
import time
import uuid
from gettext import gettext as _
from hashlib import md5
from typing import Optional
from urllib.parse import unquote

from gi.repository import GdkPixbuf
from gi.repository import GES
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GstPbutils
from gi.repository import GstVideo
from gi.repository import Gtk

from pitivi.medialibrary import AssetThumbnail
from pitivi.render import Encoders
from pitivi.settings import xdg_cache_home
from pitivi.timeline.previewers import Previewer
from pitivi.timeline.previewers import ThumbnailCache
from pitivi.undo.project import AssetAddedIntention
from pitivi.undo.project import AssetProxiedIntention
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import disconnect_all_by_func
from pitivi.utils.misc import fixate_caps_with_default_values
from pitivi.utils.misc import is_writable
from pitivi.utils.misc import path_from_uri
from pitivi.utils.misc import quote_uri
from pitivi.utils.misc import scale_pixbuf
from pitivi.utils.misc import unicode_error_dialog
from pitivi.utils.pipeline import Pipeline
from pitivi.utils.ui import beautify_time_delta
from pitivi.utils.ui import SPACING
from pitivi.utils.validate import create_monitor
from pitivi.utils.validate import has_validate


DEFAULT_NAME = _("Untitled")

ALL_RAW_VIDEO_FORMATS = []
# Starting at 2 as 0 is UNKNOWN and 1 is ENCODED.
# We want to make sure we do not try to force ENCODED
# format (as it won't be possible as we have a compositor
# in the pipeline) but we enforce a same VideoFormat is
# used during the whole encoding process.
for i in range(2, GLib.MAXINT):
    try:
        vformat = GstVideo.VideoFormat(i)
        ALL_RAW_VIDEO_FORMATS.append(
            GstVideo.VideoFormat.to_string(vformat))
    except ValueError:
        break

# Properties of encoders that should be ignored when saving/loading
# a project.
IGNORED_PROPS = ["name", "parent"]

# Caps used as the default project settings.
DEFAULT_VIDEO_SETTINGS = "video/x-raw,width=1920,height=1080,framerate=(GstFraction)30/1"
DEFAULT_AUDIO_SETTINGS = "audio/x-raw,channels=2,rate=96000"

# The minimum value for a decent audio rate.
DECENT_AUDIORATE = 44100

# Default values for the safe areas.
DEFAULT_TITLE_AREA_VERTICAL = 0.8
DEFAULT_TITLE_AREA_HORIZONTAL = 0.8
DEFAULT_ACTION_AREA_VERTICAL = 0.9
DEFAULT_ACTION_AREA_HORIZONTAL = 0.9

SCALED_THUMB_WIDTH = 96
SCALED_THUMB_HEIGHT = 54
SCALED_THUMB_DIR = "96x54"
ORIGINAL_THUMB_DIR = "original"


class ProjectManager(GObject.Object, Loggable):
    """The project manager.

    Allows the app to close and then load a different project, handle failures,
    make automatic backups.

    Attributes:
        app (Pitivi): The app.
        current_project (Project): The current project displayed by the app.
        disable_save (bool): Whether save-as is enforced when saving.
    """

    __gsignals__ = {
        "new-project-loading": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "new-project-created": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "new-project-failed": (GObject.SignalFlags.RUN_LAST, None, (str, str)),
        "new-project-loaded": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "save-project-failed": (GObject.SignalFlags.RUN_LAST, None, (str, object)),
        "project-saved": (GObject.SignalFlags.RUN_LAST, None, (object, str)),
        "closing-project": (GObject.SignalFlags.RUN_LAST, bool, (object,)),
        "project-closed": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "missing-uri": (GObject.SignalFlags.RUN_LAST, str, (object, str, object)),
        "reverting-to-saved": (GObject.SignalFlags.RUN_LAST, bool, (object,)),
    }

    def __init__(self, app):
        GObject.Object.__init__(self)
        Loggable.__init__(self)
        self.app = app
        self.current_project = None
        self.disable_save = False
        self._backup_lock = 0
        self.exitcode = 0
        self.__start_loading_time = 0
        self.time_loaded = 0

    def _try_using_backup_file(self, uri):
        backup_path = self._make_backup_uri(path_from_uri(uri))
        use_backup = False
        try:
            path = path_from_uri(uri)
            time_diff = os.path.getmtime(backup_path) - os.path.getmtime(path)
            self.debug(
                'Backup file is %d secs newer: %s', time_diff, backup_path)
        except OSError:
            self.debug('Backup file does not exist: %s', backup_path)
        except UnicodeEncodeError:
            unicode_error_dialog()
        else:
            if time_diff > 0:
                use_backup = self._restore_from_backup_dialog(time_diff)

                if use_backup:
                    uri = self._make_backup_uri(uri)
            self.debug('Loading project from backup: %s', uri)

        # For backup files and legacy formats, force the user to use "Save as"
        if use_backup or path.endswith(".xptv"):
            self.debug("Enforcing read-only mode")
            self.disable_save = True
        else:
            self.disable_save = False

        return uri

    def _is_validate_scenario(self, uri):
        if uri.endswith(".scenario") and has_validate is True:
            # Let's just normally fail if we do not have Validate
            # installed on the system
            return True

        return False

    def _project_pipeline_died_cb(self, unused_pipeline):
        """Shows an dialog telling the user that everything went kaboom."""
        # GTK does not allow an empty string as the dialog title, so we use the
        # same translatable one as render.py's pipeline error message dialog:
        dialog = Gtk.Dialog(title=_("Sorry, something didn’t work right."),
                            transient_for=self.app.gui)

        message = _("Pitivi detected a serious backend problem and could not "
                    "recover from it, even after multiple tries. The only thing "
                    "that can be done at this point is to <b>restart Pitivi</b>."
                    "\n\n"
                    "This is a rare and severe kind of bug. Please see our "
                    "<a href=\"http://developer.pitivi.org/Bug_reporting.html\">"
                    "bug reporting guide</a> and take the time to report it! "
                    "We will be very happy to fix this bug and make sure it "
                    "does not occur again in future versions."
                    "\n\n"
                    "Before closing Pitivi, you can save changes to the "
                    "existing project file or as a separate project file.")

        dialog.add_buttons(_("Save as..."), 1,
                           _("Save"), 2,
                           _("Close Pitivi"), Gtk.ResponseType.CLOSE)

        dialog.set_default_response(1)  # Default to "Save as"
        dialog.set_icon_name("pitivi")
        dialog.set_modal(True)
        dialog.get_accessible().set_name("pitivi died")

        primary = Gtk.Label()
        primary.set_line_wrap(True)
        primary.set_use_markup(True)
        primary.set_alignment(0, 0.5)
        primary.props.label = message

        # These 2 lines are needed for a decent dialog width, with wrapped text:
        dialog.props.default_width = 700
        primary.set_width_chars(50)

        # put the text in a vbox
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=SPACING * 2)
        vbox.pack_start(primary, True, True, 0)

        # make the [[image] text] hbox
        image = Gtk.Image.new_from_icon_name("dialog-error-symbolic", Gtk.IconSize.DIALOG)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=SPACING * 2)
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

        if response == 1:
            self.app.gui.editor.save_project_as()
        elif response == 2:
            self.app.gui.editor.save_project()

        self.app.shutdown()

    def load_project(self, uri):
        """Loads the specified URI as a project.

        If a backup file exists, asks if it should be loaded instead, and if so,
        forces the user to use "Save as" afterwards.
        """
        assert self.current_project is None

        is_validate_scenario = self._is_validate_scenario(uri)
        if not is_validate_scenario:
            uri = self._try_using_backup_file(uri)
            scenario = None
        else:
            scenario = path_from_uri(uri)
            uri = None

        # Load the project:
        self.__start_loading_time = time.time()
        project = Project(self.app, uri=uri, scenario=scenario)
        self.emit("new-project-loading", project)

        project.connect_after("missing-uri", self._missing_uri_cb)
        project.connect("loaded", self._project_loaded_cb)

        if not project.create_timeline():
            self.emit("new-project-failed", uri,
                      _('This might be due to a bug or an unsupported project file format. '
                        'If you were trying to add a media file to your project, '
                        'use the "Import" button instead.'))
            return None

        self.current_project = project
        self.emit("new-project-created", project)
        self.current_project.connect("project-changed", self._project_changed_cb)
        self.current_project.pipeline.connect("died", self._project_pipeline_died_cb)

        if is_validate_scenario:
            self.current_project.setup_validate_scenario()

        return project

    def _restore_from_backup_dialog(self, time_diff):
        """Asks if we need to load the autosaved project backup.

        Args:
            time_diff (int): The difference, in seconds, between file mtimes.
        """
        dialog = Gtk.Dialog(title="", transient_for=self.app.gui)
        ignore_backup_btn = dialog.add_button(_("Ignore backup"), Gtk.ResponseType.REJECT)
        ignore_backup_btn.get_style_context().add_class("destructive-action")
        dialog.add_button(_("Restore from backup"), Gtk.ResponseType.YES)
        dialog.set_icon_name("pitivi")
        dialog.set_modal(True)
        dialog.set_default_response(Gtk.ResponseType.YES)
        dialog.get_accessible().set_name("restore from backup dialog")

        primary = Gtk.Label()
        primary.set_line_wrap(True)
        primary.set_use_markup(True)
        primary.set_alignment(0, 0.5)

        message = _("An autosaved version of your project file was found. "
                    "It is %s newer than the saved project.\n\n"
                    "Would you like to load it instead?") % \
            beautify_time_delta(time_diff)
        primary.props.label = message

        # put the text in a vbox
        vbox = Gtk.Box(homogeneous=False, spacing=SPACING * 2)
        vbox.set_orientation(Gtk.Orientation.VERTICAL)
        vbox.pack_start(primary, True, True, 0)

        # make the [[image] text] hbox
        image = Gtk.Image.new_from_icon_name(
            "dialog-question-symbolic", Gtk.IconSize.DIALOG)
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
        return response == Gtk.ResponseType.YES

    def save_project(self, uri=None, formatter_type=None, backup=False):
        """Saves the current project.

        Args:
            uri (Optional[str]): If a URI is specified, this means we want to
                save to a new (different) location, so it will be used instead
                of the current project's existing URI.
            formatter_type (Optional[GES.Formatter]): The formatter to use for
                serializing the project. If None, GES defaults to
                GES.XmlFormatter.
            backup (Optional[bool]): Whether to ignore the `uri` arg and save
                the project to a special backup URI built out of the current
                project's URI. Intended for automatic backup behind the scenes.

        Returns:
            bool: Whether the project has been saved successfully.
        """
        if self.disable_save is True and (backup is True or uri is None):
            self.log(
                "Read-only mode is enforced and no new URI was specified, ignoring save request")
            return False

        if backup:
            if self.current_project is not None and self.current_project.uri is not None:
                # Ignore whatever URI that is passed on to us. It's a trap.
                uri = self._make_backup_uri(self.current_project.uri)
            else:
                # Do not try to save backup files for blank projects.
                # It is possible that self.current_project.uri == None when the backup
                # timer sent us an old instance of the (now closed) project.
                return False
        elif uri is None:
            # "Normal save" scenario. The filechoosers in mainwindow ask users
            # for permission to overwrite the file (if needed), so we're safe.
            uri = self.current_project.uri
        else:
            # "Save As" (or "normal-save a blank project") scenario. We use the
            # provided URI, so ensure it's properly encoded, or GIO will fail:
            uri = quote_uri(uri)

            if not is_writable(path_from_uri(uri)):
                # TODO: this will not be needed when GTK+ bug #601451 is fixed
                self.emit("save-project-failed", uri,
                          _("You do not have permissions to write to this folder."))
                return False

        try:
            # "overwrite" is always True: our GTK filechooser save dialogs are
            # set to always ask the user on our behalf about overwriting, so
            # if save_project is actually called, that means overwriting is OK.
            saved = self.current_project.save(
                self.current_project.ges_timeline, uri,
                formatter_type, overwrite=True)
        except GLib.Error as e:
            saved = False
            self.emit("save-project-failed", uri, e)

        if saved:
            if not backup:
                # Do not emit the signal when autosaving a backup file
                self.current_project.set_modification_state(False)
                self.debug('Saved project: %s', uri)
                # Update the project instance's uri,
                # otherwise, subsequent saves will be to the old uri.
                self.info("Setting the project instance's URI to: %s", uri)
                self.current_project.uri = uri
                self.disable_save = False
                self.emit("project-saved", self.current_project, uri)
            else:
                self.debug('Saved backup: %s', uri)

        return saved

    def export_project(self, project, uri):
        """Exports a project and all its media files to a *.tar archive."""
        # Save the project to a temporary file.
        project_name = project.name if project.name else _("project")
        asset = GES.Formatter.get_default()
        project_extension = asset.get_meta(GES.META_FORMATTER_EXTENSION)
        tmp_name = "%s.%s" % (project_name, project_extension)

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_uri = Gst.filename_to_uri(os.path.join(tmp_dir, tmp_name))
            # save_project updates the project URI... so we better back it up:
            _old_uri = self.current_project.uri
            self.save_project(tmp_uri)
            self.current_project.uri = _old_uri
            # create tar file
            try:
                with tarfile.open(path_from_uri(uri), mode="w") as tar:
                    # top directory in tar-file
                    top = "%s-export" % project_name
                    # add temporary project file
                    tar.add(path_from_uri(tmp_uri), os.path.join(top, tmp_name))

                    # get common path
                    sources = project.list_sources()
                    if self._all_sources_in_homedir(sources):
                        common = os.path.expanduser("~")
                    else:
                        common = "/"

                    # add all sources
                    for source in sources:
                        path = path_from_uri(source.get_id())
                        tar.add(
                            path, os.path.join(top, os.path.relpath(path, common)))
                    tar.close()
            # This catches errors with tarring; the GUI already shows errors while
            # saving projects (ex: permissions), so probably no GUI needed here.
            # Keep the exception generic enough to catch programming errors:
            except tarfile.TarError as e:
                everything_ok = False
                self.error(e)
                tar_file = path_from_uri(uri)
                if os.path.isfile(tar_file):
                    renamed = os.path.splitext(tar_file)[
                        0] + " (CORRUPT)" + "." + project_extension + "_tar"
                    self.warning(
                        'An error occurred, will save the tarball as "%s"', renamed)
                    os.rename(tar_file, renamed)
            else:
                everything_ok = True

        return everything_ok

    def _all_sources_in_homedir(self, sources):
        """Checks if all sources are located in the user's home directory."""
        homedir = os.path.expanduser("~")

        for source in sources:
            if not path_from_uri(source.get_id()).startswith(homedir):
                return False

        return True

    def close_running_project(self):
        """Closes the current project."""
        if self.current_project is None:
            self.warning(
                "Trying to close a project that was already closed/didn't exist")
            return True

        self.info("closing running project %s", self.current_project.uri)
        if not self.emit("closing-project", self.current_project):
            self.warning(
                "Could not close project - this could be because there were unsaved changes and the user cancelled when prompted about them")
            return False

        with Previewer.manager.paused(interrupt=True):
            self.current_project.finalize()

            project = self.current_project
            self.current_project = None
            project.create_thumb()
            self.emit("project-closed", project)
            disconnect_all_by_func(project, self._project_changed_cb)
            disconnect_all_by_func(project.pipeline, self._project_pipeline_died_cb)
            self._clean_backup(project.uri)
            self.exitcode = project.release()

        return True

    def new_blank_project(self):
        """Creates a new blank project and sets it as the current project.

        Returns:
            Project: The created project.
        """
        self.debug("New blank project")

        assert self.current_project is None

        self.__start_loading_time = time.time()
        project = Project(self.app)
        self.emit("new-project-loading", project)

        # setting default values for project metadata
        project.author = pwd.getpwuid(os.getuid()).pw_gecos.split(",")[0]

        project.create_timeline()
        project._ensure_tracks()  # pylint: disable=protected-access
        project.update_restriction_caps()
        self.current_project = project
        self.emit("new-project-created", project)

        project.connect("project-changed", self._project_changed_cb)
        project.pipeline.connect("died", self._project_pipeline_died_cb)
        project.set_modification_state(False)
        self.emit("new-project-loaded", self.current_project)
        project.loaded = True
        self.time_loaded = time.time()

        return project

    def revert_to_saved_project(self):
        """Discards all unsaved changes and reloads the current open project."""
        if self.current_project.uri is None or not self.current_project.has_unsaved_modifications():
            return True
        if not self.emit("reverting-to-saved", self.current_project):
            return False

        uri = self.current_project.uri
        self.current_project.set_modification_state(False)
        self.close_running_project()
        self.load_project(uri)
        return True

    def _project_changed_cb(self, project):
        # _backup_lock is a timer, when a change in the project is done it is
        # set to 10 seconds. If before those 10 secs pass another change occurs,
        # 5 secs are added to the timeout callback instead of saving the backup
        # file. The limit is 60 seconds.
        uri = project.uri
        if uri is None:
            return

        if self._backup_lock == 0:
            self._backup_lock = 10
            GLib.timeout_add_seconds(
                self._backup_lock, self._save_backup_cb, project, uri)
        else:
            if self._backup_lock < 60:
                self._backup_lock += 5

    def _save_backup_cb(self, unused_project, unused_uri):
        if self._backup_lock > 10:
            self._backup_lock -= 5
            return True
        else:
            self.save_project(backup=True)
            self._backup_lock = 0
        return False

    def _clean_backup(self, uri):
        if uri is None:
            return
        path = path_from_uri(self._make_backup_uri(uri))
        if os.path.exists(path):
            os.remove(path)
            self.debug('Removed backup file: %s', path)

    def _make_backup_uri(self, uri):
        """Generates a corresponding backup URI or path.

        This does not guarantee that the backup file actually exists or that
        the file extension is actually a project file.

        Args:
            uri (str): The project URI or file path.

        Returns:
            str: The backup version of the `uri`.
        """
        name, ext = os.path.splitext(uri)
        return name + ext + "~"

    def _missing_uri_cb(self, project, error, asset):
        new_uri = self.emit("missing-uri", project, error, asset)
        if not new_uri:
            project.at_least_one_asset_missing = True
        else:
            project.relocated_assets[asset.props.id] = new_uri
        project.set_modification_state(True)
        return new_uri

    def _project_loaded_cb(self, project, unused_timeline):
        self.debug("Project loaded %s", project.props.uri)
        if not self.current_project == project:
            self.debug("Project is obsolete %s", project.props.uri)
            return
        self.emit("new-project-loaded", project)
        project.loaded = True
        self.time_loaded = time.time()
        self.info("Loaded in %s", self.time_loaded - self.__start_loading_time)


class Project(Loggable, GES.Project):
    """A Pitivi project.

    Attributes:
        app (Pitivi): The app.
        name (str): The name of the project.
        description (str): The description of the project.
        ges_timeline (GES.Timeline): The timeline.
        pipeline (Pipeline): The timeline's pipeline.
        loaded (bool): Whether the project is fully loaded.

    Args:
        uri (Optional[str]): The URI of the file where the project should
            be loaded from.

    Signals:
        project-changed: Modifications were made to the project.
        start-importing: Started to import files.
    """

    __gsignals__ = {
        "asset-loading-progress": (GObject.SignalFlags.RUN_LAST, None, (object, int)),
        # Working around the fact that PyGObject does not let us emit error-loading-asset
        # and bugzilla does not let me file a bug right now :/
        "proxying-error": (GObject.SignalFlags.RUN_LAST, None,
                           (object,)),
        "start-importing": (GObject.SignalFlags.RUN_LAST, None, ()),
        "project-changed": (GObject.SignalFlags.RUN_LAST, None, ()),
        "settings-set-from-imported-asset": (GObject.SignalFlags.RUN_LAST, None,
                                             (GES.Asset,)),
        "video-size-changed": (GObject.SignalFlags.RUN_LAST, None, ()),
        "audio-channels-changed": (GObject.SignalFlags.RUN_LAST, None, ()),
        "safe-area-size-changed": (GObject.SignalFlags.RUN_LAST, None, ())
    }

    def __init__(self, app, uri=None, scenario=None, **unused_kwargs):
        Loggable.__init__(self)
        GES.Project.__init__(self, uri=uri, extractable_type=GES.Timeline)
        self.log("uri:%s", uri)
        self.pipeline = None
        self.ges_timeline = None
        self.uri = uri
        self.loaded = False
        self.at_least_one_asset_missing = False
        self.app = app
        self.loading_assets = set()

        self.relocated_assets = {}
        self.app.proxy_manager.connect("progress", self.__asset_transcoding_progress_cb)
        self.app.proxy_manager.connect("error-preparing-asset",
                                       self.__proxy_error_cb)
        self.app.proxy_manager.connect("asset-preparing-cancelled",
                                       self.__asset_transcoding_cancelled_cb)
        self.app.proxy_manager.connect("proxy-ready",
                                       self.__proxy_ready_cb)

        # GstValidate
        self.scenario = scenario
        self.runner = None
        self.monitor = None
        self._scenario = None

        # For keeping track of assets importing.
        self._dirty = False
        self.nb_remaining_file_to_import = 0
        self.nb_imported_files = 0

        # Main assets that were proxied when saving the project but
        # whose proxies had been deleted from the filesystem. The
        # proxy files are being regenerated.
        self.__deleted_proxy_files = set()

        # List of proxy assets uris that were deleted on the filesystem
        # and we are waiting for the main asset (ie. the file from
        # which the proxy was generated) to be loaded before we can try to
        # regenerate the proxy.
        self.__awaited_deleted_proxy_targets = set()

        # Project property default values
        self.register_meta(GES.MetaFlag.READWRITE, "author", "")

        self.register_meta(GES.MetaFlag.READWRITE, "scaled_proxy_width", 0)
        self.register_meta(GES.MetaFlag.READWRITE, "scaled_proxy_height", 0)
        self.register_meta(GES.MetaFlag.READWRITE, "pitivi::title_safe_area_vertical", DEFAULT_TITLE_AREA_VERTICAL)
        self.register_meta(GES.MetaFlag.READWRITE, "pitivi::title_safe_area_horizontal", DEFAULT_TITLE_AREA_HORIZONTAL)
        self.register_meta(GES.MetaFlag.READWRITE, "pitivi::action_safe_area_vertical", DEFAULT_ACTION_AREA_VERTICAL)
        self.register_meta(GES.MetaFlag.READWRITE, "pitivi::action_safe_area_horizontal", DEFAULT_ACTION_AREA_HORIZONTAL)

        # The rendering settings.
        self.set_meta("render-scale", 100.0)

        self.container_profile = \
            GstPbutils.EncodingContainerProfile.new("pitivi-profile",
                                                    _("Pitivi encoding profile"),
                                                    Gst.Caps("video/webm"),
                                                    None)
        has_default_settings = not bool(uri) and not bool(scenario)
        vsettings = DEFAULT_VIDEO_SETTINGS if has_default_settings else "video/x-raw"
        self.video_profile = GstPbutils.EncodingVideoProfile.new(
            Gst.Caps("video/x-vp8"), None, Gst.Caps(vsettings), 0)
        asettings = DEFAULT_AUDIO_SETTINGS if has_default_settings else "audio/x-raw"
        self.audio_profile = GstPbutils.EncodingAudioProfile.new(
            Gst.Caps("audio/x-vorbis"), None, Gst.Caps(asettings), 0)
        self.container_profile.add_profile(self.video_profile)
        self.container_profile.add_profile(self.audio_profile)

        # Add the container profile to the project so it is saved
        # as part of the project.
        res = self.add_encoding_profile(self.container_profile)
        assert res

        self.muxer = Encoders().default_muxer
        self.vencoder = Encoders().default_video_encoder
        self.aencoder = Encoders().default_audio_encoder
        res = self._ensure_audio_restrictions()
        assert res
        res = self._ensure_video_restrictions()
        assert res
        self._has_default_audio_settings = has_default_settings
        self._has_default_video_settings = has_default_settings

        # A ((container_profile, muxer) -> containersettings) map.
        self._containersettings_cache = {}
        # A ((container_profile, vencoder) -> vcodecsettings) map.
        self._vcodecsettings_cache = {}
        # A ((container_profile, aencoder) -> acodecsettings) map.
        self._acodecsettings_cache = {}
        # Whether the current settings are temporary and should be reverted,
        # as they apply only for rendering.
        self._has_rendering_values = False

    def _scenario_done_cb(self, scenario):
        if self.pipeline is not None:
            self.pipeline.set_force_position_listener(False)

    def setup_validate_scenario(self):
        from gi.repository import GstValidate

        self.info("Setting up validate scenario")
        self.runner = GstValidate.Runner.new()
        create_monitor(self.runner, self.app.gui)
        self.monitor = GstValidate.Monitor.factory_create(
            self.pipeline, self.runner, None)
        self._scenario = GstValidate.Scenario.factory_create(
            self.runner, self.pipeline, self.scenario)
        self.pipeline.set_force_position_listener(True)
        self._scenario.connect("done", self._scenario_done_cb)
        self._scenario.props.execute_on_idle = True

    # --------------- #
    # Our properties  #
    # --------------- #

    # Project specific properties
    @property
    def name(self):
        if not self.uri:
            return DEFAULT_NAME
        quoted_name = os.path.splitext(os.path.basename(self.uri))[0]
        return unquote(quoted_name)

    @property
    def year(self):
        return self.get_meta("year")

    @year.setter
    def year(self, year):
        if year == self.year:
            return
        self.set_meta("year", year)

    @property
    def description(self):
        return self.get_meta("description")

    @description.setter
    def description(self, description):
        if description == self.description:
            return
        self.set_meta("description", description)

    @property
    def author(self):
        return self.get_meta("author")

    @author.setter
    def author(self, author):
        if author == self.author:
            return
        self.set_meta("author", author)

    @property
    def scaled_proxy_height(self):
        return self.get_meta("scaled_proxy_height") or self.app.settings.default_scaled_proxy_height

    @scaled_proxy_height.setter
    def scaled_proxy_height(self, scaled_proxy_height):
        if scaled_proxy_height == self.get_meta("scaled_proxy_height"):
            return
        self.set_meta("scaled_proxy_height", scaled_proxy_height)
        self.set_modification_state(True)

    @property
    def scaled_proxy_width(self):
        return self.get_meta("scaled_proxy_width") or self.app.settings.default_scaled_proxy_width

    @scaled_proxy_width.setter
    def scaled_proxy_width(self, scaled_proxy_width):
        if scaled_proxy_width == self.get_meta("scaled_proxy_width"):
            return
        self.set_meta("scaled_proxy_width", scaled_proxy_width)
        self.set_modification_state(True)

    def has_scaled_proxy_size(self):
        """Returns whether the proxy size has been set."""
        return bool(self.get_meta("scaled_proxy_width") and self.get_meta("scaled_proxy_height"))

    @staticmethod
    def get_thumb_path(uri, resolution):
        """Returns path of thumbnail of specified resolution in the cache."""
        thumb_hash = md5(quote_uri(uri).encode()).hexdigest()
        thumbs_cache_dir = xdg_cache_home("project_thumbs", resolution)
        return os.path.join(thumbs_cache_dir, thumb_hash) + ".png"

    @classmethod
    def get_thumb(cls, uri):
        """Gets the project thumb, if exists, else the default thumb or None."""
        try:
            thumb = GdkPixbuf.Pixbuf.new_from_file(cls.get_thumb_path(uri, SCALED_THUMB_DIR))
        except GLib.Error:
            # Try to get the default thumb.
            try:
                thumb = Gtk.IconTheme.get_default().load_icon("video-x-generic", 128, 0)
            except GLib.Error:
                return None
            thumb = scale_pixbuf(thumb, SCALED_THUMB_WIDTH, SCALED_THUMB_HEIGHT)

        return thumb

    def __create_scaled_thumb(self):
        """Creates scaled thumbnail from the original thumbnail."""
        try:
            thumb = GdkPixbuf.Pixbuf.new_from_file(self.get_thumb_path(self.uri, ORIGINAL_THUMB_DIR))
            thumb = scale_pixbuf(thumb, SCALED_THUMB_WIDTH, SCALED_THUMB_HEIGHT)
            thumb.savev(self.get_thumb_path(self.uri, SCALED_THUMB_DIR), "png", [], [])
        except GLib.Error as e:
            self.warning("Failed to create scaled project thumbnail: %s", e)

    def __remove_thumbs(self):
        """Removes existing project thumbnails."""
        for thumb_dir in (ORIGINAL_THUMB_DIR, SCALED_THUMB_DIR):
            try:
                os.remove(self.get_thumb_path(self.uri, thumb_dir))
            except FileNotFoundError:
                pass

    @staticmethod
    def __pick_thumb_from_assets_thumbs(assets):
        """Picks project thumbnail from assets thumbnails."""
        for asset in assets:
            thumb_cache = ThumbnailCache.get(asset)
            thumb = thumb_cache.get_preview_thumbnail()
            if thumb:
                # First asset that has a preview thumbnail.
                return thumb
        return None

    def create_thumb(self):
        """Creates project thumbnails."""
        if not self.uri:
            return

        thumb_path = self.get_thumb_path(self.uri, ORIGINAL_THUMB_DIR)

        if os.path.exists(thumb_path) and not self.app.action_log.has_assets_operations():
            # The project thumbnail already exists and the assets are the same.
            return

        # Project Thumbnail Generation Approach: Out of thumbnails of all
        # the assets in the current project, the one with maximum file size
        # will be our project thumbnail - http://bit.ly/thumbnail-generation

        assets = self.list_sources()
        assets_uri = [asset.props.id for asset in assets]

        if not assets_uri:
            # There are no assets in the project,
            # so make sure there are no project thumbs.
            self.__remove_thumbs()
            return

        normal_thumb_path = None
        large_thumb_path = None
        normal_thumb_size = 0
        large_thumb_size = 0
        n_normal_thumbs = 0
        n_large_thumbs = 0

        for uri in assets_uri:
            path_128, path_256 = AssetThumbnail.get_asset_thumbnails_path(uri)

            try:
                thumb_size = os.stat(path_128).st_size
                if thumb_size > normal_thumb_size:
                    normal_thumb_path = path_128
                    normal_thumb_size = thumb_size
                n_normal_thumbs += 1
            except FileNotFoundError:
                # The asset is missing the normal thumbnail.
                pass

            try:
                thumb_size = os.stat(path_256).st_size
                if thumb_size > large_thumb_size:
                    large_thumb_path = path_256
                    large_thumb_size = thumb_size
                n_large_thumbs += 1
            except FileNotFoundError:
                # The asset is missing the large thumbnail.
                pass

        if normal_thumb_path or large_thumb_path:
            # Use the category for which we found the max number of
            # thumbnails to find the most complex thumbnail, because
            # we can't compare the small with the large.
            if n_normal_thumbs > n_large_thumbs:
                shutil.copyfile(normal_thumb_path, thumb_path)
            else:
                shutil.copyfile(large_thumb_path, thumb_path)
        else:
            # No thumbnails available in the XDG cache.
            thumb = self.__pick_thumb_from_assets_thumbs(assets)
            if not thumb:
                return
            thumb.savev(thumb_path, "png", [], [])

        self.__create_scaled_thumb()

    def set_rendering(self, rendering):
        """Sets the a/v restrictions for rendering or for editing."""
        res = self._ensure_audio_restrictions()
        assert res
        res = self._ensure_video_restrictions()
        assert res

        video_restrictions = self.video_profile.get_restriction().copy_nth(0)

        if self._has_rendering_values != rendering:
            # pylint: disable=attribute-defined-outside-init
            if rendering:
                video_restrictions_struct = video_restrictions[0]
                self.__width = video_restrictions_struct["width"]
                self.__height = video_restrictions_struct["height"]
                width = int(self.__width * self.render_scale / 100)
                height = int(self.__height * self.render_scale / 100)
            else:
                width = self.__width
                height = self.__height

            video_restrictions.set_value("width", width)
            video_restrictions.set_value("height", height)

        self._has_rendering_values = rendering
        self.video_profile.set_restriction(video_restrictions)

    @staticmethod
    def _set_restriction(profile, name, value):
        """Sets a restriction on the specified profile.

        Assumes the profile has a single restriction.

        Args:
            profile (GstPbutils.EncodingProfile): The profile to be updated.

        Returns:
            bool: Whether the profile actually changed.
        """
        caps = profile.get_restriction()
        if caps[0][name] == value or not value:
            return False

        restriction = caps.copy_nth(0)
        restriction.set_value(name, value)
        profile.set_restriction(restriction)
        return True

    def _set_video_restriction(self, name, value):
        """Updates the video profile and the corresponding project settings."""
        res = Project._set_restriction(self.video_profile, name, value)
        if res:
            self.emit("video-size-changed")
            self._has_default_video_settings = False
        return res

    def _set_audio_restriction(self, name, value):
        """Updates the audio profile and the corresponding project settings."""
        res = Project._set_restriction(self.audio_profile, name, value)
        if res:
            self.emit("audio-channels-changed")
            self._has_default_audio_settings = False
            self.update_restriction_caps()
        return res

    @property
    def videowidth(self):
        return self.video_profile.get_restriction()[0]["width"]

    @videowidth.setter
    def videowidth(self, value):
        if self._set_video_restriction("width", int(value)):
            self.update_restriction_caps()
            self.set_modification_state(True)

    @property
    def videoheight(self):
        return self.video_profile.get_restriction()[0]["height"]

    @videoheight.setter
    def videoheight(self, value):
        if self._set_video_restriction("height", int(value)):
            self.update_restriction_caps()
            self.set_modification_state(True)

    @property
    def videorate(self):
        return self.video_profile.get_restriction()[0]["framerate"]

    @videorate.setter
    def videorate(self, value):
        if self._set_video_restriction("framerate", value):
            self.update_restriction_caps()
            self.set_modification_state(True)

    def set_video_properties(self, width, height, framerate):
        """Sets the video properties in one operation.

        This should be called when several properties can be changed at once,
        to avoid GES repositioning all sources when the video size changes.

        Args:
            width (int): The new project width.
            height (int): The new project height.
            framerate (Gst.Fraction): The new project framerate.
        """
        changed = any([self._set_video_restriction("width", int(width)),
                       self._set_video_restriction("height", int(height)),
                       self._set_video_restriction("framerate", framerate)])
        if changed:
            self.update_restriction_caps()
            self.set_modification_state(True)

    @property
    def audiochannels(self) -> int:
        # The map does not always contain "channels".
        return self.audio_profile.get_restriction()[0]["channels"] or 0

    @audiochannels.setter
    def audiochannels(self, value: int):
        if self._set_audio_restriction("channels", int(value)):
            self.set_modification_state(True)

    @property
    def audiorate(self):
        try:
            return int(self.audio_profile.get_restriction()[0]["rate"])
        except TypeError:
            return None

    @audiorate.setter
    def audiorate(self, value):
        if self._set_audio_restriction("rate", int(value)):
            self.set_modification_state(True)

    @property
    def aencoder(self):
        return self.audio_profile.get_preset_name()

    @aencoder.setter
    def aencoder(self, preset_factory_name):
        if self._update_encoding_profile(self.audio_profile, preset_factory_name):
            self.set_modification_state(True)

    @property
    def vencoder(self):
        return self.video_profile.get_preset_name()

    @vencoder.setter
    def vencoder(self, preset_factory_name):
        if self._update_encoding_profile(self.video_profile, preset_factory_name):
            self.set_modification_state(True)

    @property
    def muxer(self):
        return self.container_profile.get_preset_name()

    @muxer.setter
    def muxer(self, preset_factory_name):
        if self._update_encoding_profile(self.container_profile, preset_factory_name):
            self.set_modification_state(True)

    def _update_encoding_profile(self, profile, preset_factory_name):
        """Updates the specified encoding profile.

        Args:
            profile (GstPbutils.EncodingProfile): The profile to be updated.
            preset_factory_name (str): The name of the Gst.Preset’s factory
                to be used in the profile.

        Returns:
            bool: Whether the profile has been changed.
        """
        if profile.get_preset_name() == preset_factory_name or not preset_factory_name:
            return False

        caps = self._get_caps_from_feature(preset_factory_name)
        if caps:
            profile.set_format(caps)

        # Set the name of the factory for producing the audio encoder.
        profile.set_preset_name(preset_factory_name)

        # Make sure the encoder does not use any encoding preset.
        # Gst.Preset can be set exclusively through EncodingTargets for now.
        profile.set_preset(None)

        return True

    def _get_caps_from_feature(self, name):
        """Gets the caps for the source static pad template of a feature."""
        feature = Gst.Registry.get().lookup_feature(name)
        if not feature:
            self.error("%s not in registry", name)
            return None
        for template in feature.get_static_pad_templates():
            if template.name_template == "src":
                return Gst.Caps(template.get_caps()[0].to_string())
        self.error("%s has no source static pad templates", name)
        return None

    @property
    def render_scale(self):
        return self.get_meta("render-scale")

    @render_scale.setter
    def render_scale(self, value):
        if value:
            self.set_meta("render-scale", value)

    def set_safe_areas_sizes(self, title_horizontal_factor, title_vertical_factor, action_horizontal_factor, action_vertical_factor):
        """Sets the safe areas sizes in one operation."""
        self.title_safe_area_horizontal = title_horizontal_factor
        self.title_safe_area_vertical = title_vertical_factor
        self.action_safe_area_horizontal = action_horizontal_factor
        self.action_safe_area_vertical = action_vertical_factor

    @property
    def title_safe_area_vertical(self):
        return self.get_meta("pitivi::title_safe_area_vertical")

    @title_safe_area_vertical.setter
    def title_safe_area_vertical(self, percentage):
        if percentage == self.get_meta("pitivi::title_safe_area_vertical"):
            return
        self.set_meta("pitivi::title_safe_area_vertical", percentage)
        self.emit("safe-area-size-changed")

    @property
    def title_safe_area_horizontal(self):
        return self.get_meta("pitivi::title_safe_area_horizontal")

    @title_safe_area_horizontal.setter
    def title_safe_area_horizontal(self, percentage):
        if percentage == self.get_meta("pitivi::title_safe_area_horizontal"):
            return
        self.set_meta("pitivi::title_safe_area_horizontal", percentage)
        self.emit("safe-area-size-changed")

    @property
    def action_safe_area_vertical(self):
        return self.get_meta("pitivi::action_safe_area_vertical")

    @action_safe_area_vertical.setter
    def action_safe_area_vertical(self, percentage):
        if percentage == self.get_meta("pitivi::action_safe_area_vertical"):
            return
        self.set_meta("pitivi::action_safe_area_vertical", percentage)
        self.emit("safe-area-size-changed")

    @property
    def action_safe_area_horizontal(self):
        return self.get_meta("pitivi::action_safe_area_horizontal")

    @action_safe_area_horizontal.setter
    def action_safe_area_horizontal(self, percentage):
        if percentage == self.get_meta("pitivi::action_safe_area_horizontal"):
            return
        self.set_meta("pitivi::action_safe_area_horizontal", percentage)
        self.emit("safe-area-size-changed")

    # ------------------------------#
    # Proxy creation implementation #
    # ------------------------------#
    def __asset_transcoding_progress_cb(self, proxy_manager, asset,
                                        creation_progress, estimated_time):
        self.__update_asset_loading_progress(estimated_time)

    def __get_loading_project_progress(self):
        """Computes current advancement of asset loading during project loading.

        During project loading we keep all loading assets to keep track of real advancement
        during the whole process, whereas while adding new assets, they get removed from
        the `loading_assets` list once the proxy is ready.

        Returns:
            int: The current asset loading progress (in percent).
        """
        num_loaded = 0
        all_ready = True
        for asset in self.loading_assets:
            if asset.creation_progress < 100:
                all_ready = False
            else:
                # Check that we are not recreating deleted proxy
                proxy_uri = self.app.proxy_manager.get_proxy_uri(asset)
                scaled_proxy_uri = self.app.proxy_manager.get_proxy_uri(asset, scaled=True)

                no_hq_proxy = False
                no_scaled_proxy = False

                if proxy_uri and proxy_uri not in self.__deleted_proxy_files and \
                        asset.props.id not in self.__awaited_deleted_proxy_targets:
                    no_hq_proxy = True

                if scaled_proxy_uri and scaled_proxy_uri not in self.__deleted_proxy_files and \
                        asset.props.id not in self.__awaited_deleted_proxy_targets:
                    no_scaled_proxy = True

                if no_hq_proxy and no_scaled_proxy:
                    asset.ready = True

                num_loaded += 1

        if all_ready:
            return 100

        return (num_loaded / len(self.loading_assets)) * 100

    def __get_loading_assets_progress(self):
        """Computes current advancement of asset loading.

        Returns:
            int: The current asset loading progress (in percent).
        """
        total_import_duration = 0
        for asset in self.loading_assets:
            total_import_duration += asset.get_duration()

        if total_import_duration == 0:
            self.info("No known duration yet")
            return 0

        asset_loading_progress = 0
        all_ready = True
        for asset in self.loading_assets:
            asset_weight = asset.get_duration() / total_import_duration
            asset_loading_progress += asset_weight * asset.creation_progress

            if asset.creation_progress < 100:
                all_ready = False
            elif not asset.ready:
                self.set_modification_state(True)
                asset.ready = True

        if all_ready:
            asset_loading_progress = 100

        return asset_loading_progress

    def __update_asset_loading_progress(self, estimated_time=0):
        if not self.loading_assets:
            self.emit("asset-loading-progress", 100, estimated_time)
            return

        if not self.loaded:
            progress = self.__get_loading_project_progress()
        else:
            progress = self.__get_loading_assets_progress()

        self.emit("asset-loading-progress", progress, estimated_time)

        if progress == 100:
            self.info("No more loading assets")
            self.loading_assets = set()

    def __asset_transcoding_cancelled_cb(self, unused_proxy_manager, asset):
        self.__set_proxy(asset, None)
        self.__update_asset_loading_progress()

    def __proxy_error_cb(self, unused_proxy_manager, asset, proxy, error):
        if asset is None:
            asset_id = self.app.proxy_manager.get_target_uri(proxy)
            if asset_id:
                asset = GES.Asset.request(proxy.get_extractable_type(),
                                          asset_id)
                if not asset:
                    for tmpasset in self.loading_assets:
                        if tmpasset.props.id == asset_id:
                            asset = tmpasset
                            break

                    if not asset:
                        self.error("Could not get the asset %s from its proxy %s", asset_id,
                                   proxy.props.id)

                        return
            else:
                self.info("%s is not a proxy asset", proxy.props.id)

                return

        asset.proxying_error = error
        asset.creation_progress = 100

        self.emit("proxying-error", asset)
        self.__update_asset_loading_progress()

    def __proxy_ready_cb(self, unused_proxy_manager, asset, proxy):
        if proxy and proxy.props.id in self.__deleted_proxy_files:
            self.info("Recreated proxy is now ready, stop having"
                      " its target as a proxy.")
            proxy.unproxy(asset)

        self.__set_proxy(asset, proxy)

    def __set_proxy(self, asset, proxy):
        asset.creation_progress = 100
        asset.ready = True
        if proxy:
            self.finalize_proxy(proxy)

        asset.set_proxy(proxy)
        try:
            self.loading_assets.remove(asset)
        except KeyError:
            pass

        if proxy:
            self.add_asset(proxy)
            self.loading_assets.add(proxy)

        self.__update_asset_loading_progress()

    def finalize_proxy(self, proxy):
        proxy.ready = False
        proxy.error = None
        proxy.creation_progress = 100

    # ------------------------------------------ #
    # GES.Project virtual methods implementation #
    # ------------------------------------------ #
    def do_asset_loading(self, asset):
        if asset and not GObject.type_is_a(asset.get_extractable_type(), GES.UriClip):
            # Ignore for example the assets producing GES.TitleClips.
            return

        self._prepare_asset_processing(asset)

    def __regenerate_missing_proxy(self, asset, scaled=False):
        self.info("Re generating deleted proxy file %s.", asset.props.id)
        GES.Asset.needs_reload(GES.UriClip, asset.props.id)
        self._prepare_asset_processing(asset)
        asset.force_proxying = True
        self.app.proxy_manager.add_job(asset, scaled=scaled)
        self.__update_asset_loading_progress()

    def do_missing_uri(self, error, asset):
        if self.app.proxy_manager.is_proxy_asset(asset):
            self.debug("Missing proxy file: %s", asset.props.id)
            target_uri = self.app.proxy_manager.get_target_uri(asset)

            # Take asset relocation into account.:
            target_uri = self.relocated_assets.get(target_uri, target_uri)

            GES.Asset.needs_reload(GES.UriClip, asset.props.id)
            # Check if the target has already been loaded.
            target = [asset for asset in self.list_assets(GES.UriClip) if
                      asset.props.id == target_uri]
            if target:
                scaled = self.app.proxy_manager.is_scaled_proxy(asset)
                self.__regenerate_missing_proxy(target[0], scaled=scaled)
            else:
                self.__awaited_deleted_proxy_targets.add(target_uri)

            self.__deleted_proxy_files.add(asset.props.id)
            return target_uri

        new_uri = GES.Project.do_missing_uri(self, error, asset)

        if new_uri:
            self.relocated_assets[asset.props.id] = new_uri

        return new_uri

    def _prepare_asset_processing(self, asset):
        asset.creation_progress = 0
        asset.error = None
        asset.ready = False
        asset.force_proxying = False
        asset.proxying_error = None

        if not self.loading_assets:
            # Progress == 0 means "starting to import"
            self.emit("asset-loading-progress", 0, 0)

        self.loading_assets.add(asset)

    def do_asset_removed(self, asset):
        self.app.proxy_manager.cancel_job(asset)

    def do_asset_added(self, asset):
        """Handles `GES.Project::asset-added` emitted by self."""
        self._maybe_init_settings_from_asset(asset)
        if asset and not GObject.type_is_a(asset.get_extractable_type(),
                                           GES.UriClip):
            # Ignore for example the assets producing GES.TitleClips.
            self.debug("Ignoring asset: %s", asset.props.id)
            return

        if asset not in self.loading_assets:
            self.debug("Asset %s is not in loading assets, "
                       " it must not be proxied", asset.get_id())
            return

        if asset.props.id in self.__awaited_deleted_proxy_targets:
            self.__regenerate_missing_proxy(asset)
            self.__awaited_deleted_proxy_targets.remove(asset.props.id)
        elif asset.props.id in self.__deleted_proxy_files:
            self.info("Deleted proxy file %s now ready again.", asset.props.id)
            self.__deleted_proxy_files.remove(asset.props.id)

        if self.loaded:
            if not asset.get_proxy_target() in self.list_assets(GES.Extractable):
                self.app.proxy_manager.add_job(asset)
        else:
            self.debug("Project still loading, not using proxies: %s",
                       asset.props.id)
            asset.creation_progress = 100
            self.__update_asset_loading_progress()

    def do_loading_error(self, error, asset_id, unused_type):
        """Handles `GES.Project::error-loading-asset` emitted by self."""
        asset = None
        for asset in self.loading_assets:
            if asset.get_id() == asset_id:
                break

        self.error("Could not load %s: %s -> %s", asset_id, error, asset)
        asset.error = error
        asset.creation_progress = 100
        if self.loaded:
            self.loading_assets.remove(asset)
        self.__update_asset_loading_progress()

    def do_loaded(self, unused_timeline):
        """Handles `GES.Project::loaded` emitted by self."""
        if not self.ges_timeline:
            return

        self._ensure_tracks()
        self.ges_timeline.props.auto_transition = True
        self._ensure_layer()

        if self.uri:
            self.loading_assets = {asset for asset in self.loading_assets
                                   if self.app.proxy_manager.is_asset_queued(asset)}

            if self.loading_assets:
                self.debug("The following assets are still being transcoded: %s."
                           " (They must be proxied assets with missing/deleted"
                           " proxy files).", self.loading_assets)
            self.__update_asset_loading_progress()

        if self.scenario is not None:
            return

        profiles = self.list_encoding_profiles()
        # The project just loaded, check the new
        # encoding profile and make use of it now.
        self.info("Using first usable encoding profile: %s", [p.get_preset_name() for p in profiles])
        for profile in profiles:
            if self.set_container_profile(profile):
                break

        self._load_encoder_settings(profiles)

    def set_container_profile(self, container_profile: GstPbutils.EncodingContainerProfile) -> bool:
        """Sets the specified container profile as new profile if usable.

        Returns:
            True if it has been set successfully.
        """
        if container_profile == self.container_profile:
            return True

        muxer = self.get_element_factory_name(container_profile)
        if muxer is None:
            muxer = Encoders().default_muxer
        container_profile.set_preset_name(muxer)

        video_profile: Optional[GstPbutils.EncodingVideoProfile] = None
        audio_profile: Optional[GstPbutils.EncodingAudioProfile] = None
        vencoder: Optional[str] = None
        aencoder: Optional[str] = None
        for profile in container_profile.get_profiles():
            if isinstance(profile, GstPbutils.EncodingVideoProfile):
                video_profile = profile
                if profile.get_restriction() is None:
                    profile.set_restriction(Gst.Caps("video/x-raw"))

                if not self._ensure_video_restrictions(profile):
                    return False

                vencoder = self.get_element_factory_name(profile)
                if vencoder:
                    profile.set_preset_name(vencoder)
            elif isinstance(profile, GstPbutils.EncodingAudioProfile):
                audio_profile = profile
                if profile.get_restriction() is None:
                    profile.set_restriction(Gst.Caps("audio/x-raw"))

                if not self._ensure_audio_restrictions(profile):
                    return False

                aencoder = self.get_element_factory_name(profile)
                if aencoder:
                    profile.set_preset_name(aencoder)
            else:
                self.warning("We do not handle profile: %s", profile)

        if not aencoder:
            self.error("Can't use profile, no audio encoder found.")
            return False

        if not vencoder:
            self.error("Can't use profile, no video encoder found.")
            return False

        self.container_profile = container_profile
        self.video_profile = video_profile
        self.audio_profile = audio_profile

        return True

    def is_profile_subset(self, profile, superset):
        return self.get_element_factory_name(profile) == self.get_element_factory_name(superset)

    def matches_container_profile(self, container_profile):
        if not self.is_profile_subset(container_profile, self.container_profile):
            return False

        video_matches = False
        has_video = False
        audio_matches = False
        has_audio = False
        for profile in container_profile.get_profiles():
            if isinstance(profile, GstPbutils.EncodingVideoProfile):
                has_video = True
                video_matches |= self.is_profile_subset(profile, self.video_profile)

                # For example: "Profile Youtube"
                preset_name = profile.get_preset()
                if preset_name:
                    # We assume container_profile has the same preset
                    # as the included video profile.

                    current_preset_name = self.video_profile.get_preset()
                    if not current_preset_name:
                        return False

                    # For example: "x264enc"
                    preset_factory_name = self.video_profile.get_preset_name()
                    tmp_preset = Gst.ElementFactory.make(preset_factory_name, None)
                    tmp_preset.load_preset(current_preset_name)

                    res, last_applied_preset_name = tmp_preset.get_meta(current_preset_name, "pitivi::OriginalPreset")
                    if res and preset_name != last_applied_preset_name:
                        return False

            elif isinstance(profile, GstPbutils.EncodingAudioProfile):
                has_audio = True
                audio_matches |= self.is_profile_subset(profile, self.audio_profile)

        if has_audio:
            if not audio_matches:
                return False

        if has_video:
            if not video_matches:
                return False

        return True

    def _load_encoder_settings(self, profiles):
        for container_profile in profiles:
            if not isinstance(container_profile, GstPbutils.EncodingContainerProfile):
                self.warning("%s is not an EncodingContainerProfile", container_profile)
                continue

            for profile in container_profile.get_profiles():
                preset_name = profile.get_preset()
                if not preset_name:
                    continue

                preset_factory_name = profile.get_preset_name()
                preset = Gst.ElementFactory.make(preset_factory_name, None)
                if not isinstance(preset, Gst.Preset):
                    self.warning("Element %s does not implement Gst.Preset. Cannot load"
                                 "its rendering settings", preset)
                    continue

                if profile.get_type_nick() == "video":
                    cache = self._vcodecsettings_cache
                elif profile.get_type_nick() == "audio":
                    cache = self._acodecsettings_cache
                else:
                    self.warning("Unrecognized profile type for profile %s", profile)
                    continue
                cache_key = (container_profile, preset_factory_name)

                if not preset.load_preset(preset_name):
                    self.warning("No preset named %s for encoder %s", preset_name, preset)
                    continue

                cache[cache_key] = {prop.name: preset.get_property(prop.name)
                                    for prop in GObject.list_properties(preset)
                                    if prop.name not in IGNORED_PROPS and prop.flags & GObject.ParamFlags.WRITABLE}

    # ------------------------------------------ #
    # Our API                                    #
    # ------------------------------------------ #

    def finalize(self):
        """Disconnects all signals and everything.

        Makes sure the project won't be doing anything after the call.
        """
        if self._scenario:
            self._scenario.disconnect_by_func(self._scenario_done_cb)
        self.app.proxy_manager.disconnect_by_func(self.__asset_transcoding_progress_cb)
        self.app.proxy_manager.disconnect_by_func(self.__proxy_error_cb)
        self.app.proxy_manager.disconnect_by_func(self.__asset_transcoding_cancelled_cb)
        self.app.proxy_manager.disconnect_by_func(self.__proxy_ready_cb)

    def save(self, ges_timeline, uri, formatter_asset, overwrite):
        for container_profile in self.list_encoding_profiles():
            if not isinstance(container_profile, GstPbutils.EncodingContainerProfile):
                self.warning("%s is not an EncodingContainerProfile", container_profile)
                continue

            for profile in container_profile.get_profiles():
                preset_factory_name = profile.get_preset_name()
                preset = Gst.ElementFactory.make(preset_factory_name, None)
                if not isinstance(preset, Gst.Preset):
                    self.warning("Element %s does not implement Gst.Preset. Cannot save"
                                 "its rendering settings", preset)
                    continue

                if profile.get_type_nick() == "video":
                    cache = self._vcodecsettings_cache
                elif profile.get_type_nick() == "audio":
                    cache = self._acodecsettings_cache
                else:
                    self.warning("Unrecognized profile type for profile %s", profile)
                    continue
                cache_key = (container_profile, preset_factory_name)
                if cache_key not in cache:
                    continue

                current_preset = profile.get_preset()
                if current_preset and current_preset.startswith("encoder_settings_"):
                    current_preset = None

                # The settings for the current GstPbutils.EncodingProfile.
                settings = cache[cache_key]
                # The name of the Gst.Preset storing the settings.
                preset_name = "encoder_settings_%s" % uuid.uuid4().hex
                # The project has three GstPbutils.EncodingProfile,
                # for the container, for the video, for the audio.
                # Each of them keeps the encoding settings in a Gst.Preset
                # saved externally in a separate file.
                # When the project is loaded, the encoding settings are loaded
                # automatically.
                profile.set_preset(preset_name)

                # The original preset name is also important.
                preset.set_meta(preset_name, "pitivi::OriginalPreset", current_preset)

                # Store the current GstPbutils.EncodingProfile's settings
                # in the Gst.Preset.
                for prop, value in settings.items():
                    preset.set_property(prop, value)

                # Serialize the GstPbutils.EncodingProfile's settings
                # from the cache into e.g.
                # $XDG_DATA_HOME/gstreamer-1.0/presets/GstX264Enc.prs
                # for x264enc presets.
                res = preset.save_preset(preset_name)
                assert res

        return GES.Project.save(self, ges_timeline, uri, formatter_asset, overwrite)

    def use_proxies_for_assets(self, assets, scaled=False):
        proxy_manager = self.app.proxy_manager
        originals = []
        for asset in assets:
            if proxy_manager.asset_can_be_proxied(asset, scaled):
                target = asset.get_proxy_target()
                uri = proxy_manager.get_proxy_uri(asset, scaled=scaled)
                if target and target.props.id == uri:
                    self.info("Missing proxy needs to be recreated after cancelling"
                              " its recreation")
                    target.unproxy(asset)

                originals.append(asset)

        if originals:
            with self.app.action_log.started("Proxying assets"):
                for asset in originals:
                    action = AssetProxiedIntention(asset, self, self.app.proxy_manager)
                    self.app.action_log.push(action)
                    self._prepare_asset_processing(asset)
                    asset.force_proxying = True
                    proxy_manager.add_job(asset, scaled)

    def disable_proxies_for_assets(self, assets, delete_proxy_file=False, hq_proxy=True):
        proxy_manager = self.app.proxy_manager
        for asset in assets:
            if proxy_manager.is_proxy_asset(asset):
                proxy_target = asset.get_proxy_target()
                # The asset is a proxy for the proxy_target original asset.
                self.debug("Stop proxying %s", proxy_target.props.id)
                proxy_target.set_proxy(None)
                if proxy_manager.is_scaled_proxy(asset) \
                        and not proxy_manager.is_asset_format_well_supported(proxy_target) \
                        and hq_proxy:
                    # The original asset is unsupported, and the user prefers
                    # to edit with HQ proxies instead of scaled proxies.
                    self.use_proxies_for_assets([proxy_target])
                self.remove_asset(asset)
                proxy_target.force_proxying = False
                if delete_proxy_file:
                    os.remove(Gst.uri_get_location(asset.props.id))
            else:
                # The asset is an original which is not being proxied.
                proxy_manager.cancel_job(asset)

    def regenerate_scaled_proxies(self):
        assets = self.list_assets(GES.Extractable)
        scaled_proxies = []
        scaled_proxy_targets = []

        for asset in assets:
            if self.app.proxy_manager.is_scaled_proxy(asset):
                scaled_proxies.append(asset)
                scaled_proxy_targets.append(asset.get_proxy_target())

        self.disable_proxies_for_assets(scaled_proxies, delete_proxy_file=True,
                                        hq_proxy=False)
        self.use_proxies_for_assets(scaled_proxy_targets, scaled=True)

    def _commit(self):
        """Logs the operation and commits.

        To be used as a replacement for the GES.Timeline.commit method, allowing
        to scenarialize the action in the scenarios.
        """
        self.app.write_action("commit")
        GES.Timeline.commit(self.ges_timeline)

    def create_timeline(self):
        """Loads the project's timeline."""
        try:
            # The project is loaded from the file in this call.
            self.ges_timeline = self.extract()
        except GLib.Error as e:
            self.warning("Failed to extract the timeline: %s", e)
            self.ges_timeline = None

        if self.ges_timeline is None:
            return False

        self.ges_timeline.commit = self._commit
        self.pipeline = Pipeline(self.app)
        if not self.pipeline.set_timeline(self.ges_timeline):
            self.warning("Failed to set the pipeline's timeline: %s", self.ges_timeline)
            return False

        if self.ges_timeline.get_marker_list("markers") is None:
            self.ges_timeline.set_marker_list("markers", GES.MarkerList.new())

        return True

    def update_restriction_caps(self):
        """Syncs the project settings from the render profile.

        The project settings reside in the restriction caps of the audio and
        video tracks of the timeline. They are updated to match the render
        profile stored as the first (and only) encoding profile of the project.
        """
        videocaps = Gst.Caps.new_empty_simple("video/x-raw")
        # Get the height/width without rendering settings applied
        width, height = self.get_video_width_and_height()
        videocaps.set_value("width", width)
        videocaps.set_value("height", height)
        videocaps.set_value("framerate", self.videorate)
        videocaps.set_value("pixel-aspect-ratio", Gst.Fraction(1, 1))

        audiocaps = Gst.Caps.new_empty_simple("audio/x-raw")
        audiocaps.set_value("rate", self.audiorate)
        audiocaps.set_value("channels", self.audiochannels)

        for track in self.ges_timeline.get_tracks():
            if isinstance(track, GES.VideoTrack):
                track.set_restriction_caps(videocaps)
            elif isinstance(track, GES.AudioTrack):
                track.set_restriction_caps(audiocaps)

        if self.app:
            self.app.write_action(
                "set-track-restriction-caps",
                caps=videocaps.to_string(),
                track_type=GES.TrackType.VIDEO.value_nicks[0])

            self.app.write_action(
                "set-track-restriction-caps",
                caps=audiocaps.to_string(),
                track_type=GES.TrackType.AUDIO.value_nicks[0])

        self.pipeline.commit_timeline()

    def add_uris(self, uris):
        """Adds assets asynchronously.

        Args:
            uris (List[str]): The URIs of the assets.
        """
        with self.app.action_log.started("assets-addition"):
            for uri in uris:
                if self.create_asset(quote_uri(uri), GES.UriClip):
                    # The asset was not already part of the project.
                    action = AssetAddedIntention(self, uri)
                    self.app.action_log.push(action)

    def assets_for_uris(self, uris):
        assets = []
        for uri in uris:
            asset = self.get_asset(uri, GES.UriClip)
            if not asset:
                return None
            assets.append(asset)
        return assets

    def list_sources(self):
        return self.list_assets(GES.UriClip)

    def get_project_id(self):
        project_id = self.get_string("pitivi::project-id")
        if not project_id:
            project_id = uuid.uuid4().hex
            self.set_string("pitivi::project-id", project_id)
            self.log("Assigned new project id %s", project_id)
        return project_id

    def release(self):
        res = 0

        if self.pipeline:
            self.pipeline.release()

        if self.runner:
            res = self.runner.printf()

        if self.runner:
            self.runner = None
            self.monitor = None

        self.pipeline = None
        self.ges_timeline = None

        return res

    def set_modification_state(self, state):
        if not self.loaded:
            return

        self._dirty = state
        if state:
            self.emit('project-changed')

    def has_unsaved_modifications(self):
        return self._dirty

    def get_dar(self):
        return Gst.Fraction(self.videowidth, self.videoheight)

    def get_video_width_and_height(self, render=False):
        """Returns the video width and height as a tuple.

        Args:
            render (bool): Whether to apply self.render_scale to the returned
                values.
        """
        if render:
            if not self._has_rendering_values:
                return (self.videowidth * self.render_scale / 100,
                        self.videoheight * self.render_scale / 100)
            else:
                return self.videowidth, self.videoheight

        if self._has_rendering_values:
            return (self.videowidth / self.render_scale * 100,
                    self.videoheight / self.render_scale * 100)

        return self.videowidth, self.videoheight

    def get_video_caps(self, render=False):
        """Gets the caps corresponding to the video settings.

        Returns:
            Gst.Caps: The video settings caps.
        """
        videowidth, videoheight = self.get_video_width_and_height(render=render)
        vstr = "width=%d,height=%d,pixel-aspect-ratio=1/1,framerate=%d/%d" % (
            videowidth, videoheight,
            self.videorate.num, self.videorate.denom)
        caps_str = "video/x-raw,%s" % (vstr)
        video_caps = Gst.caps_from_string(caps_str)
        return video_caps

    def get_audio_caps(self):
        """Gets the caps corresponding to the audio settings.

        Returns:
            Gst.Caps: The audio settings caps.
        """
        astr = "rate=%d,channels=%d" % (self.audiorate, self.audiochannels)
        caps_str = "audio/x-raw,%s" % (astr)
        audio_caps = Gst.caps_from_string(caps_str)
        return audio_caps

    def set_audio_properties(self, nbchanns=-1, rate=-1):
        """Sets the number of audio channels and the rate."""
        # pylint: disable=consider-using-in
        self.info("%d x %dHz %dbits", nbchanns, rate)
        if nbchanns != -1 and nbchanns != self.audiochannels:
            self.audiochannels = nbchanns
        if rate != -1 and rate != self.audiorate:
            self.audiorate = rate

    def set_encoders(self, muxer="", vencoder="", aencoder=""):
        """Sets the video and audio encoders and the muxer."""
        # pylint: disable=consider-using-in
        if muxer != "" and muxer != self.muxer:
            self.muxer = muxer
        if vencoder != "" and vencoder != self.vencoder:
            self.vencoder = vencoder
        if aencoder != "" and aencoder != self.aencoder:
            self.aencoder = aencoder

    @property
    def containersettings(self):
        cache_key = (self.container_profile, self.muxer)
        return self._containersettings_cache.setdefault(cache_key, {})

    @containersettings.setter
    def containersettings(self, value):
        cache_key = (self.container_profile, self.muxer)
        self._containersettings_cache[cache_key] = value

    @property
    def vcodecsettings(self):
        cache_key = (self.container_profile, self.vencoder)
        return self._vcodecsettings_cache.setdefault(cache_key, {})

    @vcodecsettings.setter
    def vcodecsettings(self, value):
        cache_key = (self.container_profile, self.vencoder)
        self._vcodecsettings_cache[cache_key] = value

    @property
    def acodecsettings(self):
        cache_key = (self.container_profile, self.aencoder)
        return self._acodecsettings_cache.setdefault(cache_key, {})

    @acodecsettings.setter
    def acodecsettings(self, value):
        cache_key = (self.container_profile, self.aencoder)
        self._acodecsettings_cache[cache_key] = value

    # ------------------------------------------ #
    # Private methods                            #
    # ------------------------------------------ #

    def _ensure_tracks(self):
        if self.ges_timeline is None:
            self.warning("Can't ensure tracks if no timeline set")
            return

        track_types = [track.get_property("track-type")
                       for track in self.ges_timeline.get_tracks()]

        if GES.TrackType.VIDEO not in track_types:
            self.ges_timeline.add_track(GES.VideoTrack.new())
        if GES.TrackType.AUDIO not in track_types:
            self.ges_timeline.add_track(GES.AudioTrack.new())

    def _ensure_layer(self):
        if self.ges_timeline is None:
            self.warning("Can't ensure tracks if no timeline set")
            return
        if not self.ges_timeline.get_layers():
            self.ges_timeline.append_layer()

    def _ensure_restrictions(self, profile, defaults, ref_restrictions=None,
                             prev_vals=None):
        """Make sure restriction values defined in @defaults are set on @profile.

        Attributes:
            profile (Gst.EncodingProfile): The Gst.EncodingProfile to use
            defaults (dict): A key value dict to use to set restriction defaults
            ref_restrictions (Gst.Caps): Reuse values from those caps instead
                                         of @values if available.

        """
        if isinstance(profile, GstPbutils.EncodingAudioProfile):
            facttype = Gst.ELEMENT_FACTORY_TYPE_AUDIO_ENCODER
        else:
            facttype = Gst.ELEMENT_FACTORY_TYPE_VIDEO_ENCODER

        ebin = Gst.ElementFactory.make("encodebin", None)
        ebin.props.profile = profile

        encoder = None
        for element in ebin.iterate_recurse():
            if element.get_factory().list_is_type(facttype):
                encoder = element
                break

        if not encoder:
            self.error("element '%s' not available for profile %s", profile.get_preset(), profile)
            return False

        encoder_sinkcaps = encoder.sinkpads[0].get_pad_template().get_caps().copy()
        self.debug("%s - Ensuring %s\n  defaults: %s\n  ref_restrictions: %s\n  prev_vals: %s)",
                   encoder, encoder_sinkcaps, defaults, ref_restrictions,
                   prev_vals)
        restriction = fixate_caps_with_default_values(encoder_sinkcaps,
                                                      ref_restrictions,
                                                      defaults,
                                                      prev_vals)
        assert restriction
        preset_name = encoder.get_factory().get_name()
        profile.set_restriction(restriction)
        profile.set_preset_name(preset_name)

        self.info("Fully set restriction: %s", profile.get_restriction().to_string())
        return True

    def _ensure_video_restrictions(self, profile=None):
        defaults = {
            "width": 720,
            "height": 576,
            "framerate": Gst.Fraction(25, 1),
            "pixel-aspect-ratio": Gst.Fraction(1, 1),
        }

        prev_vals = None
        if self.video_profile:
            prev_vals = self.video_profile.get_restriction().copy()

        if not profile:
            profile = self.video_profile
            ref_restrictions = Gst.Caps("video/x-raw")
        else:
            ref_restrictions = profile.get_restriction()

        return self._ensure_restrictions(profile, defaults, ref_restrictions, prev_vals)

    def _ensure_audio_restrictions(self, profile=None):
        ref_restrictions = None
        if not profile:
            profile = self.audio_profile
        else:
            ref_restrictions = profile.get_restriction()

        defaults = {"channels": Gst.IntRange(range(1, 2147483647)),
                    "rate": Gst.IntRange(range(8000, GLib.MAXINT))}
        prev_vals = None
        if self.audio_profile:
            prev_vals = self.audio_profile.get_restriction().copy()

        return self._ensure_restrictions(profile, defaults, ref_restrictions, prev_vals)

    def _maybe_init_settings_from_asset(self, asset):
        """Updates the project settings to match the specified asset.

        Args:
            asset (GES.UriClipAsset): The asset to copy the settings from.
        """
        if not (self._has_default_video_settings or
                self._has_default_audio_settings):
            # Both audio and video settings have been set already by the user.
            return
        if not isinstance(asset, GES.UriClipAsset):
            # We are only interested in actual files, not in titles, for example.
            return

        emit = False
        info = asset.get_info()
        video_streams = info.get_video_streams()
        if video_streams and self._has_default_video_settings:
            video = video_streams[0]
            if not video.is_image():
                videowidth = video.get_natural_width()
                videoheight = video.get_natural_height()
                videorate = self.videorate
                if video.get_framerate_num() > 0:
                    # The asset has a non-variable framerate.
                    videorate = Gst.Fraction(video.get_framerate_num(),
                                             video.get_framerate_denom())
                self.set_video_properties(videowidth, videoheight, videorate)
                self._has_default_video_settings = False
                emit = True
        audio_streams = info.get_audio_streams()
        if audio_streams and self._has_default_audio_settings:
            audio = audio_streams[0]
            if audio.get_sample_rate() >= DECENT_AUDIORATE:
                self.audiochannels = audio.get_channels()
                self.audiorate = audio.get_sample_rate()
                self._has_default_audio_settings = False
                emit = True
        if emit:
            self.emit("settings-set-from-imported-asset", asset)

    def get_element_factory_name(self, profile):
        """Finds a factory for an element compatible with the specified profile.

        Args:
            profile (GstPbutils.EncodingProfile): A muxer, video or audio
                profile.

        Returns:
            str: The name of the factory which can produce the required
            element, or None.
        """
        if profile.get_preset_name():
            return profile.get_preset_name()

        factories = Project.__factories_compatible_with_profile(profile)
        if not factories:
            return None

        preset = profile.get_preset()
        if not preset:
            # The element does not need to support a specific preset.
            # Return the compatible factory with the highest rank.
            return factories[0].get_name()
        else:
            # Make sure that if a #Gst.Preset is set we find an
            # element that can handle that preset.
            for factory in factories:
                elem = factory.create()
                if isinstance(elem, Gst.Preset):
                    if elem.load_preset(preset):
                        return factory.get_name()

            self.error("Could not find any element with preset %s", preset)
            return None

    @staticmethod
    def __factories_compatible_with_profile(profile):
        """Finds factories of the same type as the specified profile.

        Args:
            profile (GstPbutils.EncodingProfile): A muxer, video or audio
                profile.

        Returns:
            list[Gst.ElementFactory]: The element factories producing elements
                of the same type as the specified profile.
        """
        element_factories = []
        if isinstance(profile, GstPbutils.EncodingContainerProfile):
            element_factories = Encoders().muxers
        elif isinstance(profile, GstPbutils.EncodingVideoProfile):
            element_factories = Encoders().vencoders
        elif isinstance(profile, GstPbutils.EncodingAudioProfile):
            element_factories = Encoders().aencoders
        else:
            raise ValueError("Profile type not handled: %s" % profile)

        factories = Gst.ElementFactory.list_filter(element_factories,
                                                   Gst.Caps(profile.get_format()),
                                                   Gst.PadDirection.SRC,
                                                   False)

        factories.sort(key=lambda x: - x.get_rank())

        return factories
