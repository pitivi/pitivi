from pitivi.settings import GlobalSettings
import cairo
from pitivi.stream import VideoStream, AudioStream, TextStream, \
        MultimediaStream
from xml.sax.saxutils import escape
from urllib import unquote
from gettext import gettext as _
from gettext import ngettext

GlobalSettings.addConfigSection("user-interface")
LAYER_HEIGHT_EXPANDED = 50
LAYER_HEIGHT_COLLAPSED = 15
LAYER_SPACING = 5
TRACK_SPACING = 5

def pack_color_32(red, green, blue, alpha = 0xFFFF):
   red = red >> 8
   green = green >> 8
   blue = blue >> 8
   alpha = alpha >> 8
   return (red << 24 | green << 16 | blue << 8 | alpha)

def pack_color_64(red, green, blue, alpha = 0xFFFF):
   return (red << 48 | green << 32 | blue << 16 | alpha)

def unpack_color(value):
    if not (value >> 32):
        return unpack_color_32(value)
    else:
        return unpack_color_64(value)

def unpack_color_32(value):
    red = (value >> 24); red = red | red << 8
    green = (value >> 16) & 0xFF; green = green | green << 8
    blue = (value >> 8) & 0xFF; blue = blue | blue << 8
    alpha = value & 0xFF; alpha = alpha | alpha << 8
    return red, green, blue, alpha

def unpack_color_64(value):
    red = (value >> 48) & 0xFFFF
    green = (value >> 32) & 0xFFFF
    blue = (value >> 16) & 0xFFFF
    alpha = value & 0xFFFF
    return red, green, blue, alpha

def unpack_cairo_pattern(value):
    red, green, blue, alpha = unpack_color(value)
    return cairo.SolidPattern(
        red / 65535.0,
        green / 65535.0,
        blue / 65535.0,
        alpha / 65535.0)

def unpack_cairo_gradient(value):
    red, green, blue, alpha = unpack_color(value)
    ret = cairo.LinearGradient(0,0, 0, 50)
    ret.add_color_stop_rgba(50,
        red / 65535.0,
        green / 65535.0,
        blue / 65535.0,
        alpha / 65535.0)
    ret.add_color_stop_rgba(0,
        (red / 65535.0) * 1.5,
        (green / 65535.0) * 1.5,
        (blue / 65535.0) * 1.5,
        alpha / 65535.0)
    return ret

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
                templ = templ % (stream.par * stream.width , stream.height,
                        float(stream.framerate))
            else:
                templ = _("<b>Image:</b> %d x %d <i>pixels</i>")
                templ = templ % (stream.par * stream.width, stream.height)
            return templ
        return _("<b>Unknown Video format:</b> %s") % stream.videotype

    elif type(stream) == TextStream:
        return _("<b>Text:</b> %s") % stream.texttype

    raise NotImplementedError

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
                templ = templ % (stream.par * stream.width , stream.height,
                        float(stream.framerate))
            else:
                templ = _("<b>Image:</b> %d x %d <i>pixels</i>")
                templ = templ % (stream.par * stream.width, stream.height)
            return templ
        return _("<b>Unknown Video format:</b> %s") % stream.videotype

    elif type(stream) == TextStream:
        return _("<b>Text:</b> %s") % stream.texttype

    raise NotImplementedError

