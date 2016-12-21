# -*- coding: utf-8 -*-
# Pitivi video editor
# Copyright (c) 2005, Edward Hervey <bilboed@bilboed.com>
# Copyright (c) 2012, Thibault Saunier <thibault.saunier@collabora.com>
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
"""UI constants and various functions and classes that help with UI drawing."""
import decimal
import os
import urllib.error
import urllib.parse
import urllib.request
from gettext import gettext as _
from gettext import ngettext

import cairo
from gi.repository import Gdk
from gi.repository import GES
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import Gtk
from gi.repository.GstPbutils import DiscovererAudioInfo
from gi.repository.GstPbutils import DiscovererInfo
from gi.repository.GstPbutils import DiscovererStreamInfo
from gi.repository.GstPbutils import DiscovererSubtitleInfo
from gi.repository.GstPbutils import DiscovererVideoInfo

from pitivi.configure import get_pixmap_dir
from pitivi.utils.loggable import doLog
from pitivi.utils.loggable import ERROR
from pitivi.utils.misc import get_proxy_target
from pitivi.utils.misc import path_from_uri


# Dimensions in pixels
EXPANDED_SIZE = 65

PADDING = 6
SPACING = 10

PLAYHEAD_WIDTH = 1
PLAYHEAD_COLOR = (255, 0, 0)
SNAPBAR_WIDTH = 5
SNAPBAR_COLOR = (127, 153, 204)
LAYER_HEIGHT = 130
# The space between two layers.
SEPARATOR_HEIGHT = PADDING

SMALL_THUMB_WIDTH = 64
# 128 is the normal size for thumbnails, but for *icons* it looks insane.
LARGE_THUMB_WIDTH = 96

# Drag and drop
FILE_TARGET_ENTRY = Gtk.TargetEntry.new("text/plain", 0, 0)
URI_TARGET_ENTRY = Gtk.TargetEntry.new("text/uri-list", 0, 0)
EFFECT_TARGET_ENTRY = Gtk.TargetEntry.new("pitivi/effect", 0, 0)


def _get_settings(schema):
    if schema not in Gio.Settings.list_schemas():
        return None
    try:
        return Gio.Settings(schema_id=schema)
    except TypeError:
        # Gtk 3.10
        return Gio.Settings(schema=schema)


def _get_font(font_spec, default):
    raw_font = default
    settings = _get_settings("org.gnome.desktop.interface")
    if settings:
        if font_spec in settings.list_keys():
            raw_font = settings.get_string(font_spec)
    face = raw_font.rsplit(" ", 1)[0]
    return cairo.ToyFontFace(face)

NORMAL_FONT = _get_font("font-name", "Cantarell")
DOCUMENT_FONT = _get_font("document-font-name", "Sans")
MONOSPACE_FONT = _get_font("monospace-font-name", "Monospace")

TIMELINE_CSS = """
    .AudioBackground {
        background-color: #496c21;
    }

    .VideoBackground {
        background-color: #2d2d2d;
    }

    .AudioBackground:selected {
        background-color: #1b2e0e;
    }

    .VideoBackground:selected {
        background-color: #0f0f0f;
    }

    .KeyframeCurve {
        background-color: rgba(0, 0, 0, 0);
    }

    .Trimbar {
        background-image: url('%(trimbar_normal)s');
        opacity:0.5;
    }

    .Trimbar.left {
        border-radius: 5px 0px 0px 5px;
    }

    .Trimbar.right {
        border-radius: 0px 5px 5px 0px;
    }

    .Trimbar:hover {
        background-image: url('%(trimbar_focused)s');
    }

    .Clip {
    }

    .TransitionClip {
        background-color: rgba(127, 153, 204, 0.5);
    }

    .TransitionClip:selected {
        background-color: rgba(127, 200, 204, 0.7);
    }

    .SpacedSeparator:hover {
        background-color: rgba(127, 153, 204, 0.5);
    }

    .SpacedSeparator {
        background-color: rgba(0, 0, 0, 0.1);
    }

    .Marquee {
        background-color: rgba(224, 224, 224, 0.7);
    }

""" % ({'trimbar_normal': os.path.join(get_pixmap_dir(), "trimbar-normal.png"),
        'trimbar_focused': os.path.join(get_pixmap_dir(), "trimbar-focused.png")})
# ---------------------- ARGB color helper-------------------------------------#


def gtk_style_context_get_color(context, state):
    context.save()
    context.set_state(state)
    color = context.get_color(context.get_state())
    context.restore()
    return color


def argb_to_gdk_rgba(color_int):
    return Gdk.RGBA(color_int / 256 ** 2 % 256 / 255.,
                    color_int / 256 ** 1 % 256 / 255.,
                    color_int / 256 ** 0 % 256 / 255.,
                    color_int / 256 ** 3 % 256 / 255.)


