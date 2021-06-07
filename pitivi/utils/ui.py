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
# License along with this program; if not, see <http://www.gnu.org/licenses/>.
"""UI constants and various functions and classes that help with UI drawing."""
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from gettext import gettext as _
from gettext import ngettext
from typing import Optional
from typing import Tuple

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
from pitivi.utils.loggable import do_log
from pitivi.utils.loggable import ERROR
from pitivi.utils.loggable import INFO
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
MINI_LAYER_HEIGHT = 25
# The space between two layers.
SEPARATOR_HEIGHT = 1

CLIP_BORDER_WIDTH = 1

SMALL_THUMB_WIDTH = 64
# 128 is the normal size for thumbnails, but for *icons* it looks insane.
LARGE_THUMB_WIDTH = 96

# Drag and drop
FILE_TARGET_ENTRY = Gtk.TargetEntry.new("text/plain", 0, 0)
URI_TARGET_ENTRY = Gtk.TargetEntry.new("text/uri-list", 0, 0)
EFFECT_TARGET_ENTRY = Gtk.TargetEntry.new("pitivi/effect", 0, 0)

TOUCH_INPUT_SOURCES = (Gdk.InputSource.TOUCHPAD,
                       Gdk.InputSource.TRACKPOINT,
                       Gdk.InputSource.TABLET_PAD)

CURSORS = {
    GES.Edge.EDGE_START: Gdk.Cursor.new(Gdk.CursorType.LEFT_SIDE),
    GES.Edge.EDGE_END: Gdk.Cursor.new(Gdk.CursorType.RIGHT_SIDE)
}

NORMAL_CURSOR = Gdk.Cursor.new(Gdk.CursorType.LEFT_PTR)
DRAG_CURSOR = Gdk.Cursor.new(Gdk.CursorType.HAND1)

SCHEMA_SETTINGS_SOURCE = Gio.SettingsSchemaSource.get_default()


def get_month_format_string():
    """Returns the appropriate format string for month name in time.strftime() function."""
    # %OB produces the month name in nominative case.
    month_format_string = "%OB"
    if time.strftime(month_format_string) == "%OB":
        # %B produces the month name in genitive case.
        month_format_string = "%B"
    return month_format_string


# TODO: Drop this when we depend on glibc 2.27+
MONTH_FORMAT_STRING = get_month_format_string()


def _get_settings(schema_id: str) -> Optional[Gio.Settings]:
    if SCHEMA_SETTINGS_SOURCE is None:
        return None
    schema = SCHEMA_SETTINGS_SOURCE.lookup(schema_id, recursive=False)
    if not schema:
        return None
    return Gio.Settings.new_full(schema, backend=None, path=None)


def _get_font_scaling_factor() -> float:
    scaling_factor = 1.0
    settings = _get_settings("org.gnome.desktop.interface")
    if settings:
        if "text-scaling-factor" in settings.list_keys():
            scaling_factor = settings.get_double("text-scaling-factor")
    return scaling_factor


def _get_font(font_spec: str, default: str) -> str:
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
FONT_SCALING_FACTOR = _get_font_scaling_factor()


GREETER_PERSPECTIVE_CSS = """
    #empty_greeter_msg_title {
        font-size: 125%;
        font-weight: bold;
    }

    #recent_projects_listbox {
        border: 1px solid alpha(@borders, 0.6);
    }

    #recent_projects_listbox row {
        padding: 12px 12px 12px 12px;
        border-bottom: 1px solid alpha(@borders, 0.2);
    }

    #recent_projects_listbox row:last-child {
        border-bottom-width: 0px;
    }

    #project_name_label {
        font-weight: bold;
    }

    #project_uri_label,
    #project_last_updated_label,
    #empty_greeter_msg_subtitle {
        opacity: 0.55;
    }

    #recent_projects_labelbox {
        color: @insensitive_fg_color;
        padding-bottom: 6px;
    }

    #recent_projects_labelbox > label:backdrop {
        color: @unfocused_insensitive_color;
    }

    #recent_projects_label {
        font-weight: bold;
    }

    #project_thumbnail_box {
        background-color: #181818;
    }
"""

