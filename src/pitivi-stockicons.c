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

#include "pitivi.h"
#include "pitivi-stockicons.h"

static const char *items [] =
  {
	PITIVI_STOCK_CUT,
	PITIVI_STOCK_HAND,
	PITIVI_STOCK_POINTER,
	PITIVI_STOCK_ZOOM,
	PITIVI_STOCK_EFFECT_CAT,
	PITIVI_STOCK_EFFECT_CAT_OPEN,
	PITIVI_STOCK_EFFECT_SOUND,
	PITIVI_STOCK_EFFECT_TV,
	PITIVI_STOCK_EFFECT_SOUNDTV,
	PITIVI_STOCK_VIEWER_PLAY,
	PITIVI_STOCK_VIEWER_PAUSE,
	PITIVI_STOCK_VIEWER_STOP,
	PITIVI_STOCK_VIEWER_NEXT,
	PITIVI_STOCK_VIEWER_PREVIOUS,
	PITIVI_STOCK_VIEWER_VOLUME,
	PITIVI_STOCK_VIEWER_VOLUMEMAX,
	PITIVI_STOCK_VIEWER_VOLUMEMEDIUM,
	PITIVI_STOCK_VIEWER_VOLUMEMINIMUM,
	PITIVI_STOCK_VIEWER_VOLUMEZERO,
	PITIVI_SMPTE_1, 
	PITIVI_SMPTE_2, 
	PITIVI_SMPTE_3, 
	PITIVI_SMPTE_4, 
	PITIVI_SMPTE_5, 
	PITIVI_SMPTE_6, 
	PITIVI_SMPTE_23, 
	PITIVI_SMPTE_24, 
	PITIVI_SMPTE_25, 
	PITIVI_SMPTE_26, 
	PITIVI_SMPTE_7, 
	PITIVI_SMPTE_8, 
	PITIVI_SMPTE_21, 
	PITIVI_SMPTE_22, 
	PITIVI_SMPTE_45, 
	PITIVI_SMPTE_46, 
	PITIVI_SMPTE_41, 
	PITIVI_SMPTE_42, 
	PITIVI_SMPTE_43, 
	PITIVI_SMPTE_44, 
	PITIVI_SMPTE_47, 
	PITIVI_SMPTE_48, 
	PITIVI_SMPTE_61, 
	PITIVI_SMPTE_62, 
	PITIVI_SMPTE_63, 
	PITIVI_SMPTE_64, 
	PITIVI_SMPTE_65, 
	PITIVI_SMPTE_66, 
	PITIVI_SMPTE_67, 
	PITIVI_SMPTE_68, 
	PITIVI_SMPTE_101, 
	PITIVI_SMPTE_102, 
	PITIVI_SMPTE_201, 
	PITIVI_SMPTE_202, 
	PITIVI_SMPTE_203, 
	PITIVI_SMPTE_204, 
	PITIVI_SMPTE_205, 
	PITIVI_SMPTE_206, 
	PITIVI_SMPTE_207, 
	PITIVI_SMPTE_211, 
	PITIVI_SMPTE_212, 
	PITIVI_SMPTE_231, 
	PITIVI_SMPTE_232, 
	PITIVI_SMPTE_233, 
	PITIVI_SMPTE_234, 
	PITIVI_SMPTE_213, 
	PITIVI_SMPTE_214, 
	PITIVI_SMPTE_235, 
	PITIVI_SMPTE_236, 
	PITIVI_SMPTE_221, 
	PITIVI_SMPTE_222, 
	PITIVI_SMPTE_223, 
	PITIVI_SMPTE_224, 
	PITIVI_SMPTE_241, 
	PITIVI_SMPTE_242, 
	PITIVI_SMPTE_243, 
	PITIVI_SMPTE_244, 
	PITIVI_SMPTE_225, 
	PITIVI_SMPTE_226, 
	PITIVI_SMPTE_227, 
	PITIVI_SMPTE_228, 
	PITIVI_SMPTE_245, 
	PITIVI_SMPTE_246,
	PITIVI_SMPTE_251,
	PITIVI_SMPTE_252,
	PITIVI_SMPTE_253,
	PITIVI_SMPTE_254,
	PITIVI_SMPTE_261,
	PITIVI_SMPTE_262,
	PITIVI_SMPTE_263,
	PITIVI_SMPTE_264
  };

void
pitivi_stockicons_register (void)
{
  GtkIconFactory	*factory;
  int			i;
  
  factory = gtk_icon_factory_new ();
  gtk_icon_factory_add_default (factory);

  for (i = 0; i < (int) G_N_ELEMENTS (items); i++) {
    GtkIconSet *icon_set;
    GdkPixbuf *pixbuf;
    char *filename, *fullname;
		
    filename = g_strconcat ("../pixmaps/", items[i], ".png", NULL);
    fullname = g_strdup (filename);
    g_free (filename);
		
    pixbuf = gdk_pixbuf_new_from_file (fullname, NULL);
    g_free (fullname);

    icon_set = gtk_icon_set_new_from_pixbuf (pixbuf);
    gtk_icon_factory_add (factory, items[i], icon_set);
    gtk_icon_set_unref (icon_set);

    g_object_unref (G_OBJECT (pixbuf));
  }
	
  g_object_unref (G_OBJECT (factory));
}
