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
import tarfile
import time
from gettext import gettext as _

from gi.repository import GES
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GstPbutils
from gi.repository import Gtk

from pitivi.configure import get_ui_dir
from pitivi.preset import AudioPresetManager
from pitivi.preset import VideoPresetManager
from pitivi.render import Encoders
from pitivi.utils.loggable import Loggable
from pitivi.utils.misc import isWritable
from pitivi.utils.misc import path_from_uri
from pitivi.utils.misc import quote_uri
from pitivi.utils.misc import unicode_error_dialog
from pitivi.utils.pipeline import Pipeline
from pitivi.utils.pipeline import PipelineError
from pitivi.utils.ripple_update_group import RippleUpdateGroup
from pitivi.utils.ui import audio_channels
from pitivi.utils.ui import audio_rates
from pitivi.utils.ui import beautify_time_delta
from pitivi.utils.ui import display_aspect_ratios
from pitivi.utils.ui import frame_rates
from pitivi.utils.ui import get_combo_value
from pitivi.utils.ui import pixel_aspect_ratios
from pitivi.utils.ui import set_combo_value
from pitivi.utils.ui import SPACING
from pitivi.utils.validate import create_monitor
from pitivi.utils.validate import has_validate
from pitivi.utils.widgets import FractionWidget


DEFAULT_NAME = _("New Project")


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
        "new-project-loading": (GObject.SIGNAL_RUN_LAST, None, (object,)),
        "new-project-created": (GObject.SIGNAL_RUN_LAST, None, (object,)),
        "new-project-failed": (GObject.SIGNAL_RUN_LAST, None, (str, str)),
        "new-project-loaded": (GObject.SIGNAL_RUN_LAST, None, (object,)),
        "save-project-failed": (GObject.SIGNAL_RUN_LAST, None, (str, object)),
        "project-saved": (GObject.SIGNAL_RUN_LAST, None, (object, str)),
        "closing-project": (GObject.SIGNAL_RUN_LAST, bool, (object,)),
        "project-closed": (GObject.SIGNAL_RUN_LAST, None, (object,)),
        "missing-uri": (GObject.SIGNAL_RUN_LAST, str, (object, str, object)),
        "reverting-to-saved": (GObject.SIGNAL_RUN_LAST, bool, (object,)),
    }

    def __init__(self, app):
        GObject.Object.__init__(self)
        Loggable.__init__(self)
        self.app = app
        self.current_project = None
        self.disable_save = False
        self._backup_lock = 0
        self.exitcode = 0

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
                    "<a href=\"http://wiki.pitivi.org/wiki/Bug_reporting\">"
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
            self.app.gui.saveProjectAsDialog()
        elif response == 2:
            self.app.gui.saveProject()

        self.app.shutdown()

    def loadProject(self, uri):
        """Loads the specified URI as a project.

        If a backup file exists, asks if it should be loaded instead, and if so,
        forces the user to use "Save as" afterwards.
        """
        if self.current_project is not None and not self.closeRunningProject():
            return False

        is_validate_scenario = self._isValidateScenario(uri)
        if not is_validate_scenario:
            uri = self._tryUsingBackupFile(uri)
            scenario = None
        else:
            scenario = path_from_uri(uri)
            uri = None

        # Load the project:
        project = Project(self.app, uri=uri, scenario=scenario)
        self.emit("new-project-loading", project)

        project.connect_after("missing-uri", self._missingURICb)
        project.connect("loaded", self._projectLoadedCb)

        if not project.createTimeline():
            self.emit("new-project-failed", uri,
                      _('This might be due to a bug or an unsupported project file format. '
                        'If you were trying to add a media file to your project, '
                        'use the "Import" button instead.'))
            return False

        self.current_project = project
        self.emit("new-project-created", project)
        self.current_project.connect("project-changed", self._projectChangedCb)
        self.current_project.pipeline.connect("died", self._projectPipelineDiedCb)

        if is_validate_scenario:
            self.current_project.setupValidateScenario()

        return True

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
                    "Would you like to load it instead?"
                    % beautify_time_delta(time_diff))
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
                self.emit("project-saved", self.current_project, uri)
                self.debug('Saved project: %s', uri)
                # Update the project instance's uri,
                # otherwise, subsequent saves will be to the old uri.
                self.info("Setting the project instance's URI to: %s", uri)
                self.current_project.uri = uri
                self.disable_save = False
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

        self.current_project.finalize()

        project = self.current_project
        self.current_project = None
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

    def newBlankProject(self, ignore_unsaved_changes=False):
        """Creates a new blank project and sets it as the current project.

        Args:
            ignore_unsaved_changes (Optional[bool]): If True, forces
                the creation of a new project without prompting the user about
                unsaved changes. This is an "extreme" way to reset Pitivi's
                state.

        Returns:
            bool: Whether the project has been created successfully.
        """
        self.debug("New blank project")
        if self.current_project is not None:
            # This will prompt users about unsaved changes (if any):
            if not ignore_unsaved_changes and not self.closeRunningProject():
                # The user has not made a decision, don't do anything
                return False

        project = Project(self.app, name=DEFAULT_NAME)
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

        return True

    def revertToSavedProject(self):
        """Discards all unsaved changes and reloads the current open project."""
        if self.current_project.uri is None or not self.current_project.hasUnsavedModifications():
            return True
        if not self.emit("reverting-to-saved", self.current_project):
            return False

        uri = self.current_project.uri
        self.current_project.setModificationState(False)
        self.closeRunningProject()
        self.loadProject(uri)

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
        name (Optional[str]): The name of the new empty project.
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
                                       (GObject.TYPE_PYOBJECT,
                                        GObject.TYPE_PYOBJECT,)),
        "settings-set-from-imported-asset": (GObject.SignalFlags.RUN_LAST, None,
                                             (GES.Asset,)),
        "video-size-changed": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, app, name="", uri=None, scenario=None, **unused_kwargs):
        Loggable.__init__(self)
        GES.Project.__init__(self, uri=uri, extractable_type=GES.Timeline)
        self.log("name:%s, uri:%s", name, uri)
        self.pipeline = None
        self.ges_timeline = None
        self.uri = uri
        self.loaded = False
        self.at_least_one_asset_missing = False
        self.app = app
        self.loading_assets = []
        self.asset_loading_progress = 100
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

        # Project property default values
        self.register_meta(GES.MetaFlag.READWRITE, "name", name)
        self.register_meta(GES.MetaFlag.READWRITE, "author", "")

        # The rendering settings.
        self.set_meta("render-scale", 100.0)

        self.container_profile = \
            GstPbutils.EncodingContainerProfile.new("pitivi-profile",
                                                    _("Pitivi encoding profile"),
                                                    Gst.Caps("application/ogg"),
                                                    None)
        self.video_profile = GstPbutils.EncodingVideoProfile.new(
            Gst.Caps("video/x-theora"), None, Gst.Caps("video/x-raw"), 0)
        self.audio_profile = GstPbutils.EncodingAudioProfile.new(
            Gst.Caps("audio/x-vorbis"), None, Gst.Caps("audio/x-raw"), 0)
        self.container_profile.add_profile(self.video_profile)
        self.container_profile.add_profile(self.audio_profile)
        self.add_encoding_profile(self.container_profile)

        self.muxer = Encoders().default_muxer
        self.vencoder = Encoders().default_video_encoder
        self.aencoder = Encoders().default_audio_encoder
        self._ensureAudioRestrictions()
        self._ensureVideoRestrictions()
        has_default_settings = not bool(uri) and not bool(scenario)
        self._has_default_audio_settings = has_default_settings
        self._has_default_video_settings = has_default_settings

        # FIXME That does not really belong to here and should be savable into
        # the serialized file. For now, just let it be here.
        # A (muxer -> containersettings) map.
        self._containersettings_cache = {}
        # A (vencoder -> vcodecsettings) map.
        self._vcodecsettings_cache = {}
        # A (aencoder -> acodecsettings) map.
        self._acodecsettings_cache = {}
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
        return self.get_meta("name")

    @name.setter
    def name(self, name):
        if name == self.name:
            return
        self.set_meta("name", name)

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

    # Encoding related properties
    def set_rendering(self, rendering):
        video_restrictions = self.video_profile.get_restriction().copy_nth(0)
        video_restrictions_struct = video_restrictions[0]

        if rendering and self._has_rendering_values != rendering:
            width = int(video_restrictions_struct["width"] * self.render_scale / 100)
            height = int(video_restrictions_struct["height"] * self.render_scale / 100)

            video_restrictions.set_value('width', width)
            video_restrictions.set_value('height', height)
        elif self._has_rendering_values != rendering:
            width = int(video_restrictions_struct["width"] / self.render_scale * 100)
            height = int(video_restrictions_struct["height"] / self.render_scale * 100)

            video_restrictions.set_value("width", width)
            video_restrictions.set_value("height", height)
        else:
            restriction = self.audio_profile.get_restriction().copy_nth(0)
            self.audio_profile.set_restriction(restriction)

        self._has_rendering_values = rendering
        self.video_profile.set_restriction(video_restrictions)

    @staticmethod
    def _set_restriction(profile, name, value):
        if profile.get_restriction()[0][name] != value and value:
            restriction = profile.get_restriction().copy_nth(0)
            restriction.set_value(name, value)
            profile.set_restriction(restriction)
            return True

        return False

    def setVideoRestriction(self, name, value):
        res = Project._set_restriction(self.video_profile, name, value)
        if res:
            self.emit("video-size-changed")
            self._has_default_video_settings = False
        return res

    def __setAudioRestriction(self, name, value):
        res = Project._set_restriction(self.audio_profile, name, value)
        if res:
            self._has_default_audio_settings = False
        return res

    @property
    def videowidth(self):
        return self.video_profile.get_restriction()[0]["width"]

    @videowidth.setter
    def videowidth(self, value):
        if self.setVideoRestriction("width", int(value)):
            self._emitChange("rendering-settings-changed", "width", value)

    @property
    def videoheight(self):
        return self.video_profile.get_restriction()[0]["height"]

    @videoheight.setter
    def videoheight(self, value):
        if self.setVideoRestriction("height", int(value)):
            self._emitChange("rendering-settings-changed", "height", value)

    @property
    def videorate(self):
        return self.video_profile.get_restriction()[0]["framerate"]

    @videorate.setter
    def videorate(self, value):
        if self.setVideoRestriction("framerate", value):
            self._emitChange("rendering-settings-changed", "videorate", value)

    @property
    def videopar(self):
        return self.video_profile.get_restriction()[0]["pixel-aspect-ratio"]

    @videopar.setter
    def videopar(self, value):
        if self.setVideoRestriction("pixel-aspect-ratio", value):
            self._emitChange(
                "rendering-settings-changed", "pixel-aspect-ratio", value)

    @property
    def audiochannels(self):
        return self.audio_profile.get_restriction()[0]["channels"]

    @audiochannels.setter
    def audiochannels(self, value):
        if self.__setAudioRestriction("channels", int(value)):
            self._emitChange("rendering-settings-changed", "channels", value)

    @property
    def audiorate(self):
        try:
            return int(self.audio_profile.get_restriction()[0]["rate"])
        except TypeError:
            return None

    @audiorate.setter
    def audiorate(self, value):
        if self.__setAudioRestriction("rate", int(value)):
            self._emitChange("rendering-settings-changed", "rate", value)

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
            self._emitChange("rendering-settings-changed", "aencoder", value)

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
            self._emitChange("rendering-settings-changed", "vencoder", value)

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
            self._emitChange("rendering-settings-changed", "muxer", value)

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

        Returns:
            int: The current asset loading progress (in percent).
        """
        num_loaded = 0
        all_ready = True
        for asset in self.loading_assets:
            if asset.creation_progress < 100:
                all_ready = False
            else:
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
            self.app.action_log.commit("Adding assets")
            self.emit("asset-loading-progress", 100, estimated_time)
            return

        if not self.loaded:
            self.asset_loading_progress = self.__get_loading_project_progress()
        else:
            self.asset_loading_progress = self.__get_loading_assets_progress()

        self.emit("asset-loading-progress", self.asset_loading_progress,
                  estimated_time)

        if self.asset_loading_progress == 100:
            self.info("No more loading assets")
            self.loading_assets = []

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
        self.__setProxy(asset, proxy)

    def __setProxy(self, asset, proxy):
        asset.creation_progress = 100
        if proxy:
            proxy.ready = False
            proxy.error = None
            proxy.creation_progress = 100

        asset.set_proxy(proxy)
        try:
            self.loading_assets.remove(asset)
        except ValueError:
            pass

        if proxy:
            self.add_asset(proxy)
            self.loading_assets.append(proxy)

        self.__updateAssetLoadingProgress()

    # ------------------------------------------ #
    # GES.Project virtual methods implementation #
    # ------------------------------------------ #
    def do_asset_loading(self, asset):
        if asset and not GObject.type_is_a(asset.get_extractable_type(), GES.UriClip):
            # Ignore for example the assets producing GES.TitleClips.
            return

        if not self.loading_assets:
            # Progress == 0 means "starting to import"
            self.emit("asset-loading-progress", 0, 0)

        asset.creation_progress = 0
        asset.error = None
        asset.ready = False
        asset.force_proxying = False
        asset.proxying_error = None
        self.loading_assets.append(asset)

    def do_asset_removed(self, asset):
        self.app.proxy_manager.cancelJob(asset)

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

        if self.loaded:
            if not asset.get_proxy_target() in self.list_assets(GES.Extractable):
                self.app.proxy_manager.addJob(asset, asset.force_proxying)
        else:
            self.debug("Project still loading, not using proxies: "
                       "%s", asset.props.id)
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

        if self.scenario is not None:
            return

        # The project just loaded, we need to check the new
        # encoding profiles and make use of it now.
        container_profile = self.list_encoding_profiles()[0]
        if container_profile is not self.container_profile:
            # The encoding profile might have been reset from the
            # Project file, we just take it as our
            self.container_profile = container_profile
            self.muxer = self._getElementFactoryName(
                Encoders().muxers, container_profile)
            if self.muxer is None:
                self.muxer = Encoders().default_muxer
            for profile in container_profile.get_profiles():
                if isinstance(profile, GstPbutils.EncodingVideoProfile):
                    self.video_profile = profile
                    if self.video_profile.get_restriction() is None:
                        self.video_profile.set_restriction(
                            Gst.Caps("video/x-raw"))
                    self._ensureVideoRestrictions()

                    self.vencoder = self._getElementFactoryName(
                        Encoders().vencoders, profile)
                elif isinstance(profile, GstPbutils.EncodingAudioProfile):
                    self.audio_profile = profile
                    if self.audio_profile.get_restriction() is None:
                        self.audio_profile.set_restriction(
                            Gst.Caps("audio/x-raw"))
                    self._ensureAudioRestrictions()
                    self.aencoder = self._getElementFactoryName(
                        Encoders().aencoders, profile)
                else:
                    self.warning("We do not handle profile: %s", profile)

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

    def useProxiesForAssets(self, assets):
        originals = []
        for asset in assets:
            proxy_target = asset.get_proxy_target()
            if not proxy_target:
                # The asset is not a proxy.
                originals.append(asset)
        if originals:
            self.app.action_log.begin("Adding assets")
            for asset in originals:
                # Add and remove the asset to
                # trigger the proxy creation code path
                self.remove_asset(asset)
                self.emit("asset-loading", asset)
                asset.force_proxying = True
                self.add_asset(asset)

    def disableProxiesForAssets(self, assets, delete_proxy_file=False):
        for asset in assets:
            proxy_target = asset.get_proxy_target()
            if proxy_target:
                self.debug("Stop proxying %s", proxy_target.props.id)
                proxy_target.set_proxy(None)
                if delete_proxy_file:
                    if not self.app.proxy_manager.is_proxy_asset(asset):
                        raise RuntimeError("Trying to remove proxy %s"
                                           " but it does not look like one!",
                                           asset.props.id)
                    os.remove(Gst.uri_get_location(asset.props.id))
            else:
                self.app.proxy_manager.cancelJob(asset)

        if assets:
            self.setModificationState(True)

    def hasDefaultName(self):
        return DEFAULT_NAME == self.name

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
        try:
            self.pipeline.set_timeline(self.ges_timeline)
        except PipelineError as e:
            self.warning("Failed to set the pipeline's timeline: %s", e)
            return False

        return True

    def update_restriction_caps(self):
        # Get the height/width without rendering settings applied
        width, height = self.getVideoWidthAndHeight()
        caps = Gst.Caps.new_empty_simple("video/x-raw")

        caps.set_value("width", width)
        caps.set_value("height", height)
        caps.set_value("framerate", self.videorate)
        for track in self.ges_timeline.get_tracks():
            if isinstance(track, GES.VideoTrack):
                track.set_restriction_caps(caps)

        if self.app:
            self.app.write_action(
                "set-track-restriction-caps",
                caps=caps.to_string(),
                track_type=GES.TrackType.VIDEO.value_nicks[0])

        self.pipeline.flushSeek()

    def addUris(self, uris):
        """Adds assets asynchronously.

        Args:
            uris (List[str]): The URIs of the assets.
        """
        self.app.action_log.begin("Adding assets")
        for uri in uris:
            self.create_asset(quote_uri(uri), GES.UriClip)

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
        return Gst.Fraction(self.videowidth, self.videoheight) * self.videopar

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
        vstr = "width=%d,height=%d,pixel-aspect-ratio=%d/%d,framerate=%d/%d" % (
            videowidth, videoheight,
            self.videopar.num, self.videopar.denom,
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
        return self._containersettings_cache.setdefault(self.muxer, {})

    @containersettings.setter
    def containersettings(self, value):
        self._containersettings_cache[self.muxer] = value

    @property
    def vcodecsettings(self):
        return self._vcodecsettings_cache.setdefault(self.vencoder, {})

    @vcodecsettings.setter
    def vcodecsettings(self, value):
        self._vcodecsettings_cache[self.vencoder] = value

    @property
    def acodecsettings(self):
        return self._acodecsettings_cache.setdefault(self.aencoder, {})

    @acodecsettings.setter
    def acodecsettings(self, value):
        self._acodecsettings_cache[self.aencoder] = value

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

    def _ensureVideoRestrictions(self):
        if self.videowidth is None:
            self.videowidth = 720
        if self.videoheight is None:
            self.videoheight = 576
        if self.videorate is None:
            self.videorate = Gst.Fraction(25, 1)
        if self.videopar is None:
            self.videopar = Gst.Fraction(1, 1)

    def _ensureAudioRestrictions(self):
        if not self.audiochannels:
            self.audiochannels = 2
        if not self.audiorate:
            self.audiorate = 44100

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
                self.videowidth = video.get_width()
                self.videoheight = video.get_height()
                if video.get_framerate_num() > 0:
                    # The asset has a non-variable framerate.
                    self.videorate = Gst.Fraction(video.get_framerate_num(),
                                                  video.get_framerate_denom())
                self.videopar = Gst.Fraction(video.get_par_num(),
                                             video.get_par_denom())
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

    def _emitChange(self, signal, key, value):
        self.emit(signal, key, value)
        # TODO: Remove this when it's possible to undo/redo these changes.
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
        self.dar_combo = getObj("dar_combo")
        self.par_combo = getObj("par_combo")
        self.channels_combo = getObj("channels_combo")
        self.sample_rate_combo = getObj("sample_rate_combo")
        self.year_spinbutton = getObj("year_spinbutton")
        self.author_entry = getObj("author_entry")
        self.width_spinbutton = getObj("width_spinbutton")
        self.height_spinbutton = getObj("height_spinbutton")
        self.audio_presets_combo = getObj("audio_presets_combo")
        self.video_presets_combo = getObj("video_presets_combo")
        self.select_par_radiobutton = getObj("select_par_radiobutton")
        self.constrain_sar_button = getObj("constrain_sar_button")
        self.select_dar_radiobutton = getObj("select_dar_radiobutton")
        self.title_entry = getObj("title_entry")
        self.author_entry = getObj("author_entry")
        self.year_spinbutton = getObj("year_spinbutton")

        self.video_preset_menubutton = getObj("video_preset_menubutton")
        self.video_presets.setupUi(self.video_presets_combo,
                                   self.video_preset_menubutton)
        self.video_presets.connect("preset-loaded", self.__videoPresetLoadedCb)
        self.audio_preset_menubutton = getObj("audio_preset_menubutton")
        self.audio_presets.setupUi(self.audio_presets_combo,
                                   self.audio_preset_menubutton)

    def _setupUiConstraints(self):
        """Creates the dynamic widgets and connects other widgets."""
        # Add custom fraction widgets for DAR and PAR.
        aspect_ratio_grid = self.builder.get_object("aspect_ratio_grid")
        self.dar_fraction_widget = FractionWidget()
        aspect_ratio_grid.attach(self.dar_fraction_widget, 0, 2, 1, 1)
        self.dar_fraction_widget.show()
        self.par_fraction_widget = FractionWidget()
        aspect_ratio_grid.attach(self.par_fraction_widget, 1, 2, 1, 1)
        self.par_fraction_widget.show()

        # Add custom framerate fraction widget.
        frame_rate_box = self.builder.get_object("frame_rate_box")
        self.frame_rate_fraction_widget = FractionWidget()
        frame_rate_box.pack_end(self.frame_rate_fraction_widget, True, True, 0)
        self.frame_rate_fraction_widget.show()

        # Populate comboboxes.
        self.frame_rate_combo.set_model(frame_rates)
        self.dar_combo.set_model(display_aspect_ratios)
        self.par_combo.set_model(pixel_aspect_ratios)

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
        self.wg.addVertex(self.dar_combo, signal="changed")
        self.wg.addVertex(self.dar_fraction_widget, signal="value-changed")
        self.wg.addVertex(self.par_combo, signal="changed")
        self.wg.addVertex(self.par_fraction_widget, signal="value-changed")
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

        # Constrain width and height IFF the Link checkbox is checked.
        self.wg.addEdge(self.width_spinbutton, self.height_spinbutton,
                        predicate=self.widthHeightLinked,
                        edge_func=self.updateHeight)
        self.wg.addEdge(self.height_spinbutton, self.width_spinbutton,
                        predicate=self.widthHeightLinked,
                        edge_func=self.updateWidth)

        # Keep the framerate combo and fraction widgets in sync.
        self.wg.addBiEdge(
            self.frame_rate_combo, self.frame_rate_fraction_widget)

        # Keep the DAR combo and fraction widgets in sync.
        self.wg.addEdge(self.dar_combo, self.dar_fraction_widget,
                        edge_func=self.updateDarFromCombo)
        self.wg.addEdge(self.dar_fraction_widget, self.dar_combo,
                        edge_func=self.updateDarFromFractionWidget)

        # Keep the PAR combo and fraction widgets in sync.
        self.wg.addEdge(self.par_combo, self.par_fraction_widget,
                        edge_func=self.updateParFromCombo)
        self.wg.addEdge(self.par_fraction_widget, self.par_combo,
                        edge_func=self.updateParFromFractionWidget)

        # Constrain the DAR and PAR by linking the fraction widgets together.
        # The combos are already linked to their fraction widgets.
        self.wg.addEdge(self.par_fraction_widget, self.dar_fraction_widget,
                        edge_func=self.updateDarFromPar)
        self.wg.addEdge(self.dar_fraction_widget, self.par_fraction_widget,
                        edge_func=self.updateParFromDar)

        # Update the PAR when the w or h change and the DAR radio is selected.
        self.wg.addEdge(self.width_spinbutton, self.par_fraction_widget,
                        predicate=self.darSelected,
                        edge_func=self.updateParFromDar)
        self.wg.addEdge(self.height_spinbutton, self.par_fraction_widget,
                        predicate=self.darSelected,
                        edge_func=self.updateParFromDar)

        # Update the DAR when the w or h change and the PAR radio is selected.
        self.wg.addEdge(self.width_spinbutton, self.dar_fraction_widget,
                        predicate=self.parSelected,
                        edge_func=self.updateDarFromPar)
        self.wg.addEdge(self.height_spinbutton, self.dar_fraction_widget,
                        predicate=self.parSelected,
                        edge_func=self.updateDarFromPar)

        # Presets.
        self.audio_presets.loadAll()
        self.video_presets.loadAll()

        # Bind the widgets in the Video tab to the Video Presets Manager.
        self.bindSpinbutton(self.video_presets, "width", self.width_spinbutton)
        self.bindSpinbutton(
            self.video_presets, "height", self.height_spinbutton)
        self.bindFractionWidget(
            self.video_presets, "frame-rate", self.frame_rate_fraction_widget)
        self.bindPar(self.video_presets)

        # Bind the widgets in the Audio tab to the Audio Presets Manager.
        self.bindCombo(self.audio_presets, "channels", self.channels_combo)
        self.bindCombo(
            self.audio_presets, "sample-rate", self.sample_rate_combo)

        self.wg.addEdge(
            self.par_fraction_widget, self.video_preset_menubutton)
        self.wg.addEdge(
            self.frame_rate_fraction_widget, self.video_preset_menubutton)
        self.wg.addEdge(self.width_spinbutton, self.video_preset_menubutton)
        self.wg.addEdge(self.height_spinbutton, self.video_preset_menubutton)

        self.wg.addEdge(self.channels_combo, self.audio_preset_menubutton)
        self.wg.addEdge(self.sample_rate_combo, self.audio_preset_menubutton)

    def bindPar(self, mgr):

        def updatePar(value):
            # activate par so we can set the value
            self.select_par_radiobutton.props.active = True
            self.par_fraction_widget.setWidgetValue(value)

        mgr.bindWidget(
            "par", updatePar, self.par_fraction_widget.getWidgetValue)

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

    def _selectDarRadiobuttonToggledCb(self, unused_button):
        self._updateDarParSensitivity()

    def _updateDarParSensitivity(self):
        dar_is_selected = self.darSelected()
        self.dar_fraction_widget.set_sensitive(dar_is_selected)
        self.dar_combo.set_sensitive(dar_is_selected)
        self.par_fraction_widget.set_sensitive(not dar_is_selected)
        self.par_combo.set_sensitive(not dar_is_selected)

    def _updatePresetMenuButton(self, unused_source, unused_target, mgr):
        mgr.updateMenuActions()

    def darSelected(self):
        return self.select_dar_radiobutton.props.active

    def parSelected(self):
        return not self.darSelected()

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

    def updateDarFromPar(self):
        par = self.par_fraction_widget.getWidgetValue()
        sar = self.getSAR()
        self.dar_fraction_widget.setWidgetValue(sar * par)

    def updateParFromDar(self):
        dar = self.dar_fraction_widget.getWidgetValue()
        sar = self.getSAR()
        self.par_fraction_widget.setWidgetValue(dar / sar)

    def updateDarFromCombo(self):
        self.dar_fraction_widget.setWidgetValue(
            get_combo_value(self.dar_combo))

    def updateDarFromFractionWidget(self):
        set_combo_value(
            self.dar_combo, self.dar_fraction_widget.getWidgetValue())

    def updateParFromCombo(self):
        self.par_fraction_widget.setWidgetValue(
            get_combo_value(self.par_combo))

    def updateParFromFractionWidget(self):
        set_combo_value(
            self.par_combo, self.par_fraction_widget.getWidgetValue())

    def updateUI(self):
        # Video
        self.width_spinbutton.set_value(self.project.videowidth)
        self.height_spinbutton.set_value(self.project.videoheight)
        self.frame_rate_fraction_widget.setWidgetValue(self.project.videorate)
        self.par_fraction_widget.setWidgetValue(self.project.videopar)

        if self.project.videopar == Gst.Fraction(1, 1):
            self.select_par_radiobutton.props.active = True
        self._updateDarParSensitivity()

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
        self.title_entry.set_text(self.project.name)
        self.author_entry.set_text(self.project.author)
        if self.project.year:
            year = int(self.project.year)
        else:
            year = datetime.datetime.now().year
        self.year_spinbutton.get_adjustment().set_value(year)

    def updateProject(self):
        with self.app.action_log.started("change project settings"):
            self.project.name = self.title_entry.get_text()
            self.project.author = self.author_entry.get_text()
            self.project.year = str(self.year_spinbutton.get_value_as_int())

            self.project.videowidth = int(self.width_spinbutton.get_value())
            self.project.videoheight = int(self.height_spinbutton.get_value())
            self.project.videopar = self.par_fraction_widget.getWidgetValue()
            self.project.videorate = self.frame_rate_fraction_widget.getWidgetValue()

            self.project.audiochannels = get_combo_value(self.channels_combo)
            self.project.audiorate = get_combo_value(self.sample_rate_combo)

    def _responseCb(self, unused_widget, response):
        """Handles the dialog being closed."""
        if response == Gtk.ResponseType.OK:
            self.updateProject()
        self.window.destroy()
