# Pitivi video editor
#
#       pitivi/project.py
#
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

"""
Project related classes
"""

import os
from gi.repository import GstPbutils
from gi.repository import GES
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject
import tarfile

from time import time
from datetime import datetime
from gettext import gettext as _
from pwd import getpwuid

from pitivi.undo.undo import UndoableAction
from pitivi.configure import get_ui_dir

from pitivi.utils.validate import has_validate, create_monitor
from pitivi.utils.misc import quote_uri, path_from_uri, isWritable, unicode_error_dialog
from pitivi.utils.pipeline import PipelineError, Seeker
from pitivi.utils.loggable import Loggable
from pitivi.utils.pipeline import Pipeline
from pitivi.utils.widgets import FractionWidget
from pitivi.utils.ripple_update_group import RippleUpdateGroup
from pitivi.utils.ui import frame_rates, audio_rates,\
    audio_channels, beautify_time_delta, get_combo_value, set_combo_value,\
    pixel_aspect_ratios, display_aspect_ratios, SPACING
from pitivi.preset import AudioPresetManager, DuplicatePresetNameException,\
    VideoPresetManager
from pitivi.render import CachedEncoderList


DEFAULT_MUXER = "oggmux"
DEFAULT_VIDEO_ENCODER = "theoraenc"
DEFAULT_AUDIO_ENCODER = "vorbisenc"

# ------------------ Backend classes ---------------------------------------- #


class AssetRemovedAction(UndoableAction):

    def __init__(self, project, asset):
        UndoableAction.__init__(self)
        self.project = project
        self.asset = asset

    def undo(self):
        self.project.add_asset(self.asset)

    def do(self):
        self.project.remove_asset(self.asset)

    def asScenarioAction(self):
        st = Gst.Structure.new_empty("remove-asset")
        st.set_value("id", self.asset.get_id())
        type_string = GObject.type_name(self.asset.get_extractable_type())
        st.set_value("type", type_string)
        return st


class AssetAddedAction(UndoableAction):

    def __init__(self, project, asset):
        UndoableAction.__init__(self)
        self.project = project
        self.asset = asset

    def undo(self):
        self.project.remove_asset(self.asset)

    def do(self):
        self.project.add_asset(self.asset)

    def asScenarioAction(self):
        st = Gst.Structure.new_empty("add-asset")
        st.set_value("id", self.asset.get_id())
        type_string = GObject.type_name(self.asset.get_extractable_type())
        st.set_value("type", type_string)
        return st


class ProjectSettingsChanged(UndoableAction):

    def __init__(self, project, old, new):
        UndoableAction.__init__(self)
        self.project = project
        self.oldsettings = old
        self.newsettings = new

    def do(self):
        self.project.setSettings(self.newsettings)
        self._done()

    def undo(self):
        self.project.setSettings(self.oldsettings)
        self._undone()


class ProjectLogObserver(UndoableAction):

    def __init__(self, log):
        UndoableAction.__init__(self)
        self.log = log

    def startObserving(self, project):
        project.connect("notify-meta", self._settingsChangedCb)
        project.connect("asset-added", self._assetAddedCb)
        project.connect("asset-removed", self._assetRemovedCb)

    def stopObserving(self, project):
        try:
            project.disconnect_by_func(self._settingsChangedCb)
            project.disconnect_by_func(self._assetAddedCb)
            project.disconnect_by_func(self._assetRemovedCb)
        except Exception:
            # This can happen when we interrupt the loading of a project,
            # such as in mainwindow's _projectManagerMissingUriCb
            pass

    def _settingsChangedCb(self, project, item, value):
        """
        FIXME Renable undo/redo
        action = ProjectSettingsChanged(project, old, new)
        self.log.begin("change project settings")
        self.log.push(action)
        self.log.commit()
        """
        pass

    def _assetAddedCb(self, project, asset):
        action = AssetAddedAction(project, asset)
        self.log.push(action)

    def _assetRemovedCb(self, project, asset):
        action = AssetRemovedAction(project, asset)
        self.log.push(action)


