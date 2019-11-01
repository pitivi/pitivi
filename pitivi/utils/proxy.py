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
from fractions import Fraction
from gettext import gettext as _

from gi.repository import GES
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GstPbutils
from gi.repository import GstTranscoder

from pitivi.configure import get_gstpresets_dir
from pitivi.dialogs.prefs import PreferencesDialog
from pitivi.settings import GlobalSettings
from pitivi.utils.loggable import Loggable

# Make sure gst knowns about our own GstPresets
Gst.preset_set_app_dir(get_gstpresets_dir())


class ProxyingStrategy:
    AUTOMATIC = "automatic"
    ALL = "all"
    NOTHING = "nothing"


GlobalSettings.addConfigSection("proxy")
GlobalSettings.addConfigOption('proxying_strategy',
                               section='proxy',
                               key='proxying-strategy',
                               default=ProxyingStrategy.AUTOMATIC)

GlobalSettings.addConfigOption('num_transcoding_jobs',
                               section='proxy',
                               key='num-proxying-jobs',
                               default=4,
                               notify=True)
PreferencesDialog.addNumericPreference('num_transcoding_jobs',
                                       description="",
                                       section="_proxies",
                                       label=_("Max number of parallel transcoding jobs"),
                                       lower=1)

GlobalSettings.addConfigOption("max_cpu_usage",
                               section="proxy",
                               key="max-cpu-usage",
                               default=10,
                               notify=True)
PreferencesDialog.addNumericPreference('max_cpu_usage',
                                       description="",
                                       section="_proxies",
                                       label=_("Max CPU usage dedicated to transcoding"),
                                       lower=1,
                                       upper=100)


GlobalSettings.addConfigOption("auto_scaling_enabled",
                               section="proxy",
                               key="s-proxy-enabled",
                               default=False,
                               notify=True)
GlobalSettings.addConfigOption("default_scaled_proxy_width",
                               section="proxy",
                               key="s-proxy-width",
                               default=1920,
                               notify=True)
GlobalSettings.addConfigOption("default_scaled_proxy_height",
                               section="proxy",
                               key="s-proxy-height",
                               default=1080,
                               notify=True)

ENCODING_FORMAT_PRORES = "prores-raw-in-matroska.gep"
ENCODING_FORMAT_JPEG = "jpeg-raw-in-matroska.gep"


def create_encoding_profile_simple(container_caps, audio_caps, video_caps):
    container_profile = GstPbutils.EncodingContainerProfile.new(None, None,
                                                                Gst.Caps(container_caps),
                                                                None)
    audio_profile = GstPbutils.EncodingAudioProfile.new(Gst.Caps(audio_caps),
                                                        None, None, 0)
    video_profile = GstPbutils.EncodingVideoProfile.new(Gst.Caps(video_caps),
                                                        None, None, 0)

    container_profile.add_profile(audio_profile)
    container_profile.add_profile(video_profile)

    return container_profile


