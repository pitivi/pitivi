/* 
 * PiTiVi
 * Copyright (C) <2004> Edward G. Hervey <hervey_e@epita.fr>
 *                      Guillaume Casanova <casano_g@epita.fr>
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

#ifndef PITIVI_STOCKICONS_H
#define PITIVI_STOCKICONS_H

/*
 * Potentially, include other headers on which this header depends.
 */


#include	<gtk/gtk.h>
#include	<gdk/gdk.h>

#define PITIVI_STOCK_CUT		  "pitivi-cut"
#define PITIVI_STOCK_HAND		  "pitivi-hand"
#define PITIVI_STOCK_POINTER		  "pitivi-pointer"
#define PITIVI_STOCK_ZOOM		  "pitivi-zoom"
#define PITIVI_STOCK_NEW_PROJECT	  "pitivi-new-sample"
#define PITIVI_STOCK_SELECTION_GROW	  "pitivi-selection-grow"
#define PITIVI_STOCK_SELECT_ALL		  "pitivi-select-all"
#define PITIVI_STOCK_SELECT_NONE	  "pitivi-select-none"

#define PITIVI_STOCK_EFFECT_SOUND	  "pitivi-effects-sound"
#define PITIVI_STOCK_EFFECT_TV		  "pitivi-effects-tv"
#define PITIVI_STOCK_EFFECT_SOUNDTV	  "pitivi-effects-soundtv"
#define PITIVI_STOCK_EFFECT_CAT		  "pitivi-effects-category"
#define PITIVI_STOCK_EFFECT_CAT_OPEN	  "pitivi-effects-category-open"

#define PITIVI_STOCK_VIEWER_PLAY	  "pitivi-viewer-play"
#define PITIVI_STOCK_VIEWER_PAUSE	  "pitivi-viewer-pause"
#define PITIVI_STOCK_VIEWER_STOP	  "pitivi-viewer-stop"
#define PITIVI_STOCK_VIEWER_NEXT	  "pitivi-viewer-next"
#define PITIVI_STOCK_VIEWER_PREVIOUS	  "pitivi-viewer-previous"
#define PITIVI_STOCK_VIEWER_VOLUME        "pitivi-viewer-volume"
#define PITIVI_STOCK_VIEWER_VOLUMEMAX     "pitivi-viewer-volume-max"
#define PITIVI_STOCK_VIEWER_VOLUMEMINIMUM "pitivi-viewer-volume-min"
#define PITIVI_STOCK_VIEWER_VOLUMEMEDIUM  "pitivi-viewer-volume-medium"
#define PITIVI_STOCK_VIEWER_VOLUMEZERO    "pitivi-viewer-volume-zero"

void		pitivi_stockicons_register (void);

#endif
