# PiTiVi , Non-linear video editor
#
#       project.py
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

from pitivi.utils.misc import quote_uri, path_from_uri, isWritable
from pitivi.utils.pipeline import Seeker
from pitivi.utils.loggable import Loggable
from pitivi.utils.signal import Signallable
from pitivi.utils.pipeline import Pipeline
from pitivi.utils.timeline import Selection
from pitivi.utils.widgets import FractionWidget
from pitivi.utils.ripple_update_group import RippleUpdateGroup
from pitivi.utils.ui import frame_rates, audio_rates, audio_depths,\
    audio_channels, beautify_time_delta, get_combo_value, set_combo_value,\
    pixel_aspect_ratios, display_aspect_ratios, SPACING
from pitivi.preset import AudioPresetManager, DuplicatePresetNameException,\
    VideoPresetManager
from pitivi.render import CachedEncoderList


DEFAULT_MUXER = "oggmux"
DEFAULT_VIDEO_ENCODER = "theoraenc"
DEFAULT_AUDIO_ENCODER = "vorbisenc"

#------------------ Backend classes ------------------------------------------#


class ProjectSettingsChanged(UndoableAction):

    def __init__(self, project, old, new):
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
        self.log = log

    def startObserving(self, project):
        project.connect("notify-meta", self._settingsChangedCb)

    def stopObserving(self, project):
        try:
            project.disconnect_by_func(self._settingsChangedCb)
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