EDITOR_PERSPECTIVE_CSS = """
    #resize_status {
        font-size: 200%%;
        background-color: black;
        opacity: 0.8;
    }

    .LayerControlEntry:not(:focus) {
        border: 1px solid transparent;
        background: transparent;
    }


    .AudioBackground,
    .VideoBackground {
        transition: background-color 200ms ease-out, border-color 200ms ease-out;
    }

    .UriClip .AudioBackground {
        background-color: rgb(60, 97, 43);
        border: %(clip_border_width)spx solid shade(rgb(60, 97, 43), 1.2);
    }

    .UriClip .VideoBackground {
        background-color: rgb(25, 25, 25);
        border: %(clip_border_width)spx solid shade(rgb(25, 25, 25), 2.5);
    }

    .TitleClip .VideoBackground {
        background-color: rgb(94, 78, 102);
        border: %(clip_border_width)spx solid shade(rgb(25, 25, 25), 2.5);
    }

    .AudioBackground:selected,
    .VideoBackground:selected {
        border-color: rgb(132, 131, 79)
    }

    .UriClip .AudioBackground:selected {
        background-color: shade(rgb(60, 97, 43), 0.4);
    }

    .UriClip .VideoBackground:selected {
        background-color: shade(rgb(25, 25, 25), 0.4);
    }

    .TitleClip .VideoBackground:selected  {
        background-color: shade(rgb(94, 78, 102), 0.4);
    }


    .Thumbnail {
        transition: opacity 200ms linear;
        opacity: 1;
     }

    .VideoPreviewer:selected,
    .AudioPreviewer:selected,
    .MiniPreviewer:selected,
    .TitlePreviewer:selected {
        opacity: 0.15;
    }

    .KeyframeCurve {
        background-color: rgba(0, 0, 0, 0);
    }

    .Trimbar {
        background-image: url('%(trimbar_normal)s');
        opacity: 0.5;
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

    /* Background inside the timeline */
    .Timeline {
        background: shade(@theme_bg_color, 0.75);
    }

    /* Background in the layers list */
    .Timeline viewport {
        background: @theme_bg_color;
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
        background-color: rgba(0, 0, 0, 0.3);
    }

    .Marquee {
        background-color: rgba(224, 224, 224, 0.7);
        color: rgba(224, 224, 224, 1);
    }

    .MarkersBox {
        background-color: rgba(224, 224, 224, 0);
    }

    .Marker {
        background-image: url('%(marker_unselected)s');
    }

    .Marker:hover {
        background-image: url('%(marker_hovered)s');
    }

    .Marker:selected {
        background-image: url('%(marker_hovered)s');
    }

    .ClipMarkersBox {
        transition: 0.15s ease-out;
        opacity: 0.7;
    }

    .ClipMarkersBox:hover {
        background-color: rgba(0, 0, 0, 0.15);
        opacity: 0.85;
    }

    .ClipMarkersBox:selected {
        background-color: rgb(0, 0, 0);
        opacity: 1;
    }

    .ClipMarker {
        background-image: url('%(clip_marker_unselected)s');
    }

    .ClipMarker:hover {
        background-image: url('%(clip_marker_hovered)s');
    }

    .ClipMarker:selected {
        background-image: url('%(clip_marker_selected)s');
    }

""" % ({
    'clip_border_width': CLIP_BORDER_WIDTH,
    'marker_hovered': os.path.join(get_pixmap_dir(), "marker-hover.png"),
    'marker_unselected': os.path.join(get_pixmap_dir(), "marker-unselect.png"),
    'clip_marker_unselected': os.path.join(get_pixmap_dir(), "clip-marker.png"),
    'clip_marker_hovered': os.path.join(get_pixmap_dir(), "clip-marker-hover.png"),
    'clip_marker_selected': os.path.join(get_pixmap_dir(), "clip-marker-select.png"),
    'trimbar_focused': os.path.join(get_pixmap_dir(), "trimbar-focused.png"),
    'trimbar_normal': os.path.join(get_pixmap_dir(), "trimbar-normal.png")})