def gdk_rgba_to_argb(color):
    color_int = 0
    color_int += int(color.alpha * 255) * 256 ** 3
    color_int += int(color.red * 255) * 256 ** 2
    color_int += int(color.green * 255) * 256 ** 1
    color_int += int(color.blue * 255) * 256 ** 0
    return color_int


def pack_color_32(red, green, blue, alpha=0xFFFF):
    """Packs the specified 16bit color values in a 32bit RGBA value."""
    red = red >> 8
    green = green >> 8
    blue = blue >> 8
    alpha = alpha >> 8
    return (red << 24 | green << 16 | blue << 8 | alpha)


def pack_color_64(red, green, blue, alpha=0xFFFF):
    """Packs the specified 16bit color values in a 64bit RGBA value."""
    return (red << 48 | green << 32 | blue << 16 | alpha)


def unpack_color(value):
    """Unpacks the specified RGBA value into four 16bit color values.

    Args:
        value (int): A 32bit or 64bit RGBA value.
    """
    if not (value >> 32):
        return unpack_color_32(value)
    else:
        return unpack_color_64(value)


def unpack_color_32(value):
    """Unpacks the specified 32bit RGBA value into four 16bit color values."""
    red = (value >> 24) << 8
    green = ((value >> 16) & 0xFF) << 8
    blue = ((value >> 8) & 0xFF) << 8
    alpha = (value & 0xFF) << 8
    return red, green, blue, alpha


def unpack_color_64(value):
    """Unpacks the specified 64bit RGBA value into four 16bit color values."""
    red = (value >> 48) & 0xFFFF
    green = (value >> 32) & 0xFFFF
    blue = (value >> 16) & 0xFFFF
    alpha = value & 0xFFFF
    return red, green, blue, alpha


def hex_to_rgb(value):
    return tuple(float(int(value[i:i + 2], 16)) / 255.0 for i in range(0, 6, 2))


def set_cairo_color(context, color):
    if type(color) is Gdk.RGBA:
        cairo_color = (float(color.red), float(color.green), float(color.blue))
    elif type(color) is tuple:
        # Cairo's set_source_rgb function expects values from 0.0 to 1.0
        cairo_color = [max(0, min(1, x / 255.0)) for x in color]
    else:
        raise Exception("Unexpected color parameter: %s, %s" %
                        (type(color), color))
    context.set_source_rgb(*cairo_color)


def beautify_asset(asset):
    """Formats the specified asset for display.

    Args:
        asset (GES.Asset): The asset to display.
    """
    uri = get_proxy_target(asset).props.id
    res = ["<b>" + path_from_uri(uri) + "</b>"]

    ranks = {
        DiscovererVideoInfo: 0,
        DiscovererAudioInfo: 1,
        DiscovererStreamInfo: 2
    }

    def stream_sort_key(stream):
        try:
            return ranks[type(stream)]
        except KeyError:
            return len(ranks)

    info = asset.get_info()
    info.get_stream_list().sort(key=stream_sort_key)
    for stream in info.get_stream_list():
        try:
            beautified_string = beautify_stream(stream)
        except NotImplementedError:
            doLog(ERROR, "Beautify", "None", "Cannot beautify %s", stream)
            continue
        if beautified_string:
            res.append(beautified_string)

    if asset.creation_progress < 100:
        res.append(_("<b>Proxy creation progress:</b> %d%%") % asset.creation_progress)

    return "\n".join(res)


def info_name(info):
    """Returns a human-readable filename (without the path and quoting).

    Args:
        info (GES.Asset or DiscovererInfo): The info to display.
    """
    if isinstance(info, GES.Asset):
        filename = urllib.parse.unquote(os.path.basename(get_proxy_target(info).get_id()))
    elif isinstance(info, DiscovererInfo):
        filename = urllib.parse.unquote(os.path.basename(info.get_uri()))
    else:
        raise Exception("Unsupported argument type: %s" % type(info))
    return GLib.markup_escape_text(filename)


def beautify_stream(stream):
    if type(stream) is DiscovererAudioInfo:
        if stream.get_depth() == 0:
            return None

        templ = ngettext(
            "<b>Audio:</b> %d channel at %d <i>Hz</i> (%d <i>bits</i>)",
            "<b>Audio:</b> %d channels at %d <i>Hz</i> (%d <i>bits</i>)",
            stream.get_channels())
        templ = templ % (stream.get_channels(), stream.get_sample_rate(),
                         stream.get_depth())
        return templ

    elif type(stream) is DiscovererVideoInfo:
        par = stream.get_par_num() / stream.get_par_denom()
        if not stream.is_image():
            templ = _("<b>Video:</b> %d×%d <i>pixels</i> at %.3f <i>fps</i>")
            try:
                templ = templ % (par * stream.get_width(), stream.get_height(),
                                 float(stream.get_framerate_num()) / stream.get_framerate_denom())
            except ZeroDivisionError:
                templ = templ % (
                    par * stream.get_width(), stream.get_height(), 0)
        else:
            templ = _("<b>Image:</b> %d×%d <i>pixels</i>")
            templ = templ % (par * stream.get_width(), stream.get_height())
        return templ

    elif type(stream) is DiscovererSubtitleInfo:
        # Ignore subtitle streams
        return None

    elif type(stream) is DiscovererStreamInfo:
        caps = stream.get_caps().to_string()
        if caps in ("application/x-subtitle", "application/x-id3", "text"):
            # Ignore all audio ID3 tags and subtitle tracks, we don't show them
            return None

    raise NotImplementedError


