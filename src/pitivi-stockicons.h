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


#define PITIVI_SMPTE_1		"smpte1"
#define PITIVI_SMPTE_2		"smpte2" 
#define PITIVI_SMPTE_3		"smpte3" 
#define PITIVI_SMPTE_4		"smpte4" 
#define PITIVI_SMPTE_5		"smpte5" 
#define PITIVI_SMPTE_6		"smpte6" 
#define PITIVI_SMPTE_23		"smpte23" 
#define PITIVI_SMPTE_24		"smpte24" 
#define PITIVI_SMPTE_25		"smpte25" 
#define PITIVI_SMPTE_26		"smpte26" 
#define PITIVI_SMPTE_7		"smpte7" 
#define PITIVI_SMPTE_8		"smpte8" 
#define PITIVI_SMPTE_21		"smpte21" 
#define PITIVI_SMPTE_22		"smpte22" 
#define PITIVI_SMPTE_45		"smpte45" 
#define PITIVI_SMPTE_46		"smpte46" 
#define PITIVI_SMPTE_41		"smpte41" 
#define PITIVI_SMPTE_42		"smpte42" 
#define PITIVI_SMPTE_43		"smpte43" 
#define PITIVI_SMPTE_44		"smpte44" 
#define PITIVI_SMPTE_47		"smpte47" 
#define PITIVI_SMPTE_48		"smpte48" 
#define PITIVI_SMPTE_61		"smpte61" 
#define PITIVI_SMPTE_62		"smpte62" 
#define PITIVI_SMPTE_63		"smpte63" 
#define PITIVI_SMPTE_64		"smpte64" 
#define PITIVI_SMPTE_65		"smpte65" 
#define PITIVI_SMPTE_66		"smpte66" 
#define PITIVI_SMPTE_67		"smpte67" 
#define PITIVI_SMPTE_68		"smpte68" 
#define PITIVI_SMPTE_101	"smpte101" 
#define PITIVI_SMPTE_102	"smpte102" 
#define PITIVI_SMPTE_201	"smpte201" 
#define PITIVI_SMPTE_202	"smpte202" 
#define PITIVI_SMPTE_203	"smpte203" 
#define PITIVI_SMPTE_204	"smpte204" 
#define PITIVI_SMPTE_205	"smpte205" 
#define PITIVI_SMPTE_206	"smpte206" 
#define PITIVI_SMPTE_207	"smpte207" 
#define PITIVI_SMPTE_211	"smpte211" 
#define PITIVI_SMPTE_212	"smpte212" 
#define PITIVI_SMPTE_231	"smpte231" 
#define PITIVI_SMPTE_232	"smpte232" 
#define PITIVI_SMPTE_233	"smpte233" 
#define PITIVI_SMPTE_234	"smpte234" 
#define PITIVI_SMPTE_213	"smpte213" 
#define PITIVI_SMPTE_214	"smpte214" 
#define PITIVI_SMPTE_235	"smpte235" 
#define PITIVI_SMPTE_236	"smpte236" 
#define PITIVI_SMPTE_221	"smpte221" 
#define PITIVI_SMPTE_222	"smpte222" 
#define PITIVI_SMPTE_223	"smpte223" 
#define PITIVI_SMPTE_224	"smpte224" 
#define PITIVI_SMPTE_241	"smpte241" 
#define PITIVI_SMPTE_242	"smpte242" 
#define PITIVI_SMPTE_243	"smpte243" 
#define PITIVI_SMPTE_244	"smpte244" 
#define PITIVI_SMPTE_225	"smpte225" 
#define PITIVI_SMPTE_226	"smpte226" 
#define PITIVI_SMPTE_227	"smpte227" 
#define PITIVI_SMPTE_228	"smpte228" 
#define PITIVI_SMPTE_245	"smpte245" 
#define PITIVI_SMPTE_246	"smpte246"
#define PITIVI_SMPTE_251	"smpte251"
#define PITIVI_SMPTE_252	"smpte252"
#define PITIVI_SMPTE_253	"smpte253"
#define PITIVI_SMPTE_254	"smpte254"
#define PITIVI_SMPTE_261	"smpte261"
#define PITIVI_SMPTE_262	"smpte262"
#define PITIVI_SMPTE_263	"smpte263"
#define PITIVI_SMPTE_264	"smpte264"
#define PITIVI_SMPTE_FAILED	"smpte-failed"

void		pitivi_stockicons_register (void);

#endif
