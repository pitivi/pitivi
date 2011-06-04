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

"""
Settings
"""

import os
import platform
import gst
from ConfigParser import SafeConfigParser, ParsingError
import xdg.BaseDirectory as xdg_dirs  # Freedesktop directories spec

from gettext import gettext as _
from gettext import ngettext

from pitivi.signalinterface import Signallable
from pitivi.encode import available_combinations, \
     get_compatible_sink_caps
from pitivi.stream import get_stream_for_caps
from pitivi.log.loggable import Loggable

if platform.system() == 'Windows':
    HOME = 'USERPROFILE'
else:
    HOME = 'HOME'

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
    @returns: The content of the environment variable, or C{None} if it doesn't
    exist.
    """
    if var is None:
        return None
    if type_ == bool:
        return get_bool_env(var)
    else:
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
    return get_dir(xdg_dirs.xdg_config_home, autocreate)

def xdg_data_home(autocreate=True):
    return get_dir(xdg_dirs.xdg_data_home, autocreate)

def xdg_cache_home(autocreate=True):
    return get_dir(xdg_dirs.xdg_cache_home, autocreate)

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
            pitivi_path = self.get_local_settings_path()
            pitivi_conf_file_path = os.path.join(pitivi_path, "pitivi.conf")
            self._config.read(pitivi_conf_file_path)

        except ParsingError:
            return

        for (section, attrname, typ, key, env,
            value) in self.iterAllOptions():
            if not self._config.has_section(section):
                continue
            if key and self._config.has_option(section, key):
                if typ == int or typ == long:
                    # WARNING/FIXME : This try/except is for a small cockup in previous
                    # configurations where we stored a float value... but declared it
                    # as an integer.
                    try:
                        value = self._config.getint(section, key)
                    except ValueError:
                        value = int(self._config.getfloat(section, key))
                elif typ == float:
                    value = self._config.getfloat(section, key)
                elif typ == bool:
                    value = self._config.getboolean(section, key)
                else:
                    value = self._config.get(section, key)
                setattr(self, attrname, value)

    def _readSettingsFromEnvironmentVariables(self):
        for (section, attrname, typ, key, env,
            value) in self.iterAllOptions():
            var = get_env_by_type(typ, env)
            if var is not None:
                setattr(self, attrname, value)

    def _writeSettingsToConfigurationFile(self):
        pitivi_path = self.get_local_settings_path()
        pitivi_conf_file_path = os.path.join(pitivi_path, "pitivi.conf")

        for (section, attrname, typ, key, env_var,
            value) in self.iterAllOptions():
            if not self._config.has_section(section):
                self._config.add_section(section)
            if key:
                if value is not None:
                    self._config.set(section, key, str(value))
                else:
                    self._config.remove_option(section, key)
        try:
            file = open(pitivi_conf_file_path, 'w')
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

    def get_local_settings_path(self, autocreate=True):
        """
        Compute the absolute path to local settings directory

        @param autocreate: create the path if missing
        @return: the plugin repository path
        """

        return get_dir(os.path.join(xdg_config_home(autocreate), "pitivi"),
            autocreate)

    def get_local_plugin_path(self, autocreate=True):
        """
        Compute the absolute path to local plugin repository

        @param autocreate: create the path if missing
        @return: the plugin repository path
        """

        return get_dir(
            os.path.join(
                get_dir(
                    os.path.join(
                        xdg_data_home(autocreate),
                        "pitivi"),
                    autocreate),
                "plugins"),
            autocreate)

    def get_plugin_settings_path(self, autocreate=True):
        """
        Compute the absolute path to local plugin settings' repository

        @param autocreate: create the path if missing
        @return: the plugin settings path
        """

        return get_dir(os.path.join(self.get_local_settings_path(autocreate),
            "plugin-settings"), autocreate)

    def iterAllOptions(self):
        """
        Iterate over all registered options

        @return: an iterator which yields a tuple of (attrname, type, key,
        environment, value for each option)
        """
        for section, options in self.options.iteritems():
            for attrname, (typ, key, environment) in self.options[section].iteritems():
                yield section, attrname, typ, key, environment, getattr(self, attrname)

    def iterSection(self, section):
        """
        Iterate over all registerd options within the given section

        @param section:
        @type section: C{str}
        @return: an iterator which yields a tuple of (attrname, type, key,
        environment, value) for each option
        """
        for attrname, (typ, key, environment) in self.options[section].iteritems():
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

        see pitivi/ui/mainwindow.py, pitivi/ui/sourcelist.py for examples of
        usage.

        @param attrname: the attribute of this class which represents the option
        @type attrname: C{str}
        @param type_: the type of the attribute. not necessary if default is
        given.
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
            raise ConfigError("You must add the section \"%s\" first." %
                section)
        if key and not section:
            raise ConfigError("You must specify a section for key \"%s\"" %
                key)
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

class StreamEncodeSettings(object):
    """
    Settings for encoding a L{MultimediaStream}.

    @ivar encoder: Name of the encoder used to encode this stream. If None, no
    encoder is used and the incoming stream will be outputted directly.
    @type encoder: C{str}
    @ivar input_stream: The type of streams accepted by this settings. If
    None are specified, the stream type will be extracted from the encoder.
    @type input_stream: L{MultimediaStream}
    @ivar output_stream: The type of streams accepted by this settings. If
    None are specified, the stream type will be extracted from the encoder.
    @type output_stream: L{MultimediaStream}
    @ivar encodersettings: Encoder-specific settings.
    @type encodersettings: C{dict}
    """

    def __init__(self, encoder=None, input_stream=None, output_stream=None,
                 encodersettings={}):
        """
        @param encoder: The encoder to use. If None, no encoder is used and the
        incoming stream will be outputted directly.
        @type encoder: C{str}.
        @param input_stream: The type of streams accepted by this settings. If
        None are specified, the stream type will be extracted from the encoder.
        If one is specified, then a L{StreamModifierFactory} will be use to
        conform the incoming stream to the specified L{Stream}.
        @type input_stream: L{MultimediaStream}
        @param output_stream: The type of streams accepted by this settings. If
        None are specified, the stream type will be extracted from the encoder.
        @type output_stream: L{MultimediaStream}
        @param encodersettings: Encoder-specific settings.
        @type encodersettings: C{dict}
        """
        # FIXME : What if we need parsers after the encoder ??
        self.encoder = encoder
        self.input_stream = input_stream
        self.output_stream = output_stream
        self.encodersettings = encodersettings
        self.modifyinput = (input_stream != None)
        self.modifyoutput = (output_stream != None)
        if not self.input_stream or not self.output_stream:
            # extract stream from factory
            for p in gst.registry_get_default().lookup_feature(self.encoder).get_static_pad_templates():
                if p.direction == gst.PAD_SINK and not self.input_stream:
                    self.input_stream = get_stream_for_caps(p.get_caps().copy())
                    self.input_stream.pad_name = p.name_template
                elif p.direction == gst.PAD_SRC and not self.output_stream:
                    self.output_stream = get_stream_for_caps(p.get_caps().copy())
                    self.output_stream.pad_name = p.name_template

    def __str__(self):
        return "<StreamEncodeSettings %s>" % self.encoder

class RenderSettings(object):
    """
    Settings for rendering and multiplexing one or multiple streams.

    @cvar settings: Ordered list of encoding stream settings.
    @type settings: List of L{StreamEncodeSettings}
    @cvar muxer: Name of the muxer to use.
    @type muxer: C{str}
    @cvar muxersettings: Muxer-specific settings.
    @type muxersettings: C{dict}
    """

    def __init__(self, settings=[], muxer=None, muxersettings={}):
        self.settings = settings
        self.muxer = muxer
        self.muxersettings = muxersettings

    def __str__(self):
        return "<RenderSettings %s [%d streams]>" % (self.muxer, len(self.settings))

class ExportSettings(Signallable, Loggable):
    """
    Multimedia export settings

    Signals:

    'settings-changed' : the settings have changed
    'encoders-changed' : The encoders or muxer have changed
    """
    __signals__ = {
        "settings-changed" : None,
        "encoders-changed" : None,
        }

    # Audio/Video settings for processing/export

    # TODO : Add PAR/DAR for video
    # TODO : switch to using GstFraction internally where appliable


    # The following dependant attributes caches are common to all instances!
    # A (muxer -> containersettings) map.
    _containersettings_cache = {}
    # A (vencoder -> vcodecsettings) map.
    _vcodecsettings_cache = {}
    # A (aencoder -> acodecsettings) map.
    _acodecsettings_cache = {}

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
        self.vencoder = "theoraenc"
        self.aencoder = "vorbisenc"
        self.muxer = "oggmux"

    def copy(self):
        ret = ExportSettings()
        ret.videowidth = self.videowidth
        ret.videoheight = self.videoheight
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
        msg = _("Export Settings\n")
        msg += _("Video: ") + str(self.videowidth) + " " + str(self.videoheight) +\
               " " + str(self.videorate) + " " + str(self.videopar)
        msg += "\n\t" + str(self.vencoder) + " " +str(self.vcodecsettings)
        msg += _("\nAudio: ") + str(self.audiochannels) + " " + str(self.audiorate) +\
               " " + str(self.audiodepth)
        msg += "\n\t" + str(self.aencoder) + " " + str(self.acodecsettings)
        msg += _("\nMuxer: ") + str(self.muxer) + " " + str(self.containersettings)
        return msg

    def getVideoWidthAndHeight(self, render=False):
        """ Returns the video width and height as a tuple

        @param render: Whether to apply self.render_scale to the returned
        values.
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
        astr = "width=%d,height=%d,pixel-aspect-ratio=%d/%d,framerate=%d/%d" % (
                videowidth, videoheight,
                self.videopar.num, self.videopar.denom,
                self.videorate.num, self.videorate.denom)
        vcaps = gst.caps_from_string("video/x-raw-yuv,%s;video/x-raw-rgb,%s" % (astr, astr))
        if self.vencoder:
            return get_compatible_sink_caps(self.vencoder, vcaps)
        return vcaps

    def getAudioCaps(self):
        """ Returns the GstCaps corresponding to the audio settings """
        astr = "rate=%d,channels=%d" % (self.audiorate, self.audiochannels)
        astrcaps = gst.caps_from_string("audio/x-raw-int,%s;audio/x-raw-float,%s" % (astr, astr))
        if self.aencoder:
            return get_compatible_sink_caps(self.aencoder, astrcaps)
        return astrcaps

        # interset with current audioencoder sink pad caps

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
        """ Returns the list of audio encoders compatible with the current
        muxer """
        return self.aencoders[self.muxer]

    def getVideoEncoders(self):
        """ Returns the list of video encoders compatible with the current
        muxer """
        return self.vencoders[self.muxer]

def export_settings_to_render_settings(export,
        have_video=True, have_audio=True):
    """Convert the specified ExportSettings object to a RenderSettings object.
    """
    # Get the audio and video caps/encoder/settings
    astream = get_stream_for_caps(export.getAudioCaps())
    vstream = get_stream_for_caps(export.getVideoCaps(render=True))

    encoder_settings = []
    if export.vencoder is not None and have_video:
        vset = StreamEncodeSettings(encoder=export.vencoder,
                                    input_stream=vstream,
                                    encodersettings=export.vcodecsettings)
        encoder_settings.append(vset)

    if export.aencoder is not None and have_audio:
        aset = StreamEncodeSettings(encoder=export.aencoder,
                                    input_stream=astream,
                                    encodersettings=export.acodecsettings)
        encoder_settings.append(aset)

    settings = RenderSettings(settings=encoder_settings,
                              muxer=export.muxer,
                              muxersettings=export.containersettings)
    return settings
