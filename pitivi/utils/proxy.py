# -*- coding: utf-8 -*-
# Pitivi video editor
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
GlobalSettings.addConfigOption("max_cpu_usage",
                               section="proxy",
                               key="max-cpu-usage",
                               default=10)


ENCODING_FORMAT_PRORES = "prores-raw-in-matroska.gep"
ENCODING_FORMAT_JPEG = "jpeg-raw-in-matroska.gep"


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
    """Transcodes assets and manages proxies."""

    __gsignals__ = {
        "progress": (GObject.SignalFlags.RUN_LAST, None, (object, int, int)),
        "proxy-ready": (GObject.SignalFlags.RUN_LAST, None, (object, object)),
        "asset-preparing-cancelled": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "error-preparing-asset": (GObject.SignalFlags.RUN_LAST, None, (object, object, object)),
    }

    WHITELIST_CONTAINER_CAPS = ["video/quicktime", "application/ogg", "application/xges",
                                "video/x-matroska", "video/webm"]
    WHITELIST_AUDIO_CAPS = ["audio/mpeg", "audio/x-vorbis",
                            "audio/x-raw", "audio/x-flac",
                            "audio/x-wav"]
    WHITELIST_VIDEO_CAPS = ["video/x-h264", "image/jpeg",
                            "video/x-raw", "video/x-vp8",
                            "video/x-theora"]

    WHITELIST_FORMATS = []
    for container in WHITELIST_CONTAINER_CAPS:
        for audio in WHITELIST_AUDIO_CAPS:
            for video in WHITELIST_VIDEO_CAPS:
                WHITELIST_FORMATS.append(createEncodingProfileSimple(
                    container, audio, video))

    for audio in WHITELIST_AUDIO_CAPS:
        a = GstPbutils.EncodingAudioProfile.new(Gst.Caps(audio), None, None, 0)
        WHITELIST_FORMATS.append(a)

    proxy_extension = "proxy.mkv"

    def __init__(self, app):
        GObject.Object.__init__(self)
        Loggable.__init__(self)

        self.app = app
        # Total time to transcode in seconds.
        self._total_time_to_transcode = 0
        # Transcoded time per asset in seconds.
        self._transcoded_durations = {}
        self._start_proxying_time = 0
        self.__running_transcoders = []
        self.__pending_transcoders = []

        self.__encoding_target_file = None
        self.proxyingUnsupported = False
        for encoding_format in [ENCODING_FORMAT_JPEG, ENCODING_FORMAT_PRORES]:
            self.__encoding_profile = self.__getEncodingProfile(encoding_format)
            if self.__encoding_profile:
                self.__encoding_target_file = encoding_format
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
        if isinstance(encoding_profile, GstPbutils.EncodingAudioProfile):
            if isinstance(info.get_stream_info(), GstPbutils.DiscovererContainerInfo):
                return False
            audios = info.get_audio_streams()
            if len(audios) != 1 or not capsMatch(audios[0], encoding_profile):
                return False
            if info.get_video_streams():
                return False
            return True

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

    def __getEncodingProfile(self, encoding_target_file, asset=None):
        encoding_target = GstPbutils.EncodingTarget.load_from_file(
            os.path.join(get_gstpresets_dir(), encoding_target_file))
        encoding_profile = encoding_target.get_profile("default")

        if not encoding_profile:
            return None

        for profile in encoding_profile.get_profiles():
            profile_format = profile.get_format()
            # Do not verify we have an encoder/decoder for raw audio/video,
            # as they are not required.
            if profile_format.intersect(Gst.Caps("audio/x-raw(ANY)")) or \
                    profile_format.intersect(Gst.Caps("audio/x-video(ANY)")):
                continue
            if not Gst.ElementFactory.list_filter(
                Gst.ElementFactory.list_get_elements(
                    Gst.ELEMENT_FACTORY_TYPE_ENCODER, Gst.Rank.MARGINAL),
                    profile_format, Gst.PadDirection.SRC, False):
                return None
            if not Gst.ElementFactory.list_filter(
                Gst.ElementFactory.list_get_elements(
                    Gst.ELEMENT_FACTORY_TYPE_DECODER, Gst.Rank.MARGINAL),
                    profile_format, Gst.PadDirection.SINK, False):
                return None

        if asset:
            # If we have an asset, we force audioconvert to keep
            # the number of channels
            # TODO: remove once https://bugzilla.gnome.org/show_bug.cgi?id=767226
            # is fixed
            info = asset.get_info()
            try:
                # TODO Be smarter about multiple streams
                audio_stream = info.get_audio_streams()[0]
                channels = audio_stream.get_channels()
                audio_profile = [
                    profile for profile in encoding_profile.get_profiles()
                    if isinstance(profile, GstPbutils.EncodingAudioProfile)][0]
                audio_profile.set_restriction(Gst.Caps.from_string(
                    "audio/x-raw,channels=%d" % channels))
            except IndexError:
                pass

        return encoding_profile

    @classmethod
    def is_proxy_asset(cls, obj):
        if isinstance(obj, GES.Asset):
            uri = obj.props.id
        else:
            uri = obj

        return uri.endswith("." + cls.proxy_extension)

    def checkProxyLoadingSucceeded(self, proxy):
        if self.is_proxy_asset(proxy):
            return True

        self.emit("error-preparing-asset", None, proxy, proxy.get_error())
        return False

    def getTargetUri(self, proxy_asset):
        return ".".join(proxy_asset.props.id.split(".")[:-3])

    def getProxyUri(self, asset):
        """Returns the URI of a possible proxy file.

        The name looks like:
            <filename>.<file_size>.<proxy_extension>
        """
        asset_file = Gio.File.new_for_uri(asset.get_id())
        try:
            file_size = asset_file.query_info(Gio.FILE_ATTRIBUTE_STANDARD_SIZE,
                                              Gio.FileQueryInfoFlags.NONE,
                                              None).get_size()
        except GLib.Error as err:
            if err.matches(Gio.io_error_quark(), Gio.IOErrorEnum.NOT_FOUND):
                return None
            else:
                raise

        return "%s.%s.%s" % (asset.get_id(), file_size, self.proxy_extension)

    def isAssetFormatWellSupported(self, asset):
        for encoding_format in self.WHITELIST_FORMATS:
            if self._assetMatchesEncodingFormat(asset, encoding_format):
                self.info("Automatically not proxying")
                return True

        return False

    def __assetNeedsTranscoding(self, asset):
        if self.proxyingUnsupported:
            self.info("No proxying supported")
            return False

        if asset.is_image():
            return False

        if self.app.settings.proxyingStrategy == ProxyingStrategy.NOTHING:
            self.debug("Not proxying anything. %s",
                       self.app.settings.proxyingStrategy)
            return False

        if self.app.settings.proxyingStrategy == ProxyingStrategy.AUTOMATIC \
                and not self.is_proxy_asset(asset) and \
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

        if asset.get_info().get_duration() != proxy.get_info().get_duration():
            self.error(
                "Asset %s (duration=%s) and created proxy %s (duration=%s) do not"
                " have the same duration this should *never* happen, please file"
                " a bug with the media files." % (
                    asset.get_id(), Gst.TIME_ARGS(asset.get_info().get_duration()),
                    proxy.get_id(), Gst.TIME_ARGS(proxy.get_info().get_duration())
                )
            )

        self.emit("proxy-ready", asset, proxy)
        self.__emitProgress(proxy, 100)

    def __transcoderErrorCb(self, transcoder, error, unused_details, asset):
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
                self._transcoded_durations = {}
                self._total_time_to_transcode = 0
                self._start_proxying_time = 0

    def __emitProgress(self, asset, creation_progress):
        """Handles the transcoding progress of the specified asset."""
        if self._transcoded_durations:
            time_spent = time.time() - self._start_proxying_time
            transcoded_seconds = sum(self._transcoded_durations.values())
            remaining_seconds = max(0, self._total_time_to_transcode - transcoded_seconds)
            estimated_time = remaining_seconds * time_spent / transcoded_seconds
        else:
            estimated_time = 0

        asset.creation_progress = creation_progress
        self.emit("progress", asset, asset.creation_progress, estimated_time)

    def __proxyingPositionChangedCb(self, transcoder, position, asset):
        if transcoder not in self.__running_transcoders:
            self.info("Position changed after job cancelled!")
            return

        self._transcoded_durations[asset] = position / Gst.SECOND

        duration = transcoder.props.duration
        if duration <= 0 or duration == Gst.CLOCK_TIME_NONE:
            duration = asset.props.duration
        if duration > 0 and duration != Gst.CLOCK_TIME_NONE:
            creation_progress = 100 * position / duration
            # Do not set to >= 100 as we need to notify about the proxy first.
            asset.creation_progress = max(0, min(creation_progress, 99))

        self.__emitProgress(asset, asset.creation_progress)

    def is_asset_queued(self, asset):
        """Returns whether the specified asset is queued for transcoding.

        Args:
            asset (GES.Asset): The asset to check.

        Returns:
            bool: True iff the asset is being transcoded or pending.
        """
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
        encoding_profile = self.__getEncodingProfile(self.__encoding_target_file, asset)
        transcoder = GstTranscoder.Transcoder.new_full(
            asset_uri, proxy_uri + ".part", encoding_profile,
            dispatcher)
        transcoder.props.position_update_interval = 1000

        thumbnailbin = Gst.ElementFactory.make("teedthumbnailbin")
        thumbnailbin.props.uri = asset.get_id()

        waveformbin = Gst.ElementFactory.make("waveformbin")
        waveformbin.props.uri = asset.get_id()
        waveformbin.props.duration = asset.get_duration()

        transcoder.props.pipeline.props.video_filter = thumbnailbin
        transcoder.props.pipeline.props.audio_filter = waveformbin

        transcoder.set_cpu_usage(self.app.settings.max_cpu_usage)
        transcoder.connect("position-updated",
                           self.__proxyingPositionChangedCb,
                           asset)

        transcoder.connect("done", self.__transcoderDoneCb, asset)
        transcoder.connect("error", self.__transcoderErrorCb, asset)
        if len(self.__running_transcoders) < self.app.settings.numTranscodingJobs:
            self.__startTranscoder(transcoder)
        else:
            self.__pending_transcoders.append(transcoder)

    def cancel_job(self, asset):
        """Cancels the transcoding job for the specified asset, if any.

        Args:
            asset (GES.Asset): The original asset.
        """
        if not self.is_asset_queued(asset):
            return

        for transcoder in self.__running_transcoders:
            if asset.props.id == transcoder.props.src_uri:
                self.info("Cancelling running transcoder %s %s",
                          transcoder.props.src_uri,
                          transcoder.__grefcount__)
                self.__running_transcoders.remove(transcoder)
                self.emit("asset-preparing-cancelled", asset)
                return

        for transcoder in self.__pending_transcoders:
            if asset.props.id == transcoder.props.src_uri:
                self.info("Cancelling pending transcoder %s",
                          transcoder.props.src_uri)
                # Removing the transcoder from the list
                # will lead to its destruction (only reference)
                # here, which means it will be stopped.
                self.__pending_transcoders.remove(transcoder)
                self.emit("asset-preparing-cancelled", asset)
                return

    def add_job(self, asset):
        """Adds a transcoding job for the specified asset if needed.

        Args:
            asset (GES.Asset): The asset to be transcoded.
        """
        if self.is_asset_queued(asset):
            self.log("Asset already queued for proxying: %s", asset)
            return

        force_proxying = asset.force_proxying
        if not force_proxying and not self.__assetNeedsTranscoding(asset):
            self.debug("Not proxying asset (proxying disabled: %s)",
                       self.proxyingUnsupported)
            # Make sure to notify we do not need a proxy for that asset.
            self.emit("proxy-ready", asset, None)
            return

        proxy_uri = self.getProxyUri(asset)
        if Gio.File.new_for_uri(proxy_uri).query_exists(None):
            self.debug("Using proxy already generated: %s", proxy_uri)
            GES.Asset.request_async(GES.UriClip,
                                    proxy_uri, None,
                                    self.__assetLoadedCb, asset,
                                    None)
            return

        self.debug("Creating a proxy for %s (strategy: %s, force: %s)",
                   asset.get_id(), self.app.settings.proxyingStrategy,
                   force_proxying)
        self.__createTranscoder(asset)
        return


def get_proxy_target(obj):
    if isinstance(obj, GES.UriClip):
        asset = obj.get_asset()
    elif isinstance(obj, GES.TrackElement):
        asset = obj.get_parent().get_asset()
    else:
        asset = obj

    if ProxyManager.is_proxy_asset(asset):
        target = asset.get_proxy_target()
        if target and target.get_error() is None:
            asset = target

    return asset
