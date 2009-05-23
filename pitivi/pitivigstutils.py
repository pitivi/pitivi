# PiTiVi , Non-linear video editor
#
#       pitivi/pitivigstutils.py
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
Additional methods for gst object to simplify code in pitivi.
Might contain code already available in gst-python, but we keep it here so
that we don't have to depend on too recent versions of gst-python.
"""

import gst
import gst.interfaces
import gst.audio
import gst.video

def fraction_float(frac):
    """ override for gst.Fraction.__float__ """
    return float(frac.num) / float(frac.denom)

def fraction_eq(frac, other):
    """ override for gst.Fraction.__eq__ """
    if isinstance(other, gst.Fraction):
        return frac.num * other.denom == frac.denom * other.num
    return False

def fraction_ne(frac, other):
    """ override for gst.Fraction.__ne__ """
    return not fraction_eq(frac, other)

def fraction_mul(frac, other):
    """ override for gst.Fraction.__mul__ """
    if isinstance(other, gst.Fraction):
        return gst.Fraction(frac.num * other.num,
                            frac.denom * other.denom)
    elif isinstance(other, int):
        return frac.num * other / frac.denom
    elif isinstance(other, float):
        return float(frac.num) * other / float(frac.denom)
    raise TypeError

def fraction_div(frac, other):
    """ override for gst.Fraction.__div__ """
    if isinstance(other, int):
        return frac.num / (frac.denom * other)
    if isinstance(other, float):
        return float(frac.num) / (other * float(frac.denom))
    return TypeError

def patch_gst_python():
    """ override gst.Fraction methods not available in all gst-python """
    gst.Fraction.__float__ = fraction_float
    gst.Fraction.__eq__ = fraction_eq
    gst.Fraction.__ne__ = fraction_ne
    gst.Fraction.__mul__ = fraction_mul
    gst.Fraction.__div__ = fraction_div
