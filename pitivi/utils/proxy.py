# Pitivi video editor
#
#       pitivi/proxying.py
#
# Copyright (c) 2015, Thibault Saunier <tsaunier@gnome.org>
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
import time

from gi.repository import GES
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GstPbutils
from gi.repository import GstTranscoder

from pitivi.configure import get_gstpresets_dir
from pitivi.settings import GlobalSettings
from pitivi.utils.loggable import Loggable

# Make sure gst knowns about our own GstPresets
Gst.preset_set_app_dir(get_gstpresets_dir())


class ProxyingStrategy:
    AUTOMATIC = "automatic"
    ALL = "all"
    NOTHING = "nothing"


GlobalSettings.addConfigSection("proxy")
GlobalSettings.addConfigOption('proxyingStrategy',
                               section='proxy',
                               key='proxying-strategy',
                               default=ProxyingStrategy.AUTOMATIC)
GlobalSettings.addConfigOption('numTranscodingJobs',
                               section='proxy',
                               key='num-proxying-jobs',
                               default=4)


ENCODING_FORMAT_PRORES = "prores-opus-in-matroska.gep"
ENCODING_FORMAT_JPEG = "jpeg-opus-in-matroska.gep"


def createEncodingProfileSimple(container_caps, audio_caps, video_caps):
    c = GstPbutils.EncodingContainerProfile.new(None, None,
                                                Gst.Caps(container_caps),
                                                None)
    a = GstPbutils.EncodingAudioProfile.new(Gst.Caps(audio_caps),
                                            None, None, 0)
    v = GstPbutils.EncodingVideoProfile.new(Gst.Caps(video_caps),
                                            None, None, 0)

    c.add_profile(a)
    c.add_profile(v)

    return c