class ProxyManager(GObject.Object, Loggable):
    """Transcodes assets and manages proxies."""

    __gsignals__ = {
        "progress": (GObject.SignalFlags.RUN_LAST, None, (object, int, int)),
        "proxy-ready": (GObject.SignalFlags.RUN_LAST, None, (object, object)),
        "asset-preparing-cancelled": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "error-preparing-asset": (GObject.SignalFlags.RUN_LAST, None, (object, object, object)),
    }

    WHITELIST_CONTAINER_CAPS = ["video/quicktime", "application/ogg", "application/xges",
                                "video/x-matroska", "video/webm", "image/jpeg"]
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
                WHITELIST_FORMATS.append(create_encoding_profile_simple(
                    container, audio, video))

    for audio in WHITELIST_AUDIO_CAPS:
        a = GstPbutils.EncodingAudioProfile.new(Gst.Caps(audio), None, None, 0)
        WHITELIST_FORMATS.append(a)

    hq_proxy_extension = "proxy.mkv"
    scaled_proxy_extension = "scaledproxy.mkv"
    # Suffix for filenames of proxies being created.
    part_suffix = ".part"

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
        # The scaled proxy transcoders waiting for their corresponding shadow
        # HQ proxy transcoder to finish.
        self.__waiting_transcoders = []

        self.__encoding_target_file = None
        self.proxying_unsupported = False
        for encoding_format in [ENCODING_FORMAT_JPEG, ENCODING_FORMAT_PRORES]:
            self.__encoding_profile = self.__getEncodingProfile(encoding_format)
            if self.__encoding_profile:
                self.__encoding_target_file = encoding_format
                self.info("Using %s as proxying format", encoding_format)
                break

        if not self.__encoding_profile:
            self.proxying_unsupported = True

            self.error("Not supporting any proxy formats!")
            return

    def _scale_asset_resolution(self, asset, max_width, max_height):
        stream = asset.get_info().get_video_streams()[0]
        width = stream.get_width()
        height = stream.get_height()
        aspect_ratio = Fraction(width, height)

        if aspect_ratio.numerator >= width or aspect_ratio.denominator >= height:
            self.log("Unscalable aspect ratio.")
            return width, height
        if aspect_ratio.numerator >= max_width or aspect_ratio.denominator >= max_height:
            self.log("Cannot scale to target resolution.")
            return width, height

        if width > max_width or height > max_height:
            width_factor = max_width // aspect_ratio.numerator
            height_factor = max_height // aspect_ratio.denominator
            scaling_factor = min(height_factor, width_factor)

            width = aspect_ratio.numerator * scaling_factor
            height = aspect_ratio.denominator * scaling_factor

        return width, height

    def _asset_matches_encoding_format(self, asset, encoding_profile):
        def caps_match(info, profile):
            return not info.get_caps().intersect(profile.get_format()).is_empty()

        info = asset.get_info()
        if isinstance(encoding_profile, GstPbutils.EncodingAudioProfile):
            if isinstance(info.get_stream_info(), GstPbutils.DiscovererContainerInfo):
                return False
            audios = info.get_audio_streams()
            if len(audios) != 1 or not caps_match(audios[0], encoding_profile):
                return False
            if info.get_video_streams():
                return False
            return True

        container = info.get_stream_info()
        if container:
            if not caps_match(container, encoding_profile):
                return False

        for profile in encoding_profile.get_profiles():
            if isinstance(profile, GstPbutils.EncodingAudioProfile):
                audios = info.get_audio_streams()
                for audio_stream in audios:
                    if not caps_match(audio_stream, profile):
                        return False
            elif isinstance(profile, GstPbutils.EncodingVideoProfile):
                videos = info.get_video_streams()
                for video_stream in videos:
                    if not caps_match(video_stream, profile):
                        return False
        return True

    def __getEncodingProfile(self, encoding_target_file, asset=None, width=None,
                             height=None):
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
            if height and width and profile.get_type_nick() == "video":
                profile.set_restriction(Gst.Caps.from_string(
                    "video/x-raw, width=%d, height=%d" % (width, height)))

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
        return cls.is_scaled_proxy(obj) or cls.is_hq_proxy(obj)

    @classmethod
    def is_scaled_proxy(cls, obj):
        if isinstance(obj, GES.Asset):
            uri = obj.props.id
        else:
            uri = obj

        return uri.endswith("." + cls.scaled_proxy_extension)

    @classmethod
    def is_hq_proxy(cls, obj):
        if isinstance(obj, GES.Asset):
            uri = obj.props.id
        else:
            uri = obj

        return uri.endswith("." + cls.hq_proxy_extension)

    def checkProxyLoadingSucceeded(self, proxy):
        if self.is_proxy_asset(proxy):
            return True

        self.emit("error-preparing-asset", None, proxy, proxy.get_error())
        return False

    @classmethod
    def getTargetUri(cls, obj):
        if isinstance(obj, GES.Asset):
            uri = obj.props.id
        else:
            uri = obj

        if cls.is_scaled_proxy(uri):
            return ".".join(uri.split(".")[:-4])

        return ".".join(uri.split(".")[:-3])

    def getProxyUri(self, asset, scaled=False):
        """Gets the URI of the corresponding proxy file for the specified asset.

        The name looks like:
            <filename>.<file_size>[.<proxy_resolution>].<proxy_extension>

        Returns:
            str: The URI or None if it can't be computed for any reason.
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

        if scaled:
            if not asset.get_info().get_video_streams():
                return None

            max_w = self.app.project_manager.current_project.scaled_proxy_width
            max_h = self.app.project_manager.current_project.scaled_proxy_height
            t_width, t_height = self._scale_asset_resolution(asset, max_w, max_h)
            proxy_res = "%sx%s" % (t_width, t_height)
            return "%s.%s.%s.%s" % (asset.get_id(), file_size, proxy_res,
                                    self.scaled_proxy_extension)
        else:
            return "%s.%s.%s" % (asset.get_id(), file_size,
                                 self.hq_proxy_extension)

    def isAssetFormatWellSupported(self, asset):
        for encoding_format in self.WHITELIST_FORMATS:
            if self._asset_matches_encoding_format(asset, encoding_format):
                self.info("Automatically not proxying")
                return True

        return False

    def asset_matches_target_res(self, asset):
        """Returns whether the asset's size <= the scaled proxy size."""
        stream = asset.get_info().get_video_streams()[0]

        asset_res = (stream.get_width(), stream.get_height())
        target_res = self._scale_asset_resolution(asset,
                                                  self.app.project_manager.current_project.scaled_proxy_width,
                                                  self.app.project_manager.current_project.scaled_proxy_height)

        return asset_res == target_res

    def __assetNeedsTranscoding(self, asset, scaled=False):
        if self.proxying_unsupported:
            self.info("No proxying supported")
            return False

        if asset.is_image():
            return False

        if self.app.settings.proxying_strategy == ProxyingStrategy.NOTHING:
            self.debug("Not proxying anything. %s",
                       self.app.settings.proxying_strategy)
            return False

        if self.app.settings.proxying_strategy == ProxyingStrategy.AUTOMATIC \
                and scaled and not self.asset_matches_target_res(asset):
            return True

        if self.app.settings.proxying_strategy == ProxyingStrategy.AUTOMATIC \
                and not scaled and not self.is_hq_proxy(asset) and \
                self.isAssetFormatWellSupported(asset):
            return False

        if not self._asset_matches_encoding_format(asset, self.__encoding_profile):
            return True

        self.info("%s does not need proxy", asset.get_id())
        return False

    def asset_can_be_proxied(self, asset, scaled=False):
        """Returns whether the asset is not a proxy nor a proper proxy."""
        if asset.is_image():
            return False

        if scaled:
            if not asset.get_info().get_video_streams():
                return False

            return not self.is_scaled_proxy(asset) or \
                self.asset_matches_target_res(asset)
        else:
            return not self.is_hq_proxy(asset)

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

        shadow = transcoder and self._is_shadow_transcoder(transcoder)

        if not transcoder:
            if not self.__assetsMatch(asset, proxy):
                self.__createTranscoder(asset)
                return
        else:
            transcoder.props.pipeline.props.video_filter.finalize()
            transcoder.props.pipeline.props.audio_filter.finalize()

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

        if shadow:
            self.app.project_manager.current_project.finalize_proxy(proxy)
        else:
            self.emit("proxy-ready", asset, proxy)
            self.__emitProgress(proxy, 100)

    def __transcoder_error_cb(self, transcoder, error, unused_details, asset):
        self.emit("error-preparing-asset", asset, None, error)

    def __transcoder_done_cb(self, transcoder, asset):
        transcoder.disconnect_by_func(self.__proxying_position_changed_cb)
        transcoder.disconnect_by_func(self.__transcoder_done_cb)
        transcoder.disconnect_by_func(self.__transcoder_error_cb)

        self.debug("Transcoder done with %s", asset.get_id())

        self.__running_transcoders.remove(transcoder)

        proxy_uri = transcoder.props.dest_uri.rstrip(ProxyManager.part_suffix)
        os.rename(Gst.uri_get_location(transcoder.props.dest_uri),
                  Gst.uri_get_location(proxy_uri))

        shadow = self._is_shadow_transcoder(transcoder)
        second_transcoder = self._get_second_transcoder(transcoder)
        if second_transcoder and not shadow:
            # second_transcoder is the shadow for transcoder.
            # Defer loading until the shadow transcoder finishes.
            self.__waiting_transcoders.append([transcoder, asset])
        else:
            # Make sure that if it first failed loading, the proxy is forced to
            # be reloaded in the GES cache.
            GES.Asset.needs_reload(GES.UriClip, proxy_uri)
            GES.Asset.request_async(GES.UriClip, proxy_uri, None,
                                    self.__assetLoadedCb, asset, transcoder)

        if shadow:
            # Finish deferred loading for waiting scaled proxy transcoder.
            for pair in self.__waiting_transcoders:
                waiting_transcoder, waiting_asset = pair
                if waiting_transcoder.props.src_uri == transcoder.props.src_uri:
                    proxy_uri = waiting_transcoder.props.dest_uri.rstrip(ProxyManager.part_suffix)
                    GES.Asset.needs_reload(GES.UriClip, proxy_uri)
                    GES.Asset.request_async(GES.UriClip, proxy_uri, None,
                                            self.__assetLoadedCb, waiting_asset, waiting_transcoder)

                    self.__waiting_transcoders.remove(pair)
                    break

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

    def __proxying_position_changed_cb(self, transcoder, position, asset):
        if transcoder not in self.__running_transcoders:
            self.info("Position changed after job cancelled!")
            return

        second_transcoder = self._get_second_transcoder(transcoder)
        if second_transcoder is not None:
            position = (position + second_transcoder.props.position) // 2

        self._transcoded_durations[asset] = position / Gst.SECOND

        duration = transcoder.props.duration
        if duration <= 0 or duration == Gst.CLOCK_TIME_NONE:
            duration = asset.props.duration
        if duration > 0 and duration != Gst.CLOCK_TIME_NONE:
            creation_progress = 100 * position / duration
            # Do not set to >= 100 as we need to notify about the proxy first.

            asset.creation_progress = max(0, min(creation_progress, 99))

        self.__emitProgress(asset, asset.creation_progress)

    def _get_second_transcoder(self, transcoder):
        """Gets the shadow of a scaled proxy or the other way around."""
        all_transcoders = self.__running_transcoders + self.__pending_transcoders
        for transcoder2 in all_transcoders:
            if transcoder2.props.position_update_interval == transcoder.props.position_update_interval:
                # Both transcoders are of the same type.
                continue
            if transcoder2.props.src_uri == transcoder.props.src_uri:
                return transcoder2
        return None

    def _is_shadow_transcoder(self, transcoder):
        if transcoder.props.position_update_interval == 1001:
            return True
        return False

    def is_asset_queued(self, asset, optimisation=True, scaling=True):
        """Returns whether the specified asset is queued for transcoding.

        Args:
            asset (GES.Asset): The asset to check.
            optimisation(bool): Whether to check optimisation queue
            scaling(bool): Whether to check scaling queue

        Returns:
            bool: True if the asset is being transcoded or pending.
        """
        all_transcoders = self.__running_transcoders + self.__pending_transcoders
        is_queued = False
        for transcoder in all_transcoders:
            transcoder_uri = transcoder.props.dest_uri
            scaling_ext = "." + self.scaled_proxy_extension + ProxyManager.part_suffix
            optimisation_ext = "." + self.hq_proxy_extension + ProxyManager.part_suffix

            scaling_transcoder = transcoder_uri.endswith(scaling_ext)
            optimisation_transcoder = transcoder_uri.endswith(optimisation_ext)

            if transcoder.props.src_uri == asset.props.id:
                if optimisation and optimisation_transcoder:
                    is_queued = True
                    break

                if scaling and scaling_transcoder:
                    is_queued = True
                    break

        return is_queued

    def __createTranscoder(self, asset, width=None, height=None, shadow=False):
        self._total_time_to_transcode += asset.get_duration() / Gst.SECOND
        asset_uri = asset.get_id()

        if width and height:
            proxy_uri = self.getProxyUri(asset, scaled=True)
        else:
            proxy_uri = self.getProxyUri(asset)

        dispatcher = GstTranscoder.TranscoderGMainContextSignalDispatcher.new()

        enc_profile = self.__getEncodingProfile(self.__encoding_target_file,
                                                asset, width, height)

        transcoder = GstTranscoder.Transcoder.new_full(
            asset_uri, proxy_uri + ProxyManager.part_suffix, enc_profile,
            dispatcher)

        if shadow:
            # Used to identify shadow transcoder
            transcoder.props.position_update_interval = 1001
        else:
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
                           self.__proxying_position_changed_cb,
                           asset)

        transcoder.connect("done", self.__transcoder_done_cb, asset)
        transcoder.connect("error", self.__transcoder_error_cb, asset)

        if len(self.__running_transcoders) < self.app.settings.num_transcoding_jobs:
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

        for transcoder in self.__pending_transcoders:
            if asset.props.id == transcoder.props.src_uri:
                self.info("Cancelling pending transcoder %s",
                          transcoder.props.src_uri)
                # Removing the transcoder from the list
                # will lead to its destruction (only reference)
                # here, which means it will be stopped.
                self.__pending_transcoders.remove(transcoder)
                self.emit("asset-preparing-cancelled", asset)

    def add_job(self, asset, scaled=False, shadow=False):
        """Adds a transcoding job for the specified asset if needed.

        Args:
            asset (GES.Asset): The asset to be transcoded.
        """
        force_proxying = asset.force_proxying
        # Handle Automatic scaling
        if self.app.settings.auto_scaling_enabled and not force_proxying \
                and not shadow and not self.asset_matches_target_res(asset):
            scaled = True

        # Create shadow proxies for unsupported assets
        if not self.isAssetFormatWellSupported(asset) and not \
                self.app.settings.proxying_strategy == ProxyingStrategy.NOTHING \
                and not shadow:
            hq_uri = self.app.proxy_manager.getProxyUri(asset)
            if not Gio.File.new_for_uri(hq_uri).query_exists(None):
                self.add_job(asset, shadow=True)

        if scaled:
            if self.is_asset_queued(asset, optimisation=False):
                self.log("Asset already queued for scaling: %s", asset)
                return

        else:
            if self.is_asset_queued(asset, scaling=False):
                self.log("Asset already queued for optimization: %s", asset)
                return

        if not force_proxying:
            if not self.__assetNeedsTranscoding(asset, scaled):
                self.debug("Not proxying asset (proxying disabled: %s)",
                           self.proxying_unsupported)
                # Make sure to notify we do not need a proxy for that asset.
                self.emit("proxy-ready", asset, None)
                return

        proxy_uri = self.getProxyUri(asset, scaled)
        if Gio.File.new_for_uri(proxy_uri).query_exists(None):
            self.debug("Using proxy already generated: %s", proxy_uri)
            GES.Asset.request_async(GES.UriClip,
                                    proxy_uri, None,
                                    self.__assetLoadedCb, asset,
                                    None)
            return

        self.debug("Creating a proxy for %s (strategy: %s, force: %s, scaled: %s)",
                   asset.get_id(), self.app.settings.proxying_strategy,
                   force_proxying, scaled)
        if scaled:
            project = self.app.project_manager.current_project
            w = project.scaled_proxy_width
            h = project.scaled_proxy_height
            if not project.has_scaled_proxy_size():
                project.scaled_proxy_width = w
                project.scaled_proxy_height = h
            t_width, t_height = self._scale_asset_resolution(asset, w, h)
            self.__createTranscoder(asset, width=t_width, height=t_height, shadow=shadow)
        else:
            self.__createTranscoder(asset, shadow=shadow)


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
