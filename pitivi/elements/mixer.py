# PiTiVi , Non-linear video editor
#
#       pitivi/elements/mixer.py
#
# Copyright (c) 2009, Edward Hervey <bilboed@bilboed.com>
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
Audio and Video mixers
"""

import gobject
import gst
from pitivi.utils import native_endianness

from pitivi.signalinterface import Signallable


class SmartAdderBin(gst.Bin):

    __gstdetails__ = (
        "Smart Adder",
        "Generic/Audio",
        "Convenience wrapper around adder, accepts anything",
        "Edward Hervey <bilboed@bilboed.com>"
        )

    __gsttemplates__ = (
        gst.PadTemplate("src", gst.PAD_SRC, gst.PAD_ALWAYS,
                        gst.Caps("audio/x-raw-int;audio/x-raw-float")),
        gst.PadTemplate("sink_%u", gst.PAD_SINK, gst.PAD_REQUEST,
                        gst.Caps("audio/x-raw-int;audio/x-raw-float"))

        )

    def __init__(self):
        gst.Bin.__init__(self)
        self.adder = gst.element_factory_make("adder", "real-adder")
        # FIXME : USE THE PROJECT SETTINGS FOR THESE CAPS !
        csp = gst.element_factory_make("capsfilter")
        csp.props.caps = gst.Caps("audio/x-raw-int,depth=32,width=32,signed=True,rate=44100,channels=2,endianness=%s" % native_endianness)
        self.add(self.adder, csp)
        self.adder.link_pads_full("src", csp, "sink", gst.PAD_LINK_CHECK_NOTHING)
        srcpad = gst.GhostPad("src", csp.get_pad("src"))
        srcpad.set_active(True)
        self.add_pad(srcpad)
        self.pad_count = 0
        self.inputs = {} # key:pad_name, value:(sinkpad, aconv, aresample, adderpad)

    def do_request_new_pad(self, template, name=None):
        self.debug("template:%r, name:%r" % (template, name))
        if name == None:
            name = "sink_%u" % self.pad_count
        if name in self.inputs.keys():
            return None

        aconv = gst.element_factory_make("audioconvert", "aconv-%d" % self.pad_count)
        aresample = gst.element_factory_make("audioresample", "aresample-%d" % self.pad_count)
        self.add(aconv, aresample)
        aconv.sync_state_with_parent()
        aresample.sync_state_with_parent()
        aconv.link_pads_full("src", aresample, "sink", gst.PAD_LINK_CHECK_NOTHING)
        adderpad = self.adder.get_request_pad("sink%d")
        aresample.get_pad("src").link_full(adderpad, gst.PAD_LINK_CHECK_NOTHING)

        pad = gst.GhostPad(name, aconv.get_pad("sink"))
        pad.set_active(True)
        self.add_pad(pad)
        self.inputs[name] = (pad, aconv, aresample, adderpad)
        self.pad_count += 1
        return pad

    def do_release_pad(self, pad):
        self.debug("pad:%r" % pad)
        name = pad.get_name()
        if name in self.inputs.keys():
            sinkpad, aconv, aresample, adderpad = self.inputs.pop(name)
            # we deactivate this pad to make sure that if ever the streaming
            # thread was doing something downstream (like getting caps) it will
            # return with GST_FLOW_WRONG_STATE and not GST_FLOW_NOT_LINKED (which is
            # a fatal return flow).
            aresample.get_pad("src").set_active(False)

            self.adder.release_request_pad(adderpad)
            aresample.get_pad("src").unlink(adderpad)
            aconv.unlink(aresample)
            aconv.set_state(gst.STATE_NULL)
            aresample.set_state(gst.STATE_NULL)
            self.remove(aconv, aresample)
            self.remove_pad(sinkpad)
        self.debug("done")


gobject.type_register(SmartAdderBin)
gst.element_register(SmartAdderBin, 'smart-adder-bin')

class SmartVideomixerBin(gst.Bin):

    __gstdetails__ = (
        "Smart Videomixer",
        "Generic/Video",
        "Convenience wrapper around videomixer, accepts anything",
        "Edward Hervey <bilboed@bilboed.com>"
        )

    __gsttemplates__ = (
        gst.PadTemplate("src", gst.PAD_SRC, gst.PAD_ALWAYS,
                        gst.Caps("video/x-raw-yuv;video/x-raw-rgb")),
        gst.PadTemplate("sink_%u", gst.PAD_SINK, gst.PAD_REQUEST,
                        gst.Caps("video/x-raw-yuv;video/x-raw-rgb"))

        )

    def __init__(self, track):
        gst.Bin.__init__(self)
        self.videomixer = gst.element_factory_make("videomixer", "real-videomixer")
        # black background
        self.videomixer.props.background = 1
        # FIXME : USE THE PROJECT SETTINGS FOR THESE CAPS !
        self.colorspace = gst.element_factory_make("ffmpegcolorspace")
        self.add(self.videomixer, self.colorspace)
        self.videomixer.link_pads_full("src", self.colorspace, "sink", gst.PAD_LINK_CHECK_NOTHING)
        srcpad = gst.GhostPad("src", self.colorspace.get_pad("src"))
        srcpad.set_active(True)
        self.add_pad(srcpad)
        self.pad_count = 0
        self.inputs = {} # key : pad_name,
                         # value : (sinkpad, ffmpegcolorspace, capsfilter, videomixerpad)

        self.alpha_helper = SmartVideomixerBinPropertyHelper(self, track, self.inputs)

    def _pad_blockedCb (self, pad, blocked, unused=None):
        pass

    def change_mixer(self, has_alpha):
        # When we change from having an alpha channel to not having one,
        # we need to change the videomixer to avoid Not Negotiated Errors (since
        # we are actually changing the caps format in this case).
        # This is Hacky, but needed for the alpha passthrough optimization to be
        # usable since if fixes bugs such as #632414, #637522 (and perhaps others)
        # More infos at:
        #   http://jeff.ecchi.ca/blog/2011/04/24/negotiating-performance/
        for pad_name in self.inputs:
            values = self.inputs.get(pad_name)
            values[3].send_event(gst.event_new_flush_start())
            values[3].send_event(gst.event_new_flush_stop())
            if not values[3].is_blocked():
                values[3].set_blocked_async(True, self._pad_blockedCb)

        new_videomixer = gst.element_factory_make("videomixer", "real-videomixer")
        new_videomixer.props.background = 1

        self.videomixer.set_state(gst.STATE_NULL)
        #We change the mixer
        self.remove(self.videomixer)
        self.add(new_videomixer)

        #And relink everything in the new one
        for pad_name in self.inputs:
            values = self.inputs.get(pad_name)
            videomixerpad = new_videomixer.get_request_pad(pad_name)
            values[2].get_pad("src").unlink(values[3])
            values[2].get_pad("src").link_full(videomixerpad, gst.PAD_LINK_CHECK_NOTHING)
            self.inputs[pad_name] = (values[0], values[1], values[2], videomixerpad)

        csp_sink = self.colorspace.get_pad("sink")
        self.videomixer.get_pad("src").unlink(csp_sink)
        self.videomixer = new_videomixer
        self.videomixer.link_pads_full("src", self.colorspace, "sink", gst.PAD_LINK_CHECK_NOTHING)

        for pad_name in self.inputs:
            values = self.inputs.get(pad_name)
            values[3].send_event(gst.event_new_flush_start())
            values[3].send_event(gst.event_new_flush_stop())
            if values[3].is_blocked():
                values[3].set_blocked_async(False, self._pad_blockedCb)

        self.sync_state_with_parent()

    def update_priority(self, pad, priority):
        self.debug("pad:%r, priority:%d" % (pad, priority))
        if priority > 10000:
            priority = 10000
        a,b,c,sinkpad = self.inputs.get(pad.get_name(), (None, None, None, None))
        if sinkpad:
            sinkpad.props.zorder = 10000 - priority
        self.debug("done")

    def do_request_new_pad(self, template, name=None):
        self.debug("template:%r, name:%r" % (template, name))
        if name == None:
            name = "sink_%u" % self.pad_count
        if name in self.inputs.keys():
            return None

        csp = gst.element_factory_make("ffmpegcolorspace", "csp-%d" % self.pad_count)
        capsfilter = gst.element_factory_make("capsfilter", "capsfilter-%d" % self.pad_count)
        # configure the capsfilter caps
        if self.alpha_helper.alpha_count != 0:
            capsfilter.props.caps = gst.Caps('video/x-raw-yuv,format=(fourcc)AYUV')
        else:
            capsfilter.props.caps = gst.Caps('video/x-raw-yuv')

        self.add(csp, capsfilter)

        csp.link_pads_full("src", capsfilter, "sink", gst.PAD_LINK_CHECK_NOTHING)
        csp.sync_state_with_parent()
        capsfilter.sync_state_with_parent()

        videomixerpad = self.videomixer.get_request_pad("sink_%d" % self.pad_count)

        capsfilter.get_pad("src").link_full(videomixerpad, gst.PAD_LINK_CHECK_NOTHING)

        pad = gst.GhostPad(name, csp.get_pad("sink"))
        pad.set_active(True)
        self.add_pad(pad)
        self.inputs[name] = (pad, csp, capsfilter, videomixerpad)
        self.pad_count += 1
        return pad

    def do_release_pad(self, pad):
        self.debug("pad:%r" % pad)
        name = pad.get_name()
        if name in self.inputs.keys():
            sinkpad, csp, capsfilter, videomixerpad = self.inputs.pop(name)
            self.remove_pad(sinkpad)
            capsfilter.get_pad("src").unlink(videomixerpad)
            self.videomixer.release_request_pad(videomixerpad)
            csp.set_state(gst.STATE_NULL)
            capsfilter.set_state(gst.STATE_NULL)
            self.remove(csp)
            self.remove(capsfilter)
        self.debug("done")

class SmartVideomixerBinPropertyHelper(Signallable):
    """A set of callbacks used for considering the alpha state of all track
       objects in the composition."""

    def __init__(self, mixer, track, inputs):
        # this import is here because of a circular dependence
        from pitivi.timeline.track import TrackError
        self.inputs = inputs
        self.alpha_count = 0
        self._mixer = mixer
        # connect track-object-{added,removed} signals from track to callbacks
        track.connect("track-object-added", self._trackAddedCb)
        track.connect("track-object-removed", self._trackRemovedCb)
        track.connect("transition-added", self._transitionAddedCb)
        track.connect("transition-removed", self._transitionRemovedCb)
        # configure initial alpha state
        self.alphaStateChanged(False)


    def _trackAddedCb(self, track, track_object):
        # this import is here because of a circular dependence
        from pitivi.timeline.track import TrackError
        try:
            interpolator = track_object.getInterpolator("alpha")
        except TrackError:
            # no alpha
            pass
        else:
            interpolator.connect("keyframe-added", self._keyframeChangedCb)
            interpolator.connect("keyframe-moved", self._keyframeChangedCb)
            interpolator.connect("keyframe-removed", self._keyframeChangedCb)

    def _trackRemovedCb(self, track, track_object):
        # this import is here because of a circular dependence
        from pitivi.timeline.track import TrackError
        try:
            # FIXME: .interpolators is accessed directly as the track object
            # has been removed and its gnl_object doesn't contain any
            # controllable element anymore
            interpolator = track_object.interpolators["alpha"][1]
        except(KeyError, TrackError):
            # no alpha
            pass
        else:
            # we must decrement alpha_count and update the alpha state as
            # appropriate
            old_alpha_count = self.alpha_count
            for kf in interpolator.getKeyframes():
                if interpolator.valueAt(kf.time) < 1.0:
                    self.alpha_count -= 1
            # as we're only decrementing, this should be the only case to check
            if old_alpha_count > 0 and self.alpha_count == 0:
                self.alphaStateChanged(False)
            interpolator.disconnect_by_func(self._keyframeChangedCb)

    def _keyframeChangedCb(self, interpolator, keyframe, old_value=None):
        """Checks the alpha state and emits a signal if it has changed"""
        # FIXME: This code assumes the interpolation mode is linear and as
        # such only considers the alpha values at keyframes
        old_alpha_count = self.alpha_count
        new_value = interpolator.valueAt(keyframe.time)
        if old_value == 1.0 or old_value is None:
            if new_value < 1.0:
                self.alpha_count += 1
        elif old_value < 1.0 or old_value is not None:
            if new_value == 1.0:
                self.alpha_count -= 1
        if old_alpha_count == 0 and self.alpha_count > 0:
            self.alphaStateChanged(True)
        elif old_alpha_count > 0 and self.alpha_count == 0:
            self.alphaStateChanged(False)

    def _transitionAddedCb(self, track, transition):
        # FIXME - this assumes transitions need alpha, change it if they don't
        if self.alpha_count == 0:
            self.alphaStateChanged(True)
        self.alpha_count += 1

    def _transitionRemovedCb(self, track, transition):
        self.alpha_count -= 1
        if self.alpha_count == 0:
            self.alphaStateChanged(False)

    def alphaStateChanged(self, has_alpha):
        """Updates capsfilter caps to reflect the alpha state of composition"""
        caps = gst.Caps('video/x-raw-yuv')
        if has_alpha == True:
            caps[0]["format"] = gst.Fourcc('AYUV')
        for input in self.inputs.values():
            input[2].props.caps = caps

        self._mixer.change_mixer(has_alpha)

gobject.type_register(SmartVideomixerBin)
gst.element_register(SmartVideomixerBin, 'smart-videomixer-bin')
