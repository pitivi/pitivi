#!/usr/bin/python
# PiTiVi , Non-linear video editor
#
#       operation.py
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

import gst
from pitivi.factories.base import OperationFactory
from pitivi.stream import AudioStream, VideoStream

# FIXME: define a proper hierarchy
class OperationFactoryError(Exception):
    pass

class ModifierFactoryError(OperationFactoryError):
    pass

class TransformFactory(OperationFactory):
    """
    Factories that take exactly one input stream and output exactly one output
    stream.
    """

    def addTransformStreams(self, input_stream, output_stream):
        self.addInputStream(input_stream)
        self.addOutputStream(output_stream)

    def addInputStream(self, stream):
        if len(self.input_streams) > 1:
            raise OperationFactoryError("Can't handle more than one stream")
        return OperationFactory.addInputStream(self, stream)

    def addOutputStream(self, stream):
        if len(self.output_streams) > 1:
            raise OperationFactoryError("Can't handle more than one stream")
        return OperationFactory.addOutputStream(self, stream)

    def _requestNewInputStream(self, *args):
        raise OperationFactoryError("TransformFactory doesn't allow request pads")

class EffectFactory (TransformFactory):
    """
    Factories that applies an effect on a stream
    """
    def __init__ (self, effect, name=''):
        TransformFactory.__init__(self, name)
        self._effect = effect

    def _makeBin (self, *args):
        return gst.element_factory_make(self._effect)

class StreamModifierFactory(TransformFactory):
    """
    Factories that modify the nature/type of a stream.
    """
    pass

class AudioModifierFactory(StreamModifierFactory):

    def _makeBin(self, *args):
        b = gst.Bin()
        idt = gst.element_factory_make("identity", "single-segment")
        idt.props.single_segment = True
        idt.props.silent = True
        aconv = gst.element_factory_make("audioconvert", "aconv")
        ares = gst.element_factory_make("audioresample", "ares")
        arate = gst.element_factory_make("audiorate", "arate")
        b.add(idt, aconv, ares, arate)
        gst.element_link_many(idt, aconv, ares, arate)

        gsink = gst.GhostPad("sink", idt.get_pad("sink"))
        gsink.set_active(True)
        b.add_pad(gsink)

        # if we have an output stream specified, we add a capsfilter
        if len(self.output_streams):
            cfilter = gst.element_factory_make("capsfilter")
            cfilter.props.caps = self.output_streams[0].caps
            b.add(cfilter)
            arate.link(cfilter)

            gsrc = gst.GhostPad("src", cfilter.get_pad("src"))
        else:
            gsrc = gst.GhostPad("src", arate.get_pad("src"))

        gsrc.set_active(True)
        b.add_pad(gsrc)
        return b

class VideoModifierFactory(StreamModifierFactory):

    def _makeBin(self, *args):
        b = gst.Bin()
        idt = gst.element_factory_make("identity", "single-segment")
        idt.props.single_segment = True
        idt.props.silent = True
        csp = gst.element_factory_make("ffmpegcolorspace", "csp")
        vrate = gst.element_factory_make("videorate", "vrate")

        b.add(idt, csp, vrate)
        gst.element_link_many(idt, csp, vrate)

        gsink = gst.GhostPad("sink", idt.get_pad("sink"))
        gsink.set_active(True)
        b.add_pad(gsink)

        # if we have an output stream specified, we add a capsfilter
        vscale = gst.element_factory_make("videoscale")
        try:
            vscale.props.add_borders = True
        except AttributeError:
            self.warning("User has old version of videoscale. "
                    "add-border not enabled.")

        b.add(vscale)
        vrate.link(vscale)
        self.debug("output_streams:%d", len(self.output_streams))

        if len(self.output_streams):
            idt = gst.element_factory_make("capsfilter")
            idt.props.caps = self.output_streams[0].caps
            b.add(idt)
            vscale.link(idt)

            gsrc = gst.GhostPad("src", idt.get_pad("src"))
        else:
            gsrc = gst.GhostPad("src", vscale.get_pad("src"))

        gsrc.set_active(True)
        b.add_pad(gsrc)
        return b

def get_modifier_for_stream(input_stream=None, output_stream=None):
    """
    Returns a L{StreamModifierFactory} for the given streams.

    @raises ModifierFactoryError: If no modifier factory is available
    for the given streams.
    """
    if input_stream == None and output_stream == None:
        raise ModifierFactoryError("No streams provided")
    if (isinstance(input_stream, AudioStream) or input_stream == None) and \
           (isinstance(output_stream, AudioStream) or output_stream == None):
        res = AudioModifierFactory()
    elif (isinstance(input_stream, VideoStream) or input_stream == None) and \
             (isinstance(output_stream, VideoStream) or output_stream == None):
        res = VideoModifierFactory()
    else:
        raise ModifierFactoryError("No modifier for given stream type")
    if input_stream:
        res.addInputStream(input_stream)
    if output_stream:
        res.addOutputStream(output_stream)
    return res
