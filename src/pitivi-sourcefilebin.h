/* 
 * PiTiVi
 * Copyright (C) <2004>		Edward Hervey <bilboed@bilboed.com>
 *
 * This software has been written in EPITECH <http://www.epitech.net>
 * EPITECH is a computer science school in Paris - FRANCE -
 * under the direction of Flavien Astraud and Jerome Landrieu.
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public
 * License along with this program; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */

#ifndef PITIVI_SOURCEFILEBIN_H
#define PITIVI_SOURCEFILEBIN_H

#include <gst/gst.h>
#include "pitivi-types.h"
#include "pitivi-sourcefile.h"

GstElement	*pitivi_sourcefile_bin_new (PitiviSourceFile *self, int type, PitiviMainApp *mainapp);

#endif