PREFERENCES_CSS = """
    .sidebar list {
        background: @content_view_bg;
    }

    .sidebar row {
        padding: 10px 40px 10px 4px;
    }

    .prefs_list row {
        border-left: 1px solid rgb(32, 32, 32);
        border-right: 1px solid rgb(32, 32, 32);
        border-bottom: 1px solid rgba(25, 25, 25, 0.2);
    }

    .prefs_list .first {
        border-top: 1px solid rgb(32, 32, 32);
    }

    /* This covers the case for the last item in a group,
       and the last item in the list */
    .prefs_list,
    .prefs_list .last {
        border-bottom: 1px solid rgb(32, 32, 32);
    }
"""


def format_framerate_value(framerate):
    """Formats the framerate or returns 0 if unable to determine it."""
    if isinstance(framerate, DiscovererVideoInfo):
        num = framerate.get_framerate_num()
        denom = framerate.get_framerate_denom()
        framerate = Gst.Fraction(num, denom)

    if framerate.denom == 0:
        return "0"

    value = framerate.num / framerate.denom
    # Keep maximum 3 decimals.
    value = value * 1000 // 1 / 1000
    return "{0:n}".format(value)


def format_framerate(framerate):
    """Formats the framerate for display."""
    # Translators: 'fps' is for 'frames per second'
    return _("{0:s} fps").format(format_framerate_value(framerate))


def format_audiorate(rate):
    """Formats the audiorate (in kHz) for display."""
    if isinstance(rate, DiscovererAudioInfo):
        rate = rate.get_sample_rate()

    # We need to use "n" to format the number according to the locale:
    # https://www.python.org/dev/peps/pep-3101/#id20
    # It's tricky specifying the "precision". For example:
    # "{0:.1n}".format(44.1) == "4e+01"
    # Seems the only way to control the number of decimals is by massaging
    # the value.
    if rate // 100 % 10:
        # Show one (significant) decimal.
        rate = rate // 100 / 10
    else:
        # Show no decimals.
        rate = rate // 1000
    return _("{0:n} kHz").format(rate)


def format_audiochannels(channels):
    """Formats the audio channels for display."""
    if isinstance(channels, DiscovererAudioInfo):
        channels = channels.get_channels()

    unique_vals = {
        1: _("Mono"),
        2: _("Stereo"),
        6: _("6 (5.1)"),
        8: _("8 (7.1)")}
    try:
        return unique_vals[channels]
    except KeyError:
        return str(channels)


# ---------------------- ARGB color helper-------------------------------------#


def gtk_style_context_get_color(context, state):
    context.save()
    context.set_state(state)
    color = context.get_color(context.get_state())
    context.restore()
    return color


def argb_to_gdk_rgba(argb: int) -> Gdk.RGBA:
    return Gdk.RGBA(((argb >> 16) & 0xFF) / 255,
                    ((argb >> 8) & 0xFF) / 255,
                    ((argb >> 0) & 0xFF) / 255,
                    ((argb >> 24) & 0xFF) / 255)


def gdk_rgba_to_argb(color: Gdk.RGBA) -> int:
    return ((int(color.alpha * 255) << 24) +
            (int(color.red * 255) << 16) +
            (int(color.green * 255) << 8) +
            int(color.blue * 255))


def pack_color_32(red, green, blue, alpha=0xFFFF):
    """Packs the specified 16bit color values in a 32bit RGBA value."""
    red = red >> 8
    green = green >> 8
    blue = blue >> 8
    alpha = alpha >> 8
    return red << 24 | green << 16 | blue << 8 | alpha


def pack_color_64(red, green, blue, alpha=0xFFFF):
    """Packs the specified 16bit color values in a 64bit RGBA value."""
    return red << 48 | green << 32 | blue << 16 | alpha


