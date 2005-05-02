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

DND_TYPE_TEXT_PLAIN = 24
DND_TYPE_URI_LIST = 25
DND_TYPE_PITIVI_FILESOURCE = 26
DND_TYPE_PITIVI_EFFECT = 27
DND_TYPE_PITIVI_AUDIO_EFFECT = 28
DND_TYPE_PITIVI_VIDEO_EFFECT = 29
DND_TYPE_PITIVI_AUDIO_TRANSITION = 30
DND_TYPE_PITIVI_VIDEO_TRANSITION = 31

DND_FILE_TUPLE = ("text/plain", 0, DND_TYPE_TEXT_PLAIN)
DND_URI_TUPLE = ("text/uri-list", 0, DND_TYPE_URI_LIST)
DND_FILESOURCE_TUPLE = ("pitivi/file-source", 0, DND_TYPE_PITIVI_FILESOURCE)
DND_EFFECT_TUPLE = ("pitivi/effect", 0, DND_TYPE_PITIVI_EFFECT)
DND_AUDIO_EFFECT_TUPLE = ("pitivi/audio-effect", 0, DND_TYPE_PITIVI_AUDIO_EFFECT)
DND_VIDEO_EFFECT_TUPLE = ("pitivi/video-effect", 0, DND_TYPE_PITIVI_VIDEO_EFFECT)
DND_AUDIO_TRANSITION_TUPLE = ("pitivi/audio-transition", 0, DND_TYPE_PITIVI_AUDIO_TRANSITION)
DND_VIDEO_TRANSITION_TUPLE = ("pitivi/video-transition", 0, DND_TYPE_PITIVI_VIDEO_TRANSITION)