def time_to_string(value):
    """Converts the specified time to a human readable string.

    Format HH:MM:SS.XXX

    Args:
        value (int): The time in nanoseconds.
    """
    if value == Gst.CLOCK_TIME_NONE:
        return "--:--:--.---"

    ms = value / Gst.MSECOND
    sec = ms / 1000
    ms = ms % 1000
    mins = sec / 60
    sec = sec % 60
    hours = mins / 60
    mins = mins % 60
    return "%01d:%02d:%02d.%03d" % (hours, mins, sec, ms)


def beautify_length(length):
    """Converts the specified duration to a human readable string.

    Args:
        length (int): The duration in nanoseconds.
    """
    if length == Gst.CLOCK_TIME_NONE:
        return ""

    sec = length / Gst.SECOND
    mins = int(sec / 60)
    sec = int(sec % 60)
    hours = int(mins / 60)
    mins = int(mins % 60)

    parts = []
    if hours:
        parts.append(ngettext("%d hour", "%d hours", hours) % hours)

    if mins:
        parts.append(ngettext("%d minute", "%d minutes", mins) % mins)

    if not hours and sec:
        parts.append(ngettext("%d second", "%d seconds", sec) % sec)

    return ", ".join(parts)


def beautify_time_delta(seconds):
    """Converts the specified time to a human-readable estimate.

    This is intended for "Unsaved changes" and "Backup file found" dialogs.
    """
    mins = seconds / 60
    sec = int(seconds % 60)
    hours = mins / 60
    mins = int(mins % 60)
    days = int(hours / 24)
    hours = int(hours % 24)

    parts = []
    if days > 0:
        parts.append(ngettext("%d day", "%d days", days) % days)
    if hours > 0:
        parts.append(ngettext("%d hour", "%d hours", hours) % hours)

    if days == 0 and mins > 0:
        parts.append(ngettext("%d minute", "%d minutes", mins) % mins)

    if hours == 0 and mins < 2 and sec:
        parts.append(ngettext("%d second", "%d seconds", sec) % sec)

    return ", ".join(parts)


def beautify_ETA(length_nanos):
    """Converts the specified duration to a fuzzy estimate.

    Intended for progress ETAs, not to indicate a clip's duration.
    """
    sec = length_nanos / Gst.SECOND
    mins = sec / 60
    sec = int(sec % 60)
    hours = int(mins / 60)
    mins = int(mins % 60)

    parts = []
    if hours > 0:
        parts.append(ngettext("%d hour", "%d hours", hours) % hours)

    if mins > 0:
        parts.append(ngettext("%d minute", "%d minutes", mins) % mins)

    if hours == 0 and mins < 2 and sec:
        parts.append(ngettext("%d second", "%d seconds", sec) % sec)
    return ", ".join(parts)


# -------------------- Gtk widget helpers ----------------------------------- #

def clear_styles(widget):
    """Makes sure the widget has no border, background or other decorations.

    Args:
        widget (Gtk.Widget): The widget to clean up.
    """
    style = widget.get_style_context()
    for css_class in style.list_classes():
        style.remove_class(css_class)


def model(columns, data):
    ret = Gtk.ListStore(*columns)
    for datum in data:
        ret.append(datum)
    return ret


def set_combo_value(combo, value):
    def select_specific_row(model, unused_path, iter_, unused_data):
        if value == model.get_value(iter_, 1):
            combo.set_active_iter(iter_)
            return True
        return False

    combo.props.model.foreach(select_specific_row, None)


def get_combo_value(combo):
    active_iter = combo.get_active_iter()
    if not active_iter:
        return None
    return combo.props.model.get_value(active_iter, 1)


def get_value_from_model(model, key):
    """Searches a key in a model's second column.

    Returns:
        str: The first column element on the matching row. If no row matches,
            and the key is a `Gst.Fraction`, returns a beautified form.
            Otherwise returns the key.
    """
    for row in model:
        if row[1] == key:
            return str(row[0])
    if isinstance(key, Gst.Fraction):
        return "%.3f" % decimal.Decimal(float(key.num) / key.denom)
    return str(key)


