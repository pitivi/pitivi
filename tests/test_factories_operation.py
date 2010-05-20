#!/usr/bin/env python
#
#       test/test_factories_operation.py
#
# Copyright (C) 2010 Thibault Saunier <tsaunier@gnome.org>
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
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.


import gst

from common import TestCase

from pitivi.log.log import debug
from pitivi.factories.operation import VideoEffectFactory

class TestVideoEffectFactory(TestCase):
    def setUp(self):
        TestCase.setUp(self)
        self.factory = VideoEffectFactory ('identity', 'identity')

    def testMakeBin (self):
        bin = self.factory.makeBin()
        bin2 = self.factory.makeBin()
        self.failUnless(isinstance(bin, gst.BaseTransform))
        self.failUnless(bin.get_factory().get_name() == "identity" )
        debug ('TestVideoEffectFactory','%s %s','Bin is:', bin.get_factory().get_name())
        self.factory.releaseBin(bin)
        self.factory.releaseBin(bin2)

    def tearDown(self):
        del self.factory
        TestCase.tearDown(self)
