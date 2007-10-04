#!/usr/bin/python
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
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""
Project class
"""

import os.path
import gobject
import gst
from timeline.timeline import Timeline
from sourcelist import SourceList
from bin import SmartTimelineBin
from settings import ExportSettings
from configure import APPNAME

from gettext import gettext as _
from serializable import Serializable, to_object_from_data_type
from projectsaver import ProjectSaver, ProjectSaveError, ProjectLoadError

class Project(gobject.GObject, Serializable):
    """ The base class for PiTiVi projects
    Signals

       string save-uri-requested()
            The the current project has been requested to save itself, but
            needs a URI to which to save. Handlers should return a uri to save
            the file to or None, in which case the file will not be saved.

        boolean confirm-overwrite()
            The project has been requested to save itself, but the file on
            disk either already exists, or has been changed since the previous
            load/ save operation. In this case, the project wants permition to
            overwrite before continuing. handlers should return True if it is
            ok to overwrit the file, or False otherwise. By default, this
            signal handler assumes True.

        void settings-changed()
            The project settings have changed
    """

    __gsignals__ = {
        "save-uri-requested" : ( gobject.SIGNAL_RUN_LAST,
                                     gobject.TYPE_STRING,
                                     ( )),
        "confirm-overwrite" : ( gobject.SIGNAL_RUN_LAST,
                                gobject.TYPE_BOOLEAN,
                                (gobject.TYPE_STRING, )),
        "settings-changed" : ( gobject.SIGNAL_RUN_LAST,
                               gobject.TYPE_NONE,
                               (  ))
        }

    __data_type__ = "project"

    def __init__(self, name="", uri=None):
        """
        name : the name of the project
        uri : the uri of the project
        """
        gst.log("name:%s, uri:%s" % (name, uri))
        gobject.GObject.__init__(self)
        self.name = name
        self.settings = None
        self.description = ""
        self.uri = uri
        self.sources = SourceList(self)
        self.timeline = None
        self.timelinebin = None
        self.settingssigid = 0
        self._dirty = False
        self.timeline = Timeline(self)
        # don't want to make calling load() necessary for blank projects
        if self.uri:
            self._loaded = False
        else:
            self._loaded = True


    def load(self):
        """ call this to load a project from a file (once) """
        if self._loaded:
            # should this return false? 
            return True
        return self._load()
        
    def _load(self):
        """ loads the project from a file """
        if self.timeline:
            return
        self.timeline = Timeline(self)
        if self.uri:
            if file_is_project(self.uri):
                loader = ProjectSaver.newProjectSaver("pickle")
                path = gst.uri_get_location(self.uri)
                fileobj = open(path, "w")
                try:
                    tree = loader.deserialize(fileobj)
                    self.fromDataType(tree)
                except ProjectLoadError:
                    return False
                fileobj.close()

    def getBin(self):
        """ returns the SmartTimelineBin of the project """
        if not self.timeline:
            return None
        if not self.timelinebin:
            self.timelinebin = SmartTimelineBin(self)
        return self.timelinebin

    def _save(self):
        """ internal save function """
        if uri_is_valid(self.uri):
            path = gst.uri_get_location(self.uri)
        else:
            return False
        #TODO: a bit more sophisticated overwite detection
        if os.path.exists(path):
            if not self.emit("confirm-overwrite", self.uri):
                return False
        try:
            # dummy save code for now
            os.system("touch %s" % path)
            self._dirty = False
            return True
        except IOError:
            return False

    def save(self):
        """ Saves the project to the project's current file """
        if not self.uri:
            uri = self.emit("save-uri-requested")
            if not uri:
                return False
            self.uri = uri
        return self._save()

    def saveAs(self):
        """ Saves the project to the given file name """
        uri = self.emit("save-uri-requested")
        if not uri:
            return False
        self.uri = uri
        return self._save()

    # setting methods
    def _settingsChangedCb(self, unused_settings):
        self.emit('settings-changed')

    def getSettings(self):
        """
        return the currently configured settings.
        If no setting have been explicitely set, some smart settings will be
        chosen.
        """
        return self.settings or self.getAutoSettings()

    def setSettings(self, settings):
        """
        Sets the given settings as the project's settings.
        If settings is None, the current settings will be unset
        """
        gst.log("Setting %s as the project's settings" % settings)
        if self.settings:
            self.settings.disconnect(self.settingssigid)
        self.settings = settings
        self.emit('settings-changed')
        self.settingssigid = self.settings.connect('settings-changed', 
            self._settingsChangedCb)

    def unsetSettings(self, unused_settings):
        """ Remove the currently configured settings."""
        self.setSettings(None)

    def getAutoSettings(self):
        """
        Computes and returns smart settings for the project.
        If the project only has one source, it will be that source's settings.
        If it has more than one, it will return the largest setting that suits
        all contained sources.
        """
        if not self.timeline:
            gst.warning("project doesn't have a timeline, returning default settings")
            return ExportSettings()
        settings = self.timeline.getAutoSettings()
        if not settings:
            gst.warning("Timeline didn't return any auto settings, return default settings")
            return ExportSettings()

        # add the encoders and muxer of the default settings
        curset = self.settings or ExportSettings()
        settings.vencoder = curset.vencoder
        settings.aencoder = curset.aencoder
        settings.muxer = curset.muxer
        return settings

    def setModificationState(self, state):
        self._dirty = state

    def hasUnsavedModifications(self):
        return self._dirty

    # Serializable methods

    def toDataFormat(self):
        ret = Serializable.toDataFormat(self)
        ret["name"] = self.name
        ret["settings"] = self.getSettings().toDataFormat()
        ret["sources"] = self.sources.toDataFormat()
        ret["timeline"] = self.timeline.toDataFormat()
        return ret

    def fromDataFormat(self, obj):
        Serializable.fromDataFormat(self, obj)
        self.name = obj["name"]
        self.timeline = to_object_from_data_type(obj["timeline"])
        self.sources = to_object_from_data_type(obj["sources"])
        self.settings = to_object_from_data_type(obj["settings"])

def uri_is_valid(uri):
    return gst.uri_get_protocol(uri) == "file"

def file_is_project(uri):
    """ returns True if the given uri is a PitiviProject file"""
    if not uri_is_valid(uri):
        raise NotImplementedError(
            _("%s doesn't yet handle non local projects") % APPNAME)
    return os.path.isfile(gst.uri_get_location(uri))
