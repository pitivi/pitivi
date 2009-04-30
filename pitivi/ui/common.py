from pitivi.settings import GlobalSettings
import cairo

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