def unpack_color(value):
    """Unpacks the specified RGBA value into four 16bit color values.

    Args:
        value (int): A 32bit or 64bit RGBA value.
    """
    if not value >> 32:
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


def set_cairo_color(context, color):
    if isinstance(color, Gdk.RGBA):
        cairo_color = (float(color.red), float(color.green), float(color.blue))
    elif isinstance(color, tuple):
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
    from pitivi.utils.proxy import get_proxy_target
    uri = get_proxy_target(asset).props.id
    path = path_from_uri(uri)
    res = ["<b>" + GLib.markup_escape_text(path) + "</b>"]

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
    streams = info.get_stream_list()
    streams.sort(key=stream_sort_key)
    for stream in streams:
        try:
            beautified_string = beautify_stream(stream)
        except NotImplementedError:
            do_log(ERROR, "Beautify", "None", "Cannot beautify %s", stream)
            continue
        if beautified_string:
            res.append(beautified_string)

    duration = beautify_length(asset.get_duration())
    if duration:
        res.append(_("<b>Duration:</b> %s") % duration)

    if asset.creation_progress < 100:
        res.append(_("<b>Proxy creation progress:</b> %d%%") %
                   asset.creation_progress)

    return "\n".join(res)


def beautify_missing_asset(asset):
    """Formats the specified missing asset for display.

    Args:
        asset (GES.UriClipAsset): The asset to display.
    """
    uri = asset.get_id()
    path = path_from_uri(uri)
    res = [_("<b>Path</b>: %s") % GLib.markup_escape_text(path)]

    duration = beautify_length(asset.get_duration())
    if duration:
        res.append(_("<b>Duration</b>: %s") % duration)

    size = asset.get_meta("file-size")
    if size:
        file_size = GLib.format_size_full(
            size, GLib.FormatSizeFlags.LONG_FORMAT)
        res.append(_("<b>Size</b>: %s") % file_size)

    return "\n".join(res)


def info_name(info):
    """Returns a human-readable filename (without the path and quoting).

    Args:
        info (GES.Asset or DiscovererInfo): The info to display.
    """
    if isinstance(info, GES.Asset):
        from pitivi.utils.proxy import get_proxy_target
        filename = urllib.parse.unquote(
            os.path.basename(get_proxy_target(info).get_id()))
    elif isinstance(info, DiscovererInfo):
        filename = urllib.parse.unquote(os.path.basename(info.get_uri()))
    else:
        raise Exception("Unsupported argument type: %s" % type(info))
    return GLib.markup_escape_text(filename)


def beautify_project_path(path):
    """Beautifies project path by shortening the home directory path (if present)."""
    home_dir = os.path.expanduser("~")
    if path.startswith(home_dir):
        return path.replace(home_dir, "~")
    return path


def beautify_stream(stream):
    if isinstance(stream, DiscovererAudioInfo):
        if stream.get_depth() == 0:
            return None

        templ = ngettext(
            "<b>Audio:</b> %d channel at %d <i>Hz</i> (%d <i>bits</i>)",
            "<b>Audio:</b> %d channels at %d <i>Hz</i> (%d <i>bits</i>)",
            stream.get_channels())
        return templ % (stream.get_channels(), stream.get_sample_rate(),
                        stream.get_depth())

    elif isinstance(stream, DiscovererVideoInfo):
        par = stream.get_par_num() / stream.get_par_denom()
        width = stream.get_natural_width()
        height = stream.get_natural_height()
        if not stream.is_image():
            fps = format_framerate_value(stream)
            templ = _("<b>Video:</b> %d×%d <i>pixels</i> at %s <i>fps</i>")
            return templ % (par * width, height, fps)
        else:
            templ = _("<b>Image:</b> %d×%d <i>pixels</i>")
            return templ % (par * width, height)

    elif isinstance(stream, DiscovererSubtitleInfo):
        # Ignore subtitle streams
        return None

    elif isinstance(stream, DiscovererStreamInfo):
        caps = stream.get_caps().to_string()
        if caps in ("application/x-subtitle", "application/x-id3", "text"):
            # Ignore all audio ID3 tags and subtitle tracks, we don't show them
            return None

    raise ValueError("Unsupported stream type: %s" % stream)


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


