# PiTiVi , Non-linear video editor
#
#       pitivi/pitivi.py
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
Drag and drop constants
"""

TYPE_TEXT_PLAIN = 24
TYPE_URI_LIST = 25

# FileSourceFactory (or subclasses)
TYPE_PITIVI_FILESOURCE = 26

# What objects to these correspond to ???
TYPE_PITIVI_EFFECT = 27
TYPE_PITIVI_AUDIO_EFFECT = 28
TYPE_PITIVI_VIDEO_EFFECT = 29
TYPE_PITIVI_AUDIO_TRANSITION = 30
TYPE_PITIVI_VIDEO_TRANSITION = 31

FILE_TUPLE = ("text/plain", 0, TYPE_TEXT_PLAIN)
URI_TUPLE = ("text/uri-list", 0, TYPE_URI_LIST)
FILESOURCE_TUPLE = ("pitivi/file-source", 0, TYPE_PITIVI_FILESOURCE)
EFFECT_TUPLE = ("pitivi/effect", 0, TYPE_PITIVI_EFFECT)
AUDIO_EFFECT_TUPLE = ("pitivi/audio-effect", 0, TYPE_PITIVI_AUDIO_EFFECT)
VIDEO_EFFECT_TUPLE = ("pitivi/video-effect", 0, TYPE_PITIVI_VIDEO_EFFECT)
AUDIO_TRANSITION_TUPLE = ("pitivi/audio-transition", 0, TYPE_PITIVI_AUDIO_TRANSITION)
VIDEO_TRANSITION_TUPLE = ("pitivi/video-transition", 0, TYPE_PITIVI_VIDEO_TRANSITION)