class ProxyManager(GObject.Object, Loggable):
    """
    Transcodes assets and manages proxies
    """
    __gsignals__ = {
        "progress": (GObject.SIGNAL_RUN_LAST, None, (object, int, int)),
        "proxy-ready": (GObject.SIGNAL_RUN_LAST, None, (object, object)),
        "asset-preparing-cancelled": (GObject.SIGNAL_RUN_LAST, None, (object,)),
        "error-preparing-asset": (GObject.SIGNAL_RUN_LAST, None, (object,
                                                                  object,
                                                                  object)),
    }

    WHITELIST_FORMATS = []
    for container in ["video/quicktime", "application/ogg",
                      "video/x-matroska", "video/webm"]:
        for audio in ["audio/mpeg", "audio/x-vorbis",
                      "audio/x-raw", "audio/x-flac"]:
            for video in ["video/x-h264", "image/jpeg",
                          "video/x-raw", "video/x-vp8",
                          "video/x-theora"]:
                WHITELIST_FORMATS.append(createEncodingProfileSimple(
                    container, audio, video))

    def __init__(self, app):
        GObject.Object.__init__(self)
        Loggable.__init__(self)

        self.app = app
        self._total_time_to_transcode = 0
        self._total_transcoded_time = 0
        self._start_proxying_time = 0
        self._estimated_time = 0
        self.proxy_extension = "proxy.mkv"
        self.__running_transcoders = []
        self.__pending_transcoders = []

        self.proxyingUnsupported = False
        for encoding_format in [ENCODING_FORMAT_JPEG, ENCODING_FORMAT_PRORES]:
            self.__encoding_profile = self.__getEncodingProfile(encoding_format)
            if self.__encoding_profile:
                self.info("Using %s as proxying format", encoding_format)
                break

        if not self.__encoding_profile:
            self.proxyingUnsupported = True

            self.error("Not supporting any proxy formats!")
            return

    def _assetMatchesEncodingFormat(self, asset, encoding_profile):
        def capsMatch(info, profile):
            return not info.get_caps().intersect(profile.get_format()).is_empty()

        info = asset.get_info()
        container = info.get_stream_info()
        if container:
            if not capsMatch(container, encoding_profile):
                return False

        for profile in encoding_profile.get_profiles():
            if isinstance(profile, GstPbutils.EncodingAudioProfile):
                audios = info.get_audio_streams()
                for audio_stream in audios:
                    if not capsMatch(audio_stream, profile):
                        return False
            elif isinstance(profile, GstPbutils.EncodingVideoProfile):
                videos = info.get_video_streams()
                for video_stream in videos:
                    if not capsMatch(video_stream, profile):
                        return False
        return True

    def __getEncodingProfile(self, encoding_target_file):
        encoding_target = GstPbutils.EncodingTarget.load_from_file(
            os.path.join(get_gstpresets_dir(), encoding_target_file))
        encoding_profile = encoding_target.get_profile("default")

        if not encoding_profile:
            return None

        for profile in encoding_profile.get_profiles():
            if not Gst.ElementFactory.list_filter(
                Gst.ElementFactory.list_get_elements(
                    Gst.ELEMENT_FACTORY_TYPE_ENCODER, Gst.Rank.MARGINAL),
                    profile.get_format(), Gst.PadDirection.SRC, False):
                return None
            if not Gst.ElementFactory.list_filter(
                Gst.ElementFactory.list_get_elements(
                    Gst.ELEMENT_FACTORY_TYPE_DECODER, Gst.Rank.MARGINAL),
                    profile.get_format(), Gst.PadDirection.SINK, False):
                return None
        return encoding_profile

    def isProxyAsset(self, obj):
        if isinstance(obj, GES.Asset):
            uri = obj.props.id
        else:
            uri = obj

        return uri.endswith("." + self.proxy_extension)

    def checkProxyLoadingSucceeded(self, proxy):
        if self.isProxyAsset(proxy):
            return True

        self.emit("error-preparing-asset", None, proxy, proxy.get_error())
        return False

    def getTargetUri(self, proxy_asset):
        return ".".join(proxy_asset.props.id.split(".")[:-3])

    def getProxyUri(self, asset):
        """
        Returns the URI of a possible proxy file. The name looks like:
            <filename>.<file_size>.<proxy_extension>
        """
        asset_file = Gio.File.new_for_uri(asset.get_id())
        file_size = asset_file.query_info(Gio.FILE_ATTRIBUTE_STANDARD_SIZE,
                                          Gio.FileQueryInfoFlags.NONE,
                                          None).get_size()

        return "%s.%s.%s" % (asset.get_id(), file_size, self.proxy_extension)

    def isAssetFormatWellSupported(self, asset):
        for encoding_format in self.WHITELIST_FORMATS:
            if self._assetMatchesEncodingFormat(asset, encoding_format):
                self.info("Automatically not proxying")
                return True

        return False

    def __assetNeedsTranscoding(self, asset, force_proxying=False):
        if self.proxyingUnsupported:
            self.info("No proxying supported")
            return False

        if asset.is_image():
            return False

        if force_proxying:
            self.info("Forcing proxy creation")
            return True

        if self.app.settings.proxyingStrategy == ProxyingStrategy.NOTHING:
            self.debug("Not proxying anything. %s",
                       self.app.settings.proxyingStrategy)
            return False

        if self.app.settings.proxyingStrategy == ProxyingStrategy.AUTOMATIC \
                and not self.isProxyAsset(asset) and \
                self.isAssetFormatWellSupported(asset):
            return False

        if not self._assetMatchesEncodingFormat(asset, self.__encoding_profile):
            return True

        self.info("%s does not need proxy", asset.get_id())
        return False

    def __startTranscoder(self, transcoder):
        self.debug("Starting %s", transcoder.props.src_uri)
        if self._start_proxying_time == 0:
            self._start_proxying_time = time.time()
        transcoder.run_async()
        self.__running_transcoders.append(transcoder)

    def __assetsMatch(self, asset, proxy):
        if self.__assetNeedsTranscoding(proxy):
            return False

        info = asset.get_info()
        if info.get_duration() != asset.get_duration():
            return False

        return True

    def __assetLoadedCb(self, proxy, res, asset, transcoder):
        try:
            GES.Asset.request_finish(res)
        except GLib.Error as e:
            if transcoder:
                self.emit("error-preparing-asset", asset, proxy, e)
                del transcoder
            else:
                self.__createTranscoder(asset)

            return

        if not transcoder:
            if not self.__assetsMatch(asset, proxy):
                return self.__createTranscoder(asset)
        else:
            transcoder.props.pipeline.props.video_filter.finalize(proxy)
            transcoder.props.pipeline.props.audio_filter.finalize(proxy)

            del transcoder

        self.emit("proxy-ready", asset, proxy)
        self.__emitProgress(proxy, 100)

    def __transcoderErrorCb(self, transcoder, error, asset):
        self.emit("error-preparing-asset", asset, None, error)

    def __transcoderDoneCb(self, transcoder, asset):
        transcoder.disconnect_by_func(self.__transcoderDoneCb)
        transcoder.disconnect_by_func(self.__transcoderErrorCb)
        transcoder.disconnect_by_func(self.__proxyingPositionChangedCb)

        self.debug("Transcoder done with %s", asset.get_id())

        self.__running_transcoders.remove(transcoder)

        proxy_uri = self.getProxyUri(asset)
        os.rename(Gst.uri_get_location(transcoder.props.dest_uri),
                  Gst.uri_get_location(proxy_uri))

        # Make sure that if it first failed loading, the proxy is forced to be
        # reloaded in the GES cache.
        GES.Asset.needs_reload(GES.UriClip, proxy_uri)
        GES.Asset.request_async(GES.UriClip, proxy_uri, None,
                                self.__assetLoadedCb, asset, transcoder)

        try:
            self.__startTranscoder(self.__pending_transcoders.pop())
        except IndexError:
            if not self.__running_transcoders:
                self._total_transcoded_time = 0
                self._total_time_to_transcode = 0
                self._start_proxying_time = 0

    def __emitProgress(self, asset, progress):
        if self._total_transcoded_time:
            time_spent = time.time() - self._start_proxying_time
            self._estimated_time = max(
                0, (time_spent * self._total_time_to_transcode /
                    self._total_transcoded_time) - time_spent)
        else:
            self._estimated_time = 0

        asset.creation_progress = progress
        self.emit("progress", asset, asset.creation_progress,
                  self._estimated_time)

    def __proxyingPositionChangedCb(self, transcoder, position, asset):
        # Do not set to >= 100 as we need to notify about the proxy first
        self._total_transcoded_time -= (asset.creation_progress * (asset.get_duration() /
                                                                   Gst.SECOND)) / 100
        self._total_transcoded_time += position / Gst.SECOND

        if transcoder.props.duration:
            asset.creation_progress = max(
                0, min(99, (position / transcoder.props.duration) * 100))

        self.__emitProgress(asset, asset.creation_progress)

    def __assetQueued(self, asset):
        all_transcoders = self.__running_transcoders + self.__pending_transcoders
        for transcoder in all_transcoders:
            if asset.props.id == transcoder.props.src_uri:
                return True

        return False

    def __createTranscoder(self, asset):
        self._total_time_to_transcode += asset.get_duration() / Gst.SECOND
        asset_uri = asset.get_id()
        proxy_uri = self.getProxyUri(asset)

        dispatcher = GstTranscoder.TranscoderGMainContextSignalDispatcher.new()
        transcoder = GstTranscoder.Transcoder.new_full(
            asset_uri, proxy_uri + ".part", self.__encoding_profile,
            dispatcher)
        transcoder.props.position_update_interval = 1000

        thumbnailbin = Gst.ElementFactory.make("teedthumbnailbin")
        thumbnailbin.props.uri = asset.get_id()

        waveformbin = Gst.ElementFactory.make("waveformbin")
        waveformbin.props.uri = asset.get_id()
        waveformbin.props.duration = asset.get_duration()

        transcoder.props.pipeline.props.video_filter = thumbnailbin
        transcoder.props.pipeline.props.audio_filter = waveformbin

        transcoder.set_cpu_usage(10)
        transcoder.connect("position-updated",
                           self.__proxyingPositionChangedCb,
                           asset)

        transcoder.connect("done", self.__transcoderDoneCb, asset)
        transcoder.connect("error", self.__transcoderErrorCb, asset)
        if len(self.__running_transcoders) < self.app.settings.numTranscodingJobs:
            self.__startTranscoder(transcoder)
        else:
            self.__pending_transcoders.append(transcoder)

    def cancelJob(self, asset):
        if not self.__assetQueued(asset):
            return

        for transcoder in self.__running_transcoders:
            if asset.props.id == transcoder.props.src_uri:
                self.__running_transcoders.remove(transcoder)
                self.info("Cancelling running transcoder %s %s",
                          transcoder.props.src_uri,
                          transcoder.__grefcount__)
                self.emit("asset-preparing-cancelled", asset)
                return

        for transcoder in self.__pending_transcoders:
            if asset.props.id == transcoder.props.src_uri:
                # Removing the transcoder from the list
                # will lead to its destruction (only reference)
                # here, which means it will be stopped.
                self.__pending_transcoders.remove(transcoder)
                self.emit("asset-preparing-cancelled", asset)
                self.info("Cancelling pending transcoder %s",
                          transcoder.props.src_uri)
                return

        return

    def addJob(self, asset, force_proxying=False):
        self.debug("Maybe create a proxy for %s (strategy: %s)",
                   asset.get_id(), self.app.settings.proxyingStrategy)

        if not self.__assetNeedsTranscoding(asset, force_proxying):
            self.debug("Not proxying asset (settings.proxyingStrategy: %s,"
                       " proxy support forced: %s disabled: %s)",
                       self.app.settings.proxyingStrategy,
                       force_proxying, self.proxyingUnsupported)

            # Make sure to notify we do not need a proxy for
            # that asset.
            self.emit("proxy-ready", asset, None)
            return True

        if self.__assetQueued(asset):
            return True

        proxy_uri = self.getProxyUri(asset)
        if Gio.File.new_for_uri(proxy_uri).query_exists(None):
            self.debug("Using proxy already generated: %s",
                       proxy_uri)
            GES.Asset.request_async(GES.UriClip,
                                    proxy_uri, None,
                                    self.__assetLoadedCb, asset,
                                    None)
            return True

        self.__createTranscoder(asset)
        return True