class ProjectManager(GObject.Object, Loggable):

    """
    @type app: L{Pitivi}
    @type current_project: L{Project}
    @param disable_save: Whether saving is disabled to enforce using save-as.
    """

    __gsignals__ = {
        "new-project-loading": (GObject.SIGNAL_RUN_LAST, None, (str,)),
        "new-project-created": (GObject.SIGNAL_RUN_LAST, None, (object,)),
        "new-project-failed": (GObject.SIGNAL_RUN_LAST, None, (str, object)),
        "new-project-loaded": (GObject.SIGNAL_RUN_LAST, None, (object, bool)),
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
        self.__missing_uris = False

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

    def _pipelineDied(self, unused_pipeline):
        """
        Show an error dialog telling the user that everything went kaboom.
        """
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
        vbox = Gtk.VBox(homogeneous=False, spacing=SPACING * 2)
        vbox.pack_start(primary, True, True, 0)

        # make the [[image] text] hbox
        image = Gtk.Image.new_from_icon_name("dialog-error", Gtk.IconSize.DIALOG)
        hbox = Gtk.HBox(homogeneous=False, spacing=SPACING * 2)
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
        """
        Load the given URI as a project. If a backup file exists, ask if it
        should be loaded instead, and if so, force the user to use "Save as"
        afterwards.
        """
        if self.current_project is not None and not self.closeRunningProject():
            return False

        self.__missing_uris = False
        self.emit("new-project-loading", uri)

        is_validate_scenario = self._isValidateScenario(uri)
        if not is_validate_scenario:
            uri = self._tryUsingBackupFile(uri)
            scenario = None
        else:
            scenario = path_from_uri(uri)
            uri = None

        # Load the project:
        self.current_project = Project(self.app, uri=uri, scenario=scenario)

        self.current_project.connect_after("missing-uri", self._missingURICb)
        self.current_project.connect("loaded", self._projectLoadedCb)

        if self.current_project.createTimeline():
            self.emit("new-project-created", self.current_project)
            self.current_project.connect(
                "project-changed", self._projectChangedCb)
            self.current_project.pipeline.connect("died", self._pipelineDied)

            if is_validate_scenario:
                self.current_project.setupValidateScenario()
            return True
        else:
            self.emit("new-project-failed", uri,
                      _('This might be due to a bug or an unsupported project file format. '
                        'If you were trying to add a media file to your project, '
                        'use the "Import" button instead.'))
            self.newBlankProject(ignore_unsaved_changes=True)
            return False

    def _restoreFromBackupDialog(self, time_diff):
        """
        Ask if we need to load the autosaved project backup or not.

        @param time_diff: the difference, in seconds, between file mtimes
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
        """
        Save the current project. All arguments are optional, but the behavior
        will differ depending on the combination of which ones are set.

        If a URI is specified, this means we want to save to a new (different)
        location, so it will be used instead of the current project instance's
        existing URI.

        "backup=True" is for automatic backups: it ignores any "uri" arg, uses
        the current project instance to save to a special URI behind the scenes.

        "formatter_type" allows specifying a GES formatter type to use; if None,
        GES will default to GES.XmlFormatter.
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
                self.current_project.timeline, uri,
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
        """
        Export a project to a *.tar archive which includes the project file
        and all sources
        """
        # write project file to temporary file
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
                    'An error occurred, will save the tarball as "%s"' % renamed)
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
        """
        Checks if all sources are located in the users home directory
        """
        homedir = os.path.expanduser("~")

        for source in sources:
            if not path_from_uri(source.get_id()).startswith(homedir):
                return False

        return True

    def closeRunningProject(self):
        """ close the current project """

        if self.current_project is None:
            self.warning(
                "Trying to close a project that was already closed/didn't exist")
            return True

        self.info("closing running project %s", self.current_project.uri)
        if not self.emit("closing-project", self.current_project):
            self.warning(
                "Could not close project - this could be because there were unsaved changes and the user cancelled when prompted about them")
            return False

        self.emit("project-closed", self.current_project)
        # We should never choke on silly stuff like disconnecting signals
        # that were already disconnected. It blocks the UI for nothing.
        # This can easily happen when a project load/creation failed.
        try:
            self.current_project.disconnect_by_function(self._projectChangedCb)
        except Exception:
            self.debug(
                "Tried disconnecting signals, but they were not connected")
        self._cleanBackup(self.current_project.uri)
        self.exitcode = self.current_project.release()
        self.current_project = None

        return True

    def newBlankProject(self, emission=True, ignore_unsaved_changes=False):
        """
        Start up a new blank project.

        The ignore_unsaved_changes parameter is used in special cases to force
        the creation of a new project without prompting the user about unsaved
        changes. This is an "extreme" way to reset Pitivi's state.
        """
        if self.current_project is not None:
            # This will prompt users about unsaved changes (if any):
            if not ignore_unsaved_changes and not self.closeRunningProject():
                # The user has not made a decision, don't do anything
                return False

        self.__missing_uris = False
        if emission:
            self.emit("new-project-loading", None)
        # We don't have a URI here, None means we're loading a new project
        project = Project(self.app, _("New Project"))

        # setting default values for project metadata
        project.author = getpwuid(os.getuid()).pw_gecos.split(",")[0]

        project.createTimeline()
        project._ensureTracks()
        project.update_restriction_caps()
        self.current_project = project
        self.emit("new-project-created", project)

        project.connect("project-changed", self._projectChangedCb)
        project.pipeline.connect("died", self._pipelineDied)
        project.setModificationState(False)
        self.emit("new-project-loaded", self.current_project, emission)
        self.time_loaded = time()

        return True

    def revertToSavedProject(self):
        """
        Discard all unsaved changes and reload current open project
        """
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
        """
        Returns a backup file URI (or path if the given arg is not a URI).
        This does not guarantee that the backup file actually exists or that
        the file extension is actually a project file.

        @Param the project file path or URI
        """
        name, ext = os.path.splitext(uri)
        return name + ext + "~"

    def _missingURICb(self, project, error, asset):
        self.__missing_uris = True
        new_uri = self.emit("missing-uri", project, error, asset)
        if not new_uri:
            project.at_least_one_asset_missing = True
        self.current_project.setModificationState(True)
        return new_uri

    def _projectLoadedCb(self, unused_project, unused_timeline):
        self.debug("Project loaded %s", self.current_project.props.uri)
        self.emit("new-project-loaded", self.current_project, True)
        if self.__missing_uris:
            self.current_project.setModificationState(True)
        self.time_loaded = time()