def alter_style_class(style_class, target_widget, css_style):
    css_provider = Gtk.CssProvider()
    css = "%s { %s }" % (style_class, css_style)
    css_provider.load_from_data(css.encode('UTF-8'))
    style_context = target_widget.get_style_context()
    style_context.add_provider(
        css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def set_children_state_recurse(widget, state):
    widget.set_state_flags(state, False)
    for child in widget.get_children():
        child.set_state_flags(state, False)
        if isinstance(child, Gtk.Container):
            set_children_state_recurse(child, state)


def unset_children_state_recurse(widget, state):
    widget.unset_state_flags(state)
    for child in widget.get_children():
        child.unset_state_flags(state)
        if isinstance(child, Gtk.Container):
            unset_children_state_recurse(child, state)


def disable_scroll(widget):
    """Makes sure the specified widget does not react to scroll events."""
    def scroll_event_cb(widget, unused_event):
        GObject.signal_stop_emission_by_name(widget, "scroll-event")
        return False

    widget.connect("scroll-event", scroll_event_cb)


def fix_infobar(infobar):
    # Work around https://bugzilla.gnome.org/show_bug.cgi?id=710888
    def make_sure_revealer_does_nothing(widget):
        if not isinstance(widget, Gtk.Revealer):
            return
        widget.set_transition_type(Gtk.RevealerTransitionType.NONE)
    infobar.forall(make_sure_revealer_does_nothing)


# ----------------------- encoding datas --------------------------------------- #
# FIXME This should into a special file
frame_rates = model((str, object), (
    # Translators: fps is for frames per second
    (_("%d fps") % 12, Gst.Fraction(12.0, 1.0)),
    (_("%d fps") % 15, Gst.Fraction(15.0, 1.0)),
    (_("%d fps") % 20, Gst.Fraction(20.0, 1.0)),
    (_("%.3f fps") % 23.976, Gst.Fraction(24000.0, 1001.0)),
    (_("%d fps") % 24, Gst.Fraction(24.0, 1.0)),
    (_("%d fps") % 25, Gst.Fraction(25.0, 1.0)),
    (_("%.2f fps") % 29.97, Gst.Fraction(30000.0, 1001.0)),
    (_("%d fps") % 30, Gst.Fraction(30.0, 1.0)),
    (_("%d fps") % 50, Gst.Fraction(50.0, 1.0)),
    (_("%.2f fps") % 59.94, Gst.Fraction(60000.0, 1001.0)),
    (_("%d fps") % 60, Gst.Fraction(60.0, 1.0)),
    (_("%d fps") % 120, Gst.Fraction(120.0, 1.0)),
))

audio_rates = model((str, int), (
    (_("%d kHz") % 8, 8000),
    (_("%d kHz") % 11, 11025),
    (_("%d kHz") % 12, 12000),
    (_("%d kHz") % 16, 16000),
    (_("%d kHz") % 22, 22050),
    (_("%d kHz") % 24, 24000),
    (_("%.1f kHz") % 44.1, 44100),
    (_("%d kHz") % 48, 48000),
    (_("%d kHz") % 96, 96000)))

audio_channels = model((str, int), (
    (_("6 Channels (5.1)"), 6),
    (_("4 Channels (4.0)"), 4),
    (_("Stereo"), 2),
    (_("Mono"), 1)))

# FIXME: are we sure the following tables correct?

pixel_aspect_ratios = model((str, object), (
    (_("Square"), Gst.Fraction(1, 1)),
    (_("480p"), Gst.Fraction(10, 11)),
    (_("480i"), Gst.Fraction(8, 9)),
    (_("480p Wide"), Gst.Fraction(40, 33)),
    (_("480i Wide"), Gst.Fraction(32, 27)),
    (_("576p"), Gst.Fraction(12, 11)),
    (_("576i"), Gst.Fraction(16, 15)),
    (_("576p Wide"), Gst.Fraction(16, 11)),
    (_("576i Wide"), Gst.Fraction(64, 45)),
))

display_aspect_ratios = model((str, object), (
    (_("Standard (4:3)"), Gst.Fraction(4, 3)),
    (_("DV (15:11)"), Gst.Fraction(15, 11)),
    (_("DV Widescreen (16:9)"), Gst.Fraction(16, 9)),
    (_("Cinema (1.37)"), Gst.Fraction(11, 8)),
    (_("Cinema (1.66)"), Gst.Fraction(166, 100)),
    (_("Cinema (1.85)"), Gst.Fraction(185, 100)),
    (_("Anamorphic (2.35)"), Gst.Fraction(235, 100)),
    (_("Anamorphic (2.39)"), Gst.Fraction(239, 100)),
    (_("Anamorphic (2.4)"), Gst.Fraction(24, 10)),
))
