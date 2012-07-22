# PiTiVi , Non-linear video editor
#
#       settings.py
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

import os
import gst
from ConfigParser import SafeConfigParser, ParsingError
import xdg.BaseDirectory as xdg_dirs  # Freedesktop directories spec

from pitivi.utils.signal import Signallable
from pitivi.render import available_combinations, get_compatible_sink_caps
from pitivi.utils.loggable import Loggable


def get_bool_env(var):
    value = os.getenv(var)
    if not value:
        return False
    value = value.lower()
    if value == 'False':
        return False
    if value == '0':
        return False
    else:
        return bool(value)


def get_env_by_type(type_, var):
    """
    Returns the environment variable.

    @arg type_: The type of the variable
    @type type_: C{type}
    @arg var: The name of the environment variable.
    @type var: C{str}
    @returns: Contents of the environment variable, or C{None} if it doesn't exist.
    """
    if var is None:
        return None
    if type_ == bool:
        return get_bool_env(var)
    value = os.getenv(var)
    if value:
        return type_(os.getenv(var))
    return None


def get_env_default(var, default):
    value = os.getenv(var)
    if value:
        return value
    return default


def get_dir(path, autocreate=True):
    if autocreate and not os.path.exists(path):
        os.makedirs(path)
    return path


def get_dirs(glob):
    return [d for d in glob.split(os.path.pathsep) if os.path.exists(d)]


def get_env_dir(var, default, autocreate=True):
    return get_dir(get_env_default(var, default))


def get_env_dirs(var, default):
    return get_dirs(get_env_default(var, default))


def xdg_config_home(autocreate=True):
    """Get the directory for storing the user's pitivi configuration"""
    return get_dir(os.path.join(xdg_dirs.xdg_config_home, "pitivi"), autocreate)


def xdg_data_home(autocreate=True):
    """Get the directory for storing the user's data: presets, plugins, etc."""
    return get_dir(os.path.join(xdg_dirs.xdg_data_home, "pitivi"), autocreate)


def xdg_cache_home(autocreate=True):
    """Get the user cache directory"""
    return get_dir(os.path.join(xdg_dirs.xdg_cache_home, "pitivi"), autocreate)


def xdg_data_dirs():
    return get_env_dirs(xdg_dirs.xdg_data_dirs)


def xdg_config_dirs():
    return get_env_dirs(xdg_dirs.xdg_config_dirs)


class ConfigError(Exception):
    pass


class Notification(object):

    """A descriptor to help with the implementation of signals"""

    def __init__(self, attrname):
        self.attrname = "_" + attrname
        self.signame = attrname + "Changed"

    def __get__(self, instance, unused):
        return getattr(instance, self.attrname)

    def __set__(self, instance, value):
        setattr(instance, self.attrname, value)
        instance.emit(self.signame)