def beautify_eta(length_nanos):
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


def beautify_last_updated_timestamp(last_updated_timestamp):
    """Returns a rough estimation of how long ago the timestamp is."""
    delta_seconds = int(time.time()) - last_updated_timestamp

    if delta_seconds < 60 * 45:
        return _("Just now")

    if delta_seconds < 60 * 90:
        return _("An hour ago")

    if delta_seconds < 60 * 60 * 24:
        return _("Today")

    if delta_seconds < 60 * 60 * 24 * 2:
        return _("Yesterday")

    if delta_seconds < 60 * 60 * 24 * 7:
        return time.strftime("%A", time.localtime(last_updated_timestamp))

    if delta_seconds < 60 * 60 * 24 * 365:
        return time.strftime(MONTH_FORMAT_STRING, time.localtime(last_updated_timestamp))

    if delta_seconds < 60 * 60 * 24 * 365 * 1.5:
        return _("About a year ago")

    years = max(2, delta_seconds / (60 * 60 * 24 * 365))
    return ngettext("About %d year ago",
                    "About %d years ago", years) % years


# -------------------- Gtk widget helpers ----------------------------------- #

class BinWithNaturalWidth(Gtk.Bin):
    """A bin with a maximum width."""

    def __init__(self, child, width, *args, **kwargs):
        Gtk.Bin.__init__(self, *args, **kwargs)
        self.natural_width = width
        self.add(child)

    def do_get_request_mode(self):
        return Gtk.SizeRequestMode.HEIGHT_FOR_WIDTH

    def do_get_preferred_width(self):
        minimum, _ = Gtk.Bin.do_get_preferred_width(self)
        minimum = min(minimum, self.natural_width)
        return minimum, self.natural_width


def clear_styles(widget):
    """Makes sure the widget has no border, background or other decorations.

    Args:
        widget (Gtk.Widget): The widget to clean up.
    """
    style = widget.get_style_context()
    for css_class in style.list_classes():
        style.remove_class(css_class)


def create_model(columns, data) -> Gtk.ListStore:
    model = Gtk.ListStore(*columns)
    for datum in data:
        model.append(datum)
    return model


def create_frame_rates_model(extra_rate: Optional[Tuple[int, int]] = None) -> Gtk.ListStore:
    """Creates a framerate model based on our list of standard frame rates.

    Args:
        extra_rate: An extra frame rate to include in model.
    """
    rates = list(FRAME_RATES)
    if extra_rate and extra_rate not in rates:
        rates.append(extra_rate)
    rates.sort(key=lambda x: x[0] / x[1])

    items = []
    for fps in rates:
        fraction = Gst.Fraction(*fps)
        item = (format_framerate(fraction), fraction)
        items.append(item)

    return create_model((str, object), items)


def create_audio_rates_model(extra_rate: Optional[int] = None):
    rates = list(AUDIO_RATES)
    if extra_rate and extra_rate not in rates:
        rates.append(extra_rate)
    rates.sort()

    return create_model((str, int),
                        [(format_audiorate(rate), rate) for rate in rates])


def set_combo_value(combo, value):
    def select_specific_row(model, unused_path, iter_, found):
        model_value = model.get_value(iter_, 1)
        if value == model_value:
            combo.set_active_iter(iter_)
            found.append(1)
            return True
        return False

    found = []
    combo.props.model.foreach(select_specific_row, found)

    if len(found) != 1:
        do_log(INFO, None, "utils",
               "Could not set value %s, possible values: %s",
               (value, [v[1] for v in combo.props.model]))
        return False

    return True


def get_combo_value(combo):
    active_iter = combo.get_active_iter()
    if not active_iter:
        return None
    return combo.props.model.get_value(active_iter, 1)


