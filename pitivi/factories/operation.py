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
from pitivi.elements.smartscale import SmartVideoScale

# FIXME: define a proper hierarchy
class OperationFactoryError(Exception):
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

class StreamModifierFactory(TransformFactory):
    """
    Factories that modify the nature/type of a stream.
    """
    pass

class AudioModifierFactory(StreamModifierFactory):

    def _makeBin(self, *args):
        b = gst.Bin()
        aconv = gst.element_factory_make("audioconvert", "aconv")
        ares = gst.element_factory_make("audioresample", "ares")
        arate = gst.element_factory_make("audiorate", "arate")
        b.add(aconv, ares, arate)
        gst.element_link_many(aconv, ares, arate)

        gsink = gst.GhostPad("sink", aconv.get_pad("sink"))
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
        csp = gst.element_factory_make("ffmpegcolorspace", "csp")
        vrate = gst.element_factory_make("videorate", "vrate")

        b.add(csp, vrate)
        csp.link(vrate)

        gsink = gst.GhostPad("sink", csp.get_pad("sink"))
        gsink.set_active(True)
        b.add_pad(gsink)

        # if we have an output stream specified, we add a capsfilter
        if len(self.output_streams):
            vscale = SmartVideoScale()
            vscale.set_caps(self.output_streams[0].caps)
            b.add(vscale)
            vrate.link(vscale)

            gsrc = gst.GhostPad("src", vscale.get_pad("src"))
        else:
            gsrc = gst.GhostPad("src", vrate.get_pad("src"))

        gsrc.set_active(True)
        b.add_pad(gsrc)
        return b