class GlobalSettings(Signallable):
    """
    Global PiTiVi settings.

    The settings object loads settings from three different sources: the
    global configuration, the local configuration file, and the environment.
    Modules declare which settings they wish to access by calling the
    addConfigOption() class method during initialization.

    @cvar options: A dictionnary of available settings.
    @cvar environment: A list of the controlled environment variables.
    """

    options = {}
    environment = set()
    defaults = {}
    __signals__ = {}

    def __init__(self, **kwargs):
        Signallable.__init__(self)
        self._config = SafeConfigParser()
        self._readSettingsFromGlobalConfiguration()
        self._readSettingsFromConfigurationFile()
        self._readSettingsFromEnvironmentVariables()

    def _readSettingsFromGlobalConfiguration(self):
        # ideally, this should read settings from GConf for ex
        pass

    def _readSettingsFromConfigurationFile(self):
        # This reads the configuration from the user configuration file
        try:
            conf_file_path = os.path.join(xdg_config_home(), "pitivi.conf")
            self._config.read(conf_file_path)
        except ParsingError:
            return

        for (section, attrname, typ, key, env, value) in self.iterAllOptions():
            if not self._config.has_section(section):
                continue
            if key and self._config.has_option(section, key):
                if typ == int or typ == long:
                    try:
                        value = self._config.getint(section, key)
                    except ValueError:
                        # In previous configurations we incorrectly stored
                        # ints using float values.
                        value = int(self._config.getfloat(section, key))
                elif typ == float:
                    value = self._config.getfloat(section, key)
                elif typ == bool:
                    value = self._config.getboolean(section, key)
                else:
                    value = self._config.get(section, key)
                setattr(self, attrname, value)

    def _readSettingsFromEnvironmentVariables(self):
        for (section, attrname, typ, key, env, value) in self.iterAllOptions():
            var = get_env_by_type(typ, env)
            if var is not None:
                setattr(self, attrname, value)

    def _writeSettingsToConfigurationFile(self):
        conf_file_path = os.path.join(xdg_config_home(), "pitivi.conf")

        for (section, attrname, typ, key, env_var, value) in self.iterAllOptions():
            if not self._config.has_section(section):
                self._config.add_section(section)
            if key:
                if value is not None:
                    self._config.set(section, key, str(value))
                else:
                    self._config.remove_option(section, key)
        try:
            file = open(conf_file_path, 'w')
        except IOError, OSError:
            return
        self._config.write(file)
        file.close()

    def storeSettings(self):
        """
        Write settings to the user's local configuration file. Note that only
        those settings which were added with a section and a key value are
        stored.
        """
        self._writeSettingsToConfigurationFile()

    def iterAllOptions(self):
        """
        Iterate over all registered options

        @return: an iterator which yields a tuple of (attrname, type, key,
        environment, value for each option)
        """
        for section, options in self.options.iteritems():
            for attrname, (typ, key, environment) in options.iteritems():
                yield section, attrname, typ, key, environment, getattr(self, attrname)

    def isDefault(self, attrname):
        return getattr(self, attrname) == self.defaults[attrname]

    def setDefault(self, attrname):
        setattr(self, attrname, self.defaults[attrname])

    @classmethod
    def addConfigOption(cls, attrname, type_=None, section=None, key=None,
        environment=None, default=None, notify=False,):
        """
        Add a configuration option.

        This function should be called during module initialization, before
        the config file is read. Only options registered before the config
        file is read will be loaded.

        See mainwindow.py and medialibrary.py for examples of usage.

        @param attrname: the attribute of this class which represents the option
        @type attrname: C{str}
        @param type_: type of the attribute. Unnecessary if default is given.
        @type type_: a builtin or class
        @param section: The section of the config file under which this option is
        saved. This section must have been added with addConfigSection(). Not
        necessary if key is not given.
        @param key: the key under which this option is to be saved. Can be none if
        this option should not be saved.
        @type key: C{str}
        @param notify: whether or not this attribute should emit notification
        signals when modified (default is False).
        @type notify: C{boolean}
        """
        if section and not section in cls.options:
            raise ConfigError("You must add the section \"%s\" first." % section)
        if key and not section:
            raise ConfigError("You must specify a section for key \"%s\"" % key)
        if section and key in cls.options[section]:
            raise ConfigError("Option \"%s\" is already in use.")
        if hasattr(cls, attrname):
            raise ConfigError("Settings attribute \"%s\" is already in use.")
        if environment and environment in cls.environment:
            raise ConfigError("Settings environment varaible \"%s\" is"
                "already in use.")
        if not type_ and default == None:
            raise ConfigError("Settings attribute \"%s\" has must have a"
                " type or a default." % attrname)
        if not type_:
            type_ = type(default)
        if notify:
            setattr(cls, attrname, Notification(attrname))
            setattr(cls, "_" + attrname, default)
            cls.__signals__[attrname + 'Changed'] = []
        else:
            setattr(cls, attrname, default)
        if section and key:
            cls.options[section][attrname] = type_, key, environment
        cls.environment.add(environment)
        cls.defaults[attrname] = default

    @classmethod
    def addConfigSection(cls, section):
        """
        Add a section to the local config file.

        @param section: The section name. This section must not already exist.
        @type section: C{str}
        """
        if section in cls.options:
            raise ConfigError("Duplicate Section \"%s\"." % section)
        cls.options[section] = {}