class ProjectManager(Signallable, Loggable):
    __signals__ = {
        "new-project-loading": ["uri"],
        "new-project-created": ["project"],
        "new-project-failed": ["uri", "exception"],
        "new-project-loaded": ["project", "fully_ready"],
        "save-project-failed": ["uri", "exception"],
        "project-saved": ["project", "uri"],
        "closing-project": ["project"],
        "project-closed": ["project"],
        "missing-uri": ["formatter", "uri", "factory"],
        "reverting-to-saved": ["project"],
    }

    def __init__(self, app_instance):
        Signallable.__init__(self)
        Loggable.__init__(self)
        self.app = app_instance
        # Current project:
        self.current = None
        self.backup_lock = 0
        self.formatter = None

    def loadProject(self, uri):
        """
        Load the given URI as a project. If a backup file exists, ask if it
        should be loaded instead, and if so, force the user to use "Save as"
        afterwards.
        """
        if self.current is not None and not self.closeRunningProject():
            return False

        self.emit("new-project-loading", uri)

        # We really want a path for os.path to work
        path = path_from_uri(uri)
        backup_path = self._makeBackupURI(path_from_uri(uri))
        use_backup = False
        try:
            time_diff = os.path.getmtime(backup_path) - os.path.getmtime(path)
            self.debug('Backup file "%s" is %d secs newer' % (backup_path, time_diff))
        except OSError:
            self.debug('Backup file "%s" does not exist' % backup_path)
        else:
            if time_diff > 0:
                use_backup = self._restoreFromBackupDialog(time_diff)
        if use_backup:
            uri = self._makeBackupURI(uri)
            self.debug('Loading project from backup "%s"' % uri)
            # Make a new project instance, but don't specify the URI.
            # That way, we force the user to "Save as" (which ensures that the
            # changes in the loaded backup file are approved by the user).
            self.current = Project()
        else:
            # Load the project normally.
            # The "old" backup file will eventually be deleted or overwritten.
            self.current = Project(uri=uri)

        self.current.connect("missing-uri", self._missingURICb)
        self.current.connect("loaded", self._projectLoadedCb)
        if self.current.createTimeline():
            self.emit("new-project-created", self.current)
            self.current.connect("project-changed", self._projectChangedCb)
            return
        else:
            self.emit("new-project-failed", uri,
                      _('This might be due to a bug or an unsupported project file format. '
                      'If you were trying to add a media file to your project, '
                      'use the "Import" button instead.'))
            return

        # Reset projectManager and disconnect all the signals:
        self.newBlankProject()
        return False

    def _restoreFromBackupDialog(self, time_diff):
        """
        Ask if we need to load the autosaved project backup or not.

        @param time_diff: the difference, in seconds, between file mtimes
        """
        dialog = Gtk.Dialog("", None, 0,
                            (_("Ignore backup"), Gtk.ResponseType.REJECT,
                            _("Restore from backup"), Gtk.ResponseType.YES))
        dialog.set_icon_name("pitivi")
        dialog.set_transient_for(self.app.gui)
        dialog.set_modal(True)
        dialog.set_default_response(Gtk.ResponseType.YES)

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
        vbox = Gtk.VBox(False, SPACING * 2)
        vbox.pack_start(primary, True, True, 0)

        # make the [[image] text] hbox
        image = Gtk.Image.new_from_stock(Gtk.STOCK_DIALOG_QUESTION,
                                         Gtk.IconSize.DIALOG)
        hbox = Gtk.HBox(False, SPACING * 2)
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
        if response == Gtk.ResponseType.YES:
            return True
        else:
            return False

    def saveProject(self, project, uri=None, overwrite=False, formatter_type=None,
                    backup=False):
        """
        Save the L{Project} to the given location.

        @type project: L{Project}
        @param project: The L{Project} to save.
        @type uri: L{str}
        @param uri: The absolute URI of the location to store the project to.
        @param overwrite: Whether to overwrite existing location.
        @type overwrite: C{bool}
        @type formatter_type: L{GType}
        @param formatter: The type of the formatter to use to store the project if specified.
        default is GES.XmlFormatter
        @param backup: Whether the requested save operation is for a backup
        @type backup: C{bool}

        @see: L{GES.Project.save}
        """
        if backup:
            if project.uri and self.current.uri is not None:
                # Ignore whatever URI that is passed on to us. It's a trap.
                uri = self._makeBackupURI(project.uri)
            else:
                # Do not try to save backup files for blank projects.
                # It is possible that self.current.uri == None when the backup
                # timer sent us an old instance of the (now closed) project.
                return
        elif uri is None:
            # This allows calling saveProject without specifying the target URI
            uri = project.uri
        else:
            # Ensure the URI we are given is properly encoded, or GIO will fail
            uri = quote_uri(uri)

            # The following needs to happen before we change project.uri:
            if not isWritable(path_from_uri(uri)):
                # TODO: this will not be needed when GTK+ bug #601451 is fixed
                self.emit("save-project-failed", uri,
                          _("You do not have permissions to write to this folder."))
                return

            # Update the project instance's uri for the "Save as" scenario.
            # Otherwise, subsequent saves will be to the old uri.
            if not backup:
                project.uri = uri

        if uri is None:
            self.emit("save-project-failed", uri,
                      _("Cannot save with this file format."))
            return

        try:
            saved = project.save(project.timeline, uri, formatter_type, overwrite)
        except Exception, e:
            self.emit("save-project-failed", uri,
                      _("Cannot save with this file format. %s"), e)

        if saved:
            if not backup:
                # Do not emit the signal when autosaving a backup file
                project.setModificationState(False)
                self.emit("project-saved", project, uri)
                self.debug('Saved project "%s"' % uri)
            else:
                self.debug('Saved backup "%s"' % uri)
        else:
            self.emit("save-project-failed", uri,
                      _("Cannot save with this file format"))
        return saved

    def exportProject(self, project, uri):
        """
        Export a project to a *.tar archive which includes the project file
        and all sources
        """
        # write project file to temporary file
        project_name = project.name if project.name else _("project")
        asset = GES.Formatter.get_default()
        tmp_name = "%s.%s" % (project_name, asset.get_meta(GES.META_FORMATTER_EXTENSION))

        try:
            directory = os.path.dirname(uri)
            tmp_uri = os.path.join(directory, tmp_name)
            self.saveProject(project, tmp_uri, overwrite=True)

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
                    tar.add(path, os.path.join(top, os.path.relpath(path, common)))
                tar.close()

            # remove temporary file
            os.remove(path_from_uri(tmp_uri))
        except:
            return False

        return True

    def _allSourcesInHomedir(self, sources):
        """
        Checks if all sources are located in the users home directory
        """
        homedir = os.path.expanduser("~")

        for source in sources:
            if not path_from_uri(source.get_uri()).startswith(homedir):
                return False

        return True

    def closeRunningProject(self):
        """ close the current project """
        self.info("closing running project")

        if self.current is None:
            return True

        if not self.emit("closing-project", self.current):
            return False

        self.emit("project-closed", self.current)
        # We should never choke on silly stuff like disconnecting signals
        # that were already disconnected. It blocks the UI for nothing.
        # This can easily happen when a project load/creation failed.
        try:
            self.current.disconnect_by_function(self._projectChangedCb)
        except Exception:
            self.debug("Tried disconnecting signals, but they were not connected")
        self._cleanBackup(self.current.uri)
        self.current.release()
        self.current = None

        return True

    def newBlankProject(self, emission=True):
        """ start up a new blank project """
        # if there's a running project we must close it
        if self.current is not None and not self.closeRunningProject():
            return False

        if emission:
            self.emit("new-project-loading", None)
        # We don't have a URI here, None means we're loading a new project
        project = Project(_("New Project"))

        # setting default values for project metadata
        project.author = getpwuid(os.getuid()).pw_gecos.split(",")[0]

        project.createTimeline()
        self.emit("new-project-created", project)
        self.current = project

        project.connect("project-changed", self._projectChangedCb)
        self.emit("new-project-loaded", self.current, emission)
        self.time_loaded = time()

        return True

    def revertToSavedProject(self):
        """
        Discard all unsaved changes and reload current open project
        """
        if self.current.uri is None or not self.current.hasUnsavedModifications():
            return True
        if not self.emit("reverting-to-saved", self.current):
            return False

        uri = self.current.uri
        self.current.setModificationState(False)
        self.closeRunningProject()
        self.loadProject(uri)

    def _projectChangedCb(self, project):
        # The backup_lock is a timer, when a change in the project is done it is
        # set to 10 seconds. If before those 10 seconds pass an other change is done
        # 5 seconds are added in the timeout callback instead of saving the backup
        # file. The limit is 60 seconds.
        uri = project.uri
        if uri is None:
            return

        if self.backup_lock == 0:
            self.backup_lock = 10
            GLib.timeout_add_seconds(self.backup_lock, self._saveBackupCb, project, uri)
        else:
            if self.backup_lock < 60:
                self.backup_lock += 5

    def _saveBackupCb(self, project, uri):
        if self.backup_lock > 10:
            self.backup_lock -= 5
            return True
        else:
            self.saveProject(project, overwrite=True, backup=True)
            self.backup_lock = 0
        return False

    def _cleanBackup(self, uri):
        if uri is None:
            return
        path = path_from_uri(self._makeBackupURI(uri))
        if os.path.exists(path):
            os.remove(path)
            self.debug('Removed backup file "%s"' % path)

    def _makeBackupURI(self, uri):
        """
        Returns a backup file URI (or path if the given arg is not a URI).
        This does not guarantee that the backup file actually exists or that
        the file extension is actually a project file.

        @Param the project file path or URI
        """
        name, ext = os.path.splitext(uri)
        return name + ext + "~"

    def _missingURICb(self, project, error, asset, what=None):
        return self.emit("missing-uri", project, error, asset)

    def _projectLoadedCb(self, project, timeline):
        self.debug("Project loaded")
        self.emit("new-project-loaded", self.current, True)
        self.time_loaded = time()