class Project(Loggable, GES.Project):

    """
    The base class for Pitivi projects

    @ivar name: The name of the project
    @type name: C{str}
    @ivar description: A description of the project
    @type description: C{str}
    @ivar timeline: The timeline
    @type timeline: L{GES.Timeline}
    @ivar pipeline: The timeline's pipeline
    @type pipeline: L{Pipeline}
    @ivar loaded: Whether the project is fully loaded or not.
    @type loaded: C{bool}

    Signals:
     - C{project-changed}: Modifications were made to the project
     - C{start-importing}: Started to import files
     - C{done-importing}: Done importing files
    """

    __gsignals__ = {
        "start-importing": (GObject.SignalFlags.RUN_LAST, None, ()),
        "done-importing": (GObject.SignalFlags.RUN_LAST, None, ()),
        "project-changed": (GObject.SignalFlags.RUN_LAST, None, ()),
        "rendering-settings-changed": (GObject.SignalFlags.RUN_LAST, None,
                                       (GObject.TYPE_PYOBJECT,
                                        GObject.TYPE_PYOBJECT,))
    }

    def __init__(self, app, name="", uri=None, scenario=None, **unused_kwargs):
        """
        @param name: the name of the project
        @param uri: the uri of the project
        """
        Loggable.__init__(self)
        GES.Project.__init__(self, uri=uri, extractable_type=GES.Timeline)
        self.log("name:%s, uri:%s", name, uri)
        self.pipeline = None
        self.timeline = None
        self.seeker = Seeker()
        self.uri = uri
        self.scenario = scenario
        self.loaded = False
        self._at_least_one_asset_missing = False
        self.app = app

        # GstValidate
        self._scenario = None

        # Follow imports
        self._dirty = False
        self.nb_remaining_file_to_import = 0
        self.nb_imported_files = 0

        # Project property default values
        self.register_meta(GES.MetaFlag.READWRITE, "name", name)
        self.register_meta(GES.MetaFlag.READWRITE, "author",
                           getpwuid(os.getuid()).pw_gecos.split(",")[0])

        # Handle rendering setting
        self.set_meta("render-scale", 100.0)

        container_profile = \
            GstPbutils.EncodingContainerProfile.new("pitivi-profile",
                                                    _("Pitivi encoding profile"),
                                                    Gst.Caps(
                                                        "application/ogg"),
                                                    None)

        # Create video profile (We use the same default seetings as the project
        # settings)
        video_profile = GstPbutils.EncodingVideoProfile.new(
            Gst.Caps("video/x-theora"), None, Gst.Caps("video/x-raw"), 0)

        # Create audio profile (We use the same default seetings as the project
        # settings)
        audio_profile = GstPbutils.EncodingAudioProfile.new(
            Gst.Caps("audio/x-vorbis"), None, Gst.Caps("audio/x-raw"), 0)
        container_profile.add_profile(video_profile)
        container_profile.add_profile(audio_profile)
        # Keep a reference to those profiles
        # FIXME We should handle the case we have more than 1 audio and 1 video
        # profiles
        self.container_profile = container_profile
        self.audio_profile = audio_profile
        self.video_profile = video_profile

        # Add the profile to ourself
        self.add_encoding_profile(container_profile)

        # Now set the presets/ GstElement that will be used
        # FIXME We might want to add the default Container/video decoder/audio encoder
        # into the application settings, for now we just make sure to pick one with
        # eighest probably the user has installed ie ogg+vorbis+theora

        self.muxer = DEFAULT_MUXER
        self.vencoder = DEFAULT_VIDEO_ENCODER
        self.aencoder = DEFAULT_AUDIO_ENCODER
        self._ensureAudioRestrictions()
        self._ensureVideoRestrictions()

        # FIXME That does not really belong to here and should be savable into
        # The serilized file. For now, just let it be here.
        # A (muxer -> containersettings) map.
        self._containersettings_cache = {}
        # A (vencoder -> vcodecsettings) map.
        self._vcodecsettings_cache = {}
        # A (aencoder -> acodecsettings) map.
        self._acodecsettings_cache = {}
        self._has_rendering_values = False

        self.runner = None
        self.monitor = None
        self._scenario = None

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

    @property
    def at_least_one_asset_missing(self):
        return self._at_least_one_asset_missing

    @at_least_one_asset_missing.setter
    def at_least_one_asset_missing(self, value):
        self._at_least_one_asset_missing = value
        self.setModificationState(True)

    # Project specific properties
    @property
    def name(self):
        return self.get_meta("name")

    @name.setter
    def name(self, name):
        self.set_meta("name", name)
        self.setModificationState(True)

    @property
    def year(self):
        return self.get_meta("year")

    @year.setter
    def year(self, year):
        self.set_meta("year", year)
        self.setModificationState(True)

    @property
    def description(self):
        return self.get_meta("description")

    @description.setter
    def description(self, description):
        self.set_meta("description", description)
        self.setModificationState(True)

    @property
    def author(self):
        return self.get_meta("author")

    @author.setter
    def author(self, author):
        self.set_meta("author", author)
        self.setModificationState(True)

    # Encoding related properties
    def set_rendering(self, rendering):
        if rendering and self._has_rendering_values != rendering:
            self.videowidth = self.videowidth * self.render_scale / 100
            self.videoheight = self.videoheight * self.render_scale / 100
        elif self._has_rendering_values != rendering:
            self.videowidth = self.videowidth / self.render_scale * 100
            self.videoheight = self.videoheight / self.render_scale * 100
        else:
            restriction = self.video_profile.get_restriction().copy_nth(0)
            self.video_profile.set_restriction(restriction)

            restriction = self.audio_profile.get_restriction().copy_nth(0)
            self.audio_profile.set_restriction(restriction)
        self._has_rendering_values = rendering

    @staticmethod
    def _set_restriction(profile, name, value):
        if profile.get_restriction()[0][name] != value and value:
            restriction = profile.get_restriction().copy_nth(0)
            restriction.set_value(name, value)
            profile.set_restriction(restriction)
            return True

        return False

    def setVideoRestriction(self, name, value):
        return Project._set_restriction(self.video_profile, name, value)

    def __setAudioRestriction(self, name, value):
        return Project._set_restriction(self.audio_profile, name, value)

    @property
    def videowidth(self):
        return self.video_profile.get_restriction()[0]["width"]

    @videowidth.setter
    def videowidth(self, value):
        if value and self.setVideoRestriction("width", int(value)):
            self._emitChange("rendering-settings-changed", "width", value)

    @property
    def videoheight(self):
        return self.video_profile.get_restriction()[0]["height"]

    @videoheight.setter
    def videoheight(self, value):
        if value and self.setVideoRestriction("height", int(value)):
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
        if value and self.__setAudioRestriction("channels", int(value)):
            self._emitChange("rendering-settings-changed", "channels", value)

    @property
    def audiorate(self):
        try:
            return int(self.audio_profile.get_restriction()[0]["rate"])
        except TypeError:
            return None

    @audiorate.setter
    def audiorate(self, value):
        if value and self.__setAudioRestriction("rate", int(value)):
            self._emitChange("rendering-settings-changed", "rate", value)

    @property
    def aencoder(self):
        return self.audio_profile.get_preset_name()

    @aencoder.setter
    def aencoder(self, value):
        if self.audio_profile.get_preset_name() != value and value:
            feature = Gst.Registry.get().lookup_feature(value)
            if feature is None:
                self.error("%s not in registry", value)
            else:
                for template in feature.get_static_pad_templates():
                    if template.name_template == "src":
                        audiotype = template.get_caps()[0].to_string()
                        break
                self.audio_profile.set_format(Gst.Caps(audiotype))
            self.audio_profile.set_preset_name(value)

            self._emitChange("rendering-settings-changed", "aencoder", value)

    @property
    def vencoder(self):
        return self.video_profile.get_preset_name()

    @vencoder.setter
    def vencoder(self, value):
        if self.video_profile.get_preset_name() != value and value:
            feature = Gst.Registry.get().lookup_feature(value)
            if feature is None:
                self.error("%s not in registry", value)
            else:
                for template in feature.get_static_pad_templates():
                    if template.name_template == "src":
                        videotype = template.get_caps()[0].to_string()
                        break
                self.video_profile.set_format(Gst.Caps(videotype))

            self.video_profile.set_preset_name(value)

            self._emitChange("rendering-settings-changed", "vencoder", value)

    @property
    def muxer(self):
        return self.container_profile.get_preset_name()

    @muxer.setter
    def muxer(self, value):
        if self.container_profile.get_preset_name() != value and value:
            feature = Gst.Registry.get().lookup_feature(value)
            if feature is None:
                self.error("%s not in registry", value)
            else:
                for template in feature.get_static_pad_templates():
                    if template.name_template == "src":
                        muxertype = template.get_caps()[0].to_string()
                        break
                self.container_profile.set_format(Gst.Caps(muxertype))
            self.container_profile.set_preset_name(value)

            self._emitChange("rendering-settings-changed", "muxer", value)

    @property
    def render_scale(self):
        return self.get_meta("render-scale")

    @render_scale.setter
    def render_scale(self, value):
        if value:
            self.set_meta("render-scale", value)

    # ------------------------------------------ #
    # GES.Project virtual methods implementation #
    # ------------------------------------------ #

    def _handle_asset_loaded(self, asset=None, unused_asset_id=None):
        if asset and not GObject.type_is_a(asset.get_extractable_type(), GES.UriClip):
            # Ignore for example the assets producing GES.TitleClips.
            return
        self.nb_imported_files += 1
        self.nb_remaining_file_to_import = self.__countRemainingFilesToImport()
        if self.nb_remaining_file_to_import == 0:
            self.nb_imported_files = 0
            # We do not take into account asset comming from project
            if self.loaded is True:
                self.app.action_log.commit()
            self._emitChange("done-importing")

    def do_asset_added(self, asset):
        """
        When GES.Project emit "asset-added" this vmethod
        get calls
        """
        self._handle_asset_loaded(asset=asset)

    def do_loading_error(self, unused_error, asset_id, unused_type):
        """ vmethod, get called on "asset-loading-error"""
        self._handle_asset_loaded(unused_asset_id=asset_id)

    def do_loaded(self, unused_timeline):
        """ vmethod, get called on "loaded" """

        self._ensureTracks()
        self.timeline.props.auto_transition = True
        # self._ensureLayer()
        if self.scenario is not None:
            return

        self.loaded = True
        encoders = CachedEncoderList()
        # The project just loaded, we need to check the new
        # encoding profiles and make use of it now.
        container_profile = self.list_encoding_profiles()[0]
        if container_profile is not self.container_profile:
            # The encoding profile might have been reset from the
            # Project file, we just take it as our
            self.container_profile = container_profile
            self.muxer = self._getElementFactoryName(
                encoders.muxers, container_profile)
            if self.muxer is None:
                self.muxer = DEFAULT_MUXER
            for profile in container_profile.get_profiles():
                if isinstance(profile, GstPbutils.EncodingVideoProfile):
                    self.video_profile = profile
                    if self.video_profile.get_restriction() is None:
                        self.video_profile.set_restriction(
                            Gst.Caps("video/x-raw"))
                    self._ensureVideoRestrictions()

                    self.vencoder = self._getElementFactoryName(
                        encoders.vencoders, profile)
                elif isinstance(profile, GstPbutils.EncodingAudioProfile):
                    self.audio_profile = profile
                    if self.audio_profile.get_restriction() is None:
                        self.audio_profile.set_restriction(
                            Gst.Caps("audio/x-raw"))
                    self._ensureAudioRestrictions()
                    self.aencoder = self._getElementFactoryName(
                        encoders.aencoders, profile)
                else:
                    self.warning("We do not handle profile: %s" % profile)

    # ------------------------------------------ #
    # Our API                                    #
    # ------------------------------------------ #
    def _commit(self):
        """
        Our override of the GES.Timeline.commit method, letting us
        scenarialize the action in the scenarios.
        """
        self.app.write_action("commit")
        GES.Timeline.commit(self.timeline)

    def createTimeline(self):
        """
        Load the project.
        """
        try:
            # The project is loaded from the file in this call.
            self.timeline = self.extract()
        except GLib.Error as e:
            self.warning("Failed to extract the timeline: %s", e)
            self.timeline = None

        if self.timeline is None:
            return False

        self.timeline.commit = self._commit
        self._calculateNbLoadingAssets()

        self.pipeline = Pipeline(self.app)
        try:
            self.pipeline.set_timeline(self.timeline)
        except PipelineError as e:
            self.warning("Failed to set the pipeline's timeline: %s", e)
            return False

        return True

    def update_restriction_caps(self):
        caps = Gst.Caps.new_empty_simple("video/x-raw")

        caps.set_value("width", self.videowidth)
        caps.set_value("height", self.videoheight)
        caps.set_value("framerate", self.videorate)
        for track in self.timeline.get_tracks():
            if isinstance(track, GES.VideoTrack):
                track.set_restriction_caps(caps)

        if self.app:
            self.app.write_action("set-track-restriction-caps", {
                "caps": caps.to_string(),
                "track-type": GES.TrackType.VIDEO.value_nicks[0]})

        self.pipeline.flushSeek()

    def addUris(self, uris):
        """
        Add c{uris} asynchronously.

        The uris will be analyzed before being added, so only valid ones pass.
        """
        # Do not try to reload URIS that we already have loaded
        self.app.action_log.begin("Adding assets")
        for uri in uris:
            self.create_asset(quote_uri(uri), GES.UriClip)
        self._calculateNbLoadingAssets()

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
        self.timeline = None

        return res

    def setModificationState(self, state):
        self._dirty = state
        if state:
            self.emit('project-changed')

    def hasUnsavedModifications(self):
        return self._dirty

    def getDAR(self):
        return Gst.Fraction(self.videowidth, self.videoheight) * self.videopar

    def getVideoWidthAndHeight(self, render=False):
        """ Returns the video width and height as a tuple

        @param render: Whether to apply self.render_scale to the returned values
        @type render: bool
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
        """ Returns the GstCaps corresponding to the video settings """
        videowidth, videoheight = self.getVideoWidthAndHeight(render=render)
        vstr = "width=%d,height=%d,pixel-aspect-ratio=%d/%d,framerate=%d/%d" % (
            videowidth, videoheight,
            self.videopar.num, self.videopar.denom,
            self.videorate.num, self.videorate.denom)
        caps_str = "video/x-raw,%s" % (vstr)
        video_caps = Gst.caps_from_string(caps_str)
        return video_caps

    def getAudioCaps(self):
        """ Returns the GstCaps corresponding to the audio settings """
        astr = "rate=%d,channels=%d" % (self.audiorate, self.audiochannels)
        caps_str = "audio/x-raw,%s" % (astr)
        audio_caps = Gst.caps_from_string(caps_str)
        return audio_caps

    def setAudioProperties(self, nbchanns=-1, rate=-1):
        """
        Set the number of audio channels and the rate
        """
        self.info("%d x %dHz %dbits", nbchanns, rate)
        if not nbchanns == -1 and not nbchanns == self.audiochannels:
            self.audiochannels = nbchanns
        if not rate == -1 and not rate == self.audiorate:
            self.audiorate = rate

    def setEncoders(self, muxer="", vencoder="", aencoder=""):
        """ Set the video/audio encoder and muxer """
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
        if self.timeline is None:
            self.warning("Can't ensure tracks if no timeline set")
            return

        track_types = [track.get_property("track-type")
                       for track in self.timeline.get_tracks()]

        if GES.TrackType.VIDEO not in track_types:
            self.timeline.add_track(GES.VideoTrack.new())
        if GES.TrackType.AUDIO not in track_types:
            self.timeline.add_track(GES.AudioTrack.new())

    def _ensureLayer(self):
        if self.timeline is None:
            self.warning("Can't ensure tracks if no timeline set")
            return
        if not self.timeline.get_layers():
            self.timeline.append_layer()

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

    def _emitChange(self, signal, key=None, value=None):
        if key and value:
            self.emit(signal, key, value)
        else:
            self.emit(signal)
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

    def _calculateNbLoadingAssets(self):
        nb_remaining_file_to_import = self.__countRemainingFilesToImport()
        if self.nb_remaining_file_to_import == 0 and nb_remaining_file_to_import:
            self.nb_remaining_file_to_import = nb_remaining_file_to_import
            self._emitChange("start-importing")
            return
        self.nb_remaining_file_to_import = nb_remaining_file_to_import

    def __countRemainingFilesToImport(self):
        assets = self.get_loading_assets()
        return len([asset for asset in assets if
                    GObject.type_is_a(asset.get_extractable_type(), GES.UriClip)])


# ---------------------- UI classes ----------------------------------------- #
class ProjectSettingsDialog():

    def __init__(self, parent_window, project):
        self.project = project
        self._createUi()
        self.window.set_transient_for(parent_window)
        self._setupUiConstraints()
        self.updateUI()
        self.createAudioNoPreset(self.audio_presets)
        self.createVideoNoPreset(self.video_presets)

    def _createUi(self):
        """
        Initialize the static parts of the UI and set up various shortcuts
        """
        self.builder = Gtk.Builder()
        self.builder.add_from_file(
            os.path.join(get_ui_dir(), "projectsettings.ui"))
        self.builder.connect_signals(self)

        getObj = self.builder.get_object
        self.window = getObj("project-settings-dialog")
        self.video_properties_table = getObj("video_properties_table")
        self.video_properties_table = getObj("video_properties_table")
        self.frame_rate_combo = getObj("frame_rate_combo")
        self.dar_combo = getObj("dar_combo")
        self.par_combo = getObj("par_combo")
        self.channels_combo = getObj("channels_combo")
        self.sample_rate_combo = getObj("sample_rate_combo")
        self.year_spinbutton = getObj("year_spinbutton")
        self.author_entry = getObj("author_entry")
        self.width_spinbutton = getObj("width_spinbutton")
        self.height_spinbutton = getObj("height_spinbutton")
        self.save_audio_preset_button = getObj("save_audio_preset_button")
        self.save_video_preset_button = getObj("save_video_preset_button")
        self.audio_preset_treeview = getObj("audio_preset_treeview")
        self.video_preset_treeview = getObj("video_preset_treeview")
        self.select_par_radiobutton = getObj("select_par_radiobutton")
        self.remove_audio_preset_button = getObj("remove_audio_preset_button")
        self.remove_video_preset_button = getObj("remove_video_preset_button")
        self.constrain_sar_button = getObj("constrain_sar_button")
        self.select_dar_radiobutton = getObj("select_dar_radiobutton")
        self.video_preset_infobar = getObj("video-preset-infobar")
        self.audio_preset_infobar = getObj("audio-preset-infobar")
        self.title_entry = getObj("title_entry")
        self.author_entry = getObj("author_entry")
        self.year_spinbutton = getObj("year_spinbutton")

        # Set the shading style in the contextual toolbars below presets
        video_presets_toolbar = getObj("video_presets_toolbar")
        audio_presets_toolbar = getObj("audio_presets_toolbar")
        video_presets_toolbar.get_style_context().add_class(
            Gtk.STYLE_CLASS_INLINE_TOOLBAR)
        audio_presets_toolbar.get_style_context().add_class(
            Gtk.STYLE_CLASS_INLINE_TOOLBAR)

    def _setupUiConstraints(self):
        """
        Create dynamic widgets and
        set up the relationships between various widgets
        """
        # Add custom DAR fraction widget.
        self.dar_fraction_widget = FractionWidget()
        self.video_properties_table.attach(self.dar_fraction_widget,
                                           0, 6, 1, 1)
        self.dar_fraction_widget.show()

        # Add custom PAR fraction widget.
        self.par_fraction_widget = FractionWidget()
        self.video_properties_table.attach(self.par_fraction_widget,
                                           1, 6, 1, 1)
        self.par_fraction_widget.show()

        # Add custom framerate fraction widget.
        self.frame_rate_fraction_widget = FractionWidget()
        self.video_properties_table.attach(self.frame_rate_fraction_widget,
                                           1, 2, 1, 1)
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
        self.wg.addVertex(self.save_audio_preset_button,
                          update_func=self._updateAudioSaveButton)
        self.wg.addVertex(self.save_video_preset_button,
                          update_func=self._updateVideoSaveButton)
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
        self.audio_presets = AudioPresetManager()
        self.audio_presets.loadAll()
        self._fillPresetsTreeview(self.audio_preset_treeview,
                                  self.audio_presets,
                                  self._updateAudioPresetButtons)
        self.video_presets = VideoPresetManager()
        self.video_presets.loadAll()
        self._fillPresetsTreeview(self.video_preset_treeview,
                                  self.video_presets,
                                  self._updateVideoPresetButtons)

        # A map which tells which infobar should be used when displaying
        # an error for a preset manager.
        self._infobarForPresetManager = {
            self.audio_presets: self.audio_preset_infobar,
            self.video_presets: self.video_preset_infobar}

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
            self.par_fraction_widget, self.save_video_preset_button)
        self.wg.addEdge(
            self.frame_rate_fraction_widget, self.save_video_preset_button)
        self.wg.addEdge(self.width_spinbutton, self.save_video_preset_button)
        self.wg.addEdge(self.height_spinbutton, self.save_video_preset_button)

        self.wg.addEdge(self.channels_combo, self.save_audio_preset_button)
        self.wg.addEdge(self.sample_rate_combo, self.save_audio_preset_button)

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

    def _fillPresetsTreeview(self, treeview, mgr, update_buttons_func):
        """Set up the specified treeview to display the specified presets.

        @param treeview: The treeview for displaying the presets.
        @type treeview: TreeView
        @param mgr: The preset manager.
        @type mgr: PresetManager
        @param update_buttons_func: A function which updates the buttons for
        removing and saving a preset, enabling or disabling them accordingly.
        @type update_buttons_func: function
        """
        renderer = Gtk.CellRendererText()
        renderer.props.editable = True
        column = Gtk.TreeViewColumn("Preset", renderer, text=0)
        treeview.append_column(column)
        treeview.props.headers_visible = False
        model = mgr.getModel()
        treeview.set_model(model)
        model.connect(
            "row-inserted", self._newPresetCb, column, renderer, treeview)
        renderer.connect("edited", self._presetNameEditedCb, mgr)
        renderer.connect(
            "editing-started", self._presetNameEditingStartedCb, mgr)
        treeview.get_selection().connect("changed", self._presetChangedCb, mgr,
                                         update_buttons_func)
        treeview.connect("focus-out-event", self._treeviewDefocusedCb, mgr)

    def createAudioNoPreset(self, mgr):
        mgr.prependPreset(_("No preset"), {
            "channels": self.project.audiochannels,
            "sample-rate": self.project.audiorate})

    def createVideoNoPreset(self, mgr):
        mgr.prependPreset(_("No preset"), {
            "par": self.project.videopar,
            "frame-rate": self.project.videorate,
            "height": self.project.videoheight,
            "width": self.project.videowidth})

    def _newPresetCb(self, unused_model, path, unused_iter_, column, renderer, treeview):
        """ Handle the addition of a preset to the model of the preset manager. """
        treeview.set_cursor_on_cell(path, column, renderer, start_editing=True)
        treeview.grab_focus()

    def _presetNameEditedCb(self, unused_renderer, path, new_text, mgr):
        """Handle the renaming of a preset."""
        try:
            mgr.renamePreset(path, new_text)
        except DuplicatePresetNameException:
            error_markup = _('"%s" already exists.') % new_text
            self._showPresetManagerError(mgr, error_markup)

    def _presetNameEditingStartedCb(self, unused_renderer, unused_editable, unused_path, mgr):
        """Handle the start of a preset renaming."""
        self._hidePresetManagerError(mgr)

    def _presetChangedCb(self, selection, mgr, update_preset_buttons_func):
        """Handle the selection of a preset."""
        model, iter_ = selection.get_selected()
        if iter_:
            preset = model[iter_][0]
        else:
            preset = None
        mgr.restorePreset(preset)
        self._updateSar()
        update_preset_buttons_func()
        self._hidePresetManagerError(mgr)

    def _treeviewDefocusedCb(self, unused_widget, unused_event, mgr):
        self._hidePresetManagerError(mgr)

    def _showPresetManagerError(self, mgr, error_markup):
        """Show the specified error on the infobar associated with the manager.

        @param mgr: The preset manager for which to show the error.
        @type mgr: PresetManager
        """
        infobar = self._infobarForPresetManager[mgr]
        # The infobar must contain exactly one object in the content area:
        # a label for displaying the error.
        label = infobar.get_content_area().children()[0]
        label.set_markup(error_markup)
        infobar.show()

    def _hidePresetManagerError(self, mgr):
        """Hide the error infobar associated with the manager.

        @param mgr: The preset manager for which to hide the error infobar.
        @type mgr: PresetManager
        """
        infobar = self._infobarForPresetManager[mgr]
        infobar.hide()

    def widthHeightLinked(self):
        return self.constrain_sar_button.props.active and not self.video_presets.ignore_update_requests

    def _updateFraction(self, unused, fraction, combo):
        fraction.setWidgetValue(get_combo_value(combo))

    def _updateCombo(self, unused, combo, fraction):
        set_combo_value(combo, fraction.getWidgetValue())

    def getSAR(self):
        width = int(self.width_spinbutton.get_value())
        height = int(self.height_spinbutton.get_value())
        return Gst.Fraction(width, height)

    def _constrainSarButtonToggledCb(self, unused_button):
        self._updateSar()

    def _updateSar(self):
        self.sar = self.getSAR()

    def _selectDarRadiobuttonToggledCb(self, button):
        state = button.props.active
        self.dar_fraction_widget.set_sensitive(state)
        self.dar_combo.set_sensitive(state)
        self.par_fraction_widget.set_sensitive(not state)
        self.par_combo.set_sensitive(not state)

    @staticmethod
    def _getUniquePresetName(mgr):
        """Get a unique name for a new preset for the specified PresetManager.
        """
        existing_preset_names = list(mgr.getPresetNames())
        preset_name = _("New preset")
        i = 1
        while preset_name in existing_preset_names:
            preset_name = _("New preset %d") % i
            i += 1
        return preset_name

    def _addAudioPresetButtonClickedCb(self, unused_button):
        preset_name = self._getUniquePresetName(self.audio_presets)
        self.audio_presets.addPreset(preset_name, {
            "channels": get_combo_value(self.channels_combo),
            "sample-rate": get_combo_value(self.sample_rate_combo),
        })
        self.audio_presets.restorePreset(preset_name)
        self._updateAudioPresetButtons()

    def _removeAudioPresetButtonClickedCb(self, unused_button):
        selection = self.audio_preset_treeview.get_selection()
        model, iter_ = selection.get_selected()
        if iter_:
            self.audio_presets.removePreset(model[iter_][0])

    def _saveAudioPresetButtonClickedCb(self, unused_button):
        self.audio_presets.saveCurrentPreset()
        self.save_audio_preset_button.set_sensitive(False)
        self.remove_audio_preset_button.set_sensitive(True)

    def _addVideoPresetButtonClickedCb(self, unused_button):
        preset_name = self._getUniquePresetName(self.video_presets)
        self.video_presets.addPreset(preset_name, {
            "width": int(self.width_spinbutton.get_value()),
            "height": int(self.height_spinbutton.get_value()),
            "frame-rate": self.frame_rate_fraction_widget.getWidgetValue(),
            "par": self.par_fraction_widget.getWidgetValue(),
        })
        self.video_presets.restorePreset(preset_name)
        self._updateVideoPresetButtons()

    def _removeVideoPresetButtonClickedCb(self, unused_button):
        selection = self.video_preset_treeview.get_selection()
        model, iter_ = selection.get_selected()
        if iter_:
            self.video_presets.removePreset(model[iter_][0])

    def _saveVideoPresetButtonClickedCb(self, unused_button):
        self.video_presets.saveCurrentPreset()
        self.save_video_preset_button.set_sensitive(False)
        self.remove_video_preset_button.set_sensitive(True)

    def _updateAudioPresetButtons(self):
        can_save = self.audio_presets.isSaveButtonSensitive()
        self.save_audio_preset_button.set_sensitive(can_save)
        can_remove = self.audio_presets.isRemoveButtonSensitive()
        self.remove_audio_preset_button.set_sensitive(can_remove)

    def _updateVideoPresetButtons(self):
        self.save_video_preset_button.set_sensitive(
            self.video_presets.isSaveButtonSensitive())
        self.remove_video_preset_button.set_sensitive(
            self.video_presets.isRemoveButtonSensitive())

    def _updateAudioSaveButton(self, unused_in, button):
        button.set_sensitive(self.audio_presets.isSaveButtonSensitive())

    def _updateVideoSaveButton(self, unused_in, button):
        button.set_sensitive(self.video_presets.isSaveButtonSensitive())

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
        self.width_spinbutton.set_value(self.project.videowidth)
        self.height_spinbutton.set_value(self.project.videoheight)

        # video
        self.frame_rate_fraction_widget.setWidgetValue(self.project.videorate)
        self.par_fraction_widget.setWidgetValue(self.project.videopar)

        # audio
        set_combo_value(self.channels_combo, self.project.audiochannels)
        set_combo_value(self.sample_rate_combo, self.project.audiorate)

        self._selectDarRadiobuttonToggledCb(self.select_dar_radiobutton)

        # metadata
        self.title_entry.set_text(self.project.name)
        self.author_entry.set_text(self.project.author)
        if self.project.year:
            year = int(self.project.year)
        else:
            year = datetime.now().year
        self.year_spinbutton.get_adjustment().set_value(year)

    def updateMetadata(self):
        self.project.name = self.title_entry.get_text()
        self.project.author = self.author_entry.get_text()
        self.project.year = str(self.year_spinbutton.get_value_as_int())

    def updateSettings(self):
        self.project.videowidth = int(self.width_spinbutton.get_value())
        self.project.videoheight = int(self.height_spinbutton.get_value())
        self.project.videopar = self.par_fraction_widget.getWidgetValue()
        self.project.videorate = self.frame_rate_fraction_widget.getWidgetValue(
        )

        self.project.audiochannels = get_combo_value(self.channels_combo)
        self.project.audiorate = get_combo_value(self.sample_rate_combo)

    def _responseCb(self, unused_widget, response):
        if response == Gtk.ResponseType.OK:
            self.updateSettings()
            self.updateMetadata()
        self.window.destroy()