def alter_style_class(style_class, target_widget, css_style):
    css_provider = Gtk.CssProvider()
    css = "%s { %s }" % (style_class, css_style)
    css_provider.load_from_data(css.encode('UTF-8'))
    style_context = target_widget.get_style_context()
    style_context.add_provider(
        css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def set_state_flags_recurse(widget, state_flags, are_set, ignored_classes=()):
    """Sets the provided state on all children of the given widget."""
    if isinstance(widget, ignored_classes):
        return

    if are_set:
        widget.set_state_flags(state_flags, clear=False)
    else:
        widget.unset_state_flags(state_flags)

    if isinstance(widget, Gtk.Container):
        for child in widget.get_children():
            set_state_flags_recurse(child, state_flags, are_set, ignored_classes)


def disable_scroll_event_cb(widget, unused_event):
    GObject.signal_stop_emission_by_name(widget, "scroll-event")
    return False


def disable_scroll(widget):
    """Disables scrolling on the specified widget and its children recursively.

    Makes sure the vulnerable widgets do not react to scroll events.
    """
    if isinstance(widget, Gtk.Container):
        widget.foreach(disable_scroll)

    if isinstance(widget, (Gtk.ComboBox, Gtk.Scale, Gtk.SpinButton)):
        widget.connect("scroll-event", disable_scroll_event_cb)


def fix_infobar(infobar):
    # Work around https://bugzilla.gnome.org/show_bug.cgi?id=710888
    def make_sure_revealer_does_nothing(widget):
        if not isinstance(widget, Gtk.Revealer):
            return
        widget.set_transition_type(Gtk.RevealerTransitionType.NONE)
    infobar.forall(make_sure_revealer_does_nothing)


AUDIO_CHANNELS = create_model((str, int),
                              [(format_audiochannels(ch), ch)
                               for ch in (8, 6, 4, 2, 1)])

FRAME_RATES = [(12, 1),
               (15, 1),
               (20, 1),
               (24000, 1001),
               (24, 1),
               (25, 1),
               (30000, 1001),
               (30, 1),
               (50, 1),
               (60000, 1001),
               (60, 1),
               (120, 1)]

AUDIO_RATES = [8000,
               11025,
               12000,
               16000,
               22050,
               24000,
               44100,
               48000,
               96000]

# This whitelist is made from personal knowledge of file extensions in the wild,
# from gst-inspect |grep demux,
# http://en.wikipedia.org/wiki/Comparison_of_container_formats and
# http://en.wikipedia.org/wiki/List_of_file_formats#Video
# ...and looking at the contents of /usr/share/mime
SUPPORTED_FILE_FORMATS = {
    "video": ("3gpp", "3gpp2", "dv", "mp2t", "mp2t", "mp4", "mpeg", "ogg",
              "quicktime", "webm", "x-flv", "x-matroska", "x-mng", "x-ms-asf",
              "x-ms-wmp", "x-ms-wmv", "x-msvideo", "x-ogm+ogg", "x-theora+ogg"),
    "application": ("mxf",),
    "audio": ("aac", "ac3", "basic", "flac", "mp2", "mp4", "mpeg", "ogg",
              "opus", "webm", "x-adpcm", "x-aifc", "x-aiff", "x-aiffc",
              "x-ape", "x-flac+ogg", "x-m4b", "x-matroska", "x-ms-asx",
              "x-ms-wma", "x-speex", "x-speex+ogg", "x-vorbis+ogg", "x-wav"),
    "image": ("jp2", "jpeg", "png", "svg+xml")}

SUPPORTED_MIMETYPES = []
for category, mime_types in SUPPORTED_FILE_FORMATS.items():
    for mime in mime_types:
        SUPPORTED_MIMETYPES.append(category + "/" + mime)


def filter_unsupported_media_files(filter_info):
    """Returns whether the specified item should be displayed."""
    from pitivi.utils.proxy import ProxyManager

    if filter_info.mime_type not in SUPPORTED_MIMETYPES:
        return False

    if ProxyManager.is_proxy_asset(filter_info.uri):
        return False

    return True