class MultimediaSettings(Signallable, Loggable):
    """
    Multimedia rendering and previewing settings

    Signals:
    'settings-changed' : the settings have changed
    'encoders-changed' : The encoders or muxer have changed

    @ivar render_scale: The scale to be applied to the video width and height
    when rendering.
    @type render_scale: int
    """
    __signals__ = {
        "settings-changed": None,
        "encoders-changed": None,
        }

    # Audio/Video settings for processing/export

    # TODO : Add PAR/DAR for video
    # TODO : switch to using GstFraction internally where appliable

    muxers, aencoders, vencoders = available_combinations()

    def __init__(self, **unused_kw):
        Loggable.__init__(self)
        self.videowidth = 720
        self.videoheight = 576
        self.render_scale = 100
        self.videorate = gst.Fraction(25, 1)
        self.videopar = gst.Fraction(16, 15)
        self.audiochannels = 2
        self.audiorate = 44100
        self.audiodepth = 16
        self.vencoder = None
        self.aencoder = None
        self.muxer = "oggmux"
        # A (muxer -> containersettings) map.
        self._containersettings_cache = {}
        # A (vencoder -> vcodecsettings) map.
        self._vcodecsettings_cache = {}
        # A (aencoder -> acodecsettings) map.
        self._acodecsettings_cache = {}

    def copy(self):
        ret = MultimediaSettings()
        ret.videowidth = self.videowidth
        ret.videoheight = self.videoheight
        ret.render_scale = self.render_scale
        ret.videorate = gst.Fraction(self.videorate.num, self.videorate.denom)
        ret.videopar = gst.Fraction(self.videopar.num, self.videopar.denom)
        ret.audiochannels = self.audiochannels
        ret.audiorate = self.audiorate
        ret.audiodepth = self.audiodepth
        ret.vencoder = self.vencoder
        ret.aencoder = self.aencoder
        ret.muxer = self.muxer
        ret.containersettings = dict(self.containersettings)
        ret.acodecsettings = dict(self.acodecsettings)
        ret.vcodecsettings = dict(self.vcodecsettings)
        return ret

    def getDAR(self):
        return gst.Fraction(self.videowidth, self.videoheight) * self.videopar

    def __str__(self):
        """
        Redefine __str__ to allow printing the project audio/video settings.
        This is used for debugging, do not make these strings translatable.
        """
        msg = "\n\n"
        msg += "\tVideo: " + str(self.videowidth) + "x" + str(self.videoheight) +\
               " " + str(self.videorate) + " fps, " + str(self.videopar) + " PAR"
        msg += "\n\t\tEncoder: " + str(self.vencoder)
        if self.vcodecsettings:
            msg += "\n\t\tCodec settings: " + str(self.vcodecsettings)
        msg += "\n\tAudio: " + str(self.audiochannels) + " channels, " +\
                str(self.audiorate) + " Hz, " + str(self.audiodepth) + " bits"
        msg += "\n\t\tEncoder: " + str(self.aencoder)
        if self.acodecsettings:
            msg += "\n\t\tCodec settings: " + str(self.acodecsettings)
        msg += "\n\tMuxer: " + str(self.muxer)
        if self.containersettings:
            msg += "\n\t\t" + str(self.containersettings)
        msg += "\n\n"
        return msg

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
        caps_str = "video/x-raw-yuv,%s;video/x-raw-rgb,%s" % (vstr, vstr)
        video_caps = gst.caps_from_string(caps_str)
        if self.vencoder:
            return get_compatible_sink_caps(self.vencoder, video_caps)
        return video_caps

    def getAudioCaps(self):
        """ Returns the GstCaps corresponding to the audio settings """
        # TODO: Figure out why including 'depth' causes pipeline failures:
        astr = "rate=%d,channels=%d" % (self.audiorate, self.audiochannels)
        caps_str = "audio/x-raw-int,%s;audio/x-raw-float,%s" % (astr, astr)
        audio_caps = gst.caps_from_string(caps_str)
        if self.aencoder:
            return get_compatible_sink_caps(self.aencoder, audio_caps)
        return audio_caps

    def setVideoProperties(self, width=-1, height=-1, framerate=-1, par=-1,
            render_scale=-1):
        """ Set the video width, height and framerate """
        self.info("set_video_props %d x %d @ %r fps", width, height, framerate)
        changed = False
        if not width == -1 and not width == self.videowidth:
            self.videowidth = width
            changed = True
        if not height == -1 and not height == self.videoheight:
            self.videoheight = height
            changed = True
        if not render_scale == -1 and not render_scale == self.render_scale:
            self.render_scale = render_scale
            changed = True
        if not framerate == -1 and not framerate == self.videorate:
            self.videorate = framerate
            changed = True
        if not par == -1 and not par == self.videopar:
            self.videopar = par
            changed = True
        if changed:
            self.emit("settings-changed")

    def setAudioProperties(self, nbchanns=-1, rate=-1, depth=-1):
        """ Set the number of audio channels, rate and depth """
        self.info("%d x %dHz %dbits", nbchanns, rate, depth)
        changed = False
        if not nbchanns == -1 and not nbchanns == self.audiochannels:
            self.audiochannels = nbchanns
            changed = True
        if not rate == -1 and not rate == self.audiorate:
            self.audiorate = rate
            changed = True
        if not depth == -1 and not depth == self.audiodepth:
            self.audiodepth = depth
            changed = True
        if changed:
            self.emit("settings-changed")

    def setEncoders(self, muxer="", vencoder="", aencoder=""):
        """ Set the video/audio encoder and muxer """
        changed = False
        if not muxer == "" and not muxer == self.muxer:
            self.muxer = muxer
            changed = True
        if not vencoder == "" and not vencoder == self.vencoder:
            self.vencoder = vencoder
            changed = True
        if not aencoder == "" and not aencoder == self.aencoder:
            self.aencoder = aencoder
            changed = True
        if changed:
            self.emit("encoders-changed")

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

    def getAudioEncoders(self):
        """ List audio encoders compatible with the current muxer """
        return self.aencoders[self.muxer]

    def getVideoEncoders(self):
        """ List video encoders compatible with the current muxer """
        return self.vencoders[self.muxer]