class Project(Loggable, GES.Project):
    """The base class for PiTiVi projects

    @ivar name: The name of the project
    @type name: C{str}
    @ivar description: A description of the project
    @type description: C{str}
    @ivar timeline: The timeline
    @type timeline: L{GES.Timeline}
    @ivar pipeline: The timeline's pipeline
    @type pipeline: L{Pipeline}
    @ivar format: The format under which the project is currently stored.
    @type format: L{FormatterClass}
    @ivar loaded: Whether the project is fully loaded or not.
    @type loaded: C{bool}

    Signals:
     - C{project-changed}: Modifications were made to the project
     - C{start-importing}: Started to import files in bash
     - C{done-importing}: Done importing files in bash
    """

    __gsignals__ = {
        "start-importing": (GObject.SignalFlags.RUN_LAST, None, ()),
        "done-importing": (GObject.SignalFlags.RUN_LAST, None, ()),
        "project-changed": (GObject.SignalFlags.RUN_LAST, None, ()),
        "rendering-settings-changed": (GObject.SignalFlags.RUN_LAST, None,
                                       (GObject.TYPE_PYOBJECT,
                                        GObject.TYPE_PYOBJECT,))
    }

    def __init__(self, name="", uri=None, **kwargs):
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

        # FIXME Remove our URI and work more closely with GES.Project URI handling
        self.uri = uri

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
                                                    Gst.Caps("application/ogg"),
                                                    None)

        # Create video profile (We use the same default seetings as the project settings)
        video_profile = GstPbutils.EncodingVideoProfile.new(Gst.Caps("video/x-theora"),
                                                            None,
                                                            Gst.Caps("video/x-raw"),
                                                            0)

        # Create audio profile (We use the same default seetings as the project settings)
        audio_profile = GstPbutils.EncodingAudioProfile.new(Gst.Caps("audio/x-vorbis"),
                                                            None,
                                                            Gst.Caps("audio/x-raw"),
                                                            0)
        container_profile.add_profile(video_profile)
        container_profile.add_profile(audio_profile)
        # Keep a reference to those profiles
        # FIXME We should handle the case we have more than 1 audio and 1 video profiles
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

    #-----------------#
    # Our properties  #
    #-----------------#

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
    @property
    def videowidth(self):
        return self.video_profile.get_restriction()[0]["videowidth"]

    @videowidth.setter
    def videowidth(self, value):
        if self.video_profile.get_restriction()[0]["videowidth"] != value and value:
            self.video_profile.get_restriction()[0]["videowidth"] = value
            self._emitChange("rendering-settings-changed", "videowidth", value)

    @property
    def videoheight(self):
        return self.video_profile.get_restriction()[0]["videoheight"]

    @videoheight.setter
    def videoheight(self, value):
        if self.video_profile.get_restriction()[0]["videoheight"] != value and value:
            self.video_profile.get_restriction()[0]["videoheight"] = value
            self._emitChange("rendering-settings-changed", "videoheight", value)

    @property
    def videorate(self):
        return self.video_profile.get_restriction()[0]["videorate"]

    @videorate.setter
    def videorate(self, value):
        if self.video_profile.get_restriction()[0]["videorate"] != value and value:
            self.video_profile.get_restriction()[0]["videorate"] = value

    @property
    def videopar(self):
        return self.video_profile.get_restriction()[0]["videopar"]

    @videopar.setter
    def videopar(self, value):
        if self.video_profile.get_restriction()[0]["videopar"] != value and value:
            self.video_profile.get_restriction()[0]["videopar"] = value

    @property
    def audiochannels(self):
        return self.audio_profile.get_restriction()[0]["audiochannels"]

    @audiochannels.setter
    def audiochannels(self, value):
        if self.video_profile.get_restriction()[0]["audiochannels"] != value and value:
            self.audio_profile.get_restriction()[0]["audiochannels"] = value
            self._emitChange("rendering-settings-changed", "audiochannels", value)

    @property
    def audiorate(self):
        return self.audio_profile.get_restriction()[0]["audiorate"]

    @audiorate.setter
    def audiorate(self, value):
        if self.video_profile.get_restriction()[0]["audiorate"] != value and value:
            self.audio_profile.get_restriction()[0]["audiorate"] = value
            self._emitChange("rendering-settings-changed", "audiorate", value)

    @property
    def audiodepth(self):
        return self.audio_profile.get_restriction()[0]["audiodepth"]

    @audiodepth.setter
    def audiodepth(self, value):
        if self.video_profile.get_restriction()[0]["audiodepth"] != value and value:
            self.audio_profile.get_restriction()[0]["audiodepth"] = value
            self._emitChange("rendering-settings-changed", "audiodepth", value)

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
                        audiotype = template.get_caps()[0].get_name()
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
                        videotype = template.get_caps()[0].get_name()
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
                        muxertype = template.get_caps()[0].get_name()
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
            return self.set_meta("render-scale", value)

    #--------------------------------------------#
    # GES.Project virtual methods implementation #
    #--------------------------------------------#
    def _handle_asset_loaded(self, id):
        self.nb_imported_files += 1
        self.nb_remaining_file_to_import = len([asset for asset in self.get_loading_assets() if
                GObject.type_is_a(asset.get_extractable_type(), GES.UriClip)])
        if self.nb_remaining_file_to_import == 0:
            self.nb_imported_files = 0
            self._emitChange("done-importing")

    def do_asset_added(self, asset):
        """
        When GES.Project emit "asset-added" this vmethod
        get calls
        """
        self._handle_asset_loaded(asset.get_id())

    def do_loading_error(self, error, id, type):
        """ vmethod, get called on "asset-loading-error"""
        self._handle_asset_loaded(id)

    def do_loaded(self, timeline):
        """ vmethod, get called on "loaded" """
        self._ensureTracks()
        #self._ensureLayer()

        encoders = CachedEncoderList()
        # The project just loaded, we need to check the new
        # encoding profiles and make use of it now.
        container_profile = self.list_encoding_profiles()[0]
        if container_profile is not self.container_profile:
            # The encoding profile might have been reset from the
            # Project file, we just take it as our
            self.container_profile = container_profile
            self.muxer = self._getElementFactoryName(encoders.muxers, container_profile)
            if self.muxer is None:
                self.muxer = DEFAULT_MUXER
            for profile in container_profile.get_profiles():
                if isinstance(profile, GstPbutils.EncodingVideoProfile):
                    self.video_profile = profile
                    if self.video_profile.get_restriction() is None:
                        self.video_profile.set_restriction(Gst.Caps("video/x-raw"))
                    self._ensureVideoRestrictions()

                    self.vencoder = self._getElementFactoryName(encoders.vencoders, profile)
                elif isinstance(profile, GstPbutils.EncodingAudioProfile):
                    self.audio_profile = profile
                    if self.audio_profile.get_restriction() is None:
                        self.audio_profile.set_restriction(Gst.Caps("audio/x-raw"))
                    self._ensureAudioRestrictions()
                    self.aencoder = self._getElementFactoryName(encoders.aencoders, profile)
                else:
                    self.warning("We do not handle profile: %s" % profile)

    #--------------------------------------------#
    #               Our API                      #
    #--------------------------------------------#
    def createTimeline(self):
        """
        The pitivi.Project handle 1 timeline at a time
        unlike GES.Project
        """
        self.timeline = self.extract()
        self._calculateNbLoadingAssets()
        if self.timeline is None:
            return False

        self.timeline.selection = Selection()
        self.pipeline = Pipeline()
        self.pipeline.add_timeline(self.timeline)

        return True

    def addUris(self, uris):
        """
        Add c{uris} to the source list.

        The uris will be analyzed before being added.
        """
        # Do not try to reload URIS that we already have loaded
        for uri in uris:
            self.create_asset(quote_uri(uri), GES.UriClip)
        self._calculateNbLoadingAssets()

    def listSources(self):
        return self.list_assets(GES.UriClip)

    def release(self):
        if self.pipeline:
            self.pipeline.release()
        self.pipeline = None
        self.timeline = None

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
            scale = self.render_scale
        else:
            scale = 100
        return self.videowidth * scale / 100, self.videoheight * scale / 100

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
        # TODO: Figure out why including 'depth' causes pipeline failures:
        astr = "rate=%d,channels=%d" % (self.audiorate, self.audiochannels)
        caps_str = "audio/x-raw,%s" % (astr)
        audio_caps = Gst.caps_from_string(caps_str)
        return audio_caps

    def setAudioProperties(self, nbchanns=-1, rate=-1, depth=-1):
        """
        Set the number of audio channels, rate and depth
        """
        self.info("%d x %dHz %dbits", nbchanns, rate, depth)
        if not nbchanns == -1 and not nbchanns == self.audiochannels:
            self.audiochannels = nbchanns
        if not rate == -1 and not rate == self.audiorate:
            self.audiorate = rate
        if not depth == -1 and not depth == self.audiodepth:
            self.audiodepth = depth

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

    #--------------------------------------------#
    #               Private methods              #
    #--------------------------------------------#

    def _ensureTracks(self):
        if self.timeline is None:
            self.warning("Can't ensure tracks if no timeline set")
            return

        track_types = [track.get_property("track-type")
                       for track in self.timeline.get_tracks()]

        if GES.TrackType.VIDEO not in track_types:
            self.timeline.add_track(GES.Track.video_raw_new())
        if GES.TrackType.AUDIO not in track_types:
            self.timeline.add_track(GES.Track.audio_raw_new())

    def _ensureLayer(self):
        if self.timeline is None:
            self.warning("Can't ensure tracks if no timeline set")
            return
        if not self.timeline.get_layers():
            self.timeline.append_layer()

    def _ensureVideoRestrictions(self):
        if not self.videowidth:
            self.videowidth = 720
        if not self.videoheight:
            self.videoheight = 576
        if not self.videorate:
            self.videorate = Gst.Fraction(25, 1)
        if not self.videopar:
            self.videopar = Gst.Fraction(16, 15)

    def _ensureAudioRestrictions(self):
        if not self.audiochannels:
            self.audiochannels = 2
        if not self.audiorate:
            self.audiorate = 44100
        if not self.audiodepth:
            self.audiodepth = 16

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
                                                   Gst.Caps(profile.get_format()),
                                                   Gst.PadDirection.SRC,
                                                   False)
        if factories:
            factories.sort(key=lambda x: - x.get_rank())
            return factories[0].get_name()
        return None

    def _calculateNbLoadingAssets(self):
        nb_remaining_file_to_import = len([asset for asset in self.get_loading_assets() if
                GObject.type_is_a(asset.get_extractable_type(), GES.UriClip)])
        if self.nb_remaining_file_to_import == 0 and nb_remaining_file_to_import:
            self.nb_remaining_file_to_import = nb_remaining_file_to_import
            self._emitChange("start-importing")
            return
        self.nb_remaining_file_to_import = nb_remaining_file_to_import


