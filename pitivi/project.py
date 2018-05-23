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
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.
"""Project related classes."""
import datetime
import os
import pwd
import shutil
import tarfile
import time
import uuid
from gettext import gettext as _
from hashlib import md5
from urllib.parse import unquote

from gi.repository import GdkPixbuf
from gi.repository import GES
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GstPbutils
from gi.repository import GstVideo
from gi.repository import Gtk

from pitivi.configure import get_ui_dir
from pitivi.medialibrary import AssetThumbnail
from pitivi.preset import AudioPresetManager
from pitivi.preset import VideoPresetManager
from pitivi.render import Encoders
from pitivi.settings import get_dir
from pitivi.settings import xdg_cache_home
from pitivi.timeline.previewers import Previewer
from pitivi.timeline.previewers import ThumbnailCache
from pitivi.undo.project import AssetAddedIntention
from pitivi.undo.project import AssetProxiedIntention
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import fixate_caps_with_default_values
from pitivi.utils.misc import isWritable
from pitivi.utils.misc import path_from_uri
from pitivi.utils.misc import quote_uri
from pitivi.utils.misc import scale_pixbuf
from pitivi.utils.misc import unicode_error_dialog
from pitivi.utils.pipeline import Pipeline
from pitivi.utils.ripple_update_group import RippleUpdateGroup
from pitivi.utils.ui import audio_channels
from pitivi.utils.ui import audio_rates
from pitivi.utils.ui import beautify_time_delta
from pitivi.utils.ui import frame_rates
from pitivi.utils.ui import get_combo_value
from pitivi.utils.ui import set_combo_value
from pitivi.utils.ui import SPACING
from pitivi.utils.validate import create_monitor
from pitivi.utils.validate import has_validate
from pitivi.utils.widgets import FractionWidget


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
DEFAULT_VIDEO_SETTINGS = "video/x-raw,width=1920,height=1080,framerate=(GstFraction)30/1"
DEFAULT_AUDIO_SETTINGS = "audio/x-raw,channels=2,rate=48000"

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

    def _tryUsingBackupFile(self, uri):
        backup_path = self._makeBackupURI(path_from_uri(uri))
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
                use_backup = self._restoreFromBackupDialog(time_diff)

                if use_backup:
                    uri = self._makeBackupURI(uri)
            self.debug('Loading project from backup: %s', uri)

        # For backup files and legacy formats, force the user to use "Save as"
        if use_backup or path.endswith(".xptv"):
            self.debug("Enforcing read-only mode")
            self.disable_save = True
        else:
            self.disable_save = False

        return uri

    def _isValidateScenario(self, uri):
        if uri.endswith(".scenario") and has_validate is True:
            # Let's just normally fail if we do not have Validate
            # installed on the system
            return True

        return False

    def _projectPipelineDiedCb(self, unused_pipeline):
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
        image = Gtk.Image.new_from_icon_name("dialog-error", Gtk.IconSize.DIALOG)
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
            self.app.gui.editor.saveProjectAs()
        elif response == 2:
            self.app.gui.editor.saveProject()

        self.app.shutdown()

    def load_project(self, uri):
        """Loads the specified URI as a project.

        If a backup file exists, asks if it should be loaded instead, and if so,
        forces the user to use "Save as" afterwards.
        """
        assert self.current_project is None

        is_validate_scenario = self._isValidateScenario(uri)
        if not is_validate_scenario:
            uri = self._tryUsingBackupFile(uri)
            scenario = None
        else:
            scenario = path_from_uri(uri)
            uri = None

        # Load the project:
        self.__start_loading_time = time.time()
        project = Project(self.app, uri=uri, scenario=scenario)
        self.emit("new-project-loading", project)

        project.connect_after("missing-uri", self._missingURICb)
        project.connect("loaded", self._projectLoadedCb)

        if not project.createTimeline():
            self.emit("new-project-failed", uri,
                      _('This might be due to a bug or an unsupported project file format. '
                        'If you were trying to add a media file to your project, '
                        'use the "Import" button instead.'))
            return None

        self.current_project = project
        self.emit("new-project-created", project)
        self.current_project.connect("project-changed", self._projectChangedCb)
        self.current_project.pipeline.connect("died", self._projectPipelineDiedCb)

        if is_validate_scenario:
            self.current_project.setupValidateScenario()

        return project

    def _restoreFromBackupDialog(self, time_diff):
        """Asks if we need to load the autosaved project backup.

        Args:
            time_diff (int): The difference, in seconds, between file mtimes.
        """
        dialog = Gtk.Dialog(title="", transient_for=None)
        dialog.add_buttons(_("Ignore backup"), Gtk.ResponseType.REJECT,
                           _("Restore from backup"), Gtk.ResponseType.YES)
        # Even though we set the title to an empty string when creating dialog,
        # seems we really have to do it once more so it doesn't show
        # "pitivi"...
        dialog.set_title("")
        dialog.set_icon_name("pitivi")
        dialog.set_transient_for(self.app.gui)
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
            return True
        else:
            return False

    def saveProject(self, uri=None, formatter_type=None, backup=False):
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
                uri = self._makeBackupURI(self.current_project.uri)
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

            if not isWritable(path_from_uri(uri)):
                # TODO: this will not be needed when GTK+ bug #601451 is fixed
                self.emit("save-project-failed", uri,
                          _("You do not have permissions to write to this folder."))
                return False

        try:
            # "overwrite" is always True: our GTK filechooser save dialogs are
            # set to always ask the user on our behalf about overwriting, so
            # if saveProject is actually called, that means overwriting is OK.
            saved = self.current_project.save(
                self.current_project.ges_timeline, uri,
                formatter_type, overwrite=True)
        except Exception as e:
            saved = False
            self.emit("save-project-failed", uri, e)

        if saved:
            if not backup:
                # Do not emit the signal when autosaving a backup file
                self.current_project.setModificationState(False)
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

    def exportProject(self, project, uri):
        """Exports a project and all its media files to a *.tar archive."""
        # Save the project to a temporary file.
        project_name = project.name if project.name else _("project")
        asset = GES.Formatter.get_default()
        project_extension = asset.get_meta(GES.META_FORMATTER_EXTENSION)
        tmp_name = "%s.%s" % (project_name, project_extension)

        directory = os.path.dirname(uri)
        tmp_uri = os.path.join(directory, tmp_name)
        try:
            # saveProject updates the project URI... so we better back it up:
            _old_uri = self.current_project.uri
            self.saveProject(tmp_uri)
            self.current_project.uri = _old_uri

            # create tar file
            with tarfile.open(path_from_uri(uri), mode="w") as tar:
                # top directory in tar-file
                top = "%s-export" % project_name
                # add temporary project file
                tar.add(path_from_uri(tmp_uri), os.path.join(top, tmp_name))

                # get common path
                sources = project.listSources()
                if self._allSourcesInHomedir(sources):
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
        except Exception as e:
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

        # Ensure we remove the temporary project file no matter what:
        try:
            os.remove(path_from_uri(tmp_uri))
        except OSError:
            pass

        return everything_ok

    def _allSourcesInHomedir(self, sources):
        """Checks if all sources are located in the user's home directory."""
        homedir = os.path.expanduser("~")

        for source in sources:
            if not path_from_uri(source.get_id()).startswith(homedir):
                return False

        return True

    def closeRunningProject(self):
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
            # We should never choke on silly stuff like disconnecting signals
            # that were already disconnected. It blocks the UI for nothing.
            # This can easily happen when a project load/creation failed.
            try:
                project.disconnect_by_function(self._projectChangedCb)
            except Exception:
                self.debug(
                    "Tried disconnecting signals, but they were not connected")
            try:
                project.pipeline.disconnect_by_function(self._projectPipelineDiedCb)
            except Exception:
                self.fixme("Handle better the errors and not get to this point")
            self._cleanBackup(project.uri)
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

        project.createTimeline()
        project._ensureTracks()
        project.update_restriction_caps()
        self.current_project = project
        self.emit("new-project-created", project)

        project.connect("project-changed", self._projectChangedCb)
        project.pipeline.connect("died", self._projectPipelineDiedCb)
        project.setModificationState(False)
        self.emit("new-project-loaded", self.current_project)
        project.loaded = True
        self.time_loaded = time.time()

        return project

    def revertToSavedProject(self):
        """Discards all unsaved changes and reloads the current open project."""
        if self.current_project.uri is None or not self.current_project.hasUnsavedModifications():
            return True
        if not self.emit("reverting-to-saved", self.current_project):
            return False

        uri = self.current_project.uri
        self.current_project.setModificationState(False)
        self.closeRunningProject()
        self.load_project(uri)

    def _projectChangedCb(self, project):
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
                self._backup_lock, self._saveBackupCb, project, uri)
        else:
            if self._backup_lock < 60:
                self._backup_lock += 5

    def _saveBackupCb(self, unused_project, unused_uri):
        if self._backup_lock > 10:
            self._backup_lock -= 5
            return True
        else:
            self.saveProject(backup=True)
            self._backup_lock = 0
        return False

    def _cleanBackup(self, uri):
        if uri is None:
            return
        path = path_from_uri(self._makeBackupURI(uri))
        if os.path.exists(path):
            os.remove(path)
            self.debug('Removed backup file: %s', path)

    def _makeBackupURI(self, uri):
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

    def _missingURICb(self, project, error, asset):
        new_uri = self.emit("missing-uri", project, error, asset)
        if not new_uri:
            project.at_least_one_asset_missing = True
        else:
            project.relocated_assets[asset.props.id] = new_uri
        project.setModificationState(True)
        return new_uri

    def _projectLoadedCb(self, project, unused_timeline):
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
        "rendering-settings-changed": (GObject.SignalFlags.RUN_LAST, None,
                                       (GObject.TYPE_PYOBJECT,)),
        "settings-set-from-imported-asset": (GObject.SignalFlags.RUN_LAST, None,
                                             (GES.Asset,)),
        "video-size-changed": (GObject.SignalFlags.RUN_LAST, None, ()),
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
        self.app.proxy_manager.connect("progress", self.__assetTranscodingProgressCb)
        self.app.proxy_manager.connect("error-preparing-asset",
                                       self.__proxyErrorCb)
        self.app.proxy_manager.connect("asset-preparing-cancelled",
                                       self.__assetTranscodingCancelledCb)
        self.app.proxy_manager.connect("proxy-ready",
                                       self.__proxyReadyCb)

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
        self.add_encoding_profile(self.container_profile)

        self.muxer = Encoders().default_muxer
        self.vencoder = Encoders().default_video_encoder
        self.aencoder = Encoders().default_audio_encoder
        self._ensureAudioRestrictions()
        self._ensureVideoRestrictions()
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

    def _scenarioDoneCb(self, scenario):
        if self.pipeline is not None:
            self.pipeline.setForcePositionListener(False)

    def setupValidateScenario(self):
        from gi.repository import GstValidate

        self.info("Setting up validate scenario")
        self.runner = GstValidate.Runner.new()
        create_monitor(self.runner, self.app.gui)
        self.monitor = GstValidate.Monitor.factory_create(
            self.pipeline, self.runner, None)
        self._scenario = GstValidate.Scenario.factory_create(
            self.runner, self.pipeline, self.scenario)
        self.pipeline.setForcePositionListener(True)
        self._scenario.connect("done", self._scenarioDoneCb)
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
        self.setModificationState(True)

    @property
    def scaled_proxy_width(self):
        return self.get_meta("scaled_proxy_width") or self.app.settings.default_scaled_proxy_width

    @scaled_proxy_width.setter
    def scaled_proxy_width(self, scaled_proxy_width):
        if scaled_proxy_width == self.get_meta("scaled_proxy_width"):
            return
        self.set_meta("scaled_proxy_width", scaled_proxy_width)
        self.setModificationState(True)

    def has_scaled_proxy_size(self):
        """Returns whether the proxy size has been set."""
        return bool(self.get_meta("scaled_proxy_width") and self.get_meta("scaled_proxy_height"))

    @staticmethod
    def get_thumb_path(uri, resolution):
        """Returns path of thumbnail of specified resolution in the cache."""
        thumb_hash = md5(quote_uri(uri).encode()).hexdigest()
        thumbs_cache_dir = get_dir(os.path.join(xdg_cache_home(),
                                   "project_thumbs", resolution))
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

        assets = self.listSources()
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
        self._ensureAudioRestrictions()
        self._ensureVideoRestrictions()

        video_restrictions = self.video_profile.get_restriction().copy_nth(0)

        if self._has_rendering_values != rendering:
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
        res = Project._set_restriction(self.video_profile, name, value)
        if res:
            self.emit("video-size-changed")
            self._has_default_video_settings = False
            self.update_restriction_caps()
        return res

    def _set_audio_restriction(self, name, value):
        res = Project._set_restriction(self.audio_profile, name, value)
        if res:
            self._has_default_audio_settings = False
            self.update_restriction_caps()
        return res

    @property
    def videowidth(self):
        return self.video_profile.get_restriction()[0]["width"]

    @videowidth.setter
    def videowidth(self, value):
        if self._set_video_restriction("width", int(value)):
            self._emit_change("width")

    @property
    def videoheight(self):
        return self.video_profile.get_restriction()[0]["height"]

    @videoheight.setter
    def videoheight(self, value):
        if self._set_video_restriction("height", int(value)):
            self._emit_change("height")

    @property
    def videorate(self):
        return self.video_profile.get_restriction()[0]["framerate"]

    @videorate.setter
    def videorate(self, value):
        if self._set_video_restriction("framerate", value):
            self._emit_change("videorate")

    @property
    def audiochannels(self):
        return self.audio_profile.get_restriction()[0]["channels"]

    @audiochannels.setter
    def audiochannels(self, value):
        if self._set_audio_restriction("channels", int(value)):
            self._emit_change("channels")

    @property
    def audiorate(self):
        try:
            return int(self.audio_profile.get_restriction()[0]["rate"])
        except TypeError:
            return None

    @audiorate.setter
    def audiorate(self, value):
        if self._set_audio_restriction("rate", int(value)):
            self._emit_change("rate")

    @property
    def aencoder(self):
        return self.audio_profile.get_preset_name()

    @aencoder.setter
    def aencoder(self, value):
        if self.audio_profile.get_preset_name() != value and value:
            caps = self._get_caps_from_feature(value)
            if caps:
                self.audio_profile.set_format(caps)
            self.audio_profile.set_preset_name(value)
            # Gst.Preset can be set exclusively through EncodingTagets for now.
            self.audio_profile.set_preset(None)
            self._emit_change("aencoder")

    @property
    def vencoder(self):
        return self.video_profile.get_preset_name()

    @vencoder.setter
    def vencoder(self, value):
        if self.video_profile.get_preset_name() != value and value:
            caps = self._get_caps_from_feature(value)
            if caps:
                self.video_profile.set_format(caps)
            self.video_profile.set_preset_name(value)
            # Gst.Preset can be set exclusively through EncodingTagets for now.
            self.video_profile.set_preset(None)
            self._emit_change("vencoder")

    @property
    def muxer(self):
        return self.container_profile.get_preset_name()

    @muxer.setter
    def muxer(self, value):
        if self.container_profile.get_preset_name() != value and value:
            caps = self._get_caps_from_feature(value)
            if caps:
                self.container_profile.set_format(caps)
            self.container_profile.set_preset_name(value)
            self._emit_change("muxer")

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

    # ------------------------------#
    # Proxy creation implementation #
    # ------------------------------#
    def __assetTranscodingProgressCb(self, unused_proxy_manager, asset,
                                     creation_progress, estimated_time):
        self.__updateAssetLoadingProgress(estimated_time)

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
                proxy_uri = self.app.proxy_manager.getProxyUri(asset)
                scaled_proxy_uri = self.app.proxy_manager.getProxyUri(asset, scaled=True)

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
            return

        asset_loading_progress = 0
        all_ready = True
        for asset in self.loading_assets:
            asset_weight = asset.get_duration() / total_import_duration
            asset_loading_progress += asset_weight * asset.creation_progress

            if asset.creation_progress < 100:
                all_ready = False
            elif not asset.ready:
                self.setModificationState(True)
                asset.ready = True

        if all_ready:
            asset_loading_progress = 100

        return asset_loading_progress

    def __updateAssetLoadingProgress(self, estimated_time=0):
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

    def __assetTranscodingCancelledCb(self, unused_proxy_manager, asset):
        self.__setProxy(asset, None)
        self.__updateAssetLoadingProgress()

    def __proxyErrorCb(self, unused_proxy_manager, asset, proxy, error):
        if asset is None:
            asset_id = self.app.proxy_manager.getTargetUri(proxy)
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
        self.__updateAssetLoadingProgress()

    def __proxyReadyCb(self, unused_proxy_manager, asset, proxy):
        if proxy and proxy.props.id in self.__deleted_proxy_files:
            self.info("Recreated proxy is now ready, stop having"
                      " its target as a proxy.")
            proxy.unproxy(asset)

        self.__setProxy(asset, proxy)

    def __setProxy(self, asset, proxy):
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

        self.__updateAssetLoadingProgress()

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
        self.__updateAssetLoadingProgress()

    def do_missing_uri(self, error, asset):
        if self.app.proxy_manager.is_proxy_asset(asset):
            self.debug("Missing proxy file: %s", asset.props.id)
            target_uri = self.app.proxy_manager.getTargetUri(asset)

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
        self._maybeInitSettingsFromAsset(asset)
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
            self.__updateAssetLoadingProgress()

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
        self.__updateAssetLoadingProgress()

    def do_loaded(self, unused_timeline):
        """Handles `GES.Project::loaded` emitted by self."""
        if not self.ges_timeline:
            return

        self._ensureTracks()
        self.ges_timeline.props.auto_transition = True
        self._ensureLayer()

        if self.uri:
            self.loading_assets = set([asset for asset in self.loading_assets if
                                       self.app.proxy_manager.is_asset_queued(asset)])

            if self.loading_assets:
                self.debug("The following assets are still being transcoded: %s."
                           " (They must be proxied assets with missing/deleted"
                           " proxy files).", self.loading_assets)
            self.__updateAssetLoadingProgress()

        if self.scenario is not None:
            return

        profiles = self.list_encoding_profiles()
        if profiles:
            # The project just loaded, check the new
            # encoding profile and make use of it now.
            self.set_container_profile(profiles[0], reset_all=True)
            self._load_encoder_settings(profiles)

    def set_container_profile(self, container_profile, reset_all=False):
        """Sets @container_profile as new profile if usable.

        Attributes:
            profile (Gst.EncodingProfile): The Gst.EncodingContainerProfile to use
            reset_all (bool): Do not use restrictions from the previously set profile
        """
        if container_profile == self.container_profile:
            return False

        muxer = self._getElementFactoryName(
            Encoders().muxers, container_profile)
        if muxer is None:
            muxer = Encoders().default_muxer
        container_profile.set_preset_name(muxer)

        video_profile = audio_profile = vencoder = aencoder = None
        for profile in container_profile.get_profiles():
            if isinstance(profile, GstPbutils.EncodingVideoProfile):
                video_profile = profile
                if profile.get_restriction() is None:
                    profile.set_restriction(Gst.Caps("video/x-raw"))

                self._ensureVideoRestrictions(profile)
                vencoder = self._getElementFactoryName(Encoders().vencoders, profile)
                if vencoder:
                    profile.set_preset_name(vencoder)
            elif isinstance(profile, GstPbutils.EncodingAudioProfile):
                audio_profile = profile
                if profile.get_restriction() is None:
                    profile.set_restriction(Gst.Caps("audio/x-raw"))

                self._ensureAudioRestrictions(profile)
                aencoder = self._getElementFactoryName(Encoders().aencoders, profile)
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

    def _load_encoder_settings(self, profiles):
        for container_profile in profiles:
            if not isinstance(container_profile, GstPbutils.EncodingContainerProfile):
                self.warning("%s is not an EncodingContainerProfile", container_profile)
                continue

            for profile in container_profile.get_profiles():
                preset = profile.get_preset()
                if not preset:
                    continue

                encoder_factory_name = profile.get_preset_name()
                encoder = Gst.ElementFactory.make(encoder_factory_name, None)
                if not isinstance(encoder, Gst.Preset):
                    self.warning("Element %s does not implement Gst.Preset. Cannot load"
                                 "its rendering settings", encoder)
                    continue

                if profile.get_type_nick() == "video":
                    cache = self._vcodecsettings_cache
                elif profile.get_type_nick() == "audio":
                    cache = self._acodecsettings_cache
                else:
                    self.warning("Unrecognized profile type for profile %s", profile)
                    continue
                cache_key = (container_profile, encoder_factory_name)

                if not encoder.load_preset(preset):
                    self.warning("No preset named %s for encoder %s", preset, encoder)
                    continue

                cache[cache_key] = {prop.name: encoder.get_property(prop.name)
                                    for prop in GObject.list_properties(encoder)
                                    if prop.name not in IGNORED_PROPS and prop.flags & GObject.ParamFlags.WRITABLE}

    # ------------------------------------------ #
    # Our API                                    #
    # ------------------------------------------ #

    def finalize(self):
        """Disconnects all signals and everything.

        Makes sure the project won't be doing anything after the call.
        """
        if self._scenario:
            self._scenario.disconnect_by_func(self._scenarioDoneCb)
        self.app.proxy_manager.disconnect_by_func(self.__assetTranscodingProgressCb)
        self.app.proxy_manager.disconnect_by_func(self.__proxyErrorCb)
        self.app.proxy_manager.disconnect_by_func(self.__assetTranscodingCancelledCb)
        self.app.proxy_manager.disconnect_by_func(self.__proxyReadyCb)

    def save(self, ges_timeline, uri, formatter_asset, overwrite):
        for container_profile in self.list_encoding_profiles():
            if not isinstance(container_profile, GstPbutils.EncodingContainerProfile):
                self.warning("%s is not an EncodingContainerProfile", container_profile)
                continue

            for profile in container_profile.get_profiles():
                encoder_factory_name = profile.get_preset_name()
                encoder = Gst.ElementFactory.make(encoder_factory_name, None)
                if not isinstance(encoder, Gst.Preset):
                    self.warning("Element %s does not implement Gst.Preset. Cannot save"
                                 "its rendering settings", encoder)
                    continue

                if profile.get_type_nick() == "video":
                    cache = self._vcodecsettings_cache
                elif profile.get_type_nick() == "audio":
                    cache = self._acodecsettings_cache
                else:
                    self.warning("Unrecognized profile type for profile %s", profile)
                    continue
                cache_key = (container_profile, encoder_factory_name)
                if cache_key not in cache:
                    continue

                # Save the encoder settings in a Gst.Preset so they are
                # available in GES.Project.save() for serialization
                settings = cache[cache_key]
                preset = "encoder_settings_%s" % uuid.uuid4().hex
                profile.set_preset(preset)

                for prop, value in settings.items():
                    encoder.set_property(prop, value)
                res = encoder.save_preset(preset)
                assert res

        return GES.Project.save(self, ges_timeline, uri, formatter_asset, overwrite)

    def use_proxies_for_assets(self, assets, scaled=False):
        proxy_manager = self.app.proxy_manager
        originals = []
        for asset in assets:
            if scaled:
                is_proxied = proxy_manager.is_scaled_proxy(asset) and \
                    not proxy_manager.asset_matches_target_res(asset)
            else:
                is_proxied = proxy_manager.is_hq_proxy(asset)
            if not is_proxied:
                target = asset.get_proxy_target()
                uri = proxy_manager.getProxyUri(asset, scaled=scaled)
                if target and target.props.id == uri:
                    self.info("Missing proxy needs to be recreated after cancelling"
                              " its recreation")
                    target.unproxy(asset)

                if not asset.is_image():
                    # The asset is not a proxy and not an image.
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
                        and not proxy_manager.isAssetFormatWellSupported(proxy_target) \
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

    def createTimeline(self):
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
        # Get the height/width without rendering settings applied
        width, height = self.getVideoWidthAndHeight()
        videocaps = Gst.Caps.new_empty_simple("video/x-raw")

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

    def addUris(self, uris):
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

    def assetsForUris(self, uris):
        assets = []
        for uri in uris:
            asset = self.get_asset(uri, GES.UriClip)
            if not asset:
                return None
            assets.append(asset)
        return assets

    def listSources(self):
        return self.list_assets(GES.UriClip)

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

    def setModificationState(self, state):
        if not self.loaded:
            return

        self._dirty = state
        if state:
            self.emit('project-changed')

    def hasUnsavedModifications(self):
        return self._dirty

    def getDAR(self):
        return Gst.Fraction(self.videowidth, self.videoheight)

    def getVideoWidthAndHeight(self, render=False):
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

    def getVideoCaps(self, render=False):
        """Gets the caps corresponding to the video settings.

        Returns:
            Gst.Caps: The video settings caps.
        """
        videowidth, videoheight = self.getVideoWidthAndHeight(render=render)
        vstr = "width=%d,height=%d,pixel-aspect-ratio=1/1,framerate=%d/%d" % (
            videowidth, videoheight,
            self.videorate.num, self.videorate.denom)
        caps_str = "video/x-raw,%s" % (vstr)
        video_caps = Gst.caps_from_string(caps_str)
        return video_caps

    def getAudioCaps(self):
        """Gets the caps corresponding to the audio settings.

        Returns:
            Gst.Caps: The audio settings caps.
        """
        astr = "rate=%d,channels=%d" % (self.audiorate, self.audiochannels)
        caps_str = "audio/x-raw,%s" % (astr)
        audio_caps = Gst.caps_from_string(caps_str)
        return audio_caps

    def setAudioProperties(self, nbchanns=-1, rate=-1):
        """Sets the number of audio channels and the rate."""
        self.info("%d x %dHz %dbits", nbchanns, rate)
        if not nbchanns == -1 and not nbchanns == self.audiochannels:
            self.audiochannels = nbchanns
        if not rate == -1 and not rate == self.audiorate:
            self.audiorate = rate

    def setEncoders(self, muxer="", vencoder="", aencoder=""):
        """Sets the video and audio encoders and the muxer."""
        if not muxer == "" and not muxer == self.muxer:
            self.muxer = muxer
        if not vencoder == "" and not vencoder == self.vencoder:
            self.vencoder = vencoder
        if not aencoder == "" and not aencoder == self.aencoder:
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

    def _ensureTracks(self):
        if self.ges_timeline is None:
            self.warning("Can't ensure tracks if no timeline set")
            return

        track_types = [track.get_property("track-type")
                       for track in self.ges_timeline.get_tracks()]

        if GES.TrackType.VIDEO not in track_types:
            self.ges_timeline.add_track(GES.VideoTrack.new())
        if GES.TrackType.AUDIO not in track_types:
            self.ges_timeline.add_track(GES.AudioTrack.new())

    def _ensureLayer(self):
        if self.ges_timeline is None:
            self.warning("Can't ensure tracks if no timeline set")
            return
        if not self.ges_timeline.get_layers():
            self.ges_timeline.append_layer()

    def _ensureRestrictions(self, profile, defaults, ref_restrictions=None,
                            prev_vals=None):
        """Make sure restriction values defined in @defaults are set on @profile.

        Attributes:
            profile (Gst.EncodingProfile): The Gst.EncodingProfile to use
            defaults (dict): A key value dict to use to set restriction defaults
            ref_restrictions (Gst.Caps): Reuse values from those caps instead
                                         of @values if available.

        """
        encoder = None
        if isinstance(profile, GstPbutils.EncodingAudioProfile):
            facttype = Gst.ELEMENT_FACTORY_TYPE_AUDIO_ENCODER
        else:
            facttype = Gst.ELEMENT_FACTORY_TYPE_VIDEO_ENCODER

        ebin = Gst.ElementFactory.make('encodebin', None)
        ebin.props.profile = profile
        for element in ebin.iterate_recurse():
            if element.get_factory().list_is_type(facttype):
                encoder = element
                break

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

    def _ensureVideoRestrictions(self, profile=None):
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

        self._ensureRestrictions(profile, defaults, ref_restrictions,
                                 prev_vals)

    def _ensureAudioRestrictions(self, profile=None):
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

        return self._ensureRestrictions(profile, defaults, ref_restrictions,
                                        prev_vals)

    def _maybeInitSettingsFromAsset(self, asset):
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
                self.videowidth = video.get_natural_width()
                self.videoheight = video.get_natural_height()
                if video.get_framerate_num() > 0:
                    # The asset has a non-variable framerate.
                    self.videorate = Gst.Fraction(video.get_framerate_num(),
                                                  video.get_framerate_denom())
                self._has_default_video_settings = False
                emit = True
        audio_streams = info.get_audio_streams()
        if audio_streams and self._has_default_audio_settings:
            audio = audio_streams[0]
            self.audiochannels = audio.get_channels()
            self.audiorate = audio.get_sample_rate()
            self._has_default_audio_settings = False
            emit = True
        if emit:
            self.emit("settings-set-from-imported-asset", asset)

    def _emit_change(self, key):
        self.emit("rendering-settings-changed", key)
        self.setModificationState(True)

    def _getElementFactoryName(self, elements, profile):
        if profile.get_preset_name():
            return profile.get_preset_name()

        factories = Gst.ElementFactory.list_filter(elements,
                                                   Gst.Caps(
                                                       profile.get_format()),
                                                   Gst.PadDirection.SRC,
                                                   False)
        if factories:
            factories.sort(key=lambda x: - x.get_rank())
            preset = profile.get_preset()
            # Make sure that if a #Gst.Preset is set we find an
            # element that can handle that preset.
            if preset:
                for factory in factories:
                    elem = factory.create()
                    if isinstance(elem, Gst.Preset):
                        if elem.load_preset(preset):
                            return factory.get_name()
                self.error("Could not find any element with preset %s",
                           preset)
                return None

            return factories[0].get_name()
        return None


