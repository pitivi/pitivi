# PiTiVi , Non-linear video editor
#
#       pitivi/elements/singledecodebin.py
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
Single-stream queue-less decodebin
"""

import gobject
import gst
from pitivi.stream import get_pad_id, pad_compatible_stream
from pitivi.utils import CachedFactoryList

def is_raw(caps):
    """ returns True if the caps are RAW """
    rep = caps.to_string()
    valid = ["video/x-raw", "audio/x-raw", "text/plain", "text/x-pango-markup"]
    for val in valid:
        if rep.startswith(val):
            return True
    return False

def factoryFilter(factory):
    if factory.get_rank() < 64 :
        return False

    klass = factory.get_klass()
    for cat in ("Demuxer", "Decoder", "Parse"):
        if cat in klass:
            return True

    return False

_factoryCache = CachedFactoryList(factoryFilter)

class SingleDecodeBin(gst.Bin):
    """
    A variant of decodebin.

    * Only outputs one stream
    * Doesn't contain any internal queue
    """

    QUEUE_SIZE = 1 * gst.SECOND

    __gsttemplates__ = (
        gst.PadTemplate ("sinkpadtemplate",
                         gst.PAD_SINK,
                         gst.PAD_ALWAYS,
                         gst.caps_new_any()),
        gst.PadTemplate ("srcpadtemplate",
                         gst.PAD_SRC,
                         gst.PAD_SOMETIMES,
                         gst.caps_new_any())
        )

    def __init__(self, caps=None, uri=None, stream=None, *args, **kwargs):
        gst.Bin.__init__(self, *args, **kwargs)
        if not caps:
            caps = gst.caps_new_any()
        self.caps = caps
        self.stream = stream
        self.typefind = gst.element_factory_make("typefind", "internal-typefind")
        self.add(self.typefind)

        self.uri = uri
        if self.uri and gst.uri_is_valid(self.uri):
            self.urisrc = gst.element_make_from_uri(gst.URI_SRC, uri, "urisrc")
            self.log("created urisrc %s / %r" % (self.urisrc.get_name(),
                                                 self.urisrc))
            self.add(self.urisrc)
            # Set the blocksize to 512kbytes, this will only matter for push-based sources
            if hasattr(self.urisrc.props, "blocksize"):
                self.urisrc.props.blocksize = 524288
            self.urisrc.link(self.typefind)
        else:
            self._sinkpad = gst.GhostPad("sink", self.typefind.get_pad("sink"))
            self._sinkpad.set_active(True)
            self.add_pad(self._sinkpad)

        self.typefind.connect("have_type", self._typefindHaveTypeCb)

        self._srcpad = None

        self._dynamics = []

        self._validelements = [] #added elements

        self.debug("stream:%r" % self.stream)

        self.pending_newsegment = False
        self.eventProbeId = None

    ## internal methods

    def _controlDynamicElement(self, element):
        self.log("element:%s" % element.get_name())
        self._dynamics.append(element)
        element.connect("pad-added", self._dynamicPadAddedCb)
        element.connect("no-more-pads", self._dynamicNoMorePadsCb)

    def _findCompatibleFactory(self, caps):
        """
        Returns a list of factories (sorted by rank) which can take caps as
        input. Returns empty list if none are compatible
        """
        self.debug("caps:%s" % caps.to_string())
        res = []
        for factory in _factoryCache.get():
            for template in factory.get_static_pad_templates():
                if template.direction == gst.PAD_SINK:
                    intersect = caps.intersect(template.static_caps.get())
                    if not intersect.is_empty():
                        res.append(factory)
                        break
        self.debug("returning %r" % res)
        return res

    def _closeLink(self, element):
        """
        Inspects element and tries to connect something on the srcpads.
        If there are dynamic pads, it sets up a signal handler to
        continue autoplugging when they become available.
        """
        to_connect = []
        dynamic = False
        templates = element.get_pad_template_list()
        for template in templates:
            if not template.direction == gst.PAD_SRC:
                continue
            if template.presence == gst.PAD_ALWAYS:
                pad = element.get_pad(template.name_template)
                to_connect.append(pad)
            elif template.presence == gst.PAD_SOMETIMES:
                pad = element.get_pad(template.name_template)
                if pad:
                    to_connect.append(pad)
                else:
                    dynamic = True
            else:
                self.log("Template %s is a request pad, ignoring" % pad.name_template)

        if dynamic:
            self.debug("%s is a dynamic element" % element.get_name())
            self._controlDynamicElement(element)

        for pad in to_connect:
            self._closePadLink(element, pad, pad.get_caps())

    def _isDemuxer(self, element):
        if not 'Demux' in element.get_factory().get_klass():
            return False

        potential_src_pads = 0
        for template in element.get_pad_template_list():
            if template.direction != gst.PAD_SRC:
                continue

            if template.presence == gst.PAD_REQUEST or \
                    "%" in template.name_template:
                potential_src_pads += 2
                break
            else:
                potential_src_pads += 1

        return potential_src_pads > 1

    def _plugDecodingQueue(self, pad):
        queue = gst.element_factory_make("queue")
        queue.props.max_size_time = self.QUEUE_SIZE
        self.add(queue)
        queue.sync_state_with_parent()
        pad.link(queue.get_pad("sink"))
        pad = queue.get_pad("src")

        return pad

    def _tryToLink1(self, source, pad, factories):
        """
        Tries to link one of the factories' element to the given pad.

        Returns the element that was successfully linked to the pad.
        """
        self.debug("source:%s, pad:%s , factories:%r" % (source.get_name(),
                                                         pad.get_name(),
                                                         factories))

        if self._isDemuxer(source):
            pad = self._plugDecodingQueue(pad)

        result = None
        for factory in factories:
            element = factory.create()
            if not element:
                self.warning("weren't able to create element from %r" % factory)
                continue

            sinkpad = element.get_pad("sink")
            if not sinkpad:
                continue

            self.add(element)
            element.set_state(gst.STATE_READY)
            try:
                pad.link(sinkpad)
            except:
                element.set_state(gst.STATE_NULL)
                self.remove(element)
                continue

            self._closeLink(element)
            element.set_state(gst.STATE_PAUSED)

            result = element
            break

        return result

    def _closePadLink(self, element, pad, caps):
        """
        Finds the list of elements that could connect to the pad.
        If the pad has the desired caps, it will create a ghostpad.
        If no compatible elements could be found, the search will stop.
        """
        self.debug("element:%s, pad:%s, caps:%s" % (element.get_name(),
                                                    pad.get_name(),
                                                    caps.to_string()))
        if caps.is_empty():
            self.log("unknown type")
            return
        if caps.is_any():
            self.log("type is not know yet, waiting")
            return

        self.debug("stream %r" % (self.stream))
        if caps.intersect(self.caps) and (self.stream is None or
                (self.stream.pad_name == get_pad_id(pad))):
            # This is the desired caps
            if not self._srcpad:
                self._wrapUp(element, pad)
        elif is_raw(caps) and pad_compatible_stream(pad, self.stream):
            self.log ("not the target stream, but compatible")
            if not self._srcpad:
                self._wrapUp(element, pad)
        elif is_raw(caps):
            self.log("We hit a raw caps which isn't the wanted one")
            # FIXME : recursively remove everything until demux/typefind

        else:
            # Find something
            if len(caps) > 1:
                self.log("many possible types, delaying")
                return
            facts = self._findCompatibleFactory(caps)
            if not facts:
                self.log("unknown type")
                return
            self._tryToLink1(element, pad, facts)

    def _wrapUp(self, element, pad):
        """
        Ghost the given pad of element.
        Remove non-used elements.
        """

        if self._srcpad:
            return
        self._markValidElements(element)
        gobject.idle_add(self._removeUnusedElements, self.typefind)
        if pad.props.caps is not None:
            caps = pad.props.caps
        else:
            caps = pad.get_caps()

        self._srcpad = gst.GhostPad("src", pad)
        self._srcpad.set_active(True)

        if caps.is_fixed():
            self._exposePad(target=pad)
        else:
            self._blockPad(target=pad)

    def _exposePad(self, target):
        self.log("ghosting pad %s" % target.get_name())
        self.add_pad(self._srcpad)
        self.post_message(gst.message_new_state_dirty(self))

    def _blockPad(self, target):
        # don't pass target as an argument to set_blocked_async. Avoids
        # triggering a bug in gst-python where pad_block_destroy_data calls
        # CPython without acquiring the GIL
        self._target = target
        self._eventProbeId = target.add_event_probe(self._padEventCb)
        self._srcpad.set_blocked_async(True, self._padBlockedCb)

    def _unblockPad(self, target):
        target.remove_event_probe(self._eventProbeId)
        self._eventProbeId = None
        self._srcpad.set_blocked_async(False, self._padBlockedCb)

    def _padBlockedCb(self, ghost, blocked):
        if not blocked:
            if self.pending_newsegment is not None:
                self._srcpad.push_event(self.pending_newsegment)
                self.pending_newsegment = None
            return

        self._exposePad(target=self._target)
        self._unblockPad(target=self._target)

    def _padEventCb(self, pad, event):
        if event.type == gst.EVENT_TAG:
            self.debug("dropping TAG event")
            return False

        if event.type != gst.EVENT_NEWSEGMENT:
            self.warning("first event: %s is not a NEWSEGMENT, bailing out" %
                    event)
            self._exposePad(target=pad)
            self._unblockPad(target=pad)
            return True

        self.debug("stored pending newsegment")
        self.pending_newsegment = event
        return False

    def _markValidElements(self, element):
        """
        Mark this element and upstreams as valid
        """
        self.log("element:%s" % element.get_name())
        if element == self.typefind:
            return
        self._validelements.append(element)
        # find upstream element
        pad = list(element.sink_pads())[0]
        parent = pad.get_peer().get_parent()
        self._markValidElements(parent)

    def _removeUnusedElements(self, element):
        """
        Remove unused elements connected to srcpad(s) of element
        """
        self.log("element:%r" % element)
        for pad in list(element.src_pads()):
            if pad.is_linked():
                peer = pad.get_peer().get_parent()
                if isinstance(peer, gst.Element):
                    self._removeUnusedElements(peer)
                    if not peer in self._validelements:
                        self.log("removing %s" % peer.get_name())
                        pad.unlink(pad.get_peer())
                        peer.set_state(gst.STATE_NULL)
                        self.remove(peer)

    def _cleanUp(self):
        self.log("")
        if self._srcpad:
            self.remove_pad(self._srcpad)
        self._srcpad = None
        self._target = None
        for element in self._validelements:
            element.set_state(gst.STATE_NULL)
            self.remove(element)
        self._validelements = []

    ## Overrides

    def do_change_state(self, transition):
        self.debug("transition:%r" % transition)
        res = gst.Bin.do_change_state(self, transition)
        if transition == gst.STATE_CHANGE_PAUSED_TO_READY:
            self._cleanUp()
        return res

    ## Signal callbacks

    def _typefindHaveTypeCb(self, typefind, probability, caps):
        self.debug("probability:%d, caps:%s" % (probability, caps.to_string()))
        self._closePadLink(typefind, typefind.get_pad("src"), caps)

    ## Dynamic element Callbacks

    def _dynamicPadAddedCb(self, element, pad):
        self.log("element:%s, pad:%s" % (element.get_name(), pad.get_name()))
        if not self._srcpad:
            self._closePadLink(element, pad, pad.get_caps())

    def _dynamicNoMorePadsCb(self, element):
        self.log("element:%s" % element.get_name())

gobject.type_register(SingleDecodeBin)