#----------------------- UI classes ------------------------------------------#
class ProjectSettingsDialog():

    def __init__(self, parent, project):
        self.project = project

        self.builder = Gtk.Builder()
        self.builder.add_from_file(os.path.join(get_ui_dir(), "projectsettings.ui"))
        self._setProperties()
        self.builder.connect_signals(self)

        # add custom display aspect ratio widget
        self.dar_fraction_widget = FractionWidget()
        self.video_properties_table.attach(self.dar_fraction_widget,
                                           0, 1, 6, 7,
                                           xoptions=Gtk.AttachOptions.EXPAND | Gtk.AttachOptions.FILL,
                                           yoptions=0)
        self.dar_fraction_widget.show()

        # add custom pixel aspect ratio widget
        self.par_fraction_widget = FractionWidget()
        self.video_properties_table.attach(self.par_fraction_widget,
                                           1, 2, 6, 7,
                                           xoptions=Gtk.AttachOptions.EXPAND | Gtk.AttachOptions.FILL,
                                           yoptions=0)
        self.par_fraction_widget.show()

        # add custom framerate widget
        self.frame_rate_fraction_widget = FractionWidget()
        self.video_properties_table.attach(self.frame_rate_fraction_widget,
                                           1, 2, 2, 3,
                                           xoptions=Gtk.AttachOptions.EXPAND | Gtk.AttachOptions.FILL,
                                           yoptions=0)
        self.frame_rate_fraction_widget.show()

        # populate coboboxes with appropriate data
        self.frame_rate_combo.set_model(frame_rates)
        self.dar_combo.set_model(display_aspect_ratios)
        self.par_combo.set_model(pixel_aspect_ratios)

        self.channels_combo.set_model(audio_channels)
        self.sample_rate_combo.set_model(audio_rates)
        self.sample_depth_combo.set_model(audio_depths)

        # behavior
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
        self.wg.addVertex(self.sample_depth_combo, signal="changed")

        # constrain width and height IFF constrain_sar_button is active
        self.wg.addEdge(self.width_spinbutton, self.height_spinbutton,
                        predicate=self.constrained,
                        edge_func=self.updateHeight)
        self.wg.addEdge(self.height_spinbutton, self.width_spinbutton,
                        predicate=self.constrained,
                        edge_func=self.updateWidth)

        # keep framereate text field and combo in sync
        self.wg.addBiEdge(self.frame_rate_combo, self.frame_rate_fraction_widget)

        # keep dar text field and combo in sync
        self.wg.addEdge(self.dar_combo, self.dar_fraction_widget,
                        edge_func=self.updateDarFromCombo)
        self.wg.addEdge(self.dar_fraction_widget, self.dar_combo,
                        edge_func=self.updateDarFromFractionWidget)

        # keep par text field and combo in sync
        self.wg.addEdge(self.par_combo, self.par_fraction_widget,
                        edge_func=self.updateParFromCombo)
        self.wg.addEdge(self.par_fraction_widget, self.par_combo,
                        edge_func=self.updateParFromFractionWidget)

        # constrain DAR and PAR values. because the combo boxes are already
        # linked, we only have to link the fraction widgets together.
        self.wg.addEdge(self.par_fraction_widget, self.dar_fraction_widget,
                        edge_func=self.updateDarFromPar)
        self.wg.addEdge(self.dar_fraction_widget, self.par_fraction_widget,
                        edge_func=self.updateParFromDar)

        # update PAR when width/height change and the DAR checkbutton is
        # selected
        self.wg.addEdge(self.width_spinbutton, self.par_fraction_widget,
                        predicate=self.darSelected,
                        edge_func=self.updateParFromDar)
        self.wg.addEdge(self.height_spinbutton, self.par_fraction_widget,
                        predicate=self.darSelected,
                        edge_func=self.updateParFromDar)

        # update DAR when width/height change and the PAR checkbutton is
        # selected
        self.wg.addEdge(self.width_spinbutton, self.dar_fraction_widget,
                        predicate=self.parSelected,
                        edge_func=self.updateDarFromPar)
        self.wg.addEdge(self.height_spinbutton, self.dar_fraction_widget,
                        predicate=self.parSelected,
                        edge_func=self.updateDarFromPar)

        # presets
        self.audio_presets = AudioPresetManager()
        self.audio_presets.loadAll()
        self.video_presets = VideoPresetManager()
        self.video_presets.loadAll()

        self._fillPresetsTreeview(self.audio_preset_treeview,
                                  self.audio_presets,
                                  self._updateAudioPresetButtons)
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
        self.bindSpinbutton(self.video_presets, "height", self.height_spinbutton)
        self.bindFractionWidget(self.video_presets, "frame-rate", self.frame_rate_fraction_widget)
        self.bindPar(self.video_presets)

        # Bind the widgets in the Audio tab to the Audio Presets Manager.
        self.bindCombo(self.audio_presets, "channels", self.channels_combo)
        self.bindCombo(self.audio_presets, "sample-rate", self.sample_rate_combo)
        self.bindCombo(self.audio_presets, "depth", self.sample_depth_combo)

        self.wg.addEdge(self.par_fraction_widget, self.save_video_preset_button)
        self.wg.addEdge(self.frame_rate_fraction_widget, self.save_video_preset_button)
        self.wg.addEdge(self.width_spinbutton, self.save_video_preset_button)
        self.wg.addEdge(self.height_spinbutton, self.save_video_preset_button)

        self.wg.addEdge(self.channels_combo, self.save_audio_preset_button)
        self.wg.addEdge(self.sample_rate_combo, self.save_audio_preset_button)
        self.wg.addEdge(self.sample_depth_combo, self.save_audio_preset_button)

        # Set the shading style in the contextual toolbars below presets
        video_presets_toolbar = self.builder.get_object("video_presets_toolbar")
        audio_presets_toolbar = self.builder.get_object("audio_presets_toolbar")
        video_presets_toolbar.get_style_context().add_class("inline-toolbar")
        audio_presets_toolbar.get_style_context().add_class("inline-toolbar")

        self.updateUI()

        self.createAudioNoPreset(self.audio_presets)
        self.createVideoNoPreset(self.video_presets)

    def bindPar(self, mgr):

        def updatePar(value):
            # activate par so we can set the value
            self.select_par_radiobutton.props.active = True
            self.par_fraction_widget.setWidgetValue(value)

        mgr.bindWidget("par", updatePar, self.par_fraction_widget.getWidgetValue)

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
        model.connect("row-inserted", self._newPresetCb, column, renderer, treeview)
        renderer.connect("edited", self._presetNameEditedCb, mgr)
        renderer.connect("editing-started", self._presetNameEditingStartedCb, mgr)
        treeview.get_selection().connect("changed", self._presetChangedCb, mgr,
                                         update_buttons_func)
        treeview.connect("focus-out-event", self._treeviewDefocusedCb, mgr)

    def createAudioNoPreset(self, mgr):
        mgr.prependPreset(_("No preset"), {
            "depth": self.project.audiodepth,
            "channels": self.project.audiochannels,
            "sample-rate": self.project.audiorate})

    def createVideoNoPreset(self, mgr):
        mgr.prependPreset(_("No preset"), {
            "par": self.project.videopar,
            "frame-rate": self.project.videorate,
            "height": self.project.videoheight,
            "width": self.project.videowidth})

    def _newPresetCb(self, model, path, iter_, column, renderer, treeview):
        """ Handle the addition of a preset to the model of the preset manager. """
        treeview.set_cursor_on_cell(path, column, renderer, start_editing=True)
        treeview.grab_focus()

    def _presetNameEditedCb(self, renderer, path, new_text, mgr):
        """Handle the renaming of a preset."""
        try:
            mgr.renamePreset(path, new_text)
        except DuplicatePresetNameException:
            error_markup = _('"%s" already exists.') % new_text
            self._showPresetManagerError(mgr, error_markup)

    def _presetNameEditingStartedCb(self, renderer, editable, path, mgr):
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
        update_preset_buttons_func()
        self._hidePresetManagerError(mgr)

    def _treeviewDefocusedCb(self, widget, event, mgr):
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

    def constrained(self):
        return self.constrain_sar_button.props.active

    def _updateFraction(self, unused, fraction, combo):
        fraction.setWidgetValue(get_combo_value(combo))

    def _updateCombo(self, unused, combo, fraction):
        set_combo_value(combo, fraction.getWidgetValue())

    def getSAR(self):
        width = int(self.width_spinbutton.get_value())
        height = int(self.height_spinbutton.get_value())
        return Gst.Fraction(width, height)

    def _setProperties(self):
        getObj = self.builder.get_object
        self.window = getObj("project-settings-dialog")
        self.video_properties_table = getObj("video_properties_table")
        self.video_properties_table = getObj("video_properties_table")
        self.frame_rate_combo = getObj("frame_rate_combo")
        self.dar_combo = getObj("dar_combo")
        self.par_combo = getObj("par_combo")
        self.channels_combo = getObj("channels_combo")
        self.sample_rate_combo = getObj("sample_rate_combo")
        self.sample_depth_combo = getObj("sample_depth_combo")
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

    def _constrainSarButtonToggledCb(self, button):
        if button.props.active:
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

    def _addAudioPresetButtonClickedCb(self, button):
        preset_name = self._getUniquePresetName(self.audio_presets)
        self.audio_presets.addPreset(preset_name, {
            "channels": get_combo_value(self.channels_combo),
            "sample-rate": get_combo_value(self.sample_rate_combo),
            "depth": get_combo_value(self.sample_depth_combo)
        })
        self.audio_presets.restorePreset(preset_name)
        self._updateAudioPresetButtons()

    def _removeAudioPresetButtonClickedCb(self, button):
        selection = self.audio_preset_treeview.get_selection()
        model, iter_ = selection.get_selected()
        if iter_:
            self.audio_presets.removePreset(model[iter_][0])

    def _saveAudioPresetButtonClickedCb(self, button):
        self.audio_presets.saveCurrentPreset()
        self.save_audio_preset_button.set_sensitive(False)
        self.remove_audio_preset_button.set_sensitive(True)

    def _addVideoPresetButtonClickedCb(self, button):
        preset_name = self._getUniquePresetName(self.video_presets)
        self.video_presets.addPreset(preset_name, {
            "width": int(self.width_spinbutton.get_value()),
            "height": int(self.height_spinbutton.get_value()),
            "frame-rate": self.frame_rate_fraction_widget.getWidgetValue(),
            "par": self.par_fraction_widget.getWidgetValue(),
        })
        self.video_presets.restorePreset(preset_name)
        self._updateVideoPresetButtons()

    def _removeVideoPresetButtonClickedCb(self, button):
        selection = self.video_preset_treeview.get_selection()
        model, iter_ = selection.get_selected()
        if iter_:
            self.video_presets.removePreset(model[iter_][0])

    def _saveVideoPresetButtonClickedCb(self, button):
        self.video_presets.saveCurrentPreset()
        self.save_video_preset_button.set_sensitive(False)
        self.remove_video_preset_button.set_sensitive(True)

    def _updateAudioPresetButtons(self):
        can_save = self.audio_presets.isSaveButtonSensitive()
        self.save_audio_preset_button.set_sensitive(can_save)
        can_remove = self.audio_presets.isRemoveButtonSensitive()
        self.remove_audio_preset_button.set_sensitive(can_remove)

    def _updateVideoPresetButtons(self):
        self.save_video_preset_button.set_sensitive(self.video_presets.isSaveButtonSensitive())
        self.remove_video_preset_button.set_sensitive(self.video_presets.isRemoveButtonSensitive())

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
        self.width_spinbutton.set_value(height * self.sar)

    def updateHeight(self):
        width = int(self.width_spinbutton.get_value())
        self.height_spinbutton.set_value(width * (1 / self.sar))

    def updateDarFromPar(self):
        par = self.par_fraction_widget.getWidgetValue()
        sar = self.getSAR()
        self.dar_fraction_widget.setWidgetValue(sar * par)

    def updateParFromDar(self):
        dar = self.dar_fraction_widget.getWidgetValue()
        sar = self.getSAR()
        self.par_fraction_widget.setWidgetValue(dar * (1 / sar))

    def updateDarFromCombo(self):
        self.dar_fraction_widget.setWidgetValue(get_combo_value(self.dar_combo))

    def updateDarFromFractionWidget(self):
        set_combo_value(self.dar_combo, self.dar_fraction_widget.getWidgetValue())

    def updateParFromCombo(self):
        self.par_fraction_widget.setWidgetValue(get_combo_value(self.par_combo))

    def updateParFromFractionWidget(self):
        set_combo_value(self.par_combo, self.par_fraction_widget.getWidgetValue())

    def updateUI(self):

        self.width_spinbutton.set_value(self.project.videowidth)
        self.height_spinbutton.set_value(self.project.videoheight)

        # video
        self.frame_rate_fraction_widget.setWidgetValue(self.project.videorate)
        self.par_fraction_widget.setWidgetValue(self.project.videopar)

        # audio
        set_combo_value(self.channels_combo, self.project.audiochannels)
        set_combo_value(self.sample_rate_combo, self.project.audiorate)
        set_combo_value(self.sample_depth_combo, self.project.audiodepth)

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
        self.project.videorate = self.frame_rate_fraction_widget.getWidgetValue()

        self.project.audiochannels = get_combo_value(self.channels_combo)
        self.project.audiorate = get_combo_value(self.sample_rate_combo)
        self.project.audiodepth = get_combo_value(self.sample_depth_combo)

    def _responseCb(self, unused_widget, response):
        if response == Gtk.ResponseType.OK:
            self.updateSettings()
            self.updateMetadata()
        self.window.destroy()