# ---------------------- UI classes ----------------------------------------- #

class ProjectSettingsDialog(object):
    """Manager of a dialog for viewing and changing the project settings.

    Attributes:
        project (Project): The project who's settings are displayed.
        app (Pitivi): The current app.
    """

    def __init__(self, parent_window, project, app):
        self.app = app
        self.project = project
        self.audio_presets = AudioPresetManager(app.system)
        self.video_presets = VideoPresetManager(app.system)
        self._createUi()
        self.window.set_transient_for(parent_window)
        self._setupUiConstraints()
        self.updateUI()

    def __del__(self):
        self.video_presets.disconnect_by_func(self.__videoPresetLoadedCb)

    def _createUi(self):
        """Initializes the static parts of the UI."""
        self.builder = Gtk.Builder()
        self.builder.add_from_file(
            os.path.join(get_ui_dir(), "projectsettings.ui"))
        self.builder.connect_signals(self)

        getObj = self.builder.get_object
        self.window = getObj("project-settings-dialog")
        self.frame_rate_combo = getObj("frame_rate_combo")
        self.channels_combo = getObj("channels_combo")
        self.sample_rate_combo = getObj("sample_rate_combo")
        self.year_spinbutton = getObj("year_spinbutton")
        self.author_entry = getObj("author_entry")
        self.width_spinbutton = getObj("width_spinbutton")
        self.height_spinbutton = getObj("height_spinbutton")
        self.audio_presets_combo = getObj("audio_presets_combo")
        self.video_presets_combo = getObj("video_presets_combo")
        self.constrain_sar_button = getObj("constrain_sar_button")
        self.select_dar_radiobutton = getObj("select_dar_radiobutton")
        self.year_spinbutton = getObj("year_spinbutton")

        self.video_preset_menubutton = getObj("video_preset_menubutton")
        self.video_presets.setupUi(self.video_presets_combo,
                                   self.video_preset_menubutton)
        self.video_presets.connect("preset-loaded", self.__videoPresetLoadedCb)
        self.audio_preset_menubutton = getObj("audio_preset_menubutton")
        self.audio_presets.setupUi(self.audio_presets_combo,
                                   self.audio_preset_menubutton)

        self.scaled_proxy_width_spin = getObj("scaled_proxy_width")
        self.scaled_proxy_height_spin = getObj("scaled_proxy_height")
        self.proxy_res_linked_check = getObj("proxy_res_linked")

    def _setupUiConstraints(self):
        """Creates the dynamic widgets and connects other widgets."""

        # Add custom framerate fraction widget.
        frame_rate_box = self.builder.get_object("frame_rate_box")
        self.frame_rate_fraction_widget = FractionWidget()
        frame_rate_box.pack_end(self.frame_rate_fraction_widget, True, True, 0)
        self.frame_rate_fraction_widget.show()

        # Populate comboboxes.
        self.frame_rate_combo.set_model(frame_rates)
        self.channels_combo.set_model(audio_channels)
        self.sample_rate_combo.set_model(audio_rates)

        # Behavior.
        self.wg = RippleUpdateGroup()
        self.wg.addVertex(self.frame_rate_combo,
                          signal="changed",
                          update_func=self._updateCombo,
                          update_func_args=(self.frame_rate_fraction_widget,))
        self.wg.addVertex(self.frame_rate_fraction_widget,
                          signal="value-changed",
                          update_func=self._updateFraction,
                          update_func_args=(self.frame_rate_combo,))
        self.wg.addVertex(self.width_spinbutton, signal="value-changed")
        self.wg.addVertex(self.height_spinbutton, signal="value-changed")
        self.wg.addVertex(self.audio_preset_menubutton,
                          update_func=self._updatePresetMenuButton,
                          update_func_args=(self.audio_presets,))
        self.wg.addVertex(self.video_preset_menubutton,
                          update_func=self._updatePresetMenuButton,
                          update_func_args=(self.video_presets,))
        self.wg.addVertex(self.channels_combo, signal="changed")
        self.wg.addVertex(self.sample_rate_combo, signal="changed")
        self.wg.addVertex(self.scaled_proxy_width_spin, signal="value-changed")
        self.wg.addVertex(self.scaled_proxy_height_spin, signal="value-changed")

        # Constrain width and height IFF the Link checkbox is checked.
        # Video
        self.wg.addEdge(self.width_spinbutton, self.height_spinbutton,
                        predicate=self.widthHeightLinked,
                        edge_func=self.updateHeight)
        self.wg.addEdge(self.height_spinbutton, self.width_spinbutton,
                        predicate=self.widthHeightLinked,
                        edge_func=self.updateWidth)
        # Proxy
        self.wg.addEdge(self.scaled_proxy_width_spin,
                        self.scaled_proxy_height_spin,
                        predicate=self.proxy_res_linked,
                        edge_func=self.update_scaled_proxy_height)
        self.wg.addEdge(self.scaled_proxy_height_spin,
                        self.scaled_proxy_width_spin,
                        predicate=self.proxy_res_linked,
                        edge_func=self.update_scaled_proxy_width)

        # Keep the framerate combo and fraction widgets in sync.
        self.wg.addBiEdge(
            self.frame_rate_combo, self.frame_rate_fraction_widget)

        # Presets.
        self.audio_presets.loadAll()
        self.video_presets.loadAll()

        # Bind the widgets in the Video tab to the Video Presets Manager.
        self.bindSpinbutton(self.video_presets, "width", self.width_spinbutton)
        self.bindSpinbutton(
            self.video_presets, "height", self.height_spinbutton)
        self.bindFractionWidget(
            self.video_presets, "frame-rate", self.frame_rate_fraction_widget)

        # Bind the widgets in the Audio tab to the Audio Presets Manager.
        self.bindCombo(self.audio_presets, "channels", self.channels_combo)
        self.bindCombo(
            self.audio_presets, "sample-rate", self.sample_rate_combo)

        self.wg.addEdge(
            self.frame_rate_fraction_widget, self.video_preset_menubutton)
        self.wg.addEdge(self.width_spinbutton, self.video_preset_menubutton)
        self.wg.addEdge(self.height_spinbutton, self.video_preset_menubutton)

        self.wg.addEdge(self.channels_combo, self.audio_preset_menubutton)
        self.wg.addEdge(self.sample_rate_combo, self.audio_preset_menubutton)

    def bindFractionWidget(self, mgr, name, widget):
        mgr.bindWidget(name, widget.setWidgetValue, widget.getWidgetValue)

    def bindCombo(self, mgr, name, widget):
        mgr.bindWidget(name,
                       lambda x: set_combo_value(widget, x),
                       lambda: get_combo_value(widget))

    def bindSpinbutton(self, mgr, name, widget):
        mgr.bindWidget(name,
                       lambda x: widget.set_value(float(x)),
                       lambda: int(widget.get_value()))

    def widthHeightLinked(self):
        return self.constrain_sar_button.props.active and not self.video_presets.ignore_update_requests

    def proxy_res_linked(self):
        return self.proxy_res_linked_check.props.active

    def _updateFraction(self, unused, fraction, combo):
        fraction.setWidgetValue(get_combo_value(combo))

    def _updateCombo(self, unused, combo, fraction):
        set_combo_value(combo, fraction.getWidgetValue())

    def __videoPresetLoadedCb(self, unused_mgr):
        self._updateSar()

    def getSAR(self):
        width = int(self.width_spinbutton.get_value())
        height = int(self.height_spinbutton.get_value())
        return Gst.Fraction(width, height)

    def _constrainSarButtonToggledCb(self, unused_button):
        self._updateSar()

    def _updateSar(self):
        self.sar = self.getSAR()

    def _updatePresetMenuButton(self, unused_source, unused_target, mgr):
        mgr.updateMenuActions()

    def updateWidth(self):
        height = int(self.height_spinbutton.get_value())
        fraction = height * self.sar
        width = int(fraction.num / fraction.denom)
        self.width_spinbutton.set_value(width)

    def updateHeight(self):
        width = int(self.width_spinbutton.get_value())
        fraction = width / self.sar
        height = int(fraction.num / fraction.denom)
        self.height_spinbutton.set_value(height)

    def _proxy_res_linked_toggle_cb(self, unused_button):
        width = int(self.scaled_proxy_width_spin.get_value())
        height = int(self.scaled_proxy_height_spin.get_value())
        self.proxy_aspect_ratio = Gst.Fraction(width, height)

    def update_scaled_proxy_width(self):
        height = int(self.scaled_proxy_height_spin.get_value())
        fraction = height * self.proxy_aspect_ratio
        width = int(fraction.num / fraction.denom)
        self.scaled_proxy_width_spin.set_value(width)

    def update_scaled_proxy_height(self):
        width = int(self.scaled_proxy_width_spin.get_value())
        fraction = width / self.proxy_aspect_ratio
        height = int(fraction.num / fraction.denom)
        self.scaled_proxy_height_spin.set_value(height)

    def updateUI(self):
        # Video
        self.width_spinbutton.set_value(self.project.videowidth)
        self.height_spinbutton.set_value(self.project.videoheight)
        self.frame_rate_fraction_widget.setWidgetValue(self.project.videorate)

        matching_video_preset = self.video_presets.matchingPreset(self.project)
        if matching_video_preset:
            self.video_presets_combo.set_active_id(matching_video_preset)

        # Audio
        set_combo_value(self.channels_combo, self.project.audiochannels)
        set_combo_value(self.sample_rate_combo, self.project.audiorate)

        matching_audio_preset = self.audio_presets.matchingPreset(self.project)
        if matching_audio_preset:
            self.audio_presets_combo.set_active_id(matching_audio_preset)

        # Metadata
        self.author_entry.set_text(self.project.author)
        if self.project.year:
            year = int(self.project.year)
        else:
            year = datetime.datetime.now().year
        self.year_spinbutton.get_adjustment().set_value(year)

        self.scaled_proxy_width_spin.set_value(self.project.scaled_proxy_width)
        self.scaled_proxy_height_spin.set_value(self.project.scaled_proxy_height)

    def updateProject(self):
        with self.app.action_log.started("change project settings",
                                         toplevel=True):
            self.project.author = self.author_entry.get_text()
            self.project.year = str(self.year_spinbutton.get_value_as_int())

            self.project.videowidth = int(self.width_spinbutton.get_value())
            self.project.videoheight = int(self.height_spinbutton.get_value())
            self.project.videorate = self.frame_rate_fraction_widget.getWidgetValue()

            self.project.audiochannels = get_combo_value(self.channels_combo)
            self.project.audiorate = get_combo_value(self.sample_rate_combo)

            proxy_width = int(self.scaled_proxy_width_spin.get_value())
            proxy_height = int(self.scaled_proxy_height_spin.get_value())
            # Update scaled proxy meta-data and trigger proxy regen
            if not self.project.has_scaled_proxy_size() or \
                    self.project.scaled_proxy_width != proxy_width or \
                    self.project.scaled_proxy_height != proxy_height:
                self.project.scaled_proxy_width = proxy_width
                self.project.scaled_proxy_height = proxy_height

                self.project.regenerate_scaled_proxies()

    def _responseCb(self, unused_widget, response):
        """Handles the dialog being closed."""
        if response == Gtk.ResponseType.OK:
            self.updateProject()
        self.window.destroy()
