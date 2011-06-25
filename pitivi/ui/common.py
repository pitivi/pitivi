from pitivi.settings import GlobalSettings
import cairo
from pitivi.stream import VideoStream, AudioStream, TextStream, \
        MultimediaStream
from xml.sax.saxutils import escape
from urllib import unquote
from gettext import gettext as _
from gettext import ngettext
import gst
import gtk

GlobalSettings.addConfigSection("user-interface")
LAYER_HEIGHT_EXPANDED = 50
LAYER_HEIGHT_COLLAPSED = 15
LAYER_SPACING = 15
TRACK_SPACING = 8

SPACING = 6
PADDING = 6


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
      value: A 32bit or 64bit RGBA value.
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


def unpack_cairo_pattern(value):
    """Transforms the specified RGBA value into a SolidPattern object."""
    red, green, blue, alpha = unpack_color(value)
    return cairo.SolidPattern(
        red / 65535.0,
        green / 65535.0,
        blue / 65535.0,
        alpha / 65535.0)


def unpack_cairo_gradient(value):
    """Creates a LinearGradient object out of the specified RGBA value."""
    red, green, blue, alpha = unpack_color(value)
    gradient = cairo.LinearGradient(0, 0, 0, 50)
    gradient.add_color_stop_rgba(
        1.0,
        red / 65535.0,
        green / 65535.0,
        blue / 65535.0,
        alpha / 65535.0)
    gradient.add_color_stop_rgba(
        0,
        (red / 65535.0) * 1.5,
        (green / 65535.0) * 1.5,
        (blue / 65535.0) * 1.5,
        alpha / 65535.0)
    return gradient


def beautify_factory(factory):
    ranks = {VideoStream: 0, AudioStream: 1, TextStream: 2, MultimediaStream: 3}

    def stream_sort_key(stream):
        return ranks[type(stream)]

    streams = factory.getOutputStreams()
    streams.sort(key=stream_sort_key)
    return ("<b>" + escape(unquote(factory.name)) + "</b>\n" +
        "\n".join((beautify_stream(stream) for stream in streams)))


def factory_name(factory):
    return escape(unquote(factory.name))


def beautify_stream(stream):
    if type(stream) == AudioStream:
        if stream.raw:
            templ = ngettext("<b>Audio:</b> %d channel at %d <i>Hz</i> (%d <i>bits</i>)",
                    "<b>Audio:</b> %d channels at %d <i>Hz</i> (%d <i>bits</i>)",
                    stream.channels)
            templ = templ % (stream.channels, stream.rate, stream.width)
            return templ

        return _("<b>Unknown Audio format:</b> %s") % stream.audiotype

    elif type(stream) == VideoStream:
        if stream.raw:
            if stream.framerate.num:
                templ = _("<b>Video:</b> %d x %d <i>pixels</i> at %.2f<i>fps</i>")
                templ = templ % (stream.par * stream.width, stream.height,
                        float(stream.framerate))
            else:
                templ = _("<b>Image:</b> %d x %d <i>pixels</i>")
                templ = templ % (stream.par * stream.width, stream.height)
            return templ
        return _("<b>Unknown Video format:</b> %s") % stream.videotype

    elif type(stream) == TextStream:
        return _("<b>Text:</b> %s") % stream.texttype

    raise NotImplementedError


# from http://cairographics.org/cookbook/roundedrectangles/
def roundedrec(context, x, y, w, h, r=10):
    "Draw a rounded rectangle"
    #   A****BQ
    #  H      C
    #  *      *
    #  G      D
    #   F****E

    context.move_to(x + r, y)      # Move to A
    context.line_to(x + w - r, y)  # Straight line to B

    # Curve to C, Control points are both at Q
    context.curve_to(x + w, y, x + w, y, x + w, y + r)
    context.line_to(x + w, y + h - r)                               # Move to D
    context.curve_to(x + w, y + h, x + w, y + h, x + w - r, y + h)  # Curve to E
    context.line_to(x + r, y + h)                                   # Line to F
    context.curve_to(x, y + h, x, y + h, x, y + h - r)              # Curve to G
    context.line_to(x, y + r)                                       # Line to H
    context.curve_to(x, y, x, y, x + r, y)                          # Curve to A
    return


def model(columns, data):
    ret = gtk.ListStore(*columns)
    for datum in data:
        ret.append(datum)
    return ret

frame_rates = model((str, object), (
    # Translators: fps is for frames per second
    (_("%d fps") % 12, gst.Fraction(12.0, 1.0)),
    (_("%d fps") % 15, gst.Fraction(15.0, 1.0)),
    (_("%d fps") % 20, gst.Fraction(20.0, 1.0)),
    (_("%.3f fps") % 23.976, gst.Fraction(24000.0, 1001.0)),
    (_("%d fps") % 24, gst.Fraction(24.0, 1.0)),
    (_("%d fps") % 25, gst.Fraction(25.0, 1.0)),
    (_("%.2f fps") % 29.97, gst.Fraction(30000.0, 1001.0)),
    (_("%d fps") % 30, gst.Fraction(30.0, 1.0)),
    (_("%d fps") % 50, gst.Fraction(50.0, 1.0)),
    (_("%.2f fps") % 59.94, gst.Fraction(60000.0, 1001.0)),
    (_("%d fps") % 60, gst.Fraction(60.0, 1.0)),
    (_("%d fps") % 120, gst.Fraction(120.0, 1.0)),
))

audio_rates = model((str, int), (
    (_("%d KHz") % 8, 8000),
    (_("%d KHz") % 11, 11025),
    (_("%d KHz") % 22, 22050),
    (_("%.1f KHz") % 44.1, 44100),
    (_("%d KHz") % 48, 48000),
    (_("%d KHz") % 96, 96000)
))

audio_depths = model((str, int), (
    (_("%d bit") % 8, 8),
    (_("%d bit") % 16, 16),
    (_("%d bit") % 24, 24),
    (_("%d bit") % 32, 32)
))

audio_channels = model((str, int), (
    (_("6 Channels (5.1)"), 6),
    (_("4 Channels (4.0)"), 4),
    (_("Stereo"), 2),
    (_("Mono"), 1)
))


def set_combo_value(combo, value, default_index=-1):
    model = combo.props.model
    for i, row in enumerate(model):
        if row[1] == value:
            combo.set_active(i)
            return
    combo.set_active(default_index)


def get_combo_value(combo):
    active = combo.get_active()
    return combo.props.model[active][1]
