# Pitivi video editor
#
#       pitivi/utils/validate.py
#
# Copyright (c) 2014, Thibault Saunier <thibault.saunier@collabora.com>
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
import sys
from gi.repository import GES

has_validate = False


def stop(scenario, action):
    sys.stdout.write("STOP action, not doing anything in pitivi")
    sys.stdout.flush()
    return 1


def init():
    global has_validate
    try:
        from gi.repository import GstValidate
        GstValidate.init()
        has_validate = GES.validate_register_action_types()
        GstValidate.register_action_type("stop", "pitivi",
                                         stop, None,
                                         "Pitivi override for the stop action",
                                         GstValidate.ActionTypeFlags.NONE)
    except ImportError:
        has_validate = False
